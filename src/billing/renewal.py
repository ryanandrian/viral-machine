"""
Siklus langganan (Phase 8, DESAIN §4) — SEMUA timing config-driven (app_config, admin-editable, no-hardcode).

State: trial → trial_expired (trial lapse) · active → grace (retry) → suspended (stop). Reaktivasi = webhook/
reconciler pembayaran (set active + period_end baru + reset penanda reminder).

Notifikasi lengkap tiap fase (skenario billing tuntas):
  • H-`trial_reminder_days_before`   : trial mau habis → ajak upgrade + minta masukan
  • trial habis → trial_expired      : lapse (lead marketing)
  • H-`renewal_reminder_days_before` : langganan berbayar mau habis → ajak perpanjang
  • periode habis → grace            : dunning (mesin masih jalan `billing_grace_days` hari lagi)
  • grace lewat → suspended          : produksi dihentikan → ajak aktifkan lagi

⛔ Comp/developer (is_developer / discount≥100) EXEMPT — gratis selamanya. Idempotent (penanda *_sent_at).
Dijalankan worker_decoupled sebagai thread (cadence BILLING_CHECK_INTERVAL_SEC, default 86400).
"""

import os
import math
import time
from datetime import datetime, timezone, timedelta

from loguru import logger

from src.billing.limits import is_comp_account


def _cfg(sb, key: str, default: int) -> int:
    """Angka dari app_config (admin-editable via System Configuration, no-hardcode). Gagal → default."""
    try:
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception as e:
        logger.debug(f"[Billing] cfg {key} gagal: {e}")
    return default


def _parse_end(pe):
    if not pe:
        return None
    try:
        end = datetime.fromisoformat(str(pe).replace("Z", "+00:00"))
        return end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
    except Exception:
        return None


def next_status(row: dict, now: datetime, grace_days: int) -> str | None:
    """Status seharusnya berdasar current_period_end. None = JANGAN ubah.
    Comp/final(suspended/cancelled/trial_expired)/period-null → None. Lainnya: active/grace/suspended."""
    if is_comp_account(row):
        return None
    status = row.get("subscription_status") or "active"
    if status in ("suspended", "cancelled", "trial_expired"):
        return None
    end = _parse_end(row.get("current_period_end"))
    if not end:
        return None
    if status == "trial":
        return None if now <= end else "trial_expired"
    if now <= end:
        return "active"
    if now <= end + timedelta(days=grace_days):
        return "grace"
    return "suspended"


def sweep_subscriptions(sb) -> dict:
    """Scan tenant_configs → kirim reminder (pra-habis) + terapkan transisi status (+ notif). Comp exempt."""
    grace_days = _cfg(sb, "billing_grace_days", 7)
    trial_rem  = _cfg(sb, "trial_reminder_days_before", 1)
    renew_rem  = _cfg(sb, "renewal_reminder_days_before", 3)
    rows = (sb.table("tenant_configs")
            .select("tenant_id,subscription_status,current_period_end,is_developer,discount_pct,"
                    "trial_reminder_sent_at,renewal_reminder_sent_at,suspend_notified_at")
            .execute().data) or []
    now = datetime.now(timezone.utc)
    changed = exempt = reminded = 0

    from src.utils import email as mail

    for r in rows:
        if is_comp_account(r):
            exempt += 1
            continue
        tid = r["tenant_id"]
        cur = r.get("subscription_status") or "active"
        end = _parse_end(r.get("current_period_end"))

        # ── 1) REMINDER pra-habis (sekali per siklus via penanda *_sent_at) ──
        if end and now < end:
            secs = (end - now).total_seconds()
            days_left = max(1, math.ceil(secs / 86400))
            try:
                if cur == "trial" and trial_rem > 0 and secs <= trial_rem * 86400 and not r.get("trial_reminder_sent_at"):
                    mail.notify_trial_ending(tid, days_left, sb)
                    sb.table("tenant_configs").update({"trial_reminder_sent_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    reminded += 1
                elif cur == "active" and renew_rem > 0 and secs <= renew_rem * 86400 and not r.get("renewal_reminder_sent_at"):
                    mail.notify_renewal_reminder(tid, days_left, sb)
                    sb.table("tenant_configs").update({"renewal_reminder_sent_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    reminded += 1
            except Exception as _e:
                logger.debug(f"[Billing] reminder skip {tid}: {_e}")

        # ── 2) TRANSISI status (habis / grace / suspend) ──
        tgt = next_status(r, now, grace_days)
        if tgt and tgt != cur:
            sb.table("tenant_configs").update({"subscription_status": tgt}).eq("tenant_id", tid).execute()
            logger.info(f"[Billing] {tid}: {cur} → {tgt}")
            changed += 1
            try:
                if tgt == "trial_expired":
                    mail.notify_trial_lapse(tid, sb)
                elif tgt == "grace":
                    mail.notify_suspend_warning(tid, grace_days, sb)
                elif tgt == "suspended" and not r.get("suspend_notified_at"):
                    mail.notify_suspended(tid, sb)
                    sb.table("tenant_configs").update({"suspend_notified_at": now.isoformat()}).eq("tenant_id", tid).execute()
            except Exception as _ee:
                logger.debug(f"[Billing] notif skip {tid}: {_ee}")

    logger.info(f"[Billing] sweep: {len(rows)} tenant | changed={changed} | reminded={reminded} | comp-exempt={exempt}")
    return {"checked": len(rows), "changed": changed, "reminded": reminded, "exempt": exempt}


def run_forever(interval_seconds=None) -> None:
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("BILLING_CHECK_INTERVAL_SEC", "86400"))
    logger.info(f"[Billing] renewal sweep start | tiap {interval}s (reminder+transisi, config-driven, comp exempt)")
    while True:
        try:
            sweep_subscriptions(sb)
        except Exception as e:
            logger.error(f"[Billing] sweep error: {e}")
        time.sleep(interval)
