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
import re  # noqa: E402

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
_VISUAL_HUMAN = {
    ErrorClass.ACCOUNT_BILLING: ("Batas tagihan akun penyedia GAMBAR/VIDEO sudah tercapai. Naikkan "
                                 "batas atau perbarui pembayaran di akun penyedia Anda, lalu Jalankan Ulang."),
    ErrorClass.QUOTA_EXHAUSTED: ("Saldo/kredit penyedia GAMBAR/VIDEO sudah habis. Isi ulang saldo di "
                                 "akun penyedia Anda, lalu Jalankan Ulang."),
}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# [2026-08-12] SELURUH TABEL KODE PINDAH ke `src/providers/galat_registry.py` — SATU-SATUNYA tempat
# pemetaan galat penyedia AI (ketok owner: "pastikan tidak ada jalur lain yang menghandle AI error
# management, dan taati gerbang aturan kerja"). Menambah vendor/model = menambah DATA di registry.
# Di berkas ini tinggal: ANJURAN per-golongan (`_VISUAL_HUMAN`, khas komponen GAMBAR/VIDEO) + tiga
# pembungkus tipis di bawah yang TANDA TANGANNYA DIJAGA supaya nol titik panggil ikut berubah.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
_KELUARGA_VISUAL: tuple[str, ...] = ("cloudflare", "openai", "gemini", "fal")


def _kode_cloudflare(payload) -> tuple[int | None, str | None]:
    """Ambil (kode, pesan) dari balasan Cloudflare — bentuknya DAFTAR `{"errors":[{"code":N}]}`,
    bentuk yang penilai lama (dirancang untuk objek) tak pernah bisa membacanya. Dokumen resmi
    memberi KODE-nya, sampel nyata memberi BENTUK-nya; dua-duanya perlu."""
    if isinstance(payload, dict):
        errs = payload.get("errors")
        if isinstance(errs, list) and errs and isinstance(errs[0], dict):
            k, m = errs[0].get("code"), errs[0].get("message")
            try:
                return (int(k) if k is not None else None), (m if isinstance(m, str) else None)
            except (TypeError, ValueError):
                return None, (m if isinstance(m, str) else None)
    return None, None


def classify_cloudflare_error(payload) -> tuple["ErrorClass", str | None, bool]:
    """Balasan Cloudflare Workers AI → (kelas, pesan_penyedia, milik_kita)."""
    from src.providers.galat_registry import golongkan
    kode, pesan = _kode_cloudflare(payload)
    p = golongkan("cloudflare", kode=kode, teks=str(payload), pesan=pesan)
    return p.kelas, pesan, p.milik_kita


def classify_gemini_error(payload) -> tuple["ErrorClass", str | None, bool]:
    """Balasan Gemini → (kelas, pesan_penyedia, milik_kita). Bentuk: `{"error":{...}}`."""
    from src.providers.galat_registry import golongkan
    err = payload.get("error") if isinstance(payload, dict) else None
    err = err if isinstance(err, dict) else {}
    pesan = err.get("message") if isinstance(err.get("message"), str) else None
    kode = next((v for v in (err.get("status"), err.get("code"), err.get("reason"))
                 if isinstance(v, str)), None)
    status = err.get("code") if isinstance(err.get("code"), int) else None
    p = golongkan("gemini", status=status, kode=kode, teks=str(payload), pesan=pesan)
    return p.kelas, pesan, p.milik_kita


def classify_visual_error(exc: Exception) -> tuple["ErrorClass", str | None]:
    """Galat transport visual → (kelas, anjuran). Pembungkus tipis di atas registry tunggal.

    TANDA TANGAN LAMA DIJAGA (dipakai `ai_video` + jalur fal/OpenAI di `ai_image`, dan uji-uji yang
    sudah ada). Pemanggil tak menyebut penyedianya, jadi seluruh keluarga visual dicoba — kode vendor
    bersifat khas sehingga tak saling tabrak; bila tak ada yang cocok, jaring semantik HTTP menangkap.
    Pesan PENYEDIA selalu diutamakan apa adanya (owner 08-Agu: jangan diterjemahkan).
    """
    from src.providers.galat_registry import golongkan
    detail = {}
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        d = body.get("detail") or body.get("error")
        if isinstance(d, dict):
            detail = d
    blob = str(exc)
    kode = str(detail.get("code") or detail.get("status") or "") or None
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status is None:
        m = re.search(r"HTTP (\d{3})|Error code: (\d{3})", blob)
        status = int(m.group(1) or m.group(2)) if m else None
    pesan_penyedia = detail.get("message") if isinstance(detail.get("message"), str) else None

    for nama in _KELUARGA_VISUAL:
        p = golongkan(nama, kode=kode, teks=blob, pesan=pesan_penyedia)
        if p.dasar.startswith(("kode/teks-vendor", "terusan-agregator")):
            return p.kelas, (pesan_penyedia or _VISUAL_HUMAN.get(p.kelas))
    p = golongkan("", status=status, kode=kode, teks=blob, pesan=pesan_penyedia)
    if p.kelas is ErrorClass.UNKNOWN:
        return ErrorClass.UNKNOWN, pesan_penyedia
    return p.kelas, (pesan_penyedia or _VISUAL_HUMAN.get(p.kelas))
