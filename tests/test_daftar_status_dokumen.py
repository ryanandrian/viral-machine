"""Setiap dokumen WAJIB punya status di daftar tunggal — tak ada lagi dokumen tak berstatus.

SSOT: `SISA_KERJA_GO_LIVE.md` §0b "DAFTAR STATUS SELURUH DOKUMEN".

MASALAH YANG DIJAGA (teguran owner 2026-08-05)
*"Anda tidak pernah tahu dokumen mana yang sudah dikerjakan dan valid, mana yang belum, mana yang
dibatalkan."* **Benar, dan daftar itu tak pernah ada.** Akibatnya setiap sesi baru — termasuk Claude —
MENEBAK dokumen mana yang boleh dipercaya, lalu bekerja di atas dokumen basi. Malam itu terbukti: 3 dari 7
pernyataan tentang batas video/hari BASI, dan `CLAUDE_DESIGN_BRIEF` (kepalanya tampak tak berbahaya)
ternyata memuat spesifikasi layar untuk 3 fitur yang tidak ada di aplikasi.

Uji ini memaksa: **dokumen ke-48 tidak bisa lahir tanpa status.** Bukan agar rapi — agar sesi berikutnya
tidak menebak lagi.

BATAS UJI INI (jujur, agar tak dibaca lebih kuat dari isinya): ia menjaga KELENGKAPAN daftar, bukan
KEBENARAN pengelompokannya. Kelompok 1 (dijaga mesin) terbukti; kelompok 2–6 dibuat dari membaca KEPALA
dokumen, belum seluruh isinya — dan itu dinyatakan terbuka di §0b.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(AKAR, "SISA_KERJA_GO_LIVE.md")


def _blok_daftar() -> str:
    t = open(BACKLOG, encoding="utf-8").read()
    m = re.search(r"## 📚 §0b\. DAFTAR STATUS SELURUH DOKUMEN(.*?)\n## 📸", t, re.S)
    assert m, "§0b DAFTAR STATUS SELURUH DOKUMEN hilang dari SISA_KERJA_GO_LIVE.md"
    return m.group(1)


def _dokumen() -> list[str]:
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(AKAR, "*.md")))


class TestDaftarStatusAdaDanLengkap(unittest.TestCase):

    def test_ada_dokumen_untuk_diperiksa(self):
        """Pagar untuk pagar: glob rusak ⇒ uji di bawah hijau-palsu selamanya."""
        self.assertGreaterEqual(len(_dokumen()), 30, "pemindai dokumen rusak")

    def test_blok_daftar_masih_ada(self):
        blok = _blok_daftar()
        for kel in ("KELOMPOK 1", "KELOMPOK 2", "KELOMPOK 6"):
            self.assertIn(kel, blok, f"{kel} hilang dari §0b — daftar status tak lengkap lagi")

    def test_setiap_dokumen_punya_status(self):
        """Inti aturan. Dokumen tanpa status = sesi berikutnya menebak lagi.

        Dokumen dianggap 'berstatus' bila: namanya disebut di §0b, ATAU ia sendiri berspanduk
        (kelompok 2 disebut sebagai KATEGORI di §0b, bukan satu-satu — jadi spanduk = statusnya)."""
        blok = _blok_daftar()
        BANNER = re.compile(r"USANG|HISTORIS|CLOSED|ARSIP|ARCHIVE|SUPERSEDED|dicabut|BEKU|PENSIUN|BASI|"
                            r"jangan pakai|jangan jadikan|bukan backlog|bukan roadmap|bukan daftar kerja|"
                            r"REFERENSI|KOREKSI MENYELURUH|SELESAI|Cara pakai|DIKOREKSI|SIFAT BERKAS",
                            re.I)
        tanpa_status = []
        for nama in _dokumen():
            if nama in blok:
                continue
            kepala = "\n".join(open(os.path.join(AKAR, nama), encoding="utf-8",
                                    errors="ignore").read().split("\n")[:22])
            if BANNER.search(kepala):
                continue
            tanpa_status.append(nama)
        self.assertFalse(
            tanpa_status,
            "Dokumen TANPA status (tak disebut §0b, tak berspanduk):\n  " + "\n  ".join(tanpa_status)
            + "\nSesi berikutnya akan MENEBAK apakah dokumen ini boleh dipercaya — itu akar kekacauan "
              "yang §0b dibuat untuk menutup. Tambahkan ke §0b (kelompok yang tepat) ATAU beri spanduk "
              "di kepala berkasnya.")

    def test_kelompok_1_persis_dokumen_yang_dijaga_uji(self):
        """Klaim 'boleh dipercaya' HANYA sah bila benar-benar ada ujinya. Bila dokumen didaftarkan di
        kelompok 1 tanpa penjaga, daftar ini berubah jadi janji — dan janji itulah yang selama ini gagal."""
        blok = _blok_daftar()
        m = re.search(r"KELOMPOK 1(.*?)KELOMPOK 2", blok, re.S)
        self.assertIsNotNone(m, "kelompok 1 hilang")
        didaftar = set(re.findall(r"`([A-Za-z0-9_.-]+\.md)`", m.group(1)))
        self.assertGreaterEqual(len(didaftar), 8, "kelompok 1 mencurigakan sedikit — daftar rusak?")

        uji_gabung = ""
        for p in glob.glob(os.path.join(AKAR, "tests", "*.py")):
            uji_gabung += open(p, encoding="utf-8", errors="ignore").read()
        tanpa_penjaga = sorted(d for d in didaftar if d not in uji_gabung)
        self.assertFalse(
            tanpa_penjaga,
            "Dokumen diklaim 'DIJAGA MESIN' di kelompok 1 tapi TIDAK disebut uji mana pun: "
            + str(tanpa_penjaga)
            + "\nItu membuat §0b berbohong pada pembacanya. Pasang penjaganya, atau pindahkan ke "
              "kelompok yang jujur.")

    def test_batas_kejujuran_daftar_tetap_tertulis(self):
        """Bila peringatan 'kelompok 2-6 belum diverifikasi isi' dicabut, pembaca akan menganggap
        seluruh daftar terbukti — padahal hanya kelompok 1 yang terbukti. Itu over-claim yang
        persis dilarang CLAUDE.md §4.2."""
        blok = _blok_daftar()
        self.assertRegex(blok, r"BATAS KEJUJURAN",
                         "peringatan batas kejujuran hilang dari §0b")
        self.assertRegex(blok, r"belum diverifikasi isi",
                         "pernyataan 'kelompok 2-6 belum diverifikasi isi' hilang — daftar jadi over-claim")


if __name__ == "__main__":
    unittest.main(verbosity=2)
