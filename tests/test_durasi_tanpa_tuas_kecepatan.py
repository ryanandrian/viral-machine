"""PENJAGA ATURAN OWNER: kecepatan suara BUKAN tuas durasi — di SELURUH kode produksi.

Keputusan owner 2026-07-29, ditegakkan 2026-07-31. Bukan preferensi: diukur dari 59 render produksi
terbaru, 41% mentok di batas paling lambat (0,70), NOL render berjalan di kecepatan normal, median
0,81 — narasi dibacakan ~20% lebih lambat dari semestinya (mood rusak = barang yang produk ini jual)
DAN durasinya tetap meleset median −4,7 dtk. Ada DUA lapis yang dicabut:
  1. `script_engine.solve_speed_for_duration` → menyuntik speed ke tts_voice_settings
  2. `tts_engine._fit_duration` → meregangkan audio jadi (atempo 0,80–1,35×)

Uji di file ini gagal bila salah satu lapis itu kembali dalam bentuk apa pun. Uji tambahan mengunci
pengganti-penggantinya (penjaga fakta saat naskah diperbaiki, penanda alat skor yang rusak).
"""
import inspect

import pytest


# ── lapis 1 & 2: tak boleh ada lagi di kode produksi ──────────────────────────────────────────────

def test_solver_kecepatan_sudah_TIDAK_ADA():
    import src.intelligence.script_engine as se
    assert not hasattr(se, "solve_speed_for_duration"), \
        "solver kecepatan kembali — durasi tidak boleh dibeli dengan mood narasi"
    assert not hasattr(se, "estimate_spoken_seconds"), \
        "estimator lama (benih jeda tak terkalibrasi) kembali"
    for konstanta in ("_PAUSE_SECONDS", "_PAUSE_INFLATION"):
        assert not hasattr(se, konstanta), f"benih jeda {konstanta} kembali — harus dari kalibrasi"


def test_peregangan_audio_sudah_TIDAK_ADA():
    import src.production.tts_engine as te
    assert not hasattr(te.TTSEngine, "_fit_duration"), "peregangan audio (atempo) kembali"
    sumber = inspect.getsource(te)
    # boleh disebut di komentar sejarah; tidak boleh ada pemanggilan ffmpeg atempo
    assert "filter:a" not in sumber and "atempo=" not in sumber, \
        "ada pemanggilan atempo di tts_engine"


def test_naskah_tak_lagi_diminta_menyetel_kecepatan():
    """Prompt dulu menyuruh model mengisi `speed` 'untuk mood' — lalu sistem memakainya sebagai tuas."""
    import src.intelligence.script_engine as se
    sumber = inspect.getsource(se)
    assert '"tts_params": {{"speed"' not in sumber, "spesifikasi keluaran masih meminta `speed`"


def test_speed_dari_naskah_DIABAIKAN_bukan_diterapkan():
    """Kalau model tetap mengirim `speed`, nilainya tidak boleh sampai ke pembuat suara."""
    import src.production.tts_engine as te
    sumber = inspect.getsource(te.TTSEngine.generate)
    assert "DIABAIKAN" in sumber
    # periksa BARIS KODE saja (komentar sejarah memang menyebut mekanisme yang dicabut)
    kode = "\n".join(l for l in sumber.split("\n") if not l.strip().startswith("#"))
    assert "tts_voice_settings" not in kode, \
        "generate() masih menyentuh tts_voice_settings — jalan masuk tuas kecepatan"
    assert "config[" not in kode.replace("config.get", ""), \
        "generate() masih memutasi config penyedia suara"


# ── pengganti: penjaga fakta saat naskah diperbaiki ───────────────────────────────────────────────

def test_angka_hilang_selalu_menolak_perbaikan():
    """Durasi tidak pernah dibeli dengan membuang fakta. Angka = fakta paling mudah diverifikasi."""
    from src.intelligence.script_engine import _fakta_hilang
    asal = "Pada tahun 1348 wabah membunuh sepertiga penduduk."
    assert _fakta_hilang(asal, "Wabah membunuh banyak penduduk.") == ["1348"]
    assert _fakta_hilang(asal, "Pada tahun 1348 wabah datang.") == []


