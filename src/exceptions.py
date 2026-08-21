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
    MODEL_UNAVAILABLE = "model_unavailable"  # model tak tersedia/dipensiunkan vendor (404 model_not_found) → non-retryable [20-Jul, sampel Groq MVT]
    RATE_LIMIT      = "rate_limit"        # throttle sesaat (429) → retryable
    TRANSIENT       = "transient"         # jaringan/5xx/timeout → retryable
    UNKNOWN         = "unknown"           # belum dikenali → retryable (DEFAULT AMAN)


# Kelas yang memicu REM SEGERA (rem setelah 1× gagal — hemat biaya retry yang mustahil sembuh).
# Lingkup owner 2026-07-17: "kredit habis / masalah pembayaran". DIPERLUAS 2026-07-18 (ketok owner
# "rem segera, jangan bakar duit tenant", [B11] 3.2): AUTH_INVALID — koneksi YouTube putus permanen
# (OAuth invalid_grant) mustahil sembuh dengan diulang → hentikan produksi/publish channel seketika.
# Menambah/menghapus kelas = ubah SATU set ini.
# DIPERLUAS 2026-07-20 (ketok owner "kerjakan tawaran 1", sampel nyata insiden MVT): MODEL_UNAVAILABLE —
# model dipensiunkan/tak-ada di vendor mustahil sembuh dengan diulang → berhenti seketika + pesan manusiawi.
FAST_FAIL: frozenset = frozenset({
    ErrorClass.ACCOUNT_BILLING, ErrorClass.QUOTA_EXHAUSTED, ErrorClass.AUTH_INVALID,
    ErrorClass.MODEL_UNAVAILABLE,
})

# Kelas yang PULIH SENDIRI — sebabnya hilang tanpa tenant mengerjakan apa pun (throttle mereda, jaringan
# membaik, jatah harian berganti hari). Lawannya: kelas yang menuntut tindakan (isi ulang kredit, ganti
# kunci, pilih model lain).
#
# Ini pembeda yang paling menentukan bagi tenant, dan dulu TIDAK PERNAH disampaikan: layar & Telegram
# hanya bisa berkata "perbaiki penyebabnya (mis. saldo/kredensial AI)" — tebakan. Akibatnya satu channel
# tenant BERBAYAR mati ±44 jam menunggu sesuatu yang sudah pulih sendiri keesokan harinya.
#
# CATATAN PENTING: "pulih sendiri" TIDAK berarti sistem melepas rem sendiri. Rem tetap dilepas TENANT
# (arahan owner 2026-08-03: "jangan otomatis aktif, tapi UI/UX harus well-informed"). Himpunan ini hanya
# menentukan APA YANG DIKATAKAN kepada mereka: "tunggu, jangan ubah apa pun" vs "ada yang perlu Anda
# kerjakan dulu". SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §1 kolom "Pulih sendiri?" & §9.
SELF_HEALING: frozenset = frozenset({
    ErrorClass.RATE_LIMIT, ErrorClass.TRANSIENT,
})


class PipelineError(Exception):
    """Base error pipeline terstruktur. Membawa `category` (di mana) + `step` +
    `error_class` (makna, ERROR-MGMT) + `human_message` (pesan siap-tampil ke manusia,
    dinormalkan tiap adapter). `category` di-set per subclass; sisanya opsional per-raise."""

    category: str = "pipeline"

    def __init__(self, message: str = "", *, step: str | None = None, category: str | None = None,
                 error_class: "ErrorClass" = ErrorClass.UNKNOWN, human_message: str | None = None,
                 milik_kita: bool = False, dasar: str = "", model: str = ""):
        super().__init__(message)
        self.step = step
        if category:
            self.category = category
        self.error_class = error_class
        self.human_message = human_message
        # [2026-08-11] ASAL-USUL, DITANDAI DI TITIK RAISE — bukan ditebak dari teks di hilir.
        # `milik_kita=True` berarti kegagalan ini milik MesinViral (setelan kurang, permintaan cacat,
        # berkas hilang, FFmpeg), BUKAN milik penyedia AI tenant. Permukaan mana pun HARAM menempeli
        # kalimat "Kegagalan terjadi di layanan AI Anda" pada error ber-`milik_kita=True`.
        # Lahir dari cacat yang dikirim pada commit 0d64f79: asal-usul ditebak dari sebab TERAKHIR,
        # sehingga 75 kegagalan MILIK KITA di worker.log (49 setelan rewrite · 16 berkas tak ada ·
        # 10 FFmpeg) ditimpakan kepada penyedia AI tenant. Dokumen resmi penyedia bahkan menyatakan
        # sendiri kelompok ini (mis. Cloudflare 3003/5004/3006 = permintaan KITA cacat).
        self.milik_kita = milik_kita
        # [2026-08-21] ASAL PUTUSAN + MODEL YANG GAGAL — dibawa keluar, bukan dibuang.
        # `dasar` (galat_registry.Putusan.dasar) membedakan "vendor menyebut modelnya sendiri" dari
        # "404 telanjang dari jaring generik". Tanpa itu, karantina katalog mustahil membedakan
        # kematian model dari alamat yang salah di sisi kita — dan bisa mematikan model yang HIDUP.
        # `model` = model_key yang ditolak; vendor SUDAH menyebutkannya, membuangnya membuat
        # bukti-silang antar-tenant (satu-satunya bukti bebas-biaya) mustahil dihitung.
        self.dasar = dasar
        self.model = model


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
    "ErrorClass", "FAST_FAIL", "SELF_HEALING",
]
