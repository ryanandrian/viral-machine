"""⛔⛔ PARAMETER YANG KITA KIRIM = TANGGUNG JAWAB KITA — dua arah, keduanya wajib.

Lahir 14-Agu dari kerugian yang bisa dihitung, bukan dari kekhawatiran:

  Skema resmi Cloudflare `flux-1-schnell` hanya memuat `prompt` + `steps`; `seed` TIDAK ADA
  (dibaca 14-Agu). Kita mengirimnya. Cloudflare menerimanya diam-diam berbulan-bulan, lalu mulai
  memvalidasi skema — 8-Agu 1× · 11-Agu 1× · 13-Agu 10× · 14-Agu 22× (37 kejadian, tren NAIK):
      AiError: Bad input: Error: Additional or unevaluated properties '/seed' at '/' not allowed

  Satu adegan gagal menggagalkan SELURUH produksi (gagal-jujur §8i), jadi yang hangus adalah
  pekerjaan yang hampir selesai — uang TENANT, untuk kesalahan KITA:
      13-Agu 19:44  248 dtk · 15 panggilan LLM · 4 gambar  → $0,0146
      14-Agu 19:07  442 dtk · 34 panggilan LLM · 6 gambar  → $0,0284
      14-Agu 19:13  341 dtk · 26 panggilan LLM · 5 gambar  → $0,0246
                                                    total ±$0,068 dalam 2 hari

  Dan tenant dirugikan DUA kali: uangnya terpakai, lalu pesan yang ia terima berbunyi
  *"Kegagalan terjadi di layanan AI Anda"* — karena galatnya digolongkan `milik_kita=False`.

DUA ARAH yang dijaga berkas ini:
  (1) PENCEGAHAN — parameter tak-didukung tidak pernah dikirim (vendor baru otomatis aman)
  (2) KEJUJURAN  — bila tetap terjadi, galatnya mengaku MILIK KITA, di vendor mana pun

⛔ Bila berkas ini merah, jangan dilonggarkan. Merahnya berarti uang tenant bisa terbakar lagi
untuk parameter yang kita sendiri kirim.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.providers.galat_registry import golongkan          # noqa: E402
from src.providers.visual.ai_image import AIImageProvider   # noqa: E402


def _penyedia(params: dict | None, seed):
    """Objek provider TANPA menyentuh DB/jaringan — hanya dua atribut yang diuji."""
    p = object.__new__(AIImageProvider)
    p.model_config = {"params": dict(params or {})}
    p.visual_seed = seed
    return p


class TestSeedHanyaKeModelYangMenyatakanMendukung(unittest.TestCase):
    """ARAH 1 — pencegahan. Default WAJIB 'tidak mengirim'."""

    def test_model_tanpa_penanda_TIDAK_dikirimi_seed(self):
        """Cloudflare flux-schnell: skema resminya hanya prompt+steps ⇒ seed haram dikirim."""
        self.assertFalse(
            _penyedia({"steps": 8}, 123456)._seed_boleh_dikirim(),
            "model tanpa `supports_seed` tetap dikirimi seed → 37 kejadian 5006 & ±$0,068 uang "
            "tenant hangus akan terulang")

    def test_model_BARU_yang_belum_dikenal_juga_aman(self):
        """Syarat owner: 'berlaku untuk setiap penambahan AI model/vendor baru kedepannya'.

        Model yang belum ada hari ini tidak punya penanda apa pun ⇒ otomatis tidak dikirimi seed,
        tanpa seorang pun perlu mengingat aturan ini saat menambahkannya."""
        for params in ({}, None, {"steps": 4}, {"image_size": {"width": 1080}},
                       {"supports_seed": False}, {"supports_seed": "ya"}, {"supports_seed": 0}):
            with self.subTest(params=params):
                self.assertFalse(_penyedia(params, 999)._seed_boleh_dikirim(),
                                 f"params={params!r} tidak menyatakan dukungan resmi, seed tetap dikirim")

    def test_model_yang_MENYATAKAN_mendukung_tetap_dapat_seed(self):
        """ARAH KEDUA dari pencegahan: jangan sampai fungsi Diversity §9.1 mati diam-diam.

        fal `flux/dev` — `seed` ADA di skema resminya (dibaca 14-Agu) ⇒ wajib tetap terkirim."""
        self.assertTrue(
            _penyedia({"supports_seed": True, "num_inference_steps": 28}, 777)._seed_boleh_dikirim(),
            "model yang resmi mendukung seed tidak lagi menerimanya → keragaman gambar mati diam-diam")

    def test_tanpa_seed_terpilih_tak_ada_yang_dikirim(self):
        self.assertFalse(_penyedia({"supports_seed": True}, None)._seed_boleh_dikirim())


class TestGalatParameterMengakuMilikKita(unittest.TestCase):
    """ARAH 2 — kejujuran. Berlaku LINTAS-VENDOR, termasuk vendor yang belum ada."""

    # Pesan VERBATIM dari worker.log VPS (bukan karangan).
    NYATA = ('Cloudflare image HTTP 400: {"errors":[{"message":"AiError: Bad input: Error: '
             "Additional or unevaluated properties '/seed' at '/' not allowed "
             '(1a67b190-908f-4fce-a8ff-46fad235ee43)","code":5006}],"success":false}')

    def test_sampel_produksi_nyata_diakui_milik_kita(self):
        p = golongkan("cloudflare", status=400, kode=None, teks=self.NYATA)
        self.assertTrue(p.milik_kita,
                        "galat 37 kejadian ini masih ditimpakan ke tenant — pesannya akan kembali "
                        "berbunyi 'Kegagalan terjadi di layanan AI Anda' untuk permintaan KITA")

    def test_berlaku_untuk_vendor_yang_BELUM_ADA(self):
        """Dipasang di jalur generik, bukan di tabel Cloudflare — supaya vendor besok ikut benar."""
        for vendor in ("", "vendor_besok", "penyedia_yang_belum_lahir"):
            with self.subTest(vendor or "(tanpa nama)"):
                p = golongkan(vendor, status=400, kode=None,
                              teks="Bad request: unknown parameter 'seed' for this model")
                self.assertTrue(p.milik_kita,
                                f"vendor '{vendor}' tidak ikut terlindungi → syarat generik owner gagal")

    def test_beberapa_bentuk_kalimat_vendor_tertangkap(self):
        for teks in ("Additional properties are not allowed ('seed' was unexpected)",
                     "unevaluated properties '/guidance' at '/' not allowed",
                     "unknown parameter: seed",
                     "unexpected keyword argument 'seed'",
                     "unrecognized argument: negative_prompt",
                     "unknown field \"seed\" in request body"):
            with self.subTest(teks[:40]):
                self.assertTrue(golongkan("cloudflare", status=400, teks=teks).milik_kita)

    def test_TIDAK_salah_alamat_ke_arah_sebaliknya(self):
        """⛔ Pagar terpenting di kelas ini.

        Salah-alamat punya DUA arah, dan arah ini sama merusaknya: menandai galat MILIK TENANT
        (kunci ditolak · saldo habis · model dipensiunkan) sebagai 'milik kita' akan membuat mesin
        berkata "ini masalah MesinViral" lalu tenant menunggu kita membereskan sesuatu yang hanya
        BISA ia bereskan sendiri. Karena itu pola lebar ('not allowed' · 'bad input' · 'invalid')
        DIUJI dan DITOLAK — kalimat di bawah membuktikan kenapa.
        """
        for teks in ("Incorrect API key provided: sk-***. You can find your API key at ...",
                     "invalid_api_key: The API key is invalid",
                     "You exceeded your current quota, please check your plan and billing details",
                     "The model `llama-x` is not allowed for your account",
                     "Rate limit reached for model on tokens per day (TPD): Limit 100000"):
            with self.subTest(teks[:40]):
                p = golongkan("openai", status=None, kode=None, teks=teks)
                self.assertFalse(
                    p.milik_kita,
                    f"kalimat MILIK TENANT ini ditandai milik kita → tenant akan menunggu kami "
                    f"membereskan hal yang hanya bisa ia bereskan sendiri: {teks[:60]}")

    def test_kalimat_biasa_tidak_tertangkap(self):
        for teks in ("internal server error", "connection timeout",
                     "Service unavailable, please retry", "prompt was rejected by safety filter"):
            with self.subTest(teks[:30]):
                self.assertFalse(golongkan("cloudflare", status=None, teks=teks).milik_kita)


class TestPenggolonganTetapAmanUntukKelas(unittest.TestCase):
    """Yang berubah hanya ASAL-USUL (milik siapa), bukan kelas — nol perubahan perilaku rem."""

    def test_kelas_tetap_aman_boleh_diulang(self):
        from src.exceptions import FAST_FAIL
        p = golongkan("cloudflare", status=400, teks=TestGalatParameterMengakuMilikKita.NYATA)
        self.assertNotIn(p.kelas, FAST_FAIL,
                         "galat parameter tak boleh mengerem channel seketika — sebabnya ada di "
                         "pihak kami dan akan hilang begitu kodenya dibetulkan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
