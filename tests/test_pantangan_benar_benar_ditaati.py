"""KOTAK PANTANGAN TENANT WAJIB DITAATI MESIN PRODUKSI — NARASI **DAN** GAMBAR.

Ketetapan owner 2026-08-15 (`SISA_KERJA [B32]` T9):
    "1. KOTAK AVOID PADA NICHE STUDIO DAN NICHE LIBRARY, BAIK UNTUK LLM MAUPUN VISUAL, BENAR-BENAR
        DITAATI OLEH MESIN PRODUKSI. TITIK.
     2. PATRI 2 HAL TERKAIT ALLAH DAN RASULULLAH JUGA HANYA PENJAGAAN KEDUA; YANG PERTAMA HARUS DARI
        TENANT SENDIRI MELALUI KOTAK AVOID."

DUA CACAT YANG DIJAGA — terukur 15-Agu:

1. **Larangan GAMBAR tenant tak pernah sampai ke penulis adegan.** `image_negative_prompt` hanya
   ditempel di EKOR perintah gambar. AI yang mengarang adegan tidak pernah diberi tahu, sehingga ia
   bebas menulis "seorang pemuda duduk bersila…" walau tenant melarang manusia. Mesin gambar lalu
   menuruti ADEGAN, bukan larangan yang menempel belakangan — terukur pada video uji 15-Agu.
   ⇒ larangan tenant kalah oleh kalimat yang KITA sendiri tulis.

2. **Pantangan NARASI hanya ditegakkan bila ditulis 1–2 kata.** Butir berupa kalimat tak dicocokkan
   harfiah (dan memang tak boleh — "keras" akan menolak "kekerasan"), sehingga tak ada yang menjaganya
   sama sekali. Terukur: 79 dari 187 butir di 48 niche = kalimat. Contoh nyata `kisah_teladan_islami`:
   pantangan terpentingnya — *"depicting/voicing revered figures directly"* — nol penjagaan.
   ⇒ kini ikut dinilai oleh PENILAI NASKAH yang memang SUDAH berjalan tiap percobaan (nol panggilan AI
   tambahan, nol biaya tambahan): melanggar ⇒ nilai jatuh ⇒ naskah ditulis ulang.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NICHE = {
    "name": "Uji", "description": "d", "description_en": "d", "keywords": ["a"], "style": "s",
    "target_emotion": "t", "is_active": True, "visual_style": {"base_style": "x"},
    "visual_fallbacks": [], "mood_priority": [], "default_hashtags": [], "section_timing": {},
    "image_quality_tags": "tajam",
    "image_negative_prompt": "manusia, wajah, siluet orang, merek kompetitor",
    "emotion_scoring_criteria": "",
    "narration_persona": {"tone": "tenang", "style": "lugas", "hook_style": "question",
                          "emotion_arc": "a → b",
                          "avoid": "menyebut merek kompetitor, kadrun"},
}


class TestLaranganGambarSampaiKePenulisAdegan(unittest.TestCase):
    """Penjagaan PERTAMA milik tenant: adegan lahir sudah patuh, bukan ditambal belakangan."""

    def test_penulis_adegan_diberi_larangan_gambar_tenant(self):
        from src.intelligence.script_engine import bagian_larangan_gambar
        blok = bagian_larangan_gambar(NICHE)
        self.assertIn("manusia", blok)
        self.assertIn("siluet orang", blok)

    def test_niche_tanpa_larangan_gambar_tak_menambah_apa_pun(self):
        """Nol niche boleh berubah perilakunya hanya karena fitur ini lahir."""
        from src.intelligence.script_engine import bagian_larangan_gambar
        self.assertEqual(bagian_larangan_gambar({"image_negative_prompt": ""}), "")
        self.assertEqual(bagian_larangan_gambar({}), "")
        self.assertEqual(bagian_larangan_gambar(None), "")

    def test_terpasang_di_perintah_penulis_adegan(self):
        with open(os.path.join(AKAR, "src", "intelligence", "script_engine.py"), encoding="utf-8") as f:
            src = f.read()
        i = src.find("def generate_visual_prompts")
        j = src.find("def generate_video_prompt")
        self.assertGreater(i, 0)
        self.assertIn("bagian_larangan_gambar", src[i:j],
                      "larangan gambar tenant TIDAK diberikan ke penulis adegan — "
                      "adegan tetap bisa lahir melanggar, lalu mesin gambar menurutinya")


class TestPantanganNarasiDinilaiPenilaiNaskah(unittest.TestCase):
    """Penjagaan pertama untuk narasi: butir berupa KALIMAT ikut dinilai, bukan cuma kata."""

    def test_pantangan_masuk_ke_perintah_penilai(self):
        from src.intelligence.script_analyzer import _build_prompt
        p = _build_prompt({"hook": "x", "full_script": "y"}, "uji", NICHE)
        self.assertIn("menyebut merek kompetitor", p,
                      "penilai naskah tidak diberi tahu pantangan tenant — butir berupa kalimat "
                      "tetap tanpa penjagaan")

    def test_penilai_diminta_menjatuhkan_nilai_bila_dilanggar(self):
        from src.intelligence.script_analyzer import _build_prompt
        p = _build_prompt({"hook": "x", "full_script": "y"}, "uji", NICHE).lower()
        self.assertTrue("violat" in p or "melanggar" in p,
                        "pantangan disebut tapi penilai tidak diperintahkan menjatuhkan nilai")

    def test_niche_tanpa_pantangan_tak_mengubah_perintah(self):
        from src.intelligence.script_analyzer import _build_prompt
        tanpa = {**NICHE, "narration_persona": {**NICHE["narration_persona"], "avoid": ""}}
        p = _build_prompt({"hook": "x", "full_script": "y"}, "uji", tanpa)
        self.assertNotIn("NICHE BANS", p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
