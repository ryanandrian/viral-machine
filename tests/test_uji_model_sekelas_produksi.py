"""PENJAGA F6 — tombol Uji HARAM meluluskan model yang pasti gagal di produksi.

TEMUAN 23-Agu (terukur, bukan dugaan). Uji naskah memanggil vendor dengan
`user="Reply with exactly one word: OK"`, `max_tokens=512`, **tanpa `as_json`**. Produksi memanggil
hal yang sangat berbeda: `as_json=True` dengan jatah **1.200–2.000** token, dan hasilnya WAJIB bisa
diurai jadi JSON. Bedanya bukan teori: **4 dari 6 model APIMaster LULUS panggilan pendek lalu GAGAL
pada perintah naskah sesungguhnya** — jawabannya terpotong di batas keluaran, JSON-nya gugur.

Akibatnya lencana **"✓ Teruji"** di panel bisa BOHONG, dan gerbang DB `trg_gate_aktif_terbukti`
(migr 0208) yang menolak menyalakan model tanpa audit LULUS jadi ikut tertipu — ia menegakkan stempel
yang isinya tak sepadan. Tenant yang memilih model itu menabrak dinding di produksi pertamanya.

Yang dijaga di sini adalah PERILAKU, bukan teks:
  1. balasan yang tak bisa dipakai produksi (JSON terpotong) → uji WAJIB memvonis GAGAL
  2. jatah token uji HARAM lebih kecil dari jatah TERBESAR yang produksi pakai — kalau lebih kecil,
     model ber-batas-keluaran-rendah lolos lagi, dan kelas cacat ini kembali
  3. uji naskah WAJIB menuntut JSON (as_json), sebab itulah kontrak yang produksi andalkan
"""
from __future__ import annotations

import ast
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUKSI = "src/intelligence/script_engine.py"
PENGUJI = "src/config/model_tester.py"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


class _Hasil:
    def __init__(self, data):
        self.data = data


class _Tabel:
    """Tiruan tabel Supabase secukupnya untuk jalur `test_model` (tanpa jaringan)."""

    def __init__(self, rows, tulis):
        self._rows, self._tulis = rows, tulis
        self._patch = None
        self._tunggal = False

    def select(self, *a, **k):
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def single(self):
        self._tunggal = True          # `.single()` mengembalikan SATU baris (dict), bukan daftar
        return self

    def execute(self):
        if self._patch is not None:
            self._tulis.append(self._patch)
            self._patch = None
            return _Hasil([])
        if self._tunggal:
            self._tunggal = False
            return _Hasil(self._rows[0] if self._rows else None)
        return _Hasil(self._rows)


class _SB:
    def __init__(self, tulis):
        self._tulis = tulis

    def table(self, nama):
        if nama == "ai_models":
            return _Tabel([{"model_key": "m-uji", "model_id": "m-uji", "component": "llm",
                            "provider_key": "penyedia-uji", "default_params": {},
                            "cost_hint": {}}], self._tulis)
        if nama == "ai_providers":
            return _Tabel([{"auth_type": "none", "is_active": True, "key_group": "penyedia-uji"}],
                          self._tulis)
        return _Tabel([], self._tulis)


class _Penyedia:
    """Vendor tiruan: mengembalikan apa pun yang uji ini tentukan."""

    def __init__(self, balasan):
        self._balasan = balasan
        self.terpakai = {}

    def complete(self, **kw):
        self.terpakai = kw
        if isinstance(self._balasan, Exception):
            raise self._balasan
        return self._balasan


def _jalankan_uji(balasan):
    from src.config import model_tester
    tulis: list = []
    penyedia = _Penyedia(balasan)
    with patch.object(model_tester, "_service_sb", lambda: _SB(tulis)), \
         patch("src.providers.llm.build_llm_provider", lambda cfg: penyedia):
        hasil = model_tester.test_model("m-uji")
    return hasil, penyedia, tulis


