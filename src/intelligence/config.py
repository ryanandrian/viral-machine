import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TenantConfig:
    """Konfigurasi per tenant — setiap user punya instance ini"""
    tenant_id: str
    niche: str = ""  # diset eksplisit; '' → fail-loud (no global default niche)
    # BAHASA KONTEN (per-CHANNEL, locale BCP-47 dari channels.content_language — katalog content_languages).
    # Menentukan bahasa OUTPUT video: narasi/judul/deskripsi/hashtag (script engine, hook optimizer,
    # analyzer, publisher metadata). Prompt IMAGE tetap English by-design. Default en-US = perilaku lama.
    language: str = "en-US"
    target_audience: str = "global"
    videos_per_day: int = 1
    platforms: list = field(default_factory=lambda: ["youtube"])
    posting_hour: int = 8
    style: str = "educational_entertaining"
    hook_style: str = "question"
    video_duration: int = 58
    # Multi-Format (per-channel, MULTI_FORMAT §3) — None → perilaku lama (timing niche, WPS 2.4)
    duration_preset: int | None = None     # detik (rujuk duration_presets); null = legacy
    format_profile:  str | None = None     # rujuk format_profiles.format_key (sumber WPS)
    # Branded Content (per-channel, MULTI_FORMAT §6) — None/implicit → tanpa branding (non-breaking)
    landing_link:   str | None = None      # URL di deskripsi
    link_position:  str = "bottom"         # top | bottom
    cta_mode:       str = "implicit"       # implicit | soft_sell
    brand_name:     str | None = None
    brand_cta_text: str | None = None
    brand_logo:     str | None = None      # path/URL logo utk overlay
    logo_position:  str = "top-right"
    logo_size:      float = 0.12
    logo_opacity:   float = 0.85
    # Publish privacy per-channel (trial-safe) — DEFAULT private; tenant ubah ke public saat config cocok
    publish_privacy: str = "private"   # private | public | unlisted
    # AI Disclosure (Phase 6.3, §9.2) — YouTube status.containsSyntheticMedia. DEFAULT True (compliance-first).
    ai_disclosure: bool = True
    # Diversity Engine (Phase 6.2, AI Slop Defense §9.1) — hint TRANSIEN per-run, diset producer via
    # DiversityEngine (BUKAN dari channel_row). None → tanpa rotasi (non-breaking, perilaku lama).
    channel_id:             str | None = None   # untuk lookback rotasi per-channel
    # [B11] Batch 1.4 — target channel YouTube (channels.platform_channel_id). Dipakai pagar
    # salah-channel di YouTubePublisher.publish: identitas token HARUS == target ini.
    platform_channel_id:    str | None = None
    preferred_hook_pattern: str | None = None   # saran LRU hook formula — PREFERENSI (quality-first), bukan paksa
    visual_seed:            int | None = None   # seed image-gen → frame fingerprint unik
    preferred_music_mood:   str | None = None   # mood LRU dari niches.mood_priority (niche-safe) — §9.1
    run_kind:               str = ""            # asal run: ""=terjadwal · "test"=Test now tenant · "admin_test" · "retry" (utk tandai laporan)

def tenant_config_from_channel(channel_row: dict, niche=None) -> "TenantConfig":
    """Bangun TenantConfig dari row `channels` — thread field Multi-Format + Branded sekaligus.
    Dipakai producer & publisher → SATU sumber threading (hindari duplikasi/drift)."""
    return TenantConfig(
        tenant_id       = channel_row["tenant_id"],
        niche           = niche if niche is not None else (channel_row.get("niche") or ""),
        # Bahasa KONTEN per-channel (channels.content_language). NULL (channel lama pra-migrasi) → en-US.
        language        = channel_row.get("content_language") or "en-US",
        duration_preset = channel_row.get("duration_preset"),
        format_profile  = channel_row.get("format_profile"),
        landing_link    = channel_row.get("landing_link"),
        link_position   = channel_row.get("link_position") or "bottom",
        cta_mode        = channel_row.get("cta_mode") or "implicit",
        brand_name      = channel_row.get("brand_name"),
        brand_cta_text  = channel_row.get("brand_cta_text"),
        brand_logo      = channel_row.get("brand_logo"),
        logo_position   = channel_row.get("logo_position") or "top-right",
        logo_size       = float(channel_row.get("logo_size") or 0.12),
        logo_opacity    = float(channel_row.get("logo_opacity") or 0.85),
        publish_privacy = channel_row.get("publish_privacy") or "private",
        ai_disclosure   = (channel_row.get("ai_disclosure") if channel_row.get("ai_disclosure") is not None else True),
        channel_id      = (str(channel_row["id"]) if channel_row.get("id") is not None
                           else (str(channel_row["channel_id"]) if channel_row.get("channel_id") is not None else None)),
        platform_channel_id = channel_row.get("platform_channel_id"),
    )


