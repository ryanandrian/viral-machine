"""
Producer — loop persisten jaga buffer per-channel (Phase 5.3, DESAIN §12c).

JANTUNG anti-OOM: render dibatasi **semaphore = MAX_CONCURRENT_RENDER (jumlah core)**,
dipegang SATU proses loop hidup (BUKAN cron — cron spawn buta = tak ada rem = OOM, terbukti).
produce_one = pipeline.run(publish=False) → upload video+thumbnail ke S3 → simpan SEMUA input
publish (script/metadata) di content_inventory → status ready. Publisher (proses terpisah)
yang melakukan publish dari buffer.
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from src.orchestrator import inventory
from src.utils import s3_buffer


def max_concurrent_render() -> int:
    """Rem anti-OOM: = jumlah core (config-driven PRODUCER_MAX_RENDER). Lihat §12c."""
    v = os.getenv("PRODUCER_MAX_RENDER")
    if v and v.isdigit():
        return max(1, int(v))
    return max(1, os.cpu_count() or 2)


def default_buffer_depth() -> int:
    """Target stok ready per-channel (config-driven). Per-niche override = channels.buffer_depth."""
    v = os.getenv("PRODUCER_BUFFER_DEPTH")
    return int(v) if v and v.isdigit() else 2


def produce_one(channel_row: dict) -> int | None:
    """Produksi 1 video (TANPA publish) → buffer. Return inv_id ready, atau None bila gagal/QC fail."""
    from src.intelligence.config import TenantConfig
    from src.orchestrator.pipeline import Pipeline

    tenant_id  = channel_row["tenant_id"]
    channel_id = str(channel_row.get("id") or channel_row.get("channel_id") or "default")
    niche      = channel_row.get("niche")
    inv_id = inventory.record_producing(tenant_id, channel_id, niche,
                                        {"channel": channel_row.get("channel_name")})
    try:
        tc = TenantConfig(tenant_id=tenant_id, niche=niche)
        result = Pipeline().run(tc, publish=False)   # PRODUCE-ONLY
        if (result.get("status") != "success" or not result.get("video_path")
                or not result.get("steps", {}).get("qc", {}).get("passed")):
            inventory.mark_failed(inv_id, result.get("error") or "produce/QC gagal")
            return None

        run_id = result["run_id"]
        video  = result["video_path"]
        thumb  = result.get("thumbnail_path")
        vkey = f"{tenant_id}/{channel_id}/{run_id}.mp4"
        s3_buffer.upload(video, vkey)
        tkey = None
        if thumb and os.path.exists(thumb):
            tkey = f"{tenant_id}/{channel_id}/{run_id}.jpg"
            s3_buffer.upload(thumb, tkey)

        # Persist SEMUA input publish (publisher = proses terpisah, tak punya file lokal)
        inventory.mark_ready(inv_id, vkey, metadata={
            "run_id":    run_id,
            "video_s3":  vkey,
            "thumb_s3":  tkey,
            "script":    result.get("script", {}),
            "niche":     result.get("niche"),
        })
        # Aset berat sudah di buffer → bersihkan lokal
        for p in (video, thumb):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        logger.info(f"[Producer] buffer ready: {vkey} (inv {inv_id})")
        return inv_id
    except Exception as e:
        inventory.mark_failed(inv_id, str(e))
        logger.error(f"[Producer] produce gagal (tenant={tenant_id}, ch={channel_id}): {e}")
        return None


def _active_channels(sb) -> list:
    return sb.table("channels").select("*").eq("is_active", True).execute().data or []


def plan_and_submit(sb, pool: ThreadPoolExecutor, sem: threading.Semaphore, depth: int) -> int:
    """Satu siklus: hitung defisit buffer per-channel → submit produksi sampai slot core habis.
    Return jumlah job di-submit. Rem: hanya submit bila semaphore (core) tersedia (anti-overload)."""
    channels = _active_channels(sb)
    deficits = []
    for ch in channels:
        cid = str(ch.get("id"))
        stok = inventory.buffer_depth(cid, "ready") + inventory.buffer_depth(cid, "producing")
        target = ch.get("buffer_depth") or depth
        if stok < target:
            deficits.append((target - stok, ch))
    deficits.sort(key=lambda x: -x[0])   # buffer paling tipis dulu (§12c prioritas)

    submitted = 0
    for _, ch in deficits:
        if not sem.acquire(blocking=False):
            break   # semua core sibuk → tunggu siklus berikut (REM anti-OOM)

        def _task(ch=ch):
            try:
                produce_one(ch)
            finally:
                sem.release()

        pool.submit(_task)
        submitted += 1
    return submitted


def run_forever(idle_seconds: int = 10) -> None:
    """Loop persisten Producer (§12c). MAX_CONCURRENT_RENDER = core (semaphore = rem)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    MAX, depth = max_concurrent_render(), default_buffer_depth()
    logger.info(f"[Producer] start | MAX_CONCURRENT_RENDER={MAX} (core) | buffer_depth={depth}")
    sem = threading.Semaphore(MAX)
    with ThreadPoolExecutor(max_workers=MAX, thread_name_prefix="producer") as pool:
        while True:
            try:
                plan_and_submit(sb, pool, sem, depth)
            except Exception as e:
                logger.error(f"[Producer] loop error: {e}")
            time.sleep(idle_seconds)
