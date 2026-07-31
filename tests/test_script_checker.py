"""Pemeriksa mutu naskah — mengunci cacat yang PERNAH lolos ke naskah nyata.

Setiap uji di sini punya asal-usul: cacat yang benar-benar muncul di naskah hasil produksi/riset
29–31 Jul 2026. Yang dijaga bukan "kode berjalan", tapi "cacat itu tidak bisa lolos lagi".
"""
from src.intelligence.script_checker import (
    ada_cacat_parah, periksa_naskah, ringkas_temuan,
)

BERSIH = ("Pada tahun 1348, Wabah Hitam membunuh sepertiga penduduk Eropa. "
          "Kota Praha menutup gerbangnya selama empat puluh hari. "
          "Yang tersisa hanya catatan seorang juru tulis bernama Marek.")


def _jenis(temuan):
    return {t["jenis"] for t in temuan}


def test_naskah_bersih_tidak_menghasilkan_temuan():
    assert periksa_naskah(BERSIH, content_language="id-ID") == []
    assert ringkas_temuan([]) == "bersih"


def test_naskah_kosong_ditandai_parah():
    t = periksa_naskah("")
    assert _jenis(t) == {"kosong"} and ada_cacat_parah(t)


def test_kalimat_menggantung_tertangkap():
    """Cacat nyata: naskah berakhir tanpa tanda baca → penonton mendengar kalimat terputus."""
    t = periksa_naskah("Kota itu jatuh pada tahun 1348 dan penduduknya", content_language="id-ID")
    assert "kalimat_menggantung" in _jenis(t)
    assert ada_cacat_parah(t)


def test_elipsis_tertangkap_dengan_jumlahnya():
    """Terukur: satu '...' = >1 detik hening. Sumber kesalahan ramalan durasi terbesar."""
    t = periksa_naskah("Kota itu jatuh... lalu sunyi... selamanya.", content_language="id-ID")
    e = [x for x in t if x["jenis"] == "elipsis"]
    assert e and "2" in e[0]["pesan"]
    assert not e[0]["parah"]          # merusak durasi, tapi bukan cacat yang terdengar rusak


def test_frasa_berulang_tertangkap():
    """Cacat nyata long-form: frasa 'peradaban ini' muncul 8 kali dalam satu naskah 480 detik."""
    teks = ("Peradaban ini runtuh perlahan. " * 4) + "Akhirnya sunyi."
    t = periksa_naskah(teks, content_language="id-ID")
    f = [x for x in t if x["jenis"] == "frasa_berulang"]
    assert f and "peradaban ini" in f[0]["bukti"].lower()


def test_kata_terlarang_dibaca_dari_NICHE_bukan_dari_kode():
    """Aturan datang dari baris niche di DB. Ratusan niche akan datang — nol setelan per-niche di kode."""
    profil = {"narration_persona": {"avoid": "secara magis, klise, tanpa dasar"}}
    t = periksa_naskah("Air itu berubah secara magis menjadi emas.", niche_profile=profil,
                       content_language="id-ID")
    k = [x for x in t if x["jenis"] == "kata_terlarang_niche"]
    assert k and "secara magis" in k[0]["bukti"]
    assert k[0]["parah"]
    # niche lain, aturan lain: teks yang sama BERSIH bila niche-nya tak melarang
    assert "kata_terlarang_niche" not in _jenis(
        periksa_naskah("Air itu berubah secara magis menjadi emas.",
                       niche_profile={"narration_persona": {"avoid": "kata kasar"}},
                       content_language="id-ID"))


def test_tanpa_profil_niche_tidak_mengarang_daftar_terlarang():
    assert "kata_terlarang_niche" not in _jenis(
        periksa_naskah("Air itu berubah secara magis.", niche_profile=None, content_language="id-ID"))


def test_kata_inggris_menyelinap_tertangkap_di_konten_non_inggris():
    """Cacat nyata: kata Inggris menyelinap ke narasi Indonesia."""
    t = periksa_naskah("Kota itu jatuh, and the penduduk melarikan diri.", content_language="id-ID")
    b = [x for x in t if x["jenis"] == "bahasa_asing"]
    assert b and b[0]["parah"]
    assert "and" in b[0]["bukti"]


def test_konten_inggris_tidak_dihukum_karena_berbahasa_inggris():
    assert "bahasa_asing" not in _jenis(
        periksa_naskah("The city fell in 1348 and the people fled.", content_language="en-US"))


def test_label_beat_bocor_tertangkap():
    """Cacat nyata: nama bagian ikut terbaca narator."""
    t = periksa_naskah("hook: Kota itu jatuh pada tahun 1348.", beat_keys=["hook", "core_facts"],
                       content_language="id-ID")
    assert "label_beat_bocor" in _jenis(t) and ada_cacat_parah(t)


def test_artefak_sambungan_per_segmen_tertangkap():
    """Cacat nyata naskah per-bagian: titik ganda & kalimat diawali huruf kecil di sambungan."""
    t = periksa_naskah("Kota itu jatuh. . lalu sunyi selamanya.", content_language="id-ID")
    a = [x for x in t if x["jenis"] == "artefak_sambungan"]
    assert a and not a[0]["parah"]


def test_ringkasan_menyebut_jenis_dan_bukti():
    t = periksa_naskah("Kota itu jatuh... and the penduduk", content_language="id-ID")
    r = ringkas_temuan(t)
    assert "elipsis" in r and "bahasa_asing" in r and "kalimat_menggantung" in r


def test_pemeriksa_tak_pernah_memberi_skor_mutu():
    """Modul ini menjawab 'ada cacat pasti?', BUKAN 'seberapa bagus'. Skor mutu = wewenang lain,
    dan alat skor itu sendiri sedang tidak bisa dipercaya (penanda `estimated`)."""
    import inspect

    import src.intelligence.script_checker as sc
    sumber = inspect.getsource(sc)
    for terlarang in ("viral_score", "def skor", "def score"):
        assert terlarang not in sumber
