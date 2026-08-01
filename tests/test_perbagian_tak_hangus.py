"""BAGIAN NASKAH YANG SUDAH BERHASIL DITULIS TIDAK BOLEH HANGUS KARENA BAGIAN LAIN GAGAL.

Cacat NYATA yang tertangkap pipeline SUNGGUHAN (BISIK NUSANTARA, 2026-08-02 03:02): jalur
tulis-per-bagian sudah memperpanjang ENAM dari tujuh adegan (76 → 149 kata), lalu adegan ke-7 kena
batas kuota harian Groq — dan SELURUH hasilnya dibuang. Naskah kembali ke 76 kata, gerbang durasi
menolaknya (29 dtk untuk preset 90), produksi berhenti. Lima panggilan model yang sudah dibayar dan
BERHASIL, hangus percuma.

Alasan lama ("struktur naskah harus utuh — bagian yang hilang membuat narasi berhenti tanpa penutup")
benar, tapi melewatkan satu fakta: naskah ASAL sudah punya teks untuk SETIAP adegan aktif — itu
syarat A2 yang dijaga `_validate_and_fix`. Jadi ada pilihan ketiga yang jelas lebih baik: pakai
bagian baru yang berhasil, tambal yang gagal dengan teks ASALNYA.

Ini kelas cacat yang sama dengan "135 kata dibuang karena throttle 8 detik" (RETRO REWIND, 1-Agu) —
kerja yang sudah selesai dibuang karena satu langkah terakhir gagal.
"""

import src.intelligence.script_engine as se
from src.exceptions import ErrorClass, LLMError

_BEATS = ["hook", "core_facts", "cta"]
_ASAL = {"hook": "pembuka asal", "core_facts": "fakta asal", "cta": "penutup asal"}
_RESEP = {"kata_min": 60, "kata_maks": 100, "kata_bidik": 80, "kalimat": 6, "_kalibrasi": {}}


class _ProviderJatuhDiBeatKetiga:
    """Dua bagian pertama berhasil; yang ketiga selalu kena batas kuota (tanpa lama-tunggu wajar)."""

    def __init__(self):
        self.panggil = 0

    def complete(self, **kw):
        self.panggil += 1
        if self.panggil <= 2:
            return '{"text": "kalimat baru yang jauh lebih panjang dan padat isinya untuk adegan ini."}'
        e = LLMError("Rate limit reached for model — please try again in 2h13m.", step="script")
        e.error_class = ErrorClass.RATE_LIMIT
        raise e


def _jalankan(provider, asal):
    return se._generate_per_beat(provider, "model-uji", {"topic": "uji"}, "niche_uji",
                                 _BEATS, _RESEP, None, "id-ID", None, asal=asal)


def test_bagian_gagal_ditambal_teks_asal_bukan_membuang_semuanya():
    hasil = _jalankan(_ProviderJatuhDiBeatKetiga(), _ASAL)
    assert hasil, "seluruh hasil dibuang padahal dua bagian sudah berhasil"
    assert hasil.get("cta") == "penutup asal", "bagian yang gagal tidak ditambal teks asalnya"
    for b in _BEATS:
        assert (hasil.get(b) or "").strip(), f"adegan '{b}' kosong — struktur naskah bolong"
    assert hasil["hook"] != _ASAL["hook"], "bagian yang BERHASIL ditulis ulang malah ikut tertimpa"


def test_naskah_akhir_memuat_semua_bagian():
    hasil = _jalankan(_ProviderJatuhDiBeatKetiga(), _ASAL)
    fs = hasil.get("full_script") or ""
    assert "penutup asal" in fs, "teks tambalan tidak ikut ke naskah akhir"
    assert len(fs.split()) > len(" ".join(_ASAL.values()).split()), (
        "naskah akhir tidak lebih panjang dari asal — kerja yang berhasil tidak terpakai"
    )


def test_tanpa_teks_asal_barulah_menyerah():
    """Kalau naskah asal pun tak punya bagian itu, struktur benar-benar akan bolong → batalkan."""
    hasil = _jalankan(_ProviderJatuhDiBeatKetiga(), {"hook": "a", "core_facts": "b"})   # cta tak ada
    assert hasil == {}, "melanjutkan dengan adegan kosong — narasi akan berhenti tanpa penutup"


def test_error_yang_tak_bisa_ditunggu_juga_ditambal():
    """Kredit habis / kunci ditolak (non-retryable) sama saja: yang sudah jadi jangan dibuang."""
    class _Mati:
        def __init__(self):
            self.panggil = 0

        def complete(self, **kw):
            self.panggil += 1
            if self.panggil <= 2:
                return '{"text": "kalimat baru yang cukup panjang untuk adegan ini sekali jalan."}'
            e = LLMError("insufficient credit", step="script")
            e.error_class = ErrorClass.ACCOUNT_BILLING
            raise e

    hasil = _jalankan(_Mati(), _ASAL)
    assert hasil and hasil.get("cta") == "penutup asal"
