"""Halaman pemasaran WAJIB menyediakan jalan masuk untuk tenant terdaftar — termasuk di HP.

LAPORAN OWNER 2026-09-02: "di landing page tidak ada menu/tombol login untuk tenant terdaftar?"

Terbukti, dan lebih buruk dari sekadar tak terlihat. Di `marketing.css` @880px:
    .mk-actions .btn:not(.btn-default), .mk-actions .segmented, ... { display: none; }
Tombol "Masuk" memakai `btn btn-ghost` ⇒ **disembunyikan**. Menu hamburger hanya memuat
`NAV_LINKS` (tautan halaman), tanpa Masuk. Sisa satu-satunya tombol: "Mulai Gratis"
(`btn-default`) yang menuju view=signup.

Akibat nyata, bukan teori: dari HP tenant terdaftar TAK PUNYA jalan masuk; satu-satunya
tombol menyeretnya ke layar DAFTAR. Pagi 02-Sep owner sendiri terjebak persis begitu dan
tak sengaja membuat tenant baru lewat "Daftar dengan Google" (log nginx 09:00–09:01 WIB:
Android → /auth?view=signup → callback Google → akun baru).

Kompas §7 "apakah ini memblok tenant berbayar?" = YA — karena itu dikunci uji.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELL = "apps/web/src/components/marketing-shell.tsx"
CSS = "apps/web/src/styles/marketing.css"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """Komentar BARIS dibuang DULU (urutan terbalik pernah menelan kode nyata — lihat
    test_akun_terhapus_tak_mengotori_daftar_admin)."""
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


def _blok_menu_hp(isi: str) -> str:
    """Isi <nav className="mk-links"> — satu-satunya wadah yang terbuka lewat tombol burger."""
    i = isi.find('className={`mk-links')
    if i == -1:
        i = isi.find('className="mk-links')
    assert i != -1, "nav.mk-links tak ditemukan — struktur shell berubah"
    j = isi.find("</nav>", i)
    assert j != -1, "penutup </nav> tak ditemukan"
    return isi[i:j]


class TestMenuHpPunyaJalanMasuk(unittest.TestCase):
    def setUp(self):
        self.shell = _tanpa_komentar(_isi(SHELL))

    def test_menu_hamburger_memuat_tautan_masuk(self):
        blok = _blok_menu_hp(self.shell)
        self.assertIn(
            "/auth?view=login", blok,
            "menu HP tak memuat tautan Masuk — di HP tombol Masuk disembunyikan CSS, "
            "jadi tenant terdaftar kehabisan jalan masuk.",
        )

    def test_tautan_masuk_di_menu_hp_dwibahasa(self):
        blok = _blok_menu_hp(self.shell)
        i = blok.find("/auth?view=login")
        potongan = blok[i : i + 260]
        self.assertRegex(
            potongan, r"<Bi\s+id=\"[^\"]+\"\s+en=\"[^\"]+\"",
            "tautan Masuk di menu HP tidak dwibahasa.",
        )

    def test_tombol_masuk_desktop_tetap_ada(self):
        """Jangan memperbaiki HP dengan mengorbankan desktop."""
        i = self.shell.find('className="mk-actions"')
        self.assertNotEqual(i, -1, "wadah .mk-actions tak ditemukan")
        aksi = self.shell[i : i + 1200]
        self.assertIn("/auth?view=login", aksi,
                      "tombol Masuk hilang dari header desktop.")


class TestJalanMasukHpBenarBenarTampil(unittest.TestCase):
    """Ada di markup ≠ terlihat. CSS yang memutuskan."""

    def setUp(self):
        self.css = _isi(CSS)

    def test_ada_aturan_yang_menampilkannya_pada_lebar_hp(self):
        mq = [m for m in re.findall(r"@media[^{]+\{.*?\n\}", self.css, flags=re.S)
              if "mk-links" in m or "mk-burger" in m]
        self.assertTrue(mq, "media query header pemasaran tak ditemukan")
        gabung = "\n".join(mq).replace(" ", "")
        self.assertIn(
            "mk-login-m", gabung,
            "tak ada aturan yang MENAMPILKAN tautan Masuk versi HP di dalam media query.",
        )
        self.assertNotRegex(
            gabung, r"\.mk-login-m\{display:none",
            "aturan HP justru menyembunyikan tautan Masuk versi HP.",
        )

    def test_tak_dobel_di_desktop(self):
        """Di desktop tombol Masuk sudah ada di .mk-actions — versi menu harus disembunyikan."""
        luar = re.sub(r"@media[^{]+\{.*?\n\}", "", self.css, flags=re.S).replace(" ", "")
        self.assertRegex(
            luar, r"\.mk-login-m\{display:none",
            "tautan Masuk versi HP tidak disembunyikan di desktop — akan tampil dobel.",
        )


if __name__ == "__main__":
    unittest.main()
