"""Jalur GAMBAR/VIDEO membawa MAKNA errornya — §8e-B, mengikuti prosedur §5 & pola `_classify_el_error`.

SSOT: `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §5 (checklist onboarding 5 langkah) + §6 (tata-kelola) + §8e.

**DIBANGUN MENGIKUTI PROSEDUR, BUKAN RANCANGAN BARU** — ini penting, karena teguran owner 2026-08-05:
*"setiap tukang sipil datang membawa konsep desainnya sendiri, kebayang hancurnya bangunan ini."*
Prosedur §5 yang diikuti persis:
  1. sampel error NYATA ditangkap dari worker.log produksi
  2. dicatat di §4 (kolom Bukti = tanggal + lokasi log)
  3. dipetakan ke `ErrorClass` HANYA yang jelas (ragu → UNKNOWN)
  4. `classify_visual_error()` di adapter transportnya, pola `_classify_el_error`
  5. diuji (classifier + propagasi + keputusan) → status ✅ + commit kode & dokumen BERSAMAAN

BUKTI SAMPEL (§6: "HANYA kode ber-bukti-sampel yang dipetakan"):
  • fal 403 — worker.log 2026-07-14 19:54/19:56/19:57, **6 kejadian**:
      `{"detail":"User is locked. Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing."}`
  • OpenAI (jalur gambar) — worker.log 2026-07-29 11:32:40 di `_generate_hook_frame`:
      `Error code: 400 - {'message':'Billing hard limit has been reached.','code':'billing_hard_limit_reached'}`

KENAPA BUKAN "KEPUTUSAN PRODUK BARU": `QUOTA_EXHAUSTED` & `ACCOUNT_BILLING` SUDAH anggota `FAST_FAIL`
sejak ketok owner 17-Jul & 18-Jul. §6 menyatakan *"menambah/menghapus kelas fast-fail = ubah `FAST_FAIL`
saja"* ⇒ memetakan kode penyedia BARU ke kelas yang SUDAH ADA adalah langkah 3 prosedur normal.
Arahan owner sendiri: **petakan per KELAS, jangan per nama penyedia.**

DAMPAK: saat saldo/tagihan penyedia gambar habis, rem menyala setelah 1 kegagalan alih-alih 3 ⇒ biaya
tenant tak terbakar 3× pada sebab yang mustahil sembuh dengan diulang (insiden RAD 17-Jul yang
melahirkan seluruh arsitektur ini).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import FAST_FAIL, ErrorClass, VisualError  # noqa: E402
from src.providers.visual.base import classify_visual_error  # noqa: E402

# ── SAMPEL PRODUKSI, VERBATIM ────────────────────────────────────────────────
SAMPEL_FAL_403 = ('fal submit HTTP 403: {"detail":"User is locked. Reason: Exhausted balance. '
                  'Top up your balance at fal.ai/dashboard/billing."}')
SAMPEL_OPENAI_BILLING = ("Error code: 400 - {'error': {'message': 'Billing hard limit has been reached.', "
                         "'type': 'billing_limit_user_error', 'code': 'billing_hard_limit_reached'}}")


class TestSampelProduksiTerpetakan(unittest.TestCase):

    def test_fal_saldo_habis_jadi_quota_exhausted(self):
        ec, human = classify_visual_error(VisualError(SAMPEL_FAL_403))
        self.assertIs(ec, ErrorClass.QUOTA_EXHAUSTED,
                      "saldo penyedia habis tak dikenali — biaya akan terbakar 3× sebelum rem")
        self.assertTrue(human and "saldo" in human.lower(),
                        "pesan manusiawi tak menyebut apa yang harus tenant kerjakan")

    def test_openai_batas_tagihan_jadi_account_billing(self):
        ec, human = classify_visual_error(VisualError(SAMPEL_OPENAI_BILLING))
        self.assertIs(ec, ErrorClass.ACCOUNT_BILLING)
        self.assertTrue(human, "pesan manusiawi kosong")

    def test_kedua_kelas_memang_anggota_FAST_FAIL(self):
        """Inti dampaknya. Bila kelak salah satu dicabut dari FAST_FAIL, remnya kembali 3× dan biaya
        tenant terbakar lagi — dan itu harus jadi keputusan SADAR, bukan efek samping."""
        for k in (ErrorClass.QUOTA_EXHAUSTED, ErrorClass.ACCOUNT_BILLING):
            self.assertIn(k, FAST_FAIL, f"{k.value} bukan lagi fast-fail — rem kembali menunggu 3× gagal")


class TestYangRaguTETAP_UNKNOWN(unittest.TestCase):
    """§5.3 & §6: hanya yang JELAS dipetakan. Salah-petakan lebih berbahaya daripada tak memetakan —
    kelas fast-fail menghentikan channel tenant setelah 1 kegagalan."""

    def test_error_jaringan_biasa_tetap_unknown(self):
        for pesan in ("fal submit HTTP 500: internal error",
                      "fal job timeout >600s (status terakhir: IN_QUEUE)",
                      "Unduh klip gagal HTTP 502",
                      "Response tidak mengandung b64_json maupun url"):
            ec, human = classify_visual_error(VisualError(pesan))
            self.assertIs(ec, ErrorClass.UNKNOWN, f"'{pesan[:40]}' salah dipetakan jadi {ec.value} — "
                                                  f"channel tenant akan direm padahal cukup diulang")
            self.assertIsNone(human)

    def test_bukan_exception_atau_kosong_tidak_meledak(self):
        for e in (VisualError(""), Exception("x"), VisualError("None")):
            ec, _ = classify_visual_error(e)
            self.assertIs(ec, ErrorClass.UNKNOWN)

    def test_body_terstruktur_didahulukan_seperti_pola_el(self):
        """Pola `_classify_el_error`: body terstruktur DULU, baru string-scan."""
        e = VisualError("teks tanpa petunjuk")
        e.body = {"error": {"code": "billing_hard_limit_reached", "message": "Batas tagihan tercapai"}}
        ec, human = classify_visual_error(e)
        self.assertIs(ec, ErrorClass.ACCOUNT_BILLING)
        self.assertEqual(human, "Batas tagihan tercapai", "pesan PENYEDIA harus didahulukan bila ada")


class TestAdapterMeneruskanKelasnya(unittest.TestCase):
    """Classifier benar tapi tak dipanggil = nol guna. Ini yang terjadi selama ini di jalur visual."""

    def _sumber(self, nama: str) -> str:
        return open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "src", "providers", "visual", nama), encoding="utf-8").read()

    def test_ai_video_meneruskan_error_class(self):
        s = self._sumber("ai_video.py")
        self.assertIn("classify_visual_error", s, "ai_video tak memakai classifier")
        self.assertRegex(s, r"raise VisualError\([^)]*error_class=",
                         "ai_video tak meneruskan error_class — makna hilang di lapisan atas")

    def test_ai_image_meneruskan_error_class_di_kedua_transport(self):
        s = self._sumber("ai_image.py")
        self.assertIn("classify_visual_error", s, "ai_image tak memakai classifier")
        self.assertGreaterEqual(
            len([m for m in s.split("raise VisualError(") if "error_class=" in m[:200]]), 2,
            "ai_image meneruskan error_class di <2 titik — jalur fal DAN OpenAI wajib keduanya "
            "(sampel produksi ada untuk keduanya)")

    def test_classifier_tinggal_di_base_bukan_disalin(self):
        """Satu sumber. Menyalin tabel ke dua berkas = 'dua penggaris' yang sudah pernah melahirkan
        insiden di rantai durasi (lihat test_pipeline_gerbang_durasi.py)."""
        for nama in ("ai_video.py", "ai_image.py"):
            self.assertNotIn("_VISUAL_ERROR_MAP", self._sumber(nama),
                             f"{nama} menyalin tabel kelas error — wajib satu sumber di base.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
