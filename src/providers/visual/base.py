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
            config: dict konfigurasi provider. Minimal: {'visual_provider': 'ai_image:<model>',
                    'visual_api_key': str} (visual_provider = visual_mode generator, di-set assembler).
        """
        self.config = config
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
        """Nama unik provider, contoh: 'ai_image:flux-schnell', 'ai_image:gpt-image-1-mini'"""
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
        """
        pass


# VisualError di-RE-EXPORT dari hierarki terpusat (Phase 2) — kini PipelineError subclass.
from src.exceptions import VisualError  # noqa: E402,F401
from src.exceptions import ErrorClass  # noqa: E402


# ── [§8e-B] Classifier transport VISUAL — mengikuti PROSEDUR §5 & POLA `_classify_el_error` ──────
#
# Dibangun mengikuti `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §5 (5 langkah) & §6 (tata-kelola), BUKAN
# rancangan baru: (1) sampel NYATA ditangkap · (2) dicatat di §4 · (3) dipetakan HANYA yang jelas ·
# (4) diimplement di adapter transportnya dgn pola `_classify_el_error` · (5) diuji + commit bersamaan.
#
# BUKTI SAMPEL (wajib per §6 "HANYA kode ber-bukti-sampel yang dipetakan"):
#   • fal 403 — worker.log 2026-07-14 19:54/19:56/19:57 (6 kejadian):
#       {"detail":"User is locked. Reason: Exhausted balance. Top up your balance at
#        fal.ai/dashboard/billing."}
#     → saldo penyedia HABIS ⇒ QUOTA_EXHAUSTED (§1 "kredit/kuota habis").
#   • OpenAI (jalur gambar) — worker.log 2026-07-29 11:32:40, `visual_assembler._generate_hook_frame`:
#       Error code: 400 - {'message':'Billing hard limit has been reached.',
#                          'code':'billing_hard_limit_reached'}
#     → batas TAGIHAN akun tercapai ⇒ ACCOUNT_BILLING (sudah tercatat §4 sejak lahir dokumen).
#
# KENAPA INI BUKAN "KEPUTUSAN PRODUK BARU": kedua kelas SUDAH anggota `FAST_FAIL` sejak ketok owner
# 17-Jul & 18-Jul. §6 menyatakan "menambah/menghapus kelas fast-fail = ubah `FAST_FAIL` saja" — jadi
# memetakan kode penyedia BARU ke kelas yang SUDAH ADA adalah langkah 3 prosedur normal, bukan gerbang
# baru. Arahan owner sendiri: petakan per KELAS, jangan per nama penyedia.
#
# Kode di luar tabel → UNKNOWN (retryable, perilaku lama) = aman. Ragu → JANGAN dipetakan (§5.3).
_VISUAL_ERROR_MAP = {
    "billing_hard_limit_reached": ErrorClass.ACCOUNT_BILLING,
    "Exhausted balance":         ErrorClass.QUOTA_EXHAUSTED,
    "User is locked":            ErrorClass.QUOTA_EXHAUSTED,
}
_VISUAL_HUMAN = {
    ErrorClass.ACCOUNT_BILLING: ("Batas tagihan akun penyedia GAMBAR/VIDEO sudah tercapai. Naikkan "
                                 "batas atau perbarui pembayaran di akun penyedia Anda, lalu Jalankan Ulang."),
    ErrorClass.QUOTA_EXHAUSTED: ("Saldo/kredit penyedia GAMBAR/VIDEO sudah habis. Isi ulang saldo di "
                                 "akun penyedia Anda, lalu Jalankan Ulang."),
}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# PEMETAAN GALAT PER-PENYEDIA — SUMBER: DOKUMENTASI RESMI PENYEDIA (AI_ERROR_MGMT §1 Aturan Emas,
# diperbarui 2026-08-11 atas ketok owner: "setiap error ai pasti ada panduan dari providernya,
# jangan menunggu masalah muncul baru diperbaiki").
#
# ⚠️ PELAJARAN YANG MENGUNCI ATURAN ITU: Cloudflare memakai **HTTP 429 untuk DUA hal berlawanan** —
#    3036 (jatah gratis harian 10.000 neuron HABIS → BERHENTI) vs 3040 (kapasitas penuh SESAAT →
#    ULANGI). Memetakan dari status HTTP saja = menghentikan produksi channel tenant atas dasar
#    yang salah. Sampel tunggal pun tak menyelamatkan: ia hanya menampakkan satu dari dua.
#
# Sumber, dibaca 2026-08-11:
#   • https://developers.cloudflare.com/workers-ai/platform/errors/
#   • https://developers.cloudflare.com/workers-ai/platform/limits/
#   • https://ai.google.dev/gemini-api/docs/api-errors
#   • https://ai.google.dev/gemini-api/docs/troubleshooting
# ═══════════════════════════════════════════════════════════════════════════════════════════════

