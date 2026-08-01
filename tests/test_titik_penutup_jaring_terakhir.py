"""NASKAH TIDAK BOLEH BERAKHIR TANPA TITIK — penonton mendengarnya sebagai kalimat terpotong.

Diukur pada 82 naskah produksi (2026-08-02): `kalimat_menggantung` adalah cacat PARAH yang PALING
SERING lolos — 7 naskah berakhir tanpa tanda baca akhir. Penulis memang diminta memperbaikinya, tapi
bila permintaan itu gagal (kuota habis, jawaban ditolak pagar fakta/panjang), naskah TETAP dipakai —
cacatnya ikut terbawa ke video yang ditonton orang.

Untuk kasus ini perbaikannya deterministik dan tidak menyentuh isi: pasang titik. Nol kata ditambah,
nol kata dibuang, nol panggilan model.

Yang dijaga di sini: (1) titik benar-benar dipasang, (2) beat terakhir ikut ditutup — kalau tidak,
teks beat dan naskah akhir jadi berbeda, dan pemetaan adegan mencocokkan teks beat ke kata audio,
(3) naskah yang sudah rapi tidak disentuh.
"""

import inspect

import src.intelligence.script_engine as se
from src.intelligence.script_checker import periksa_naskah

_SUMBER = inspect.getsource(se.ScriptEngine.generate)


def test_jaring_terakhir_terpasang_di_jalur_generate():
    assert "titik penutup dipasang" in _SUMBER, "jaring terakhir tidak ada di jalur pembuatan naskah"


def test_jaring_berjalan_SETELAH_penulis_diminta_memperbaiki():
    """Urutan penting: jangan menutup titik lebih dulu, itu akan menyembunyikan cacat dari penulis."""
    i_penulis = _SUMBER.find("perbaikan cacat mekanis")
    i_jaring = _SUMBER.find("titik penutup dipasang")
    assert i_penulis != -1 and i_jaring != -1
    assert i_penulis < i_jaring, (
        "titik dipasang SEBELUM penulis diminta memperbaiki — cacat jadi tak terlihat olehnya"
    )


def test_menutup_titik_benar_benar_menghapus_cacatnya():
    teks = "kota itu hilang tanpa jejak. penyelam menemukan tembok batu di dasar danau"
    assert "kalimat_menggantung" in {t["jenis"] for t in periksa_naskah(teks)}
    assert "kalimat_menggantung" not in {t["jenis"] for t in periksa_naskah(teks + ".")}


def test_tanda_akhir_lain_tidak_ikut_ditambahi():
    """Naskah yang berakhir '?' atau '"' sudah sah — jangan ditambahi titik."""
    for akhir in ("Benarkah begitu?", "Ia berkata \"pergilah\"", "Selesai!", "Titik…"):
        assert "kalimat_menggantung" not in {t["jenis"] for t in periksa_naskah("kalimat awal. " + akhir)}
