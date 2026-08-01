"""HTTP 429 dikenali untuk SEMUA penyedia — bukan lewat kalimat khas satu vendor.

Alasan (arahan owner 2026-08-01): katalog model akan terus bertambah dan dipakai banyak tenant. Aturan
yang mengenali kalimat khas satu vendor akan DIAM-DIAM gagal pada vendor berikutnya — tenant-nya
menerima "kesalahan tak dikenal" untuk hal yang sebenarnya cukup ditunggu.

Sejalan dengan SSOT `AI_ERROR_MANAGEMENT_ARCHITECTURE.md`: §1 mendefinisikan RATE_LIMIT sebagai
"throttle sesaat (429)", dan §2 mewajibkan klasifikasi menempel pada TRANSPORT, bukan merek model.
"""

import pytest

from src.exceptions import FAST_FAIL, ErrorClass
from src.providers.llm.adapters import _classify_openai_compat_error as klasifikasi


@pytest.mark.parametrize("pesan", [
    "Error code: 429 - {'error': {'message': 'Rate limit reached ... tokens per day (TPD)'}}",
    "Error code: 429 - too many requests, please slow down",
    "429 Too Many Requests",
])
def test_429_vendor_apa_pun_dikenali_sebagai_batas_laju(pesan):
    kelas, manusiawi = klasifikasi(Exception(pesan))
    assert kelas is ErrorClass.RATE_LIMIT
    assert manusiawi, "429 tanpa pesan manusiawi → tenant membaca teks mentah vendor"


def test_429_dari_ATRIBUT_sdk_juga_dikenali():
    """SDK OpenAI/Groq/Anthropic sama-sama menyediakan status_code — membacanya lebih andal daripada
    menebak dari teks (§6: circuit-breaker tak boleh string-sniffing)."""
    class _E(Exception):
        status_code = 429
    kelas, _ = klasifikasi(_E("pesan vendor yang belum pernah kita lihat"))
    assert kelas is ErrorClass.RATE_LIMIT


def test_batas_laju_TIDAK_mengerem_channel():
    """Kekhawatiran lama 'jangan salah-rem' berlaku untuk QUOTA_EXHAUSTED, bukan RATE_LIMIT.
    Mengerem channel tenant untuk throttle sesaat = produksi berhenti sampai tenant menekan tombol."""
    assert ErrorClass.RATE_LIMIT not in FAST_FAIL
    assert ErrorClass.UNKNOWN not in FAST_FAIL


def test_kredit_habis_TETAP_menang_atas_aturan_429_umum():
    """Urutannya menentukan: 'kredit habis' juga datang sebagai 429 di OpenAI. Bila aturan umum menang,
    channel yang kreditnya habis akan mencoba ulang selamanya tanpa memberi tahu tenant."""
    kelas, _ = klasifikasi(Exception("Error code: 429 - {'type': 'insufficient_quota'}"))
    assert kelas is ErrorClass.QUOTA_EXHAUSTED and kelas in FAST_FAIL


def test_pesan_membedakan_batas_HARIAN_dari_batas_sesaat():
    """Tindakan tenantnya berbeda: yang satu cukup ditunggu, yang lain perlu menaikkan paket.
    Mengatakan 'jatah harian habis' untuk throttle per-menit = tenant menunggu sampai besok sia-sia."""
    _, harian = klasifikasi(Exception("Error code: 429 - tokens per day (TPD) limit reached"))
    _, sesaat = klasifikasi(Exception("Error code: 429 - too many requests"))
    assert "HARIAN" in harian and "HARIAN" not in sesaat


def test_error_lain_tetap_UNKNOWN_aman():
    """§6: hanya yang jelas maknanya dipetakan; ragu → UNKNOWN (retryable, default aman)."""
    kelas, _ = klasifikasi(Exception("Error code: 500 - internal server error"))
    assert kelas is ErrorClass.UNKNOWN
