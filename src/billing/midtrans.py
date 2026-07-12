"""
Midtrans Snap (redirect) + webhook handler (Phase 8b, DESAIN §4/§8).

ENV-DRIVEN (sandbox↔production = tukar `MIDTRANS_ENV`, NOL bongkar kode):
  • Snap create  : backend → Snap token + redirect_url (halaman bayar di-host Midtrans).
  • Webhook      : status OTORITATIF (signature SHA512) → aktifkan/update langganan tenant.
    JANGAN pernah aktifkan dari browser-redirect (bisa hilang) — hanya dari webhook ter-verify.

Harga dari `pricing_config` (DB, no-hardcode). Audit di `payments`.
Tahap 1 finalisasi_tier_plan (2026-07-13): harga checkout = compute_checkout_amount (diskon
terbesar-menang, comp ditolak) · periode = compute_new_period (rumus nilai-adil — sisa hari
dikonversi antar-paket sesuai rasio harga) · _apply_settlement idempotent via klaim optimistik.
(Catatan: alias tier lama agency/scale sudah direkonsiliasi migr 0025 — tidak ada penanganan alias.)
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


def _app_cfg_int(sb, key: str, default: int) -> int:
    """Angka dari app_config (admin-editable via System Configuration, no-hardcode). Gagal → default."""
    try:
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception:
        pass
    return default


def compute_new_period(sb, tenant_id: str, new_plan_type: str, now: datetime) -> tuple:
    """
    Periode langganan baru — RUMUS NILAI-ADIL (finalisasi_tier_plan Pilar 2, ratifikasi owner
    2026-07-13): sisa hari periode berjalan DIKONVERSI ke paket baru sesuai rasio harga/hari:
        period_end = now + durasi_paket + sisa_hari × (harga_paket_lama ÷ harga_paket_baru)
    • Perpanjang paket sama (rasio 1) → sisa hari tersambung UTUH (bayar dini tak pernah rugi).
    • Upgrade → sisa nilai terbawa proporsional (prorate jujur, tanpa mesin refund).
    • Downgrade → nilai sisa jadi masa lebih panjang di paket murah (kapasitas dijepit gerbang kuota).
    • Tanpa periode hidup (trial/expired/suspended/blocked/grace-lewat) ATAU paket lama tak berharga
      (mis. 'trial' — tak ada di pricing_config) → murni now + durasi (tanpa kredit).
    Harga acuan = pricing_config SAAT INI (config-driven). Return (start, end, catatan_log).
    """
    period_days = _app_cfg_int(sb, "subscription_period_days", 30)
    credit_days = 0.0
    note = "tanpa kredit"
    try:
        r = (sb.table("tenant_configs")
             .select("subscription_status,plan_type,current_period_end")
             .eq("tenant_id", tenant_id).limit(1).execute())
        row = (r.data or [{}])[0]
        status   = row.get("subscription_status") or "active"
        old_plan = row.get("plan_type")
        old_end  = row.get("current_period_end")
        if status in ("active", "grace") and old_plan and old_end:
            end_dt = datetime.fromisoformat(str(old_end).replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            remaining = (end_dt - now).total_seconds() / 86400.0
            if remaining > 0:
                old_price = plan_price_idr(sb, old_plan)      # 'trial' → raise → except → kredit 0
                new_price = plan_price_idr(sb, new_plan_type)
                credit_days = remaining * (old_price / float(new_price))
                note = f"kredit {credit_days:.2f}h (sisa {remaining:.2f}h × {old_price}/{new_price})"
    except Exception as e:
        logger.info(f"[Midtrans] periode tanpa kredit tenant={tenant_id}: {e}")
        credit_days = 0.0
    start = now
    end = now + timedelta(days=period_days + credit_days)
    return start, end, note


def compute_checkout_amount(sb, tenant_id: str, plan_type: str) -> tuple:
    """
    Harga checkout RESMI (finalisasi_tier_plan Pilar 3, ratifikasi owner 2026-07-13):
    dasar = pricing_config[plan] → diskon TERBESAR dari {discount_pct admin 1–99 (BERTAHAN tiap
    tagihan sampai di-nol-kan), winback aktif (hangus otomatis)} — tak digabung; min Rp 1.000.
    Akun comp (is_developer / discount_pct≥100) = gratis selamanya → checkout DITOLAK
    (kode 'comp_account_no_billing' — FE memang tak menampilkan tombol bayar utk comp).
    Return (amount, diskon_pct_terpakai).
    """
    base = plan_price_idr(sb, plan_type)
    trow = {}
    try:
        r = (sb.table("tenant_configs").select("is_developer,discount_pct")
             .eq("tenant_id", tenant_id).limit(1).execute())
        trow = (r.data or [{}])[0]
    except Exception as e:
        logger.debug(f"[Midtrans] baca tenant utk harga gagal (diskon diabaikan): {e}")
    from src.billing.limits import is_comp_account
    if is_comp_account(trow):
        raise ValueError("comp_account_no_billing")
    admin_disc = 0
    try:
        d = int(trow.get("discount_pct") or 0)
        if 0 < d < 100:
            admin_disc = d
    except Exception:
        pass
    wb = _winback_discount(sb, tenant_id)
    disc = max(admin_disc, wb)
    if disc <= 0:
        return base, 0
    amount = max(1000, round(base * (100 - disc) / 100))
    logger.info(f"[Midtrans] diskon {disc}% ({'admin' if admin_disc >= wb else 'winback'}) "
                f"tenant={tenant_id}: {base} → {amount}")
    return amount, disc


def _winback_discount(sb, tenant_id: str) -> int:
    """% diskon comeback AKTIF (belum kedaluwarsa) utk tenant, dari tenant_configs (LIFECYCLE B9). 0 = tak ada.
    no-hardcode: nilai di-set worker nurture (winback_offer_pct/_expires_at). Dikonsumsi saat aktivasi (di-reset)."""
    try:
        r = (sb.table("tenant_configs").select("winback_offer_pct,winback_offer_expires_at")
             .eq("tenant_id", tenant_id).limit(1).execute())
        if r.data:
            pct = int(r.data[0].get("winback_offer_pct") or 0)
            exp = r.data[0].get("winback_offer_expires_at")
            if pct > 0 and exp:
                e = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if e.tzinfo is None:
                    e = e.replace(tzinfo=timezone.utc)
                if _now() <= e:
                    return max(0, min(100, pct))
    except Exception:
        pass
    return 0


def _order_id(tenant_id: str, plan_type: str, ts: int) -> str:
    """Order id unik & dapat di-audit (≤50 char, alfanumerik+dash)."""
    return f"MV-{plan_type}-{str(tenant_id).replace('-', '')[:12]}-{ts}"


def _tenant_name(sb, tenant_id: str) -> str | None:
    """Nama tenant (display_handle) untuk customer_details Midtrans — rekonsiliasi jelas di dashboard."""
    try:
        r = sb.table("tenant_configs").select("display_handle").eq("tenant_id", tenant_id).limit(1).execute()
        if r.data and r.data[0].get("display_handle"):
            return str(r.data[0]["display_handle"])
    except Exception:
        pass
    return None


def _snap_post(order_id: str, amount: int, item_id: str, item_name: str,
               customer_email: str | None, finish_url: str | None, expiry_hours: int = 24,
               customer_name: str | None = None) -> dict:
    """POST ke Snap API → {token, redirect_url}.
    Notification PER-TRANSAKSI via X-Override-Notification: akun Midtrans DIBAGI dgn app lain
    (mis. aiwa, awalan order 'AIWA') di domain berbeda → JANGAN andalkan Notification URL GLOBAL
    dashboard (milik app lain). Order ID ber-awalan 'MV-' menjaga keunikan lintas-app. no-hardcode: env."""
    body = {
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "item_details": [{"id": item_id, "price": amount, "quantity": 1, "name": item_name[:50]}],
        "callbacks": {"finish": finish_url or os.getenv("MIDTRANS_FINISH_URL",
                                                        "https://mesinviral.com/billing")},
        "expiry": {"unit": "hours", "duration": expiry_hours},  # masa berlaku link bayar (config-driven)
    }
    cust: dict = {}
    if customer_name:
        cust["first_name"] = customer_name[:20]  # Midtrans first_name maks 20 char
    if customer_email:
        cust["email"] = customer_email
    if cust:
        body["customer_details"] = cust
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


def _cancel_pending_orders(sb, tenant_id: str, category: str) -> None:
    """ANTI DOBEL-BAYAR (owner 2026-07-04): sebelum buat order baru, BATALKAN order pending lama
    tenant utk kategori sama — 1 tenant = maks 1 tagihan hidup. VA/link lama di SMS/email Midtrans
    mati (tak bisa dibayar); tenant bebas pilih ulang metode. 404 dari Midtrans = order belum pernah
    di-charge (token saja) → cukup tandai canceled di ledger. Fail-soft per-order."""
    rows = (sb.table("payments").select("order_id").eq("tenant_id", tenant_id)
            .eq("category", category).eq("status", "pending").execute().data) or []
    for r in rows:
        oid = r["order_id"]
        try:
            auth = base64.b64encode((_server_key() + ":").encode()).decode()
            req = urllib.request.Request(f"{_status_base()}/{oid}/cancel",
                                         headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
                                         method="POST")
            urllib.request.urlopen(req, timeout=15)
        except Exception as e:
            logger.info(f"[Midtrans] cancel order lama {oid}: {e} (404=belum di-charge, aman)")
        sb.table("payments").update({"status": "canceled", "updated_at": _now().isoformat()}).eq("order_id", oid).execute()
        logger.info(f"[Midtrans] order pending lama DIBATALKAN: {oid} (anti dobel-bayar)")


def snap_create_transaction(sb, tenant_id: str, plan_type: str,
                            customer_email: str | None = None,
                            finish_url: str | None = None) -> dict:
    """LANGGANAN bulanan. Buat order `payments` pending → Snap → {order_id, token, redirect_url, amount}.
    Frontend redirect user ke redirect_url. Status final via webhook."""
    _cancel_pending_orders(sb, tenant_id, "subscription")   # anti dobel-bayar (owner 2026-07-04)
    amount, _disc = compute_checkout_amount(sb, tenant_id, plan_type)   # diskon terbesar-menang + tolak comp
    ts       = int(time.time())
    order_id = _order_id(tenant_id, plan_type, ts)
    sb.table("payments").insert({
        "order_id": order_id, "tenant_id": tenant_id, "plan_type": plan_type,
        "gross_amount": amount, "status": "pending", "category": "subscription",
    }).execute()
    try:
        d = _snap_post(order_id, amount, plan_type, f"MesinViral {plan_type} (bulanan)", customer_email, finish_url,
                       _app_cfg_int(sb, "checkout_expiry_hours", 24), customer_name=_tenant_name(sb, tenant_id))
    except urllib.error.HTTPError as e:
        logger.error(f"[Midtrans] Snap subscription gagal order={order_id}: HTTP {e.code} {e.read().decode()[:300]}")
        sb.table("payments").update({"status": "create_failed"}).eq("order_id", order_id).execute()
        raise
    sb.table("payments").update({"snap_token": d.get("token"), "redirect_url": d.get("redirect_url")}).eq("order_id", order_id).execute()
    logger.info(f"[Midtrans] Snap subscription order={order_id} amount={amount} ({'prod' if _is_production() else 'sandbox'})")
    # Email ber-brand "Selesaikan pembayaran" (fail-soft) — email Midtrans TAK memuat link Snap (owner 2026-07-04).
    try:
        from src.utils.email import notify_payment_link
        notify_payment_link(tenant_id, order_id, amount, d.get("redirect_url"),
                            _app_cfg_int(sb, "checkout_expiry_hours", 24), sb)
    except Exception as _pe:
        logger.debug(f"[Midtrans] email link bayar skip (non-fatal): {_pe}")
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
    _cancel_pending_orders(sb, tenant_id, "addon")   # anti dobel-bayar (owner 2026-07-04)
    amount   = price_by_key(sb, r["price_key"])
    ts       = int(time.time())
    order_id = f"MV-niche-{str(request_id).replace('-', '')[:12]}-{ts}"
    sb.table("payments").insert({
        "order_id": order_id, "tenant_id": tenant_id, "plan_type": None,
        "gross_amount": amount, "status": "pending", "category": "addon", "ref_id": str(request_id),
    }).execute()
    sb.table("niche_requests").update({"order_id": order_id}).eq("request_id", request_id).execute()
    try:
        d = _snap_post(order_id, amount, r["price_key"], f"Niche custom: {r['title']}", customer_email, finish_url,
                       _app_cfg_int(sb, "checkout_expiry_hours", 24), customer_name=_tenant_name(sb, tenant_id))
    except urllib.error.HTTPError as e:
        logger.error(f"[Midtrans] Snap addon gagal order={order_id}: HTTP {e.code} {e.read().decode()[:300]}")
        sb.table("payments").update({"status": "create_failed"}).eq("order_id", order_id).execute()
        raise
    sb.table("payments").update({"snap_token": d.get("token"), "redirect_url": d.get("redirect_url")}).eq("order_id", order_id).execute()
    logger.info(f"[Midtrans] Snap addon(niche) order={order_id} req={request_id} amount={amount}")
    try:
        from src.utils.email import notify_payment_link
        notify_payment_link(tenant_id, order_id, amount, d.get("redirect_url"),
                            _app_cfg_int(sb, "checkout_expiry_hours", 24), sb)
    except Exception as _pe:
        logger.debug(f"[Midtrans] email link bayar addon skip (non-fatal): {_pe}")
    return {"order_id": order_id, "token": d.get("token"),
            "redirect_url": d.get("redirect_url"), "amount": amount}


def verify_signature(order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
    """signature_key = SHA512(order_id + status_code + gross_amount + ServerKey). gross_amount = string apa adanya dari payload."""
    raw = f"{order_id}{status_code}{gross_amount}{_server_key()}"
    return hashlib.sha512(raw.encode()).hexdigest() == (signature_key or "")


def _apply_settlement(sb, order: dict, txn: str | None, fraud, payment_type=None, raw=None) -> bool:
    """SATU sumber penerapan hasil transaksi — dipakai webhook (push) DAN reconciler (pull).
    IDEMPOTENT via KLAIM OPTIMISTIK (Tahap 1.3): aktivasi hanya oleh penulis yang berhasil memindah
    status order dari nilai sebelumnya → re-delivery webhook / balapan webhook×reconciler TIDAK
    dobel-menerapkan periode (kredit nilai-adil membuat dobel-terapkan = merugikan; dulu aman karena
    rumusnya konstan). settlement/capture + fraud accept → add-on: RPC settle · langganan: aktivasi."""
    order_id = order["order_id"]
    prev_status = order.get("status")
    upd = {"status": txn, "fraud_status": fraud, "updated_at": _now().isoformat()}
    if payment_type:
        upd["payment_type"] = payment_type
    if raw is not None:
        upd["raw_notification"] = raw
        if raw.get("transaction_id"):
            upd["transaction_id"] = raw["transaction_id"]
    activated = False

    if txn in ("settlement", "capture") and (fraud in (None, "", "accept")):
        # paid_at dari waktu Midtrans (settlement_time > transaction_time, zona WIB) — fallback jam server.
        _t = (raw or {}).get("settlement_time") or (raw or {}).get("transaction_time")
        upd["paid_at"] = f"{_t}+07:00" if _t else _now().isoformat()
        claimed = False
        if prev_status not in ("settlement", "capture"):
            # KLAIM: pindahkan status HANYA bila masih = prev_status (eq ganda). 0 baris = penulis
            # lain sudah menerapkan (balapan/re-delivery) → jangan aktivasi ulang.
            _cl = (sb.table("payments").update({"status": txn, "updated_at": _now().isoformat()})
                   .eq("order_id", order_id).eq("status", prev_status).execute())
            claimed = bool(_cl.data)
            if not claimed:
                logger.info(f"[Midtrans] order={order_id} sudah diterapkan penulis lain — lewati aktivasi")
        if claimed:
            if order.get("category") == "addon":
                try:
                    sb.rpc("settle_niche_request_paid",
                           {"p_request_id": order.get("ref_id"), "p_order_id": order_id}).execute()
                    activated = True
                except Exception as _re:
                    logger.error(f"[Midtrans] settle addon gagal order={order_id} ref={order.get('ref_id')}: {_re}")
            else:
                # Periode NILAI-ADIL (Pilar 2): sisa hari paket lama terkonversi — perpanjangan dini
                # tak lagi memotong hak tenant; upgrade/downgrade prorate via rasio harga.
                start, end, _note = compute_new_period(sb, order["tenant_id"], order["plan_type"], _now())
                upd["period_start"] = start.isoformat(); upd["period_end"] = end.isoformat()
                # Aktivasi + RESET penanda reminder + SIKLUS-HIDUP (LIFECYCLE B9) → tenant bersih dari jejak lapsed/blokir.
                sb.table("tenant_configs").update({
                    "subscription_status": "active", "plan_type": order["plan_type"],
                    "current_period_end": end.isoformat(),
                    "renewal_reminder_sent_at": None, "suspend_notified_at": None,
                    "suspended_at": None, "blocked_at": None, "deletion_scheduled_at": None,
                    "deletion_warn_sent": 0, "nurture_step": 0, "nurture_last_sent_at": None,
                    "lead_temp": None, "raw_assets_purged_at": None,
                    "winback_offer_pct": None, "winback_offer_expires_at": None,
                }).eq("tenant_id", order["tenant_id"]).execute()
                logger.info(f"[Midtrans] periode order={order_id}: {_note} → end {end.isoformat()}")
                activated = True
    elif txn in ("refund", "partial_refund", "chargeback") and order.get("category") != "addon":
        # Refund/chargeback LANGGANAN → CABUT akses (suspend). Add-on: niche telanjur dibuat → keputusan admin.
        sb.table("tenant_configs").update({"subscription_status": "suspended"}).eq("tenant_id", order["tenant_id"]).execute()
        logger.info(f"[Midtrans] refund order={order_id} → tenant {order['tenant_id']} SUSPENDED (akses dicabut)")

    sb.table("payments").update(upd).eq("order_id", order_id).execute()

    # Receipt email (langganan, hanya penulis yang mengaktivasi; add-on emailnya via RPC). Fail-soft.
    if activated and order.get("category") != "addon":
        try:
            from src.utils.email import notify_payment_receipt
            notify_payment_receipt(order["tenant_id"], order.get("plan_type"), order.get("gross_amount") or 0, sb, order_id=order_id)
        except Exception as _ee:
            logger.debug(f"[Midtrans] receipt email skip (non-fatal): {_ee}")
    logger.info(f"[Midtrans] settle order={order_id} txn={txn} fraud={fraud} activated={activated}")
    return activated


def handle_notification(sb, payload: dict) -> dict:
    """Webhook Midtrans (PUSH, jalur cepat). Verifikasi signature → _apply_settlement.
    ⚠️ Di akun Midtrans BERBAGI, notifikasi bisa TAK sampai (dikirim ke URL global app lain) →
    `reconcile_pending` (PULL via API status) = PENJAMIN. Keduanya pakai _apply_settlement yang SAMA."""
    order_id    = payload.get("order_id")
    status_code = str(payload.get("status_code", ""))
    gross       = str(payload.get("gross_amount", ""))
    sig         = payload.get("signature_key", "")
    if not verify_signature(order_id, status_code, gross, sig):
        logger.warning(f"[Midtrans] signature INVALID order={order_id} — TOLAK (anti-spoof)")
        return {"ok": False, "reason": "invalid_signature"}
    order = (sb.table("payments").select("*").eq("order_id", order_id).limit(1).execute().data or [None])[0]
    if not order:
        logger.warning(f"[Midtrans] order tak ditemukan: {order_id}")
        return {"ok": False, "reason": "order_not_found"}
    activated = _apply_settlement(sb, order, payload.get("transaction_status"), payload.get("fraud_status"),
                                  payment_type=payload.get("payment_type"), raw=payload)
    return {"ok": True, "order_id": order_id, "transaction_status": payload.get("transaction_status"),
            "tenant_id": order["tenant_id"], "activated": activated}


def _status_base() -> str:
    return "https://api.midtrans.com/v2" if _is_production() else "https://api.sandbox.midtrans.com/v2"


def get_transaction_status(order_id: str) -> dict:
    """GET status transaksi dari API Midtrans (terautentikasi server key = tepercaya, tanpa signature)."""
    auth = base64.b64encode((_server_key() + ":").encode()).decode()
    req = urllib.request.Request(f"{_status_base()}/{order_id}/status",
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def reconcile_pending(sb, max_age_hours: int = 48) -> dict:
    """PENJAMIN pembayaran (PULL) — tak tergantung delivery notifikasi (penting utk akun Midtrans BERBAGI).
    Tiap payment 'pending' (usia < max_age_hours): tanya API status → terapkan via _apply_settlement (jalur
    SAMA dgn webhook). expire/cancel/deny → tandai. Idempotent, fail-soft per baris (1 error tak stop loop)."""
    cutoff = (_now() - timedelta(hours=max_age_hours)).isoformat()
    rows = (sb.table("payments").select("*").eq("status", "pending")
            .gte("created_at", cutoff).limit(200).execute().data) or []
    checked = settled = 0
    for order in rows:
        oid = order["order_id"]; checked += 1
        try:
            d = get_transaction_status(oid)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # belum ada transaksi di Midtrans (user belum bayar) — biarkan pending
            logger.warning(f"[Midtrans] reconcile status gagal order={oid}: HTTP {e.code}")
            continue
        except Exception as e:
            logger.warning(f"[Midtrans] reconcile order={oid} error: {e}")
            continue
        txn = d.get("transaction_status"); fraud = d.get("fraud_status")
        if txn in ("settlement", "capture") and (fraud in (None, "", "accept")):
            _apply_settlement(sb, order, txn, fraud, payment_type=d.get("payment_type"), raw=d)
            settled += 1
        elif txn in ("expire", "cancel", "deny"):
            sb.table("payments").update({"status": txn, "updated_at": _now().isoformat()}).eq("order_id", oid).execute()
    if checked:
        logger.info(f"[Midtrans] reconcile: checked={checked} settled={settled}")
    return {"checked": checked, "settled": settled}
