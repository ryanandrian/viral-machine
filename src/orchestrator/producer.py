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
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    tenant_id  = channel_row["tenant_id"]
    channel_id = str(channel_row.get("id") or channel_row.get("channel_id") or "default")
    niche      = channel_row.get("niche")
    inv_id = inventory.record_producing(tenant_id, channel_id, niche,
                                        {"channel": channel_row.get("channel_name")})
    try:
        tc = tenant_config_from_channel(channel_row, niche=niche)
        # Diversity Engine (Phase 6.2, DESAIN §9.1) — hint rotasi per-channel (LRU lookback).
        # PREFERENSI saja (quality tetap di-gate ScriptAnalyzer/skor hook); fail-soft → None.
        try:
            from src.intelligence.diversity import DiversityEngine
            from src.intelligence.config import get_niches
            _div = DiversityEngine()
            tc.preferred_hook_pattern = _div.pick_hook_pattern(channel_id)
            tc.visual_seed = _div.pick_seed(channel_id)
            # Music-mood rotation (§9.1): kandidat = niches.mood_priority (semua niche-appropriate,
            # admin-kurasi) → LRU per-channel. Tak ada pool → None (perilaku lama, non-breaking).
            _mood_pool = (get_niches().get(niche) or {}).get("mood_priority") or []
            tc.preferred_music_mood = _div.pick(channel_id, "music", _mood_pool) if _mood_pool else None
        except Exception as _de:
            logger.debug(f"[Producer] diversity hint skip (ch={channel_id}): {_de}")
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
        _script = result.get("script", {}) or {}
        _winner = (_script.get("hook_data") or {}).get("winner") or {}
        inventory.mark_ready(inv_id, vkey, metadata={
            "run_id":    run_id,
            "video_s3":  vkey,
            "thumb_s3":  tkey,
            "script":    _script,
            "niche":     result.get("niche"),
            # Dimensi diversity (Phase 6.2) → publisher tulis ke `videos` (histori lookback berikutnya)
            "hook_pattern": _winner.get("formula"),
            "visual_seed":  tc.visual_seed,
            # mood AKTUAL = mood rotasi yang di-inject ke music_selector (bukan saran LLM
            # background_music_mood yang TAK dipakai music_selector). Null bila niche tanpa mood_priority.
            "music_mood":   tc.preferred_music_mood,
            "viral_score":  _script.get("viral_score"),
            "insights_grade": _script.get("insights_grade", ""),
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


# ── DIRECT / ON-DEMAND (V2 "1 mesin, 2 mode") ──────────────────────────────
# Jalur prioritas: tenant/admin minta produksi 1 job SEKARANG (test/retry/admin_test).
# Di-drain SEBELUM stok-buffer, pakai semaphore+pool yang SAMA (anti-OOM utuh). Mesin = pipeline.run().
def run_direct(sb, job: dict) -> None:
    """Eksekusi 1 direct_job: produce + publish (privacy sesuai job) + tulis production_runs.
    Context run_id → pipeline_run_logs (live-tail D5). Tandai status di direct_jobs."""
    from datetime import datetime, timezone
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    jid = job["id"]
    tenant_id = job["tenant_id"]
    run_id = f"direct-{str(jid)[:8]}"
    _now = lambda: datetime.now(timezone.utc).isoformat()

    ch = (sb.table("channels").select("*").eq("id", job["channel_id"]).limit(1).execute().data or [None])[0]
    if not ch:
        sb.table("direct_jobs").update({"status": "failed", "error": "channel tak ditemukan", "completed_at": _now()}).eq("id", jid).execute()
        return
    sb.table("direct_jobs").update({"run_id": run_id}).eq("id", jid).execute()

    niche = job.get("niche") or ch.get("niche")
    status, yt_url, err, qc_ok = "failed", None, None, False
    try:
        tc = tenant_config_from_channel(ch, niche=niche)
        try:
            tc.publish_privacy = job.get("publish_privacy") or "private"
        except Exception:
            pass
        with logger.contextualize(tenant_id=tenant_id, run_id=run_id):
            result = Pipeline().run(tc, publish=True)
        # Sumber kebenaran = ADA URL publish + status QC (pipeline set steps.qc.passed).
        # Opsi A: QC-fail TETAP menghasilkan URL (di-publish PRIVAT) → JANGAN dilabeli 'success'.
        yt_url = (result.get("published", {}).get("youtube") or {}).get("url")
        qc     = result.get("steps", {}).get("qc", {})
        qc_ok  = bool(qc.get("passed"))
        if yt_url and qc_ok:
            status = "success"
        elif yt_url and not qc_ok:
            status = "qc_failed"   # di-publish PRIVAT + advisory (tenant putuskan public/take-down)
            err = qc.get("reason") or "QC tak lolos — di-publish privat untuk ditinjau"
        else:
            status = "failed"
            err = qc.get("reason") or result.get("error") or "tidak publish (QC/produksi gagal)"
    except Exception as e:
        err = str(e)
        logger.error(f"[Direct] job {jid} gagal: {e}")

    # Tulis production_runs (muncul di Runs/D5). queue_id NULL (bukan jalur pipeline_queue).
    try:
        sb.table("production_runs").insert({
            "tenant_id": tenant_id, "run_id": run_id, "channel_id": str(job["channel_id"]),
            "niche": niche, "status": status, "youtube_url": yt_url,
            "qc_passed": qc_ok, "error_message": err,
            "run_metadata": {"direct": True, "job_type": job.get("job_type")},
        }).execute()
    except Exception as e:
        logger.warning(f"[Direct] tulis production_runs gagal: {e}")

    # direct_jobs.status CHECK = pending|producing|published|failed → qc_failed (sudah ter-publish
    # PRIVAT) dipetakan ke 'published'; nuansa QC-fail ada di production_runs.status + advisory.
    sb.table("direct_jobs").update({
        "status": "published" if status in ("success", "qc_failed") else "failed",
        "error": err, "completed_at": _now(),
    }).eq("id", jid).execute()


def drain_direct(sb, pool: ThreadPoolExecutor, sem: threading.Semaphore) -> int:
    """Drain direct_jobs pending SEBELUM stok-buffer. Acquire semaphore yang SAMA (≤core → anti-OOM).
    Idle → diproses tick berikut (≤idle_seconds); sibuk → paling depan saat 1 core bebas. Return jumlah submit."""
    jobs = (sb.table("direct_jobs").select("*").eq("status", "pending").order("created_at").limit(64).execute().data) or []
    from datetime import datetime, timezone
    submitted = 0
    for job in jobs:
        if not sem.acquire(blocking=False):
            break   # semua core sibuk → tunggu tick berikut (rem sama)
        sb.table("direct_jobs").update({"status": "producing", "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", job["id"]).execute()

        def _task(job=job):
            try:
                run_direct(sb, job)
            finally:
                sem.release()

        pool.submit(_task)
        submitted += 1
    return submitted


def _active_channels(sb) -> list:
    return sb.table("channels").select("*").eq("is_active", True).execute().data or []


def plan_and_submit(sb, pool: ThreadPoolExecutor, sem: threading.Semaphore, depth: int) -> int:
    """Satu siklus: hitung defisit buffer per-channel → submit produksi sampai slot core habis.
    Return jumlah job di-submit. Rem: hanya submit bila semaphore (core) tersedia (anti-overload)."""
    channels = _active_channels(sb)
    from src.billing.limits import gate_for_channel
    deficits = []
    for ch in channels:
        # Phase 8a — gate monetisasi: jangan produksi (buang compute) utk tenant suspended/cancelled.
        if not gate_for_channel(sb, ch)["can_produce"]:
            logger.info(f"[Producer] skip ch={ch.get('id')} tenant={ch.get('tenant_id')} — subscription tidak aktif")
            continue
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
                drain_direct(sb, pool, sem)     # jalur prioritas (test/retry/admin) — semaphore SAMA
                plan_and_submit(sb, pool, sem, depth)   # stok-buffer dgn slot core sisa
            except Exception as e:
                logger.error(f"[Producer] loop error: {e}")
            time.sleep(idle_seconds)
