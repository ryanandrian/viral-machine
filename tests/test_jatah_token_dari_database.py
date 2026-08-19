"""ANGKA JATAH TOKEN WAJIB DARI DATABASE — bukan literal di kode.

CACAT YANG DIJAGA — pelanggaran SAYA SENDIRI, 19-Agu, di dalam perbaikan yang saya buat hari itu:
saat menutup bug "jawaban terpotong" (`[B35]`) saya menanam DUA angka bisnis sebagai literal di kode
— batas atas jatah **4000** dan lantai kenaikan **2000** — beberapa jam setelah saya sendiri
mengutip aturan *"nilai bisnis dari DB/config, nol literal di kode"*. Owner menagihnya:
*"aplikasi ini anda bangun full configuration, minim hardcode, semuanya bisa diadjust lewat database
(admin panel), ini rancangan anda, tapi anda rusak rancangan anda sendiri."*

**Kenapa merugikan, bukan sekadar tidak rapi:** angka itu menentukan seberapa jauh mesin boleh
menaikkan jatah sebelum menyerah. Vendor & model berganti generasi terus — terbukti DUA KALI dalam
tiga hari (Groq memensiunkan 2 model 16-Agu; Google menutup model untuk akun baru). Selama angkanya
literal, owner **tak bisa menyetelnya sendiri**: tiap penyesuaian menuntut sunting kode + deploy,
jalur paling lambat dan paling berisiko.

YANG DIJAGA: kedua angka dibaca dari `app_config` (mekanisme yang SUDAH ADA — `get_int`, cache,
fail-soft), dengan angka terukur sebagai cadangan bila DB tak terjangkau. Cadangan itu WAJIB tetap
ada — gangguan DB tak boleh melumpuhkan produksi.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTERS = os.path.join(AKAR, "src", "providers", "llm", "adapters.py")
KUNCI = ("llm_jatah_token_batas_atas", "llm_jatah_token_kenaikan_min")


class TestJatahTokenDariDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(ADAPTERS, encoding="utf-8") as f:
            cls.src = f.read()

    def test_kedua_angka_dibaca_dari_app_config(self):
        kurang = [k for k in KUNCI if k not in self.src]
        self.assertEqual(
            kurang, [],
            f"Angka jatah token belum dibaca dari `app_config`: {kurang}. Selama literal di kode, "
            "owner tak bisa menyetelnya dari panel admin — tiap penyesuaian menuntut sunting kode + "
            "deploy. Itu melanggar rancangan config-driven aplikasi ini.")

    def test_masih_punya_cadangan_bila_db_terganggu(self):
        """Yang diikat: ADANYA cadangan — bukan susunan hurufnya. (Versi pertama uji ini menuntut
        angka MENTAH sebagai argumen kedua, padahal cadangan bernama yang berketerangan lebih baik.
        Uji harfiah = uji palsu; diperketat ke KONTRAKnya: cadangan ada, bernilai angka, dan jalur
        pembacaannya tahan galat.)"""
        for kunci in KUNCI:
            self.assertTrue(
                re.search(r"get_int\(\s*[\"']" + kunci + r"[\"']\s*,\s*[\w\d]+\s*\)", self.src),
                f"`{kunci}` dibaca tanpa argumen cadangan — blip DB menjatuhkan jalur naskah.")
        # Cadangannya wajib benar-benar ada sebagai angka, dan pembacaannya wajib tahan galat.
        from src.providers.llm import adapters as A
        self.assertIsInstance(A._BATAS_JATAH_CADANGAN, int)
        self.assertIsInstance(A._MIN_JATAH_NAIK_CADANGAN, int)
        self.assertTrue(re.search(r"except Exception:\s*\n\s*return _BATAS_JATAH_CADANGAN", self.src),
                        "pembacaan config tak dibungkus penanganan galat — gangguan DB akan meledak "
                        "di tengah produksi, bukan mundur ke cadangan")

    def test_angka_di_app_config_ada_dan_masuk_akal(self):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(AKAR, ".env"))
        from supabase import create_client
        u = os.getenv("SUPABASE_URL")
        k = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not (u and k):
            self.skipTest("kredensial DB tak tersedia — bukan kegagalan")
        sb = create_client(u, k)
        rows = {r["key"]: r for r in sb.table("app_config").select("key,value,description")
                .in_("key", list(KUNCI)).execute().data}
        hilang = [x for x in KUNCI if x not in rows]
        self.assertEqual(hilang, [], f"Kunci belum ada di app_config: {hilang} — admin tak punya "
                                    "kenop untuk menyetelnya.")
        atas = int(rows["llm_jatah_token_batas_atas"]["value"])
        naik = int(rows["llm_jatah_token_kenaikan_min"]["value"])
        # Terukur 18/19-Agu: jawaban sah 1.235–1.280 token · Gemini butuh 4000 · Groq MENOLAK 8000.
        self.assertGreaterEqual(atas, 2500, "batas atas di bawah kebutuhan terukur (jawaban ±1.280 token)")
        self.assertLessEqual(atas, 6000, "batas atas mendekati angka yang vendor TOLAK (Groq 413 pada 8000)")
        self.assertLess(naik, atas, "lantai kenaikan tak boleh melampaui batas atas")
        for x in KUNCI:
            self.assertTrue((rows[x].get("description") or "").strip(),
                            f"kenop `{x}` tanpa keterangan — admin tak tahu artinya")


if __name__ == "__main__":
    unittest.main()
