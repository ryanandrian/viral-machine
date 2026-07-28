"""Identitas suara KATALOG vs VENDOR — satu titik terjemahan di `build_tts_provider`.

`voice_catalog.voice_key` = kunci katalog kita (dirujuk `channels.voice_key`, `tts_delivery_samples`,
kalibrasi pace). `vendor_voice_id` = identitas suara yang SAMA di sisi vendor. Terjemahan hanya boleh
terjadi saat membangun adaptor; kalau bocor ke config pemanggil, kalibrasi pace & atribusi video akan
tercatat memakai penamaan vendor → data ukur bercampur antar-jalur.

Uji ini juga mengunci kontrak config adaptor fal (tts_api_key/tts_model/tts_voice) — sempat salah nama
sehingga jalur suara fal mustahil menerima kunci API dari pemanggil mana pun.
"""
import asyncio
import json
import urllib.error
import urllib.request

import pytest

import src.config.format_catalog as fc
from src.providers.tts import TTSError, build_tts_provider
from src.providers.tts.fal_tts import FalTTSProvider


@pytest.fixture
def katalog(monkeypatch):
    """Adaptor per-penyedia dipatok; peta vendor diisi per-uji."""
    monkeypatch.setattr(fc, "tts_adapter", lambda pk, default=None: {
        "fal": "fal_tts", "elevenlabs": "elevenlabs", "edge_tts": "edge"}.get(pk, default))

    def pasang(peta: dict):
        monkeypatch.setattr(fc, "voice_vendor_id", lambda vk, default=None: peta.get(vk) or default)
    return pasang


# ── terjemahan katalog → vendor ───────────────────────────────────────────────────────────────────

def test_vendor_terisi_maka_adaptor_menerima_id_vendor(katalog):
    katalog({"fal-luna-id": "BfwyZzLnL4udYd1qYpiN"})
    p = build_tts_provider("fal", {"tts_voice": "fal-luna-id", "tts_api_key": "k", "tts_model": "m"})
    assert p.voice == "BfwyZzLnL4udYd1qYpiN"


def test_config_pemanggil_TIDAK_dimutasi(katalog):
    """Pagar utama: pace & atribusi video harus tetap memakai kunci KATALOG."""
    katalog({"fal-luna-id": "BfwyZzLnL4udYd1qYpiN"})
    cfg = {"tts_voice": "fal-luna-id", "tts_api_key": "k", "tts_model": "m"}
    build_tts_provider("fal", cfg)
    assert cfg["tts_voice"] == "fal-luna-id"


def test_vendor_kosong_perilaku_lama_persis(katalog):
    """Semua penyedia non-agregator: kolom kosong → voice_key dipakai apa adanya."""
    katalog({})
    p = build_tts_provider("edge_tts", {"tts_voice": "id-ID-ArdiNeural"})
    assert p.voice == "id-ID-ArdiNeural"


def test_vendor_sama_dengan_voice_key_tidak_menyalin_config(katalog):
    katalog({"alloy": "alloy"})
    cfg = {"tts_voice": "alloy", "tts_api_key": "k", "tts_model": "m"}
    p = build_tts_provider("elevenlabs", cfg)
    assert p.voice == "alloy" and cfg["tts_voice"] == "alloy"


def test_gagal_baca_peta_vendor_tidak_menggagalkan_produksi(monkeypatch, katalog):
    """DB suara bermasalah → jangan mati; pakai voice_key (vendor agregator menolak JUJUR)."""
    monkeypatch.setattr(fc, "tts_adapter", lambda pk, default=None: "edge")
    monkeypatch.setattr(fc, "voice_vendor_id", lambda vk, default=None: default)
    p = build_tts_provider("edge_tts", {"tts_voice": "id-ID-GadisNeural"})
    assert p.voice == "id-ID-GadisNeural"


def test_voice_kosong_gagal_jujur_bukan_suara_asal(katalog):
    """Tanpa voice, adaptor WAJIB menolak — bukan memilih suara sembarang (§0.6)."""
    katalog({"x": "y"})
    with pytest.raises(TTSError):
        build_tts_provider("edge_tts", {})


# ── kontrak config adaptor fal ────────────────────────────────────────────────────────────────────

