"""LOG TIDAK BOLEH MEMBANJIR, DAN PENYAPUNYA TIDAK BOLEH DIAM-DIAM BERHENTI.

KENAPA BERKAS INI ADA (ketok owner 2026-08-13: "tidak boleh ada lagi issue terkait log dan log
sweeper di seluruh area mesinviral v2")

TIGA CACAT YANG DITUTUP, semuanya terukur di server sebelum disentuh:

  1. MESIN TERLALU BERISIK — channel yang langganannya mati dicatat ULANG tiap siklus (terukur
     15,6 detik sekali). 9.950 baris dalam 24 jam untuk 2 channel = 44% dari seluruh isi log.
     Ruginya bukan disk (44 GB kosong) melainkan SINYAL TENGGELAM: tiap diagnosa harus mengaduk
     berkas puluhan MB berisi pengulangan yang sama. Malam ini saja alat ukur tertipu DUA KALI
     karenanya.

  2. PENYAPU LOG MENYAPU ALAMAT YANG SALAH — aturan `/etc/logrotate.d/viral-machine` ditulis
     24-April (era v1), menunjuk `/home/rad4vm/viral-machine/logs/*.log`. Proyek pindah ke v2
     pada 17-Juni; aturannya tertinggal. Selama DUA BULAN ia melapor setiap hari
     "does not exist -- skipping" dan tak seorang pun mendengar, sementara `worker.log` tumbuh
     ke 48 MB tanpa satu pun berkas hasil putaran.
     ⚠️ AKAR STRUKTURALNYA: berkas setelan itu ada DI LUAR repo — tak terversikan, tak terperiksa.
     Karena itu ia kini hidup di `scripts/logrotate-viral-machine.conf` dan dipasang `deploy_be.sh`.

  3. DAFTAR SAPUAN BERKAS KERJA TERTINGGAL saat format berganti — penyapu hanya mengenal
     `.json`/`.mp3`/`.srt`, sementara produksi menulis `.ass` (subtitle; dulu `.srt`), `.txt`
     (daftar klip), `.jpg` (gambar mini), `.mp4`. Terukur: 634 dari 808 berkas >7 hari, ±73 MB;
     tertua 16-Juni dan 17-Juni — hari pindahan v1→v2.

Pola yang sama pada ketiganya: **kegagalan yang melapor ke ruang kosong.** Berkas ini mengubahnya
jadi kegagalan yang MENYALAKAN LAMPU.
"""
import inspect
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KONF_ROTASI = os.path.join(AKAR, "scripts", "logrotate-viral-machine.conf")
SKRIP_DEPLOY = os.path.join(AKAR, "scripts", "deploy_be.sh")


def _teks(p):
    return open(p, encoding="utf-8", errors="ignore").read()


# ── 1. Mesin tidak boleh mencatat hal yang sama tiap siklus ─────────────────────────────────────

class TestMesinTidakBerisik(unittest.TestCase):

    def test_channel_tak_aktif_dicatat_sekali(self):
        from src.orchestrator import producer
        src = inspect.getsource(producer.plan_and_submit)
        self.assertIn("_SKIP_SUDAH_DICATAT", src,
                      "channel tak aktif dicatat ulang tiap siklus — 9.950 baris/hari menenggelamkan "
                      "sinyal yang sesungguhnya")
        self.assertRegex(src, r"if cid not in _SKIP_SUDAH_DICATAT",
                         "penanda ada tapi tidak dipakai sebagai penjaga")

    def test_perubahan_keadaan_TETAP_tercatat(self):
        """Mencatat sekali TIDAK boleh berarti buta. Begitu channel kembali aktif, penandanya wajib
        dihapus supaya kalau kelak mati lagi, kejadian itu tercatat lagi."""
        from src.orchestrator import producer
        src = inspect.getsource(producer.plan_and_submit)
        self.assertIn("_SKIP_SUDAH_DICATAT.discard(cid)", src,
                      "penanda tak pernah dihapus → channel yang pulih lalu mati lagi TIDAK tercatat, "
                      "dan itu membuat kita buta pada perubahan keadaan")

    def test_alur_keputusan_produksi_TIDAK_disentuh(self):
        """ANTI-REGRESI paling penting: yang boleh berubah hanya pencatatan. Syarat gerbang dan
        `continue` wajib utuh — kalau tidak, channel mana yang berproduksi bisa ikut berubah."""
        from src.orchestrator import producer
        src = inspect.getsource(producer.plan_and_submit)
        self.assertRegex(src, r'if not gate_for_channel\(sb, ch\)\["can_produce"\]:',
                         "syarat gerbang langganan berubah — itu di luar lingkup perbaikan log")
        i = src.index('if not gate_for_channel')
        self.assertIn("continue", src[i:i + 900], "cabang lewat kehilangan `continue`")


# ── 2. Aturan penyapu log: terversikan, benar, dan dipasang otomatis ────────────────────────────

