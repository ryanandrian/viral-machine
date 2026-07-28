"""Alur alarm drift: berbunyi → ditahan rem → mengabari saat PULIH → lalu diam.

Menguji perilaku utuh check_drift_alarm dengan database & Telegram TIRUAN — tak ada pesan sungguhan
terkirim dan tak ada baris produksi tersentuh. Yang dikunci di sini adalah janji ke owner:
  * satu alarm per jendela rem (bukan tiap kali worker restart),
  * status tersimpan sehingga pemeriksaan berikutnya bisa menyebut ARAH pergerakan,
  * kabar PULIH dikirim TEPAT SEKALI, lalu sunyi selama masih normal.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.production import pace_calibration as pc


class _Q:
    """Peniru rantai query supabase-py seperlunya (select/eq/order/limit/not_/is_/execute)."""

    def __init__(self, db, tabel):
        self.db, self.tabel, self._eq = db, tabel, {}

    def select(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, kol, val):
        self._eq[kol] = val
        return self

    @property
    def not_(self):
        return self

    def is_(self, *_a, **_k):
        return self

    def execute(self):
        rows = self.db.data.get(self.tabel, [])
        for k, v in self._eq.items():
            rows = [r for r in rows if r.get(k) == v]
        return type("R", (), {"data": rows})()

    def upsert(self, row):
        baris = self.db.data.setdefault(self.tabel, [])
        for i, r in enumerate(baris):
            if r.get("key") == row.get("key"):
                baris[i] = row
                break
        else:
            baris.append(row)
        return type("E", (), {"execute": lambda *_: None})()


class _DB:
    def __init__(self, sampel):
        self.data = {"tts_delivery_samples": sampel, "app_config": []}

    def table(self, nama):
        return _Q(self, nama)


def _sampel(err_pct: float, n: int = 30):
    """n sampel dengan selisih taksiran-vs-nyata persis err_pct%."""
    return [{"predicted_secs": 100 * (1 + err_pct / 100), "raw_audio_secs": 100.0,
             "created_at": f"2026-07-2{i % 10}T00:00:00+00:00"} for i in range(n)]


@pytest.fixture
def tangkap(monkeypatch):
    """Sadap Telegram: pesan dikumpulkan, tak ada yang benar-benar terkirim."""
    keluar = []

    class _TN:
        def notify_admin(self, teks):
            keluar.append(teks)

    import src.utils.telegram_notifier as tn
    monkeypatch.setattr(tn, "TelegramNotifier", lambda *_a, **_k: _TN())
    monkeypatch.setenv("DRIFT_ALARM_PCT", "10")
    monkeypatch.setenv("DRIFT_WINDOW_N", "30")
    return keluar


def test_alarm_pertama_berbunyi_lalu_ditahan_rem(tangkap):
    db = _DB(_sampel(12.0))
    h1 = pc.check_drift_alarm(sb=db)
    assert h1["alarmed"] is True and h1["suppressed"] is False
    assert len(tangkap) == 1 and "di bawah standar" in tangkap[0]

    h2 = pc.check_drift_alarm(sb=db)          # langsung diperiksa lagi (mis. worker restart)
    assert h2["suppressed"] is True, "rem 24 jam tidak bekerja — owner akan didering berkali-kali"
    assert len(tangkap) == 1, "alarm kedua lolos padahal masih dalam jendela rem"


def test_pemeriksaan_berikutnya_menyebut_arah_membaik(tangkap):
    db = _DB(_sampel(12.0))
    pc.check_drift_alarm(sb=db)
    # rem dimundurkan supaya alarm berikutnya boleh bunyi (meniru pemeriksaan besok)
    st = json.loads(db.data["app_config"][0]["value_text"])
    st["last_at"] = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    db.data["app_config"][0]["value_text"] = json.dumps(st)

    db.data["tts_delivery_samples"] = _sampel(10.5)      # membaik, tapi masih di atas batas
    pc.check_drift_alarm(sb=db)
    assert len(tangkap) == 2
    assert "MEMBAIK" in tangkap[1] and "12.0" in tangkap[1]


def test_kabar_pulih_dikirim_tepat_sekali(tangkap):
    db = _DB(_sampel(12.0))
    pc.check_drift_alarm(sb=db)                          # alarm
    db.data["tts_delivery_samples"] = _sampel(9.0)       # kembali normal
    h = pc.check_drift_alarm(sb=db)
    assert h["alarmed"] is False
    assert len(tangkap) == 2 and "KEMBALI NORMAL" in tangkap[1]

    pc.check_drift_alarm(sb=db)                          # masih normal → harus SUNYI
    assert len(tangkap) == 2, "kabar pulih terkirim berulang — jadi kebisingan baru"


def test_normal_sejak_awal_tidak_mengirim_apa_pun(tangkap):
    db = _DB(_sampel(5.0))
    h = pc.check_drift_alarm(sb=db)
    assert h["alarmed"] is False
    assert tangkap == []


def test_data_terlalu_tipis_tidak_membunyikan_alarm_palsu(tangkap):
    db = _DB(_sampel(30.0, n=4))
    h = pc.check_drift_alarm(sb=db)
    assert h["status"] == "insufficient_data"
    assert tangkap == []