@dataclass
class SystemConfig:
    """Konfigurasi mesin (platform) — bukan milik tenant.
    Hanya berisi infra yang dioperasikan platform: Supabase, R2.
    API key tenant (OpenAI, Anthropic, ElevenLabs, dll) disimpan di tenant_configs Supabase.
    """
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    # R2 (Cloudflare) DIHAPUS 2026-06-23 — aset musik = S3 Biznet Gio (kunci opak object_key, §10.G). Fosil v1.

VIRAL_SCORE_WEIGHTS = {
    "search_volume": 0.25,
    "trend_momentum": 0.25,
    "emotional_trigger": 0.20,
    "competition_gap": 0.15,
    "evergreen_potential": 0.15
}

system_config = SystemConfig()

# ── Niche Registry — fully Supabase-driven, no Python hardcode ─────────────
#
# Waterfall:
#   1. Memory cache (per process) — instan
#   2. Supabase niches table     — sumber kebenaran utama (admin-managed)
#   3. data/niches_cache.json    — local cache, auto-update setiap DB berhasil dibaca
#   4. RuntimeError              — pipeline berhenti + lapor Telegram
#
# data/niches_cache.json hanya bisa dikelola admin (server-side).
# Tenant tidak punya akses ke file ini.
# ────────────────────────────────────────────────────────────────────────────

_NICHES_CACHE: dict | None = None
_NICHES_TS: float = 0.0
# Masa berlaku cache — SAMA dengan empat cache konfigurasi lain (`app_config`, `content_beats`,
# `format_catalog`, katalog LLM) supaya seluruh konfigurasi bernapas dalam irama yang sama.
#
# CACAT YANG DITUTUP 2026-08-02: sebelum ini cache niche TIDAK punya masa berlaku sama sekali —
# sekali dibaca, dipegang sampai proses mati. Pekerja produksi hidup berjam-jam sampai berhari-hari,
# jadi SELURUH DNA niche yang menjadi asupan LLM (deskripsi, persona narasi, gaya visual, kriteria
# emosi, kata kunci, timing seksi, hashtag) adalah potret saat pekerja dinyalakan. Admin menyunting
# niche di `/admin/niches`, atau tenant Business di `/niche-studio` — tersimpan benar di DB, tak
# pernah sampai ke naskah. `invalidate_niches_cache()` sudah ditulis untuk kasus ini tapi TIDAK
# PERNAH dipanggil satu baris pun (mekanisme lahir mati), dan memang tak bisa menolong: layar
# berjalan di proses Next.js, pekerja di proses Python — memori keduanya terpisah.
_TTL = 300
_CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "niches_cache.json"


def _load_from_supabase() -> dict:
    """Load semua niche dari Supabase niches table (admin-managed)."""
    try:
        from supabase import create_client
    except ImportError as e:
        raise RuntimeError(f"supabase-py tidak terinstall: {e}")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/KEY tidak tersedia di environment")

    sb     = create_client(url, key)
    result = sb.table("niches").select("*").execute()
    rows   = result.data or []

    if not rows:
        raise RuntimeError(
            "Tabel niches kosong — admin perlu seed data niche via migration SQL"
        )

    niches = {}
    for row in rows:
        niche_id = row.get("niche_id")
        if not niche_id:
            continue
        niches[niche_id] = _rapikan_baris(row)
    return niches


# Bentuk kosong per-properti — dipakai supaya NULL di DB berperilaku sama seperti dulu bagi konsumen
# (list/dict/str, bukan None). Kunci di luar daftar ini ikut apa adanya.
_BENTUK_KOSONG: dict = {
    "keywords": [], "visual_fallbacks": [], "mood_priority": [], "default_hashtags": [],
    "narration_persona": {}, "visual_style": {}, "section_timing": {},
    "style": "", "target_emotion": "", "image_quality_tags": "", "image_negative_prompt": "",
    "emotion_scoring_criteria": "", "description": "", "description_en": "",
}


