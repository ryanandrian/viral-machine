"""SUARA YANG DITAMPILKAN AKTIF WAJIB BISA DIPAKAI — katalog tak boleh menjanjikan yang mati.

CACAT YANG DIJAGA (pertanyaan owner 2026-08-18: *"mengapa tts gemini belum ada audio test"*):
sebuah mesin suara butuh TIGA baris hidup serentak agar bisa dipakai tenant —
  (1) `tts_profiles.is_active`      → mesinnya muncul di pemilih layar channel
  (2) `ai_models` component='tts'   → ada model yang bisa dipanggil
  (3) `voice_catalog.is_active`     → ada karakter suaranya
Layar channel MENYARING suara berdasarkan mesin yang dipilih, jadi begitu (1) mati, suara seaktif
apa pun **tak pernah terlihat siapa pun**.

Keadaan nyata saat penjaga ini dibuat — DUA mesin cacat sekaligus:
  • `gemini`: 4 suara aktif + model TTS aktif + **LULUS uji 18-Agu 07:56**, tapi profil mesin MATI
    ⇒ seluruh pekerjaan itu tak terjangkau tenant.
  • `groq`  : 2 suara aktif, profil mesin MATI, dan **NOL model TTS di katalog** ⇒ suara hantu:
    tak bisa dipakai, dan contoh audionya pun mustahil dibuat.

KELAS YANG SAMA TERJADI DUA KALI DALAM DUA HARI — 16-Agu pada 12 suara fal (suara & model
dinyalakan, mesin tetap mati). Menyalakan model TTS tidak otomatis menyalakan mesinnya, dan tak ada
apa pun yang memperingatkan. Itu sebabnya konsistensinya dijaga mesin, bukan diingat manusia.

Dijaga: KETIGANYA hidup bersama, atau ketiganya mati bersama. Keadaan separuh = katalog menipu.
Ditambah: suara yang ditawarkan wajib punya contoh audio, supaya tenant bisa MENDENGAR sebelum
memilih — itu isi kolom `voice_catalog.preview_url` yang dikelola di Katalog panel admin.
"""
import os
import sys
import unittest
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sb():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not (url and key):
        return None
    return create_client(url, key)


class TestKatalogSuara(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = _sb()
        if cls.sb is None:
            raise unittest.SkipTest("kredensial DB tak tersedia — bukan kegagalan")
        cls.profil = {t["provider_key"]: t for t in
                      cls.sb.table("tts_profiles").select("provider_key,is_active").execute().data}
        cls.model = defaultdict(list)
        for m in cls.sb.table("ai_models").select("model_key,provider_key,is_active") \
                .eq("component", "tts").eq("is_active", True).execute().data:
            cls.model[m["provider_key"]].append(m["model_key"])
        cls.suara = defaultdict(list)
        for v in cls.sb.table("voice_catalog").select("voice_key,provider_key,is_active,preview_url") \
                .eq("is_active", True).execute().data:
            cls.suara[v["provider_key"]].append(v)

    def test_suara_aktif_hanya_pada_mesin_yang_menyala(self):
        """Suara aktif di mesin yang mati = pekerjaan mubazir; tenant tak pernah melihatnya."""
        buruk = {pk: len(v) for pk, v in self.suara.items()
                 if not (self.profil.get(pk) or {}).get("is_active")}
        self.assertEqual(
            buruk, {},
            f"Suara AKTIF pada mesin suara yang MATI: {buruk}. Layar channel menyaring suara "
            "menurut mesin yang dipilih, jadi suara ini tak pernah terlihat siapa pun — katalog "
            "menjanjikan sesuatu yang tak bisa dipakai.")

    def test_mesin_menyala_wajib_punya_model_yang_bisa_dipanggil(self):
        buruk = [pk for pk, p in self.profil.items()
                 if p.get("is_active") and not self.model.get(pk)]
        self.assertEqual(
            buruk, [],
            f"Mesin suara menyala tanpa satu pun model TTS aktif: {buruk}. Tenant bisa memilihnya, "
            "lalu produksinya gagal karena tak ada model untuk dipanggil.")

    def test_mesin_menyala_wajib_punya_suara(self):
        buruk = [pk for pk, p in self.profil.items()
                 if p.get("is_active") and not self.suara.get(pk)]
        self.assertEqual(buruk, [],
                         f"Mesin suara menyala tanpa satu pun karakter suara: {buruk}.")

    def test_setiap_suara_yang_ditawarkan_bisa_didengar_dulu(self):
        """Owner 18-Agu: tenant harus bisa MENDENGAR contohnya sebelum memilih."""
        bisu = {pk: [v["voice_key"] for v in vs if not (v.get("preview_url") or "").strip()]
                for pk, vs in self.suara.items()}
        bisu = {k: v for k, v in bisu.items() if v}
        self.assertEqual(
            bisu, {},
            f"Suara aktif TANPA contoh audio: {bisu}. Tenant disuruh memilih suara yang tak bisa "
            "ia dengar lebih dulu — kolom `preview_url` di Katalog panel admin.")


if __name__ == "__main__":
    unittest.main()
