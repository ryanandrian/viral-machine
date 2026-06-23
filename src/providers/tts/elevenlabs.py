"""
ElevenLabs TTS Provider — suara paling natural, berbayar.
Fase 6C s6c8 upgrade:
  - SDK v2.40.0: audio via audio_base_64 (bukan response.audio)
  - Word-level timestamps: gabung char-level → word-level
  - Voice di-resolve di config layer (channels.voice_key, §10.B FINAL); delivery override via tts_voice_settings
"""

import asyncio
import base64
import time
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError

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
                    "word":  cur_word,  # s71e: pertahankan tanda baca untuk smart grouping
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
            "word":  cur_word,  # s71e: pertahankan tanda baca untuk smart grouping
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
        # F1-05: voice sudah ter-resolve di config layer (channels.voice_key → niches.voice_defaults[provider]).
        # Provider pakai apa adanya — NO map hardcode, NO fallback (gagal jujur bila kosong).
        self.voice = config.get("tts_voice")
        if not self.voice:
            raise TTSError(
                "ElevenLabs: voice belum ter-resolve. Set voice di Channel (channels.voice_key, §10.B FINAL)."
            )

        # POINT 1 (no-hardcode): model TTS dari config (channels.tts_model → katalog ai_models component='tts').
        # Sebelumnya `eleven_turbo_v2_5` DIPAKU di generate() → tenant tak bisa pilih model + biaya per-model
        # mustahil. Kini config-driven; default di-resolve di config layer (sort_order katalog). Gagal jujur bila kosong.
        self.model = (config.get("tts_model") or "").strip()
        if not self.model:
            raise TTSError(
                "ElevenLabs: model TTS belum ter-resolve. Set model di Channel (channels.tts_model) "
                "atau pastikan katalog ai_models punya model 'tts' aktif untuk provider 'elevenlabs'."
            )

        self._word_timestamps: list[dict] | None = None

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio + word-level timestamps via ElevenLabs API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from elevenlabs.client import AsyncElevenLabs
        except ImportError:
            raise TTSError("elevenlabs tidak terinstall. Jalankan: python3.11 -m pip install elevenlabs")

        logger.info(f"[ElevenLabs] voice={self.voice} model={self.model} chars={len(text)}")

        try:
            from elevenlabs import VoiceSettings
            client = AsyncElevenLabs(api_key=self.api_key)
            niche  = self.config.get("niche") or ""

            # F1-05 (no-hardcode): baseline delivery = voice_catalog.default_settings (per voice,
            # di-inject config layer); override per-tenant via tts_voice_settings[niche] (mis. ryan speed 0.86).
            baseline      = self.config.get("tts_voice_default_settings", {}) or {}
            tts_vs_config = self.config.get("tts_voice_settings", {}) or {}
            _override     = tts_vs_config.get(niche, {}) if isinstance(tts_vs_config, dict) else {}
            niche_vs      = {**baseline, **_override}
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
                model_id=self.model,
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
