"""
Loader/writer OAuth Google (YouTube) dari POOL `tenant_youtube_accounts` — model OAuth PLATFORM (2026-06-25).
client_id/secret = app PLATFORM (.env GOOGLE_CLIENT_*); refresh/access token per koneksi (Fernet, src/utils/crypto.py).
Resolusi: channels.youtube_account_id → akun pool; fallback akun pool tunggal valid tenant. NO-FALLBACK file.
Butuh SUPABASE_KEY = service_role di env. (Tabel lama tenant_credentials/channel_credentials sudah DI-DROP migr 0095.)
"""

import os
from loguru import logger

from src.utils.crypto import encrypt, decrypt


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _row_to_creds(r: dict | None) -> dict | None:
    """Map baris tenant_youtube_accounts → dict creds decrypted, atau None bila tak ada refresh_token.
    OAuth PLATFORM: client_id/secret dari .env PLATFORM (GOOGLE_CLIENT_ID/SECRET), BUKAN dari baris tenant
    (kolom google_client_id/secret di baris = artefak BYO-CC lama, tak dipakai lagi)."""
    if not r or not r.get("google_refresh_token_enc"):
        return None
    return {
        "client_id":     os.getenv("GOOGLE_CLIENT_ID") or r.get("google_client_id"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET") or (decrypt(r.get("google_client_secret_enc")) if r.get("google_client_secret_enc") else None),
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


def mark_youtube_account_invalid(tenant_id: str, channel_id: str | None = None, *, reason: str = "") -> bool:
    """[B11] 3.2 — Tandai koneksi YouTube (pool) INVALID saat refresh token DITOLAK PERMANEN oleh
    Google (OAuth `invalid_grant`: token dicabut/kedaluwarsa). Mustahil sembuh dengan diulang.

    Efek berantai (semua sudah terpasang): `status='invalid'` → fungsi DB `channel_missing`
    (syarat status='valid') menutup gerbang readiness → producer BERHENTI memproduksi channel ini
    (hemat biaya) & FE /integrations menampilkan badge invalid. Pulih otomatis saat tenant reconnect
    (OAuth callback set status='valid').

    IDEMPOTEN & best-effort (TAK PERNAH meng-crash pipeline): flip HANYA bila status masih 'valid'
    → return True (transisi). Sudah invalid / tak ada baris → return False (no-op).
    Pada transisi, kirim notif SEKALI ke tenant (no silent degradation)."""
    try:
        sb = _sb()
        aid = _account_id_for(sb, tenant_id, channel_id)
        if not aid:
            return False
        res = (sb.table("tenant_youtube_accounts")
               .select("status,yt_channel_title,label").eq("id", aid).limit(1).execute())
        row = (res.data or [None])[0]
        if not row or row.get("status") == "invalid":
            return False   # tak ada baris / sudah invalid → no-op (cegah notif berulang)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        sb.table("tenant_youtube_accounts").update(
            {"status": "invalid", "validated_at": now, "updated_at": now}
        ).eq("id", aid).execute()
        logger.error(f"[tenant_credentials] koneksi YouTube {aid} → INVALID (tenant {tenant_id}; {reason or 'invalid_grant'})")
        _notify_youtube_invalid(sb, tenant_id, row.get("yt_channel_title") or row.get("label") or "")
        return True
    except Exception as e:
        logger.warning(f"[tenant_credentials] mark invalid gagal (non-fatal): {e}")
        return False


def _notify_youtube_invalid(sb, tenant_id: str, channel_label: str) -> None:
    """Best-effort Telegram ke TENANT (hormati saklar telegram_enabled). Pesan jelas & actionable:
    koneksi putus → produksi/publish DITAHAN → sambungkan ulang. Gagal telegram ≠ crash."""
    try:
        from src.utils.telegram_notifier import TelegramNotifier
        _who = f"'{channel_label}' " if channel_label else ""
        msg = (f"❌ Koneksi YouTube {_who}terputus (izin dicabut / kedaluwarsa). "
               f"Produksi & publish channel ini DITAHAN otomatis agar tidak membuang biaya. "
               f"Sambungkan ulang di menu Integrasi → Koneksi YouTube untuk melanjutkan.")
        TelegramNotifier().notify_tenant(sb, tenant_id, msg)
    except Exception as e:
        logger.warning(f"[tenant_credentials] notif invalid gagal (non-fatal): {e}")
