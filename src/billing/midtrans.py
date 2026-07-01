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
    # Switch sandbox↔production = ubah MIDTRANS_ENV SAJA. Kedua set kunci tinggal permanen di .env;
    # kode ambil yang cocok otomatis (nol tukar kunci, nol risiko env≠key, nol perubahan kode).
    env = "PRODUCTION" if _is_production() else "SANDBOX"
    key = os.getenv(f"MIDTRANS_{env}_SERVER_KEY", "")
    if not key:
        raise ValueError(f"MIDTRANS_{env}_SERVER_KEY tak diset di env (gitignored) — wajib utk Snap/webhook.")
    return key


def _now() -> datetime:
    return datetime.now(timezone.utc)


def price_by_key(sb, key: str) -> int:
    """Harga (IDR) dari pricing_config by key EKSAK (no-hardcode). Tak ada/aktif → raise."""
    try:
        res = (sb.table("pricing_config").select("value_idr")
               .eq("key", key).eq("active", True).limit(1).execute())
        if res.data:
            return int(res.data[0]["value_idr"])
    except Exception as e:
        logger.debug(f"[Midtrans] pricing lookup {key} gagal: {e}")
    raise ValueError(f"Harga '{key}' tak ada/aktif di pricing_config — set dulu (no-hardcode).")


def plan_price_idr(sb, plan_type: str) -> int:
    """Harga paket langganan (IDR) dari pricing_config key `plan_{tier}`."""
    return price_by_key(sb, f"plan_{plan_type}")


def _order_id(tenant_id: str, plan_type: str, ts: int) -> str:
    """Order id unik & dapat di-audit (≤50 char, alfanumerik+dash)."""
    return f"MV-{plan_type}-{str(tenant_id).replace('-', '')[:12]}-{ts}"


def _snap_post(order_id: str, amount: int, item_id: str, item_name: str,
               customer_email: str | None, finish_url: str | None) -> dict:
    """POST ke Snap API → {token, redirect_url}.
    Notification PER-TRANSAKSI via X-Override-Notification: akun Midtrans DIBAGI dgn app lain
    (mis. aiwa, awalan order 'AIWA') di domain berbeda → JANGAN andalkan Notification URL GLOBAL
    dashboard (milik app lain). Order ID ber-awalan 'MV-' menjaga keunikan lintas-app. no-hardcode: env."""
    body = {
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "item_details": [{"id": item_id, "price": amount, "quantity": 1, "name": item_name[:50]}],
        "callbacks": {"finish": finish_url or os.getenv("MIDTRANS_FINISH_URL",
                                                        "https://mesinviral.com/billing")},
    }
    if customer_email:
        body["customer_details"] = {"email": customer_email}
    notif_url = os.getenv("MIDTRANS_NOTIFICATION_URL") or (
        os.getenv("APP_BASE_URL", "https://mesinviral.com").rstrip("/") + "/api/webhooks/midtrans")
    auth = base64.b64encode((_server_key() + ":").encode()).decode()
    req = urllib.request.Request(
        _snap_base() + "/transactions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json",
                 "Accept": "application/json", "X-Override-Notification": notif_url},
        method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())


def snap_create_transaction(sb, tenant_id: str, plan_type: str,
                            customer_email: str | None = None,
                            finish_url: str | None = None) -> dict:
    """LANGGANAN bulanan. Buat order `payments` pending → Snap → {order_id, token, redirect_url, amount}.
    Frontend redirect user ke redirect_url. Status final via webhook."""
    amount   = plan_price_idr(sb, plan_type)
    ts       = int(time.time())
    order_id = _order_id(tenant_id, plan_type, ts)
    sb.table("payments").insert({
        "order_id": order_id, "tenant_id": tenant_id, "plan_type": plan_type,
        "gross_amount": amount, "status": "pending", "category": "subscription",
    }).execute()
    try:
        d = _snap_post(order_id, amount, plan_type, f"MesinViral {plan_type} (bulanan)", customer_email, finish_url)
    except urllib.error.HTTPError as e:
        logger.error(f"[Midtrans] Snap subscription gagal order={order_id}: HTTP {e.code} {e.read().decode()[:300]}")
        sb.table("payments").update({"status": "create_failed"}).eq("order_id", order_id).execute()
        raise
    sb.table("payments").update({"snap_token": d.get("token")}).eq("order_id", order_id).execute()
    logger.info(f"[Midtrans] Snap subscription order={order_id} amount={amount} ({'prod' if _is_production() else 'sandbox'})")
    return {"order_id": order_id, "token": d.get("token"),
            "redirect_url": d.get("redirect_url"), "amount": amount}


