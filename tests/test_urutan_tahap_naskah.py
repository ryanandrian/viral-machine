"""URUTAN TAHAP PEMBUATAN NASKAH TIDAK BOLEH TERGESER — sistem terpadu, bukan tambalan berurutan.

Tujuh tahap di `ScriptEngine.generate` saling bergantung pada URUTAN, dan salah urut tidak pernah
memunculkan error — ia hanya menghasilkan angka basi atau cacat yang tersembunyi:

  1. resep durasi (+ margin aman)      → sasaran untuk semua tahap sesudahnya
  2. tulis per-bagian                  → dipakai bila satu panggilan tak sanggup
  3. perbaikan panjang (refit)         → merapatkan ke band
  4. periksa ulang naskah AKHIR        → cacat harus dinilai pada teks yang BENAR-BENAR dipakai
  5. perbaikan cacat oleh penulis      → hanya berguna bila (4) sudah menilai teks final
  6. jaring titik penutup              → HARUS sesudah (5): kalau lebih dulu, cacatnya tak pernah
                                          terlihat oleh penulis
  7. SATU perhitungan durasi akhir     → HARUS paling belakang: ia memberi makan penjaga
                                          audio-terpotong & alarm akurasi. Titik yang ditambahkan (6)
                                          menambah satu jeda kalimat — kalau (7) berjalan lebih dulu,
                                          angkanya basi.

Cacat nyata yang lahir dari salah urut (2026-08-01): `_duration_est` dihitung DI DALAM loop attempt,
sehingga menempel pada teks lama — penjaga audio-terpotong membandingkan audio nyata dengan ramalan
naskah yang sudah tidak dipakai.
"""

import inspect

import src.intelligence.script_engine as se

_SRC = inspect.getsource(se.ScriptEngine.generate)

_TAHAP = [
    ("resep durasi + margin aman",       "_margin_penulis(preset_seconds"),
    ("tulis per-bagian (tambal asal)",   "asal=best_script"),
    ("perbaikan panjang (refit)",        "_refit_naskah("),
    ("periksa ulang naskah akhir",       "periksa_naskah as _periksa2"),
    ("perbaikan cacat oleh penulis",     "_perbaikan_lebih_baik(_cacat"),
    ("jaring titik penutup",             "titik penutup dipasang"),
    ("perhitungan durasi akhir",         "SATU PERHITUNGAN AKHIR"),
]


def _posisi():
    return [(nama, _SRC.find(kunci)) for nama, kunci in _TAHAP]


def test_semua_tahap_masih_ada():
    hilang = [n for n, p in _posisi() if p < 0]
    assert not hilang, f"tahap hilang dari jalur pembuatan naskah: {hilang}"


def test_urutan_tahap_tidak_tergeser():
    pos = _posisi()
    urut = [p for _, p in pos]
    assert urut == sorted(urut), (
        "urutan tahap berubah — sistem terpadu, salah urut TIDAK memunculkan error tapi "
        f"menghasilkan angka basi: {[n for n, _ in sorted(pos, key=lambda x: x[1])]}"
    )


def test_titik_penutup_sesudah_penulis_diminta_memperbaiki():
    d = dict(_posisi())
    assert d["perbaikan cacat oleh penulis"] < d["jaring titik penutup"], (
        "titik dipasang sebelum penulis diminta memperbaiki — cacatnya jadi tak terlihat olehnya"
    )


def test_durasi_akhir_dihitung_PALING_BELAKANG():
    d = dict(_posisi())
    for nama, p in _posisi():
        if nama == "perhitungan durasi akhir":
            continue
        assert p < d["perhitungan durasi akhir"], (
            f"'{nama}' berjalan SESUDAH perhitungan durasi akhir — ramalan jadi basi, dan angka basi "
            f"itu yang memberi makan penjaga audio-terpotong serta alarm akurasi"
        )
