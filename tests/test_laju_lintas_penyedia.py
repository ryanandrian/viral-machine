"""LAJU BICARA berlaku untuk penyedia MANA PUN — termasuk yang belum ada hari ini.

Arahan owner 2026-08-01: katalog model akan terus bertambah dan dipakai banyak tenant, jadi perbaikan
harus GENERAL, bukan per-vendor. Menuliskan rentang tiap penyedia di kode berarti setiap penyedia baru
menuntut perubahan kode — dan yang lupa diubah akan gagal DIAM-DIAM.

Mekanismenya sudah ada sejak lama di DB (`tts_profiles.speed_param` + `param_schema`) dengan pembacanya
(`format_catalog.tts_speed_range`) — tapi NOL PEMAKAI sampai hari ini, sementara tiga tempat menanam
rentangnya sendiri di kode. Uji ini mengunci penyatuannya.
"""

import inspect

import pytest

from src.production.voice_delivery import RASIO_ALAMI, rasio_laju


@pytest.mark.parametrize("setelan,rentang,harap", [
    ({"rate": "+15%"}, (0.5, 2.0), 1.15),      # Edge: persen → pengali
    ({"speed": 0.87}, (0.7, 1.2), 0.87),       # ElevenLabs: pengali langsung
    ({"speed": 0.25}, (0.25, 4.0), 0.25),      # OpenAI: rentang jauh lebih lebar
    ({"speed": 0.8}, (1.0, 1.0), 1.0),         # Gemini: TAK punya kenop → apa pun jadi 1,0
    ({"speed": 2.0}, (0.7, 1.2), 1.0),         # di luar rentang penyedia → tolak, jangan kirim
    ({"rate": "-90%"}, (0.5, 2.0), 1.0),       # di luar rentang → tolak
    ({}, (0.7, 1.2), 1.0),                     # tak disebut → alami
])
def test_rasio_menghormati_rentang_penyedianya_sendiri(setelan, rentang, harap):
    assert rasio_laju(setelan, rentang) == pytest.approx(harap, abs=1e-6)


def test_nilai_di_luar_rentang_TIDAK_diteruskan_ke_vendor():
    """Meneruskan nilai yang ditolak vendor = produksi gagal karena setelan katalog, bukan karena
    naskah. Lebih baik laju alami (aturan owner) daripada error."""
    assert rasio_laju({"speed": 3.5}, (0.7, 1.2)) == RASIO_ALAMI


def test_rentang_dibaca_dari_DB_bukan_ditanam_di_kode():
    """`tts_profiles.param_schema` = satu-satunya sumber rentang. Penyedia baru cukup satu baris DB."""
    from src.config import format_catalog as fc
    src = inspect.getsource(fc.tts_speed_range)
    assert "param_schema" in src and "speed_param" in src


@pytest.mark.parametrize("modul", [
    "src.providers.tts.edge_tts", "src.providers.tts.elevenlabs",
    "src.providers.tts.fal_tts", "src.providers.tts.openai_tts",
])
def test_setiap_adaptor_memakai_rentang_dari_DB(modul):
    """Tak boleh ada adaptor yang menanam rentangnya sendiri lagi."""
    import importlib
    src = inspect.getsource(importlib.import_module(modul))
    assert "tts_speed_range" in src, f"{modul} tidak memakai rentang dari DB"
    assert "max(0.25" not in src and "min(4.0" not in src, f"{modul} masih menanam rentang di kode"


def test_kalibrasi_memakai_rentang_yang_SAMA_dengan_adaptor():
    """Bila kedua sisi memakai pagar berbeda, nilai katalog di luar rentang dihitung apa adanya oleh
    kalibrasi tapi dijatuhkan ke 1,0 oleh adaptor → SETIAP sampel suara itu ditolak, selamanya, tanpa
    satu pun pesan. Kelas cacat yang sama menghabiskan dua hari pada 31-Jul."""
    import src.production.pace_calibration as pc
    src = inspect.getsource(pc.compute_pace_calibration)
    assert "tts_speed_range" in src, "kalibrasi memakai pagar sendiri, bukan rentang penyedia"
    assert "provider_key" in src, "kalibrasi tak membaca penyedia suara → rentangnya tak bisa benar"
