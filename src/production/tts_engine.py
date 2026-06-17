"""
TTS Engine — provider routing + fallback hierarchy.
Fase 6C s6c8:
  - Routing ke provider yang benar dari tenant_configs (tidak lagi hardcode Edge TTS)
  - Fallback hierarchy: ElevenLabs → OpenAI TTS → Edge TTS (last resort)
  - Concern logging setiap fallback — user tahu apa yang terjadi
  - Fix: full_script fallback cover 8 section (bukan 5 section lama)
  - tts_voice_per_niche dari tenant_configs
"""

import asyncio
import os
import time
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig

load_dotenv()

# Concern messages — DINAMIS, nama provider TIDAK ditanam (no-hardcode, QC §0.3).
# Pesan fallback dibangun dari nama provider config (lihat _fallback_concern).
CONCERN_ALL_FAILED = "❌  CRITICAL: Semua penyedia TTS gagal. Cek koneksi & kredensial penyedia suara."


def _fallback_concern(prev_provider: str, next_provider: str) -> str:
    """Pesan concern fallback DINAMIS — nama provider dari config, bukan literal (§0.3)."""
    return (
        f"⚠️  CONCERN: penyedia suara '{prev_provider}' gagal → fallback ke '{next_provider}'. "
        f"Kualitas suara/timestamp dapat menurun & kecepatan bicara berbeda "
        f"(durasi bisa meleset dari target preset). Periksa kredensial/saldo akun '{prev_provider}'."
    )


def _build_full_script(script: dict) -> str:
    """
    Susun full script dari dict.
    Cover 8 section (bukan 5 section lama).
    Priority: full_script field → gabung semua section.
    """
    full = script.get("full_script", "").strip()
    if full:
        return full

    # Fallback: gabung semua 8 section
    sections = [
        "hook", "mystery_drop", "build_up", "pattern_interrupt",
        "core_facts", "curiosity_bridge", "climax", "cta"
    ]
    parts = [script.get(s, "").strip() for s in sections if script.get(s)]
    return " ".join(parts)


def _get_provider_config(tenant_config: TenantConfig) -> dict:
    """Load TenantRunConfig dari Supabase. Return dict config untuk provider.
    Keys dari tenant DB only — tidak ada env fallback (DESIGN.md).
    """
    try:
        from src.config.tenant_config import load_tenant_config
        rc = load_tenant_config(tenant_config.tenant_id)
        return {
            "tts_provider":        rc.tts_provider,
            "tts_voice":           rc.tts_voice,
            "tts_api_key":         rc.tts_api_key or "",
            "tts_voice_per_niche": rc.tts_voice_per_niche,
            "tts_voice_settings":  getattr(rc, "tts_voice_settings", {}) or {},
            "tts_fallback_provider": getattr(rc, "tts_fallback_provider", "edge_tts") or "edge_tts",
            "visual_api_key":      getattr(rc, "visual_api_key", "") or "",
            "niche":               tenant_config.niche,
            "tenant_id":           tenant_config.tenant_id,
        }
    except Exception as e:
        logger.warning(f"[TTSEngine] RunConfig load failed ({e}) — pakai defaults")
        return {
            "tts_provider":        "edge_tts",   # free universal fallback (SOFTCODE §2)
            "tts_voice":           "en-US-GuyNeural",
            "tts_api_key":         "",
            "tts_voice_per_niche": None,
            "tts_fallback_provider": "edge_tts",
            "visual_api_key":      "",
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

    if provider_name == "elevenlabs":
        from src.providers.tts.elevenlabs import ElevenLabsProvider
        provider = ElevenLabsProvider(config)
    elif provider_name == "openai_tts":
        from src.providers.tts.openai_tts import OpenAITTSProvider
        provider = OpenAITTSProvider(config)
    else:
        from src.providers.tts.edge_tts import EdgeTTSProvider
        provider = EdgeTTSProvider(config)

    audio = asyncio.run(provider.generate(text, output_path))
    timestamps = provider.get_word_timestamps() or []
    return str(audio), timestamps


class TTSEngine:
    """
    TTS Engine dengan fallback hierarchy.
    ElevenLabs (best) → OpenAI TTS → Edge TTS (last resort).
    Setiap fallback dicatat sebagai concern untuk user.
    """

    def __init__(self):
        # Transparansi (§4b): dipakai pipeline untuk advisory — provider TERKONFIGURASI
        # vs yang AKTUAL me-render. Di-set ulang tiap generate().
        self.last_primary = None
        self.last_provider = None
        self.last_fallback_used = False
        self.last_concern = ""

    def generate(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
    ) -> tuple[str, list[dict]]:
        """
        Generate audio dari script.
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

        # Load config dari Supabase
        config          = _get_provider_config(tenant_config)
        primary  = config.get("tts_provider") or "edge_tts"
        fallback = config.get("tts_fallback_provider") or "edge_tts"
        logger.info(f"[TTSEngine] Primary: {primary} | fallback: {fallback}")
        # Transparansi (§4b): catat provider terkonfigurasi sejak awal (utk advisory).
        self.last_primary = primary
        self.last_provider = None
        self.last_fallback_used = False

        # Fallback chain CONFIG-DRIVEN (tts_provider + tts_fallback_provider) — BUKAN
        # hardcode. TIDAK ada auto cross-vendor (mis. elevenlabs→openai_tts yang tenant
        # mungkin tak punya keynya); fallback hanya yang diset tenant (default edge_tts =
        # gratis universal). SOFTCODE §2.
        chain = []
        for p in (primary, fallback):
            if p and p not in chain:
                chain.append(p)

        last_error = None
        for i, provider_name in enumerate(chain):
            try:
                if i > 0:
                    # Fallback aktif → concern DINAMIS (no-hardcode nama provider, §0.3)
                    prev = chain[i-1]
                    concern_msg = _fallback_concern(prev, provider_name)
                    logger.warning(concern_msg)
                    self.last_concern = concern_msg

                logger.info(f"[TTSEngine] Trying: {provider_name}")
                audio_path, word_timestamps = _run_provider(
                    provider_name, text, config, output_dir
                )

                if audio_path and os.path.exists(audio_path):
                    # Transparansi (§4b): provider yang BENAR-BENAR me-render + apakah fallback.
                    self.last_provider = provider_name
                    self.last_fallback_used = (provider_name != primary)
                    size_kb    = os.path.getsize(audio_path) / 1024
                    ts_count   = len(word_timestamps)
                    ts_quality = "~98% akurasi" if provider_name == "elevenlabs" else \
                                 "tidak tersedia" if provider_name == "openai_tts" else \
                                 "~80% estimasi"
                    logger.info(
                        f"[TTSEngine] ✅ {provider_name}: {size_kb:.1f}KB "
                        f"| {ts_count} word timestamps ({ts_quality})"
                    )
                    return audio_path, word_timestamps

            except Exception as e:
                last_error = e
                logger.error(f"[TTSEngine] {provider_name} failed: {e}")
                continue

        # Semua gagal
        logger.error(CONCERN_ALL_FAILED)
        logger.error(f"[TTSEngine] Last error: {last_error}")
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
