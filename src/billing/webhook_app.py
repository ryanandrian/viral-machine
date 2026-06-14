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
    from fastapi import FastAPI, Request

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

except ImportError:
    # fastapi belum terinstall di env dev — endpoint diaktifkan saat cutover (tambah ke requirements).
    app = None
    logger.debug("[Webhook] fastapi belum terinstall — app=None (aktif saat cutover).")
