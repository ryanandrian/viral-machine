"""Worker heartbeat (Phase 10.8) — upsert status tiap thread ke `worker_heartbeats` untuk E3 System Health.
Dipanggil periodik dari worker_decoupled main loop. service_role (tabel tanpa policy). Fail-soft."""

import socket
from datetime import datetime, timezone

from loguru import logger


def record(sb, threads) -> None:
    node = socket.gethostname()
    now = datetime.now(timezone.utc).isoformat()
    for t in threads:
        try:
            sb.table("worker_heartbeats").upsert(
                {"worker_name": t.name, "status": "up" if t.is_alive() else "down",
                 "node": node, "last_heartbeat_at": now},
                on_conflict="worker_name",
            ).execute()
        except Exception as e:  # fail-soft: heartbeat tak boleh ganggu worker
            logger.warning(f"[Heartbeat] {t.name}: {e}")
