"""
TTS Engine — provider/voice dari CHANNEL via registry config-driven, NO-FALLBACK.
Fase 6C s6c8:
  - Provider/voice dari CHANNEL (channels.tts_provider/voice_key, §10.B FINAL) — config-driven
  - NO-FALLBACK (F1-05): provider gagal = gagal jujur + log, tak pindah diam-diam
  - Delivery override per-tenant via tts_voice_settings (mis. ryan speed)
"""

import asyncio
import os
import re
import subprocess
import time
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig
from src.config import ambang as _ambang
from src.exceptions import ErrorClass, PipelineError, TTSError

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
        # voice = kunci KATALOG (channels.voice_key). Untuk penyedia AGREGATOR, build_tts_provider
        # menerjemahkannya ke identitas vendor (voice_catalog.vendor_voice_id) di SALINAN config —
        # nilai di sini tetap kunci katalog, sebab dipakai sampel pace & atribusi video di bawah.
        "tts_voice":           rc.tts_voice,
        "tts_model":           rc.tts_model or "",
        "tts_api_key":         rc.tts_api_key or "",
        "tts_voice_settings":  getattr(rc, "tts_voice_settings", {}) or {},          # delivery override per-tenant (mis. ryan speed)
        "tts_voice_default_settings": getattr(rc, "tts_voice_default_settings", {}) or {},  # baseline delivery dari voice_catalog
        "niche_voice_expression": getattr(rc, "niche_voice_expression", None),  # [EKSPRESI VOKAL] gaya-baca per-niche (niches.voice_expression)
        "visual_api_key":      getattr(rc, "visual_api_key", "") or "",
        # Koefisien durasi suara ini — dipakai penjaga audio-terpotong PER POTONGAN pada naskah
        # panjang (video Regular). Tanpa ini, potongan dinilai dengan angka bawaan, dan suara yang
        # jauh dari bawaan (ElevenLabs) bisa lolos/tertuduh keliru.
        "duration_calibration": getattr(rc, "duration_calibration", None),
        "niche":               tenant_config.niche,
        "tenant_id":           tenant_config.tenant_id,
    }


def _voice_rate_of(provider) -> str | None:
    """[0184] Setelan laju yang BENAR-BENAR dipakai adaptor (bukan dihitung ulang di sini).
    Adaptor yang tak punya konsep ini → None → sampel tidak dipakai kalibrasi (gagal-aman)."""
    v = getattr(provider, "effective_rate", None)
    return str(v) if v else None


def _potong_kalimat(teks: str, maks_huruf: int) -> list[str]:
    """Pecah naskah panjang di BATAS KALIMAT, tiap potongan ≤ `maks_huruf`.

    Memotong di tengah kalimat akan terdengar: narator berhenti mendadak lalu memulai lagi dengan
    intonasi awal-kalimat. Karena itu batas potongnya selalu akhir kalimat. Satu kalimat yang sendirian
    sudah melebihi batas TIDAK dipotong paksa — dikirim apa adanya (lebih baik satu permintaan besar
    daripada narasi yang patah di tengah kalimat)."""
    t = (teks or "").strip()
    if not t or len(t) <= maks_huruf:
        return [t] if t else []
    kalimat = re.split(r"(?<=[.!?…])\s+", t)
    potongan, kini = [], ""
    for k in kalimat:
        if not k:
            continue
        if kini and len(kini) + 1 + len(k) > maks_huruf:
            potongan.append(kini)
            kini = k
        else:
            kini = f"{kini} {k}".strip() if kini else k
    if kini:
        potongan.append(kini)
    return potongan


