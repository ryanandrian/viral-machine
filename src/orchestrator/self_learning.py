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
    fetched = computed = weighted = 0
    weighted_tenants = set()
    for ch in channels:
        tid = ch["tenant_id"]
        cid = str(ch.get("id"))
        # ANALYTICS + meta PER-CHANNEL: ChannelAnalytics pakai koneksi YouTube channel ini (pool tenant_youtube_accounts).
        # FIX AKAR RETENSI-0 (2026-07-13): fetch WAJIB per-CHANNEL dgn koneksinya sendiri — token OAuth
        # terikat per-IDENTITAS channel (RAD & MVT = 2 koneksi pada 1 akun Google). Gerbang lama
        # "sekali per tenant" menyapu video SEMUA channel dgn token channel pertama → Analytics balas
        # SUKSES-TAPI-KOSONG utk channel lain → watch/retensi 0 senyap (akar sejati saga retensi).
        # Tak redundan: sapu di fetch_and_store kini ter-scope channel_id (tiap video tetap 1×).
        try:
            from src.analytics.channel_analytics import ChannelAnalytics
            ca = ChannelAnalytics(tenant_id=tid, channel_id=cid)
            ca.sync_channel_meta(tid, channel_id=cid)   # nama/platform_channel_id/subs — scope channel ini
            ca.fetch_and_store(tid, channel_id=cid)
            fetched += 1
        except Exception as e:
            logger.warning(f"[self_learning] analytics gagal ch={cid} tenant={tid}: {e}")
        # COMPUTE insights (channel-scoped tag)
        try:
            from src.analytics.performance_analyzer import PerformanceAnalyzer
            res = PerformanceAnalyzer().compute_and_store(tid, channel_id=cid)
            computed += 1
            logger.info(f"[self_learning] insights ch={cid}: grade={res.get('grade')} n={res.get('videos_analyzed')}")
        except Exception as e:
            logger.warning(f"[self_learning] compute insights gagal ch={cid}: {e}")
        # VIRAL-WEIGHTS adaptif (S3-A) — PER-TENANT (kolom tenant_configs), sekali per tenant.
        if tid not in weighted_tenants:
            try:
                from src.analytics.viral_weight_optimizer import ViralWeightOptimizer
                vw = ViralWeightOptimizer(sb).compute_and_store(tid)
                weighted += 1
                weighted_tenants.add(tid)
                logger.info(f"[self_learning] viral_weights tenant={tid}: status={vw.get('status')} n={vw.get('n')}")
            except Exception as e:
                logger.warning(f"[self_learning] viral_weights gagal tenant={tid}: {e}")
    logger.info(f"[self_learning] run_once: fetch={fetched} channel | compute={computed} channel | weights={weighted} tenant")
    return {"fetched": fetched, "computed": computed, "weighted": weighted}


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
