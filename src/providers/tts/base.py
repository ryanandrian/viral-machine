"""
Base class untuk semua TTS Provider.
Setiap provider baru WAJIB inherit class ini dan implement method generate().
"""

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base class untuk Text-to-Speech provider."""

    def __init__(self, config: dict):
        """
        Args:
            config: dict berisi konfigurasi provider dari tenant_configs.
                    Minimal: {'voice': str, 'api_key': str (opsional)}
        """
        self.config = config
        self.voice = config.get("tts_voice", "en-US-GuyNeural")
        self.api_key = config.get("tts_api_key")

    @abstractmethod
    async def generate(self, text: str, output_path: Path) -> Path:
        """
        Generate audio dari teks.

        Args:
            text: Teks yang akan dikonversi ke audio
            output_path: Path file output (.mp3 atau .wav)

        Returns:
            Path file audio yang sudah dibuat

        Raises:
            TTSError: Jika generasi audio gagal
        """
        pass

    @abstractmethod
    def get_word_timestamps(self) -> list[dict] | None:
        """
        Ambil word-level timestamps dari hasil generate terakhir.
        Digunakan untuk subtitle yang akurat.

        Returns:
            List of {'word': str, 'start': float, 'end': float}
            atau None jika provider tidak support
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nama unik provider, contoh: 'edge_tts', 'elevenlabs'"""
        pass

    @property
    @abstractmethod
    def supports_word_timestamps(self) -> bool:
        """True jika provider support word-level timestamps untuk subtitle akurat."""
        pass


class TTSError(Exception):
    """Exception untuk error pada TTS provider."""
    pass
