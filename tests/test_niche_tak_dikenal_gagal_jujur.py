"""NICHE TAK DIKENAL HARUS MENGHENTIKAN RUN — HARAM diganti diam-diam dengan niche lain.

CACAT YANG DIJAGA (F-2, `AUDIT_ATRIBUSI_NICHE_2026-07-15.md`)
Enam titik intelijen dulu memakai pola: *niche tak dikenal → pakai **niche AKTIF PERTAMA***. Akibatnya
konten niche LAIN diproduksi diam-diam atas nama channel tenant — kelas pelanggaran yang sama dengan
tiga fallback senyap yang ditanam 14-Jul dan ditegur keras owner (§0.6: kegagalan komponen = STOP +
notifikasi, HARAM fallback senyap).

📌 **TEMUAN 2026-08-15 (`[B32]` T8):** perbaikannya **SUDAH dikerjakan 15-Jul** di keenam titik — tapi
`AUDIT_ATRIBUSI_NICHE` masih menulis *"MENUNGGU KETOK"*. **Dokumen yang basi persis seperti ini adalah
sumber pengerusakan**: sesi berikutnya membacanya, menyangka belum dikerjakan, lalu "memperbaiki" yang
sudah benar. Yang kurang bukan kodenya — melainkan **penjaganya**. Berkas ini penjaganya, dan dokumennya
dikoreksi bersamaan.

Diuji sebagai PERILAKU (fungsinya dipanggil sungguhan dengan niche karangan), bukan dengan mencocokkan
teks komentar — komentar bisa benar sementara kodenya berubah.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NICHE_HANTU = "__niche_yang_tidak_pernah_ada__"


class _ConfigPalsu:
    """Cukup memuat yang dibaca titik-titik itu."""
    def __init__(self):
        self.niche = NICHE_HANTU
        self.tenant_id = "uji"
        self.content_language = "id-ID"


class TestEnamTitikGagalJujur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

    def test_penulis_naskah_berhenti(self):
        from src.intelligence.script_engine import _get_profile
        with self.assertRaises(Exception) as ctx:
            _get_profile(NICHE_HANTU)
        self.assertIn(NICHE_HANTU, str(ctx.exception))

    def test_pemikat_pembuka_berhenti(self):
        from src.intelligence.hook_optimizer import HookOptimizer
        with self.assertRaises(Exception) as ctx:
            HookOptimizer()._build_prompt({"topic": "x"}, _ConfigPalsu())
        self.assertIn(NICHE_HANTU, str(ctx.exception))

    def test_pemilih_topik_berhenti(self):
        from src.intelligence.niche_selector import NicheSelector
        with self.assertRaises(Exception) as ctx:
            NicheSelector()._prepare_signals_summary({"peak_region": "id"}, _ConfigPalsu())
        self.assertIn(NICHE_HANTU, str(ctx.exception))

    def test_nol_substitusi_senyap_tersisa_di_kode(self):
        """Pola lama: mengambil niche pertama dari registry sebagai pengganti. Dijaga agar tak kembali."""
        akar = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
        pelanggar = []
        for a, _, bs in os.walk(akar):
            for b in bs:
                if not b.endswith(".py"):
                    continue
                p = os.path.join(a, b)
                with open(p, encoding="utf-8") as f:
                    for i, baris in enumerate(f, 1):
                        t = baris.strip()
                        if t.startswith("#"):
                            continue
                        # substitusi = mengambil elemen pertama registry niche lalu memakainya
                        if ("next(iter(niches" in t or "list(niches.values())[0]" in t
                                or "list(niches)[0]" in t):
                            pelanggar.append(f"{os.path.relpath(p, akar)}:{i}")
        self.assertEqual(pelanggar, [],
                         f"substitusi senyap niche kembali muncul: {pelanggar}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
