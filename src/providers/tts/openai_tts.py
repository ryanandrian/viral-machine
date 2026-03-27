"""
OpenAI TTS Provider — kualitas sangat baik, berbayar.
Status: AKTIF — tersedia sebagai pilihan di tenant_configs.
Harga: ~$0.015 per 1000 karakter (tts-1), ~$0.030 (tts-1-hd).
Catatan: OpenAI TTS belum support word-level timestamps.

Cara aktifkan via dashboard (nanti):
  tts_provider = 'openai_tts'
  tts_voice    = 'onyx'  (alloy/echo/fable/onyx/nova/shimmer)
  llm_api_key  = dipakai ulang, tidak perlu key terpisah
"""

import asyncio
import os
import time
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError


# Voice OpenAI yang cocok per niche
OPENAI_VOICES = {
    "universe_mysteries": "onyx",    # Deep, authoritative
    "fun_facts":          "nova",    # Upbeat, friendly
    "dark_history":       "fable",   # Dramatic
    "ocean_mysteries":    "onyx",    # Deep
}

OPENAI_MODELS = {
    "standard": "tts-1",     # Lebih cepat, sedikit kurang natural
    "hd":       "tts-1-hd",  # Lebih natural, sedikit lebih lambat
}


class OpenAITTSProvider(TTSProvider):
    """
    OpenAI TTS — kualitas sangat baik, tanpa word timestamps.
    Menggunakan API key yang sama dengan LLM (llm_api_key).
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # Pakai llm_api_key jika tts_api_key tidak ada
        self.api_key = (
            config.get("tts_api_key")
            or config.get("llm_api_key")
            or os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise TTSError(
                "OpenAI TTS membutuhkan API key. "
                "Set llm_api_key di tenant_configs atau OPENAI_API_KEY di .env."
            )
        niche = config.get("niche", "universe_mysteries")
        if not config.get("tts_voice"):
            self.voice = OPENAI_VOICES.get(niche, "onyx")

        self.model = config.get("tts_model", "tts-1")  # standard default

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio via OpenAI TTS API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise TTSError("openai tidak terinstall. Jalankan: pip install openai")

        logger.info(f"[OpenAI TTS] voice={self.voice} model={self.model} chars={len(text)}")

        try:
            client   = AsyncOpenAI(api_key=self.api_key)
            response = await client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="mp3",
            )
            response.stream_to_file(str(output_path))

            size_kb = output_path.stat().st_size / 1024
            logger.info(f"[OpenAI TTS] Generated: {output_path.name} ({size_kb:.1f} KB)")
            return output_path

        except TTSError:
            raise
        except Exception as e:
            raise TTSError(f"OpenAI TTS generation failed: {e}") from e

    def get_word_timestamps(self) -> list[dict] | None:
        # OpenAI TTS belum support word-level timestamps
        # Return None — video_renderer akan fallback ke estimasi
        return None

    @property
    def provider_name(self) -> str:
        return "openai_tts"

    @property
    def supports_word_timestamps(self) -> bool:
        return False