def _rapikan_baris(row: dict) -> dict:
    """SELURUH kolom baris niche → dict siap-pakai. **Tanpa daftar kolom tulis-tangan.**

    ═══ KENAPA TANPA DAFTAR (koreksi 2026-08-15, `SISA_KERJA [B32]` T4) ═══
    Versi lama menyalin kolom satu per satu. Kolom di luar daftar itu hilang SENYAP: tersimpan benar di
    DB, tak pernah sampai ke penulis naskah/gambar. Sudah memakan korban DUA kali — `emotion_scoring_criteria`
    (4-Jul) dan `description` (1-Agu, terisi 47 niche lalu berhenti di DB) — dan keduanya baru ketahuan
    setelah berbulan-bulan. Terukur 15-Agu: **16 kunci sampai ke mesin, 27 kolom ada di DB.**
    Menyalin SELURUH baris menghapus kelas cacatnya, bukan menambal kejadian ketiganya: kolom DNA yang
    admin tambahkan besok otomatis sampai ke mesin tanpa menyentuh berkas ini.
    Dijaga `tests/test_dna_niche_sampai_utuh.py` (kolom baru tak sampai ⇒ MERAH).

    Yang tetap dipertahankan dari versi lama: `name` jatuh ke `niche_id`, NULL → bentuk kosong sesuai
    tipenya, dan warisan `voice_profile` → `narration_persona` (kolomnya sudah di-drop migr 0083, tapi
    cache lokal lama bisa masih memuatnya).
    """
    d = dict(row)
    d["name"] = row.get("name") or row.get("niche_id")
    d["is_active"] = row.get("is_active", True)
    d["narration_persona"] = row.get("narration_persona") or row.get("voice_profile") or {}
    for k, kosong in _BENTUK_KOSONG.items():
        if k == "narration_persona":
            continue
        if not d.get(k):
            d[k] = type(kosong)() if isinstance(kosong, (list, dict)) else kosong
    d.pop("voice_profile", None)          # warisan; sudah dilebur ke narration_persona di atas
    return d


def muat_niche_segar(niche_id: str) -> dict:
    """Baca SATU niche LANGSUNG dari DB — melewati cache, bentuknya identik `get_niches()[id]`.

    Ada supaya penyatuan jalur baca TIDAK menanam jeda baru. Sebagian pembaca (pemilih musik, kategori
    YouTube, gaya visual per-run) selama ini membaca langsung ke DB = selalu mutakhir; memaksa mereka
    lewat cache 300 detik berarti menukar satu cacat dengan cacat lain. Pintu tetap SATU, pilihannya
    dua: bercache (`get_niches`) atau segar (fungsi ini). Gagal baca → dict kosong (pemanggil sudah
    memakai `.get(...)`), sama seperti perilaku kueri langsung yang digantikannya.
    """
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not key:
            return {}
        r = (create_client(url, key).table("niches").select("*")
             .eq("niche_id", niche_id).limit(1).execute())
        baris = (r.data or [None])[0]
        return _rapikan_baris(baris) if baris else {}
    except Exception as e:
        print(f"[NicheRegistry] muat_niche_segar('{niche_id}') gagal: {e}")
        return {}


