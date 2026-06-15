"""
YouTube OAuth BYO-CC — alur web per-tenant (gate-cutover real-build, owner-approved Opsi A).

PRINSIP KEAMANAN (owner 2026-06-15: "seluruh kredensial tenant AMAN" = nilai jual):
- Tenant membawa Google OAuth app SENDIRI (client_id + client_secret). Kita TIDAK pernah
  memegang password Google mereka — hanya refresh_token hasil consent mereka.
- SELURUH enkripsi (Fernet, ENCRYPTION_KEY) + tukar-token + tulis tenant_credentials terjadi
  DI SERVER ini (Python). Master key TIDAK pernah ke frontend/Vercel (Opsi A — pilihan owner).
- tenant_credentials: client_secret/refresh_token/access_token = Fernet; RLS service_role-only
  (frontend/tenant TIDAK bisa baca raw). PK = tenant_id (1 user = 1 tenant).

Modul ini BEBAS-fastapi (diuji via panggil-fungsi langsung, pola sama spt billing.midtrans).
Route tipis di src/billing/webhook_app.py men-delegate ke fungsi di sini.

State (anti-CSRF + binding tenant): HMAC-SHA256 atas {t,n,e,r} pakai OAUTH_STATE_SECRET
(BUKAN ENCRYPTION_KEY — secret terpisah; bocornya TIDAK membuka kredensial apa pun).

Env:
  ENCRYPTION_KEY              Fernet master (sudah ada; src/utils/crypto.py)
  SUPABASE_URL / SUPABASE_KEY service_role (sudah ada)
  OAUTH_STATE_SECRET          rahasia tanda-tangan state (baru)
  YOUTUBE_OAUTH_REDIRECT_URI  callback tetap yg tenant daftarkan di GCP app mereka (baru)
  APP_BASE_URL                tujuan redirect browser setelah selesai (baru; default localhost:3000)
"""

import os
import json
import time
import hmac
import base64
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote

from loguru import logger

from src.utils.crypto import encrypt, decrypt

# Scope identik dgn youtube_publisher.YouTubePublisher.SCOPES (upload + analytics).
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

STATE_TTL = 600  # detik (10 menit) — cukup untuk consent, sempit untuk anti-replay.


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} tidak diset di env — wajib untuk YouTube OAuth.")
    return v


def _redirect_uri() -> str:
    return _require("YOUTUBE_OAUTH_REDIRECT_URI")


def _app_base() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- State: HMAC (anti-CSRF + binding tenant_id + return-path) ----------

def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_state(tenant_id: str, ret: str = "/settings", ttl: int = STATE_TTL) -> str:
    """Tanda-tangani state {tenant_id, nonce, exp, return-path}. Dipakai sbg param `state` OAuth."""
    secret = _require("OAUTH_STATE_SECRET").encode()
    body = {"t": tenant_id, "n": _b64u(os.urandom(9)), "e": int(time.time()) + ttl, "r": ret}
    payload = _b64u(json.dumps(body, separators=(",", ":")).encode())
    sig = _b64u(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_state(state: str) -> dict | None:
    """Verifikasi signature + expiry. Return {'t':tenant_id,'r':ret} atau None bila invalid."""
    try:
        secret = _require("OAUTH_STATE_SECRET").encode()
        payload, sig = state.split(".", 1)
        expected = _b64u(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64u(payload))
        if int(data.get("e", 0)) < int(time.time()):
            return None
        if not data.get("t"):
            return None
        return {"t": data["t"], "r": data.get("r", "/settings")}
    except Exception as e:
        logger.warning(f"[yt-oauth] verify_state gagal: {e}")
        return None


# ---------- OAuth Flow (google-auth-oauthlib, web flow) ----------

def _client_config(client_id: str, client_secret: str) -> dict:
    return {"web": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [_redirect_uri()],
    }}


