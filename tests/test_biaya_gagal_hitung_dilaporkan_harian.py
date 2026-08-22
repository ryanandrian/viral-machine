"""Kegagalan menghitung biaya AI WAJIB dilaporkan — mesin tak boleh menunggu manusia curiga.

MASALAH YANG DIJAGA (dilaporkan owner 2026-08-22)
Mesin biaya SUDAH mencatat, pada tiap produksi, model mana yang gagal ia hitung (`cost.unpriced` di
`run_metadata`). Tapi **nol pembaca**: satu-satunya tempat ia muncul = tanda kecil di kolom Biaya AI
layar tenant. Akibatnya `gemini-2.5-flash-preview-tts` melaporkan biaya suara Rp 0 selama **16
produksi / 4 channel aktif** tanpa seorang pun tahu — termasuk saya, yang membangunnya.

KENAPA BERBASIS BUKTI PRODUKSI, BUKAN ATURAN PER-JENIS
Vendor berikutnya bisa datang dengan satuan tagihan yang belum ada hari ini; daftar aturan
"jenis A pakai satuan B" PASTI tertinggal, dan hasilnya nol senyap yang sama. Yang tak bisa
tertinggal: produksi NYATA yang gagal dihitung. Jadi pemicunya = bukti, bukan teori — otomatis
berlaku untuk keempat jenis, vendor apa pun, satuan apa pun. Nol alarm palsu: hanya menyala bila
uang nyata sudah tak terhitung.
"""
import ast
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.billing.price_sync as ps   # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Q:
    """Peniru rantai kueri supabase: .select().gte().execute()"""
    def __init__(self, rows, dipakai): self._rows, self._dipakai = rows, dipakai
    def select(self, *a, **k): return self
    def gte(self, *a, **k): self._dipakai["gte"] = a; return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return type("R", (), {"data": self._rows})()


class _SB:
    def __init__(self, runs, state=None):
        self.runs, self.state, self.tabel_dibaca, self.dipakai = runs, state or {}, [], {}
    def table(self, nama):
        self.tabel_dibaca.append(nama)
        if nama == "production_runs":
            return _Q(self.runs, self.dipakai)
        if nama == "system_state":
            return _Q([{"value": self.state[k]} for k in self.state] or [], self.dipakai)
        return _Q([], self.dipakai)


def _run(unpriced_list):
    return {"run_metadata": {"cost": {"usd": 0.3, "unpriced": unpriced_list}}}


class TestAlarmBerbasisBuktiProduksi(unittest.TestCase):

    def test_model_gagal_dihitung_dilaporkan_dengan_namanya(self):
        sb = _SB([_run(["gemini-2.5-flash-preview-tts"]), _run(["gemini-2.5-flash-preview-tts"])])
        with patch.object(ps, "_notify_admin") as alarm, \
             patch.object(ps, "_state_get_epoch", return_value=0), \
             patch.object(ps, "_state_set_epoch"):
            ps.report_unpriced_models(sb)
        alarm.assert_called_once()
        teks = alarm.call_args[0][0]
        self.assertIn("gemini-2.5-flash-preview-tts", teks, "nama model tak disebut → alarm tak bisa ditindak")
        self.assertIn("2", teks, "jumlah produksi terdampak tak disebut")

    def test_tak_ada_kegagalan_maka_diam(self):
        sb = _SB([_run([]), {"run_metadata": {"cost": {"usd": 1.0}}}, {"run_metadata": None}])
        with patch.object(ps, "_notify_admin") as alarm, \
             patch.object(ps, "_state_get_epoch", return_value=0), \
             patch.object(ps, "_state_set_epoch"):
            ps.report_unpriced_models(sb)
        alarm.assert_not_called()

    def test_tak_membanjiri_sekali_sehari(self):
        sb = _SB([_run(["m"])])
        import time as _t
        with patch.object(ps, "_notify_admin") as alarm, \
             patch.object(ps, "_state_get_epoch", return_value=int(_t.time()) - 3600), \
             patch.object(ps, "_state_set_epoch"):
            ps.report_unpriced_models(sb)
        alarm.assert_not_called()

    def test_bukti_dibaca_dari_produksi_bukan_katalog(self):
        """Implementasi berbasis TEORI katalog akan membaca ai_models — itu yang pasti tertinggal."""
        sb = _SB([_run(["m"])])
        with patch.object(ps, "_notify_admin"), patch.object(ps, "_state_get_epoch", return_value=0), \
             patch.object(ps, "_state_set_epoch"):
            ps.report_unpriced_models(sb)
        self.assertIn("production_runs", sb.tabel_dibaca,
                      "bukti tak dibaca dari produksi nyata")
        self.assertNotIn("ai_models", sb.tabel_dibaca,
                         "alarm dibangun dari teori katalog, bukan bukti produksi")

    def test_jendela_waktu_dibatasi(self):
        """Tanpa batas waktu, alarm akan menyebut model yang sudah lama diperbaiki."""
        sb = _SB([_run(["m"])])
        with patch.object(ps, "_notify_admin"), patch.object(ps, "_state_get_epoch", return_value=0), \
             patch.object(ps, "_state_set_epoch"):
            ps.report_unpriced_models(sb)
        self.assertIn("gte", sb.dipakai, "kueri tak dibatasi rentang waktu")

    def test_gagal_lunak_tak_menggagalkan_pemanggil(self):
        class _Rusak:
            def table(self, *a): raise RuntimeError("DB mati")
        with patch.object(ps, "_notify_admin"):
            ps.report_unpriced_models(_Rusak())   # tak boleh melempar


class TestDijalankanHarian(unittest.TestCase):
    """AST: penjaga teks lolos bila panggilannya dikomentari."""

    def test_petugas_harian_memanggilnya(self):
        with open(os.path.join(AKAR, "src/orchestrator/buffer_janitor.py"), encoding="utf-8") as f:
            pohon = ast.parse(f.read())
        panggilan = [n for n in ast.walk(pohon)
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "id", getattr(n.func, "attr", "")) == "report_unpriced_models"]
        self.assertEqual(len(panggilan), 1,
                         "laporan kegagalan hitung biaya tidak dijalankan harian → kembali senyap")


if __name__ == "__main__":
    unittest.main()