# Cloudflare Workers AI — kode internal → makna kita.
_CF_ERROR_MAP: dict[int, "ErrorClass"] = {
    3036: ErrorClass.QUOTA_EXHAUSTED,    # 429 · jatah gratis harian 10.000 neuron habis
    3023: ErrorClass.ACCOUNT_BILLING,    # 403 · akun diblokir ("Service unavailable for account")
    5035: ErrorClass.ACCOUNT_BILLING,    # 403 · model ini menuntut Workers PAID plan
    5016: ErrorClass.AUTH_INVALID,       # 403 · tenant belum menyetujui syarat model
    5018: ErrorClass.AUTH_INVALID,       # 403 · akun tak diizinkan untuk model privat
    3041: ErrorClass.AUTH_INVALID,       # 403 · idem 5018
    5007: ErrorClass.MODEL_UNAVAILABLE,  # 400 · "No such model ${model} or task"
    3042: ErrorClass.MODEL_UNAVAILABLE,  # 404 · format/nama model ID tak sah
    3040: ErrorClass.TRANSIENT,          # 429 · kapasitas penuh SESAAT → boleh diulang
    3007: ErrorClass.TRANSIENT,          # 408 · timeout
    3008: ErrorClass.TRANSIENT,          # 408 · aborted
    5005: ErrorClass.MODEL_UNAVAILABLE,  # 405 · model tak mendukung LoRa
}
# Kode yang dokumen Cloudflare sendiri nyatakan sebagai PERMINTAAN KITA yang cacat.
# HARAM ditimpakan ke tenant (lihat `PipelineError.milik_kita`).
_CF_MILIK_KITA: frozenset[int] = frozenset({
    3003,   # 400 · "Request is missing headers or body"
    5004,   # 400 · tipe data base64 tak sah
    3006,   # 413 · payload kebesaran
    5019,   # 405 · versi SDK kedaluwarsa (milik KITA, bukan tenant)
    3039,   # 400 · berkas finetune wajib tak lengkap
})

# Gemini API — status/kode resmi → makna kita. Dipakai jalur GAMBAR Gemini (nol channel memakainya
# per 11-Agu, tapi jalurnya ADA di kode; aturan §5 menuntut dipetakan SEBELUM ada yang menyalakannya).
_GEMINI_ERROR_MAP: dict[str, "ErrorClass"] = {
    "quota_exceeded":      ErrorClass.QUOTA_EXHAUSTED,  # 429 · jatah HARIAN habis → berhenti
    "rate_limit_exceeded": ErrorClass.RATE_LIMIT,       # 429 · batas PER-MENIT → ulangi
    "failed_precondition": ErrorClass.ACCOUNT_BILLING,  # 400 · prasyarat tagihan belum terpenuhi
    "authentication":      ErrorClass.AUTH_INVALID,     # 401 · kunci hilang/salah/kedaluwarsa
    "unauthenticated":     ErrorClass.AUTH_INVALID,     # 401 · nama status gRPC
    "permission_denied":   ErrorClass.AUTH_INVALID,     # 403 · kunci tak berhak
    "model_not_found":     ErrorClass.MODEL_UNAVAILABLE,  # 404
    "not_found":           ErrorClass.MODEL_UNAVAILABLE,  # 404
    "service_unavailable": ErrorClass.TRANSIENT,        # 503
    "unavailable":         ErrorClass.TRANSIENT,        # 503 · nama status gRPC
    "deadline_exceeded":   ErrorClass.TRANSIENT,        # 504
    "api_error":           ErrorClass.TRANSIENT,        # 500
    "internal":            ErrorClass.TRANSIENT,        # 500 · nama status gRPC
    # ⚠️ SENGAJA konservatif: `RESOURCE_EXHAUSTED` menaungi jatah-harian DAN batas-per-menit
    #    sekaligus. Tanpa kode spesifik, kita TIDAK bisa membedakannya → pilih yang boleh diulang,
    #    supaya throttle sesaat tak pernah menghentikan channel tenant secara keliru.
    "resource_exhausted":  ErrorClass.RATE_LIMIT,
}
_GEMINI_MILIK_KITA: frozenset[str] = frozenset({
    "invalid_request", "invalid_argument", "parameter_unknown", "out_of_range",
})


