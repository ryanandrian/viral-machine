"""
Niche Request Sweeper (CUSTOM_NICHE_REQUEST_FLOW.md §5) — auto-close masa evaluasi.

Untuk tiap pesanan custom niche berstatus 'delivered':
  • lewat N hari (app_config.niche_eval_window_days, admin-editable) tanpa respons → status 'closed' + email penutup.
  • H-1 (>= N-1 hari, belum diingatkan) → email pengingat + tandai reminder_sent_at (tak berulang).

Email = antre ke email_outbox (dispatcher SMTP yang kirim). service_role (bypass RLS). Fail-soft:
error per-baris/loop tak menghentikan worker. Dijalankan worker_decoupled sebagai thread (cadence
NICHE_SWEEP_INTERVAL_SEC, default 3600s).
"""

import os
import time
from datetime import datetime, timezone

from loguru import logger


def _eval_window_days(sb) -> int:
    """Lebar masa evaluasi (hari) — admin-editable via app_config; default 3 (no-hardcode)."""
    try:
        r = sb.table("app_config").select("value").eq("key", "niche_eval_window_days").limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception as e:
        logger.warning(f"[NicheSweep] baca niche_eval_window_days gagal: {e}")
    return 3


def _enqueue(sb, tenant_id: str, subject: str, body: str) -> None:
    try:
        sb.table("email_outbox").insert({"tenant_id": tenant_id, "subject": subject, "body": body}).execute()
    except Exception as e:
        logger.warning(f"[NicheSweep] enqueue email gagal (tenant {tenant_id}): {e}")


def sweep_once(sb) -> int:
    """Tutup pesanan 'delivered' yang lewat masa evaluasi + kirim pengingat H-1. Return jumlah ditutup."""
    days = _eval_window_days(sb)
    now = datetime.now(timezone.utc)
    res = (sb.table("niche_requests")
           .select("request_id,tenant_id,title,delivered_at,reminder_sent_at")
           .eq("status", "delivered").execute())
    rows = res.data or []
    closed = 0
    for r in rows:
        da = r.get("delivered_at")
        if not da:
            continue
        try:
            d0 = datetime.fromisoformat(str(da).replace("Z", "+00:00"))
        except Exception:
            continue
        elapsed_days = (now - d0).total_seconds() / 86400.0
        title = r.get("title", "")
        if elapsed_days >= days:
            sb.table("niche_requests").update(
                {"status": "closed", "closed_at": now.isoformat(), "updated_at": now.isoformat()}
            ).eq("request_id", r["request_id"]).execute()
            _enqueue(sb, r["tenant_id"], f"Pesanan niche selesai — {title}",
                     f"Halo,\n\nMasa evaluasi niche custom \"{title}\" telah berakhir tanpa permintaan perbaikan, "
                     f"jadi pesanan kami tandai SELESAI. Niche tetap aktif & bisa Anda pakai di channel.\n"
                     f"Terima kasih!\n\n— Tim MesinViral")
            closed += 1
        elif elapsed_days >= max(0, days - 1) and not r.get("reminder_sent_at"):
            sb.table("niche_requests").update({"reminder_sent_at": now.isoformat()}).eq("request_id", r["request_id"]).execute()
            _enqueue(sb, r["tenant_id"], f"Pengingat evaluasi niche — {title}",
                     f"Halo,\n\nMasa evaluasi niche custom \"{title}\" akan segera berakhir. Mohon segera cek di "
                     f"Pustaka Niche: tekan \"Terima & Selesaikan\" bila sudah puas, atau \"Minta perbaikan\" bila "
                     f"perlu disesuaikan. Lewat batas tanpa respons, pesanan otomatis dianggap selesai.\n\n— Tim MesinViral")
    return closed


def run_forever(interval_seconds=None) -> None:
    """Loop persisten — dipanggil worker_decoupled sebagai thread."""
    from supabase import create_client

    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("NICHE_SWEEP_INTERVAL_SEC", "3600"))
    logger.info(f"[NicheSweep] dispatcher start | tiap {interval}s (auto-close evaluasi + pengingat H-1)")
    while True:
        try:
            n = sweep_once(sb)
            if n:
                logger.info(f"[NicheSweep] {n} pesanan custom niche ditutup (masa evaluasi lewat)")
        except Exception as e:  # fire-and-forget: jangan pernah matikan loop
            logger.error(f"[NicheSweep] error: {e}")
        time.sleep(interval)
