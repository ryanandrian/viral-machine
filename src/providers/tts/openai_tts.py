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


# F1-05: OPENAI_VOICES (map niche→voice hardcode) DIHAPUS — voice single-source
# (channels.voice_key → niches.voice_defaults[openai_tts] → voice_catalog).

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
        # Pakai visual_api_key (OpenAI key) — tidak ada env fallback (DESIGN.md)
        self.api_key = (
            config.get("tts_api_key")
            or config.get("visual_api_key")
            or ""
        )
        if not self.api_key:
            raise TTSError(
                "OpenAI TTS membutuhkan API key. "
                "Set tts_api_key atau visual_api_key di tenant_configs Supabase."
            )
        # F1-05: voice ter-resolve di config layer. NO map hardcode/fallback (perbaiki bug:
        # self.voice dulu TAK ter-set bila tts_voice ADA → AttributeError saat generate).
        self.voice = config.get("tts_voice")
        if not self.voice:
            raise TTSError(
                "OpenAI TTS: voice belum ter-resolve. Set voice di Channel (channels.voice_key, §10.B FINAL)."
            )
        self.model = config.get("tts_model") or "tts-1"  # standard default

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio via OpenAI TTS API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise TTSError("openai tidak terinstall. Jalankan: pip install openai")

        # Durasi-via-speed (Pilihan A, multi-provider): terapkan kecepatan terpecahkan gate/LLM.
        # Sumber = {baseline voice_catalog.default_settings} ⊕ {override tts_voice_settings[niche]}
        # (gate menyuntik speed ter-solve ke override saat runtime) — POLA SAMA elevenlabs (no-hardcode).
        # S=1.0 (default) ⇒ perilaku lama (OpenAI default) = nol regresi. Clamp ke rentang API OpenAI.
        niche     = self.config.get("niche") or ""
        baseline  = self.config.get("tts_voice_default_settings", {}) or {}
        vs_cfg    = self.config.get("tts_voice_settings", {}) or {}
        override  = vs_cfg.get(niche, {}) if isinstance(vs_cfg, dict) else {}
        speed     = float({**baseline, **override}.get("speed", 1.0) or 1.0)
        speed     = round(min(4.0, max(0.25, speed)), 3)   # rentang API OpenAI TTS
        logger.info(f"[OpenAI TTS] voice={self.voice} model={self.model} speed={speed} chars={len(text)}")

        try:
            client   = AsyncOpenAI(api_key=self.api_key)
            response = await client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="mp3",
                speed=speed,
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
