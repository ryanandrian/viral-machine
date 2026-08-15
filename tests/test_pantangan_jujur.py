"""FASILITAS "PANTANGAN" MILIK TENANT HARUS JUJUR SOAL CARA KERJANYA.

Ketetapan owner 2026-08-15 (`SISA_KERJA [B32]`):
    "KITA SUDAH BERIKAN FASILITAS AVOID, TINGGAL KITA PASTIKAN FASILITAS YANG KITA SEDIAKAN ITU
     BERJALAN DENGAN BAIK. YANG KITA BUAT ADALAH TOOLS BUKAN MENGARAHKAN/MEMBATASI KONTEN TENANT."

CACAT YANG DIJAGA — terukur 15-Agu:
Label lama berbunyi *"teks bebas, **dipatuhi mesin apa adanya**"*. Itu janji yang TIDAK BENAR.
`script_checker` mencocokkan **harfiah per-butir**, sehingga:
  • `kadrun`                              → TERTANGKAP, naskah ditolak
  • `kata KADRUN`                         → LOLOS
  • `menggambarkan atau menyuarakan Nabi` → LOLOS
Dari **187 butir pantangan di 48 niche, 79 (42%) berupa kalimat** yang tak akan pernah cocok harfiah
— dan pemilik niche tak punya satu pun cara untuk mengetahuinya.

⚠️ MESINNYA TIDAK DIUBAH. Kalimat panjang TETAP berguna: ia ikut dikirim ke AI penulis sebagai arahan.
Yang diperbaiki adalah **keterangannya** — tenant berhak tahu butir mana yang ditegakkan keras dan mana
yang berupa arahan. Ini memperbaiki ALAT, bukan mengatur isi konten tenant.

⛔ JANGAN "perbaiki" dengan mencocokkan makna (semantik) atau memaksa tenant menulis kata tunggal:
keduanya membuat alat jadi kaku dan mengambil alih keputusan yang menjadi hak tenant.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITOR = os.path.join(AKAR, "apps", "web", "src", "components", "niche-dna-editor.tsx")


class TestPerilakuMesinTakBerubah(unittest.TestCase):
    """Kontrak mesin dikunci apa adanya — supaya perbaikan keterangan tak diam-diam mengubah aturan."""

    def _temuan(self, avoid: str, teks: str):
        from src.intelligence.script_checker import periksa_naskah
        t = periksa_naskah(teks, niche_profile={"narration_persona": {"avoid": avoid}},
                           content_language="id-ID")
        return [x for x in t if x["jenis"] == "kata_terlarang_niche"]

    TEKS = "Banyak orang menyebut mereka KADRUN tanpa alasan. Sikap itu keliru."

    def test_butir_satu_kata_ditegakkan_keras(self):
        self.assertTrue(self._temuan("kadrun", self.TEKS),
                        "butir 1 kata TIDAK ditegakkan — janji 'ditolak harfiah' jadi bohong")

    def test_butir_kalimat_tidak_dicocokkan_harfiah(self):
        self.assertFalse(self._temuan("kata KADRUN yang merendahkan", self.TEKS),
                         "butir kalimat tiba-tiba dicocokkan harfiah — alat jadi kaku, banyak "
                         "naskah SAH akan ditolak (kelas cacat 'keras'→'kekerasan' yang sudah dibayar)")

    def test_pelanggaran_keras_dinilai_parah(self):
        from src.intelligence.script_checker import ada_cacat_parah, periksa_naskah
        t = periksa_naskah(self.TEKS, niche_profile={"narration_persona": {"avoid": "kadrun"}},
                           content_language="id-ID")
        self.assertTrue(ada_cacat_parah(t), "pelanggaran pantangan tak lagi dianggap parah")


class TestLayarJujur(unittest.TestCase):
    def setUp(self):
        with open(EDITOR, encoding="utf-8") as f:
            self.src = f.read()

    def test_janji_palsu_dicabut(self):
        """Yang dijaga = LABEL yang dibaca tenant, bukan komentar kode yang menjelaskan sejarahnya.
        (Uji versi pertama saya salah sasaran: ia menandai komentar penjelasnya sendiri — persis
        kelas 'alat ukur yang salah' pada `test_rute_api_terjaga.py`.)"""
        for baris in self.src.splitlines():
            t = baris.strip()
            if t.startswith("//") or t.startswith("*") or t.startswith("{/*"):
                continue
            self.assertNotIn("dipatuhi mesin apa adanya", t,
                             "label masih menjanjikan 'dipatuhi apa adanya' — 42% butir nyatanya tidak")
            self.assertNotIn("obeyed verbatim", t)

    def test_dua_peran_dijelaskan(self):
        for kunci in ("harfiah", "arahan"):
            self.assertIn(kunci, self.src,
                          f"layar tak menjelaskan peran `{kunci}` — tenant tetap menebak")

    def test_hitungan_per_butir_ditampilkan(self):
        self.assertIn("ditegakkan harfiah", self.src,
                      "tenant tak diberi tahu BERAPA butirnya yang benar-benar ditegakkan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
