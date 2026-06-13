"""
Hierarki exception terpusat untuk pipeline produksi (Phase 2 — Error Management).

`PipelineError` = base; subclass per-kategori (config/llm/tts/visual/render/publish)
agar error bisa di-handle, di-notify (Telegram), dan dicatat secara TERSTRUKTUR
(kategori + step), bukan `Exception` generik.

Provider error (`LLMError`/`TTSError`/`VisualError`) di-RE-EXPORT dari sini di file
base provider masing-masing → satu sumber kebenaran, semua jadi `PipelineError`
subclass TANPA memutus import lama (`from src.providers.llm.base import LLMError`
tetap jalan). Persist error ke DB = Phase 3 (`pipeline_run_logs`).
"""


class PipelineError(Exception):
    """Base error pipeline terstruktur. Membawa `category` + `step` untuk
    logging/notify/persist. `category` di-set per subclass; `step` opsional per-raise."""

    category: str = "pipeline"

    def __init__(self, message: str = "", *, step: str | None = None, category: str | None = None):
        super().__init__(message)
        self.step = step
        if category:
            self.category = category


class ConfigError(PipelineError):
    """Config tenant tidak valid/tidak lengkap (provider/niche/key/bucket belum diset)."""
    category = "config"


class LLMError(PipelineError):
    """Error pada LLM provider (script/utility/analyzer/rewrite)."""
    category = "llm"


class TTSError(PipelineError):
    """Error pada TTS provider."""
    category = "tts"


class VisualError(PipelineError):
    """Error pada Visual provider (image/video)."""
    category = "visual"


class RenderError(PipelineError):
    """Error saat render/assembly/encode video."""
    category = "render"


class PublishError(PipelineError):
    """Error saat publish ke platform (YouTube/Reels/TikTok)."""
    category = "publish"


__all__ = [
    "PipelineError", "ConfigError", "LLMError", "TTSError",
    "VisualError", "RenderError", "PublishError",
]
