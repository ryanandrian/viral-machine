"""Penjaga: harga model yang penanda modelnya BERAWALAN VENDOR wajib ikut terisi otomatis.

LATAR (ditemukan 2026-08-16). Sumber harga otomatis untuk model naskah membangun daftarnya
**berdasarkan nama tanpa awalan vendor** — penjelasan fungsinya sendiri menyatakan itu:
`id ... berbentuk 'vendor/model_id' → dipetakan by suffix`. Tetapi pencariannya memakai penanda
model UTUH. Untuk model yang penandanya polos (`gpt-4o-mini`) keduanya kebetulan sama, jadi tak
pernah ketahuan. Untuk model yang penandanya berawalan vendor (`google/gemini-2.5-flash`,
seluruh model naskah fal) pencarian SELALU meleset → harganya tak pernah terisi sendiri, dan
angka lama yang keliru tak pernah tergantikan.

⚠️ KOREKSI BESAR 23-Agu-2026 (F3). Uji ini DULU mengharuskan model naskah fal mendapat harga dari
sumber cadangan (OpenRouter) dan mengharuskan tarif `per_request_usd` lamanya DIHAPUS. Itu ternyata
MENGUNCI PERILAKU YANG SALAH: fal adalah AGREGATOR — ia menetapkan tarifnya sendiri
($0,001 PER PERMINTAAN, terverifikasi dari API resmi fal 23-Agu), sementara sumber cadangan mencari
BY SUFFIX sehingga yang ditemukan adalah tarif VENDOR ASAL (Anthropic/OpenAI/Google per token).
Akibat nyata: 3 baris naskah fal berharga tarif vendor lain, dan catatan asalnya terhapus.

Niat asli uji ini tetap dijaga — "harga jangan membusuk diam-diam" — tapi caranya diperbaiki:
baris AGREGATOR yang tak punya sumber sah **dilaporkan sebagai tanpa-sumber** (muncul di laporan
harian + ditandai di panel), dan harga lamanya TIDAK ditimpa tarif vendor lain.

Yang dijaga PERILAKUNYA: model polos tetap dapat harga otomatis dari sumber cadangan · baris
agregator TIDAK boleh memakainya · model tanpa sumber dilaporkan jujur · baris terkunci tak tersentuh.

[24-Agu] Data uji di bawah memuat stempel `cost_hint.audit = "LULUS ..."` karena sinkron kini
menolak menulis harga untuk model yang belum pernah lulus tombol Uji (butir C: API harga fal
menjawab 200 OK untuk endpoint yang TIDAK ADA, jadi "200 OK" bukan bukti modelnya ada). Prasyaratnya
DIPENUHI di data uji, bukan dilonggarkan di kodenya — yang diuji di sini tetap perilaku HARGA.
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

    def test_baris_agregator_TIDAK_memakai_tarif_vendor_lain(self):
        """Inti koreksi F3. Model naskah fal ber-tarif per-permintaan (tarif SAH milik fal) tak boleh
        ditimpa tarif per-token vendor asal yang ditemukan sumber cadangan by-suffix."""
        ringkas, ditulis = _jalankan([
            {"model_key": "google/gemini-2.5-flash", "model_id": "google/gemini-2.5-flash",
             "component": "llm", "provider_key": "fal",
             "pricing": {"per_request_usd": 0.001, "source": "manual"}, "pricing_locked": False,
             "cost_hint": {"audit": "LULUS uji manual admin 2026-08-23 10:00"},},
        ])
        self.assertNotIn(
            "google/gemini-2.5-flash", ditulis,
            "Baris AGREGATOR ditimpa tarif vendor di belakangnya — itu memakai harga pihak lain "
            "untuk penyedia yang menagih sendiri (cacat 23-Agu).")
        self.assertIn(
            "google/gemini-2.5-flash", ringkas["missing"],
            "Baris agregator tanpa sumber sah WAJIB dilaporkan tanpa-sumber, supaya muncul di "
            "laporan harian & ditandai di panel — bukan didiamkan.")

    def test_model_berpenanda_polos_tidak_berubah_perilakunya(self):
        """REGRESI: seluruh model lama memakai penanda polos — jangan sampai ikut bergeser."""
        _, ditulis = _jalankan([
            {"model_key": "gpt-4o-mini", "model_id": "gpt-4o-mini", "component": "llm",
             "provider_key": "openai", "pricing": {"in_per_1m": 0.15}, "pricing_locked": False,
             "cost_hint": {"audit": "LULUS uji manual admin 2026-08-23 10:00"},},
        ])
        self.assertEqual(ditulis["gpt-4o-mini"]["pricing"]["in_per_1m"], 0.15)
        self.assertEqual(ditulis["gpt-4o-mini"]["pricing"]["out_per_1m"], 0.6)

    def test_model_tanpa_sumber_dilaporkan_jujur(self):
        """Model gambar/video/suara fal memang tak ada di sumber mana pun — harganya JANGAN
        dikosongkan, dan ketiadaan sumbernya harus dilaporkan apa adanya."""
        ringkas, ditulis = _jalankan([
            {"model_key": "kling-2.5-turbo-pro", "model_id": "kling-2.5-turbo-pro",
             "component": "video", "provider_key": "fal",
             "pricing": {"per_video_base_usd": 0.35, "source": "manual"}, "pricing_locked": False,
             "cost_hint": {"audit": "LULUS uji manual admin 2026-08-23 10:00"},},
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
