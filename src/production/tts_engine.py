"""
TTS Engine — thin wrapper ke TTS Provider.
v0.2: Return (audio_path, word_timestamps) untuk caption timing akurat.
"""

import asyncio
import os
import time
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig
from src.providers.tts.edge_tts import EdgeTTSProvider, generate_sync

load_dotenv()


class TTSEngine:
    """
    Thin wrapper ke TTS Provider.
    Return: (audio_path, word_timestamps) — timestamps dipakai video_renderer
    untuk caption yang akurat.
    """

    VOICES = {
        "universe_mysteries": {
            "edge_voice":  "en-US-GuyNeural",
            "description": "Deep, authoritative — misteri & sains"
        },
        "fun_facts": {
            "edge_voice":  "en-US-JennyNeural",
            "description": "Energetic, upbeat — fun facts"
        },
        "dark_history": {
            "edge_voice":  "en-US-ChristopherNeural",
            "description": "Dramatic, intense — dark history"
        },
        "ocean_mysteries": {
            "edge_voice":  "en-US-GuyNeural",
            "description": "Deep, mysterious — ocean content"
        },
    }

    def generate(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs"
    ) -> tuple[str, list[dict]]:
        """
        Generate audio dari script.

        Returns:
            Tuple (audio_path, word_timestamps)
            - audio_path: str path ke file MP3
            - word_timestamps: list[{'word': str, 'start': float, 'end': float}]
              Empty list jika provider tidak support timestamps
        """
        # Susun full script text
        full_script = script.get("full_script", "")
        if not full_script:
            parts = [
                script.get("hook", ""),
                script.get("build_up", ""),
                script.get("core_facts", ""),
                script.get("climax", ""),
                script.get("cta", "")
            ]
            full_script = " ".join(p for p in parts if p).strip()

        word_count = len(full_script.split())
        logger.info(f"Generating TTS: {word_count} words")

        # Pilih voice berdasarkan niche
        voice_data = self.VOICES.get(tenant_config.niche, self.VOICES["universe_mysteries"])

        # Override dari tenant_config jika ada
        try:
            from src.config.tenant_config import load_tenant_config
            run_config  = load_tenant_config(tenant_config.tenant_id)
            tts_voice   = run_config.tts_voice
            tts_provider = run_config.tts_provider
        except Exception:
            tts_voice    = voice_data["edge_voice"]
            tts_provider = "edge_tts"

        logger.info(f"Voice: {tts_voice} ({voice_data['description']})")

        config = {
            "tenant_id":    tenant_config.tenant_id,
            "niche":        tenant_config.niche,
            "tts_provider": tts_provider,
            "tts_voice":    tts_voice,
        }

        audio_path, word_timestamps = generate_sync(full_script, config, output_dir)

        if audio_path and os.path.exists(audio_path):
            size_kb = os.path.getsize(audio_path) / 1024
            ts_count = len(word_timestamps)
            logger.info(
                f"Audio generated: {audio_path} "
                f"({size_kb:.1f} KB, {ts_count} word timestamps)"
            )
            return audio_path, word_timestamps

        logger.error("TTS generation failed")
        return "", []

    @staticmethod
    def get_duration(audio_path: str) -> float:
        """Estimasi durasi audio dari file size."""
        try:
            size_bytes = os.path.getsize(audio_path)
            return round((size_bytes * 8) / (128 * 1000), 1)
        except Exception:
            return 0.0
