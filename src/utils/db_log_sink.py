"""
Loguru → pipeline_run_logs (Phase 3 — DB-based logging).

Sink batch-insert log produksi ke Supabase agar UI bisa live-tail per-tenant
(Realtime D5) + persist error terstruktur (menutup DB-persist yang di-defer Phase 2).

Konteks (tenant_id/run_id/queue_id/step/category) dibaca dari loguru `record["extra"]`,
di-set via `logger.contextualize(...)` di worker (tenant_id/queue_id) + pipeline (run_id).
HANYA log yang punya `tenant_id` di context yang ditulis ke DB (skip noise global).

⚠️ WORKER produksi WAJIB pakai SUPABASE **service_role** key — RLS pipeline_run_logs:
INSERT hanya service_role (tak ada insert policy); anon/publishable ke-block.
Sink best-effort: kegagalan flush TIDAK pernah meng-crash pipeline (log ke stderr).
"""

import os
import sys
import threading

from loguru import logger

# Flush per-record (=1) untuk live-tail near-real-time (<5s) — gate Phase 3. Sink jalan
# di thread loguru background (enqueue=True) → TIDAK pernah memblok pipeline.
_BATCH_SIZE = 1
_buffer: list[dict] = []
_lock = threading.Lock()
_enabled = False


def _client():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _flush_locked() -> None:
    """Flush buffer ke DB. Caller HARUS memegang _lock."""
    if not _buffer:
        return
    rows = list(_buffer)
    _buffer.clear()
    try:
        _client().table("pipeline_run_logs").insert(rows).execute()
    except Exception as e:  # best-effort — JANGAN recurse ke sink / crash pipeline
        print(f"[db_log_sink] flush gagal ({len(rows)} rows): {e}", file=sys.stderr)


def _sink(message) -> None:
    rec = message.record
    ex = rec["extra"]
    row = {
        "tenant_id":  ex.get("tenant_id") or "unknown",
        "channel_id": ex.get("channel_id"),
        "queue_id":   str(ex["queue_id"]) if ex.get("queue_id") is not None else None,
        "run_id":     ex.get("run_id"),
        "level":      rec["level"].name,
        "step":       ex.get("step"),
        "category":   ex.get("category"),
        "message":    rec["message"],
        "metadata":   {"module": rec["name"], "function": rec["function"], "line": rec["line"]},
    }
    with _lock:
        _buffer.append(row)
        if len(_buffer) >= _BATCH_SIZE:
            _flush_locked()


def flush_logs() -> None:
    """Flush paksa sisa buffer (panggil di akhir run/job agar tail tak hilang).
    `logger.complete()` men-drain antrian enqueue dulu agar semua record terproses."""
    try:
        logger.complete()
    except Exception:
        pass
    with _lock:
        _flush_locked()


def setup_db_logging(level: str = "INFO") -> bool:
    """Daftarkan sink DB (idempotent). Hanya aktif jika SUPABASE_URL/KEY ada.
    Filter: hanya log dengan tenant_id di context (log produksi). Return True jika aktif."""
    global _enabled
    if _enabled:
        return True
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")):
        logger.warning("[db_log_sink] SUPABASE_URL/KEY tak ada — DB logging non-aktif")
        return False
    logger.add(
        _sink,
        level=level,
        enqueue=True,  # sink di thread background → tak memblok pipeline (render 35 mnt)
        filter=lambda r: r["extra"].get("tenant_id") is not None,
    )
    _enabled = True
    logger.debug("[db_log_sink] DB logging aktif (pipeline_run_logs)")
    return True
