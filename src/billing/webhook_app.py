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

    # ── YouTube OAuth BYO-CC (Opsi A: server ini memegang Fernet + dance OAuth) ──────────
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
                body.get("tenant_id"), body.get("client_id"),
                body.get("client_secret"), channel_id=body.get("channel_id"),
                ret=body.get("ret", "/settings"),
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
        disconnect(body.get("tenant_id"), channel_id=body.get("channel_id"))
        return {"ok": True}

    async def _yt_status(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.billing.youtube_oauth import connection_status
        body = await request.json()
        return connection_status(body.get("tenant_id"), channel_id=body.get("channel_id"))

    app.add_api_route("/api/youtube/oauth/init", _yt_init, methods=["POST"])
    app.add_api_route("/api/youtube/oauth/callback", _yt_callback, methods=["GET"])
    app.add_api_route("/api/youtube/oauth/disconnect", _yt_disconnect, methods=["POST"])
    app.add_api_route("/api/youtube/oauth/status", _yt_status, methods=["POST"])

    # ── Vault API key AI (migr 0044): enkripsi Fernet + tulis *_enc (master key hanya di sini) ──
    async def _keys_set(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import set_api_keys
        try:
            body = await request.json()
            return set_api_keys(body.get("tenant_id"), body)
        except Exception as e:
            logger.warning(f"[key-vault] set gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/keys/set", _keys_set, methods=["POST"])

    # ── F2-09: vault MULTI-akun — tambah akun API (encrypt Fernet + insert tenant_api_accounts) ──
    async def _accounts_set(request: "Request"):
        if not _internal_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        from src.utils.api_key_vault import add_api_account
        try:
            body = await request.json()
            return add_api_account(body.get("tenant_id"), body.get("component"), body.get("label"),
                                   body.get("key"), body.get("provider"))
        except Exception as e:
            logger.warning(f"[key-vault] add account gagal: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    app.add_api_route("/api/accounts/set", _accounts_set, methods=["POST"])

except ImportError:
    # fastapi belum terinstall di env dev — endpoint diaktifkan saat cutover (tambah ke requirements).
    app = None
    logger.debug("[Webhook] fastapi belum terinstall — app=None (aktif saat cutover).")
