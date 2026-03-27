"""
ElevenLabs TTS Provider — suara paling natural, berbayar.
Status: AKTIF — tersedia sebagai pilihan di tenant_configs.
Default: TIDAK — user harus secara eksplisit pilih via config.

Cara aktifkan via dashboard (nanti):
  tts_provider = 'elevenlabs'
  tts_voice    = 'voice_id_dari_elevenlabs'
  tts_api_key  = 'sk_xxx...'
"""

import asyncio
import time
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError


# Voice ID populer di ElevenLabs — user bisa override via tts_voice
ELEVENLABS_VOICES = {
    "universe_mysteries": "pNInz6obpgDQGcFmaJgB",  # Adam — deep, authoritative
    "fun_facts":          "EXAVITQu4vr4xnSDxMaL",  # Bella — upbeat
    "dark_history":       "VR6AewLTigWG4xSOukaG",  # Arnold — dramatic
    "ocean_mysteries":    "pNInz6obpgDQGcFmaJgB",  # Adam
}


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS — suara paling natural.
    Butuh API key berbayar dari elevenlabs.io.
    Support word-level timestamps via alignment API.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        if not self.api_key:
            raise TTSError(
                "ElevenLabs membutuhkan API key. "
                "Set tts_api_key di tenant_configs atau .env (ELEVENLABS_API_KEY)."
            )
        niche = config.get("niche", "universe_mysteries")
        if not config.get("tts_voice"):
            self.voice = ELEVENLABS_VOICES.get(niche, ELEVENLABS_VOICES["universe_mysteries"])

        self._word_timestamps: list[dict] | None = None

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio via ElevenLabs API dengan word timestamps."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from elevenlabs.client import AsyncElevenLabs
        except ImportError:
            raise TTSError(
                "elevenlabs tidak terinstall. Jalankan: pip install elevenlabs"
            )

        logger.info(f"[ElevenLabs] voice={self.voice} chars={len(text)}")

        try:
            client = AsyncElevenLabs(api_key=self.api_key)

            # Gunakan with_timestamps endpoint untuk dapat word alignment
            response = await client.text_to_speech.convert_with_timestamps(
                voice_id=self.voice,
                text=text,
                model_id="eleven_turbo_v2_5",  # Paling cepat + murah
                output_format="mp3_44100_128",
            )

            # Tulis audio
            with open(output_path, "wb") as f:
                f.write(response.audio)

            # Parse word timestamps dari alignment data
            if hasattr(response, "alignment") and response.alignment:
                self._word_timestamps = [
                    {
                        "word":  char_data.get("character", ""),
                        "start": round(char_data.get("start_time", 0), 3),
                        "end":   round(char_data.get("end_time", 0), 3),
                    }
                    for char_data in response.alignment.get("character_start_times_seconds", [])
                ]
            else:
                self._word_timestamps = None

            size_kb = output_path.stat().st_size / 1024
            logger.info(f"[ElevenLabs] Generated: {output_path.name} ({size_kb:.1f} KB)")
            return output_path

        except TTSError:
            raise
        except Exception as e:
            raise TTSError(f"ElevenLabs generation failed: {e}") from e

    def get_word_timestamps(self) -> list[dict] | None:
        return self._word_timestamps

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    @property
    def supports_word_timestamps(self) -> bool:
        return True
