"""ELIPSIS BUKAN ARTEFAK SAMBUNGAN — pemeriksa tidak boleh menuduh dua kali untuk satu tanda.

Cacat di PEMERIKSANYA sendiri, terukur pada 82 naskah produksi (2026-08-02): pola `\\.\\s*\\.` ikut
cocok DI DALAM "..." dan `[.!?]\\s+[a-z]` cocok pada "you... it's". Akibatnya setiap elipsis dihitung
DUA KALI — sekali sebagai `elipsis` (benar) dan sekali lagi sebagai `artefak_sambungan` dengan alasan
"titik ganda" + "kalimat diawali huruf kecil" (10× dan 5× — semuanya SALAH).

Bukan sekadar laporan yang kotor: temuan itu masuk daftar cacat mekanis yang dikirim ke penulis, jadi
model diminta memperbaiki sisa-penggabungan yang TIDAK PERNAH ADA — memakai putaran perbaikan dan
kuota penyedia untuk mengejar hantu, sementara cacat aslinya (elipsis) tetap di tempatnya.

Sesudah perbaikan, 82 naskah yang sama: elipsis 17× · frasa berulang 9× · kalimat menggantung 7× ·
bahasa asing 1× — dan NOL artefak sambungan palsu.
"""

from src.intelligence.script_checker import periksa_naskah


def _j(t):
    return {x["jenis"] for x in periksa_naskah(t)}


def test_elipsis_tidak_dituduh_artefak_sambungan():
    t = "Tapi tunggu... ini belum selesai. Ada satu hal lagi yang harus kamu tahu sekarang."
    j = _j(t)
    assert "elipsis" in j, "elipsis-nya sendiri malah tak terdeteksi"
    assert "artefak_sambungan" not in j, f"elipsis dituduh sisa penggabungan: {j}"


def test_elipsis_unicode_juga():
    assert "artefak_sambungan" not in _j("Tapi tunggu… ini belum selesai. Ada hal lain yang penting.")


def test_titik_ganda_SUNGGUHAN_tetap_tertangkap():
    assert "artefak_sambungan" in _j("Kota itu hilang.. penyelam menemukan tembok batu di dasar danau.")


def test_huruf_kecil_setelah_titik_tetap_tertangkap():
    assert "artefak_sambungan" in _j("Kota itu hilang. penyelam menemukan tembok batu di dasar danau.")


def test_spasi_ganda_tetap_tertangkap():
    assert "artefak_sambungan" in _j("Kota itu hilang.  Penyelam menemukan tembok batu di dasar danau.")


def test_naskah_bersih_tetap_bersih():
    assert _j("Kota itu hilang. Penyelam menemukan tembok batu di dasar danau.") == set()


def test_penggantian_elipsis_tidak_melahirkan_spasi_ganda_palsu():
    """Kalau elipsis diganti spasi, 'a... b' jadi 'a  b' → tuduhan spasi-ganda palsu."""
    assert "artefak_sambungan" not in _j("Kota itu hilang... penyelam datang mencari jejak yang tersisa.")
