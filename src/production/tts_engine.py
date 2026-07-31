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
                         text: str | None = None, raw_audio_secs: float | None = None) -> None:
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
                # ⛔ PEREGANGAN AUDIO (atempo) DIHAPUS — lapis kedua tuas kecepatan yang sama-sama
                # dilarang owner. DULU: audio di luar window ±15% di-time-stretch 0,80–1,35× "tanpa biaya
                # TTS". Terukur: 17 dari 140 render produksi audionya diubah setelah selesai, faktor median
                # 0,832 — yaitu memperlambat 17%, di ATAS pelambatan yang sudah terjadi di pace suara.
                # Dua lapis pelambatan bertumpuk pada video yang sama.
                # SEKARANG: audio dipakai apa adanya. Durasi diurus di hulu (jumlah kata + kalimat);
                # bila tetap meleset, gerbang pipeline melaporkannya JUJUR (bukan menutupinya dengan
                # merusak suara). Pengukuran mentah tetap diambil untuk sampel kalibrasi + laporan selisih.
                _raw_secs = TTSEngine.get_duration(audio_path)
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