class TestAturanPenyapuLog(unittest.TestCase):

    def test_aturan_ada_DI_REPO(self):
        """Akar cacat 2 bulan itu: setelan hidup hanya di server. Di repo = terversikan + ikut deploy."""
        self.assertTrue(os.path.exists(KONF_ROTASI),
                        "aturan pemangkas log tidak ada di repo — ia akan melenceng lagi tanpa jejak")

    def test_menunjuk_berkas_log_yang_BENAR(self):
        k = _teks(KONF_ROTASI)
        self.assertIn("/home/rad4vm/viral-machine-v2/worker.log", k,
                      "aturan tidak menunjuk berkas log yang sebenarnya")
        self.assertNotRegex(k, r"^\s*/home/rad4vm/viral-machine/",
                            "masih menunjuk folder v1 yang sudah tidak ada (fosil pindahan 17-Jun)")

    def test_dua_baris_yang_TERBUKTI_wajib(self):
        """Keduanya ditemukan lewat jalan-kering, bukan penalaran — jangan dicabut tanpa menguji ulang."""
        k = _teks(KONF_ROTASI)
        self.assertTrue(
            re.search(r"^\s*su root root", k, re.M),
            "tanpa `su root root` logrotate MENOLAK: parent directory has insecure permissions → "
            "aturan gagal DIAM-DIAM, persis penyakit yang diobati")
        self.assertTrue(
            re.search(r"^\s*copytruncate", k, re.M),
            "tanpa `copytruncate` systemd tetap menulis ke berkas lama → berkas aktif tampak "
            "kosong selamanya")

    def test_batas_simpan_masuk_akal(self):
        k = _teks(KONF_ROTASI)
        self.assertTrue(re.search(r"^\s*daily", k, re.M), "putaran harian tak disebut")
        m = re.search(r"^\s*rotate\s+(\d+)", k, re.M)
        self.assertIsNotNone(m, "jumlah simpanan tak disebut → log bisa menumpuk lagi lewat arsipnya")
        self.assertLessEqual(int(m.group(1)), 30, "menyimpan terlalu banyak arsip = masalah yang sama")


class TestDeployMemasangDanMemeriksa(unittest.TestCase):
    """Terversikan saja tak cukup: harus ADA yang memasang, dan ADA yang menyalakan lampu bila gagal."""

    def test_deploy_memasang_aturan(self):
        s = _teks(SKRIP_DEPLOY)
        self.assertIn("logrotate-viral-machine.conf", s,
                      "deploy tidak memasang aturan dari repo → server bisa tetap memakai yang lama")
        self.assertIn("/etc/logrotate.d/viral-machine", s)

    def test_deploy_MEMPERINGATKAN_bila_log_membengkak(self):
        """Inilah pengubah 'gagal senyap' jadi 'gagal kelihatan'. Tanpa ini, kalau pemangkas berhenti
        lagi (sebab apa pun), tak ada yang tahu sampai berbulan-bulan kemudian."""
        s = _teks(SKRIP_DEPLOY)
        self.assertIn("worker.log", s, "deploy tak pernah melihat ukuran log")
        self.assertRegex(s, r"PERINGATAN.*pemangkas log|pemangkas log.*tidak bekerja",
                         "tak ada peringatan saat log membengkak — kegagalan tetap senyap")

    def test_kegagalan_pemasangan_tak_menggagalkan_deploy(self):
        """Perbaikan log tak boleh menahan perbaikan produksi — tapi wajib kelihatan."""
        s = _teks(SKRIP_DEPLOY)
        i = s.find("logrotate-viral-machine.conf")
        cuplik = s[max(0, i - 400):i + 900]
        self.assertIn("PERINGATAN", cuplik, "gagal pasang harus diumumkan")
        self.assertNotIn("exit 1", cuplik, "gagal memasang aturan log tidak boleh menggagalkan deploy")


# ── 3. Daftar sapuan berkas kerja harus mencakup yang benar-benar ditulis produksi ──────────────

class TestSapuanBerkasKerja(unittest.TestCase):

    def _pola(self):
        from src.utils.storage_cleaner import StorageCleaner
        return inspect.getsource(StorageCleaner.cleanup_old_logs)

    def test_mencakup_jenis_yang_NYATA_menumpuk(self):
        """Terukur di server 13-Agu: .ass 188 · .txt 188 · .jpg 111 · .mp4 2 — semuanya >7 hari,
        tertua 16/17-Juni. Tak satu pun ada di daftar sapuan lama."""
        src = self._pola()
        for ext, jml in (("ass", 188), ("txt", 188), ("jpg", 111), ("mp4", 2)):
            with self.subTest(ext):
                self.assertIn(f'"*.{ext}"', src,
                              f"berkas .{ext} tak pernah disapu — {jml} berkas menumpuk sejak Juni")

    def test_jenis_LAMA_tak_ikut_dicabut(self):
        """Menghapus pola lama = meninggalkan sampah berkas yang formatnya sudah tak dipakai lagi."""
        src = self._pola()
        for ext in ("json", "mp3", "srt"):
            self.assertIn(f'"*.{ext}"', src, f"pola lama .{ext} hilang → berkas lama tak tersapu")

    def test_video_memakai_ambang_LEBIH_LONGGAR(self):
        """Video satu-satunya yang kehilangannya tak bisa dipulihkan. Sudah diverifikasi penerbitan
        mengunduh dari S3 (bukan dari folder ini), tapi ambang longgar tetap dipakai sebagai jarak
        aman — umur simpan stok 72 jam, ambang ini belasan kali lipat di atasnya."""
        src = self._pola()
        m = re.search(r'"\*\.mp4":\s*(\w+)', src)
        self.assertIsNotNone(m, "pola video tak ditemukan")
        self.assertEqual(m.group(1), "cutoff_json",
                         "video memakai ambang pendek — risiko menghapus video yang belum sempat "
                         "terbit tidak sepadan dengan 50 MB")

    def test_lama_simpan_dari_SETELAN_bukan_angka_mati(self):
        from src.orchestrator import pipeline
        src = inspect.getsource(pipeline.Pipeline.run)
        self.assertIn("cleanup_old_logs", src)
        i = src.index("cleanup_old_logs")
        cuplik = src[i:i + 400]
        self.assertIn("os.getenv", cuplik,
                      "lama simpan ditulis mati di kode (§3.3: nilai dari setelan, nol literal)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
