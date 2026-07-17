"""
TTS Engine — provider/voice dari CHANNEL via registry config-driven, NO-FALLBACK.
Fase 6C s6c8:
  - Provider/voice dari CHANNEL (channels.tts_provider/voice_key, §10.B FINAL) — config-driven
  - NO-FALLBACK (F1-05): provider gagal = gagal jujur + log, tak pindah diam-diam
  - Delivery override per-tenant via tts_voice_settings (mis. ryan speed)
"""

import asyncio
import os
import time
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig
from src.exceptions import ErrorClass, PipelineError

load_dotenv()

def _build_full_script(script: dict) -> str:
    """
    Susun full script dari dict.
    Cover 8 section (bukan 5 section lama).
    Priority: full_script field → gabung semua section.
    """
    full = script.get("full_script", "").strip()
    if full:
        return full

    # Fallback: gabung semua section — SATU SUMBER kosakata (0128)
    from src.content import beats as _beats
    sections = _beats.all_beats()
    parts = [script.get(s, "").strip() for s in sections if script.get(s)]
    return " ".join(parts)


def _get_provider_config(tenant_config: TenantConfig) -> dict:
    """F1-05/§10.B FINAL: Load config CHANNEL-AWARE (provider+voice dari channel; voice ter-resolve di
    load_tenant_config = channels.voice_key SAJA — voice = channel, niche provider-agnostik). NO fallback
    provider, NO map hardcode (voice = config['tts_voice'] yang sudah resolved). Keys dari tenant DB only.
    """
    from src.config.tenant_config import load_tenant_config
    rc = load_tenant_config(
        tenant_config.tenant_id,
        getattr(tenant_config, "channel_id", None),
        getattr(tenant_config, "niche", None),
    )
    return {
        "tts_provider":        rc.tts_provider,
        "tts_voice":           rc.tts_voice,                 # sudah resolved (channel/niche) — provider pakai apa adanya
        "tts_model":           rc.tts_model or "",
        "tts_api_key":         rc.tts_api_key or "",
        "tts_voice_settings":  getattr(rc, "tts_voice_settings", {}) or {},          # delivery override per-tenant (mis. ryan speed)
        "tts_voice_default_settings": getattr(rc, "tts_voice_default_settings", {}) or {},  # baseline delivery dari voice_catalog
        "niche_voice_expression": getattr(rc, "niche_voice_expression", None),  # [EKSPRESI VOKAL] gaya-baca per-niche (niches.voice_expression)
        "visual_api_key":      getattr(rc, "visual_api_key", "") or "",
        "niche":               tenant_config.niche,
        "tenant_id":           tenant_config.tenant_id,
    }


def _run_provider(provider_name: str, text: str, config: dict, output_dir: str) -> tuple[str, list[dict]]:
    """
    Jalankan satu TTS provider.
    Return (audio_path, word_timestamps) atau raise Exception jika gagal.
    """
    timestamp   = int(time.time())
    tenant_id   = config.get("tenant_id", "default")
    output_path = Path(output_dir) / f"audio_{tenant_id}_{timestamp}.mp3"

    # F5-06: dispatch DB-driven via registry (tts_profiles.adapter) — ganti if/elif hardcode.
    from src.providers.tts import build_tts_provider
    provider = build_tts_provider(provider_name, config)

    audio = asyncio.run(provider.generate(text, output_path))
    timestamps = provider.get_word_timestamps() or []
    return str(audio), timestamps


