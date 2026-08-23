"""Biaya AI yang TAK BISA DIHITUNG haram dilaporkan NOL secara senyap — untuk KEEMPAT jenis model.

MASALAH YANG DIJAGA (dilaporkan owner 2026-08-22)
`gemini-2.5-flash-preview-tts` (4 channel AKTIF) — biaya suaranya dilaporkan **Rp 0** selama 16
produksi. Sebabnya BUKAN angka salah: Google menagih model itu **per token**, umpan harga mencatatnya
apa adanya (`in_per_1m`/`out_per_1m`), sedangkan penghitung biaya kita hanya mengenal SATU satuan
untuk suara — per sejuta huruf. Satuan itu kosong → biaya nol.

Kelas kegagalan yang sama SUDAH ditemukan & ditutup untuk GAMBAR (`gpt-image-1` per-token → tokennya
dihitung di keranjang naskah), dan pertanyaan yang sama TIDAK ditanyakan untuk suara. Uji ini
menanyakannya untuk **keempat** jenis sekaligus, supaya jenis/vendor berikutnya tak lolos lagi.

YANG DIJAGA (perilaku penghitung, bukan angka tertentu):
  1. suara ber-tagih token: token vendor tercatat → biaya TERHITUNG (bukan "tanpa harga")
  2. suara ber-tagih token TANPA hitungan token dari vendor → JUJUR masuk daftar tanpa-harga
  3. suara ber-harga per-huruf → perilaku LAMA, tak bergeser sedikit pun (nol regresi)
  4. haram terhitung DUA KALI (huruf + token untuk model yang sama)
  5. keempat jenis punya jalur hitung yang hidup: naskah · suara · gambar · video
  6. keranjang meter baru WAJIB ikut di-reset — keranjang tak dikenal = pencatatan hilang SENYAP
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing import ai_cost          # noqa: E402
from src.utils import cost_meter         # noqa: E402

# Harga contoh: bentuknya yang penting, bukan angkanya.
HARGA = {
    "suara-token":  {"in_per_1m": 0.3,  "out_per_1m": 2.5},          # Gemini TTS: token saja
    "suara-huruf":  {"per_1m_chars": 50},                            # ElevenLabs: per huruf
    "naskah":       {"in_per_1m": 1.0,  "out_per_1m": 2.0},
    "naskah-panggil": {"per_request_usd": 0.001},
    "gambar":       {"per_image": 0.01},
    "video-detik":  {"per_second_usd": 0.05},
    "video-klip":   {"per_video_base_usd": 0.35, "base_seconds": 5, "per_extra_second_usd": 0.07},
}


# [F2, 23-Agu] Formula dinyatakan TEGAS — jangan biarkan `_formula_map` menembak database nyata:
# hasil uji akan bergantung urutan jalannya (lihat catatan di test_ai_cost_per_request.py).
FORMULA = {"suara-token": "suara_token", "suara-huruf": "suara_huruf", "naskah": "naskah_token",
           "naskah-panggil": "naskah_panggilan", "gambar": "gambar_satuan",
           "video-detik": "video_detik", "video-klip": "video_klip", "model-asing": "naskah_token"}


def _hitung(usage: dict) -> dict:
    with patch.object(ai_cost, "_pricing_map", return_value=HARGA), \
         patch.object(ai_cost, "_formula_map", return_value=FORMULA):
        return ai_cost.compute_cost_usd(usage) or {}


class TestSuaraBerTagihToken(unittest.TestCase):

    def test_token_vendor_tercatat_maka_biaya_terhitung(self):
        """(1) Kasus produksi yang selama ini nol."""
        h = _hitung({"tts": {"suara-token": 2309},
                     "tts_tokens": {"suara-token": {"tokens_in": 600, "tokens_out": 2250}}})
        self.assertNotIn("suara-token", h.get("unpriced", []),
                         "model suara ber-tagih token masih dilabeli 'tanpa harga' padahal tokennya tercatat")
        self.assertGreater(h["breakdown"]["tts"], 0,
                           "biaya suara masih NOL padahal token vendor + harga token tersedia")
        # Angka = token × harga token (600×0.3 + 2250×2.5) / 1e6
        self.assertAlmostEqual(h["breakdown"]["tts"], (600 * 0.3 + 2250 * 2.5) / 1e6, places=9)

    def test_tanpa_hitungan_token_tetap_jujur(self):
        """(2) Vendor tak mengirim hitungan → JANGAN mengarang; laporkan tanpa-harga."""
        h = _hitung({"tts": {"suara-token": 2309}})
        self.assertIn("suara-token", h.get("unpriced", []),
                      "biaya suara tak bisa dihitung tapi TIDAK dilaporkan — ini nol senyap")
        self.assertEqual(h["breakdown"]["tts"], 0.0)

    def test_harga_per_huruf_tak_bergeser(self):
        """(3) Nol regresi pada jalur yang sudah benar."""
        h = _hitung({"tts": {"suara-huruf": 1_000_000}})
        self.assertEqual(h["breakdown"]["tts"], 50.0)
        self.assertEqual(h.get("unpriced", []), [])

    def test_haram_terhitung_dua_kali(self):
        """(4) Model ber-harga per-huruf yang tokennya JUGA tercatat → huruf saja, sekali."""
        h = _hitung({"tts": {"suara-huruf": 1_000_000},
                     "tts_tokens": {"suara-huruf": {"tokens_in": 999_999, "tokens_out": 999_999}}})
        self.assertEqual(h["breakdown"]["tts"], 50.0,
                         "biaya suara terhitung DUA KALI (huruf + token)")


class TestKeempatJenisPunyaJalurHidup(unittest.TestCase):
    """(5) Sekali jalan untuk naskah · suara · gambar · video — tiap satuan yang didukung."""

    def test_semua_satuan_menghasilkan_biaya(self):
        kasus = [
            ("naskah token",   {"llm": {"naskah": {"tokens_in": 1_000_000, "tokens_out": 0, "calls": 1}}}, "llm"),
            ("naskah panggil", {"llm": {"naskah-panggil": {"tokens_in": 0, "tokens_out": 0, "calls": 3}}}, "llm"),
            ("suara huruf",    {"tts": {"suara-huruf": 1_000_000}}, "tts"),
            ("suara token",    {"tts": {"suara-token": 100},
                                "tts_tokens": {"suara-token": {"tokens_in": 1_000_000, "tokens_out": 0}}}, "tts"),
            ("gambar",         {"image": {"gambar": 5}}, "image"),
            ("video detik",    {"video": {"video-detik": {"seconds": 8, "clips": 1}}}, "video"),
            ("video klip",     {"video": {"video-klip": {"seconds": 8, "clips": 1}}}, "video"),
        ]
        for nama, usage, keranjang in kasus:
            with self.subTest(nama):
                h = _hitung(usage)
                self.assertEqual(h.get("unpriced", []), [], f"{nama}: dilabeli tanpa-harga")
                self.assertGreater(h["breakdown"][keranjang], 0, f"{nama}: biaya NOL")

    def test_model_tak_dikenal_selalu_dilaporkan(self):
        """Jenis apa pun: harga tak ada → WAJIB muncul di daftar, bukan hilang."""
        for keranjang, pakai in (("llm", {"tokens_in": 10, "tokens_out": 10, "calls": 1}),
                                 ("tts", 100), ("image", 1),
                                 ("video", {"seconds": 5, "clips": 1})):
            with self.subTest(keranjang):
                h = _hitung({keranjang: {"model-asing": pakai}})
                self.assertIn("model-asing", h.get("unpriced", []),
                              f"{keranjang}: model tanpa harga TIDAK dilaporkan → nol senyap")


class TestKeranjangMeterBaruIkutDireset(unittest.TestCase):
    """(6) `_bucket()` mengembalikan None untuk keranjang tak dikenal → add_* jadi no-op SENYAP.
    Keranjang yang lupa didaftarkan di reset() = pencatatan hilang tanpa jejak."""

    def test_pencatat_token_suara_benar_benar_merekam(self):
        cost_meter.reset()
        cost_meter.add_tts_tokens("suara-token", 600, 2250)
        s = cost_meter.summary()
        self.assertIn("tts_tokens", s,
                      "keranjang token suara tak ikut di-reset → pencatatan hilang senyap")
        self.assertEqual(s["tts_tokens"]["suara-token"], {"tokens_in": 600, "tokens_out": 2250})

    def test_menumpuk_antar_panggilan(self):
        cost_meter.reset()
        cost_meter.add_tts_tokens("m", 10, 20)
        cost_meter.add_tts_tokens("m", 5, 7)
        self.assertEqual(cost_meter.summary()["tts_tokens"]["m"], {"tokens_in": 15, "tokens_out": 27})

    def test_meter_mati_tak_meledak(self):
        """Thread tanpa reset() (mis. publisher) → no-op, bukan galat."""
        import threading
        hasil = {}
        def kerja():
            try:
                cost_meter.add_tts_tokens("m", 1, 1)
                hasil["ok"] = True
            except Exception as e:
                hasil["ok"] = f"meledak: {e}"
        t = threading.Thread(target=kerja); t.start(); t.join()
        self.assertIs(hasil.get("ok"), True)


class TestMesinSuaraGeminiMencatatTokenVendor(unittest.TestCase):
    """Hitungan token diambil dari BALASAN vendor (usageMetadata), bukan ditaksir dari huruf."""

    def _sumber(self) -> str:
        import inspect
        from src.providers.tts import gemini_tts
        return inspect.getsource(gemini_tts)

    def test_membaca_usageMetadata(self):
        s = self._sumber()
        self.assertIn("usageMetadata", s,
                      "mesin suara Gemini tak membaca hitungan token vendor")
        self.assertIn("candidatesTokenCount", s, "token keluaran (audio) tak dibaca")
        self.assertIn("promptTokenCount", s, "token masukan (teks) tak dibaca")

    def test_memanggil_pencatat_token_suara(self):
        """AST: penjaga berbasis teks lolos saat panggilannya dikomentari."""
        import ast
        panggilan = [n for n in ast.walk(ast.parse(self._sumber()))
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "attr", "") == "add_tts_tokens"]
        self.assertEqual(len(panggilan), 1,
                         "add_tts_tokens tidak dipanggil mesin suara Gemini (atau dipanggil ganda)")

    def test_tak_menaksir_token_dari_panjang_teks(self):
        """Menaksir = mengarang angka. Haram."""
        import ast, re
        s = self._sumber()
        i = s.index("add_tts_tokens")
        blok = s[max(0, i - 400):i + 200]
        self.assertNotRegex(blok, r"len\(text\)\s*[/*]",
                            "token ditaksir dari panjang teks — itu angka karangan")


if __name__ == "__main__":
    unittest.main()
