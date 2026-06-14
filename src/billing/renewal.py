"""
Subscription renewal/expiry sweep (Phase 8, DESAIN §4 billing lifecycle).

Lengkapi siklus monetisasi berbasis `tenant_configs.current_period_end`:
  active → (period_end lewat) → **grace** (window retry bayar) → **suspended**.
Reaktivasi = lewat webhook Midtrans (handle_notification set active + period_end baru).

⛔ **Comp/developer account EXEMPT** (is_developer / discount≥100) — GRATIS SELAMANYA,
tak pernah disentuh ([[project: ryan always-free]]). Status final (suspended/cancelled) & period_end
null juga di-skip. Idempotent. Config: BILLING_GRACE_DAYS (7), BILLING_CHECK_INTERVAL_SEC (86400).
Dijalankan sebagai thread di worker_decoupled (cadence harian).
"""

import os
import time
from datetime import datetime, timezone, timedelta

from loguru import logger

from src.billing.limits import is_comp_account


def _grace_days() -> int:
    v = os.getenv("BILLING_GRACE_DAYS")
    return int(v) if v and v.isdigit() else 7


def next_status(row: dict, now: datetime) -> str | None:
    """
    Status seharusnya berdasar current_period_end. None = JANGAN ubah.
    Comp → None (exempt). suspended/cancelled → None (final; reaktivasi via webhook bayar).
    period_end null → None (belum ada siklus, mis. trial tanpa end). Lainnya: active/grace/suspended.
    """
    if is_comp_account(row):
        return None
    status = row.get("subscription_status") or "active"
    if status in ("suspended", "cancelled", "trial_expired"):
        return None   # status final (reaktivasi hanya via webhook bayar)
    pe = row.get("current_period_end")
    if not pe:
        return None
    try:
        end = datetime.fromisoformat(str(pe).replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    if status == "trial":
        # Trial habis (durasi lewat) → 'trial_expired' (non-producing + LEAD marketing utk follow-up/feedback).
        # Beda dari 'suspended' (paid lapse). TANPA grace (tak ada pembayaran utk di-retry).
        return None if now <= end else "trial_expired"
    if now <= end:
        return "active"   # periode masih berjalan (sudah renew)
    if now <= end + timedelta(days=_grace_days()):
        return "grace"    # lewat jatuh tempo, masih window retry
    return "suspended"    # lewat grace → stop


def sweep_subscriptions(sb) -> dict:
    """Scan tenant_configs → update status sesuai next_status. Comp exempt. Return ringkasan."""
    rows = (sb.table("tenant_configs")
            .select("tenant_id,subscription_status,current_period_end,is_developer,discount_pct")
            .execute().data) or []
    now = datetime.now(timezone.utc)
    changed = exempt = 0
    for r in rows:
        if is_comp_account(r):
            exempt += 1
            continue
        cur = r.get("subscription_status") or "active"
        tgt = next_status(r, now)
        if tgt and tgt != cur:
            sb.table("tenant_configs").update({"subscription_status": tgt}).eq("tenant_id", r["tenant_id"]).execute()
            logger.info(f"[Billing] {r['tenant_id']}: {cur} → {tgt} (period_end lewat)")
            changed += 1
            # Notif email (8c) — HANYA saat transisi (sekali, bukan tiap sweep). Fail-soft.
            try:
                if tgt == "trial_expired":
                    from src.utils.email import notify_trial_lapse
                    notify_trial_lapse(r["tenant_id"], sb)
                elif tgt == "grace":
                    from src.utils.email import notify_suspend_warning
                    notify_suspend_warning(r["tenant_id"], _grace_days(), sb)
            except Exception as _ee:
                logger.debug(f"[Billing] notif email skip (non-fatal): {_ee}")
    logger.info(f"[Billing] renewal sweep: {len(rows)} tenant | changed={changed} | comp-exempt={exempt}")
    return {"checked": len(rows), "changed": changed, "exempt": exempt}


def run_forever(interval_seconds=None) -> None:
    """Loop persisten — dipanggil worker_decoupled sebagai thread (cadence harian)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("BILLING_CHECK_INTERVAL_SEC", "86400"))
    logger.info(f"[Billing] renewal sweep start | tiap {interval}s (active→grace→suspend, comp exempt)")
    while True:
        try:
            sweep_subscriptions(sb)
        except Exception as e:
            logger.error(f"[Billing] sweep error: {e}")
        time.sleep(interval)