def _kode_cloudflare(payload) -> tuple[int | None, str | None]:
    """Ambil (kode, pesan) dari balasan Cloudflare.

    Bentuknya DAFTAR — `{"errors":[{"code":3036,"message":"…"}], "success":false}` — bentuk yang
    `classify_visual_error` (dirancang untuk balasan berbentuk objek) tak pernah bisa membacanya.
    Itu sebabnya sampel nyata tetap berharga: dokumen memberi KODE, sampel memberi BENTUK.
    """
    if isinstance(payload, dict):
        errs = payload.get("errors")
        if isinstance(errs, list) and errs and isinstance(errs[0], dict):
            k = errs[0].get("code")
            m = errs[0].get("message")
            try:
                return (int(k) if k is not None else None), (m if isinstance(m, str) else None)
            except (TypeError, ValueError):
                return None, (m if isinstance(m, str) else None)
    return None, None


def classify_cloudflare_error(payload) -> tuple["ErrorClass", str | None, bool]:
    """Balasan Cloudflare Workers AI → (kelas, pesan_penyedia, milik_kita).

    Kode di luar tabel resmi → UNKNOWN (retryable) = perilaku lama, aman.
    Pesan yang dipakai adalah pesan PENYEDIA apa adanya — owner 08-Agu: jangan diterjemahkan
    (akan ada ratusan model; pesan aslinya lebih informatif daripada karangan kita).
    """
    kode, pesan = _kode_cloudflare(payload)
    if kode is None:
        return ErrorClass.UNKNOWN, pesan, False
    if kode in _CF_MILIK_KITA:
        return ErrorClass.UNKNOWN, pesan, True
    return _CF_ERROR_MAP.get(kode, ErrorClass.UNKNOWN), pesan, False


def classify_gemini_error(payload) -> tuple["ErrorClass", str | None, bool]:
    """Balasan Gemini → (kelas, pesan_penyedia, milik_kita). Bentuk: `{"error":{...}}`."""
    err = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(err, dict):
        return ErrorClass.UNKNOWN, None, False
    pesan = err.get("message") if isinstance(err.get("message"), str) else None
    for kunci in (err.get("status"), err.get("code"), err.get("reason")):
        if not isinstance(kunci, str):
            continue
        k = kunci.strip().lower()
        if k in _GEMINI_MILIK_KITA:
            return ErrorClass.UNKNOWN, pesan, True
        if k in _GEMINI_ERROR_MAP:
            return _GEMINI_ERROR_MAP[k], pesan, False
    return ErrorClass.UNKNOWN, pesan, False


def classify_visual_error(exc: Exception) -> tuple["ErrorClass", str | None]:
    """Petakan error transport visual → (ErrorClass, human_message). Pola persis `_classify_el_error`:
    body terstruktur BILA ada, else string-scan token PASTI di `str(exc)`.
    Tak cocok → (UNKNOWN, None) = aman, perilaku lama dipertahankan."""
    detail = {}
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        d = body.get("detail") or body.get("error")
        if isinstance(d, dict):
            detail = d
    blob = str(exc)
    kode = str(detail.get("code") or detail.get("status") or "")
    ec = _VISUAL_ERROR_MAP.get(kode)
    if ec is None:
        for tok, cls in _VISUAL_ERROR_MAP.items():
            if tok in blob:
                ec = cls
                break
    if ec is None:
        return ErrorClass.UNKNOWN, None
    pesan_penyedia = detail.get("message") if isinstance(detail.get("message"), str) else None
    return ec, (pesan_penyedia or _VISUAL_HUMAN.get(ec))