def _save_cache(niches: dict) -> None:
    """Simpan registry ke local cache — admin-only fallback, auto-updated."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(niches, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[NicheRegistry] Cache save gagal (non-fatal): {e}")


def _load_cache() -> dict | None:
    """Load registry dari local cache (admin-only fallback)."""
    if not _CACHE_FILE.exists():
        return None
    with open(_CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not data:
        return None
    return data


def get_niches() -> dict:
    """
    Load niche registry. Fully Supabase-driven — tidak ada hardcode.

    Returns:
        dict: {niche_id: {name, keywords, style, target_emotion, narration_persona,
                          visual_style, visual_fallbacks, mood_priority,
                          hook_templates, is_active, ...}}

    Raises:
        RuntimeError: jika Supabase unreachable DAN local cache tidak ada.
                      Pipeline harus berhenti dan lapor ke Telegram.
    """
    global _NICHES_CACHE, _NICHES_TS
    if _NICHES_CACHE is not None and (time.time() - _NICHES_TS) < _TTL:
        return _NICHES_CACHE

    # 1. Coba Supabase (primary source)
    try:
        niches = _load_from_supabase()
        _save_cache(niches)
        _NICHES_CACHE, _NICHES_TS = niches, time.time()
        print(f"[NicheRegistry] {len(niches)} niches loaded from Supabase")
        return _NICHES_CACHE
    except Exception as e:
        print(f"[NicheRegistry] Supabase tidak tersedia ({e}) — coba local cache")

    # 1b. PENYEGARAN gagal tapi kita SUDAH punya data baik → pakai yang lama, JANGAN hentikan produksi.
    #     Tanpa cabang ini, memberi masa berlaku pada cache justru menanam cacat baru: satu kedipan
    #     jaringan saat penyegaran akan menjatuhkan produksi yang sebelumnya berjalan mulus (dan bisa
    #     memicu RuntimeError di bawah). Penanda waktu ikut dimajukan supaya percobaan berikutnya
    #     tidak membanjiri DB setiap panggilan.
    if _NICHES_CACHE is not None:
        _NICHES_TS = time.time()
        print(f"[NicheRegistry] ⚠️  penyegaran gagal — tetap memakai {len(_NICHES_CACHE)} niche "
              f"yang sudah ada (coba lagi ≤{_TTL} dtk)")
        return _NICHES_CACHE

    # 2. Coba local cache (admin-managed fallback)
    try:
        niches = _load_cache()
        if niches:
            _NICHES_CACHE, _NICHES_TS = niches, time.time()
            print(
                f"[NicheRegistry] ⚠️  {len(niches)} niches dari local cache "
                f"(data/niches_cache.json) — Supabase unreachable"
            )
            return _NICHES_CACHE
    except Exception as e:
        print(f"[NicheRegistry] Local cache gagal: {e}")

    # 3. Tidak ada yang tersedia — pipeline tidak boleh jalan
    raise RuntimeError(
        "[NicheRegistry] Niche config tidak tersedia.\n"
        "Supabase unreachable DAN local cache (data/niches_cache.json) tidak ada.\n"
        "Hubungi admin: periksa koneksi DB atau restore file data/niches_cache.json."
    )


# ── Bahasa konten — nama tampilan dari katalog content_languages (DB-driven, no hardcode) ──
_CONTENT_LANG_CACHE: dict | None = None
_CONTENT_LANG_TS: float = 0.0

def content_language_name(locale: str) -> str:
    """Nama bahasa utk prompt LLM (mis. 'id-ID' → 'Bahasa Indonesia') dari tabel content_languages.

    Masa berlaku `_TTL` sama dengan katalog konfigurasi lain: bahasa yang admin tambahkan ke katalog
    ikut terbaca pekerja yang sedang berjalan, tanpa restart. Fail-soft → locale apa adanya (LLM
    paham kode BCP-47)."""
    global _CONTENT_LANG_CACHE, _CONTENT_LANG_TS
    loc = (locale or "").strip()
    if not loc:
        return "English"
    if _CONTENT_LANG_CACHE is None or (time.time() - _CONTENT_LANG_TS) >= _TTL:
        try:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            r = sb.table("content_languages").select("locale, display_name").execute()
            _CONTENT_LANG_CACHE = {row["locale"]: (row.get("display_name") or row["locale"]) for row in (r.data or [])}
        except Exception:
            # Fail-soft. Isi yang SUDAH baik tidak dihapus — sebelum masa berlaku ada, baris ini
            # hanya berjalan sekali sehingga menulis {} tak berbahaya; dengan penyegaran berkala,
            # menulis {} akan MENGHAPUS katalog yang sudah benar hanya karena satu kedipan jaringan.
            if _CONTENT_LANG_CACHE is None:
                _CONTENT_LANG_CACHE = {}
        _CONTENT_LANG_TS = time.time()   # sukses atau gagal: jangan mencoba tiap panggilan
    return _CONTENT_LANG_CACHE.get(loc, loc)


def is_english_locale(locale: str) -> bool:
    """True utk en/en-US/en-GB/… — jalur en = perilaku lama PERSIS (blok bahasa tidak di-inject)."""
    return (locale or "").strip().lower().startswith("en") or not (locale or "").strip()


def invalidate_niches_cache() -> None:
    """
    Reset memory cache — paksa reload dari Supabase pada pemanggilan get_niches() berikutnya.

    Dipakai proses yang MENYUNTING niche lalu ingin membacanya kembali seketika (mis. skrip
    pemeliharaan). Layar admin/tenant TIDAK bisa memakainya — memorinya di proses lain; untuk itu
    yang bekerja adalah masa berlaku `_TTL` di atas.
    """
    global _NICHES_CACHE, _NICHES_TS
    _NICHES_CACHE, _NICHES_TS = None, 0.0
