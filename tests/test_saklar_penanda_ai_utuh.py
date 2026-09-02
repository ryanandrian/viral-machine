"""Saklar penanda AI ke YouTube wajib UTUH dari layar sampai database.

LATAR (owner 2026-09-02): tenant melihat label AI di YouTube pada SETIAP video dan khawatir itu
merugikan monetisasi. Ditelusuri: mesin mengirim `containsSyntheticMedia: true` di tiap publish
(`youtube_publisher.py`), aktif sejak 14-Jun (`d83149e`, default ON), bernilai True di 15/15 channel,
dan **tenant tidak punya saklarnya di layar mana pun** — kolomnya ada di DB tapi tak pernah dipasang.

Fakta kebijakan (YouTube Help, diperiksa 02-Sep-2026): mengungkap TIDAK membatasi jangkauan maupun
kelayakan monetisasi; yang dihukum justru konsisten TIDAK mengungkap (label paksa, penghapusan
konten, suspensi dari Partner Program). Wajib hanya untuk konten realistis yang bisa menyesatkan.
Karena itu keputusan owner: **saklar diserahkan ke tenant per channel, bawaan tetap menyala.**

Uji ini mengikat RANTAI PENUH, bukan sekadar "ada tombolnya": kolom dibaca → saklar mengubah →
tersimpan → ikut penghitung belum-disimpan & pembatalan. Satu mata putus = saklar yang menipu:
tenant menggeser, layar berubah, tapi mesin tetap menerima nilai lama.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"
MESIN = "src/distribution/youtube_publisher.py"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestRantaiSaklarUtuh(unittest.TestCase):
    def setUp(self):
        self.l = _tanpa_komentar(_isi(LAYAR))

    def test_kolom_ikut_dibaca_dari_database(self):
        """Tak ikut di `select` ⇒ nilainya selalu jatuh ke bawaan, saklar tampak menyala terus."""
        m = re.search(r'\.select\("id,channel_name[^"]*"\)', self.l)
        self.assertIsNotNone(m, "kueri kolom channel tak ditemukan")
        self.assertIn("ai_disclosure", m.group(0),
                      "kolom ai_disclosure tak ikut dibaca — layar tak pernah tahu nilai sebenarnya.")

    def test_ada_saklar_yang_mengubahnya(self):
        self.assertRegex(
            self.l, r"setAiDisc\(",
            "tak ada saklar yang mengubah penanda AI di layar.",
        )

    def test_ikut_tersimpan_ke_database(self):
        i = self.l.find('publish_privacy: privacy')
        self.assertNotEqual(i, -1, "blok simpan kartu Pengaturan channel tak ditemukan")
        self.assertIn("ai_disclosure:", self.l[i - 400:i + 400],
                      "penanda AI tidak ikut disimpan — tenant menggeser, mesin tetap terima nilai lama.")

    def test_ikut_penghitung_belum_disimpan_dan_pembatalan(self):
        """Kalau tak ikut, tombol Simpan tak menyala / Batal tak mengembalikannya — saklar menipu."""
        i = self.l.find("ident: chg(")
        self.assertNotEqual(i, -1, "penghitung dirty kartu ident tak ditemukan")
        self.assertIn("aiDisc", self.l[i:i + 400],
                      "penanda AI tak masuk penghitung 'belum disimpan'.")
        j = self.l.find("ident: () =>")
        self.assertNotEqual(j, -1, "pembatalan kartu ident tak ditemukan")
        self.assertIn("setAiDisc", self.l[j:j + 400],
                      "tombol Batal tidak mengembalikan penanda AI.")

    def test_bawaan_tetap_menyala(self):
        """Bawaan OFF = tenant tanpa sadar berhenti mengungkap ⇒ risiko sanksi Partner Program."""
        self.assertRegex(
            self.l, r"aiDisc:\s*c\?\.ai_disclosure\s*\?\?\s*true",
            "bawaan penanda AI bukan menyala — berbahaya untuk channel berkonten realistis.",
        )

    def test_penjelasan_risiko_dwibahasa(self):
        # jangkar = saklar DI LAYAR (bukan deklarasi state/undo yang muncul lebih dulu)
        i = self.l.find("setAiDisc(e.target.checked)")
        self.assertNotEqual(i, -1, "saklar penanda AI tak ditemukan di layar")
        blok = self.l[max(0, i - 1800):i + 300]
        self.assertRegex(blok, r"<Bi\s+id=\"[^\"]+\"\s+en=\"[^\"]+\"",
                         "saklar penanda AI tanpa penjelasan dwibahasa.")
        self.assertRegex(
            blok, r"(monetisasi|Partner|sanksi|risiko)",
            "penjelasan tidak menyebut risikonya — tenant mematikannya tanpa tahu akibatnya.",
        )


class TestMesinTetapMembacaKolomItu(unittest.TestCase):
    """Saklar tak ada gunanya bila mesin berhenti membacanya."""

    def test_publisher_masih_mengirim_dari_kolom_channel(self):
        m = _isi(MESIN)
        self.assertRegex(
            m, r'"containsSyntheticMedia":\s*bool\(getattr\(tenant_config, "ai_disclosure"',
            "publisher tak lagi mengambil penanda AI dari setelan channel.",
        )


if __name__ == "__main__":
    unittest.main()