def _log_delivery_sample(tenant_config, config: dict, provider_name: str, word_count: int, audio_path: str,
                         script: dict | None = None, target_audio_secs: float | None = None,
                         text: str | None = None, raw_audio_secs: float | None = None) -> None:
    """F4-01: 1 baris per render TTS SUKSES → tts_delivery_samples (delivery NYATA per voice×speed).
    Dipakai F5-01 (kalibrasi pace EWMA → ganti seed P) + verifikasi akurasi P §10.D. Best-effort/fail-soft,
    NOL pengaruh produksi. speed = yg BENAR-BENAR dipakai provider (incl. override LLM §10.A).

    DURASI-F1 (instrumentasi): rekam TAKSIRAN model vs AKTUAL + rincian jeda → error estimator TERUKUR (kalibrasi F2).
      • predicted_secs/pause_secs = dari script["_duration_est"] (diisi script_engine utk run ber-preset; None → NULL)
      • raw_audio_secs            = durasi MENTAH sebelum atempo (pembanding sah; None → pakai audio_secs = tanpa closed-loop)
      • target_secs               = target audio (preset − trailing)
      • pause_counts              = _count_pauses(text) — rincian tanda-jeda dari naskah
    Semua field F1 di-guard; gagal hitung salah satu TIDAK menggagalkan insert (nullable). NOL ffprobe tambahan."""
    try:
        niche = config.get("niche")
        _vs   = (config.get("tts_voice_settings") or {}).get(niche) or {}
        speed = _vs.get("speed") or (config.get("tts_voice_default_settings") or {}).get("speed") or 1.0
        audio_secs = TTSEngine.get_duration(audio_path)
        # F1: field observasi (masing-masing best-effort; None bila tak tersedia → kolom NULL)
        _de = (script or {}).get("_duration_est") if isinstance(script, dict) else None
        _de = _de if isinstance(_de, dict) else {}
        _predicted = _de.get("est_seconds")
        _pause_est = _de.get("pause_seconds")
        _raw = raw_audio_secs if raw_audio_secs is not None else audio_secs   # tanpa closed-loop, mentah = final
        _pause_counts = None
        if text:
            try:
                from src.intelligence.script_engine import _count_pauses   # lazy: hindari circular + fail-soft
                _pause_counts = _count_pauses(text)
            except Exception:
                _pause_counts = None
        # [DURASI-F5] kata NYATA per-beat dari naskah final (ground-truth; hitungan SISTEM, bukan
        # laporan LLM) → bahan penyelarasan bobot-beat berkala. Fail-soft → NULL.
        _beat_words = None
        try:
            from src.content import beats as _cbeats
            _bw = {b: len((script.get(b) or "").split()) for b in _cbeats.all_beats()
                   if isinstance(script, dict) and (script.get(b) or "").strip()}
            _beat_words = _bw or None
        except Exception:
            _beat_words = None
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        sb.table("tts_delivery_samples").insert({
            "tenant_id":  config.get("tenant_id"),
            "channel_id": str(getattr(tenant_config, "channel_id", None) or ""),
            "niche":      niche,
            "provider":   provider_name,
            "voice_key":  config.get("tts_voice"),
            "speed":      round(float(speed), 4),
            "words":      int(word_count),
            "audio_secs": round(float(audio_secs), 2),
            "preset":     getattr(tenant_config, "duration_preset", None),
            # DURASI-F1
            "predicted_secs": round(float(_predicted), 2) if _predicted is not None else None,
            "raw_audio_secs": round(float(_raw), 2) if _raw is not None else None,
            "target_secs":    round(float(target_audio_secs), 2) if target_audio_secs is not None else None,
            "pause_secs":     round(float(_pause_est), 2) if _pause_est is not None else None,
            "pause_counts":   _pause_counts,
            "beat_words":     _beat_words,   # [DURASI-F5]
        }).execute()
        logger.info(f"[TTSEngine] F4-01 sample: {word_count}w @spd{speed} → {audio_secs:.1f}s "
                    f"(raw {round(float(_raw),1) if _raw is not None else '?'}s, pred "
                    f"{round(float(_predicted),1) if _predicted is not None else '?'}s) ({provider_name}/{niche})")
    except Exception as e:
        logger.debug(f"[TTSEngine] log delivery sample skip (non-fatal): {e}")