def snap_create_niche_addon(sb, tenant_id: str, request_id: str,
                            customer_email: str | None = None,
                            finish_url: str | None = None) -> dict:
    """ADD-ON custom-niche (E1). Validasi kepemilikan + status awaiting_payment → order pending
    (category=addon, ref_id=request_id) → tautkan niche_requests.order_id → Snap. Settlement via webhook
    → RPC settle_niche_request_paid (majukan ke in_progress otomatis)."""
    res = (sb.table("niche_requests")
           .select("request_id,tenant_id,title,price_key,status")
           .eq("request_id", request_id).limit(1).execute())
    r = (res.data or [None])[0]
    if not r:
        raise ValueError("pesanan niche tak ditemukan")
    if str(r["tenant_id"]) != str(tenant_id):
        raise ValueError("bukan pemilik pesanan")
    if r["status"] != "awaiting_payment":
        raise ValueError(f"status '{r['status']}' bukan awaiting_payment")
    if not r.get("price_key"):
        raise ValueError("price_key pesanan kosong")
    amount   = price_by_key(sb, r["price_key"])
    ts       = int(time.time())
    order_id = f"MV-niche-{str(request_id).replace('-', '')[:12]}-{ts}"
    sb.table("payments").insert({
        "order_id": order_id, "tenant_id": tenant_id, "plan_type": None,
        "gross_amount": amount, "status": "pending", "category": "addon", "ref_id": str(request_id),
    }).execute()
    sb.table("niche_requests").update({"order_id": order_id}).eq("request_id", request_id).execute()
    try:
        d = _snap_post(order_id, amount, r["price_key"], f"Niche custom: {r['title']}", customer_email, finish_url)
    except urllib.error.HTTPError as e:
        logger.error(f"[Midtrans] Snap addon gagal order={order_id}: HTTP {e.code} {e.read().decode()[:300]}")
        sb.table("payments").update({"status": "create_failed"}).eq("order_id", order_id).execute()
        raise
    sb.table("payments").update({"snap_token": d.get("token")}).eq("order_id", order_id).execute()
    logger.info(f"[Midtrans] Snap addon(niche) order={order_id} req={request_id} amount={amount}")
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
        if order.get("category") == "addon":
            # ADD-ON (custom-niche): majukan pesanan awaiting_payment → in_progress via RPC tunggal
            # (buat niche + email). Idempotent (aman retry webhook). Tenant subscription TAK disentuh.
            try:
                sb.rpc("settle_niche_request_paid",
                       {"p_request_id": order.get("ref_id"), "p_order_id": order_id}).execute()
                activated = True
            except Exception as _re:
                logger.error(f"[Midtrans] settle addon gagal order={order_id} ref={order.get('ref_id')}: {_re}")
                # jangan raise: tetap catat status pembayaran & balas 200 (Midtrans tak retry-storm)
        else:
            # LANGGANAN: status otoritatif → tenant aktif + paket + akhir periode.
            start = _now()
            end   = start + timedelta(days=_PERIOD_DAYS)
            upd["period_start"] = start.isoformat()
            upd["period_end"]   = end.isoformat()
            sb.table("tenant_configs").update({
                "subscription_status": "active",
                "plan_type":           order["plan_type"],
                "current_period_end":  end.isoformat(),
            }).eq("tenant_id", order["tenant_id"]).execute()
            activated = True
    # expire/deny/cancel checkout BARU → biarkan langganan eksisting; suspend = saat renewal gagal
    # (cek current_period_end periodik — follow-up 8 polish, bukan dari 1 notif checkout gagal).

    sb.table("payments").update(upd).eq("order_id", order_id).execute()

    # Receipt email (8c) — HANYA langganan, saat transisi BARU ke aktif (idempotent thd retry webhook).
    # (Add-on: email "pembayaran diterima" sudah dikirim oleh RPC settle_niche_request_paid.) Fail-soft.
    if activated and order.get("category") != "addon" and order.get("status") not in ("settlement", "capture"):
        try:
            from src.utils.email import notify_payment_receipt
            notify_payment_receipt(order["tenant_id"], order.get("plan_type"), order.get("gross_amount") or 0, sb)
        except Exception as _ee:
            logger.debug(f"[Midtrans] receipt email skip (non-fatal): {_ee}")

    logger.info(f"[Midtrans] notif order={order_id} txn={txn} fraud={fraud} activated={activated}")
    return {"ok": True, "order_id": order_id, "transaction_status": txn,
            "tenant_id": order["tenant_id"], "activated": activated}
