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
    niche: str = "universe_mysteries"
    language: str = "en"
    target_audience: str = "global"
    videos_per_day: int = 1
    platforms: list = field(default_factory=lambda: ["youtube"])
    posting_hour: int = 8
    style: str = "educational_entertaining"
    hook_style: str = "question"
    video_duration: int = 58

@dataclass
class SystemConfig:
    """Konfigurasi mesin (platform) — bukan milik tenant.
    Hanya berisi infra yang dioperasikan platform: Supabase, R2.
    API key tenant (OpenAI, Anthropic, ElevenLabs, dll) disimpan di tenant_configs Supabase.
    """
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    r2_endpoint: str = field(default_factory=lambda: os.getenv("R2_ENDPOINT", ""))
    r2_access_key: str = field(default_factory=lambda: os.getenv("R2_ACCESS_KEY", ""))
    r2_secret_key: str = field(default_factory=lambda: os.getenv("R2_SECRET_KEY", ""))
    r2_bucket: str = field(default_factory=lambda: os.getenv("R2_BUCKET", "viral-machine"))

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
            "hook_templates":   row.get("hook_templates") or [],
            "is_active":        row.get("is_active", True),
            "voice_profile":    row.get("voice_profile") or {},
            "visual_style":     row.get("visual_style") or {},
            "visual_fallbacks": row.get("visual_fallbacks") or [],
            "mood_priority":    row.get("mood_priority") or [],
            "default_hashtags": row.get("default_hashtags") or [],
            "section_timing":        row.get("section_timing") or {},
            "image_quality_tags":    row.get("image_quality_tags") or "",
            "image_negative_prompt": row.get("image_negative_prompt") or "",
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
        dict: {niche_id: {name, keywords, style, target_emotion, voice_profile,
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


def invalidate_niches_cache() -> None:
    """
    Reset memory cache — paksa reload dari Supabase pada pemanggilan get_niches() berikutnya.
    Dipanggil jika admin update niches table dan ingin perubahan langsung berlaku.
    """
    global _NICHES_CACHE
    _NICHES_CACHE = None
