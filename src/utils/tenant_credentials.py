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


def _account_id_for(sb, tenant_id: str, channel_id: str | None) -> str | None:
    """id koneksi YouTube (tenant_youtube_accounts) yang dipakai channel ini, atau akun pool tenant (tunggal/valid)."""
    if channel_id:
        r = sb.table("channels").select("youtube_account_id").eq("id", channel_id).limit(1).execute()
        aid = (r.data or [{}])[0].get("youtube_account_id") if r.data else None
        if aid:
            return aid
    r = sb.table("tenant_youtube_accounts").select("id").eq("tenant_id", tenant_id).eq("status", "valid").limit(1).execute()
    return (r.data or [{}])[0].get("id") if r.data else None


def load_google_credentials(tenant_id: str, channel_id: str | None = None) -> dict | None:
    """Creds OAuth (decrypted) dari POOL `tenant_youtube_accounts` (model 2026-06-24):
      channel.youtube_account_id → akun pool; fallback akun pool tenant (valid).
    None bila tak ada / belum connect."""
    try:
        sb = _sb()
        aid = _account_id_for(sb, tenant_id, channel_id)
        if not aid:
            return None
        res = sb.table("tenant_youtube_accounts").select("*").eq("id", aid).limit(1).execute()
        return _row_to_creds(res.data[0]) if res.data else None
    except Exception as e:
        logger.warning(f"[tenant_credentials] load gagal ({e})")
        return None


def save_google_access_token(tenant_id: str, access_token: str, token_expiry=None, channel_id: str | None = None) -> None:
    """Update access_token terenkripsi pasca-refresh ke akun pool YouTube. Best-effort (tak crash pipeline)."""
    try:
        sb = _sb()
        aid = _account_id_for(sb, tenant_id, channel_id)
        if not aid:
            return
        upd = {"google_access_token_enc": encrypt(access_token)}
        if token_expiry is not None:
            upd["token_expiry"] = token_expiry
        sb.table("tenant_youtube_accounts").update(upd).eq("id", aid).execute()
    except Exception as e:
        logger.warning(f"[tenant_credentials] simpan access_token gagal (non-fatal): {e}")