def _sambung_audio(bagian: list[Path], keluaran: Path) -> Path:
    """Sambung potongan audio jadi satu berkas, tanpa jeda tambahan di sambungannya.

    Dipakai `ffmpeg concat` dengan RE-ENCODE: menyambung mp3 mentah (copy) menyisakan padding encoder
    di tiap sambungan — terdengar sebagai 'tik' halus dan menambah durasi yang tak terhitung model."""
    daftar = keluaran.parent / f"{keluaran.stem}_daftar.txt"
    daftar.write_text("\n".join(f"file '{p.as_posix()}'" for p in bagian), encoding="utf-8")
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(daftar),
                        "-c:a", "libmp3lame", "-b:a", "128k", str(keluaran)],
                       capture_output=True, timeout=600)
    try:
        daftar.unlink()
    except OSError:
        pass
    if r.returncode != 0 or not keluaran.exists() or keluaran.stat().st_size < 2000:
        raise TTSError(f"Penyambungan potongan suara gagal: {r.stderr[-200:].decode('utf-8', 'replace')}",
                       error_class=ErrorClass.TRANSIENT)
    return keluaran


def _geser_timestamp(ts: list[dict], offset: float) -> list[dict]:
    """Geser penanda waktu satu potongan ke posisinya di audio gabungan (caption tetap presisi)."""
    out = []
    for w in ts or []:
        try:
            out.append({**w, "start": float(w.get("start", 0)) + offset,
                        "end": float(w.get("end", 0)) + offset})
        except (TypeError, ValueError):
            continue
    return out


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

    # ── BATAS WAKTU: penyedia yang MENGGANTUNG tidak boleh mematikan utas pekerja ─────────────────
    # Sampai 2026-08-01 panggilan ini tanpa batas waktu sama sekali. Adaptor Edge (penyedia BAWAAN
    # semua tenant) membaca aliran websocket; bila vendor berhenti mengirim tanpa menutup sambungan,
    # `generate` tidak pernah kembali. Terjadi nyata saat pengukuran hari ini: satu render berhenti
    # dan prosesnya diam belasan menit.
    # Di produksi akibatnya kelas "gagal senyap" yang paling mahal: satu dari tujuh utas pekerja mati
    # selamanya — tanpa error, tanpa notifikasi, tanpa jejak di log. Channel itu berhenti berproduksi
    # dan tak seorang pun tahu sebabnya; utas berikutnya yang menggantung memakan kapasitas berikutnya.
    # Batasnya ikut panjang naskah (naskah Regular 1.000+ kata memang lama), sangat longgar terhadap
    # kecepatan normal (Edge ±500 huruf ≈ 5 dtk), dan hasilnya TRANSIENT = produksi diulang.
    _detik = min(_ambang.detik("tts_timeout_maks_sec", 900),
                 _ambang.detik("tts_timeout_dasar_sec", 180)
                 + _ambang.milidetik("tts_timeout_per_huruf_ms", 200) * len(text or ""))

    # ── NASKAH PANJANG (video Regular 2–12 menit) DIPOTONG & DISAMBUNG ───────────────────────────
    # Naskah 1.000+ kata (±6.000–11.000 huruf) melampaui batas satu permintaan di semua penyedia, dan
    # bahkan bila diterima, satu permintaan sebesar itu jauh lebih sering menggantung atau terputus di
    # tengah. Potongannya SELALU di batas kalimat (memotong di tengah kalimat terdengar: narator
    # berhenti mendadak lalu memulai lagi dengan intonasi awal-kalimat).
    # Penjaga audio-terpotong tetap berlaku PER POTONGAN — justru di sinilah ia paling dibutuhkan,
    # sebab satu potongan yang gagal di tengah akan tersembunyi di dalam audio gabungan yang panjang.
    _maks_huruf = _ambang.angka("tts_chunk_maks_huruf", 3000)
    _bagian_teks = _potong_kalimat(text, _maks_huruf)
    if len(_bagian_teks) > 1:
        logger.info(f"[TTSEngine] naskah {len(text)} huruf → {len(_bagian_teks)} potongan "
                    f"(batas {_maks_huruf} huruf/potongan, dipotong di batas kalimat)")
        from src.production.duration_model import prediksi_audio as _pred
        _kalib = config.get("duration_calibration")
        _berkas, _ts_gab, _offset = [], [], 0.0
        for _i, _bt in enumerate(_bagian_teks, 1):
            _pp = Path(output_dir) / f"{output_path.stem}_bagian{_i:02d}.mp3"
            _det_b = min(_ambang.detik("tts_timeout_maks_sec", 900),
                         _ambang.detik("tts_timeout_dasar_sec", 180)
                         + _ambang.milidetik("tts_timeout_per_huruf_ms", 200) * len(_bt))
            _prov_b = build_tts_provider(provider_name, config)
            try:
                asyncio.run(asyncio.wait_for(_prov_b.generate(_bt, _pp), timeout=_det_b))
            except asyncio.TimeoutError:
                raise TTSError(f"Penyedia suara '{provider_name}' tidak menyelesaikan potongan {_i} "
                               f"dari {len(_bagian_teks)} dalam {_det_b:.0f} detik.",
                               error_class=ErrorClass.TRANSIENT)
            _d = TTSEngine.get_duration(str(_pp))
            _ramal_b = _pred(_bt, _kalib)
            _amb_potong = _ambang.pct("tts_potong_ambang_pct", 75)
            if _ramal_b > 0 and _d > 0 and (_d / _ramal_b) < _amb_potong:
                raise TTSError(
                    f"Suara potongan {_i} dari {len(_bagian_teks)} tidak lengkap: {_d:.1f} dtk "
                    f"padahal seharusnya ±{_ramal_b:.1f} dtk. Narasi akan terputus di tengah video — "
                    f"produksi dihentikan agar tidak menghasilkan video cacat.",
                    error_class=ErrorClass.TRANSIENT)
            _ts_gab += _geser_timestamp(_prov_b.get_word_timestamps() or [], _offset)
            _offset += _d
            _berkas.append(_pp)
            logger.info(f"[TTSEngine] potongan {_i}/{len(_bagian_teks)}: {len(_bt)} huruf → {_d:.1f} dtk")
        _sambung_audio(_berkas, output_path)
        for _pp in _berkas:
            try:
                _pp.unlink()
            except OSError:
                pass
        logger.info(f"[TTSEngine] {len(_berkas)} potongan disambung → {TTSEngine.get_duration(str(output_path)):.1f} dtk")
        return str(output_path), _ts_gab, _voice_rate_of(provider)

    async def _dengan_batas():
        return await asyncio.wait_for(provider.generate(text, output_path), timeout=_detik)

    try:
        audio = asyncio.run(_dengan_batas())
    except asyncio.TimeoutError:
        try:
            if output_path.exists():
                output_path.unlink()      # berkas separuh jadi tak boleh tertinggal
        except OSError:
            pass
        raise TTSError(
            f"Penyedia suara '{provider_name}' tidak menyelesaikan permintaan dalam {_detik:.0f} detik "
            f"({len(text or '')} huruf). Produksi dihentikan agar tidak menggantung — akan diulang.",
            error_class=ErrorClass.TRANSIENT)
    timestamps = provider.get_word_timestamps() or []
    return str(audio), timestamps, _voice_rate_of(provider)


