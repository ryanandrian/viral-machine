"""
Worker v2 DECOUPLED (Phase 5.3 cutover) — Producer + Publisher loop konkuren.

Menggantikan model lama produce+publish-satu-tarikan (`scripts/worker.py`). DESAIN §12c:
  • PRODUCER  : loop persisten, jaga stok buffer per-channel; rem semaphore = jumlah core
                (MAX_CONCURRENT_RENDER) → anti-OOM. Render → upload Biznet S3 → content_inventory.
  • PUBLISHER : loop 30s, publish video ready dari buffer saat slot (TIMEZONE TENANT).

Self-driven (producer baca `channels`, publisher baca slot) → TIDAK perlu pg_cron dispatcher
(itu yang treat publish_slots sbg UTC = Bug 1; di sini timezone-aware).

⚠️ Deploy v2 (saat cutover, bukan sekarang) — env WAJIB:
  SUPABASE_URL=<v2>  SUPABASE_KEY=<service_role>  ENCRYPTION_KEY=<...>  S3_*=<Biznet>
  @reboot cd ~/viral-machine && python3.11 scripts/worker_decoupled.py >> logs/worker.log 2>&1
"""

import os
import sys
import time
import signal
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger


def main() -> None:
    from src.utils.db_log_sink import setup_db_logging
    from src.orchestrator import producer, publisher, buffer_janitor, self_learning
    from src.billing import renewal as billing_renewal

    setup_db_logging()

    stop = threading.Event()

    def _shutdown(sig, _frame):
        logger.info(f"[WorkerV2] Signal {sig} — stop (loop daemon berhenti saat proses exit)")
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("[WorkerV2] ══════════════════════════════════════════")
    logger.info("[WorkerV2] DECOUPLED — Producer + Publisher + Janitor loop konkuren (§12c)")
    logger.info(f"[WorkerV2] MAX_CONCURRENT_RENDER={producer.max_concurrent_render()} (core)")
    logger.info("[WorkerV2] ══════════════════════════════════════════")

    threads = [
        threading.Thread(target=producer.run_forever, name="producer", daemon=True),
        threading.Thread(target=publisher.run_forever, name="publisher", daemon=True),
        threading.Thread(target=buffer_janitor.run_forever, name="janitor", daemon=True),
        threading.Thread(target=self_learning.run_forever, name="self_learning", daemon=True),
        threading.Thread(target=billing_renewal.run_forever, name="billing_renewal", daemon=True),
    ]
    for t in threads:
        t.start()

    while not stop.is_set():
        time.sleep(1)
    logger.info("[WorkerV2] shutdown selesai")


if __name__ == "__main__":
    main()
