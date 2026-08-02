"""PERBAIKAN NASKAH TIDAK BOLEH DITERIMA HANYA KARENA JUMLAH CACATNYA TURUN.

Cacat yang ditutup 2026-08-02. Aturan penerimaan dulu `len(cacat_baru) < len(cacat_lama)` — murni
JUMLAH. (Variabelnya bahkan bernama `_parah_baru` padahal isinya total; nama yang berbohong itu
sendiri yang membuat cacatnya tak terlihat saat kode dibaca.)

Akibatnya: perbaikan yang membuang DUA cacat RINGAN tetapi MELAHIRKAN SATU cacat PARAH tetap
diterima — 1 < 2. Angka membaik, narasi memburuk. Cacat parah = yang pasti terdengar penonton:
kalimat menggantung, bahasa asing menyelinap, label adegan terbaca narator, narasi tanpa jeda.

Aturan sekarang: cacat PARAH tidak boleh bertambah; kalau jumlah parahnya sama, barulah total jadi
penentu.
"""

import src.intelligence.script_engine as se


def _c(parah: int, ringan: int) -> list:
    return ([{"jenis": "parah", "parah": True}] * parah
            + [{"jenis": "ringan", "parah": False}] * ringan)


def test_menukar_dua_ringan_dengan_satu_PARAH_harus_DITOLAK():
    """Kasus persis yang lolos sebelum perbaikan."""
    assert not se._perbaikan_lebih_baik(_c(0, 2), _c(1, 0)), (
        "perbaikan yang melahirkan cacat PARAH diterima hanya karena jumlahnya turun"
    )


def test_mengurangi_cacat_parah_DITERIMA():
    assert se._perbaikan_lebih_baik(_c(2, 0), _c(1, 0))
    assert se._perbaikan_lebih_baik(_c(1, 3), _c(0, 3))


def test_parah_sama_tapi_ringan_berkurang_DITERIMA():
    assert se._perbaikan_lebih_baik(_c(1, 3), _c(1, 1))


def test_parah_sama_dan_ringan_bertambah_DITOLAK():
    assert not se._perbaikan_lebih_baik(_c(1, 1), _c(1, 3))


def test_tidak_ada_perubahan_DITOLAK():
    assert not se._perbaikan_lebih_baik(_c(1, 2), _c(1, 2))


def test_naskah_bersih_jadi_bercacat_DITOLAK():
    assert not se._perbaikan_lebih_baik([], _c(0, 1))
    assert not se._perbaikan_lebih_baik([], _c(1, 0))


def test_semua_cacat_hilang_DITERIMA():
    assert se._perbaikan_lebih_baik(_c(2, 3), [])


def test_daftar_kosong_atau_none_tidak_meledak():
    assert not se._perbaikan_lebih_baik(None, None)
    assert se._perbaikan_lebih_baik(_c(1, 0), None)


def test_jalur_produksi_memakai_aturan_ini():
    """Penjaga sambungan: aturan tak boleh kembali jadi perbandingan jumlah di dalam `generate`."""
    import inspect
    src = inspect.getsource(se.ScriptEngine.generate)
    assert "_perbaikan_lebih_baik(" in src, "jalur produksi tidak memakai aturan berbasis keparahan"
    assert "_parah_baru < len(_cacat)" not in src, "perbandingan jumlah yang lama masih ada"
