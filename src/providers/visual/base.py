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
