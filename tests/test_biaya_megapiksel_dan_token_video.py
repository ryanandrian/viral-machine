"""PENJAGA F4b — dua cara tagih fal yang tak bisa diwakili satu angka tetap.

MASALAHNYA. fal menagih gambar **per MEGAPIKSEL, dibulatkan KE ATAS**, dan video seedance
**per TOKEN** = (tinggi × lebar × fps × durasi) ÷ 1024. Katalog kita menyimpannya sebagai satu angka
tetap yang dihitung TANGAN untuk satu ukuran saja (1080×1920, 24fps). Angkanya benar **hari ini**;
ia jadi salah tanpa suara begitu resolusi, fps, atau durasi berubah — dan tak ada yang akan
menyadarinya, sebab angkanya tetap "ada" dan tetap masuk akal. Itu kelas cacat yang sama dengan
tarif suara Gemini: bukan angka hilang, tapi angka yang berhenti cocok dengan cara vendor menagih.

YANG DIJAGA (perilaku, bukan teks):
  1. megapiksel DIBULATKAN KE ATAS per gambar — 2,07 MP ditagih 3 MP (bukan 2, bukan 2,07)
  2. token video dihitung dari fakta yang DIUKUR dari berkas hasil, bukan dari asumsi katalog
  3. ukuran/fps tak terukur ⇒ **JUJUR** belum-terhitung, haram ditaksir
  4. satu gambar/klip tak bisa tertagih dua kali (per-satuan DAN per-megapiksel/token)
  5. satuan vendor `megapixels` / `1m tokens` punya jalannya dari API resmi fal ke formula kita
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _hitung(pakai, harga, formula):
    from src.billing import ai_cost
    with patch.object(ai_cost, "_pricing_map", return_value=harga), \
         patch.object(ai_cost, "_formula_map", return_value=formula):
        return ai_cost.compute_cost_usd(pakai)


class TestGambarPerMegapiksel(unittest.TestCase):

    def test_megapiksel_dibulatkan_ke_atas(self):
        """1080×1920 = 2,0736 MP → fal menagih 3 MP. Pembulatan terjadi PER GAMBAR, di pencatat."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_image_megapiksel("m-gambar", 1080 * 1920)
        cost_meter.add_image_megapiksel("m-gambar", 1080 * 1920)
        mp = (cost_meter.summary().get("image_megapiksel") or {}).get("m-gambar")
        self.assertEqual(mp, 6.0,
                         f"megapiksel tertagih {mp} — fal membulatkan KE ATAS per gambar (3+3=6)")

    def test_biaya_dihitung_dari_megapiksel_tertagih(self):
        h = _hitung({"image_megapiksel": {"m-gambar": 6.0}},
                    {"m-gambar": {"per_megapixel_usd": 0.003}},
                    {"m-gambar": "gambar_megapiksel"})
        self.assertEqual(h["unpriced"], [], f"formula megapiksel masih dilaporkan tak didukung: {h}")
        self.assertAlmostEqual(h["usd"], 0.018, places=6,
                               msg=f"biaya megapiksel salah: {h['breakdown']}")

    def test_ukuran_tak_terukur_maka_JUJUR(self):
        """Ukuran gagal dibaca ⇒ belum-terhitung. Haram menaksir dari jumlah gambar."""
        h = _hitung({"image": {"m-gambar": 5}},
                    {"m-gambar": {"per_megapixel_usd": 0.003, "per_image": 0.009}},
                    {"m-gambar": "gambar_megapiksel"})
        self.assertIn("m-gambar", h["unpriced"],
                      f"biaya ditaksir dari jumlah gambar padahal formulanya per megapiksel: {h}")
        self.assertEqual(h["usd"], 0.0, "angka ditebak, bukan dilaporkan jujur")

    def test_tak_tertagih_dua_kali(self):
        h = _hitung({"image_megapiksel": {"m-gambar": 3.0}, "image": {"m-gambar": 1}},
                    {"m-gambar": {"per_megapixel_usd": 0.003, "per_image": 0.009}},
                    {"m-gambar": "gambar_megapiksel"})
        self.assertAlmostEqual(h["usd"], 0.009, places=6,
                               msg=f"tertagih per-gambar DAN per-megapiksel: {h['breakdown']}")

    def test_pencatat_menolak_ukuran_ngawur(self):
        """Ditemukan lewat SABOTASE: versi pertama uji ini memakai `assertFalse` pada nilainya, jadi
        ia LOLOS ketika penolaknya dicabut — sebab ukuran 0/-5 kebetulan menghasilkan 0 (falsy).
        Yang benar: kuncinya harus TIDAK ADA sama sekali, dan dicoba dengan angka negatif yang
        BESAR supaya hasilnya truthy bila penolaknya hilang."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_image_megapiksel("m", 0)
        cost_meter.add_image_megapiksel("m", -2_000_000)
        cost_meter.add_image_megapiksel("m", None)
        cost_meter.add_image_megapiksel("m", "bukan-angka")
        self.assertNotIn("m", cost_meter.summary().get("image_megapiksel") or {},
                         "ukuran ngawur dicatat sebagai megapiksel tertagih")


class TestVideoPerToken(unittest.TestCase):

    def test_token_video_dari_fakta_terukur(self):
        """(tinggi × lebar × fps × durasi) ÷ 1024 — 1080×1920 24fps 8s = 388.800 token."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_video_token("m-video", lebar=1080, tinggi=1920, fps=24, detik=8)
        tok = (cost_meter.summary().get("video_token") or {}).get("m-video")
        self.assertAlmostEqual(tok, 1080 * 1920 * 24 * 8 / 1024, places=1,
                              msg=f"token video salah hitung: {tok}")

    def test_biaya_dihitung_dari_token_video(self):
        tok = 1080 * 1920 * 24 * 8 / 1024
        h = _hitung({"video_token": {"m-video": tok}},
                    {"m-video": {"per_1m_video_tokens_usd": 2.5}},
                    {"m-video": "video_token"})
        self.assertEqual(h["unpriced"], [], f"formula token video masih tak didukung: {h}")
        self.assertAlmostEqual(h["usd"], tok / 1e6 * 2.5, places=6,
                               msg=f"biaya token video salah: {h['breakdown']}")

    def test_fakta_tak_lengkap_maka_JUJUR(self):
        """Kuncinya harus TIDAK ADA (bukan cuma bernilai 0) — nilai 0 tetap lolos `assertFalse`
        walau penolaknya dicabut; itu tertangkap sabotase 23-Agu. Satu fakta negatif dipakai supaya
        hasilnya truthy bila penolaknya hilang."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_video_token("m-video", lebar=0, tinggi=1920, fps=24, detik=8)
        cost_meter.add_video_token("m-video", lebar=-1080, tinggi=1920, fps=24, detik=8)
        cost_meter.add_video_token("m-video", lebar=1080, tinggi=1920, fps=None, detik=8)
        self.assertNotIn("m-video", cost_meter.summary().get("video_token") or {},
                         "token dihitung padahal salah satu faktanya tak terukur (= ditebak)")

    def test_video_tak_tertagih_dua_kali(self):
        tok = 100_000.0
        h = _hitung({"video_token": {"m-video": tok},
                     "video": {"m-video": {"seconds": 8.0, "clips": 1}}},
                    {"m-video": {"per_1m_video_tokens_usd": 2.5, "per_second_usd": 0.1215}},
                    {"m-video": "video_token"})
        self.assertAlmostEqual(h["usd"], tok / 1e6 * 2.5, places=6,
                              msg=f"tertagih per-detik DAN per-token: {h['breakdown']}")


class TestJalanDariApiResmiFal(unittest.TestCase):

    def test_satuan_vendor_punya_formula(self):
        """API harga fal menyebut satuannya sendiri (`megapixels`, `1m tokens`). Tanpa pemetaan ini
        tarifnya TIDAK ditulis — barisnya tetap tanpa-sumber selamanya."""
        from src.billing.price_sync import SATUAN_VENDOR
        for satuan, formula in (("megapixels", "gambar_megapiksel"), ("1m tokens", "video_token")):
            with self.subTest(satuan):
                self.assertIn(satuan, SATUAN_VENDOR,
                              f"satuan vendor '{satuan}' belum punya jalan ke formula kita")
                self.assertEqual(SATUAN_VENDOR[satuan][0], formula)

    def test_formula_ini_bukan_lagi_tak_didukung(self):
        from src.billing.ai_cost import FORMULA_BELUM_DIDUKUNG
        for f in ("gambar_megapiksel", "video_token"):
            with self.subTest(f):
                self.assertNotIn(f, FORMULA_BELUM_DIDUKUNG,
                                 f"formula '{f}' masih dilaporkan belum didukung")

    def test_pencatat_dipanggil_dari_jalur_produksi(self):
        """Pencatat yang tak dipanggil = kode mati, dan biayanya jadi belum-terhitung selamanya."""
        import ast
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for berkas, nama in (("src/providers/visual/ai_image.py", "add_image_megapiksel"),
                             ("src/providers/visual/ai_video.py", "add_video_token")):
            with self.subTest(nama):
                with open(os.path.join(akar, berkas), encoding="utf-8") as f:
                    pohon = ast.parse(f.read())
                titik = [n for n in ast.walk(pohon) if isinstance(n, ast.Call)
                         and getattr(n.func, "attr", "") == nama]
                self.assertEqual(len(titik), 1,
                                 f"{nama} dipanggil {len(titik)}x di {berkas} — wajib TEPAT satu")

    def test_fakta_video_DIUKUR_bukan_diambil_dari_katalog(self):
        """Ditemukan lewat SABOTASE: mengganti pengukuran dengan angka tetap (1080/1920/24) LOLOS
        seluruh uji lama. Padahal itu justru inti F4b — kita tak pernah menyebutkan fps kepada
        vendor, jadi angka katalog adalah TEBAKAN, dan tebakan yang tampak pasti itulah yang
        membuat tarif suara Gemini salah 4× selama berbulan-bulan.

        Dijaga dua arah: pengukur berkas WAJIB dipanggil, dan tiap fakta yang diserahkan ke pencatat
        HARAM berupa angka tetap di kode."""
        import ast
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(akar, "src/providers/visual/ai_video.py"), encoding="utf-8") as f:
            pohon = ast.parse(f.read())
        ukur = [n for n in ast.walk(pohon) if isinstance(n, ast.Call)
                and getattr(n.func, "attr", "") == "_probe_dimensi"]
        self.assertEqual(len(ukur), 1,
                         "pengukur dimensi berkas tidak dipanggil (atau dipanggil ganda) — "
                         "fakta tagihan jadi tebakan")
        panggil = [n for n in ast.walk(pohon) if isinstance(n, ast.Call)
                   and getattr(n.func, "attr", "") == "add_video_token"]
        self.assertEqual(len(panggil), 1, "pencatat token video wajib dipanggil tepat sekali")
        for kw in panggil[0].keywords:
            if kw.arg in ("lebar", "tinggi", "fps"):
                with self.subTest(kw.arg):
                    self.assertNotIsInstance(
                        kw.value, ast.Constant,
                        f"'{kw.arg}' diserahkan sebagai ANGKA TETAP di kode — wajib hasil pengukuran "
                        f"berkas, sebab vendor bisa mengirim resolusi/fps yang berbeda")


class TestRincianBiayaTakSalahAlamat(unittest.TestCase):
    """Rincian biaya per komponen HARAM salah alamat.

    Terukur 23-Agu: model gambar yang ditagih per TOKEN (`gpt-image-1-mini`, 82 produksi) biayanya
    masuk baris **naskah**, sebab token gambar tercatat di keranjang naskah. Totalnya benar; yang
    salah adalah ALAMATNYA. Hari ini tak berdampak karena rincian itu belum dibaca layar mana pun —
    tapi begitu ditampilkan, tenant melihat "Gambar: Rp 0" sambil membayar gambar di baris naskah.
    Memperbaikinya SEKARANG lebih murah daripada menemukannya lagi lewat keluhan tenant.

    Aturannya: baris rincian ditentukan oleh **JENIS MODEL yang skema tagihnya miliki**, bukan oleh
    keranjang meter tempat pemakaiannya kebetulan tercatat."""

    def test_biaya_gambar_bertagih_token_masuk_baris_GAMBAR(self):
        h = _hitung({"llm": {"m-gambar": {"tokens_in": 1_000_000, "tokens_out": 1_000_000,
                                          "calls": 3}}},
                    {"m-gambar": {"in_per_1m": 1.0, "out_per_1m": 2.0}},
                    {"m-gambar": "gambar_token"})
        self.assertAlmostEqual(h["breakdown"]["image"], 3.0, places=6,
                               msg=f"biaya gambar tidak masuk baris gambar: {h['breakdown']}")
        self.assertAlmostEqual(h["breakdown"]["llm"], 0.0, places=6,
                               msg=f"biaya gambar nyasar ke baris naskah: {h['breakdown']}")
        self.assertAlmostEqual(h["usd"], 3.0, places=6, msg="total ikut berubah — haram")

    def test_baris_naskah_tetap_naskah(self):
        """Kebalikannya wajib utuh: model naskah tetap di baris naskah (nol regresi)."""
        h = _hitung({"llm": {"m-naskah": {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 1}}},
                    {"m-naskah": {"in_per_1m": 3.0, "out_per_1m": 15.0}},
                    {"m-naskah": "naskah_token"})
        self.assertAlmostEqual(h["breakdown"]["llm"], 3.0, places=6,
                               msg=f"biaya naskah nyasar: {h['breakdown']}")

    def test_biaya_suara_bertagih_token_tetap_di_baris_SUARA(self):
        h = _hitung({"tts_tokens": {"m-suara": {"tokens_in": 1_000_000, "tokens_out": 1_000_000}}},
                    {"m-suara": {"in_per_1m": 0.5, "out_per_1m": 10.0}},
                    {"m-suara": "suara_token"})
        self.assertAlmostEqual(h["breakdown"]["tts"], 10.5, places=6,
                               msg=f"biaya suara nyasar: {h['breakdown']}")
