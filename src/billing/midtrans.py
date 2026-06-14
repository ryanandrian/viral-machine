"""
Midtrans Snap (redirect) + webhook handler (Phase 8b, DESAIN §4/§8).

ENV-DRIVEN (sandbox↔production = tukar `MIDTRANS_ENV`, NOL bongkar kode):
  • Snap create  : backend → Snap token + redirect_url (halaman bayar di-host Midtrans).
  • Webhook      : status OTORITATIF (signature SHA512) → aktifkan/update langganan tenant.
    JANGAN pernah aktifkan dari browser-redirect (bisa hilang) — hanya dari webhook ter-verify.

Harga dari `pricing_config` (DB, no-hardcode). Audit di `payments`. Plan alias agency↔scale
(plan_limits pakai 'agency', pricing_config seed 'plan_scale') ditangani di plan_price_idr.
"""

import os
import time
import json
import base64
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from loguru import logger

_PERIOD_DAYS = 30  # 1 siklus langganan (bulanan)


def _is_production() -> bool:
    return os.getenv("MIDTRANS_ENV", "sandbox").lower() == "production"


def _snap_base() -> str:
    return ("https://app.midtrans.com/snap/v1" if _is_production()
            else "https://app.sandbox.midtrans.com/snap/v1")


def _server_key() -> str:
    key = os.getenv("MIDTRANS_SERVER_KEY", "")
    if not key:
        raise ValueError("MIDTRANS_SERVER_KEY tak diset di env (gitignored) — wajib utk Snap/webhook.")
    return key


def _now() -> datetime:
    return datetime.now(timezone.utc)


def plan_price_idr(sb, plan_type: str) -> int:
    """Harga paket (IDR) dari pricing_config (no-hardcode). agency↔scale alias. Tak ada → raise."""
    alias = {"agency": "scale", "scale": "agency"}.get(plan_type)
    for key in [f"plan_{plan_type}"] + ([f"plan_{alias}"] if alias else []):
        try:
            res = (sb.table("pricing_config").select("value_idr")
                   .eq("key", key).eq("active", True).limit(1).execute())
            if res.data:
                return int(res.data[0]["value_idr"])
        except Exception as e:
            logger.debug(f"[Midtrans] pricing lookup {key} gagal: {e}")
    raise ValueError(f"Harga paket '{plan_type}' tak ada di pricing_config — set dulu (no-hardcode).")


def _order_id(tenant_id: str, plan_type: str, ts: int) -> str:
    """Order id unik & dapat di-audit (≤50 char, alfanumerik+dash)."""
    return f"MV-{plan_type}-{str(tenant_id).replace('-', '')[:12]}-{ts}"


def snap_create_transaction(sb, tenant_id: str, plan_type: str,
                            customer_email: str | None = None,
                            finish_url: str | None = None) -> dict:
    """
    Buat transaksi Snap → simpan order `payments` (pending) → return {order_id, token, redirect_url, amount}.
    Frontend redirect user ke redirect_url (halaman bayar Midtrans). Status final via webhook.
    """
    amount   = plan_price_idr(sb, plan_type)
    ts       = int(time.time())
    order_id = _order_id(tenant_id, plan_type, ts)

    sb.table("payments").insert({
        "order_id": order_id, "tenant_id": tenant_id, "plan_type": plan_type,
        "gross_amount": amount, "status": "pending",
    }).execute()

    body = {
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "item_details": [{"id": plan_type, "price": amount, "quantity": 1,
                          "name": f"MesinViral {plan_type} (bulanan)"}],
        "callbacks": {"finish": finish_url or os.getenv("MIDTRANS_FINISH_URL",
                                                        "https://mesinviral.com/billing/finish")},
    }
    if customer_email:
        body["customer_details"] = {"email": customer_email}

    auth = base64.b64encode((_server_key() + ":").encode()).decode()
    req = urllib.request.Request(
        _snap_base() + "/transactions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json",
                 "Accept": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        d = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        logger.error(f"[Midtrans] Snap create gagal order={order_id}: HTTP {e.code} {detail}")
        sb.table("payments").update({"status": "create_failed"}).eq("order_id", order_id).execute()
        raise

    sb.table("payments").update({"snap_token": d.get("token")}).eq("order_id", order_id).execute()
    logger.info(f"[Midtrans] Snap created order={order_id} amount={amount} ({'prod' if _is_production() else 'sandbox'})")
    return {"order_id": order_id, "token": d.get("token"),
            "redirect_url": d.get("redirect_url"), "amount": amount}


def verify_signature(order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
    """signature_key = SHA512(order_id + status_code + gross_amount + ServerKey). gross_amount = string apa adanya dari payload."""
    raw = f"{order_id}{status_code}{gross_amount}{_server_key()}"
    return hashlib.sha512(raw.encode()).hexdigest() == (signature_key or "")


def handle_notification(sb, payload: dict) -> dict:
    """
    Proses webhook Midtrans (OTORITATIF). Verifikasi signature → update `payments` →
    aktifkan langganan tenant bila settlement/capture (fraud accept). Idempotent (status re-set).
    """
    order_id    = payload.get("order_id")
    status_code = str(payload.get("status_code", ""))
    gross       = str(payload.get("gross_amount", ""))
    sig         = payload.get("signature_key", "")

    if not verify_signature(order_id, status_code, gross, sig):
        logger.warning(f"[Midtrans] signature INVALID order={order_id} — TOLAK (anti-spoof)")
        return {"ok": False, "reason": "invalid_signature"}

    txn   = payload.get("transaction_status")
    fraud = payload.get("fraud_status")

    res   = sb.table("payments").select("*").eq("order_id", order_id).limit(1).execute()
    order = (res.data or [None])[0]
    if not order:
        logger.warning(f"[Midtrans] order tak ditemukan: {order_id}")
        return {"ok": False, "reason": "order_not_found"}

    upd = {"status": txn, "payment_type": payload.get("payment_type"),
           "fraud_status": fraud, "raw_notification": payload,
           "updated_at": _now().isoformat()}
    activated = False

    if txn in ("settlement", "capture") and (fraud in (None, "", "accept")):
        start = _now()
        end   = start + timedelta(days=_PERIOD_DAYS)
        upd["period_start"] = start.isoformat()
        upd["period_end"]   = end.isoformat()
        # AKTIVASI: status otoritatif → tenant aktif + paket + akhir periode
        sb.table("tenant_configs").update({
            "subscription_status": "active",
            "plan_type":           order["plan_type"],
            "current_period_end":  end.isoformat(),
        }).eq("tenant_id", order["tenant_id"]).execute()
        activated = True
    # expire/deny/cancel checkout BARU → biarkan langganan eksisting; suspend = saat renewal gagal
    # (cek current_period_end periodik — follow-up 8 polish, bukan dari 1 notif checkout gagal).

    sb.table("payments").update(upd).eq("order_id", order_id).execute()

    # Receipt email (8c) — HANYA saat transisi BARU ke aktif (idempotent thd retry webhook). Fail-soft.
    if activated and order.get("status") not in ("settlement", "capture"):
        try:
            from src.utils.email import notify_payment_receipt
            notify_payment_receipt(order["tenant_id"], order.get("plan_type"), order.get("gross_amount") or 0, sb)
        except Exception as _ee:
            logger.debug(f"[Midtrans] receipt email skip (non-fatal): {_ee}")

    logger.info(f"[Midtrans] notif order={order_id} txn={txn} fraud={fraud} activated={activated}")
    return {"ok": True, "order_id": order_id, "transaction_status": txn,
            "tenant_id": order["tenant_id"], "activated": activated}
