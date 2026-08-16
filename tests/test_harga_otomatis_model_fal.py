"""Penjaga: harga model yang penanda modelnya BERAWALAN VENDOR wajib ikut terisi otomatis.

LATAR (ditemukan 2026-08-16). Sumber harga otomatis untuk model naskah membangun daftarnya
**berdasarkan nama tanpa awalan vendor** — penjelasan fungsinya sendiri menyatakan itu:
`id ... berbentuk 'vendor/model_id' → dipetakan by suffix`. Tetapi pencariannya memakai penanda
model UTUH. Untuk model yang penandanya polos (`gpt-4o-mini`) keduanya kebetulan sama, jadi tak
pernah ketahuan. Untuk model yang penandanya berawalan vendor (`google/gemini-2.5-flash`,
seluruh model naskah fal) pencarian SELALU meleset → harganya tak pernah terisi sendiri, dan
angka lama yang keliru tak pernah tergantikan.

Yang dijaga PERILAKUNYA, bukan cara mencocokkannya: model berawalan vendor harus mendapat harga
dari sumber otomatis, model polos tidak boleh berubah perilakunya, dan model yang memang tak ada
sumbernya tetap dilaporkan jujur sebagai tanpa-sumber (bukan dikosongkan diam-diam).
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.billing.price_sync as ps  # noqa: E402

HARGA_SUMBER = {"gemini-2.5-flash": {"in_per_1m": 0.3, "out_per_1m": 2.5},
                "gpt-4o-mini": {"in_per_1m": 0.15, "out_per_1m": 0.6}}


class _Tabel:
    def __init__(self, rows, tulis):
        self._rows, self._tulis, self._patch, self._key = rows, tulis, None, None

    def select(self, *a, **k):
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def upsert(self, *a, **k):
        self._patch = None
        return self

    def eq(self, _kol, val):
        self._key = val
        return self

    def execute(self):
        if self._patch is not None:
            self._tulis.append((self._key, self._patch))
            self._patch = None
            return type("R", (), {"data": []})()
        return type("R", (), {"data": self._rows})()


class _SB:
    def __init__(self, models, provs, tulis):
        self._m, self._p, self._t = models, provs, tulis

    def table(self, nama):
        if nama == "ai_models":
            return _Tabel(self._m, self._t)
        if nama == "ai_providers":
            return _Tabel(self._p, self._t)
        return _Tabel([], self._t)


def _jalankan(models):
    """Sinkron harga hermetik: sumber utama sengaja dimatikan → jalur sumber-cadangan naskah."""
    tulis = []
    sb = _SB(models, [{"provider_key": "fal", "price_feed_prefix": None}], tulis)
    with patch.object(ps, "requests") as rq, \
         patch.object(ps, "_openrouter_map", lambda: dict(HARGA_SUMBER)), \
         patch.object(ps, "_notify_admin", lambda *a, **k: None):
        rq.get.side_effect = RuntimeError("sumber utama sengaja dimatikan dalam uji")
        ringkas = ps.sync_prices(sb=sb, force=True)
    return ringkas, dict(tulis)


class TestHargaOtomatis(unittest.TestCase):

    def test_model_berawalan_vendor_dapat_harga_otomatis(self):
        ringkas, ditulis = _jalankan([
            {"model_key": "google/gemini-2.5-flash", "model_id": "google/gemini-2.5-flash",
             "component": "llm", "provider_key": "fal",
             "pricing": {"per_request_usd": 0.001, "source": "manual"}, "pricing_locked": False},
        ])
        self.assertIn(
            "google/gemini-2.5-flash", ditulis,
            "Model naskah berawalan vendor tidak pernah mendapat harga dari sumber otomatis — "
            "tabel harganya tinggal angka manual lama yang tak pernah diperbarui siapa pun.")
        baru = ditulis["google/gemini-2.5-flash"]["pricing"]
        self.assertEqual(baru["in_per_1m"], 0.3)
        self.assertEqual(baru["out_per_1m"], 2.5)
        self.assertNotIn(
            "per_request_usd", baru,
            "Tarif per-permintaan yang lama harus TERGANTI, bukan menumpang — kalkulator biaya "
            "memeriksanya lebih dulu, jadi selama ia ada, token yang terpakai diabaikan.")
        self.assertEqual(ringkas["missing"], [])

    def test_model_berpenanda_polos_tidak_berubah_perilakunya(self):
        """REGRESI: seluruh model lama memakai penanda polos — jangan sampai ikut bergeser."""
        _, ditulis = _jalankan([
            {"model_key": "gpt-4o-mini", "model_id": "gpt-4o-mini", "component": "llm",
             "provider_key": "openai", "pricing": {"in_per_1m": 0.15}, "pricing_locked": False},
        ])
        self.assertEqual(ditulis["gpt-4o-mini"]["pricing"]["in_per_1m"], 0.15)
        self.assertEqual(ditulis["gpt-4o-mini"]["pricing"]["out_per_1m"], 0.6)

    def test_model_tanpa_sumber_dilaporkan_jujur(self):
        """Model gambar/video/suara fal memang tak ada di sumber mana pun — harganya JANGAN
        dikosongkan, dan ketiadaan sumbernya harus dilaporkan apa adanya."""
        ringkas, ditulis = _jalankan([
            {"model_key": "kling-2.5-turbo-pro", "model_id": "kling-2.5-turbo-pro",
             "component": "video", "provider_key": "fal",
             "pricing": {"per_video_base_usd": 0.35, "source": "manual"}, "pricing_locked": False},
        ])
        self.assertEqual(ringkas["missing"], ["kling-2.5-turbo-pro"])
        self.assertNotIn("kling-2.5-turbo-pro", ditulis,
                         "Model tanpa sumber harga TIDAK boleh disentuh — harga manualnya hilang.")

    def test_harga_yang_dikunci_admin_tetap_tak_tersentuh(self):
        """REGRESI pengaman lama: kunci admin menang atas sinkron otomatis."""
        _, ditulis = _jalankan([
            {"model_key": "google/gemini-2.5-flash", "model_id": "google/gemini-2.5-flash",
             "component": "llm", "provider_key": "fal",
             "pricing": {"in_per_1m": 99.0}, "pricing_locked": True},
        ])
        self.assertEqual(ditulis, {})


if __name__ == "__main__":
    unittest.main()