def _chars_of(text: str | None):
    """[0182] Jumlah huruf/angka naskah (tanpa spasi & tanda baca) — satuan bicara model durasi.
    SATU sumber: `duration_model.ciri_teks`, supaya angka di sampel identik dengan yang dipakai
    meramal. Gagal apa pun → None (kolom nullable; kalibrasi melewati baris tanpa huruf)."""
    try:
        from src.production.duration_model import ciri_teks
        return int(ciri_teks(text or "")["chars"]) or None
    except Exception:
        return None


def _log_delivery_sample(tenant_config, config: dict, provider_name: str, word_count: int, audio_path: str,
                         script: dict | None = None, target_audio_secs: float | None = None,
                         text: str | None = None, raw_audio_secs: float | None = None,
                         voice_rate: str | None = None) -> None:
    """F4-01: 1 baris per render TTS SUKSES → tts_delivery_samples (delivery NYATA per voice×speed).
    Dipakai F5-01 (kalibrasi pace EWMA → ganti seed P) + verifikasi akurasi P §10.D. Best-effort/fail-soft,
    NOL pengaruh produksi. speed = yg BENAR-BENAR dipakai provider (incl. override LLM §10.A).

    DURASI-F1 (instrumentasi): rekam TAKSIRAN model vs AKTUAL + rincian jeda → error estimator TERUKUR (kalibrasi F2).
      • predicted_secs/pause_secs = dari script["_duration_est"] (diisi script_engine utk run ber-preset; None → NULL)
      • raw_audio_secs            = durasi audio apa adanya (sejak 2026-07-31 = audio_secs; peregangan atempo dihapus)
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
            # [0182] huruf naskah = satuan bicara model durasi per-huruf. Tanpa kolom ini model tak bisa
            # dikalibrasi dari data produksi. Fail-soft: gagal hitung → NULL (baris tetap masuk).
            "chars":      _chars_of(text),
            # [0184] setelan laju NYATA render ini → kalibrasi menolak sampel dari baseline berbeda
            "voice_rate": voice_rate,
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
        Generate audio dari script. Suara TIDAK PERNAH dimodifikasi demi durasi (owner 2026-07-29):
        tak ada modulasi pace, tak ada peregangan audio. Durasi ditentukan di HULU oleh jumlah kata +
        jumlah kalimat (`duration_model`), dan gerbang pipeline yang memutuskan bila tetap meleset.

        target_audio_secs / overhead_secs: dipakai untuk PELAPORAN & sampel kalibrasi saja — selisih
        di atas 2 dtk dicatat sebagai peringatan, TIDAK dikoreksi. (Dulu keduanya memberi window
        koreksi atempo; itu dihapus 2026-07-31.)
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
        # ⛔ KECEPATAN SUARA BUKAN TUAS DURASI (keputusan owner 2026-07-29; ditegakkan 2026-07-31).
        # DULU: `script.tts_params.speed` hasil solver §10.A disuntik ke tts_voice_settings → pace suara
        # dimodulasi demi mengejar preset. Terukur dari 59 render produksi terbaru: 41% mentok di batas
        # paling lambat (0,70) dan NOL render berjalan di kecepatan normal — median 0,81. Artinya lebih
        # dari separuh video dibacakan ~20% lebih lambat dari semestinya, DAN durasinya tetap meleset
        # (median −4,7 dtk dari target). Mood narasi = barang yang produk ini jual; membakarnya untuk
        # durasi adalah tukar-tambah yang salah, dan ternyata tidak menghasilkan durasi juga.
        # SEKARANG: durasi ditentukan di HULU oleh jumlah kata + jumlah kalimat (duration_model), dan
        # suara selalu memakai baseline voice-nya sendiri (voice_catalog.default_settings). Bila naskah
        # masih membawa `tts_params.speed` (mis. dari model), nilainya DIABAIKAN — bukan diterapkan.
        if isinstance(script.get("tts_params"), dict) and script["tts_params"].get("speed") is not None:
            logger.info(f"[TTSEngine] speed dari naskah ({script['tts_params'].get('speed')}) DIABAIKAN — "
                        f"kecepatan suara bukan tuas durasi; pakai baseline voice")
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
            audio_path, word_timestamps, _vrate = _run_provider(primary, text, config, output_dir)

            if audio_path and os.path.exists(audio_path):
                self.last_provider = primary           # transparansi pipeline (§4b)
                self.last_fallback_used = False         # no-fallback → selalu False
                size_kb    = os.path.getsize(audio_path) / 1024
                ts_count   = len(word_timestamps)
                ts_quality = "~98% akurasi" if primary == "elevenlabs" else \
                             "tidak tersedia" if primary == "openai_tts" else \
                             "~80% estimasi"
                logger.info(f"[TTSEngine] ✅ {primary}: {size_kb:.1f}KB | {ts_count} word timestamps ({ts_quality})")
                # ⛔ PEREGANGAN AUDIO (atempo) DIHAPUS — lapis kedua tuas kecepatan yang sama-sama
                # dilarang owner. DULU: audio di luar window ±15% di-time-stretch 0,80–1,35× "tanpa biaya
                # TTS". Terukur: 17 dari 140 render produksi audionya diubah setelah selesai, faktor median
                # 0,832 — yaitu memperlambat 17%, di ATAS pelambatan yang sudah terjadi di pace suara.
                # Dua lapis pelambatan bertumpuk pada video yang sama.
                # SEKARANG: audio dipakai apa adanya. Durasi diurus di hulu (jumlah kata + kalimat);
                # bila tetap meleset, gerbang pipeline melaporkannya JUJUR (bukan menutupinya dengan
                # merusak suara). Pengukuran mentah tetap diambil untuk sampel kalibrasi + laporan selisih.
                _raw_secs = TTSEngine.get_duration(audio_path)
                # ── LAPIS 2: AUDIO JAUH LEBIH PENDEK DARI RAMALAN = TIDAK LENGKAP ─────────────────
                # Berlaku untuk SEMUA penyedia suara, bukan cuma Edge. Terbukti nyata 2026-08-01:
                # audio terpotong 13,8 dtk lolos seluruh pipeline karena berkasnya ada, tak kosong,
                # dan durasinya "wajar" — lalu korektor atempo (dulu) meregangkannya agar pas durasi,
                # sehingga narasi yang terputus tersembunyi sempurna dari semua pemeriksaan.
                # Baru bisa dideteksi sejak ada alat ukur yang akurat (~1 dtk): kalau audio jauh lebih
                # pendek daripada yang diramal dari TEKSNYA, yang hilang adalah suaranya, bukan
                # ramalannya. GAGAL JUJUR — video dengan narasi terputus lebih buruk daripada gagal.
                _est = ((script or {}).get("_duration_est") or {}).get("est_seconds")
                if _est and _raw_secs > 0:
                    _rasio = _raw_secs / float(_est)
                    _amb_potong = _ambang.pct("tts_potong_ambang_pct", 75)
                    if _rasio < _amb_potong:
                        _msg = (f"Suara tidak lengkap: audio {_raw_secs:.1f} dtk padahal naskahnya "
                                f"seharusnya ±{float(_est):.1f} dtk ({_rasio:.0%}). Narasi terputus — "
                                f"produksi dihentikan, akan diulang.")
                        logger.error(f"[TTSEngine] {_msg}")
                        self.last_error = _msg
                        self.last_error_class = ErrorClass.TRANSIENT
                        self.last_human_error = ("Suara tidak selesai dibuat sehingga narasinya "
                                                 "terputus. Produksi diulang otomatis.")
                        try:
                            os.remove(audio_path)
                        except OSError:
                            pass
                        return "", []
                    if _rasio < 0.9:
                        logger.warning(f"[TTSEngine] audio {_raw_secs:.1f}s vs ramalan {float(_est):.1f}s "
                                       f"({_rasio:.0%}) — masih di atas ambang, tapi dicatat")
                if target_audio_secs and target_audio_secs > 0:
                    _selisih = _raw_secs - float(target_audio_secs)
                    if abs(_selisih) > 2.0:
                        logger.warning(f"[TTSEngine] audio {_raw_secs:.1f}s vs target {target_audio_secs:.1f}s "
                                       f"(selisih {_selisih:+.1f}s) — TIDAK dikoreksi (suara tak disentuh); "
                                       f"gerbang durasi pipeline yang memutuskan")
                # F4-01 observability: catat delivery NYATA (best-effort) → kalibrasi pace F5-01 + verifikasi P §10.D.
                # DURASI-F1: + taksiran vs aktual + jeda (script["_duration_est"], target, teks) + huruf [0182].
                _log_delivery_sample(tenant_config, config, primary, word_count, audio_path,
                                     script=script, target_audio_secs=target_audio_secs,
                                     text=text, raw_audio_secs=_raw_secs, voice_rate=_vrate)
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

