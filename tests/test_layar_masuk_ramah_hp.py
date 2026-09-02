"""Layar auth tenant wajib bisa dipakai dari HP — Enter mengirim, isian otomatis dikenali.

LAHIR DARI KEJADIAN 2026-09-02. Owner melapor "invalid login credential" dari HP. Penyebab
sebenarnya sandi lama (bukan bug), TAPI penelusuran membuka cacat nyata yang belum tersentuh:

  `apps/web/src/app/auth/page.tsx` tidak punya SATU PUN elemen <form> (grep `<form` = nol).
  Tombolnya memakai onClick. Akibatnya di HP, menekan tombol "Go"/Enter pada keyboard TIDAK
  mengirim apa-apa — layar diam, pengguna mengira aplikasinya rusak. Kolomnya juga tanpa
  autoComplete/autoCapitalize: keyboard HP mengapitalkan huruf pertama email, dan penyimpan
  sandi tidak menawarkan isian otomatis.

Layar admin (`app/admin/login/page.tsx:65-92`) SUDAH benar sejak awal — uji ini mengunci agar
layar tenant tidak lagi tertinggal, dan agar view berisian BERIKUTNYA tidak lahir cacat lagi.

CAKUPAN (§0 mata 5 — jalur saudara): keempat view berisian, bukan hanya `login`. Tenant baru
mendaftar dari HP lewat `signup`; yang lupa sandi lewat `forgot` lalu `reset`.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAL_AUTH = "apps/web/src/app/auth/page.tsx"

# view berisian → handler yang WAJIB dipicu oleh pengiriman form (bukan onClick tombol)
VIEW_HANDLER = {
    "login": "doLogin",
    "signup": "doSignup",
    "forgot": "doForgot",
    "reset": "doReset",
}


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """Komentar pernah MENYELAMATKAN uji palsu — kata yang dijaga dikutip di komentar sebelahnya."""
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))


def _blok_view(isi: str, view: str) -> str:
    """Potong blok JSX satu view: dari `{view === "X" &&` sampai penanda view berikutnya/akhir."""
    mulai = isi.find(f'view === "{view}" &&')
    assert mulai != -1, f'penanda view "{view}" tidak ditemukan — struktur halaman berubah'
    sisa = isi[mulai + 10:]
    lanjut = re.search(r'view === "[a-z-]+" &&', sisa)
    return sisa[: lanjut.start()] if lanjut else sisa


class TestEnterDiHpMengirimForm(unittest.TestCase):
    """Inti cacat: tanpa <form>, keyboard HP tidak punya cara mengirim."""

    def setUp(self):
        self.isi = _tanpa_komentar(_isi(HAL_AUTH))

    def test_tiap_view_berisian_punya_form_dengan_onsubmit(self):
        for view, handler in VIEW_HANDLER.items():
            with self.subTest(view=view):
                blok = _blok_view(self.isi, view)
                self.assertRegex(
                    blok, r"<form\b[^>]*onSubmit=",
                    f'view "{view}": isian tidak dibungkus <form onSubmit> — Enter di HP mati.',
                )
                self.assertIn(
                    f"{handler}()", blok,
                    f'view "{view}": <form> ada tapi tidak memanggil {handler}().',
                )

    def test_pembungkus_isian_adalah_form_bukan_div(self):
        """`.form-stack` = pembungkus isian. Selama ia <div>, Enter tak punya sasaran."""
        for view in VIEW_HANDLER:
            with self.subTest(view=view):
                blok = _blok_view(self.isi, view)
                self.assertNotRegex(
                    blok, r'<div className="form-stack"',
                    f'view "{view}": pembungkus isian masih <div>, wajib <form>.',
                )
                self.assertRegex(
                    blok, r'<form className="form-stack"',
                    f'view "{view}": pembungkus isian bukan <form className="form-stack">.',
                )

    def test_tombol_aksi_utama_bertipe_submit_bukan_onclick(self):
        """Jangkar perilaku: handler dipicu lewat pengiriman form. Tombol ber-onClick={doX}
        berarti hanya klik yang jalan — persis cacat yang diperbaiki."""
        for view, handler in VIEW_HANDLER.items():
            with self.subTest(view=view):
                blok = _blok_view(self.isi, view)
                self.assertNotIn(
                    f"onClick={{{handler}}}", blok,
                    f'view "{view}": tombol masih onClick={{{handler}}} — Enter di HP tetap mati.',
                )
                self.assertRegex(
                    blok, r'<button[^>]*type="submit"',
                    f'view "{view}": tidak ada tombol type="submit".',
                )


class TestIsianDikenaliKeyboardDanPenyimpanSandi(unittest.TestCase):
    """Keyboard HP mengapitalkan huruf pertama; penyimpan sandi butuh autoComplete."""

    def setUp(self):
        self.isi = _tanpa_komentar(_isi(HAL_AUTH))

    def test_setiap_kolom_email_menolak_kapital_otomatis(self):
        for view in ("login", "signup", "forgot"):
            with self.subTest(view=view):
                blok = _blok_view(self.isi, view)
                for baris in re.findall(r"<input[^>]*type=\"email\"[^>]*>", blok):
                    self.assertIn(
                        'autoCapitalize="none"', baris,
                        f'view "{view}": kolom email tanpa autoCapitalize="none" — '
                        "keyboard HP mengapitalkan huruf pertama.",
                    )
                    self.assertIn(
                        "autoComplete=", baris,
                        f'view "{view}": kolom email tanpa autoComplete.',
                    )

    def test_kolom_sandi_membawa_autocomplete_yang_benar(self):
        """`current-password` di layar masuk (isian otomatis), `new-password` di
        daftar/reset (usulan sandi kuat). Tertukar = penyimpan sandi salah perlakuan."""
        harapan = {
            "login": "current-password",
            "signup": "new-password",
            "reset": "new-password",
        }
        for view, nilai in harapan.items():
            with self.subTest(view=view):
                blok = _blok_view(self.isi, view)
                pw = re.findall(r"<PwInput\b.*?/>", blok, flags=re.S)  # `=>` di prop bikin [^>] putus
                self.assertTrue(pw, f'view "{view}": tidak ada kolom sandi — struktur berubah?')
                for baris in pw:
                    self.assertIn(
                        f'autoComplete="{nilai}"', baris,
                        f'view "{view}": kolom sandi wajib autoComplete="{nilai}".',
                    )


class TestEmailDinormalkanSepertiJalurLain(unittest.TestCase):
    """doLogin satu-satunya jalur auth yang mengirim email MENTAH; doSignup/doForgot dan
    kedua route server sudah trim+lowercase. Spasi sisipan dari isian otomatis HP = gagal masuk."""

    def test_dologin_trim_dan_lowercase(self):
        isi = _tanpa_komentar(_isi(HAL_AUTH))
        mulai = isi.find("async function doLogin()")
        self.assertNotEqual(mulai, -1, "doLogin tidak ditemukan — struktur berubah")
        badan = isi[mulai : isi.find("async function", mulai + 10)]
        self.assertIn("signInWithPassword", badan, "doLogin tak lagi memanggil signInWithPassword?")
        self.assertRegex(
            badan, r"email\.trim\(\)\.toLowerCase\(\)",
            "doLogin mengirim email mentah — samakan dengan doSignup/doForgot (trim+lowercase).",
        )


if __name__ == "__main__":
    unittest.main()
