"""Teks layar WAJIB dwibahasa ID/EN — satu bahasa = cacat, item belum selesai.

SSOT: `CLAUDE.md` §3.5 — *"Teks UI/email = dwibahasa ID/EN via mekanisme `Bi` (API kirim KODE, FE
menerjemahkan). Satu bahasa = cacat."*

MASALAH YANG DIJAGA (diukur 2026-08-04)
Keadaan saat ini BERSIH: **67 berkas FE memakai dwibahasa, nol yang pincang** (jumlah `data-id` =
`data-en` di SETIAP berkas), dan **nol** komponen `<Bi id=… />` tanpa `en=`. Tapi seperti temuan-temuan
lain malam ini, kebersihan itu hasil DISIPLIN — **nol uji memeriksanya secara menyeluruh**. Layar
berikutnya bisa lahir satu bahasa, dan yang menemukannya adalah tenant berbahasa Inggris yang melihat
label Indonesia (atau sebaliknya) — bukan kita.

Pola "aturan tertulis tapi tak ditegakkan kode" sudah terbukti berulang di repo ini:
`LIFECYCLE §4.2` · `PROGRAM_BUKTI §6c.1` · `AGENT §5g.9` · `CLAUDE.md §3.3` (kenop).
**Yang tak dijaga mesin akan membusuk.**

BATAS UJI INI (jujur): ia menghitung KESEIMBANGAN `data-id`/`data-en` per berkas dan kelengkapan atribut
`Bi`. Ia menangkap kasus yang PALING SERING terjadi — menambah satu bahasa lalu lupa pasangannya.
Ia TIDAK bisa menilai apakah terjemahannya bermutu; itu tetap mata manusia.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FE = os.path.join(AKAR, "apps", "web", "src")


def _berkas_tsx() -> list[str]:
    return [p for p in glob.glob(os.path.join(FE, "**", "*.tsx"), recursive=True)
            if "node_modules" not in p]


def _rel(p: str) -> str:
    return os.path.relpath(p, AKAR)


class TestDwibahasaSeimbang(unittest.TestCase):

    def test_ada_berkas_untuk_diperiksa(self):
        """Pagar untuk pagar: bila glob rusak, uji di bawah hijau-palsu selamanya."""
        n = len(_berkas_tsx())
        self.assertGreaterEqual(n, 40, f"hanya {n} berkas .tsx ditemukan — pola pencarian rusak")

    def test_jumlah_data_id_sama_dengan_data_en(self):
        """Kasus paling sering: menambah `<span data-id>` lalu lupa pasangan `data-en`.
        Akibatnya label hilang total bagi pembaca bahasa yang lain (CSS menyembunyikan yang tak cocok)."""
        pincang = []
        for p in _berkas_tsx():
            t = open(p, encoding="utf-8", errors="ignore").read()
            a, b = t.count("data-id"), t.count("data-en")
            if a != b:
                pincang.append(f"{_rel(p)} (data-id:{a} data-en:{b})")
        self.assertFalse(pincang,
                         "Dwibahasa PINCANG — satu bahasa akan hilang dari layar (CLAUDE.md §3.5):\n  "
                         + "\n  ".join(pincang))

    def test_komponen_Bi_selalu_membawa_kedua_bahasa(self):
        """`<Bi id="…" />` tanpa `en` = teks Indonesia saja bagi seluruh pengguna EN."""
        cacat = []
        for p in _berkas_tsx():
            t = open(p, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r"<Bi\b[^>]*?/>", t, re.S):
                tag = m.group(0)
                if "id=" in tag and "en=" not in tag:
                    cacat.append(f"{_rel(p)}: {' '.join(tag.split())[:90]}")
                elif "en=" in tag and "id=" not in tag:
                    cacat.append(f"{_rel(p)}: {' '.join(tag.split())[:90]}")
        self.assertFalse(cacat, "Komponen Bi satu bahasa (CLAUDE.md §3.5):\n  " + "\n  ".join(cacat))


class TestMekanismeDwibahasaMasihUtuh(unittest.TestCase):
    """Kalau mekanismenya sendiri hilang/berubah, seluruh uji di atas jadi tak bermakna —
    dan seluruh layar diam-diam berhenti dwibahasa tanpa satu pun uji merah."""

    def test_css_penyembunyi_bahasa_masih_ada(self):
        """Mekanismenya: CSS menyembunyikan bahasa yang tak dipilih. Tanpa aturan itu, KEDUA bahasa
        tampil berdampingan di setiap label — cacat yang langsung terlihat tenant."""
        css = [p for p in glob.glob(os.path.join(FE, "**", "*.css"), recursive=True)
               if "node_modules" not in p]
        gabung = "".join(open(p, encoding="utf-8", errors="ignore").read() for p in css)
        gabung_rapat = re.sub(r"\s+", "", gabung)
        self.assertIn('html[lang="en"][data-id]{display:none', gabung_rapat,
                      "aturan CSS penyembunyi data-id untuk lang=en HILANG — kedua bahasa akan tampil "
                      "bersamaan di seluruh layar")
        self.assertRegex(gabung_rapat, r'\[data-en\]\{display:none',
                         "aturan CSS penyembunyi data-en HILANG")

    def test_komponen_Bi_masih_ada(self):
        ada = glob.glob(os.path.join(FE, "**", "bi.tsx"), recursive=True) + \
            glob.glob(os.path.join(FE, "**", "Bi.tsx"), recursive=True)
        gabung = "".join(open(p, encoding="utf-8", errors="ignore").read()
                         for p in _berkas_tsx()[:400])
        self.assertTrue(ada or "data-id" in gabung,
                        "mekanisme Bi/data-id tak ditemukan sama sekali di FE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
