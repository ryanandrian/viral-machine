"""JALUR KEDUA ALAT UKUR JEDA (penanda waktu) HARUS BISA DIJALANKAN — bukan sekadar ada di berkas.

Cacat yang ditutup 2026-08-02: `jeda_dari_timestamp` + `gabung_jeda_timestamp` ditulis khusus untuk
penyedia yang TAK DETERMINISTIK (ElevenLabs `stability` 0,3 — sebaran antar-render menelan selisih
0,2–0,4 dtk yang dicari, jadi pagar MAD menolaknya, sebagaimana seharusnya). Keduanya punya NOL
pemanggil: tidak di `ukur_jeda`, tidak di `scripts/ukur_jeda_suara.py`. Kemampuannya nyata, pintunya
tak pernah dipasang — sehingga 20 suara ElevenLabs/fal tak punya jalan keluar dari angka bawaan,
sementara dokumen menjanjikan dua metode pengukuran.

Yang dijaga di sini:
  1. Tanda yang DITOLAK jalur pertama bisa dilengkapi jalur kedua.
  2. Jalur pertama TIDAK PERNAH ditimpa jalur kedua (ia mengukur durasi audio sungguhan; yang kedua
     mengandalkan laporan penyedia).
  3. Kegagalan jalur kedua tidak senyap — selalu ada catatan yang bisa dibaca operator.
"""

import src.production.pause_probe as pp


def _jarak(none_n=40, comma_n=20, dasar=0.05, biaya=0.30):
    """Kumpulan jarak antar-kata tiruan: `comma_n` jarak ber-koma, `none_n` jarak tanpa tanda."""
    return [{"_jarak": {"none": [dasar] * none_n, "comma": [dasar + biaya] * comma_n,
                        "em_dash": [], "ellipsis": [], "sentence": []}}]


def test_tanda_yang_ditolak_jalur_pertama_dilengkapi_jalur_kedua():
    nilai, metode, catatan = pp._lengkapi_dari_timestamp({}, {}, _jarak())
    assert "sec_per_comma" in nilai, f"koma tak terisi; catatan: {catatan}"
    assert abs(nilai["sec_per_comma"] - 0.30) < 0.01
    assert metode["sec_per_comma"] == "penanda_waktu"
    assert "sec_per_comma" in catatan


def test_jalur_pertama_tidak_pernah_ditimpa():
    """Angka dari pasangan terkontrol wajib bertahan walau jalur kedua punya angka untuk tanda sama."""
    nilai = {"sec_per_comma": 0.396}
    metode = {"sec_per_comma": "pasangan_terkontrol"}
    nilai, metode, catatan = pp._lengkapi_dari_timestamp(nilai, metode, _jarak(biaya=0.30))
    assert nilai["sec_per_comma"] == 0.396, "jalur kedua menimpa hasil jalur pertama"
    assert metode["sec_per_comma"] == "pasangan_terkontrol"


def test_penyedia_tanpa_penanda_waktu_dijelaskan_bukan_didiamkan():
    nilai, metode, catatan = pp._lengkapi_dari_timestamp({}, {}, [])
    assert nilai == {} and metode == {}
    assert "penanda waktu" in catatan.lower()


def test_data_penanda_waktu_kurang_ditolak_dengan_alasan():
    """Di bawah syarat minimum pembanding → TOLAK, dan sebutkan alasannya (jangan menebak)."""
    nilai, metode, catatan = pp._lengkapi_dari_timestamp({}, {}, _jarak(none_n=5, comma_n=20))
    assert nilai == {}, "angka dipasang padahal pembandingnya terlalu sedikit"
    assert "jarak antar-kata" in catatan or "tidak menghasilkan angka sah" in catatan


def test_biaya_tak_terbedakan_dari_jeda_alami_ditolak():
    """Tanda yang 'biayanya' hanya 0,005 dtk = derau, bukan pengukuran."""
    nilai, _m, catatan = pp._lengkapi_dari_timestamp({}, {}, _jarak(biaya=0.005))
    assert "sec_per_comma" not in nilai, f"derau lolos sebagai pengukuran: {nilai}"


def test_jalur_kedua_benar_benar_tersambung_ke_alat_resmi():
    """Penjaga anti-kambuh: fungsi jalur kedua harus PUNYA pemanggil di dalam modul ini.

    Cacat aslinya bukan angkanya salah — melainkan kodenya benar tapi tak pernah dipanggil. Uji
    perilaku tak bisa melihat itu; yang bisa hanya memeriksa sambungannya.
    """
    import inspect
    sumber = inspect.getsource(pp)
    for fn in ("jeda_dari_timestamp", "gabung_jeda_timestamp", "_lengkapi_dari_timestamp"):
        # >1 kemunculan = ada pemakaian selain barisnya sendiri
        assert sumber.count(fn) > 1, f"{fn}() kembali jadi kode mati — tak ada yang memanggilnya"
    assert "_lengkapi_dari_timestamp" in inspect.getsource(pp.ukur_jeda), (
        "alat resmi `ukur_jeda` tidak menyambung ke jalur penanda waktu"
    )
