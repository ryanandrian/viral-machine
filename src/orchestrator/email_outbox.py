"""Email Outbox dispatcher (Phase 10.1) — memproses antrean `email_outbox` yang di-isi admin
(E1 "Kirim email"). Loop: ambil pending → resolve email tenant (Auth admin API via
`email.tenant_email`) → `send_email` SMTP (fail-soft) → tandai sent/failed.

service_role (bypass RLS — tabel email_outbox tanpa policy). Fire-and-forget: error per-baris
tak menghentikan loop; SMTP gagal = baris 'failed' + error tercatat (bukan crash).
Dijalankan worker_decoupled sebagai thread (cadence config EMAIL_OUTBOX_INTERVAL_SEC, default 60s).
"""

import os
import time
from datetime import datetime, timezone

from loguru import logger


def process_outbox(sb, limit: int = 20) -> int:
    """Proses sampai `limit` email pending. Return jumlah terkirim."""
    res = (
        sb.table("email_outbox")
        .select("id, tenant_id, subject, body")
        .eq("status", "pending")
        .order("created_at")
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return 0

    from src.utils.email import tenant_email, send_email

    sent = 0
    for r in rows:
        now = datetime.now(timezone.utc).isoformat()
        to = tenant_email(r["tenant_id"], sb)
        if not to:
            sb.table("email_outbox").update(
                {"status": "failed", "error": "email tenant tak ditemukan", "sent_at": now}
            ).eq("id", r["id"]).execute()
            logger.warning(f"[EmailOutbox] {r['id']} gagal: email tenant {r['tenant_id']} tak ditemukan")
            continue
        ok = send_email(to, r["subject"], r["body"])
        sb.table("email_outbox").update(
            {"status": "sent" if ok else "failed",
             "error": None if ok else "SMTP gagal (lihat log worker)",
             "sent_at": now}
        ).eq("id", r["id"]).execute()
        if ok:
            sent += 1
            logger.info(f"[EmailOutbox] terkirim → {to} (tenant {r['tenant_id']})")
    return sent


def run_forever(interval_seconds=None) -> None:
    """Loop persisten — dipanggil worker_decoupled sebagai thread."""
    from supabase import create_client

    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("EMAIL_OUTBOX_INTERVAL_SEC", "60"))
    logger.info(f"[EmailOutbox] dispatcher start | tiap {interval}s (admin→tenant email queue)")
    while True:
        try:
            process_outbox(sb)
        except Exception as e:  # fire-and-forget: jangan pernah matikan loop
            logger.error(f"[EmailOutbox] error: {e}")
        time.sleep(interval)
