"""
Loader/writer OAuth Google (YouTube) dari tabel tenant_credentials — Phase 4.4 BYO-CC.

Kredensial tersimpan TERENKRIPSI (Fernet, src/utils/crypto.py). DB-first; caller boleh
fallback ke file (transisi sampai creds tiap tenant di-seed ke DB). Butuh SUPABASE_KEY =
service_role di env (RLS tenant_credentials = service_role only).
"""

import os
from loguru import logger

from src.utils.crypto import encrypt, decrypt


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def load_google_credentials(tenant_id: str) -> dict | None:
    """Return dict creds (decrypted) untuk google.oauth2 Credentials, atau None bila
    tak ada / belum di-seed. Bentuk: client_id/client_secret/refresh_token/token/token_uri/
    scopes/channel_id."""
    try:
        res = _sb().table("tenant_credentials").select("*").eq("tenant_id", tenant_id).limit(1).execute()
        if not res.data:
            return None
        r = res.data[0]
        if not r.get("google_refresh_token_enc"):
            return None
        return {
            "client_id":     r.get("google_client_id"),
            "client_secret": decrypt(r.get("google_client_secret_enc")),
            "refresh_token": decrypt(r.get("google_refresh_token_enc")),
            "token":         decrypt(r.get("google_access_token_enc")),
            "token_uri":     "https://oauth2.googleapis.com/token",
            "scopes":        r.get("scopes") or [],
            "channel_id":    r.get("channel_id"),
        }
    except Exception as e:
        logger.warning(f"[tenant_credentials] load gagal ({e}) — caller fallback ke file")
        return None


def save_google_access_token(tenant_id: str, access_token: str, token_expiry=None) -> None:
    """Update access_token terenkripsi setelah refresh (best-effort, tak crash pipeline)."""
    try:
        upd = {"google_access_token_enc": encrypt(access_token)}
        if token_expiry is not None:
            upd["token_expiry"] = token_expiry
        _sb().table("tenant_credentials").update(upd).eq("tenant_id", tenant_id).execute()
    except Exception as e:
        logger.warning(f"[tenant_credentials] simpan access_token gagal (non-fatal): {e}")
