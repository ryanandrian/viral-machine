"""TOMBOL "HEMAT / SEIMBANG / TERBAIK" TIDAK BOLEH DITAWARKAN BILA TAK BERPENGARUH.

CACAT YANG DIJAGA (temuan owner 18-Agu: *"padahal hemat/seimbang/terbaik bukannya tergantung model
yang dipilih?"* — dan itu BENAR):
tiga tombol itu sebenarnya parameter milik SATU pemasok (OpenAI `quality`), dan mesin hanya
mengirimkannya di jalur OpenAI. Untuk Cloudflare, fal, dan Gemini — **9 dari 12 channel** —
tombolnya DIABAIKAN sepenuhnya. Tenant menekan "Terbaik", tidak ada yang berubah.

Tuas mutu SEBENARNYA berbeda-beda per model dan sudah tersimpan sebagai DATA di katalog:
    cf-flux-schnell   steps 8 (batas maksimum Cloudflare)
    fal flux-schnell  num_inference_steps 4      ← "hemat" = MODELNYA, bukan tombol
    fal flux-dev      num_inference_steps 28     ← "terbaik" = MODELNYA, bukan tombol
    gemini image      tak punya tuas apa pun
⇒ Di fal, beda "hemat" dan "terbaik" adalah **beda model**. Tombol terpisah menyiratkan mutu bisa
dinaikkan tanpa mengganti model — dan itu tidak benar.

RIWAYATNYA (mata ke-3 §0): tombol ini TIDAK salah saat dibuat — tertulis di
`REMEDIASI_NICHE_CHANNEL_VOICE_LLM.md`: *"kenop biaya & mode produksi milik CHANNEL, keputusan
owner"*, dan waktu itu katalog hanya berisi OpenAI. Yang salah: **SAYA menambah pemasok lain dan
meninggalkan tombolnya**. Jadi yang diperbaiki di sini penerapannya, bukan rancangannya.

MESIN TIDAK DISENTUH: jalur produksi memang sudah benar — ia hanya mengirim `quality` pada jalur
yang menerimanya. Yang berbohong hanya LAYAR. Penandanya DATA (`default_params.supports_quality_tier`,
default TIDAK) — pola yang sama persis dengan `supports_seed` (§6 ketetapan owner 14-Agu: jangan
kirim parameter yang skema resmi model tak menyatakan menerimanya; vendor BARU otomatis aman).
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = os.path.join(AKAR, "apps", "web", "src", "app", "(app)", "channels", "[id]", "page.tsx")
MESIN = os.path.join(AKAR, "src", "providers", "visual", "ai_image.py")


def _sb():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(AKAR, ".env"))
    from supabase import create_client
    u, k = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(u, k) if (u and k) else None


class TestA_LayarTakMenawarkanYangTakBerpengaruh(unittest.TestCase):

    def setUp(self):
        with open(LAYAR, encoding="utf-8") as f:
            self.src = f.read()

    def test_kenop_disaring_menurut_dukungan_model(self):
        self.assertIn(
            "supports_quality_tier", self.src,
            "Layar masih menawarkan Hemat/Seimbang/Terbaik TANPA memeriksa apakah model yang "
            "dipilih benar-benar menerimanya — 9 dari 12 channel menekan tombol yang diabaikan mesin.")

    def test_tenant_diberi_tahu_mutu_mengikuti_model(self):
        """Menyembunyikan tombol saja tak cukup: tenant harus tahu mutu ditentukan pilihan MODEL."""
        self.assertTrue(
            re.search(r"Mutu mengikuti model", self.src),
            "Tombol disembunyikan tanpa penjelasan — tenant kehilangan kendali tanpa tahu ke mana "
            "kendalinya pindah (di fal: 'hemat' vs 'terbaik' = schnell vs dev, yaitu MODEL).")


class TestB_MesinTakDisentuh(unittest.TestCase):
    """REGRESI: jalur produksi sudah benar sejak awal — hanya mengirim `quality` pada jalur yang
    menerimanya. Uji ini mengunci supaya perbaikan LAYAR tak merembet ke mesin."""

    def test_quality_hanya_dikirim_di_jalur_yang_menerimanya(self):
        with open(MESIN, encoding="utf-8") as f:
            teks = f.read()
        pengirim = [b.split("(")[0].strip() for b in re.findall(
            r"async def (_generate_\w+)\(.*?(?=\n    async def |\Z)", teks, re.S)]
        blok = dict(re.findall(r"async def (_generate_\w+)\(.*?\n(.*?)(?=\n    async def |\Z)", teks, re.S))
        mengirim = [n for n, isi in blok.items() if "image_quality" in isi]
        self.assertEqual(
            mengirim, ["_generate_dalle"],
            f"Jalur yang mengirim setelan mutu berubah menjadi {mengirim}. Mengirim parameter yang "
            "skema resmi model tak menerimanya = produksi GAGAL (ketetapan owner 14-Agu).")


class TestC_PenandaAdaDiKatalog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sb = _sb()
        if cls.sb is None:
            raise unittest.SkipTest("kredensial DB tak tersedia — bukan kegagalan")

    def test_model_openai_menyatakan_dukungannya(self):
        rows = self.sb.table("ai_models").select("model_key,provider_key,default_params") \
            .eq("component", "image").eq("provider_key", "openai").execute().data
        kurang = [r["model_key"] for r in rows
                  if not (r.get("default_params") or {}).get("supports_quality_tier")]
        self.assertEqual(
            kurang, [],
            f"Model OpenAI yang MENERIMA setelan mutu tak menyatakannya: {kurang}. Akibatnya layar "
            "menyembunyikan tombol yang seharusnya ada, dan tenant kehilangan kendali yang nyata.")

    def test_model_yang_tak_menerimanya_tidak_mengaku(self):
        rows = self.sb.table("ai_models").select("model_key,provider_key,default_params") \
            .eq("component", "image").neq("provider_key", "openai").execute().data
        bohong = [r["model_key"] for r in rows
                  if (r.get("default_params") or {}).get("supports_quality_tier")]
        self.assertEqual(bohong, [],
                         f"Model yang mengabaikan setelan mutu mengaku menerimanya: {bohong}.")


if __name__ == "__main__":
    unittest.main()
