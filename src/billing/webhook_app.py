"""
Webhook endpoint MINIMAL (Phase 8b, DESAIN §7 — "endpoint minimal utk webhook Midtrans").

Terima notifikasi Midtrans (server-to-server) → `billing.midtrans.handle_notification`
(signature-verified, OTORITATIF → aktivasi langganan). Worker utama = loop (bukan web server),
jadi ini app web terpisah, di-DEPLOY saat cutover:
    uvicorn src.billing.webhook_app:app --host 0.0.0.0 --port 8088
lalu nginx route `https://mesinviral.com/api/webhooks/midtrans*` → port ini.
(requirements cutover: fastapi + uvicorn). Selalu balas 200 agar Midtrans tak retry-storm;
notifikasi invalid-signature diabaikan di handler (anti-spoof), tetap 200.
"""

import os
from loguru import logger


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


try:
    import hmac as _hmac
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, RedirectResponse

    app = FastAPI(title="MesinViral Webhooks", docs_url=None, redoc_url=None)

    async def _midtrans_notify(request: "Request"):
        from src.billing.midtrans import handle_notification
        try:
            payload = await request.json()
        except Exception as e:
            logger.warning(f"[Webhook] payload bukan JSON: {e}")
            return {"ok": False, "reason": "bad_payload"}
        return handle_notification(_sb(), payload)

    async def _health():
        return {"ok": True}

    # 3 notification URL Midtrans → satu handler (handler aman karena signature-verified)
    for _p in ("/api/webhooks/midtrans",
               "/api/webhooks/midtrans/recurring",
               "/api/webhooks/midtrans/account"):
        app.add_api_route(_p, _midtrans_notify, methods=["POST"])
    app.add_api_route("/health", _health, methods=["GET"])

    # ── YouTube OAuth PLATFORM (app platform .env; server ini pegang Fernet + dance OAuth) ──────────
    # init/disconnect/status = server-to-server dari Next, di-AUTH via X-Internal-Secret
    # (== MV_INTERNAL_SECRET). Next sudah verifikasi sesi Supabase tenant SEBELUM memanggil →
    # tenant_id yg dikirim sudah ter-otentikasi. callback = redirect dari Google (publik).
    def _internal_ok(request: "Request") -> bool:
        want = os.getenv("MV_INTERNAL_SECRET") or ""
        got = request.headers.get("x-internal-secret") or ""
        return bool(want) and _hmac.compare_digest(want, got)

    async def _yt_init(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.youtube_oauth import init_connection
        try:
            body = await request.json()
            url = init_connection(
                body.get("tenant_id"),
                account_id=body.get("account_id"), label=body.get("label", ""),
                ret=body.get("ret", "/integrations"),
            )
            return {"authorize_url": url}
        except Exception as e:
            logger.warning(f"[yt-oauth] init gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _yt_callback(request: "Request"):
        from src.billing.youtube_oauth import handle_callback
        q = request.query_params
        url = handle_callback(q.get("code"), q.get("state"), q.get("error"))
        return RedirectResponse(url, status_code=302)

    async def _yt_disconnect(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.youtube_oauth import disconnect
        body = await request.json()
        disconnect(body.get("tenant_id"), body.get("account_id"))
        return {"ok": True}

    async def _yt_status(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.youtube_oauth import list_accounts
        body = await request.json()
        return list_accounts(body.get("tenant_id"))

    app.add_api_route("/api/youtube/oauth/init", _yt_init, methods=["POST"])
    app.add_api_route("/api/youtube/oauth/callback", _yt_callback, methods=["GET"])
    app.add_api_route("/api/youtube/oauth/disconnect", _yt_disconnect, methods=["POST"])
    app.add_api_route("/api/youtube/oauth/status", _yt_status, methods=["POST"])

    # ── Vault kredensial POOL (Fernet, master key hanya di sini) — model 2026-06-24 ──
    # Kunci AI per penyedia → tenant_ai_accounts (+ validate-early). Telegram → uji pesan tes.
    async def _cred_ai_set(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import set_ai_account
        try:
            b = await request.json()
            return set_ai_account(b.get("tenant_id"), b.get("provider_key"), b.get("key"),
                                  b.get("label", ""), b.get("account_id"))
        except Exception as e:
            logger.warning(f"[vault] cred ai set gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _cred_ai_delete(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import delete_ai_account
        try:
            b = await request.json()
            return delete_ai_account(b.get("tenant_id"), b.get("account_id"))
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _cred_ai_list(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import list_ai_accounts
        try:
            b = await request.json()
            return list_ai_accounts(b.get("tenant_id"))
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _cred_telegram_test(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import validate_telegram
        try:
            b = await request.json()
            return validate_telegram(b.get("tenant_id"), b.get("chat_id"))
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/credentials/ai",            _cred_ai_set,        methods=["POST"])
    app.add_api_route("/api/credentials/ai/list",       _cred_ai_list,       methods=["POST"])
    app.add_api_route("/api/credentials/ai/delete",     _cred_ai_delete,     methods=["POST"])
    app.add_api_route("/api/credentials/telegram/test", _cred_telegram_test, methods=["POST"])

    # ── Checkout Midtrans (buat transaksi Snap) — dipanggil server-to-server dari Next (mv-web),
    #    di-AUTH via X-Internal-Secret; tenant_id sudah diverifikasi sesi Supabase oleh pemanggil.
    #    Return {redirect_url,...} → Next redirect user ke halaman bayar Midtrans. ──
    async def _billing_checkout(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.midtrans import snap_create_transaction
        try:
            b = await request.json()
            # period "monthly"|"annual" (Tahap 2) — default bulanan; nilai lain ditolak di compute (invalid_period)
            _months = 12 if b.get("period") == "annual" else 1
            return snap_create_transaction(_sb(), b.get("tenant_id"), b.get("plan_type"),
                                           customer_email=b.get("email"), finish_url=b.get("finish_url"),
                                           period_months=_months)
        except Exception as e:
            logger.warning(f"[billing] checkout langganan gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _billing_niche_checkout(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.midtrans import snap_create_niche_addon
        try:
            b = await request.json()
            return snap_create_niche_addon(_sb(), b.get("tenant_id"), b.get("request_id"),
                                           customer_email=b.get("email"), finish_url=b.get("finish_url"))
        except Exception as e:
            logger.warning(f"[billing] checkout add-on niche gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/billing/checkout",       _billing_checkout,       methods=["POST"])
    app.add_api_route("/api/billing/niche-checkout", _billing_niche_checkout, methods=["POST"])

    # ── LIFECYCLE (B9): reaktivasi 1-klik dari email (token HMAC, TANPA login). Dipanggil Next via vault.
    #    trial_expired + tuas extend nyala → perpanjang trial GRATIS (re-engage). Status lain → arahkan bayar. ──
    async def _lifecycle_reactivate(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.youtube_oauth import verify_state
        try:
            b = await request.json()
            st = verify_state(b.get("token") or "")
            if not st or not st.get("t"):
                return JSONResponse({"error": "token tidak valid/kedaluwarsa"}, status_code=400)
            tid = st["t"]
            sb = _sb()
            r = sb.table("tenant_configs").select("subscription_status").eq("tenant_id", tid).limit(1).execute()
            status = (r.data or [{}])[0].get("subscription_status") if r.data else None
            if status is None:
                return JSONResponse({"error": "tenant tak ditemukan"}, status_code=404)

            def _cfg_int(key, default):
                try:
                    x = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
                    return int(x.data[0]["value"]) if x.data else default
                except Exception:
                    return default

            extend = _cfg_int("nurture_trial_extend_days", 3)
            # Trial lapsed + tuas nyala → perpanjangan GRATIS + reset penanda nurture (sekali; klik ulang → status
            # sudah 'trial' → jatuh ke cabang checkout, tak bisa extend berulang tanpa lapse lagi).
            if status == "trial_expired" and extend > 0:
                from datetime import datetime, timezone, timedelta
                end = (datetime.now(timezone.utc) + timedelta(days=extend)).isoformat()
                sb.table("tenant_configs").update({
                    "subscription_status": "trial", "current_period_end": end,
                    "nurture_step": 0, "nurture_last_sent_at": None, "trial_reminder_sent_at": None,
                    "winback_offer_pct": None, "winback_offer_expires_at": None,
                }).eq("tenant_id", tid).execute()
                logger.info(f"[lifecycle] reactivate: trial diperpanjang {extend} hari tenant={tid}")
                return {"ok": True, "action": "extended", "days": extend}
            # suspended/blocked/active/deleted → tak bisa gratis → arahkan ke pembayaran
            return {"ok": True, "action": "checkout", "status": status}
        except Exception as e:
            logger.warning(f"[lifecycle] reactivate gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/lifecycle/reactivate", _lifecycle_reactivate, methods=["POST"])

    # ── LIFECYCLE (B9): HAPUS PERMANEN tenant (aksi admin). Dipanggil Next (mv-web) via vault SETELAH
    #    requireSuperAdmin. Logika = _hard_delete_tenant (revoke token YouTube + purge S3 + purge tabel
    #    konten + anonimkan sisa; KEEP payments). Di sini karena butuh klien Google/S3 (Python). ──
    async def _admin_hard_delete(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            b = await request.json()
            tid = b.get("tenant_id")
            if not tid:
                return JSONResponse({"error": "tenant_id wajib"}, status_code=400)
            from src.billing.renewal import _hard_delete_tenant
            _hard_delete_tenant(_sb(), tid)
            logger.info(f"[lifecycle] admin HARD-DELETE tenant={tid}")
            return {"ok": True}
        except Exception as e:
            logger.warning(f"[lifecycle] admin hard-delete gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/admin/lifecycle/hard-delete", _admin_hard_delete, methods=["POST"])

    # ── Masukan /feedback (B8): kabari ADMIN via Telegram. Dipanggil Next (mv-web) via vault PASCA-insert
    #    (token bot + chat_id admin company_profile hanya di sisi Python). Fail-soft: gagal ≠ error submit. ──
    async def _feedback_notify_admin(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.telegram_notifier import TelegramNotifier
        try:
            b = await request.json()
            ok = TelegramNotifier().notify_admin_feedback(
                reason=str(b.get("reason") or ""), source=str(b.get("source") or ""),
                tenant_id=str(b.get("tenant_id") or ""), email=str(b.get("email") or ""),
                message=str(b.get("message") or ""))
            return {"ok": bool(ok)}
        except Exception as e:
            logger.warning(f"[feedback] notif admin gagal: {e}")
            return {"ok": False}

    app.add_api_route("/api/feedback/notify-admin", _feedback_notify_admin, methods=["POST"])

    # Uji-NYATA satu model katalog (butir-1). Next sudah verifikasi super-admin sebelum memanggil.
    async def _admin_test_model(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from starlette.concurrency import run_in_threadpool
        from src.config.model_tester import test_model
        try:
            b = await request.json()
            return await run_in_threadpool(test_model, str(b.get("model_key") or ""), str(b.get("key") or ""))
        except Exception as e:
            logger.warning(f"[model_tester] endpoint gagal: {e}")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    app.add_api_route("/api/admin/catalog/test-model", _admin_test_model, methods=["POST"])

    # Probe harga 1 model (butir-4): deteksi model_id/prefix salah SEKETIKA saat admin simpan model.
    async def _admin_price_probe(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from starlette.concurrency import run_in_threadpool
        from src.billing.price_sync import sync_prices
        try:
            b = await request.json()
            mk = str(b.get("model_key") or "")
            res = await run_in_threadpool(sync_prices, None, True, mk)
            return {"ok": True, "priced": mk not in (res.get("missing") or []), **res}
        except Exception as e:
            logger.warning(f"[price_probe] gagal: {e}")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    app.add_api_route("/api/admin/catalog/price-probe", _admin_price_probe, methods=["POST"])

    # Startup: cermin nilai-sah katalog (adapter/enum) dari registry KODE → DB (self-heal, anti-drift).
    @app.on_event("startup")
    async def _sync_catalog_enums():
        try:
            from src.config.catalog_sync import sync_catalog_valid_values
            sync_catalog_valid_values()
        except Exception as e:
            logger.warning(f"[catalog_sync] startup sync gagal (non-fatal): {e}")

except ImportError:
    # fastapi belum terinstall di env dev — endpoint diaktifkan saat cutover (tambah ke requirements).
    app = None
    logger.debug("[Webhook] fastapi belum terinstall — app=None (aktif saat cutover).")
