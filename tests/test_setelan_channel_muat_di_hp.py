"""Kartu "Judul pembuka (hook)" & "Caption (subtitle video)" wajib muat di layar HP.

LAPORAN OWNER 2026-09-02: dibuka dari HP, bagian konfigurasi kedua kartu itu TERPOTONG.

Sebabnya terukur: kedua kartu memakai grid dua kolom **lebar-TETAP** yang ditulis sebagai gaya
SEBARIS (`gridTemplateColumns: "220px 1fr"`). Gaya sebaris kebal media query, jadi di HP selebar
±400px kolom kontrol hanya kebagian ±92px — slider, radio-pill, dan pemilih warna terpotong.
Ironisnya berkas CSS halaman ini SUDAH punya pola bertumpuk (`.cd-grid2` @1000px) yang menganggur.

DUA HAL YANG WAJIB TETAP BENAR saat menumpuk (jangan diperbaiki jadi rusak):
  1. Lebar pratinjau DIKUNCI 220px. Ukuran huruf pratinjau dihitung `font_size * PRV_W/1080` agar
     setara hasil render; melebarkan pratinjau di HP membuat pratinjau BOHONG.
  2. `position: sticky` pada pratinjau harus bisa dibatalkan saat menumpuk — karena itu ia tak
     boleh lagi ditulis sebagai gaya sebaris (sebaris menang atas media query).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"
CSS = "apps/web/src/app/(app)/channels/[id]/channel-detail.css"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """Komentar BARIS dibuang DULU — lihat catatan di test_akun_terhapus_*: urutan terbalik
    pernah menelan 404 baris kode nyata karena `//` yang memuat teks `/*`."""
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestKartuSetelanTakLagiLebarTetap(unittest.TestCase):
    def setUp(self):
        self.layar = _tanpa_komentar(_isi(LAYAR))

    def test_nol_grid_dua_kolom_lebar_tetap_yang_ditulis_sebaris(self):
        """Jangkar cacat: `gridTemplateColumns` sebaris yang memuat satuan px = kebal media query."""
        pelanggar = [
            b for b in re.findall(r"gridTemplateColumns:[^,\n]+", self.layar)
            if "px" in b or "PRV_W" in b
        ]
        self.assertEqual(
            pelanggar, [],
            "grid lebar-TETAP masih ditulis sebaris (kebal media query) → terpotong di HP: "
            + " | ".join(pelanggar),
        )

    def test_kedua_kartu_memakai_kelas_responsif_yang_sama(self):
        """Kartu hook DAN caption — jalur saudara; memperbaiki satu saja = separuh cacat tinggal."""
        for judul in ("Judul pembuka (hook)", "Caption (subtitle video)"):
            with self.subTest(kartu=judul):
                i = self.layar.find(judul)
                self.assertNotEqual(i, -1, f'kartu "{judul}" tak ditemukan — struktur layar berubah')
                blok = self.layar[i : i + 2600]
                self.assertRegex(
                    blok, r'className="cd-prv2"',
                    f'kartu "{judul}" tidak memakai kelas grid responsif `cd-prv2`.',
                )

    def test_sticky_pratinjau_tak_lagi_sebaris(self):
        """Sebaris menang atas media query ⇒ pratinjau tetap menempel & mengunci layar di HP."""
        self.assertNotIn(
            'position: "sticky"', self.layar,
            "position sticky masih ditulis sebaris — tak bisa dibatalkan saat menumpuk di HP.",
        )


class TestSaatMenumpukPratinjauTetapJujur(unittest.TestCase):
    def setUp(self):
        self.css = _isi(CSS)

    def test_ada_media_query_yang_menumpuk_kartu_setelan(self):
        self.assertIn(".cd-prv2", self.css, "kelas .cd-prv2 belum ada di CSS halaman ini.")
        mq = [m for m in re.findall(r"@media[^{]+\{[^@]*?\}\s*\}", self.css, flags=re.S)
              if "cd-prv2" in m]
        self.assertTrue(mq, ".cd-prv2 tidak punya media query — tak akan menumpuk di HP.")
        gabung = "\n".join(mq)
        self.assertRegex(
            gabung.replace(" ", ""), r"grid-template-columns:1fr",
            "media query .cd-prv2 tidak menumpuk jadi satu kolom.",
        )

    def test_lebar_pratinjau_dikunci_saat_menumpuk(self):
        """Skala huruf pratinjau dihitung terhadap 220px (PRV_W). Melebarkannya = pratinjau bohong."""
        mq = [m for m in re.findall(r"@media[^{]+\{[^@]*?\}\s*\}", self.css, flags=re.S)
              if "cd-prv2" in m]
        gabung = "\n".join(mq).replace(" ", "")
        self.assertRegex(
            gabung, r"max-width:220px",
            "saat menumpuk, lebar pratinjau tidak dikunci 220px — skala huruf jadi menyesatkan.",
        )


class TestLebarPratinjauTakBisaBerpisahDiamDiam(unittest.TestCase):
    """Angka 220 hidup di DUA tempat: `PRV_W` (page.tsx, dipakai menghitung skala huruf) dan
    lebar kolom + max-width (CSS). Bila salah satu diubah sendirian, pratinjau tetap tampil
    rapi tapi ukurannya BOHONG — tak ada yang menjerit. Mesin yang menjaga, bukan ingatan."""

    def test_prv_w_di_layar_sama_dengan_lebar_di_css(self):
        layar = _tanpa_komentar(_isi(LAYAR))
        m = re.search(r"const PRV_W\s*=\s*(\d+)", layar)
        self.assertIsNotNone(m, "PRV_W tak ditemukan di layar")
        prv = m.group(1)

        css = _isi(CSS).replace(" ", "")
        self.assertIn(
            f".cd-prv2{{display:grid;grid-template-columns:{prv}px1fr", css.replace("\n", ""),
            f"lebar kolom pratinjau di CSS tak lagi {prv}px — skala huruf pratinjau jadi bohong.",
        )
        mq = [m2 for m2 in re.findall(r"@media[^{]+\{[^@]*?\}\s*\}", _isi(CSS), flags=re.S)
              if "cd-prv2" in m2]
        self.assertRegex(
            "\n".join(mq).replace(" ", ""), rf"max-width:{prv}px",
            f"kunci lebar saat menumpuk tak lagi {prv}px — tak sinkron dengan PRV_W.",
        )


if __name__ == "__main__":
    unittest.main()
