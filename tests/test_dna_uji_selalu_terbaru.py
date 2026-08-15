"""UJI NICHE WAJIB MEMAKAI DNA YANG BARU SAJA DISIMPAN — bukan potret 5 menit lalu.

CACAT YANG DIJAGA (`SISA_KERJA [B32]` T5)
Registry niche di mesin bercache **300 detik**. Alurnya tenant: sunting DNA → Simpan → tekan
"Jalankan test". Bila pekerja masih memegang potret lama, video ujinya lahir dari DNA **LAMA** —
dan tenant menyimpulkan "perubahan saya tidak berpengaruh", lalu mengubahnya lagi ke arah yang salah.
Tak ada satu kalimat pun di layar yang memberitahu adanya jeda ini.

Cache itu sendiri BENAR untuk produksi terjadwal (48 niche × tiap run = beban DB sia-sia); yang salah
adalah memakainya pada jalur yang dipicu MANUSIA yang baru saja menekan Simpan.

`invalidate_niches_cache()` sudah ada sejak lama — **dengan NOL pemanggil** (tercatat di komentarnya
sendiri sejak 2-Agu). Mekanisme yang lahir mati. T5 menyambungkannya ke jalur direct-job.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCER = os.path.join(AKAR, "src", "orchestrator", "producer.py")
PANEL_FE = os.path.join(AKAR, "apps", "web", "src", "components", "test-niche-panel.tsx")
EDITOR_FE = os.path.join(AKAR, "apps", "web", "src", "components", "niche-dna-editor.tsx")


class TestJalurUjiMemaksaDnaTerbaru(unittest.TestCase):
    def test_penyegar_ada_dan_benar_benar_mengosongkan_potret(self):
        """Perilaku akhir, bukan keberadaan nama fungsi."""
        import src.intelligence.config as cfg
        from src.orchestrator.producer import segarkan_dna_sebelum_direct

        cfg._NICHES_CACHE = {"palsu": {"name": "potret basi"}}
        cfg._NICHES_TS = 9_999_999_999.0
        segarkan_dna_sebelum_direct()
        self.assertIsNone(cfg._NICHES_CACHE,
                          "potret DNA lama masih dipegang — uji niche akan memakai DNA basi")

    def test_dipanggil_di_jalur_direct(self):
        """Penyegar yang tak dipanggil = mekanisme lahir mati, persis nasib `invalidate_niches_cache`
        selama ini (ditulis 2-Agu, nol pemanggil sampai hari ini)."""
        with open(PRODUCER, encoding="utf-8") as f:
            src = f.read()
        i = src.find("def run_direct(")
        self.assertGreater(i, 0, "run_direct tidak ditemukan")
        badan = src[i:i + 3000]
        self.assertIn("segarkan_dna_sebelum_direct()", badan,
                      "run_direct tidak menyegarkan DNA — tenant menguji DNA lamanya")

    def test_aman_walau_penyegaran_gagal(self):
        """Gagal menyegarkan HARAM menjatuhkan produksi yang seharusnya jalan (§0.6)."""
        import src.intelligence.config as cfg
        from src.orchestrator.producer import segarkan_dna_sebelum_direct
        asli = cfg.invalidate_niches_cache
        try:
            def _meledak():
                raise RuntimeError("DB rewel")
            cfg.invalidate_niches_cache = _meledak
            segarkan_dna_sebelum_direct()   # tidak boleh melempar
        finally:
            cfg.invalidate_niches_cache = asli


class TestLayarMemberiTahuKapanBerlaku(unittest.TestCase):
    """Tenant tidak boleh menebak. §3.6: keterangan ada di TITIK pemakaian, bukan di dokumen."""

    def test_panel_uji_menyebut_dna_terbaru(self):
        with open(PANEL_FE, encoding="utf-8") as f:
            s = f.read()
        self.assertTrue("DNA terbaru" in s or "DNA yang baru" in s,
                        "panel uji tidak menyatakan bahwa yang dipakai adalah DNA terbaru")

    def test_editor_menjelaskan_jeda_produksi_terjadwal(self):
        with open(EDITOR_FE, encoding="utf-8") as f:
            s = f.read()
        self.assertIn("beberapa menit", s,
                      "editor tidak memberi tahu bahwa produksi TERJADWAL baru memakai DNA baru "
                      "setelah beberapa menit")


if __name__ == "__main__":
    unittest.main(verbosity=2)