class TTSEngine:
    """
    TTS Engine TUNGGAL — provider+voice dari CHANNEL, dispatch protokol via registry config-driven
    (build_tts_provider → tts_profiles.adapter, F5-06). NO-FALLBACK (§3.8/F1-05): HANYA provider
    terkonfigurasi channel; gagal = gagal jujur (tak pindah diam-diam). Adaptor per-protokol di src/providers/tts/.
    """

    def __init__(self):
        # Transparansi (§4b): dipakai pipeline untuk advisory — provider TERKONFIGURASI
        # vs yang AKTUAL me-render. Di-set ulang tiap generate().
        self.last_primary = None
        self.last_provider = None
        self.last_fallback_used = False   # no-fallback (F1-05): selalu False; dipertahankan utk advisory pipeline
        # [ERROR-MGMT] detail error TERAKHIR — dipropagasi pipeline (error TTS ditelan di sini,
        # return "",[]; tanpa ini detail provider [billing/quota] hilang). Di-reset tiap generate().
        self.last_error = None
        self.last_error_class = ErrorClass.UNKNOWN
        self.last_human_error = None

    def generate(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
        target_audio_secs: float | None = None,
        overhead_secs: float | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Generate audio dari script.
        target_audio_secs: target durasi AUDIO (preset − overhead). Bila di-set → closed-loop
        durasi: ukur audio, kalau di luar window QC → atempo (time-stretch, NOL biaya TTS) ke target +
        skala word_timestamps. None → perilaku lama (open-loop, non-breaking).
        overhead_secs [DURASI-3+F4]: overhead render PENUH (trailing efektif + loop bersih;
        format_catalog.effective_overhead — rumus SAMA dgn naskah/gerbang/renderer) utk window
        _fit_duration. None → env RENDER_TRAILING_SILENCE (perilaku lama, non-breaking).
        Returns: (audio_path, word_timestamps)
        """
        os.makedirs(output_dir, exist_ok=True)

        # Susun text — cover 8 section
        text = _build_full_script(script)
        if not text:
            logger.error("[TTSEngine] Script kosong — tidak bisa generate TTS")
            return "", []

        word_count = len(text.split())
        logger.info(f"[TTSEngine] Generating TTS: {word_count} words")

        # Load config CHANNEL-AWARE (F1-05)
        config   = _get_provider_config(tenant_config)
        # F4-03 (§10.A DURASI-VIA-SPEED): pakai SPEED pilihan LLM (script.tts_params.speed) — override
        # speed-niche statik. Speed inilah yg membuat durasi mendarat (LLM sudah nudge W÷(P×speed)≈target).
        # Clamp [0.7,1.2] (= param_schema EL; openai lebih lebar; edge pakai rate → speed diabaikan). Per-call.
        try:
            _llm_speed = (script.get("tts_params") or {}).get("speed")
            if _llm_speed is not None:
                # Clamp PROVIDER-AWARE (multi-provider, no-hardcode): rentang dari tts_profiles per provider
                # (EL speed[0.7,1.2] · openai[0.25,4.0] · edge rate→pengali). Gate sudah clamp ke comfort;
                # ini jaring defensif. Ganti hardcode EL-spesifik [0.7,1.2] lama.
                from src.config.format_catalog import tts_speed_range as _tsr
                _plo, _phi = _tsr(config.get("tts_provider"))
                _llm_speed = round(min(_phi, max(_plo, float(_llm_speed))), 3)
                _niche_k = config.get("niche")
                _vs = dict(config.get("tts_voice_settings") or {})
                _vs[_niche_k] = {**(_vs.get(_niche_k) or {}), "speed": _llm_speed}
                config["tts_voice_settings"] = _vs
                logger.info(f"[TTSEngine] §10.A speed dari LLM = {_llm_speed} (niche={_niche_k}) — override speed statik")
        except Exception as _se:
            logger.warning(f"[TTSEngine] inject LLM speed gagal (pakai speed config): {_se}")
        primary  = config.get("tts_provider")
        # F1-05 NO-FALLBACK (§3.8/§10.E): produksi pakai HANYA provider terkonfigurasi channel.
        # Provider tak terkonfigurasi / gagal → GAGAL JUJUR (tak pindah diam-diam ke edge).
        if not primary:
            logger.error("[TTSEngine] tts_provider channel belum dikonfigurasi — gagal jujur (no-fallback)")
            return "", []
        logger.info(f"[TTSEngine] Provider (no-fallback): {primary}")
        self.last_primary = primary
        self.last_provider = None
        self.last_fallback_used = False
        self.last_error = None                       # [ERROR-MGMT] reset per generate
        self.last_error_class = ErrorClass.UNKNOWN
        self.last_human_error = None
        # NO-FALLBACK (F1-05/§3.8): HANYA provider terkonfigurasi channel — gagal = GAGAL JUJUR (tak pindah diam-diam).
        try:
            logger.info(f"[TTSEngine] Generating with: {primary}")
            audio_path, word_timestamps = _run_provider(primary, text, config, output_dir)

            if audio_path and os.path.exists(audio_path):
                self.last_provider = primary           # transparansi pipeline (§4b)
                self.last_fallback_used = False         # no-fallback → selalu False
                size_kb    = os.path.getsize(audio_path) / 1024
                ts_count   = len(word_timestamps)
                ts_quality = "~98% akurasi" if primary == "elevenlabs" else \
                             "tidak tersedia" if primary == "openai_tts" else \
                             "~80% estimasi"
                logger.info(f"[TTSEngine] ✅ {primary}: {size_kb:.1f}KB | {ts_count} word timestamps ({ts_quality})")
                # Closed-loop durasi (opsional, NOL biaya TTS): rapikan via atempo bila di luar window.
                # DURASI-F1: ukur durasi MENTAH SEKALI di sini → dipakai-ulang oleh _fit_duration (lewati
                # ffprobe internalnya) + direkam ke sampel (raw_audio_secs). Jumlah ffprobe = SAMA dgn
                # sebelumnya → NOL penambahan waktu pipeline.
                _raw_secs = None
                if target_audio_secs and target_audio_secs > 0:
                    _raw_secs = TTSEngine.get_duration(audio_path)
                    audio_path, word_timestamps = self._fit_duration(
                        audio_path, word_timestamps, float(target_audio_secs), output_dir,
                        precomputed_actual=_raw_secs, overhead_secs=overhead_secs,
                    )
                # F4-01 observability: catat delivery NYATA (best-effort) → kalibrasi pace F5-01 + verifikasi P §10.D.
                # DURASI-F1: + taksiran vs aktual + jeda (script["_duration_est"], target, teks, raw pra-atempo).
                _log_delivery_sample(tenant_config, config, primary, word_count, audio_path,
                                     script=script, target_audio_secs=target_audio_secs,
                                     text=text, raw_audio_secs=_raw_secs)
                # B2 cost-tracking: TTS ditagih per KARAKTER teks (fakta billing ElevenLabs/OpenAI;
                # edge gratis → harga 0 di katalog). Dicatat per model TTS channel. Fail-soft.
                try:
                    from src.utils import cost_meter
                    cost_meter.add_tts(config.get("tts_model") or primary, len(text))
                except Exception:
                    pass
                return audio_path, word_timestamps

            logger.error(f"[TTSEngine] {primary}: audio kosong/tak terbentuk — gagal jujur (no-fallback)")
            return "", []
        except Exception as e:
            # [ERROR-MGMT] simpan detail (error ditelan di sini → return "",[]) agar pipeline bisa
            # meneruskan makna + pesan manusiawi. Perilaku return TIDAK berubah (nol regresi pemanggil).
            self.last_error = str(e)
            if isinstance(e, PipelineError):
                self.last_error_class = getattr(e, "error_class", ErrorClass.UNKNOWN)
                self.last_human_error = getattr(e, "human_message", None)
            else:
                self.last_error_class = ErrorClass.UNKNOWN
                self.last_human_error = None
            logger.error(f"[TTSEngine] {primary} failed: {e} — gagal jujur (no-fallback)")
            return "", []

    @staticmethod
    def get_duration(audio_path: str) -> float:
        """Durasi audio via ffprobe (akurat untuk semua bitrate/provider)."""
        import subprocess, json
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", audio_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                dur = stream.get("duration")
                if dur:
                    return round(float(dur), 1)
        except Exception:
            pass
        # Fallback: estimasi dari file size (128 kbps — hanya untuk ElevenLabs/OpenAI TTS)
        try:
            size_bytes = os.path.getsize(audio_path)
            return round((size_bytes * 8) / (128 * 1000), 1)
        except Exception:
            return 0.0

    @staticmethod
    def _fit_duration(audio_path: str, word_timestamps: list, target_secs: float, output_dir: str,
                      precomputed_actual: float | None = None, overhead_secs: float | None = None):
        """Closed-loop durasi TANPA biaya TTS ekstra (akar: kecepatan bicara EL bervariasi ±15%).
        SYARAT (kesepakatan owner): hanya dipakai pada audio dari naskah yg SUDAH lulus gate mutu;
        koreksi HANYA bila hasil di luar window QC; HANYA bila faktor dalam batas aman (suara tak rusak);
        kalau di luar batas → biarkan apa adanya (→ ready_with_issues, mutu suara > paksa durasi).
        Caption: word_timestamps diskala dgn faktor yg sama → tetap sinkron.
        atempo: out_dur = in_dur / factor (pitch tetap).
        DURASI-F1: precomputed_actual = durasi mentah yg SUDAH diukur pemanggil → dipakai-ulang
        (hemat 1 ffprobe, nol tambah waktu). None → ukur sendiri (perilaku lama persis)."""
        try:
            actual = float(precomputed_actual) if precomputed_actual is not None else TTSEngine.get_duration(audio_path)
            if actual <= 0:
                return audio_path, word_timestamps
            # [DURASI-3+F4] overhead dari pemanggil = PENUH per-preset (trailing efektif + loop bersih;
            # rumus sama dgn naskah/gerbang/renderer). None → env trailing (perilaku lama, non-breaking).
            trailing = float(overhead_secs) if overhead_secs is not None else float(os.getenv("RENDER_TRAILING_SILENCE", "1.5"))
            tol      = float(os.getenv("QC_DURATION_TOLERANCE", "0.15"))
            preset   = target_secs + trailing            # target FINAL ≈ preset (audio + overhead penuh)
            final_est = actual + trailing
            lo, hi   = preset * (1 - tol), preset * (1 + tol)
            if lo <= final_est <= hi:
                return audio_path, word_timestamps        # sudah dalam window → JANGAN sentuh suara
            factor = actual / target_secs                 # atempo value
            amin = float(os.getenv("TTS_ATEMPO_MIN", "0.80"))
            amax = float(os.getenv("TTS_ATEMPO_MAX", "1.35"))  # §10.A lebarkan: tangkap sisa overshoot jeda (1.35=mutu masih oke)
            if not (amin <= factor <= amax):
                logger.warning(
                    f"[TTSEngine] durasi {actual:.1f}s vs target {target_secs:.1f}s — faktor {factor:.2f} "
                    f"di luar batas aman [{amin},{amax}] → TIDAK di-atempo (jaga mutu suara) → ready_with_issues"
                )
                return audio_path, word_timestamps
            import subprocess
            out = os.path.join(output_dir, "fit_" + os.path.basename(audio_path))
            subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path, "-filter:a", f"atempo={factor:.4f}", "-vn", out],
                check=True, capture_output=True,
            )
            scale  = 1.0 / factor                          # new_dur/old_dur → skala timestamp
            scaled = [{**w, "start": float(w.get("start", 0)) * scale, "end": float(w.get("end", 0)) * scale}
                      for w in (word_timestamps or [])]
            new = TTSEngine.get_duration(out)
            logger.info(
                f"[TTSEngine] ⏱ atempo fit: {actual:.1f}s → {new:.1f}s (target {target_secs:.1f}s, "
                f"factor {factor:.3f}) — caption diskala, biaya EL=0"
            )
            return out, scaled
        except Exception as e:
            logger.warning(f"[TTSEngine] fit durasi gagal ({e}) — pakai audio asli")
            return audio_path, word_timestamps
