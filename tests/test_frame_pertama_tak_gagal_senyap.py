"""Frame pertama gagal TIDAK BOLEH senyap — video tetap terbit, tapi sebabnya wajib terlihat.

SSOT: `CLAUDE.md` §0.6 — *"kegagalan komponen = STOP + notifikasi, HARAM fallback senyap."*
Rinciannya: `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §8f.

MASALAH YANG DIJAGA (diukur ke worker.log produksi 2026-08-04)
`visual_assembler._generate_hook_frame` gagal → `logger.warning(... keeping original clips[0])` → video
**tetap dikirim** dengan frame pembuka yang lebih lemah, **tanpa notifikasi ke siapa pun**. Frame pertama
adalah penentu penonton berhenti menggulir; menurunkannya diam-diam melemahkan janji inti produk.

**4 gagal dari 181 percobaan (2,2%)**, empat sebab berbeda — dan **dua di antaranya kode kita sendiri**:

| Sebab | Milik |
|---|---|
| `[Errno 2] No such file: hook_frame_img.jpg` | **kode kita** |
| `FFmpeg image-to-video failed` | **kode kita** |
| `Billing hard limit has been reached` (OpenAI) | akun penyedia tenant |
| `cannot schedule new futures after interpreter shutdown` | worker sedang berhenti (jinak) |

**Kenapa diperbaiki tanpa menunggu ketok:** §0.6 SUDAH diketok owner. Membuat kegagalan TERLIHAT adalah
pelaksanaan aturan itu, bukan keputusan produk baru. Yang MASIH butuh ketok (dan sengaja TIDAK dikerjakan):
menghentikan produksi atau mengulang N× saat frame pertama gagal — itu perilaku-saat-gagal.
Alarm ke tenant juga TIDAK dipasang: untuk 2,2% kejadian, alarm = berisik. Cukup: tercatat sebagai
`ok_degraded` + sebabnya di laporan run, dan log naik dari WARNING ke ERROR.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSEMBLER = os.path.join(AKAR, "src", "production", "visual_assembler.py")
PIPELINE = os.path.join(AKAR, "src", "orchestrator", "pipeline.py")


class TestSebabFramePertamaDirekam(unittest.TestCase):

    def test_atribut_sebab_ada_dan_dikosongkan_tiap_perakitan(self):
        s = open(ASSEMBLER, encoding="utf-8").read()
        self.assertRegex(s, r"hook_frame_error:\s*str \| None = None",
                         "atribut perekam sebab frame pertama hilang")
        self.assertRegex(s, r"self\.hook_frame_error = None",
                         "sebab run LAMA tak dikosongkan di awal perakitan — akan menempel di run BARU "
                         "dan membuat tenant mengejar masalah yang sudah selesai")

    def test_penangkap_merekam_sebab_dan_naik_ke_ERROR(self):
        """WARNING tenggelam di worker.log — itu sebabnya 4 kejadian tak pernah diketahui."""
        s = open(ASSEMBLER, encoding="utf-8").read()
        # Cari PENANGKAP-nya, bukan komentar/docstring: blok yang menyebut frame pertama gagal.
        # (Versi pertama uji ini mencari "Hook frame" dan mendarat di docstring `_generate_hook_frame`
        #  ⇒ merah palsu. Alat ukur yang salah = bug baru yang ditanam.)
        m = re.search(r"FRAME PERTAMA GAGAL", s)
        self.assertIsNotNone(m, "pesan kegagalan frame pertama hilang dari penangkapnya")
        wilayah = s[max(0, m.start() - 500):m.start() + 500]
        self.assertIn("self.hook_frame_error = str(e)", wilayah,
                      "sebab kegagalan frame pertama TIDAK direkam — kembali senyap (§0.6)")
        self.assertRegex(wilayah, r"logger\.error\(",
                         "kegagalan frame pertama masih di level WARNING — tenggelam di worker.log")


class TestLaporanRunMenyebutDegradasi(unittest.TestCase):

    def test_pipeline_menandai_ok_degraded_beserta_sebabnya(self):
        s = open(PIPELINE, encoding="utf-8").read()
        i = s.find('result["steps"]["visuals"]')
        self.assertGreater(i, 0, "hasil langkah visual hilang dari laporan run")
        wilayah = s[i:i + 900]
        self.assertIn("hook_frame_error", wilayah,
                      "laporan run tak menyebut kegagalan frame pertama — degradasi kembali senyap")
        self.assertIn("ok_degraded", wilayah,
                      "status tetap 'ok' padahal mutu turun — laporan yang menyesatkan pembacanya")

    def test_produksi_TIDAK_dihentikan_karena_frame_pertama(self):
        """Pagar arah sebaliknya, dan ini penting: menghentikan video karena frame pembuka gagal =
        perilaku-saat-gagal = KEPUTUSAN PRODUK (§0.6/§2.3d) yang BELUM diketok owner.
        Kalau kelak seseorang mengubahnya jadi `raise`, uji ini merah dan memaksa ketok dulu."""
        s = open(PIPELINE, encoding="utf-8").read()
        i = s.find('result["steps"]["visuals"]')
        wilayah = s[i:i + 900]
        self.assertNotRegex(wilayah, r"raise\s+\w*Error",
                            "produksi DIHENTIKAN karena frame pertama gagal — itu perilaku-saat-gagal "
                            "yang belum diketok owner (§8f: pilihan a/b/c masih terbuka)")


class TestSpecMasihMemuatTemuannya(unittest.TestCase):
    """Kalau §8f dicabut dari dokumen sementara kodenya tetap, angka temuannya hilang dan sesi
    berikutnya tak tahu bahwa 2 dari 4 sebab adalah bug kita sendiri."""

    def test_angka_dan_pemilik_sebab_masih_tertulis(self):
        t = open(os.path.join(AKAR, "AI_ERROR_MANAGEMENT_ARCHITECTURE.md"), encoding="utf-8").read()
        self.assertIn("4 gagal dari 181", t, "angka temuan §8f hilang dari SSOT")
        self.assertRegex(t, r"hook_frame_img\.jpg",
                         "sebab konkret (berkas tak ada) hilang — temuan jadi tak bisa diverifikasi")
        self.assertRegex(t, r"FFmpeg image-to-video failed",
                         "sebab konkret (FFmpeg) hilang dari SSOT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
