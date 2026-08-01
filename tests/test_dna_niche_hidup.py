"""DNA NICHE HARUS SAMPAI KE LLM — termasuk suntingan yang dibuat SETELAH pekerja menyala.

Issue utama owner #3: "SELURUH DNA NICHE HARUS MENJADI ASUPAN LLM DALAM MEMBANGUN NARASI".

Cacat yang ditutup (ditemukan & diperbaiki 2026-08-02): `get_niches()` menyimpan hasil bacaannya
tanpa masa berlaku sama sekali — sekali terbaca, dipegang sampai proses mati. Pekerja produksi hidup
berjam-jam sampai berhari-hari, jadi seluruh DNA yang menjadi asupan LLM (deskripsi, persona narasi,
gaya visual, kriteria emosi, kata kunci, timing seksi, hashtag) adalah POTRET saat pekerja dinyalakan.
Admin menyunting niche di `/admin/niches`, tenant Business di `/niche-studio` — tersimpan benar di
DB, tak pernah sampai ke naskah.

`invalidate_niches_cache()` sudah ditulis persis untuk kasus ini, tapi NOL pemanggil — dan memang tak
bisa menolong: layar berjalan di proses Next.js, pekerja di proses Python.

Empat cache konfigurasi lain (`app_config`, `content_beats`, `format_catalog`, katalog LLM) sudah
memakai masa berlaku 300 detik sejak lama. Yang satu ini tertinggal.

Uji kedua di bawah menjaga agar perbaikannya TIDAK menanam cacat baru: memberi masa berlaku berarti
akan ada penyegaran, dan penyegaran bisa gagal. Kegagalan itu HARAM menjatuhkan produksi yang
sebelumnya berjalan mulus.
"""

import src.intelligence.config as cfg

_DNA_LAMA = {"sejarah": {"name": "Sejarah", "description": "Kisah masa lalu", "keywords": ["a"],
                         "style": "", "target_emotion": "", "is_active": True,
                         "narration_persona": {}, "visual_style": {}, "visual_fallbacks": [],
                         "mood_priority": [], "default_hashtags": [], "section_timing": {},
                         "image_quality_tags": "", "image_negative_prompt": "",
                         "emotion_scoring_criteria": "", "description_en": ""}}
_DNA_BARU = {"sejarah": {**_DNA_LAMA["sejarah"],
                         "description": "Kisah masa lalu yang belum pernah diceritakan",
                         "narration_persona": {"tone": "tenang, berwibawa"}}}


def _pakai(monkeypatch, sumber: list):
    """Ganti pembaca DB dengan urutan jawaban yang ditentukan. Elemen Exception = DB gagal."""
    sisa = list(sumber)

    def _palsu():
        jawab = sisa.pop(0) if sisa else sumber[-1]
        if isinstance(jawab, Exception):
            raise jawab
        return jawab

    monkeypatch.setattr(cfg, "_load_from_supabase", _palsu)
    monkeypatch.setattr(cfg, "_save_cache", lambda *_a, **_k: None)


def test_suntingan_dna_terbaca_tanpa_restart(monkeypatch):
    """Admin menyunting deskripsi & persona niche → pekerja yang SEDANG berjalan ikut membacanya."""
    cfg.invalidate_niches_cache()
    try:
        _pakai(monkeypatch, [_DNA_LAMA, _DNA_BARU])
        assert cfg.get_niches()["sejarah"]["description"] == "Kisah masa lalu"

        # Masih dalam masa berlaku → sengaja TIDAK menembak DB lagi (hemat, dan itu gunanya cache).
        assert cfg.get_niches()["sejarah"]["description"] == "Kisah masa lalu"

        # Masa berlaku lewat (meniru 5 menit berlalu) → DNA baru WAJIB terbaca, tanpa restart.
        cfg._NICHES_TS -= cfg._TTL + 1
        segar = cfg.get_niches()["sejarah"]
        assert segar["description"] == "Kisah masa lalu yang belum pernah diceritakan", (
            "DNA niche masih potret lama — suntingan admin tak pernah sampai ke LLM"
        )
        assert segar["narration_persona"] == {"tone": "tenang, berwibawa"}
    finally:
        cfg.invalidate_niches_cache()


def test_gangguan_db_saat_menyegarkan_tidak_menjatuhkan_produksi(monkeypatch):
    """DB berkedip saat penyegaran → pakai DNA yang sudah ada. Jangan berhenti, jangan kosong."""
    cfg.invalidate_niches_cache()
    try:
        _pakai(monkeypatch, [_DNA_LAMA, RuntimeError("koneksi putus")])
        assert cfg.get_niches()["sejarah"]["description"] == "Kisah masa lalu"

        cfg._NICHES_TS -= cfg._TTL + 1
        tetap = cfg.get_niches()          # tidak boleh melempar, tidak boleh kosong
        assert tetap["sejarah"]["description"] == "Kisah masa lalu"

        # Penanda waktu dimajukan → percobaan berikutnya tidak membanjiri DB tiap panggilan.
        panggilan = {"n": 0}
        asli = cfg._load_from_supabase

        def _hitung():
            panggilan["n"] += 1
            return asli()

        monkeypatch.setattr(cfg, "_load_from_supabase", _hitung)
        for _ in range(5):
            cfg.get_niches()
        assert panggilan["n"] == 0, "penyegaran gagal justru memicu tembakan DB beruntun"
    finally:
        cfg.invalidate_niches_cache()


def test_katalog_bahasa_tak_terhapus_saat_penyegaran_gagal(monkeypatch):
    """Katalog bahasa yang sudah benar tidak boleh dikosongkan hanya karena satu kedipan jaringan."""
    cfg._CONTENT_LANG_CACHE = {"id-ID": "Bahasa Indonesia"}
    cfg._CONTENT_LANG_TS = 0.0            # sudah kedaluwarsa → paksa penyegaran
    try:
        import supabase as _sb
        monkeypatch.setattr(_sb, "create_client",
                            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("putus")))
        assert cfg.content_language_name("id-ID") == "Bahasa Indonesia", (
            "katalog bahasa terhapus saat penyegaran gagal → prompt LLM kehilangan nama bahasa"
        )
    finally:
        cfg._CONTENT_LANG_CACHE, cfg._CONTENT_LANG_TS = None, 0.0
