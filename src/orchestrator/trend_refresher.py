"""
TrendRefresher — thread worker pengisi `trend_cache` (TREND_RADAR_ARCHITECTURE.md §3 Pilar-1 + §5).

DI LUAR hot-path produce. Fetch 1× per (niche, geo, source) per TTL, PACED (anti-429).
request_sumber = O(niche × geo ÷ TTL) → KONSTAN vs jumlah tenant. Produce hanya BACA cache.
Pola thread sama dgn producer/publisher/janitor/email_outbox/heartbeat (worker_decoupled).
"""

import os
import time

from loguru import logger


def _int_config(sb, key: str, default: int) -> int:
    try:
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception:
        pass
    return default


def _active_region_keys(sb) -> list:
    """peak_region tenant yang punya channel aktif (default ['us']). Cache hanya geo yang dipakai."""
    try:
        chans = sb.table("channels").select("tenant_id").eq("is_active", True).execute().data or []
        tids = list({c["tenant_id"] for c in chans})
        regions = set()
        for tid in tids:
            try:
                r = sb.table("tenant_configs").select("peak_region").eq("tenant_id", tid).limit(1).execute().data
                rk = (r[0].get("peak_region") if r else None) or "us"
            except Exception:
                rk = "us"
            regions.add(str(rk).lower())
        return sorted(regions) or ["us"]
    except Exception as e:
        logger.warning(f"[TrendRefresher] active regions gagal: {e}")
        return ["us"]


def _active_niches(sb) -> list:
    """Semua niche AKTIF di katalog → (niche_id, keywords). Cache utk semua (random-mode bisa pakai apa saja;
    match §5: O(niche×geo))."""
    try:
        from src.intelligence.config import get_niches
        niches = get_niches()
        return [(nid, (nd.get("keywords") or []))
                for nid, nd in niches.items()
                if nd.get("is_active", True) and nd.get("keywords")]
    except Exception as e:
        logger.warning(f"[TrendRefresher] active niches gagal: {e}")
        return []


def run_once(sb, radar=None) -> int:
    """Satu siklus: refresh sumber basi utk semua (niche aktif × geo aktif) + sumber global. Return jumlah cache ditulis."""
    from src.intelligence.trend_radar import TrendRadar
    radar  = radar or TrendRadar()
    ttl    = _int_config(sb, "trend_cache_ttl_sec", 43200)
    pacing = _int_config(sb, "trend_refresh_pacing_ms", 3000) / 1000.0
    yt_key = os.getenv("YOUTUBE_API_KEY", "") or os.getenv("YT_PLATFORM_API_KEY", "")

    niches  = _active_niches(sb)
    regions = _active_region_keys(sb)
    written = 0
    for nid, kws in niches:
        for rk in regions:
            try:
                w = radar.refresh_niche_geo(nid, rk, kws, ttl_sec=ttl, yt_api_key=yt_key, only_stale=True)
                written += w
                if w:
                    logger.info(f"[TrendRefresher] refreshed niche={nid} geo={rk} ({w} sumber)")
            except Exception as e:
                logger.warning(f"[TrendRefresher] refresh {nid}/{rk} gagal: {e}")
            time.sleep(pacing)   # pace antar (niche,geo) → jaga Google Trends di bawah rate-limit (anti-429)
    try:
        written += radar.refresh_global(ttl_sec=ttl, only_stale=True)
    except Exception as e:
        logger.warning(f"[TrendRefresher] refresh_global gagal: {e}")
    return written


def run_forever(idle_seconds: int = 1800) -> None:
    """Loop persisten (cek tiap 30 mnt; hanya fetch yang BASI > TTL → mayoritas siklus murah)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    logger.info("[TrendRefresher] start | isi trend_cache (paced, TTL & pacing dari app_config)")
    while True:
        try:
            n = run_once(sb)
            logger.info(f"[TrendRefresher] cycle selesai — {n} cache ditulis")
        except Exception as e:
            logger.error(f"[TrendRefresher] loop error: {e}")
        time.sleep(idle_seconds)
