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
    """PERUBAHAN KEBENARAN 02-Sep (ketokan owner): dulu lebar pratinjau DIKUNCI 220px saat
    menumpuk, karena ukuran huruf dihitung `font_size * PRV_W/1080` di JavaScript — melebarkan
    kanvas membuat pratinjau bohong. Owner minta pratinjau HP **selebar ruang yang ada**, tinggi
    mengikuti rasio. Penguncian itu digantikan yang lebih benar: kanvas jadi WADAH PENGUKUR
    (`container-type: inline-size`) dan seluruh ukuran ditulis relatif `100cqw/1080` ⇒ sebanding
    hasil render pada lebar BERAPA PUN, jadi tak ada lagi yang perlu dikunci."""

    def setUp(self):
        self.css = _isi(CSS)
        self.layar = _tanpa_komentar(_isi(LAYAR))

    def test_ada_media_query_yang_menumpuk_kartu_setelan(self):
        self.assertIn(".cd-prv2", self.css, "kelas .cd-prv2 belum ada di CSS halaman ini.")
        mq = [m for m in re.findall(r"@media[^{]+\{[^@]*?\}\s*\}", self.css, flags=re.S)
              if "cd-prv2" in m]
        self.assertTrue(mq, ".cd-prv2 tidak punya media query — tak akan menumpuk di HP.")
        self.assertRegex(
            "\n".join(mq).replace(" ", ""), r"grid-template-columns:1fr",
            "media query .cd-prv2 tidak menumpuk jadi satu kolom.",
        )

    def test_pratinjau_hp_tidak_lagi_dikunci_sempit(self):
        """Permintaan owner: di HP pratinjau selebar ruang, tinggi ikut rasio."""
        mq = "\n".join(m for m in re.findall(r"@media[^{]+\{[^@]*?\}\s*\}", self.css, flags=re.S)
                       if "cd-prv2" in m).replace(" ", "")
        self.assertNotRegex(
            mq, r"\.cd-prv2>\.cd-prv\{[^}]*max-width",
            "pratinjau HP masih dikunci lebarnya — owner meminta selebar ruang yang ada.",
        )

    def test_kanvas_pratinjau_adalah_wadah_pengukur(self):
        css = self.css.replace(" ", "")
        self.assertRegex(
            css, r"\.cd-prv-canvas\{[^}]*container-type:inline-size",
            "kanvas pratinjau bukan wadah pengukur — ukuran di dalamnya tak bisa proporsional.",
        )
        self.assertRegex(
            css, r"\.cd-prv-canvas\{[^}]*aspect-ratio:9/16",
            "kanvas pratinjau kehilangan rasio 9:16 — tinggi tak lagi mengikuti lebar.",
        )

    def test_nol_ukuran_yang_dihitung_dari_lebar_tetap(self):
        """`PRV_W/1080` di JavaScript = ukuran dipaku ke satu lebar; begitu kanvas melebar di HP,
        pratinjau langsung bohong. Semua harus lewat cqw."""
        sisa = re.findall(r"PRV_W\s*/\s*1080", self.layar)
        self.assertEqual(
            sisa, [],
            f"masih ada {len(sisa)} perhitungan berbasis lebar tetap (PRV_W/1080) — "
            "pratinjau akan bohong saat melebar di HP.",
        )

    def test_garis_tepi_ikut_diskalakan_agar_tak_blur(self):
        """AKAR BLUR (terukur): huruf & offset bayangan diskalakan, `outline` dipakai MENTAH —
        halo 4px mengelilingi huruf 11,8px di kanvas 220px (4,9x terlalu tebal)."""
        for baris in re.findall(r"textShadow:[^\n]+", self.layar):
            with self.subTest(baris=baris[:60]):
                self.assertNotRegex(
                    baris, r"[a-zA-Z]*[Nn]um\(\"outline\"[^)]*\)\}px",
                    "garis tepi dipakai mentah (px) tanpa diskalakan ke lebar kanvas → teks blur.",
                )
                self.assertNotRegex(
                    baris, r"\d+px",
                    "masih ada ukuran px TETAP di bayangan — tak ikut mengecil bersama kanvas.",
                )
                self.assertRegex(
                    baris, r"cq\([^)]*[Nn]um\(\"outline\"",
                    "garis tepi tidak melewati penskala kanvas (cq) — sumber blur.",
                )


if __name__ == "__main__":
    unittest.main()
