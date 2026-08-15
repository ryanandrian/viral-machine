"""PRATINJAU DI NICHE LIBRARY (ADMIN) HARUS MEMAKAI CHANNEL YANG PUNYA KUNCI AI.

CACAT YANG DIJAGA (dilaporkan owner 2026-08-15, beberapa menit setelah T11 di-deploy):
tombol Pratinjau di **Niche Library tidak bekerja sama sekali**. Sebabnya: rute mengarahkan pratinjau
admin ke **channel uji INTERNAL admin** (`admin_test_internal`) — yang tabel kuncinya **KOSONG**
(terverifikasi: nol baris `tenant_ai_accounts`). Gerbang kesiapan menolaknya sebelum job mengantre,
jadi **nol job pratinjau pernah lahir** dari klik admin; yang tampil hanya kegagalan.

Akar salahnya seharusnya saya lihat sejak awal: channel uji internal admin memang belum pernah diisi
kunci — fakta yang saya sendiri temukan dan laporkan pagi ini, lalu saya lupakan saat membangun
tombolnya. Admin juga seorang tenant (`tenant_id = auth.uid()`), jadi pratinjau memakai channel &
kunci MILIKNYA — dan biayanya jatuh ke dompet yang menekan tombolnya.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTE = os.path.join(AKAR, "apps", "web", "src", "app", "api", "niches", "preview-image", "route.ts")


class TestRutePratinjau(unittest.TestCase):
    def setUp(self):
        with open(RUTE, encoding="utf-8") as f:
            self.src = f.read()

    def test_admin_memeriksa_channelnya_sendiri_dulu(self):
        i = self.src.find("if (asAdmin)")
        self.assertGreater(i, 0)
        blok = self.src[i:i + 900]
        self.assertIn("testChannelReadiness(g.user.id)", blok,
                      "pratinjau admin tidak memeriksa channel miliknya sendiri — ia akan jatuh ke "
                      "channel internal yang kuncinya kosong dan tombolnya mati seperti 15-Agu")

    def test_channel_internal_hanya_cadangan(self):
        i = self.src.find("if (asAdmin)")
        blok = self.src[i:i + 900]
        self.assertRegex(blok, r"\?\s*g\.user\.id\s*:\s*ADMIN_TEST_TID",
                         "channel internal admin masih jadi pilihan UTAMA, bukan cadangan")

    def test_polling_menerima_kedua_pemilik(self):
        """POST bisa memilih tenant admin ATAU channel internal ⇒ GET wajib menerima keduanya,
        kalau tidak hasilnya jadi 'not found' dan gambar tak pernah tampil."""
        i = self.src.find("export async function GET")
        blok = self.src[i:]
        self.assertIn("ADMIN_TEST_TID", blok)
        self.assertIn("j.tenant_id === pemilik", blok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
