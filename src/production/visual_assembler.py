"""
Visual Assembler — thin wrapper ke Visual Provider.
v0.2: Delegasi ke PexelsProvider dengan duration filter.
"""

import asyncio
import os
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig
from src.providers.visual.pexels import PexelsProvider

load_dotenv()


class VisualAssembler:
    """Thin wrapper — delegasi ke Visual Provider yang sesuai config."""

    def assemble(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
    ) -> list[str]:
        """
        Download video clips untuk script yang diberikan.
        Returns: List path clip (string) — kompatibel dengan pipeline lama.
        """
        max_clip_mb = self._get_max_clip_mb(tenant_config)

        config = {
            "tenant_id":          tenant_config.tenant_id,
            "niche":              tenant_config.niche,
            "visual_provider":    "pexels",
            "visual_max_clip_mb": max_clip_mb,
            "visual_api_key":     os.getenv("PEXELS_API_KEY", ""),
        }
        provider  = PexelsProvider(config)
        keywords  = provider.extract_keywords_from_script(script, tenant_config.niche)

        logger.info(f"Searching footage: {keywords[:3]}")

        clips_dir = Path(output_dir) / f"clips_{tenant_config.tenant_id}"
        clips     = asyncio.run(
            provider.fetch_clips(keywords=keywords, count=6, output_dir=clips_dir)
        )

        paths = [str(clip.path) for clip in clips]
        logger.info(f"Assembly complete: {len(paths)} clips")
        return paths

    def _get_max_clip_mb(self, tenant_config: TenantConfig, default: int = 150) -> int:
        """Baca max_clip_mb dari Supabase jika tersedia."""
        try:
            from src.config.tenant_config import load_tenant_config
            return load_tenant_config(tenant_config.tenant_id).visual_max_clip_mb
        except Exception:
            return default
