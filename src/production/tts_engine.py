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

# Concern messages — ditampilkan ke log saat fallback terjadi
CONCERN_MESSAGES = {
    "elevenlabs_to_openai": (
        "⚠️  CONCERN: ElevenLabs gagal → fallback ke OpenAI TTS. "
        "Kualitas suara menurun, word timestamps tidak tersedia. "
        "Cek ELEVENLABS_API_KEY atau status akun di elevenlabs.io"
    ),
    "elevenlabs_to_edge": (
        "⚠️  CONCERN: ElevenLabs gagal → fallback ke Edge TTS (gratis). "
        "Kualitas suara minimal, timestamps estimasi ~80%. "
        "Cek ELEVENLABS_API_KEY atau upgrade akun ElevenLabs."
    ),
    "openai_to_edge": (
        "⚠️  CONCERN: OpenAI TTS gagal → fallback ke Edge TTS (gratis). "
        "Kualitas suara minimal. Cek OPENAI_API_KEY."
    ),
    "all_failed": (
        "❌  CRITICAL: Semua TTS provider gagal. "
        "Cek koneksi internet dan API keys di .env."
    ),
}


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
            "visual_api_key":      getattr(rc, "visual_api_key", "") or "",
            "niche":               tenant_config.niche,
            "tenant_id":           tenant_config.tenant_id,
        }
    except Exception as e:
        logger.warning(f"[TTSEngine] RunConfig load failed ({e}) — pakai defaults")
        return {
            "tts_provider":        "edge_tts",
            "tts_voice":           "en-US-GuyNeural",
            "tts_api_key":         "",
            "tts_voice_per_niche": None,
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
        primary         = config.get("tts_provider", "edge_tts")
        logger.info(f"[TTSEngine] Primary provider: {primary}")

        # Tentukan fallback chain berdasarkan primary provider
        if primary == "elevenlabs":
            chain = ["elevenlabs", "openai_tts", "edge_tts"]
        elif primary == "openai_tts":
            chain = ["openai_tts", "edge_tts"]
        else:
            chain = ["edge_tts"]

        last_error = None
        for i, provider_name in enumerate(chain):
            try:
                if i > 0:
                    # Ini adalah fallback — log concern
                    prev = chain[i-1]
                    concern_key = f"{prev}_to_{provider_name}"
                    concern_msg = CONCERN_MESSAGES.get(
                        concern_key,
                        f"⚠️  CONCERN: {prev} gagal → fallback ke {provider_name}"
                    )
                    logger.warning(concern_msg)

                logger.info(f"[TTSEngine] Trying: {provider_name}")
                audio_path, word_timestamps = _run_provider(
                    provider_name, text, config, output_dir
                )

                if audio_path and os.path.exists(audio_path):
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
        logger.error(CONCERN_MESSAGES["all_failed"])
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
