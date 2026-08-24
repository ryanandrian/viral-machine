"""PENJAGA A — biaya HARAM tertukar antar penyedia untuk model yang namanya sama.

KETOKAN OWNER 24-Agu: *"yang harus dipastikan tidak overlaping adalah model yang sama tapi dari
provider yang berbeda (direct, agregator, router) masing-masing punya harga yang berbeda, dan tenant
bisa saja memilih salah satunya."*

BUG DI JALUR YANG ADA (terukur, bukan dugaan):
  • meteran biaya mencatat **nama model saja**, tanpa penyedia yang melayaninya
  • peta harga memakai nama itu sebagai kunci — dua baris bernama sama, yang kedua MENIMPA yang
    pertama tanpa suara
  • `ai_models.model_id` **tidak punya aturan keunikan** (hanya `model_key` yang unik), jadi dua
    baris memang BOLEH bernama sama

Hari ini aman **karena kebetulan** namanya berbeda (`gemini-2.5-flash` langsung vs
`google/gemini-2.5-flash` lewat fal). Tapi APIMaster & OpenRouter memakai protokol OpenAI dan
menyebut model dengan nama **persis sama** (`gpt-4o-mini`) — jadi begitu penyedia router ditambahkan
(arah yang owner tetapkan), tabrakan itu PASTI terjadi. Selisihnya bukan receh: $0,15 per 1jt token
(langsung) vs $0,001 per panggilan (lewat fal) = **150×** untuk model yang sama.

YANG DIJAGA:
  1. dua baris bernama SAMA dari penyedia berbeda → masing-masing ditagih dengan harganya SENDIRI
  2. formula pun ikut per penyedia (langsung = per token · lewat agregator = per panggilan)
  3. nama polos yang AMBIGU (dipakai >1 baris) → dilaporkan JUJUR belum-terhitung, haram ditebak
  4. catatan LAMA (nama polos, tanpa penyedia) tetap terhitung — nol regresi pada riwayat
  5. bentuk kunci hidup di SATU tempat, tidak diketik ulang di meteran
  6. SETIAP titik pencatat menyerahkan penyedianya — satu yang lupa = celah yang kembali
"""
from __future__ import annotations

import ast
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dua baris katalog yang bernama SAMA — persis keadaan yang lahir saat penyedia router ditambahkan.
BARIS_TABRAKAN = [
    {"model_key": "gpt-4o-mini", "model_id": "gpt-4o-mini", "provider_key": "openai",
     "pricing": {"in_per_1m": 0.15, "out_per_1m": 0.6}, "pricing_model": "naskah_token"},
    {"model_key": "router/gpt-4o-mini", "model_id": "gpt-4o-mini", "provider_key": "apimaster",
     "pricing": {"per_request_usd": 0.001}, "pricing_model": "naskah_panggilan"},
]


class _Hasil:
    def __init__(self, data):
        self.data = data


class _Tabel:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def execute(self):
        return _Hasil(self._rows)


class _SB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, nama):
        return _Tabel(self._rows if nama == "ai_models" else [])


def _hitung(pakai, rows=None):
    """compute_cost_usd terhadap katalog TIRUAN — peta harga & formula dibaca dari baris itu,
    bukan dari DB nyata (supaya uji ini tak bergantung keadaan data produksi)."""
    from src.billing import ai_cost
    sb = _SB(rows if rows is not None else BARIS_TABRAKAN)
    return ai_cost.compute_cost_usd(pakai, sb=sb)


