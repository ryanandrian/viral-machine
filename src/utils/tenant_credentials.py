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


def _row_to_creds(r: dict | None) -> dict | None:
    """Map baris (channel_credentials / tenant_credentials) → dict creds decrypted, atau None
    bila tak ada refresh_token. Kedua tabel memakai nama kolom google_* yang sama."""
    if not r or not r.get("google_refresh_token_enc"):
        return None
    return {
        "client_id":     r.get("google_client_id"),
        "client_secret": decrypt(r.get("google_client_secret_enc")) if r.get("google_client_secret_enc") else None,
        "refresh_token": decrypt(r.get("google_refresh_token_enc")),
        "token":         decrypt(r.get("google_access_token_enc")) if r.get("google_access_token_enc") else None,
        "token_uri":     "https://oauth2.googleapis.com/token",
        "scopes":        r.get("scopes") or [],
        "channel_id":    r.get("yt_channel_id") or r.get("channel_id"),
    }


def load_google_credentials(tenant_id: str, channel_id: str | None = None) -> dict | None:
    """Creds OAuth (decrypted) untuk google.oauth2 Credentials. PER-CHANNEL:
      1. channel_id → `channel_credentials` (multi-channel, migr 0060)
      2. fallback → `tenant_credentials` per-tenant (legacy/backward-compat)
    None bila tak ada / belum di-seed. Caller tanpa channel_id = perilaku LAMA (tenant_credentials)."""
    try:
        sb = _sb()
        if channel_id:
            res = sb.table("channel_credentials").select("*").eq("channel_id", channel_id).limit(1).execute()
            if res.data:
                creds = _row_to_creds(res.data[0])
                if creds:
                    return creds
        res = sb.table("tenant_credentials").select("*").eq("tenant_id", tenant_id).limit(1).execute()
        return _row_to_creds(res.data[0]) if res.data else None
    except Exception as e:
        logger.warning(f"[tenant_credentials] load gagal ({e}) — caller fallback ke file")
        return None


def save_google_access_token(tenant_id: str, access_token: str, token_expiry=None, channel_id: str | None = None) -> None:
    """Update access_token terenkripsi pasca-refresh. PER-CHANNEL bila channel_id (→ channel_credentials);
    else tenant_credentials (legacy). Best-effort (tak crash pipeline)."""
    try:
        upd = {"google_access_token_enc": encrypt(access_token)}
        if token_expiry is not None:
            upd["token_expiry"] = token_expiry
        sb = _sb()
        if channel_id:
            sb.table("channel_credentials").update(upd).eq("channel_id", channel_id).execute()
        else:
            sb.table("tenant_credentials").update(upd).eq("tenant_id", tenant_id).execute()
    except Exception as e:
        logger.warning(f"[tenant_credentials] simpan access_token gagal (non-fatal): {e}")
