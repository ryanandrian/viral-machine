"""
Base class untuk semua Visual Provider.
Setiap provider baru WAJIB inherit class ini dan implement method fetch_clips().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoClip:
    """Representasi satu video clip yang sudah didownload."""
    path: Path
    duration: float        # detik
    width: int
    height: int
    file_size_mb: float
    source_url: str
    provider: str


class VisualProvider(ABC):
    """Abstract base class untuk Visual/Video provider."""

    def __init__(self, config: dict):
        """
        Args:
            config: dict berisi konfigurasi provider dari tenant_configs.
                    Minimal: {'visual_provider': str, 'visual_max_clip_mb': int}
        """
        self.config = config
        self.max_clip_size_mb = config.get("visual_max_clip_mb", 50)
        self.api_key = config.get("visual_api_key")

    @abstractmethod
    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path
    ) -> list[VideoClip]:
        """
        Ambil video clips berdasarkan keywords.

        Args:
            keywords: List kata kunci untuk pencarian visual
            count: Jumlah clips yang dibutuhkan
            output_dir: Direktori untuk menyimpan clips

        Returns:
            List VideoClip yang sudah didownload dan siap dipakai

        Raises:
            VisualError: Jika fetch atau download gagal
        """
        pass

    @abstractmethod
    def extract_keywords_from_script(self, script: str, niche: str) -> list[str]:
        """
        Ekstrak keywords visual dari script narasi.
        Setiap provider bisa punya strategi ekstraksi berbeda.

        Args:
            script: Teks narasi video
            niche: Niche channel (universe_mysteries, dll)

        Returns:
            List keywords yang relevan untuk pencarian visual
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nama unik provider, contoh: 'pexels', 'ai_image:flux-schnell'"""
        pass

    @property
    @abstractmethod
    def is_ai_generated(self) -> bool:
        """True jika visual digenerate oleh AI (bukan stock footage)."""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        True jika provider aktif dan siap dipakai.
        Contoh: ai_video providers return False di v0.2 (DISABLED).
        """
        pass


class VisualError(Exception):
    """Exception untuk error pada Visual provider."""
    pass
