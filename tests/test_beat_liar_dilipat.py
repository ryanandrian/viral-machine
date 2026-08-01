"""TEKS DI ADEGAN YANG TIDAK DIPAKAI PRESET TIDAK BOLEH JADI YATIM — dan tidak boleh dibuang.

Cacat yang ditutup 2026-08-02. Skema JSON meminta SEMBILAN kunci narasi, prompt lalu berkata
"kosongkan yang tidak aktif". Model sering tidak menurut. Terukur pada 82 video produksi:
  • 80 kejadian beat TIDAK aktif berisi teks,
  • 22 di antaranya `core_facts_2` (18–32 kata) — kunci yang bahkan TIDAK dikenal katalog beat, dan
    cabang kode yang mengaktifkannya mustahil benar (`_beats_for_preset` menyaring ke beat dikenal).

Teks itu tetap terucap (ada di `full_script`) tetapi tidak dimiliki adegan mana pun, sehingga jatah
kata per-adegan menghitung 127 kata padahal 170 kata terdengar, dan prompt gambar untuk adegan itu
tak tahu ada 32 kata lain yang terdengar saat gambarnya tampil. Lebih buruk lagi: bila model tidak
mengirim `full_script`, perakitan cadangan hanya menyapu beat kanonik → teks `core_facts_2` HILANG
dari narasi sepenuhnya.

Penjaganya harus di KODE, bukan di kalimat permintaan — riset 29-Jul membuktikan memperbaiki susunan
prompt tidak menyelesaikan ketidakpatuhan model.
"""

import src.intelligence.script_engine as se

_AKTIF = ["hook", "mystery_drop", "build_up", "core_facts", "curiosity_bridge", "climax", "cta"]


def _skrip():
    return {"hook": "kota itu hilang", "mystery_drop": "tak ada yang tahu",
            "build_up": "para peneliti mencari", "pattern_interrupt": "tapi tunggu dulu",
            "core_facts": "tembok batu ditemukan",
            "core_facts_2": "dan usianya dua belas ribu tahun",
            "curiosity_bridge": "lalu apa artinya", "climax": "jawabannya mengubah sejarah",
            "cta": "ikuti kisah berikutnya"}


def _jumlah_kata(sc):
    return sum(len((sc.get(k) or "").split()) for k in sc)


def test_nol_kata_dibuang():
    sc = _skrip()
    sebelum = _jumlah_kata(sc)
    se._lipat_beat_liar(sc, _AKTIF)
    assert _jumlah_kata(sc) == sebelum, "ada kata yang hilang saat pelipatan — narasi rusak"


def test_teks_liar_pindah_ke_adegan_SEBELUMNYA():
    """Urutan bicara harus utuh: teks yang terdengar sesudah `build_up` menempel ke `build_up`."""
    sc = _skrip()
    se._lipat_beat_liar(sc, _AKTIF)
    assert sc["pattern_interrupt"] == ""
    assert sc["core_facts_2"] == ""
    assert sc["build_up"] == "para peneliti mencari tapi tunggu dulu"
    assert sc["core_facts"] == "tembok batu ditemukan dan usianya dua belas ribu tahun"


def test_urutan_bicara_tidak_berubah():
    """Gabungan seluruh adegan aktif SESUDAH pelipatan = urutan kata yang sama dengan sebelumnya."""
    sc = _skrip()
    KANON = ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "core_facts_2",
             "curiosity_bridge", "climax", "cta"]
    sebelum = " ".join((sc.get(k) or "").strip() for k in KANON if (sc.get(k) or "").strip())
    se._lipat_beat_liar(sc, _AKTIF)
    sesudah = " ".join((sc.get(k) or "").strip() for k in _AKTIF if (sc.get(k) or "").strip())
    assert sesudah == sebelum, "urutan kata berubah — narasi tersusun ulang, bukan sekadar dibukukan"


def test_teks_liar_sebelum_adegan_aktif_pertama_tidak_hilang():
    """Preset pendek (mis. 8 dtk = core saja): teks di `hook` yang tak aktif tetap harus terbawa."""
    sc = {"hook": "pembuka yang tak diminta", "core_facts": "fakta inti", "cta": ""}
    se._lipat_beat_liar(sc, ["core_facts"])
    assert sc["hook"] == ""
    assert sc["core_facts"] == "pembuka yang tak diminta fakta inti"


def test_naskah_yang_sudah_rapi_tidak_disentuh():
    sc = {"hook": "a b", "core_facts": "c d", "cta": "e f", "pattern_interrupt": ""}
    salinan = dict(sc)
    se._lipat_beat_liar(sc, ["hook", "core_facts", "cta"])
    assert sc == salinan, "naskah rapi ikut diubah — perbaikan tidak boleh punya efek samping"


def test_tanpa_daftar_adegan_aktif_tidak_melakukan_apa_pun():
    """Channel tanpa preset (jalur lama) → jangan menyentuh apa pun."""
    sc = _skrip()
    salinan = dict(sc)
    se._lipat_beat_liar(sc, None)
    assert sc == salinan


def test_kunci_warisan_tak_diminta_lagi_ke_model():
    """`core_facts_2` tak pernah bisa aktif — jangan diminta di skema JSON (itu undangan mengisinya)."""
    import inspect
    sumber = inspect.getsource(se._build_user_prompt)
    assert '"core_facts_2": "exact SECOND' not in sumber, (
        "skema JSON masih meminta core_facts_2 — model akan mengisinya lagi"
    )