def _flow(client_id: str, client_secret: str, state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    return Flow.from_client_config(
        _client_config(client_id, client_secret),
        scopes=SCOPES,
        redirect_uri=_redirect_uri(),
        state=state,
    )


# ---------- Penyimpanan kredensial (service_role, Fernet) ----------

def save_client_creds(tenant_id: str, client_id: str, client_secret: str) -> None:
    """Simpan OAuth app milik tenant: client_id (plain) + client_secret (Fernet). Upsert PK tenant_id.
    Kolom token (refresh/access) TIDAK disentuh di sini — diisi saat callback."""
    _sb().table("tenant_credentials").upsert({
        "tenant_id": tenant_id,
        "google_client_id": client_id.strip(),
        "google_client_secret_enc": encrypt(client_secret.strip()),
        "updated_at": _now_iso(),
    }, on_conflict="tenant_id").execute()


def _store_tokens(tenant_id: str, creds, channel_id: str | None) -> None:
    """Tulis token hasil consent — semua sensitif di-Fernet. refresh_token hanya ditimpa bila ada
    (Google kadang tak kirim ulang refresh_token; jangan hapus yang lama dengan null)."""
    upd = {
        "google_access_token_enc": encrypt(creds.token),
        "token_expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
        "channel_id": channel_id,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "updated_at": _now_iso(),
    }
    if creds.refresh_token:
        upd["google_refresh_token_enc"] = encrypt(creds.refresh_token)
    _sb().table("tenant_credentials").update(upd).eq("tenant_id", tenant_id).execute()


def _fetch_channel_id(creds) -> str | None:
    """Ambil channel_id YouTube milik pemberi-consent (mine=true). Best-effort."""
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        items = yt.channels().list(part="id", mine=True).execute().get("items", [])
        return items[0]["id"] if items else None
    except Exception as e:
        logger.warning(f"[yt-oauth] fetch channel_id gagal (non-fatal): {e}")
        return None


# ---------- API publik (dipanggil route webhook_app) ----------

def init_connection(tenant_id: str, client_id: str, client_secret: str, ret: str = "/settings") -> str:
    """Simpan OAuth app tenant + bangun consent URL Google (offline + prompt consent → refresh_token).
    Return authorize_url. Dipanggil server-to-server dari Next (X-Internal-Secret)."""
    if not (tenant_id and client_id and client_secret):
        raise ValueError("tenant_id/client_id/client_secret wajib.")
    save_client_creds(tenant_id, client_id, client_secret)
    flow = _flow(client_id, client_secret, state=sign_state(tenant_id, ret=ret))
    url, _ = flow.authorization_url(
        access_type="offline",       # minta refresh_token (akses jangka panjang)
        include_granted_scopes="true",
        prompt="consent",            # paksa Google kirim refresh_token tiap kali
    )
    return url


def handle_callback(code: str | None, state: str | None, error: str | None = None) -> str:
    """Tukar code→token, ambil channel_id, simpan terenkripsi. Return URL redirect browser ke app.
    SELALU redirect (tak pernah raise) — UX bersih; error disampaikan via query string."""
    app = _app_base()
    st = verify_state(state) if state else None
    ret = (st or {}).get("r", "/settings")

    def _err(reason: str) -> str:
        return f"{app}{ret}?youtube=error&reason={quote(reason)}"

    if error:
        return _err(error)
    if not st:
        return _err("bad_state")
    if not code:
        return _err("no_code")

    tenant_id = st["t"]
    try:
        res = (_sb().table("tenant_credentials")
               .select("google_client_id,google_client_secret_enc")
               .eq("tenant_id", tenant_id).limit(1).execute())
        if not res.data or not res.data[0].get("google_client_secret_enc"):
            return _err("no_client")
        client_id = res.data[0]["google_client_id"]
        client_secret = decrypt(res.data[0]["google_client_secret_enc"])

        flow = _flow(client_id, client_secret, state=state)
        flow.fetch_token(code=code)
        creds = flow.credentials
        if not creds.refresh_token:
            # Tanpa refresh_token, upload jangka-panjang mustahil → minta tenant cabut akses & ulang.
            logger.warning(f"[yt-oauth] tenant={tenant_id} consent tanpa refresh_token")
            return _err("no_refresh_token")
        channel_id = _fetch_channel_id(creds)
        _store_tokens(tenant_id, creds, channel_id)
        logger.info(f"[yt-oauth] tenant={tenant_id} tersambung (channel={channel_id})")
    except Exception as e:
        logger.error(f"[yt-oauth] callback gagal tenant={tenant_id}: {e}")
        return _err("exchange_failed")

    return f"{app}{ret}?youtube=connected"


def disconnect(tenant_id: str) -> None:
    """Putuskan YouTube: hapus token + channel (Fernet → null), simpan OAuth app (client_id/secret)
    agar reconnect satu-klik. service_role only."""
    _sb().table("tenant_credentials").update({
        "google_refresh_token_enc": None,
        "google_access_token_enc": None,
        "token_expiry": None,
        "channel_id": None,
        "scopes": [],
        "updated_at": _now_iso(),
    }).eq("tenant_id", tenant_id).execute()


def connection_status(tenant_id: str) -> dict:
    """Status untuk FE (lewat Next, bukan langsung): connected/has_client/channel_id. Tak bocorkan secret."""
    res = (_sb().table("tenant_credentials")
           .select("google_client_id,google_refresh_token_enc,channel_id")
           .eq("tenant_id", tenant_id).limit(1).execute())
    if not res.data:
        return {"connected": False, "has_client": False, "channel_id": None}
    r = res.data[0]
    return {
        "connected": bool(r.get("google_refresh_token_enc")),
        "has_client": bool(r.get("google_client_id")),
        "channel_id": r.get("channel_id"),
    }
