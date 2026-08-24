"""PENJAGA F8 — biaya yang salah TANPA mesin menyadarinya wajib punya alarm.

BEDA DENGAN ALARM YANG SUDAH ADA. `report_unpriced_models` (22-Agu) melapor bila penghitung
**tahu** ia gagal (`cost.unpriced` terisi). Yang TIDAK tertangkap: kasus penghitung **tidak tahu** —
angkanya keluar, tampak wajar, dan nol alarm menyala. Itu persis bentuk insiden 22-Agu: biaya suara
4 channel aktif dilaporkan Rp 0 selama **16 produksi** sementara seluruh mesin diam, sebab dari sisi
penghitung tak ada yang "gagal".

Dua tanda yang bisa diperiksa tanpa satu pun panggilan ke vendor, dan keduanya BERARTI uang nyata
tak tertagih:
  (a) ada PANGGILAN tercatat tapi token nol ⇒ vendor berhenti melaporkan pemakaian, dan kita
      menagih 0 untuk panggilan yang sungguh terjadi
  (b) ada pemakaian, biaya total 0, dan daftar "belum terhitung" KOSONG ⇒ nol senyap sejati

Keduanya **nol pada 246 produksi hari ini** (diukur 23-Agu) — jadi alarm ini tidak berisik hari ini;
nilainya = menangkap REGRESI kelas itu, bukan memperbaiki angka hari ini.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Hasil:
    def __init__(self, data):
        self.data = data


class _Tabel:
    def __init__(self, rows, tulis):
        self._rows, self._tulis = rows, tulis
        self._patch = None

    def select(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, patch, *a, **k):
        self._patch = patch
        return self

    def execute(self):
        if self._patch is not None:
            self._tulis.append(self._patch)
            self._patch = None
            return _Hasil([])
        return _Hasil(self._rows)


class _SB:
    def __init__(self, runs, tulis, state=None):
        self._runs, self._tulis, self._state = runs, tulis, state or []

    def table(self, nama):
        if nama == "production_runs":
            return _Tabel(self._runs, self._tulis)
        if nama == "system_state":
            return _Tabel(self._state, self._tulis)
        return _Tabel([], self._tulis)


def _jalankan(runs):
    """Jalankan rekonsiliasi hermetik; kembalikan (ringkasan, pesan-alarm)."""
    from src.billing import price_sync
    pesan: list = []
    sb = _SB(runs, [])
    with patch.object(price_sync, "_notify_admin", lambda t: pesan.append(t)), \
         patch.object(price_sync, "_state_get_epoch", lambda *a, **k: 0), \
         patch.object(price_sync, "_state_set_epoch", lambda *a, **k: None):
        ringkas = price_sync.report_rekonsiliasi_biaya(sb=sb)
    return ringkas, pesan


class TestRekonsiliasiBiayaHarian(unittest.TestCase):

    def test_panggilan_tanpa_token_dilaporkan(self):
        """Vendor berhenti mengirim hitungan pemakaian ⇒ kita menagih 0 untuk panggilan nyata."""
        runs = [{"id": 1, "run_metadata": {
            "ai_usage": {"llm": {"m-naskah": {"calls": 12, "tokens_in": 0, "tokens_out": 0}}},
            "cost": {"usd": 0.0, "unpriced": []}}}]
        ringkas, pesan = _jalankan(runs)
        self.assertIn("m-naskah", str(ringkas.get("panggilan_tanpa_token") or {}),
                      f"panggilan tanpa token tidak terdeteksi: {ringkas}")
        self.assertTrue(pesan, "temuan tidak dialarmkan ke admin (senyap = kelas cacat 22-Agu)")
        self.assertIn("m-naskah", pesan[0], "alarm tak menyebut model yang bermasalah")

    def test_biaya_nol_senyap_dilaporkan(self):
        """Pemakaian ADA, biaya 0, dan penghitung TIDAK mengaku gagal — inilah nol senyap sejati."""
        runs = [{"id": 7, "run_metadata": {
            "ai_usage": {"tts": {"m-suara": 1640}},
            "cost": {"usd": 0.0, "unpriced": []}}}]
        ringkas, pesan = _jalankan(runs)
        self.assertEqual(ringkas.get("nol_senyap"), [7], f"nol senyap tak terdeteksi: {ringkas}")
        self.assertTrue(pesan, "nol senyap tidak dialarmkan")

    def test_produksi_sehat_tidak_menimbulkan_alarm(self):
        """Alarm palsu mengajari admin mengabaikan alarm. Vendor GRATIS (biaya 0 yang SAH) dan
        pemakaian bertoken normal tak boleh menyalakan apa pun."""
        runs = [
            {"id": 2, "run_metadata": {
                "ai_usage": {"llm": {"m": {"calls": 4, "tokens_in": 900, "tokens_out": 400}}},
                "cost": {"usd": 0.0123, "unpriced": []}}},
            # biaya 0 TAPI penghitung mengaku ada yang belum terhitung → sudah ada alarmnya sendiri
            {"id": 3, "run_metadata": {
                "ai_usage": {"tts": {"m-suara": 100}},
                "cost": {"usd": 0.0, "unpriced": ["m-suara"]}}},
        ]
        ringkas, pesan = _jalankan(runs)
        self.assertFalse(ringkas.get("panggilan_tanpa_token"), f"alarm palsu: {ringkas}")
        self.assertFalse(ringkas.get("nol_senyap"), f"alarm palsu: {ringkas}")
        self.assertFalse(pesan, f"alarm palsu terkirim ke admin: {pesan}")

    def test_alarm_tak_berulang_di_hari_yang_sama(self):
        """Alarm yang mengulang tiap putaran petugas harian = alarm yang diabaikan."""
        from src.billing import price_sync
        runs = [{"id": 9, "run_metadata": {
            "ai_usage": {"tts": {"m-suara": 10}}, "cost": {"usd": 0.0, "unpriced": []}}}]
        pesan: list = []
        with patch.object(price_sync, "_notify_admin", lambda t: pesan.append(t)), \
             patch.object(price_sync, "_state_get_epoch", lambda *a, **k: 9_999_999_999), \
             patch.object(price_sync, "_state_set_epoch", lambda *a, **k: None):
            price_sync.report_rekonsiliasi_biaya(sb=_SB(runs, []))
        self.assertFalse(pesan, "alarm terkirim lagi padahal hari ini sudah dikirim")

    def test_gagal_apa_pun_tak_mengganggu_petugas_harian(self):
        """Rekonsiliasi adalah pengawas, bukan jalur kerja. Kegagalannya haram menjatuhkan janitor."""
        from src.billing import price_sync

        class _Meledak:
            def table(self, *a, **k):
                raise RuntimeError("DB sengaja dimatikan dalam uji")
        hasil = price_sync.report_rekonsiliasi_biaya(sb=_Meledak())
        self.assertIsInstance(hasil, dict, "rekonsiliasi melempar galat ke petugas harian")

    def test_dipanggil_petugas_harian(self):
        """Fungsi yang tak dipanggil = kode mati. Ini kelas cacat yang sudah terjadi: rincian
        kegagalan ditulis tiap run sejak lama, nol pembaca, 16 produksi lolos."""
        import ast
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(akar, "src/orchestrator/buffer_janitor.py"), encoding="utf-8") as f:
            pohon = ast.parse(f.read())
        dipanggil = [n for n in ast.walk(pohon) if isinstance(n, ast.Call)
                     and getattr(n.func, "id", "") == "report_rekonsiliasi_biaya"]
        self.assertTrue(dipanggil,
                        "rekonsiliasi tak dipanggil petugas harian → alarm ini kode mati")


class TestHargaTerkunciTakBolehDilupakan(unittest.TestCase):
    """Setiap pengecualian yang mesin berikan WAJIB punya masa kedaluwarsa (ketokan owner 24-Agu:
    *"jangan hanya berfikir saat ini, tapi berfikir kedepannya"*).

    KEADAAN YANG DIPERBAIKI. Alarm harga-basi dulu berbunyi `if pricing_locked: continue` — jadi
    persisnya TERBALIK terhadap kenyataan: baris **otomatis** dijaga alarm padahal ia memutakhirkan
    diri sendiri dan hampir mustahil basi, sementara baris **TERKUNCI** — satu-satunya yang BISA
    basi, sebab tak ada yang memutakhirkannya — tak dijaga apa pun. Untuk hari ini tak terasa
    (angkanya baru diperiksa tangan); untuk ke depan itu JAMINAN angka salah, senyap, selamanya:
    vendor mengubah tarif kapan saja.

    Dua baris bahkan tak punya tanggal sama sekali (`veo`, `cf-flux-schnell`) ⇒ mustahil pernah
    terdeteksi tua. "Tanpa tanggal" karena itu diperlakukan sebagai **belum pernah dipastikan**,
    bukan sebagai "aman".

    Jendelanya beda dengan yang otomatis, dan itu disengaja: harga yang diperiksa manusia tak perlu
    ditengok tiap minggu (bawaan 90 hari), sedangkan sumber otomatis yang mandek seminggu sudah
    pertanda rusak (7 hari)."""

    def _jalankan(self, rows):
        from src.billing import price_sync
        pesan: list = []
        with patch.object(price_sync, "_notify_admin", lambda t: pesan.append(t)), \
             patch.object(price_sync, "_state_get_epoch", lambda *a, **k: 0), \
             patch.object(price_sync, "_state_set_epoch", lambda *a, **k: None):
            price_sync._check_staleness(_SB([], []), rows)
        return pesan

    @staticmethod
    def _umur(hari):
        import datetime as _dt
        return (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=hari)).isoformat()

    def test_harga_terkunci_yang_lama_tak_diperiksa_dilaporkan(self):
        pesan = self._jalankan([{"model_key": "m-kunci-tua", "pricing_locked": True,
                                 "pricing": {"per_1m_chars": 100, "synced_at": self._umur(200)}}])
        self.assertTrue(pesan, "harga terkunci berumur 200 hari tak dilaporkan — ia takkan pernah "
                               "ditengok lagi, padahal vendor bisa mengubah tarifnya kapan saja")
        self.assertIn("m-kunci-tua", pesan[0])

    def test_harga_terkunci_TANPA_tanggal_dilaporkan(self):
        """Tanpa tanggal = belum pernah dipastikan. Memperlakukannya 'aman' = pengecualian permanen."""
        pesan = self._jalankan([{"model_key": "m-tanpa-tanggal", "pricing_locked": True,
                                 "pricing": {"per_second_usd": 0.1}}])
        self.assertTrue(pesan, "harga terkunci tanpa tanggal tak dilaporkan — mustahil terdeteksi tua")
        self.assertIn("m-tanpa-tanggal", pesan[0])

    def test_harga_terkunci_yang_baru_diperiksa_TIDAK_dilaporkan(self):
        """Alarm palsu pada baris yang baru diperiksa = alarm yang diabaikan."""
        pesan = self._jalankan([{"model_key": "m-baru", "pricing_locked": True,
                                 "pricing": {"per_1m_chars": 100, "synced_at": self._umur(10)}}])
        self.assertFalse(pesan, f"alarm palsu pada harga yang baru diperiksa: {pesan}")

    def test_baris_otomatis_tetap_dijaga_jendela_pendek(self):
        """Nol regresi: sumber otomatis yang mandek > 7 hari tetap berbunyi seperti sebelumnya."""
        pesan = self._jalankan([{"model_key": "m-otomatis", "pricing_locked": False,
                                 "pricing": {"in_per_1m": 1.0, "synced_at": self._umur(30)}}])
        self.assertTrue(pesan, "baris otomatis yang mandek tak lagi dilaporkan — regresi")
        self.assertIn("m-otomatis", pesan[0])

    def test_dua_sebab_dipisah_karena_tindakannya_beda(self):
        """Sumber otomatis MANDEK (periksa sumbernya) ≠ harga ketikan tangan yang lama tak
        diperiksa ulang (buka halaman resmi vendor). Satu kalimat untuk dua tindakan = alarm tumpul."""
        pesan = self._jalankan([
            {"model_key": "m-otomatis", "pricing_locked": False,
             "pricing": {"in_per_1m": 1.0, "synced_at": self._umur(30)}},
            {"model_key": "m-kunci-tua", "pricing_locked": True,
             "pricing": {"per_1m_chars": 100, "synced_at": self._umur(200)}}])
        self.assertTrue(pesan)
        t = pesan[0]
        self.assertIn("m-otomatis", t)
        self.assertIn("m-kunci-tua", t)
        i_auto, i_kunci = t.index("m-otomatis"), t.index("m-kunci-tua")
        antara = t[min(i_auto, i_kunci):max(i_auto, i_kunci)]
        self.assertRegex(antara, r"(?i)(dikunci|terkunci|ketikan tangan|diperiksa ulang)",
                         "kedua sebab dilebur jadi satu daftar — admin tak tahu mana yang mana")
