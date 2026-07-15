"""
[DURASI-F2] Kalibrasi durasi dari render NYATA — dua besaran, SATU sumber data (tts_delivery_samples):
  1. α respons-speed per PROVIDER  → tts_speed_response   (regresi log-log; EL terukur α≈1.32 R²=0.80)
  2. pace per (VOICE × NICHE)      → tts_pace_calibration (median tahan-outlier; inversi SADAR-α)

AKAR (data 110 render + backfill log 2026-07-15/16): estimator menebak pace 1-angka & menganggap provider
patuh-penuh pada speed; kenyataan pace berubah per (voice × gaya-DNA-niche) s/d 25% DAN ElevenLabs
melebih-lebihkan speed → taksiran salah → 85% video PENDEK. Bukti replay leave-one-out (2026-07-16):
error taksiran 9.3% → 4.7% (median), dalam-±10% 54% → 74%, SEMUA 8 niche membaik.

MODEL (identik estimator script_engine §10.A — konstanta di-IMPORT, bukan disalin):
    est = words / (delivery_wps × _PAUSE_INFLATION × speed^α) + pause
Inversi pace per sampel (raw_audio_secs = durasi MENTAH pra-atempo, pembanding sah):
    delivery_wps_i = words / ((raw_audio − pause) × speed^α × _PAUSE_INFLATION)

PAGAR ANTI-RANJAU:
  • HANYA menulis 2 tabel BARU (additif; kosong = perilaku lama persis — α default 1.0, pace fallback lapis lama).
  • `voice_catalog.pace_locked=true` → voice TIDAK ditulis + baris kalibrasi lamanya DIHAPUS (admin berdaulat).
  • Sel < PACE_CALIB_MIN_N sampel tidak ditulis; α butuh ≥ PACE_CALIB_ALPHA_MIN_N (kurang bukti ≠ menebak).
  • Nilai di luar pagar (pace [1.0,4.0] · α [0.5,2.0]) → DILEWATI + warning (gagal jujur, TIDAK di-clamp senyap).
  • Sampel tak layak dibuang eksplisit (kata < PACE_CALIB_MIN_WORDS · raw≤0 · speed≤0 · pause_secs NULL ·
    speech < 30% raw → model-jeda tak bisa dipercaya utk sampel itu).
Konsumsi (tenant_config → script_engine): pace (voice×niche) → (voice,'*') → voice_catalog → tts_profiles;
α per provider → estimator+solver (tanpa baris → 1.0).
Penjadwalan berkala + alarm drift = F5 (belum — modul ini dipanggil manual/di-wire nanti).
"""

import os
import math
import statistics
from loguru import logger

# Pagar nilai: pace = rentang admin voice_catalog; α = pagar teknis (0.5–2.0; di luar itu data rusak).
_WPS_LO, _WPS_HI     = 1.0, 4.0
_ALPHA_LO, _ALPHA_HI = 0.5, 2.0
# Porsi minimal waktu-bicara dari durasi mentah; di bawah ini model-jeda mendominasi → sampel tak layak.
_MIN_SPEECH_FRACTION = 0.30


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _fit_alpha(points: list) -> tuple:
    """Regresi linear ln(rate) = ln(swps) + α·ln(speed). points = [(speed, rate_obs)]. Return (α, r²)."""
    xs = [math.log(s) for s, _ in points]
    ys = [math.log(r) for _, r in points]
    n  = len(points)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:  # semua speed identik → α tak teridentifikasi (bukan 1.0 palsu — jangan tulis)
        return None, 0.0
    a = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / sxx
    c = my - a * mx
    ss_res = sum((ys[i] - (a * xs[i] + c)) ** 2 for i in range(n))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return a, (1 - ss_res / ss_tot if ss_tot else 0.0)


