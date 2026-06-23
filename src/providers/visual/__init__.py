"""
Registry provider Visual — family dispatch + instansiasi terpusat (mirror providers/llm & providers/tts).

`build_visual_provider(visual_mode, config)` = SATU sumber instansiasi provider visual (ganti instansiasi
inline tersebar di visual_assembler). Family diturunkan dari `visual_mode`:
  • 'ai_image:<m>' → AIImageProvider (model image dari katalog ai_models; transport openai/replicate)
  • 'ai_video:<m>' → AIVideoProvider (video-gen; kini stub/disabled)

Visual v2 = GENERATOR AI saja (stock footage Pexels = fosil v1, dibuang 2026-06-24).
Pemilihan MODEL image/video tetap config-driven via DB (ai_models). Tambah MODEL pada platform yang
ada = baris DB (nol kode); platform transport baru = +1 adaptor (lihat ai_image._TRANSPORTS).
"""

from src.providers.visual.base import VisualProvider, VideoClip, VisualError


def visual_family(visual_mode: str) -> str:
    """Family/strategi perakitan dari visual_mode. Unknown → '' (caller gagal jujur)."""
    vm = (visual_mode or "").strip()
    if vm.startswith("ai_image:"):
        return "ai_image"
    if vm.startswith("ai_video:"):
        return "ai_video"
    return ""


def _registry() -> dict:
    """Registry kelas provider visual per-family. Lazy import (anti-circular)."""
    from src.providers.visual.ai_image import AIImageProvider
    from src.providers.visual.ai_video import AIVideoProvider
    return {"ai_image": AIImageProvider, "ai_video": AIVideoProvider}


def build_visual_provider(visual_mode: str, config: dict) -> VisualProvider:
    """Bangun provider Visual dari visual_mode + config — SATU sumber (ganti instansiasi inline).
    NO silent fallback (selaras §3.8): family tak dikenal → gagal JUJUR (VisualError)."""
    fam = visual_family(visual_mode)
    cls = _registry().get(fam)
    if not cls:
        raise VisualError(
            f"visual_mode '{visual_mode}' tak dikenal. Gunakan 'ai_image:<model>' | 'ai_video:<model>'."
        )
    return cls(config)


__all__ = ["VisualProvider", "VideoClip", "VisualError", "build_visual_provider", "visual_family"]