def test_adaptor_fal_membaca_nama_config_yang_dipakai_pemanggil():
    """tts_engine & model_tester mengirim tts_*; nama lain = kunci API tak pernah sampai."""
    p = FalTTSProvider({"tts_api_key": "kunci", "tts_model": "fal-ai/x", "tts_voice": "Rachel"})
    assert (p.api_key, p.model, p.voice) == ("kunci", "fal-ai/x", "Rachel")


def test_tanpa_kunci_gagal_jujur():
    p = FalTTSProvider({"tts_model": "fal-ai/x", "tts_voice": "Rachel"})
    with pytest.raises(TTSError):
        asyncio.run(p.generate("halo", "/tmp/tidak-dipakai.mp3"))


def test_tanpa_model_gagal_jujur():
    p = FalTTSProvider({"tts_api_key": "k", "tts_voice": "Rachel"})
    with pytest.raises(TTSError):
        asyncio.run(p.generate("halo", "/tmp/tidak-dipakai.mp3"))


# ── lapisan delivery (harus IDENTIK ElevenLabs langsung) ──────────────────────────────────────────

def _payload_terkirim(monkeypatch, config: dict) -> dict:
    """Tangkap payload yang BENAR-BENAR dikirim ke fal tanpa memanggil jaringan."""
    tangkap = {}

    def fake_urlopen(req, timeout=None):
        tangkap["body"] = json.loads(req.data.decode())
        raise urllib.error.URLError("dihentikan sengaja setelah payload tertangkap")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    p = FalTTSProvider({"tts_api_key": "k", "tts_model": "fal-ai/x", **config})
    with pytest.raises(TTSError):
        asyncio.run(p.generate("Uji.", "/tmp/tidak-dipakai.mp3"))
    return tangkap["body"]


def test_baseline_voice_catalog_dikirim_keempatnya(monkeypatch):
    """Sebelum perbaikan hanya `speed` yang dikirim → suara lewat fal beda dari ElevenLabs langsung."""
    body = _payload_terkirim(monkeypatch, {
        "tts_voice": "Adam",
        "tts_voice_default_settings": {"speed": 0.87, "style": 0.5, "stability": 0.3, "similarity_boost": 0.75},
    })
    assert body["speed"] == 0.87 and body["style"] == 0.5
    assert body["stability"] == 0.3 and body["similarity_boost"] == 0.75
    assert body["timestamps"] is True and body["voice"] == "Adam"


def test_ekspresi_niche_menimpa_baseline_hanya_style_dan_stability(monkeypatch):
    body = _payload_terkirim(monkeypatch, {
        "tts_voice": "Adam", "niche": "dark_history",
        "tts_voice_default_settings": {"speed": 0.87, "style": 0.5, "stability": 0.3},
        "niche_voice_expression": {"style": 0.9, "stability": 0.2, "speed": 1.2},
    })
    assert body["style"] == 0.9 and body["stability"] == 0.2
    assert body["speed"] == 0.87   # speed = milik mesin durasi, bukan ekspresi niche


def test_warisan_tenant_menang_terakhir(monkeypatch):
    body = _payload_terkirim(monkeypatch, {
        "tts_voice": "Adam", "niche": "fun_facts",
        "tts_voice_default_settings": {"speed": 0.87, "style": 0.5},
        "niche_voice_expression": {"style": 0.9},
        "tts_voice_settings": {"fun_facts": {"speed": 0.8, "style": 0.1}},
    })
    assert body["speed"] == 0.8 and body["style"] == 0.1


def test_ekspresi_di_luar_rentang_diabaikan(monkeypatch):
    body = _payload_terkirim(monkeypatch, {
        "tts_voice": "Adam", "niche": "n",
        "tts_voice_default_settings": {"stability": 0.3},
        "niche_voice_expression": {"stability": 5.0},
    })
    assert body["stability"] == 0.3


def test_tanpa_pengaturan_apa_pun_pakai_angka_elevenlabs(monkeypatch):
    """Angka bawaan sengaja SAMA dgn adaptor ElevenLabs: suara sama = terdengar sama."""
    body = _payload_terkirim(monkeypatch, {"tts_voice": "Adam"})
    assert (body["stability"], body["similarity_boost"], body["style"], body["speed"]) == (0.30, 0.75, 0.50, 0.87)


def test_nilai_pengaturan_rusak_tidak_mematikan_render(monkeypatch):
    body = _payload_terkirim(monkeypatch, {
        "tts_voice": "Adam", "tts_voice_default_settings": {"speed": "cepat sekali"}})
    assert body["speed"] == 0.87
