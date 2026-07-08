import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
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
        niches[niche_id] = {
            "name":             row.get("name", niche_id),
            "keywords":         row.get("keywords") or [],
            "style":            row.get("style") or "",
            "target_emotion":   row.get("target_emotion") or "",
            "is_active":        row.get("is_active", True),
            "narration_persona": row.get("narration_persona") or row.get("voice_profile") or {},
            "visual_style":     row.get("visual_style") or {},
            "visual_fallbacks": row.get("visual_fallbacks") or [],
            "mood_priority":    row.get("mood_priority") or [],
            "default_hashtags": row.get("default_hashtags") or [],
            "section_timing":        row.get("section_timing") or {},
            "image_quality_tags":    row.get("image_quality_tags") or "",
            "image_negative_prompt": row.get("image_negative_prompt") or "",
            # BUG FIX 2026-07-04 (audit NICHE_DNA): kolom ini TIDAK pernah disalin → kriteria scoring
            # admin tak pernah sampai ke prompt QUALITY BAR (script_engine:497) & analyzer prioritas-1
            # (script_analyzer:74) — selalu jatuh ke derive/default. (hook_templates di-drop: fosil,
            # nol konsumen — hook via HOOK_FORMULAS + persona.hook_style.)
            "emotion_scoring_criteria": row.get("emotion_scoring_criteria") or "",
            # Voice = PER-CHANNEL (§10.B FINAL, owner 2026-06-23): niche provider-AGNOSTIK,
            # TIDAK menyimpan voice. narration_persona = gaya/persona narasi (membentuk TEKS naskah
            # via LLM, BUKAN pemilih suara). voice_key/voice_defaults niche = fosil (di-drop migr 0083).
        }
    return niches


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
    global _NICHES_CACHE
    if _NICHES_CACHE is not None:
        return _NICHES_CACHE

    # 1. Coba Supabase (primary source)
    try:
        niches = _load_from_supabase()
        _save_cache(niches)
        _NICHES_CACHE = niches
        print(f"[NicheRegistry] {len(niches)} niches loaded from Supabase")
        return _NICHES_CACHE
    except Exception as e:
        print(f"[NicheRegistry] Supabase tidak tersedia ({e}) — coba local cache")

    # 2. Coba local cache (admin-managed fallback)
    try:
        niches = _load_cache()
        if niches:
            _NICHES_CACHE = niches
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

def content_language_name(locale: str) -> str:
    """Nama bahasa utk prompt LLM (mis. 'id-ID' → 'Bahasa Indonesia') dari tabel content_languages.
    Cache per-proses; fail-soft → locale apa adanya (LLM paham kode BCP-47)."""
    global _CONTENT_LANG_CACHE
    loc = (locale or "").strip()
    if not loc:
        return "English"
    if _CONTENT_LANG_CACHE is None:
        try:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            r = sb.table("content_languages").select("locale, display_name").execute()
            _CONTENT_LANG_CACHE = {row["locale"]: (row.get("display_name") or row["locale"]) for row in (r.data or [])}
        except Exception:
            _CONTENT_LANG_CACHE = {}   # fail-soft; jangan retry tiap panggilan dalam proses ini
    return _CONTENT_LANG_CACHE.get(loc, loc)


def is_english_locale(locale: str) -> bool:
    """True utk en/en-US/en-GB/… — jalur en = perilaku lama PERSIS (blok bahasa tidak di-inject)."""
    return (locale or "").strip().lower().startswith("en") or not (locale or "").strip()


def invalidate_niches_cache() -> None:
    """
    Reset memory cache — paksa reload dari Supabase pada pemanggilan get_niches() berikutnya.
    Dipanggil jika admin update niches table dan ingin perubahan langsung berlaku.
    """
    global _NICHES_CACHE
    _NICHES_CACHE = None
