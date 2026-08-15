"""MENGOSONGKAN PILIHAN DI TEST LAB HARUS MENJADI NULL, BUKAN TEKS KOSONG.

CACAT YANG DIJAGA (dilaporkan owner 2026-08-15: *"mengapa saya tidak bisa pilih ElevenLabs, selalu
kembali ke edge"*):
mengganti penyedia TTS mengirim `voice_key: ""` untuk mengosongkan pilihan lama. Tapi
`channels.voice_key` terikat ke `voice_catalog`, dan `""` **bukan kosong** — ia nilai yang wajib ada
di katalog. Database menolak apa adanya:

    violates foreign key constraint "channels_voice_key_fkey"
    Key (voice_key)=() is not present in table "voice_catalog"

⇒ PATCH gagal ⇒ layar memuat ulang ⇒ pilihan MELOMPAT KEMBALI ke penyedia lama. Dari kursi pemakai,
tampak seperti "ElevenLabs tidak bisa dipilih" — padahal katalognya lengkap (4 model TTS ElevenLabs
aktif) dan kuncinya sudah valid. Terbukti: `UPDATE` dengan `""` GAGAL, `UPDATE` dengan `NULL` BERHASIL.

Pelajarannya melampaui satu layar: **"mengosongkan pilihan" dan "string kosong" bukan hal yang sama**
begitu kolomnya terikat katalog. Aturan itu kini dijaga di titik masuknya, sekali untuk semua field.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTE = os.path.join(AKAR, "apps", "web", "src", "app", "api", "admin", "test-lab", "route.ts")


class TestNormalisasiKosong(unittest.TestCase):
    def setUp(self):
        with open(RUTE, encoding="utf-8") as f:
            self.src = f.read()

    def test_kosong_diubah_jadi_null(self):
        self.assertIn('v === "" ? null : v', self.src,
                      "teks kosong masih dikirim apa adanya ke DB — kolom ber-katalog akan menolaknya "
                      "dan pilihan pemakai melompat kembali seperti 15-Agu")

    def test_tipe_patch_mengizinkan_null(self):
        self.assertIn("Record<string, string | null>", self.src,
                      "bentuk patch masih memaksa string ⇒ NULL mustahil dikirim")


if __name__ == "__main__":
    unittest.main(verbosity=2)