class TestBiayaMengikutiPenyedia(unittest.TestCase):

    def setUp(self):
        from src.billing.ai_cost import kunci_biaya   # noqa: F401 — gagal cepat bila belum ada
        self.kunci = kunci_biaya

    def test_model_sama_penyedia_beda_ditagih_masing_masing(self):
        """Inti ketokan owner. Satu juta token masuk & keluar lewat OpenAI langsung = $0,75;
        tiga panggilan lewat router = $0,003. Keduanya di produksi yang sama."""
        pakai = {"llm": {
            self.kunci("openai", "gpt-4o-mini"): {"tokens_in": 1_000_000, "tokens_out": 1_000_000,
                                                  "calls": 2},
            self.kunci("apimaster", "gpt-4o-mini"): {"tokens_in": 500_000, "tokens_out": 500_000,
                                                     "calls": 3},
        }}
        h = _hitung(pakai)
        self.assertEqual(h["unpriced"], [], f"salah satu penyedia tak terhitung: {h}")
        self.assertAlmostEqual(h["usd"], 0.15 + 0.6 + 3 * 0.001, places=6,
                               msg=f"biaya tertukar antar penyedia: {h}")

    def test_formula_ikut_penyedia(self):
        """Model yang sama bisa ditagih per TOKEN oleh vendor langsung dan per PANGGILAN oleh
        agregator. Formula wajib mengikuti barisnya, bukan namanya."""
        h_langsung = _hitung({"llm": {self.kunci("openai", "gpt-4o-mini"):
                                     {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 9}}})
        self.assertAlmostEqual(h_langsung["usd"], 0.15, places=6,
                               msg=f"baris langsung tak memakai formula token: {h_langsung}")
        h_router = _hitung({"llm": {self.kunci("apimaster", "gpt-4o-mini"):
                                    {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 9}}})
        self.assertAlmostEqual(h_router["usd"], 9 * 0.001, places=6,
                               msg=f"baris router tak memakai formula per-panggilan: {h_router}")

    def test_nama_polos_yang_AMBIGU_dilaporkan_jujur(self):
        """Catatan tanpa penyedia pada nama yang dipakai DUA baris = mustahil ditentukan. Menebak
        salah satunya berarti biaya tenant bisa 150x salah — lebih baik mengaku belum terhitung."""
        h = _hitung({"llm": {"gpt-4o-mini": {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 1}}})
        self.assertIn("gpt-4o-mini", h["unpriced"],
                      f"nama ambigu DITEBAK alih-alih dilaporkan: {h}")
        self.assertEqual(h["usd"], 0.0, "angka ditebak dari salah satu penyedia")

    def test_catatan_lama_tanpa_penyedia_tetap_terhitung(self):
        """Nol regresi: 246 produksi riwayat memakai nama polos. Selama namanya TIDAK ambigu,
        ia wajib tetap terhitung seperti sebelumnya."""
        satu = [BARIS_TABRAKAN[0]]          # hanya satu baris → nama tidak ambigu
        h = _hitung({"llm": {"gpt-4o-mini": {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 1}}},
                    rows=satu)
        self.assertEqual(h["unpriced"], [], f"riwayat lama jadi tak terhitung — REGRESI: {h}")
        self.assertAlmostEqual(h["usd"], 0.15, places=6)

    def test_meteran_SUNGGUH_mencatat_penyedia(self):
        """Ditemukan lewat SABOTASE: melumpuhkan penyusun kunci di meteran (kembali mencatat nama
        model saja) LOLOS seluruh uji lain — sebab uji-uji itu menyusun catatannya sendiri. Yang
        dijaga di sini: meteran yang SUNGGUH dipakai produksi memang menuliskan penyedianya."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_llm("gpt-4o-mini", 10, 5, penyedia="openai")
        cost_meter.add_llm("gpt-4o-mini", 10, 5, penyedia="apimaster")
        cost_meter.add_tts("m-suara", 100, penyedia="elevenlabs")
        cost_meter.add_image("m-gambar", 2, penyedia="fal")
        ring = cost_meter.summary()
        self.assertIn(self.kunci("openai", "gpt-4o-mini"), ring.get("llm") or {},
                      f"meteran tidak mencatat penyedia: {ring.get('llm')}")
        self.assertIn(self.kunci("apimaster", "gpt-4o-mini"), ring.get("llm") or {},
                      "dua penyedia untuk model bernama sama TERGABUNG jadi satu catatan — "
                      "biayanya akan tertukar")
        self.assertEqual(len(ring.get("llm") or {}), 2,
                         f"catatan dua penyedia tidak terpisah: {ring.get('llm')}")
        self.assertIn(self.kunci("elevenlabs", "m-suara"), ring.get("tts") or {})
        self.assertIn(self.kunci("fal", "m-gambar"), ring.get("image") or {})

    def test_meteran_tanpa_penyedia_tetap_mencatat(self):
        """Gagal-aman: pemanggil lama / penyedia kosong tetap tercatat memakai nama model saja
        (perilaku sebelum perubahan) — jangan sampai pencatatan hilang senyap."""
        from src.utils import cost_meter
        cost_meter.reset()
        cost_meter.add_llm("m-lama", 3, 4)
        self.assertIn("m-lama", cost_meter.summary().get("llm") or {},
                      "pencatatan hilang saat penyedia tak disebutkan")

    def test_bentuk_kunci_hidup_di_satu_tempat(self):
        """Meteran tak boleh menyusun sendiri bentuk kuncinya — dua tempat = dua bentuk, dan
        biaya berhenti ketemu harganya (kelas cacat 'pengetahuan tersebar')."""
        isi = open(os.path.join(AKAR, "src/utils/cost_meter.py"), encoding="utf-8").read()
        self.assertIn("kunci_biaya", isi,
                      "meteran tidak memakai penyusun kunci bersama")
        import re
        tanpa_komentar = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("#"))
        self.assertNotRegex(tanpa_komentar, r'f"\{[^}]*\}\|\{',
                            "meteran menyusun sendiri bentuk kunci (dua sumber kebenaran)")

    def test_setiap_pencatat_menyerahkan_penyedianya(self):
        """Satu titik yang lupa = celah kembali, dan kembalinya senyap."""
        berkas = ("src/providers/llm/adapters.py", "src/providers/visual/ai_image.py",
                  "src/providers/visual/ai_video.py", "src/production/tts_engine.py",
                  "src/providers/tts/gemini_tts.py")
        lupa = []
        for rel in berkas:
            pohon = ast.parse(open(os.path.join(AKAR, rel), encoding="utf-8").read())
            for n in ast.walk(pohon):
                if not isinstance(n, ast.Call):
                    continue
                nama = getattr(n.func, "attr", "")
                if not nama.startswith("add_") or nama == "add_":
                    continue
                if not any(kw.arg == "penyedia" for kw in n.keywords):
                    lupa.append(f"{rel}:{n.lineno} {nama}")
        self.assertFalse(lupa,
                         "titik pencatat biaya TIDAK menyerahkan penyedianya — biaya bisa "
                         "tertukar begitu dua penyedia melayani model bernama sama:\n"
                         + "\n".join(f"  · {x}" for x in lupa))


class TestSinkronTakMempercayaiJawabanYangTakTerbukti(unittest.TestCase):
    """PENJAGA C — sinkron harga berhenti mempercayai "200 OK".

    TEMUAN 24-Agu, diuji ke API nyata: **API harga fal menjawab HTTP 200 untuk endpoint yang TIDAK
    ADA.** Nama karangan `fal-ai/veo3.1/fast/audio-off` dijawab *"0,00017 per compute seconds"* —
    tarif GPU bawaannya. Artinya "200 OK" **bukan bukti modelnya ada**: satu salah ketik pada
    penanda model bisa membuat kita menulis harga yang tampak wajar untuk model yang tak pernah ada.

    Hari ini kita selamat hanya karena satuan "compute seconds" tak kita kenali sehingga ditolak —
    **bukan karena kita memeriksanya.** Keselamatan yang bergantung kebetulan bukan keselamatan.

    Penutupnya bukan menebak-nebak nama, tapi aturan yang lebih tegas: **harga tidak ditulis untuk
    model yang belum pernah lulus tombol Uji.** Model yang belum terbukti ada, harganya tak bermakna.
    Terukur saat dipasang: 42 baris aktif SEMUANYA sudah lulus uji ⇒ nol baris kehilangan
    pemutakhiran; 5 baris yang belum lulus semuanya NONAKTIF (tak terlihat tenant)."""

    def _rows(self, audit):
        return [{"model_key": "m-baru", "model_id": "m-baru", "component": "llm",
                 "provider_key": "openai", "pricing": {"in_per_1m": 1.0},
                 "pricing_locked": False, "pricing_pending": None, "default_params": {},
                 "cost_hint": ({"audit": audit} if audit else {})}]

    def _jalankan(self, rows):
        """Sinkron hermetik: umpan memuat harga BARU untuk baris itu."""
        from unittest.mock import patch as _p
        import src.billing.price_sync as ps
        tulis = []

        class _T:
            def __init__(s, r):
                s._r, s._patch, s._key = r, None, None

            def select(s, *a, **k):
                return s

            def update(s, patch):
                s._patch = patch
                return s

            def upsert(s, *a, **k):
                return s

            def eq(s, _k, v):
                s._key = v
                return s

            def execute(s):
                if s._patch is not None:
                    tulis.append((s._key, s._patch))
                    s._patch = None
                    return type("R", (), {"data": []})()
                return type("R", (), {"data": s._r})()

        class _SBs:
            def table(s, nama):
                if nama == "ai_models":
                    return _T(rows)
                if nama == "ai_providers":
                    return _T([{"provider_key": "openai", "price_feed_prefix": None,
                                "price_api_url": None, "key_group": "openai"}])
                return _T([])

        # 2x dari harga lama (1.0 -> 2.0): di bawah ambang penjaga lonjakan (3x) supaya yang
        # diuji di sini benar-benar aturan "lulus uji", bukan penjaga lonjakan.
        umpan = {"m-baru": {"input_cost_per_token": 2e-06}}
        with _p.object(ps, "requests") as rq, \
             _p.object(ps, "_notify_admin", lambda *a, **k: None), \
             _p.object(ps, "_state_set_epoch", lambda *a, **k: None), \
             _p.object(ps, "_state_get_epoch", lambda *a, **k: 0):
            rq.get.return_value = type("R", (), {"json": lambda s=None: umpan})()
            ringkas = ps.sync_prices(sb=_SBs(), force=True)
        return ringkas, dict(tulis)

    def test_model_yang_belum_lulus_uji_tak_ditulis_harganya(self):
        _, tulis = self._jalankan(self._rows("GAGAL uji manual admin 2026-08-17: ..."))
        self.assertNotIn("m-baru", tulis,
                         "harga ditulis untuk model yang GAGAL uji — model yang belum terbukti ada, "
                         "harganya tak bermakna, dan 200-OK bukan bukti ia ada")

    def test_model_tanpa_stempel_uji_tak_ditulis_harganya(self):
        _, tulis = self._jalankan(self._rows(None))
        self.assertNotIn("m-baru", tulis,
                         "harga ditulis untuk model yang belum pernah diuji")

    def test_model_yang_LULUS_uji_tetap_dimutakhirkan(self):
        """Kebalikannya wajib ikut dijaga — kalau tidak, perbaikan ini mematikan sinkron."""
        _, tulis = self._jalankan(self._rows("LULUS uji manual admin 2026-08-23 10:00"))
        self.assertIn("m-baru", tulis,
                      "model yang sudah lulus uji BERHENTI dimutakhirkan — itu regresi")
        self.assertAlmostEqual((tulis["m-baru"]["pricing"] or {}).get("in_per_1m"), 2.0, places=6)

    def test_satuan_vendor_yang_tak_dikenal_DILAPORKAN_bukan_cuma_dicatat_log(self):
        """Vendor mengganti cara tagih = kejadian yang WAJIB terlihat: harga barisnya berhenti
        dimutakhirkan, dan kalau hanya tercatat di log, tak seorang pun membacanya. Terbukti nyata:
        API fal menjawab satuan `compute seconds` untuk endpoint yang tak ada."""
        from unittest.mock import patch as _p
        import src.billing.price_sync as ps
        rows = self._rows("LULUS uji manual admin 2026-08-23 10:00")
        pesan = []

        class _T:
            def __init__(s, r):
                s._r, s._patch = r, None

            def select(s, *a, **k):
                return s

            def update(s, patch):
                s._patch = patch
                return s

            def upsert(s, *a, **k):
                return s

            def eq(s, *a, **k):
                return s

            def execute(s):
                s._patch = None
                return type("R", (), {"data": s._r})()

        class _SBs:
            def table(s, nama):
                if nama == "ai_models":
                    return _T(rows)
                if nama == "ai_providers":
                    return _T([{"provider_key": "openai", "price_feed_prefix": None,
                                "price_api_url": "https://contoh.uji/{model_id}",
                                "key_group": "openai"}])
                return _T([])

        with _p.object(ps, "requests") as rq, \
             _p.object(ps, "_kunci_platform", lambda *a, **k: "kunci-uji"), \
             _p.object(ps, "_harga_vendor", lambda *a, **k: ("compute seconds", 0.00017)), \
             _p.object(ps, "VENDOR_API_DELAY", 0.0), \
             _p.object(ps, "_notify_admin", lambda t: pesan.append(t)), \
             _p.object(ps, "_state_set_epoch", lambda *a, **k: None), \
             _p.object(ps, "_state_get_epoch", lambda *a, **k: 0):
            rq.get.return_value = type("R", (), {"json": lambda s=None: {}})()
            ringkas = ps.sync_prices(sb=_SBs(), force=True)
        self.assertTrue(ringkas.get("satuan_asing"),
                        f"satuan vendor tak dikenal tidak dilaporkan di ringkasan: {ringkas}")
        self.assertTrue(any("compute seconds" in p for p in pesan),
                        f"satuan tak dikenal hanya masuk log, tak dialarmkan: {pesan}")
