"""
Viral Machine Worker — polling loop untuk pipeline_queue.

Menggantikan semua crontab schedule entries.
Scheduler (pg_cron di Supabase) insert job ke pipeline_queue setiap slot.
Worker ini poll queue, eksekusi pipeline, tulis hasil ke production_runs.

Deploy di VPS (crontab — hanya satu baris):
  @reboot cd /home/rad4vm/viral-machine && /usr/bin/python3.11 scripts/worker.py >> logs/worker.log 2>&1
"""

import os
import sys
import time
import signal
from datetime import datetime, timezone, timedelta
from loguru import logger
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

POLL_INTERVAL   = 30   # detik antara poll jika tidak ada job
STALE_THRESHOLD = 30   # menit — job "running" lebih dari ini dianggap crash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY tidak ada di .env")
    return create_client(url, key)


def _recover_stale_jobs(sb) -> None:
    """
    Reset job yang stuck di 'running' saat worker restart.
    Terjadi jika worker crash di tengah eksekusi job sebelumnya.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD)).isoformat()
        stale  = (
            sb.table("pipeline_queue")
            .select("id, tenant_id")
            .eq("status", "running")
            .lt("started_at", cutoff)
            .execute()
        )
        for job in stale.data or []:
            sb.table("pipeline_queue").update({
                "status":        "failed",
                "completed_at":  _now(),
                "error_message": f"Stale — worker restart atau timeout >{STALE_THRESHOLD}m",
            }).eq("id", job["id"]).execute()
            logger.warning(f"[Worker] Reset stale job: tenant={job['tenant_id']} id={job['id']}")
    except Exception as e:
        logger.warning(f"[Worker] Stale recovery gagal (non-fatal): {e}")


def _run_production(job: dict, sb) -> None:
    """Eksekusi pipeline untuk satu tenant. Tulis hasil ke production_runs."""
    tenant_id = job["tenant_id"]
    queue_id  = job["id"]

    logger.info(f"[Worker] ▶ Start  tenant={tenant_id}  queue_id={queue_id}")

    sb.table("pipeline_queue").update({
        "status":     "running",
        "started_at": _now(),
    }).eq("id", queue_id).execute()

    try:
        from src.intelligence.config import TenantConfig
        from src.config.tenant_config import load_tenant_config
        from src.orchestrator.pipeline import Pipeline

        run_config = load_tenant_config(tenant_id)
        niche      = getattr(run_config, "niche", "universe_mysteries")
        tenant     = TenantConfig(tenant_id=tenant_id, niche=niche)

        result = Pipeline().run(tenant, publish=True)

        # Tulis ringkasan ke production_runs
        yt          = result.get("published", {}).get("youtube", {})
        script_step = result.get("steps", {}).get("script", {})
        qc_step     = result.get("steps", {}).get("qc", {})

        sb.table("production_runs").insert({
            "queue_id":         queue_id,
            "tenant_id":        tenant_id,
            "run_id":           result.get("run_id"),
            "topic":            script_step.get("title", ""),
            "niche":            result.get("niche", niche),
            "viral_score":      script_step.get("viral_score"),
            "llm_provider":     script_step.get("llm_provider"),
            "status":           result.get("status"),
            "youtube_url":      yt.get("url"),
            "youtube_video_id": yt.get("video_id"),
            "elapsed_seconds":  result.get("elapsed_seconds"),
            "qc_passed":        qc_step.get("passed"),
            "error_message":    str(result.get("error", ""))[:500] or None,
            "run_metadata":     result,
        }).execute()

        final = "done" if result.get("status") == "success" else "failed"
        sb.table("pipeline_queue").update({
            "status":       final,
            "completed_at": _now(),
        }).eq("id", queue_id).execute()

        logger.info(
            f"[Worker] ✅ Done  tenant={tenant_id}  "
            f"status={final}  elapsed={result.get('elapsed_seconds')}s"
        )

    except Exception as e:
        logger.error(f"[Worker] ❌ Failed  tenant={tenant_id}  error={e}")
        sb.table("pipeline_queue").update({
            "status":        "failed",
            "completed_at":  _now(),
            "error_message": str(e)[:500],
        }).eq("id", queue_id).execute()


def _poll(sb) -> bool:
    """
    Ambil satu pending job dari queue dan eksekusi.
    Return True jika ada job diproses, False jika queue kosong.
    """
    try:
        res = (
            sb.table("pipeline_queue")
            .select("*")
            .eq("status", "pending")
            .order("scheduled_at")
            .limit(1)
            .execute()
        )
        if not res.data:
            return False

        job = res.data[0]

        if job["job_type"] == "production":
            _run_production(job, sb)
        else:
            logger.warning(f"[Worker] Job type tidak dikenal: {job['job_type']} — skip")
            sb.table("pipeline_queue").update({
                "status":        "failed",
                "completed_at":  _now(),
                "error_message": f"Unsupported job_type: {job['job_type']}",
            }).eq("id", job["id"]).execute()

        return True

    except Exception as e:
        logger.error(f"[Worker] Poll error: {e}")
        return False


def main():
    logger.info("[Worker] ══════════════════════════════════════════")
    logger.info("[Worker] Viral Machine Worker — started")
    logger.info(f"[Worker] Poll interval : {POLL_INTERVAL}s")
    logger.info(f"[Worker] Stale timeout : {STALE_THRESHOLD}m")
    logger.info("[Worker] ══════════════════════════════════════════")

    sb      = _get_supabase()
    running = True

    def _shutdown(sig, _frame):
        nonlocal running
        logger.info(f"[Worker] Signal {sig} — stop setelah job selesai")
        running = False

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    _recover_stale_jobs(sb)

    while running:
        had_job = _poll(sb)
        if not had_job:
            logger.debug(f"[Worker] Idle — next poll in {POLL_INTERVAL}s")
            time.sleep(POLL_INTERVAL)
        # Jika ada job: langsung poll lagi tanpa delay


if __name__ == "__main__":
    main()
