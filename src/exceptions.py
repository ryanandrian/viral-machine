"""
Hierarki exception terpusat untuk pipeline produksi (Phase 2 — Error Management).

`PipelineError` = base; subclass per-kategori (config/llm/tts/visual/render/publish)
agar error bisa di-handle, di-notify (Telegram), dan dicatat secara TERSTRUKTUR
(kategori + step), bukan `Exception` generik.

Provider error (`LLMError`/`TTSError`/`VisualError`) di-RE-EXPORT dari sini di file
base provider masing-masing → satu sumber kebenaran, semua jadi `PipelineError`
subclass TANPA memutus import lama (`from src.providers.llm.base import LLMError`
tetap jalan). Persist error ke DB = Phase 3 (`pipeline_run_logs`).

[ERROR-MGMT 2026-07-18] Dimensi SEMANTIK error ditambah: `error_class` (ErrorClass) —
ORTOGONAL dengan `category` (category=DI MANA gagal: tts/llm/visual; error_class=KENAP
gagal: billing/quota/rate-limit/…). Adapter tiap transport memetakan kode provider-nya
→ ErrorClass (single source of truth arsitektur = AI_ERROR_MANAGEMENT_ARCHITECTURE.md).
Circuit-breaker berpikir dalam ErrorClass, bukan teks. SPEC = dokumen tsb.
"""

from enum import Enum


class ErrorClass(str, Enum):
    """Klasifikasi SEMANTIK error AI — provider-agnostik. Adapter memetakan kode
    mentah provider ke sini; sistem (circuit-breaker) beraksi atas MAKNA, bukan teks.
    str-Enum → nilai `.value` aman disimpan ke DB (production_runs.error_class) & JSON."""
    ACCOUNT_BILLING = "account_billing"   # pembayaran/langganan gagal → non-retryable
    QUOTA_EXHAUSTED = "quota_exhausted"   # kredit/kuota habis → non-retryable
    AUTH_INVALID    = "auth_invalid"      # kunci/koneksi ditolak-permanen (mis. OAuth invalid_grant) → non-retryable
    RATE_LIMIT      = "rate_limit"        # throttle sesaat (429) → retryable
    TRANSIENT       = "transient"         # jaringan/5xx/timeout → retryable
    UNKNOWN         = "unknown"           # belum dikenali → retryable (DEFAULT AMAN)


# Kelas yang memicu REM SEGERA (rem setelah 1× gagal — hemat biaya retry yang mustahil sembuh).
# Lingkup owner 2026-07-17: "kredit habis / masalah pembayaran". DIPERLUAS 2026-07-18 (ketok owner
# "rem segera, jangan bakar duit tenant", [B11] 3.2): AUTH_INVALID — koneksi YouTube putus permanen
# (OAuth invalid_grant) mustahil sembuh dengan diulang → hentikan produksi/publish channel seketika.
# Menambah/menghapus kelas = ubah SATU set ini.
FAST_FAIL: frozenset = frozenset({
    ErrorClass.ACCOUNT_BILLING, ErrorClass.QUOTA_EXHAUSTED, ErrorClass.AUTH_INVALID,
})


class PipelineError(Exception):
    """Base error pipeline terstruktur. Membawa `category` (di mana) + `step` +
    `error_class` (makna, ERROR-MGMT) + `human_message` (pesan siap-tampil ke manusia,
    dinormalkan tiap adapter). `category` di-set per subclass; sisanya opsional per-raise."""

    category: str = "pipeline"

    def __init__(self, message: str = "", *, step: str | None = None, category: str | None = None,
                 error_class: "ErrorClass" = ErrorClass.UNKNOWN, human_message: str | None = None):
        super().__init__(message)
        self.step = step
        if category:
            self.category = category
        self.error_class = error_class
        self.human_message = human_message


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
    "ErrorClass", "FAST_FAIL",
]