class TestUjiNaskahSekelasProduksi(unittest.TestCase):

    def test_balasan_terpotong_divonis_GAGAL(self):
        """Ini persis kegagalan 4 model APIMaster: JSON terpotong di batas keluaran.
        Balasan begini MUSTAHIL dipakai produksi ⇒ meluluskannya = lencana yang berbohong."""
        hasil, _, tulis = _jalankan_uji('{"text": "Sebuah naskah yang panjang dan belum sele')
        self.assertFalse(hasil.get("ok"),
                         f"balasan JSON TERPOTONG diluluskan → lencana '✓ Teruji' berbohong: {hasil}")
        self.assertTrue(any("GAGAL" in str(p.get("cost_hint", {}).get("audit", "")) for p in tulis),
                        "vonis gagal tak tercap ke jejak audit → gerbang aktivasi tetap tertipu")

    def test_balasan_bukan_JSON_divonis_GAGAL(self):
        """Model yang menjawab prosa walau diminta JSON akan menggugurkan naskah di produksi."""
        hasil, _, _ = _jalankan_uji("Tentu! Berikut naskahnya: sebuah pagi yang tenang...")
        self.assertFalse(hasil.get("ok"),
                         f"balasan non-JSON diluluskan padahal produksi menuntut JSON: {hasil}")

    def test_JSON_sah_tapi_tanpa_kunci_yang_produksi_baca_divonis_GAGAL(self):
        """Ditemukan lewat SABOTASE (23-Agu): JSON yang sah tapi tak memuat kunci yang dibaca
        produksi tetap diluluskan. Model begitu jalan mulus di uji lalu menghasilkan naskah KOSONG
        di produksi — kelas kegagalan yang sama, hanya bentuknya lain."""
        hasil, _, _ = _jalankan_uji('{"judul": "Pagi di pasar", "catatan": "siap"}')
        self.assertFalse(hasil.get("ok"),
                         f"JSON tanpa kunci yang produksi baca diluluskan → naskah kosong di "
                         f"produksi: {hasil}")

    def test_balasan_sekelas_produksi_LULUS(self):
        """Kebalikannya wajib ikut dijaga: uji yang jadi terlalu ketat akan memblokir model yang
        SEHAT — itu 'kunci tanpa jalur buka', dan owner sudah menegurnya sekali."""
        hasil, _, _ = _jalankan_uji('{"text": "' + ("kata " * 90).strip() + '"}')
        self.assertTrue(hasil.get("ok"),
                        f"model yang menjawab benar malah divonis gagal: {hasil}")

    def test_uji_menuntut_JSON_seperti_produksi(self):
        _, penyedia, _ = _jalankan_uji('{"text": "cukup"}')
        self.assertTrue(penyedia.terpakai.get("as_json"),
                        "uji naskah tidak menuntut JSON, padahal seluruh jalur naskah produksi "
                        "memanggil dengan as_json=True → yang diuji bukan kontrak yang dipakai")

    def test_jatah_token_uji_tak_lebih_kecil_dari_produksi(self):
        """Anti-melemah: jatah uji dibaca dari kenop, tapi BAWAANNYA tak boleh di bawah jatah
        TERBESAR yang produksi pakai. Angka produksi dibaca dari kodenya (AST), bukan dihafal —
        kalau produksi naik, penjaga ini ikut naik sendiri."""
        pohon = ast.parse(_isi(PRODUKSI))
        jatah_produksi = [kw.value.value for n in ast.walk(pohon) if isinstance(n, ast.Call)
                          for kw in n.keywords
                          if kw.arg == "max_tokens" and isinstance(kw.value, ast.Constant)
                          and isinstance(kw.value.value, int)]
        self.assertTrue(jatah_produksi, "tak satu pun jatah token produksi terbaca — periksa jangkar")
        terbesar = max(jatah_produksi)

        _, penyedia, _ = _jalankan_uji('{"text": "cukup"}')
        dipakai = penyedia.terpakai.get("max_tokens")
        self.assertIsInstance(dipakai, int, "uji naskah tak menyebut jatah token")
        self.assertGreaterEqual(
            dipakai, terbesar,
            f"jatah token uji ({dipakai}) LEBIH KECIL dari jatah terbesar produksi ({terbesar}) ⇒ "
            f"model yang batas keluarannya rendah akan LULUS uji lalu GAGAL di produksi — persis "
            f"kegagalan 4 model APIMaster 23-Agu")

    def test_kenop_jatah_uji_bisa_diatur_admin(self):
        """Nilai bisnis dari config, bukan literal (§3). Bawaan kode = jaring pengaman saja."""
        isi = _isi(PENGUJI)
        self.assertRegex(isi, r"ambang\.angka\(\s*[\"']uji_model_max_tokens[\"']",
                         "jatah token uji ditanam sebagai angka mati — tak bisa diatur tanpa deploy")
