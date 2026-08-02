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


# ── KESALAHAN PALING MAHAL 2026-07-31: mengukur pada setelan suara yang BEDA dari produksi ─────────

def test_kalibrasi_MENOLAK_sampel_dari_setelan_suara_berbeda():
    """Dua hari pengukuran terbuang karena diukur pada baseline `-5%` sementara produksi memakai
    baseline lain — selisih 15% pada laju bicara, dan TIDAK ADA apa pun di sistem yang memberi tahu
    (kolom `speed` bernilai 1,0 di kedua dunia, karena speed hanya PENGALI di atas baseline).
    Koefisien dari sampel campur-baseline akan tampak terkalibrasi padahal salah untuk produksi.
    Sejak 0184: sampel wajib merekam setelan laju NYATA, dan yang berbeda DIBUANG eksplisit."""
    import inspect

    import src.production.pace_calibration as pc
    src = inspect.getsource(pc.compute_pace_calibration)
    assert "voice_rate" in src, "kalibrasi tidak lagi memeriksa setelan suara sampel"
    assert "setelan_suara_beda" in src, "sampel dari baseline berbeda tidak dilaporkan"


def test_adaptor_suara_mengekspos_setelan_yang_BENAR_dipakai():
    """Nilainya harus datang dari adaptor, bukan dihitung ulang di tempat lain (dua sumber = drift).

    Dilaporkan sebagai RASIO terhadap laju alami, bukan sebagai string milik penyedia. Sebabnya nyata:
    hanya Edge menulis `rate` bergaya persen, sehingga penjaga kalibrasi yang membandingkan STRING
    menolak setiap sampel ElevenLabs/fal/OpenAI — suara berbayar tak akan pernah bisa terkalibrasi,
    selamanya, tanpa satu pun pesan error."""
    from src.providers.tts.edge_tts import EdgeTTSProvider
    p = EdgeTTSProvider({"tts_voice": "id-ID-ArdiNeural", "niche": "x",
                         "tts_voice_default_settings": {"rate": "+15%"}, "tts_voice_settings": {}})
    assert p.rate == "+15%", "yang dikirim ke vendor berubah"
    assert p.effective_rate == "1.1500"
    p2 = EdgeTTSProvider({"tts_voice": "id-ID-ArdiNeural", "niche": "x",
                          "tts_voice_default_settings": {}, "tts_voice_settings": {}})
    assert p2.rate == "+0%", "baseline kosong harus ratio 1, bukan angka karangan"
    assert p2.effective_rate == "1.0000"


def test_edge_TIDAK_LAGI_membaca_tuas_kecepatan_warisan():
    """Ranjau yang masih hidup sampai 2026-08-01: solver kecepatan dicabut 31-Jul, tapi adaptor Edge
    MASIH membaca `tts_voice_settings[niche].speed` — lubang tempat solver dulu menyuntik. Nilai
    lamanya masih ada di DB setiap tenant, jadi channel BJ Yusroon (aktif, preset 90 dtk) dibacakan
    pada −17% sampai hari ini. Persis keluhan owner 'seperti orang malas'."""
    from src.providers.tts.edge_tts import EdgeTTSProvider
    p = EdgeTTSProvider({"tts_voice": "id-ID-GadisNeural", "niche": "dark_history",
                         "tts_voice_default_settings": {},
                         "tts_voice_settings": {"dark_history": {"speed": 0.83, "style": 0.55}}})
    assert p.rate == "+0%", "tuas kecepatan lewat warisan tenant HIDUP KEMBALI di adaptor Edge"
    assert p.effective_rate == "1.0000"


def test_kalibrasi_MENYAPU_baris_warisan_hanya_setelah_ada_baris_sah():
    """Ranjau nyata di DB (terhitung 2026-08-01): 11 dari 18 baris kalibrasi hanya berisi
    `delivery_wps` dari algoritma LAMA — dihitung lewat model jeda yang salah, dari sampel
    ber-kecepatan 0,7–1,3 (dunia yang sudah tidak ada). Tak bisa dipakai model baru, tak bisa
    diverifikasi asalnya, dan menunggu dipakai jalur cadangan.

    Yang dikunci di sini: penyapuan hanya menyasar baris TANPA koefisien, hanya untuk suara yang
    SUDAH punya baris sah, dan tidak menyentuh suara yang dikunci admin — supaya tak pernah ada
    keadaan 'kalibrasi hilang'."""
    import inspect

    import src.production.pace_calibration as pc
    src = inspect.getsource(pc.compute_pace_calibration)
    assert 'is_("sec_per_char", "null")' in src, "penyapuan tidak dibatasi ke baris tanpa koefisien"
    assert 'neq("niche", "*")' in src, "penyapuan bisa menghapus baris bintang yang berisi koefisien"
    assert "if vk in locked:" in src, "suara yang dikunci admin bisa tersapu"
    assert "sapu = [b[\"voice_key\"] for b in ditulis]" in src, \
        "penyapuan tidak dibatasi ke suara yang sudah punya baris sah"
