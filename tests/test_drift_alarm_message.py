"""Pesan alarm drift durasi WAJIB menyebut ARAH pergerakan, dan pemulihan WAJIB dikabari.

Insiden 2026-07-28: owner 5 hari berturut menerima peringatan yang terasa identik. Angkanya
sebenarnya membaik terus (12,8 → 12,3 → 11,5 → 11,5 → 10,4%), tapi pesan hanya menyebut angka hari
itu tanpa pembanding — jadi proses penyembuhan terbaca sebagai kemacetan. Pesan lama juga menyuruh
"panggil developer bila muncul lagi besok", padahal muncul-lagi WAJAR selama angkanya turun. Dan
ketika akhirnya normal (27 Jul), tidak ada kabar apa pun — diam tak bisa dibedakan dari alarm rusak.

Uji ini mengunci ketiga perbaikan itu pada teksnya (fungsi murni, tanpa Telegram/DB).
"""
from src.production.pace_calibration import _drift_alarm_text, _drift_recovery_text


def test_membaik_disebut_dan_tidak_menyuruh_panggil_developer():
    """Angka turun = mesin sedang bekerja → jangan bikin owner panik."""
    t = _drift_alarm_text(10.4, 10, 30, prev=11.5)
    assert "10.4%" in t and "11.5%" in t
    assert "MEMBAIK" in t
    assert "Tidak perlu tindakan" in t
    assert "minta developer" not in t.lower()


def test_memburuk_justru_menyuruh_panggil_developer():
    t = _drift_alarm_text(12.0, 10, 30, prev=10.4)
    assert "MEMBURUK" in t and "10.4%" in t
    assert "developer" in t.lower()


def test_mentok_di_angka_sama_juga_menyuruh_periksa():
    """Tidak turun beberapa hari = koreksi otomatis mentok — inilah kondisi yang benar utk eskalasi."""
    t = _drift_alarm_text(10.4, 10, 30, prev=10.4)
    assert "TIDAK BERUBAH" in t
    assert "developer" in t.lower()


def test_pemeriksaan_pertama_tanpa_pembanding_tidak_mengarang_tren():
    t = _drift_alarm_text(10.4, 10, 30, prev=None)
    assert "MEMBAIK" not in t and "MEMBURUK" not in t and "TIDAK BERUBAH" not in t
    assert "pertama" in t.lower()


def test_kabar_pemulihan_menyebut_angka_dan_menutup_kecemasan():
    t = _drift_recovery_text(9.3, 10, 30, prev=10.4)
    assert "KEMBALI NORMAL" in t
    assert "9.3%" in t and "10.4%" in t
    assert "Tidak ada tindakan" in t


def test_semua_pesan_bebas_jargon_teknis():
    """Owner non-teknis: pesan tak boleh memuat istilah mesin (§4.1)."""
    jargon = ["drift", "median", "estimator", "wps", "calibration", "threshold", "delivery_wps"]
    pesan = [
        _drift_alarm_text(10.4, 10, 30, prev=11.5),
        _drift_alarm_text(12.0, 10, 30, prev=10.4),
        _drift_alarm_text(10.4, 10, 30, prev=None),
        _drift_recovery_text(9.3, 10, 30, prev=10.4),
    ]
    for t in pesan:
        for j in jargon:
            assert j not in t.lower(), f"jargon '{j}' bocor ke pesan owner: {t[:80]}"


def test_perubahan_sangat_kecil_tidak_diklaim_membaik():
    """Turun 0,02% bukan perbaikan berarti — jangan menenangkan owner secara palsu."""
    t = _drift_alarm_text(10.40, 10, 30, prev=10.42)
    assert "TIDAK BERUBAH" in t
