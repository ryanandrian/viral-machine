"""
Ambang & kenop numerik rantai DURASI · NASKAH · SUARA — satu pintu, sumbernya DB.

═══ KENAPA MODUL INI ADA ═══

Belasan ambang yang menentukan perilaku mesin hanya hidup sebagai variabel lingkungan dengan angka
bawaan di kode: batas audio-terpotong, cakupan naskah, jumlah putaran perbaikan, ambang alarm, syarat
minimum kalibrasi, dan seterusnya. Diperiksa 2026-08-01: **`.env` di server tidak memuat satu pun** —
jadi seluruhnya berjalan dengan angka bawaan kode, dan tak satu pun terlihat atau bisa diubah owner.
Mengubahnya berarti menyunting kode dan deploy ulang.

Itu melanggar dua hal sekaligus: aturan owner "nol hardcode, harus bisa diatur di panel", dan prinsip
yang sama yang membuat kenop `voice_catalog.default_settings` dulu berisi angka tak terlihat selama
berbulan-bulan.

Modul ini menjadikan `app_config` (tabel yang SUDAH punya layar admin) sebagai sumbernya, dengan angka
bawaan di kode HANYA sebagai jaring pengaman bila DB tak terjangkau. Nilai disimpan sebagai BILANGAN
BULAT dalam satuan yang wajar bagi manusia (persen, detik, milidetik, jumlah) — bukan pecahan —
supaya layar admin bisa memakai kotak angka biasa dan owner tak perlu memikirkan desimal.

Pemakaian:
    from src.config import ambang
    ambang.pct("tts_potong_ambang_pct", 75)     → 0.75
    ambang.detik("tts_timeout_dasar_sec", 180)  → 180.0
    ambang.milidetik("probe_maks_mad_ms", 100)  → 0.10
    ambang.angka("script_refit_rounds", 3)      → 3
    ambang.saklar("qc_require_audio", True)     → True
"""

from __future__ import annotations

from src.config.app_config import get_int


def angka(key: str, bawaan: int) -> int:
    """Kenop berupa jumlah/hitungan (mis. berapa putaran, berapa sampel minimum)."""
    return get_int(key, bawaan)


def pct(key: str, bawaan_pct: int) -> float:
    """Kenop berupa PERSEN di DB → pecahan 0..1 di kode. 75 → 0,75."""
    return get_int(key, bawaan_pct) / 100.0


def detik(key: str, bawaan_detik: int) -> float:
    return float(get_int(key, bawaan_detik))


def milidetik(key: str, bawaan_ms: int) -> float:
    """Kenop berupa MILIDETIK di DB → detik di kode. Dipakai untuk ambang yang lebih kecil dari
    satu detik, supaya tetap bilangan bulat di layar admin (100 ms, bukan 0,1 dtk)."""
    return get_int(key, bawaan_ms) / 1000.0


def saklar(key: str, bawaan: bool) -> bool:
    """Kenop hidup/mati: 1 = hidup, 0 = mati."""
    return bool(get_int(key, 1 if bawaan else 0))


def teks(key: str, bawaan: str) -> str:
    """Kenop berupa teks (mis. rasio layar '9:16') — dari kolom value_text."""
    from src.config.app_config import get_text
    return get_text(key, bawaan)
