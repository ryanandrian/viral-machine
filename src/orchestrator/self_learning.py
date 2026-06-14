"""
Self-Learning loop (Phase 6.1, 🥇 CORE MOAT) — DESAIN §8.

Tiap cadence: per channel aktif → (1) FETCH YouTube Analytics (24-72h post-publish) ke
`video_analytics`, (2) COMPUTE `channel_insights` (niche_weights/top_hooks/content_type/avoid).
Insights di-inject balik ke generasi (ScriptEngine/NicheSelector/HookOptimizer) → mesin "makin
pintar tiap hari". Channel-scoped (compute pakai channel_id; full per-channel filter = 6.4).

Cadence config-driven (SELF_LEARNING_INTERVAL_SEC, default 24j). Loop persisten via worker_decoupled.
Fetch = read-only YT API; idempotent upsert. Best-effort (gagal 1 channel tak ganggu lain).
"""

import os
import time

from loguru import logger


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def run_once(sb=None) -> dict:
    sb = sb or _sb()
    channels = (sb.table("channels").select("tenant_id,id,channel_name")
                .eq("is_active", True).execute().data) or []
    fetched = computed = 0
    fetched_tenants = set()
    for ch in channels:
        tid = ch["tenant_id"]
        cid = str(ch.get("id"))
        # FETCH analytics per-tenant (sekali; fetch_and_store tenant-wide + idempotent)
        if tid not in fetched_tenants:
            try:
                from src.analytics.channel_analytics import ChannelAnalytics
                ChannelAnalytics(tenant_id=tid).fetch_and_store(tid)
                fetched += 1
            except Exception as e:
                logger.warning(f"[self_learning] fetch analytics gagal tenant={tid}: {e}")
            fetched_tenants.add(tid)
        # COMPUTE insights (channel-scoped tag)
        try:
            from src.analytics.performance_analyzer import PerformanceAnalyzer
            res = PerformanceAnalyzer().compute_and_store(tid, channel_id=cid)
            computed += 1
            logger.info(f"[self_learning] insights ch={cid}: grade={res.get('grade')} n={res.get('videos_analyzed')}")
        except Exception as e:
            logger.warning(f"[self_learning] compute insights gagal ch={cid}: {e}")
    logger.info(f"[self_learning] run_once: fetch={fetched} tenant | compute={computed} channel")
    return {"fetched": fetched, "computed": computed}


def run_forever(interval_seconds=None) -> None:
    """Loop persisten self-learning — dipanggil worker_decoupled sebagai thread."""
    sb = _sb()
    interval = int(interval_seconds or os.getenv("SELF_LEARNING_INTERVAL_SEC", "86400"))  # default 24j
    logger.info(f"[self_learning] start | tiap {interval}s (fetch YT analytics + compute insights)")
    while True:
        try:
            run_once(sb)
        except Exception as e:
            logger.error(f"[self_learning] loop error: {e}")
        time.sleep(interval)