def test_nama_panjang_dijaga_nama_pendek_tidak():
    """Terukur: kata biasa berhuruf besar ('Tires') memblokir perbaikan yang sah dan membuang satu
    putaran. Nama diri sungguhan cenderung panjang (Neuschwanstein, Pajajaran)."""
    from src.intelligence.script_engine import _MIN_HURUF_NAMA, _fakta_hilang
    assert _MIN_HURUF_NAMA >= 6
    asal = "Kastil Neuschwanstein memakai Tires buatan lokal."
    assert _fakta_hilang(asal, "Kastil memakai Tires buatan lokal.") == ["Neuschwanstein"]
    assert _fakta_hilang(asal, "Kastil Neuschwanstein memakai roda buatan lokal.") == []


def test_kata_pertama_kalimat_bukan_nama_diri():
    from src.intelligence.script_engine import _nama_diri
    assert "Kastil" not in _nama_diri("Kastil itu runtuh.")
    assert "Neuschwanstein" in _nama_diri("Kastil Neuschwanstein itu runtuh.")


# ── pengganti: alat skor yang rusak wajib menandai dirinya ────────────────────────────────────────

def test_taksiran_lokal_selalu_bertanda():
    """Cacat produksi: saat penilai LLM gagal, skor cadangan (±20 poin lebih rendah) dipakai apa
    adanya sebagai gerbang mutu DAN masuk data mesin belajar, tanpa jejak."""
    from src.intelligence.script_analyzer import ScriptAnalyzer
    a = ScriptAnalyzer(provider=None)
    hasil = a.analyze({"hook": "Uji", "core_facts": "Isi naskah uji."}, "dark_history")
    assert hasil.get("estimated") is True
    assert hasil.get("estimate_reason")
    assert hasil.get("weak_areas") == [], "taksiran lokal tak boleh memicu retry palsu"


# ── satu sumber angka ─────────────────────────────────────────────────────────────────────────────

def test_hitungan_tanda_jeda_satu_sumber():
    """Dulu ada dua implementasi penghitung tanda-jeda (script_engine & duration_model) — risiko
    drift senyap antara angka yang MERAMAL dan angka yang DICATAT ke sampel kalibrasi."""
    from src.intelligence.script_engine import _count_pauses
    from src.production.duration_model import ciri_teks
    teks = "Satu... dua, tiga — empat. Lima!"
    a, b = _count_pauses(teks), ciri_teks(teks)
    for k in ("sentence", "ellipsis", "comma", "em_dash"):
        assert a[k] == b[k], f"'{k}' beda antara pencatat sampel dan peramal durasi"


# ── baris kalibrasi warisan tak boleh MENUTUP baris yang berisi koefisien ──────────────────────────

def test_baris_per_niche_tanpa_koefisien_tidak_menutup_baris_bintang(monkeypatch):
    """Cacat NYATA & terukur (2026-07-31): baris ('id-ID-GadisNeural','dark_history') warisan sistem
    lama hanya berisi `delivery_wps`. Karena dipilih membuta sebagai "lebih spesifik", baris '*' yang
    BERISI koefisien tertutup → produksi jatuh ke angka bawaan suara LAIN → ramalan naskah 239 kata
    meleset 42 detik (88,6 vs 130,8). Aturan: ambil baris yang PUNYA koefisien."""
    from src.config.tenant_config import TenantConfigManager, TenantRunConfig

    warisan = {"niche": "dark_history", "delivery_wps": 1.975}          # tanpa koefisien
    berisi = {"niche": "*", "delivery_wps": 2.15, "sec_per_char": 0.06299,
              "sec_per_sentence": 0.974, "chars_per_word": 5.85, "words_per_sentence": 15.0,
              "calib_error_secs": 1.02}

    class _Q:
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def in_(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self): return type("R", (), {"data": [warisan, berisi]})()

    class _SB:
        def table(self, nama): return _Q()

    m = TenantConfigManager.__new__(TenantConfigManager)
    m._supabase = _SB()
    cfg = TenantRunConfig(tenant_id="t")
    cfg.tts_voice = "id-ID-GadisNeural"
    cfg.tts_provider = "edge_tts"
    m._load_pace_calibration(cfg, "dark_history")
    assert cfg.duration_calibration, "koefisien tertutup oleh baris warisan — cacat 42 detik kembali"
    assert cfg.duration_calibration["sec_per_char"] == 0.06299
