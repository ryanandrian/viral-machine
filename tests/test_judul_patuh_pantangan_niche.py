"""JUDUL TOPIK WAJIB TUNDUK PADA KOTAK PANTANGAN NICHE — bukan hanya naskahnya.

Ketetapan owner 2026-08-15: *"1 SUNNAH PER KONTEN"* + *"kotak avoid benar-benar ditaati mesin produksi"*.

CACAT YANG DIJAGA — terukur dua kali hari ini:
Pemilih topik membaca aturan niche sebagai SARAN. Niche `sunnah_harian` menyatakan tegas "SATU sunnah
per video, judul dilarang memuat angka", dan aturannya bahkan dipindah ke kalimat PERTAMA deskripsi.
Hasil dua putaran pengukuran: **1 dari 5** lalu **1 dari 5** judul tetap berbunyi *"7 Daily Sunnah
Practices…"*, plus 3 dari 5 memuat lambang ﷺ yang tak bisa dirender font takarir.
⇒ Instruksi saja tidak mengikat. Yang mengikat = penyaring.

BENTUK PERBAIKANNYA (sengaja sekecil mungkin, dan BUKAN selera kita):
judul yang melanggar **kata terlarang milik niche itu sendiri** (`narration_persona.avoid`) dibuang dari
daftar pilihan — memakai pemeriksa harfiah yang SUDAH dipakai untuk naskah (`script_checker`), bukan
aturan baru. Niche tanpa pantangan → nol perubahan. Ini menegakkan aturan PEMILIK NICHE, bukan
membatasi konten tenant (`DESAIN §5b`: selera tidak pernah milik mesin).

GAGAL-LUNAK: bila SEMUA kandidat melanggar, daftar dikembalikan apa adanya + WARNING — produksi tidak
pernah berhenti (prinsip `niche_selector`).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NICHE = {"narration_persona": {"avoid": "tujuh, seven, ﷺ, listicle, polemik mazhab"}}


class TestSaringJudul(unittest.TestCase):
    def test_judul_melanggar_dibuang(self):
        from src.intelligence.niche_selector import saring_judul_terlarang
        topik = [{"topic": "7 Daily Sunnah Practices of Prophet Muhammad ﷺ"},
                 {"topic": "Tujuh Sunnah Harian Rasulullah"},
                 {"topic": "Adab Minum yang Sering Terlewat"}]
        sisa = saring_judul_terlarang(topik, NICHE)
        self.assertEqual([t["topic"] for t in sisa], ["Adab Minum yang Sering Terlewat"])

    def test_lambang_non_latin_ikut_tersaring(self):
        from src.intelligence.niche_selector import saring_judul_terlarang
        sisa = saring_judul_terlarang([{"topic": "Key Teachings of Prophet Muhammad ﷺ"},
                                       {"topic": "Doa Sebelum Tidur"}], NICHE)
        self.assertEqual(len(sisa), 1)

    def test_semua_melanggar_tak_menghentikan_produksi(self):
        """Prinsip `niche_selector`: produksi TIDAK pernah berhenti."""
        from src.intelligence.niche_selector import saring_judul_terlarang
        semua = [{"topic": "Tujuh Sunnah"}, {"topic": "Seven Sunnahs"}]
        self.assertEqual(len(saring_judul_terlarang(semua, NICHE)), 2)

    def test_niche_tanpa_pantangan_tak_berubah(self):
        from src.intelligence.niche_selector import saring_judul_terlarang
        t = [{"topic": "7 Hal Menakjubkan"}]
        self.assertEqual(saring_judul_terlarang(t, {}), t)
        self.assertEqual(saring_judul_terlarang(t, None), t)

    def test_terpasang_di_jalur_pemilihan(self):
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(akar, "src", "intelligence", "niche_selector.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.find("    def select(")
        self.assertIn("saring_judul_terlarang", src[i:i + 6000],
                      "penyaring tidak dipanggil di jalur pemilihan topik")


if __name__ == "__main__":
    unittest.main(verbosity=2)
