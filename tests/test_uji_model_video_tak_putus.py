"""UJI MODEL YANG LAMA TIDAK BOLEH BERAKHIR SEBAGAI "respons tidak valid".

CACAT YANG DIJAGA (dilaporkan owner 2026-08-16, layar Catalog → Uji model MiniMax Hailuo 02):
layar menampilkan *"respons tidak valid"*, seolah modelnya rusak. Log server membuktikan sebaliknya:

    17:59:07  [AIVideo] Initialized: model=hailuo-02-standard
    18:00:37  [AIVideo] ✓ Klip jadi: clip_01_ai.mp4 5.9s (0.9MB)
    18:00:37  "POST /api/admin/catalog/test-model HTTP/1.1" 200 OK

Mesin BERHASIL. Videonya jadi, dan vendor MENAGIHNYA (±Rp 4.000). Yang gagal adalah SAMBUNGANNYA:
uji makan 90 detik, melewati batas tunggu jalur perantara, sehingga balasan yang sampai ke layar
bukan JSON → `r.json()` gagal → pesan penutup "respons tidak valid" dan hasilnya hilang.

Kelas cacatnya bukan "video lambat", melainkan **menunggu di tempat untuk pekerjaan panjang**. Model
video berikutnya bisa lebih lambat lagi; menaikkan batas tunggu hanya memindahkan garis putusnya.
Yang benar: hasil uji SUDAH disimpan permanen ke `ai_models.cost_hint.audit` oleh mesin — jadi
layar cukup MENUNGGU jejak itu berubah, persis pola "titip lalu tanya berkala" yang sudah dipakai
tombol Pratinjau 1 gambar.

Dua hal yang dijaga di sini:
  A. Layar tidak boleh menyerah saat sambungan putus — ia wajib menunggu jejak hasilnya.
  B. Jejak hasil wajib bisa DIBEDAKAN antar-uji di hari yang sama. Stempel bertanggal saja membuat
     uji ulang menghasilkan catatan identik ⇒ layar yang menunggu perubahan menggantung selamanya.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = os.path.join(AKAR, "apps", "web", "src", "app", "admin", "(panel)", "catalog", "page.tsx")
MESIN = os.path.join(AKAR, "src", "config", "model_tester.py")


def _baca(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestA_LayarTakMenyerah(unittest.TestCase):
    """Sambungan putus ≠ uji gagal. Uji tetap berjalan di server dan hasilnya tetap tersimpan."""

    def setUp(self):
        self.src = _baca(LAYAR)

    def test_ada_penantian_hasil_saat_sambungan_putus(self):
        self.assertIn(
            "tungguHasilUji", self.src,
            "Layar masih menunggu di tempat. Untuk model video yang butuh >1 menit, sambungan putus "
            "lebih dulu dan admin diberi tahu 'respons tidak valid' — padahal videonya jadi dan "
            "sudah ditagih vendor.")

    def test_balasan_tak_terparse_tidak_langsung_jadi_pesan_gagal(self):
        self.assertNotIn(
            'catch(() => ({ ok: false, error: "respons tidak valid" }))', self.src,
            "Balasan yang tak bisa dibaca masih langsung dijadikan vonis GAGAL. Itu memvonis model "
            "yang sebenarnya bekerja, dan membuang hasil yang sudah dibayar.")


class TestB_JejakHasilBisaDibedakan(unittest.TestCase):
    """Layar menunggu jejak BERUBAH — maka jejaknya wajib berubah tiap uji, termasuk di hari sama."""

    def setUp(self):
        self.src = _baca(MESIN)

    def test_stempel_hasil_menyertakan_waktu(self):
        self.assertIn(
            "%Y-%m-%d %H:%M", self.src,
            "Stempel hasil uji masih bertanggal saja. Menguji ulang model yang sama di hari yang "
            "sama menghasilkan catatan IDENTIK, sehingga layar yang menunggu perubahan menggantung "
            "tanpa akhir.")

    def test_penanda_mulai_ditulis_sebelum_panggilan_vendor(self):
        self.assertIn(
            "SEDANG DIUJI", self.src,
            "Tidak ada penanda 'sedang diuji'. Tanpa itu layar tak bisa membedakan 'uji belum mulai' "
            "dari 'uji sedang berjalan', dan admin tidak tahu apakah kreditnya sedang terpakai.")


if __name__ == "__main__":
    unittest.main()
