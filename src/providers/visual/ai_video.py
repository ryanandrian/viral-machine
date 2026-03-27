"""
AI Video Generation Provider — DISABLED di v0.2.
Arsitektur sudah siap, diaktifkan di versi mendatang.

Provider yang akan didukung:
  - runway-gen3  (~$0.05-0.10/detik, ~3 menit/clip)
  - kling        (~$0.14/clip 5 detik, ~2 menit/clip)
  - luma         (~$0.02/detik, ~1 menit/clip)

Alasan DISABLED v0.2:
  - Biaya: 6 clips × 5 detik × $0.05 = $1.50/video
  - Waktu: 6 clips × 3 menit = 18 menit → pipeline dari 378s → 1500s+
  - Belum viable untuk pipeline otomatis harian
  - Akan diaktifkan ketika ada plan premium atau on-demand generation
"""

from pathlib import Path

from loguru import logger

from src.providers.visual.base import VisualProvider, VideoClip, VisualError


class AIVideoProvider(VisualProvider):
    """
    AI Video Generation — DISABLED v0.2.
    Raise VisualError jika diinisialisasi agar pipeline tidak diam-diam gagal.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        provider_str = config.get("visual_provider", "")
        parts        = provider_str.split(":", 1)
        self.ai_model = parts[1] if len(parts) > 1 else "unknown"

        # Langsung raise — jangan biarkan pipeline jalan dengan provider disabled
        raise VisualError(
            f"AI Video provider '{self.ai_model}' DISABLED di v0.2. "
            f"Pilih provider lain: 'pexels', 'ai_image:flux-schnell', dll. "
            f"AI Video akan diaktifkan di versi mendatang."
        )

    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path,
    ) -> list[VideoClip]:
        raise VisualError("AI Video provider DISABLED di v0.2.")

    def extract_keywords_from_script(self, script: dict, niche: str) -> list[str]:
        return []

    @property
    def provider_name(self) -> str:
        return f"ai_video:{self.ai_model}"

    @property
    def is_ai_generated(self) -> bool:
        return True

    @property
    def is_enabled(self) -> bool:
        return False  # Selalu False — provider ini disabled
