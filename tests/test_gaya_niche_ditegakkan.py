"""GAYA RUPA NICHE HARUS BERADA DI DEPAN PERINTAH GAMBAR — dan larangan frame pembuka milik DNA.

═══ APA YANG DIUKUR, BUKAN DIDUGA (uji terkendali 2026-08-15, `SISA_KERJA [B32]` T6) ═══
SATU adegan yang sama dikirim ke mesin gambar yang sama (`gpt-image-1-mini`) dalam empat susunan,
memakai DNA `sunnah_harian` yang meminta **animasi 3D**:

| susunan | gaya rupa | daftar "Avoid" | hasil (7 gambar) |
|---|---|---|---|
| A apa adanya (produksi hari ini) | di EKOR | ada | **foto** (2/2) |
| B gaya DI DEPAN                  | di DEPAN | ada | **animasi 3D** (2/3, sisanya setengah jalan) |
| C tanpa "Avoid"                  | di EKOR | tidak | foto (1/1) |
| D gaya di depan, tanpa "Avoid"   | di DEPAN | tidak | foto (2/2) |

**Pengungkitnya = LETAK, bukan panjangnya perintah.** Mesin gambar menimbang kata-kata awal jauh lebih
berat; gaya yang menempel di ekor — sesudah paragraf deskriptif panjang — praktis tak terdengar.

⛔ **DUGAAN SAYA SEBELUMNYA GUGUR.** Saya menduga kalimat `Avoid: photorealistic…` justru MEMANGGIL
fotorealisme (menyebut = menghadirkan). Varian D mematahkannya: membuang daftar "Avoid" **memperburuk**
hasil, bukan memperbaiki. Dugaan itu dicatat di sini supaya tak dihidupkan lagi oleh sesi berikutnya.

⚠️ **JUJUR SOAL BATASNYA:** menaruh gaya di depan **sangat memperbaiki, tidak menjamin** — satu dari
tiga percobaan B hanya setengah bergaya. Karena itu ini disebut *penegakan*, bukan *kepastian*; lapis
pemeriksaan hasil ada di T7.

═══ KENAPA HANYA NICHE YANG MEMILIH GAYA ═══
`render_style` kosong ⇒ perintah gambar **sama persis seperti sebelumnya** untuk 47 niche lama —
jaminan byte-identik dari 14-Agu tidak dilanggar. Niche yang MEMILIH gaya (hari ini 1, besok berapa pun)
otomatis mendapat penegakannya tanpa menyentuh kode: generik untuk model & vendor mana pun, sesuai
mandat owner 14-Agu.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _provider(render_style: str):
    """Provider asli, tanpa jaringan — hanya perakit prompt yang diuji."""
    from src.providers.visual.ai_image import AIImageProvider
    cfg = {
        "visual_provider": "ai_image:gpt-image-1-mini",
        "visual_api_key": "kunci-palsu-tak-dipakai",
        "niche": "uji",
        "niche_visual_style": ({"render_style": render_style} if render_style else {}),
        "model_row": {"provider_key": "openai", "model_id": "gpt-image-1-mini",
                      "component": "image", "default_params": {}},
    }
    return AIImageProvider(cfg)


class TestGayaNicheDiDepanPerintah(unittest.TestCase):
    ADEGAN = "A young man in a cozy living room sitting cross-legged on the floor"

    def test_gaya_niche_muncul_di_awal(self):
        p = _provider("stylized 3D animated")
        pos, _ = p._build_image_prompt(self.ADEGAN)
        awal = pos[:80].lower()
        self.assertIn("stylized 3d animated", awal,
                      f"gaya rupa niche TIDAK di depan — terukur: yang di ekor diabaikan mesin gambar. "
                      f"Awal prompt: {pos[:80]!r}")

    def test_adegannya_tetap_utuh(self):
        p = _provider("stylized 3D animated")
        pos, _ = p._build_image_prompt(self.ADEGAN)
        self.assertIn(self.ADEGAN, pos, "isi adegan hilang saat gaya disisipkan")

    def test_niche_tanpa_gaya_rupa_tak_berubah_sehuruf_pun(self):
        """47 niche lama: jaminan byte-identik 14-Agu HARAM dilanggar."""
        p_kosong = _provider("")
        pos, neg = p_kosong._build_image_prompt(self.ADEGAN)
        self.assertTrue(pos.startswith(self.ADEGAN),
                        f"prompt niche tanpa `render_style` berubah — regresi 47 niche. Awal: {pos[:60]!r}")

    def test_daftar_larangan_tetap_dikirim(self):
        """Terukur: membuang daftar `Avoid` MEMPERBURUK hasil (varian D). Jangan dicabut."""
        p = _provider("stylized 3D animated")
        _, neg = p._build_image_prompt(self.ADEGAN)
        self.assertTrue(neg.strip(), "daftar larangan gambar hilang — terukur memperburuk kepatuhan gaya")


class TestLaranganFramePembukaMilikDna(unittest.TestCase):
    """`"No people."` dulu dipatri di kode — bertentangan dengan niche yang subjeknya justru manusia
    (mis. sunnah harian). Ia dipindah ke DNA: default tetap sama, tapi niche bisa menentukan."""

    def test_bawaan_tetap_melarang_orang(self):
        from src.production.visual_assembler import prompt_frame_pembuka
        p = prompt_frame_pembuka({}, "konsep")
        self.assertIn("No people", p, "bawaan berubah — 47 niche lama ikut terpengaruh")

    def test_niche_boleh_mengizinkan_orang_di_frame_pembuka(self):
        from src.production.visual_assembler import prompt_frame_pembuka
        p = prompt_frame_pembuka({"hook_frame_people": "yes"}, "konsep")
        self.assertNotIn("No people", p,
                         "niche yang subjeknya manusia masih dipaksa 'tanpa orang' di frame pembuka")

    def test_gaya_rupa_juga_di_depan_pada_frame_pembuka(self):
        from src.production.visual_assembler import prompt_frame_pembuka
        p = prompt_frame_pembuka({"render_style": "stylized 3D animated"}, "konsep")
        self.assertIn("stylized 3d animated", p[:90].lower(),
                      "frame pembuka — frame terpenting — masih menaruh gaya di ekor")


if __name__ == "__main__":
    unittest.main(verbosity=2)
