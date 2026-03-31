"""
ElevenLabs TTS Provider — suara paling natural, berbayar.
Fase 6C s6c8 upgrade:
  - SDK v2.40.0: audio via audio_base_64 (bukan response.audio)
  - Word-level timestamps: gabung char-level → word-level
  - Voice per niche dari tts_voice_per_niche di tenant_configs
"""

import asyncio
import base64
import time
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError

# Default voice per niche — override via tenant_configs.tts_voice_per_niche
ELEVENLABS_VOICES = {
    "universe_mysteries": "pNInz6obpgDQGcFmaJgB",  # Adam — deep, authoritative
    "fun_facts":          "21m00Tcm4TlvDq8ikWAM",  # Rachel — energetic
    "dark_history":       "VR6AewLTigWG4xSOukaG",  # Arnold — dramatic
    "ocean_mysteries":    "EXAVITQu4vr4xnSDxMaL",  # Bella — calm, mysterious
}


def _chars_to_words(
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[dict]:
    """
    Konversi character-level timestamps → word-level timestamps.
    Gabungkan karakter non-spasi yang berurutan menjadi satu kata.
    """
    words      = []
    cur_word   = ""
    word_start = None
    word_end   = None

    for char, t_start, t_end in zip(characters, start_times, end_times):
        if char == " " or char == "":
            if cur_word:
                words.append({
                    "word":  cur_word.strip(".,!?;:\"'"),
                    "start": round(word_start, 3),
                    "end":   round(word_end, 3),
                })
                cur_word   = ""
                word_start = None
                word_end   = None
        else:
            if word_start is None:
                word_start = t_start
            cur_word += char
            word_end  = t_end

    # Flush kata terakhir
    if cur_word:
        words.append({
            "word":  cur_word.strip(".,!?;:\"'"),
            "start": round(word_start, 3),
            "end":   round(word_end, 3),
        })

    return [w for w in words if w["word"]]


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS — suara paling natural, word-level timestamps akurat.
    SDK v2.40.0: audio via audio_base_64, alignment via .characters.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        if not self.api_key:
            raise TTSError(
                "ElevenLabs membutuhkan API key. "
                "Set ELEVENLABS_API_KEY di .env atau tts_api_key di tenant_configs."
            )
        niche = config.get("niche", "universe_mysteries")

        # Priority: tts_voice_per_niche → tts_voice → niche default
        voice_per_niche = config.get("tts_voice_per_niche", {})
        if isinstance(voice_per_niche, dict) and niche in voice_per_niche:
            self.voice = voice_per_niche[niche]
            logger.info(f"[ElevenLabs] Voice dari tts_voice_per_niche: {self.voice}")
        elif config.get("tts_voice") and config["tts_voice"] != "en-US-GuyNeural":
            self.voice = config["tts_voice"]
        else:
            self.voice = ELEVENLABS_VOICES.get(niche, ELEVENLABS_VOICES["universe_mysteries"])

        self._word_timestamps: list[dict] | None = None

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio + word-level timestamps via ElevenLabs API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from elevenlabs.client import AsyncElevenLabs
        except ImportError:
            raise TTSError("elevenlabs tidak terinstall. Jalankan: python3.11 -m pip install elevenlabs")

        logger.info(f"[ElevenLabs] voice={self.voice} chars={len(text)}")

        try:
            from elevenlabs import VoiceSettings
            client = AsyncElevenLabs(api_key=self.api_key)
            niche  = self.config.get("niche", "universe_mysteries")

            # Config-driven: baca dari Supabase tts_voice_settings JSONB
            # Fallback ke nilai default jika belum ada di Supabase config
            DEFAULTS = {
                "universe_mysteries": {"speed": 0.87, "style": 0.50, "stability": 0.30, "similarity_boost": 0.75},
                "dark_history":       {"speed": 0.83, "style": 0.55, "stability": 0.28, "similarity_boost": 0.75},
                "ocean_mysteries":    {"speed": 0.86, "style": 0.40, "stability": 0.35, "similarity_boost": 0.75},
                "fun_facts":          {"speed": 0.90, "style": 0.35, "stability": 0.50, "similarity_boost": 0.80},
            }
            tts_vs_config = self.config.get("tts_voice_settings", {}) or {}
            niche_vs      = {**DEFAULTS.get(niche, DEFAULTS["universe_mysteries"]),
                             **tts_vs_config.get(niche, {})}
            voice_settings = VoiceSettings(
                stability        = float(niche_vs.get("stability",        0.30)),
                similarity_boost = float(niche_vs.get("similarity_boost", 0.75)),
                style            = float(niche_vs.get("style",            0.50)),
                speed            = float(niche_vs.get("speed",            0.87)),
            )
            source = "supabase" if tts_vs_config.get(niche) else "default"
            logger.info(
                f"[ElevenLabs] voice_settings [{source}] niche={niche}: "
                f"speed={voice_settings.speed} style={voice_settings.style} "
                f"stability={voice_settings.stability}"
            )
            response = await client.text_to_speech.convert_with_timestamps(
                voice_id=self.voice,
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )

            # Decode audio dari base64 (SDK v2.40.0)
            if not response.audio_base_64:
                raise TTSError("ElevenLabs response: audio_base_64 kosong")

            audio_bytes = base64.b64decode(response.audio_base_64)
            output_path.write_bytes(audio_bytes)

            # Parse word-level timestamps dari character alignment
            al = response.alignment
            if al and al.characters and al.character_start_times_seconds:
                self._word_timestamps = _chars_to_words(
                    al.characters,
                    al.character_start_times_seconds,
                    al.character_end_times_seconds,
                )
                logger.info(
                    f"[ElevenLabs] ✅ {len(self._word_timestamps)} word timestamps "
                    f"(akurasi ~98%)"
                )
            else:
                self._word_timestamps = None
                logger.warning("[ElevenLabs] Alignment tidak tersedia — karaoke tidak akurat")

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