def compute_pace_calibration(sb=None, dry_run: bool = False) -> dict:
    """Hitung α per provider + pace per (voice×niche & voice,'*') dari tts_delivery_samples → upsert
    tts_speed_response + tts_pace_calibration. dry_run=True → hitung saja, NOL tulis.
    Fail-soft total: exception → log + return {"error": ...} — TIDAK pernah mengganggu produksi."""
    try:
        from src.intelligence.script_engine import _PAUSE_INFLATION  # SATU sumber konstanta (no-copy)
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        min_n       = _env_int("PACE_CALIB_MIN_N", 5)        # bukti minimal per sel pace
        min_words   = _env_int("PACE_CALIB_MIN_WORDS", 5)    # naskah super-pendek = rasio jeda liar
        alpha_min_n = _env_int("PACE_CALIB_ALPHA_MIN_N", 10) # α = regresi; butuh lebih banyak titik

        locked = {r["voice_key"] for r in
                  (sb.table("voice_catalog").select("voice_key,pace_locked")
                     .eq("pace_locked", True).execute().data or [])}

        rows, off = [], 0
        while True:  # paginasi manual — jangan percaya cap default (pelajaran undercount 7.220-vs-1000)
            b = (sb.table("tts_delivery_samples")
                   .select("provider,voice_key,niche,speed,words,raw_audio_secs,pause_secs")
                   .range(off, off + 999).execute().data or [])
            rows += b
            if len(b) < 1000:
                break
            off += 1000

        # ── saring sampel layak ──
        ok, skipped = [], 0
        for r in rows:
            try:
                w  = float(r.get("words") or 0)
                ra = float(r.get("raw_audio_secs") or 0)
                sp = float(r.get("speed") or 0)
                pa = r.get("pause_secs")
                if (not r.get("voice_key")) or (not r.get("niche")) or (not r.get("provider")) \
                   or w < min_words or ra <= 0 or sp <= 0 or pa is None:
                    skipped += 1; continue
                speech = ra - float(pa)
                if speech < _MIN_SPEECH_FRACTION * ra:
                    skipped += 1; continue
                ok.append(dict(pv=r["provider"], vk=r["voice_key"], niche=r["niche"],
                               w=w, sp=sp, speech=speech))
            except Exception:
                skipped += 1

        # ── LANGKAH 1: α per provider (dipakai inversi pace di langkah 2) ──
        alphas, alpha_rows, alpha_rejected = {}, [], []
        byprov = {}
        for s in ok:
            byprov.setdefault(s["pv"], []).append((s["sp"], s["w"] / s["speech"]))
        for pv, pts in sorted(byprov.items()):
            if len(pts) < alpha_min_n:
                continue                                   # tanpa baris → konsumen pakai 1.0 (perilaku lama)
            a, r2 = _fit_alpha(pts)
            if a is None or not (_ALPHA_LO <= a <= _ALPHA_HI):
                alpha_rejected.append((pv, a, len(pts)))
                logger.warning(f"[PaceCalib] α {pv}={a} di luar pagar [{_ALPHA_LO},{_ALPHA_HI}] "
                               f"atau tak teridentifikasi — DILEWATI (konsumen tetap 1.0)")
                continue
            alphas[pv] = round(a, 3)
            alpha_rows.append({"provider": pv, "alpha": round(a, 3), "sample_n": len(pts)})
            logger.info(f"[PaceCalib] α {pv} = {a:.3f} (n={len(pts)}, R²={r2:.2f})")

        # ── LANGKAH 2: pace per sel, inversi SADAR-α (provider tanpa α → 1.0) ──
        cells = {}
        used = 0
        for s in ok:
            if s["vk"] in locked:
                continue
            a = alphas.get(s["pv"], 1.0)
            wps = s["w"] / (s["speech"] * (s["sp"] ** a) * float(_PAUSE_INFLATION))
            cells.setdefault((s["vk"], s["niche"]), []).append(wps)
            cells.setdefault((s["vk"], "*"), []).append(wps)
            used += 1

        written, rejected_range, below_min = [], [], 0
        for (vk, niche), vals in sorted(cells.items()):
            if len(vals) < min_n:
                below_min += 1; continue
            med = round(statistics.median(vals), 3)
            if not (_WPS_LO <= med <= _WPS_HI):
                rejected_range.append((vk, niche, med, len(vals)))
                logger.warning(f"[PaceCalib] sel ({vk},{niche}) median {med} di luar pagar "
                               f"[{_WPS_LO},{_WPS_HI}] — DILEWATI (data dicurigai, tidak di-clamp)")
                continue
            written.append({"voice_key": vk, "niche": niche, "delivery_wps": med, "sample_n": len(vals)})

        if not dry_run:
            if alpha_rows:
                sb.table("tts_speed_response").upsert(alpha_rows).execute()
            if written:
                sb.table("tts_pace_calibration").upsert(written).execute()
            for vk in locked:  # admin lock → bersihkan jejak kalibrasi voice itu
                sb.table("tts_pace_calibration").delete().eq("voice_key", vk).execute()

        summary = {"samples_used": used, "samples_skipped": skipped,
                   "alphas": alphas, "alpha_rejected": alpha_rejected,
                   "cells_written": len(written), "cells_below_min_n": below_min,
                   "cells_rejected_range": rejected_range, "locked_voices": sorted(locked),
                   "min_n": min_n, "dry_run": dry_run, "rows": written}
        logger.info(f"[PaceCalib] used={used} skipped={skipped} α={alphas} cells={len(written)} "
                    f"below_min={below_min} rejected={len(rejected_range)} locked={len(locked)} dry_run={dry_run}")
        return summary
    except Exception as e:
        logger.error(f"[PaceCalib] gagal (fail-soft, produksi tak terganggu): {e}")
        return {"error": str(e)}
