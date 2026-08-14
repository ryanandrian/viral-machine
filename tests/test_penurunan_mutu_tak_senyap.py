"""⛔ PENURUNAN MUTU TIDAK BOLEH SENYAP — §8f · §0.6 (HARAM fallback senyap).

FRAME PERTAMA = tuas viral: penentu penonton berhenti menggulir. Bila pembuatannya gagal, video
TETAP diterbitkan dengan klip biasa sebagai pembuka — lebih lemah, dan sampai 15-Agu **tak seorang
pun diberi tahu**.

═══ AKAR YANG SAMA, TIGA KALI — inilah yang berkas ini jaga ═══
Sebabnya SUDAH ditangkap sejak 05-Agu (`visual_assembler.hook_frame_error`) dan dimasukkan ke
`result["steps"]["visuals"]`. Tapi `steps` **tidak pernah ditulis ke tabel mana pun** — komentar di
`visual_assembler.py` bahkan mengakuinya sejak 08-Agu, dan tetap begitu selama sepuluh hari.
Terukur 15-Agu: **85 run sejak 8-Agu, NOL yang menyimpannya.**

Pola yang sama muncul tiga kali di sistem ini: keterangan DITANGKAP lalu DIBUANG sebelum sampai ke
siapa pun — (1) golongan galat ada di `production_runs`, layar tak membacanya · (2) sebab frame
pembuka ada di memori, tak disimpan · (3) pesan mentah penyedia ada di dalam galat, ditimpa pesan
kita saat menyimpan. **Menangkap ≠ menyampaikan**, dan uji di bawah menguji YANG KEDUA.

═══ DATA NYATA yang melahirkannya ═══
13 kegagalan frame pembuka dari 653 percobaan (2%). Sebabnya beragam, dan **3 di antaranya bug
KITA sendiri** (parameter `seed` yang ditolak Cloudflare — baru ditutup 14-Agu), 2 lagi bug kita
di Juni (berkas tak ada · FFmpeg), sisanya milik penyedia/akun tenant.

⛔ Yang SENGAJA tidak diubah: video tetap diterbitkan. Menghentikan produksi karena frame pembuka =
keputusan produk (§0.6) dan bukan hak Claude. Yang dilarang §0.6 adalah **senyap**-nya.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator.producer import _mutu_fields  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sampel VERBATIM dari worker.log VPS (bukan karangan).
NYATA = ('Cloudflare image HTTP 400: {"errors":[{"message":"AiError: Bad input: Error: Additional '
         "or unevaluated properties '/seed' at '/' not allowed\",\"code\":5006}],\"success\":false}")


def _hasil(hook_err=None, extra_visual=None):
    v = {"status": "ok", "clips": 6}
    if hook_err:
        v["status"] = "ok_degraded"
        v["hook_frame_error"] = hook_err
    v.update(extra_visual or {})
    return {"steps": {"visuals": v}}


class TestSebabFramePembukaIkutTersimpan(unittest.TestCase):

    def test_sebab_nyata_ikut_ke_run_metadata(self):
        out = _mutu_fields(_hasil(NYATA))
        self.assertIn("mutu", out, "sebab frame pembuka TIDAK ikut disimpan — ia kembali senyap, "
                                   "persis keadaan 05–15 Agu (85 run, nol tersimpan)")
        self.assertEqual(out["mutu"]["frame_pembuka_gagal"], NYATA)

    def test_pesan_penyedia_TIDAK_dipotong(self):
        """§8h: memotong pesan penyedia justru membuang angka & tautan perbaikannya."""
        panjang = "x" * 4000
        out = _mutu_fields(_hasil(panjang))
        self.assertEqual(len(out["mutu"]["frame_pembuka_gagal"]), 4000,
                         "pesan penyedia dipotong saat disimpan — larangan §8h dilanggar")

    def test_run_SEHAT_tak_menambah_apa_pun(self):
        """Nol perubahan untuk produksi normal — jangan mengotori catatan run yang baik."""
        self.assertEqual(_mutu_fields(_hasil()), {})
        self.assertEqual(_mutu_fields({}), {})
        self.assertEqual(_mutu_fields({"steps": {}}), {})

    def test_gagal_soft_tak_menghentikan_produksi(self):
        """Pencatatan tak boleh jadi syarat produksi — bentuk cacat pun tak boleh melempar."""
        for cacat in ({"steps": None}, {"steps": {"visuals": None}}, {"steps": {"visuals": "bukan dict"}},
                      {"steps": []}, None):
            with self.subTest(cacat=cacat):
                try:
                    hasil = _mutu_fields(cacat if isinstance(cacat, dict) else {})
                except Exception as e:                       # noqa: BLE001
                    self.fail(f"_mutu_fields melempar pada bentuk cacat {cacat!r}: {e}")
                self.assertIsInstance(hasil, dict)


class TestKeduaJalurProduksiMenyimpannya(unittest.TestCase):
    """URUTAN & CAKUPAN — dibaca dari POHON SINTAKS, bukan pencarian teks.

    Cacat 05-Agu bukan karena nilainya tak ada, melainkan karena **tak ada yang memakainya**. Uji ini
    memastikan KEDUA jalur produksi (terjadwal + tombol tenant) benar-benar menyertakannya.
    """

    def test_dua_jalur_menyertakan_mutu_fields(self):
        import ast
        pohon = ast.parse(open(os.path.join(AKAR, "src", "orchestrator", "producer.py"),
                               encoding="utf-8").read())
        pakai = [n.lineno for n in ast.walk(pohon)
                 if isinstance(n, ast.Call)
                 and (n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")) == "_mutu_fields"]
        self.assertGreaterEqual(
            len(pakai), 2,
            f"_mutu_fields dipakai di {len(pakai)} tempat — harus DUA (produksi terjadwal + jalur "
            f"tombol tenant). Kalau hanya satu, separuh produksi kembali senyap.")

    def test_visual_assembler_masih_merekam_sebabnya(self):
        """Hulu rantai: bila perekamannya dicabut, seluruh jalur ini jadi sia-sia."""
        import ast
        pohon = ast.parse(open(os.path.join(AKAR, "src", "production", "visual_assembler.py"),
                               encoding="utf-8").read())
        tulis = [n for n in ast.walk(pohon)
                 if isinstance(n, ast.Attribute) and n.attr == "hook_frame_error"]
        self.assertTrue(tulis, "visual_assembler tak lagi merekam sebab frame pembuka — "
                               "rantai pelaporannya putus di hulu")


if __name__ == "__main__":
    unittest.main(verbosity=2)
