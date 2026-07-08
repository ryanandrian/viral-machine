"""
YouTube OAuth PLATFORM (model final 2026-06-25) — alur web; tenant TIDAK pegang client creds.

PRINSIP:
- App Google = PLATFORM (1 app utk semua tenant): GOOGLE_CLIENT_ID/SECRET di .env (swappable).
  Tenant cukup "Hubungkan dengan Google" → consent → kita simpan refresh/access token mereka.
- Enkripsi (Fernet, ENCRYPTION_KEY) + tukar-token + tulis ke POOL `tenant_youtube_accounts`
  terjadi DI SERVER ini. Master key tak pernah ke frontend.
- 1 tenant boleh banyak koneksi (pool); channel pilih koneksi + channel tujuan.
  (Model BYO-CC lama — tenant bawa client sendiri — sudah DIBUANG.)

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

# Google sering MENGEMBALIKAN scope lebih banyak dari yang diminta (mis. openid/email/profile karena akun
# sudah login Google) → oauthlib menolak "Scope has changed" saat fetch_token. Relax = terima scope superset.
# (Tak menurunkan keamanan: kita tetap simpan refresh_token utk scope YouTube yang kita pakai.)
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

# Scope identik dgn youtube_publisher.YouTubePublisher.SCOPES (upload + baca + analitik).
# B4: scope "kelola penuh" (.../auth/youtube) DIBUANG — verifikasi Google lebih ringan; dulu cuma
# dipakai update deskripsi channel hardcode yg sudah dihapus.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
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


def sign_state(tenant_id: str, account_id: str | None = None, ret: str = "/integrations", ttl: int = STATE_TTL) -> str:
    """Tanda-tangani state {tenant_id, account_id, nonce, exp, return-path}. account_id = baris
    tenant_youtube_accounts (POOL koneksi, model 2026-06-24). Dipakai sbg param `state` OAuth."""
    secret = _require("OAUTH_STATE_SECRET").encode()
    body = {"t": tenant_id, "a": account_id, "n": _b64u(os.urandom(9)), "e": int(time.time()) + ttl, "r": ret}
    payload = _b64u(json.dumps(body, separators=(",", ":")).encode())
    sig = _b64u(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_state(state: str) -> dict | None:
    """Verifikasi signature + expiry. Return {'t':tenant_id,'a':account_id,'r':ret} atau None."""
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
        return {"t": data["t"], "a": data.get("a"), "r": data.get("r", "/integrations")}
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
    # autogenerate_code_verifier=False → MATIKAN PKCE. Client ini = web-app rahasia (punya client_secret),
    # jadi PKCE tak diperlukan. Default lib = True → init kirim code_challenge, tapi callback bikin Flow baru
    # tanpa code_verifier asli → Google tolak "Missing code verifier" (invalid_grant). Mematikan PKCE =
    # init tak kirim challenge → callback tak butuh verifier. (Stateless: tak perlu simpan verifier antar-request.)
    return Flow.from_client_config(
        _client_config(client_id, client_secret),
        scopes=SCOPES,
        redirect_uri=_redirect_uri(),
        state=state,
        autogenerate_code_verifier=False,
    )


# ---------- Penyimpanan kredensial (service_role, Fernet) ----------

def _platform_client() -> tuple[str, str]:
    """Kredensial OAuth app PLATFORM (1 app utk SEMUA tenant) dari .env. Tenant TIDAK pegang ini.
    Swappable: ganti GOOGLE_CLIENT_ID/SECRET di .env (mis. developer → lumite.biz.id) tanpa sentuh data tenant."""
    cid = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    sec = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not (cid and sec):
        raise ValueError("GOOGLE_CLIENT_ID/SECRET platform belum diset di .env")
    return cid, sec


def _create_account(tenant_id: str, account_id: str | None, label: str = "") -> str:
    """Buat baris koneksi YouTube (pool) — TANPA client creds (OAuth Platform). Return account_id."""
    sb = _sb()
    if account_id:
        sb.table("tenant_youtube_accounts").update({"updated_at": _now_iso()}).eq("id", account_id).eq("tenant_id", tenant_id).execute()
        return account_id
    res = sb.table("tenant_youtube_accounts").insert(
        {"tenant_id": tenant_id, "label": (label or "YouTube")[:80], "status": "unchecked", "updated_at": _now_iso()}
    ).execute()
    return (res.data or [{}])[0].get("id")


def _store_tokens(tenant_id: str, account_id: str, creds, identity: dict | None = None) -> None:
    """Tulis token hasil consent (Fernet) ke baris pool + status='valid' + identitas channel (nama/foto).
    refresh_token hanya ditimpa bila ada."""
    # CATATAN: tabel tenant_youtube_accounts TIDAK punya kolom `scopes` → jangan ditulis (dulu bikin
    # update gagal → exchange_failed). Scope tak perlu disimpan: publisher fallback ke SCOPES bila kosong.
    upd = {
        "google_access_token_enc": encrypt(creds.token),
        "token_expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
        "status": "valid", "validated_at": _now_iso(), "updated_at": _now_iso(),
    }
    if creds.refresh_token:
        upd["google_refresh_token_enc"] = encrypt(creds.refresh_token)
    if identity:
        upd["yt_channel_id"] = identity["id"]
        upd["yt_channel_title"] = (identity.get("title") or "")[:120] or None
        upd["yt_channel_thumb"] = identity.get("thumb") or None
    _sb().table("tenant_youtube_accounts").update(upd).eq("id", account_id).eq("tenant_id", tenant_id).execute()


def _fetch_channel_identity(creds) -> dict | None:
    """Ambil IDENTITAS channel pemberi-consent: id + nama + thumbnail (mine=true).
    [B11] Batch 1.2: identitas = fondasi pagar salah-channel → kegagalan di sini = koneksi GAGAL JUJUR
    (bukan best-effort NULL seperti dulu; tanpa identitas semua pagar buta)."""
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        items = yt.channels().list(part="id,snippet", mine=True).execute().get("items", [])
        if not items:
            return None
        it = items[0]
        sn = it.get("snippet") or {}
        thumbs = sn.get("thumbnails") or {}
        thumb = ((thumbs.get("default") or thumbs.get("medium") or {}).get("url")) or None
        return {"id": it["id"], "title": sn.get("title") or "", "thumb": thumb}
    except Exception as e:
        logger.warning(f"[yt-oauth] fetch channel identity gagal: {e}")
        return None


def _find_existing_connection(tenant_id: str, yt_channel_id: str, exclude_id: str) -> str | None:
    """Cari baris pool tenant yang SUDAH memegang channel YouTube ini (dedup, [B11] Batch 1.2)."""
    res = (_sb().table("tenant_youtube_accounts").select("id")
           .eq("tenant_id", tenant_id).eq("yt_channel_id", yt_channel_id)
           .neq("id", exclude_id).limit(1).execute())
    return (res.data or [{}])[0].get("id")


def _delete_placeholder(tenant_id: str, account_id: str) -> None:
    """Hapus baris pool HANYA bila masih placeholder (belum pernah punya refresh_token) —
    jangan pernah menghapus koneksi hidup. Fail-soft."""
    try:
        res = (_sb().table("tenant_youtube_accounts").select("google_refresh_token_enc")
               .eq("id", account_id).eq("tenant_id", tenant_id).limit(1).execute())
        row = (res.data or [None])[0]
        if row is not None and not row.get("google_refresh_token_enc"):
            _sb().table("tenant_youtube_accounts").delete().eq("id", account_id).eq("tenant_id", tenant_id).execute()
    except Exception as e:
        logger.warning(f"[yt-oauth] hapus placeholder gagal (non-fatal): {e}")


# ---------- API publik (dipanggil route webhook_app) ----------

def init_connection(tenant_id: str, account_id: str | None = None, label: str = "", ret: str = "/integrations") -> str:
    """OAuth PLATFORM: buat baris koneksi (pool) + consent URL pakai app PLATFORM (GOOGLE_CLIENT_ID/SECRET .env).
    Tenant TIDAK pegang client creds — cukup "Hubungkan dengan Google". account_id None → koneksi BARU (boleh banyak akun)."""
    if not tenant_id:
        raise ValueError("tenant_id wajib.")
    cid, sec = _platform_client()
    aid = _create_account(tenant_id, account_id, label=label)
    flow = _flow(cid, sec, state=sign_state(tenant_id, account_id=aid, ret=ret))
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
    account_id = st.get("a")   # baris tenant_youtube_accounts (pool)
    if not account_id:
        return _err("no_account")
    try:
        cid, sec = _platform_client()   # OAuth Platform: pakai app platform, bukan client per-tenant
        flow = _flow(cid, sec, state=state)
        flow.fetch_token(code=code)
        creds = flow.credentials
        if not creds.refresh_token:
            # Tanpa refresh_token, upload jangka-panjang mustahil → minta tenant cabut akses & ulang.
            logger.warning(f"[yt-oauth] tenant={tenant_id} consent tanpa refresh_token")
            _delete_placeholder(tenant_id, account_id)
            return _err("no_refresh_token")
        # [B11] Batch 1.2 — identitas WAJIB (id+nama+foto). Gagal baca = koneksi gagal JUJUR:
        # tanpa identitas, pagar anti-duplikat & anti-salah-channel buta. Placeholder dibersihkan.
        identity = _fetch_channel_identity(creds)
        if not identity:
            _delete_placeholder(tenant_id, account_id)
            return _err("identity_failed")
        # [B11] Batch 1.2 — DEDUP: channel YouTube ini sudah terhubung? → segarkan token di baris LAMA,
        # buang placeholder baru, beri pesan ramah (bukan baris ganda / bukan error menakutkan).
        existing = _find_existing_connection(tenant_id, identity["id"], exclude_id=account_id)
        if existing:
            _store_tokens(tenant_id, existing, creds, identity=identity)
            _delete_placeholder(tenant_id, account_id)
            logger.info(f"[yt-oauth] tenant={tenant_id} channel {identity['id']} sudah terhubung → token disegarkan (akun={existing})")
            return f"{app}{ret}?youtube=already&channel={quote(identity.get('title') or identity['id'])}"
        _store_tokens(tenant_id, account_id, creds, identity=identity)
        logger.info(f"[yt-oauth] tenant={tenant_id} akun={account_id} tersambung (yt={identity['id']} \"{identity.get('title','')}\")")
        return f"{app}{ret}?youtube=connected&channel={quote(identity.get('title') or identity['id'])}"
    except Exception as e:
        logger.error(f"[yt-oauth] callback gagal tenant={tenant_id}: {e}")
        return _err("exchange_failed")


def disconnect(tenant_id: str, account_id: str) -> None:
    """Putus + HAPUS koneksi YouTube dari pool + lepas channel yang menunjuknya. service_role only."""
    if not account_id:
        return
    sb = _sb()
    sb.table("channels").update({"youtube_account_id": None}).eq("tenant_id", tenant_id).eq("youtube_account_id", account_id).execute()
    sb.table("tenant_youtube_accounts").delete().eq("id", account_id).eq("tenant_id", tenant_id).execute()


def _revoke_google_token(token: str) -> bool:
    """Cabut 1 token (refresh/access) di Google (POST oauth2.googleapis.com/revoke). Fail-soft.
    HTTP 400 = token sudah invalid/dicabut → dianggap sukses (idempotent)."""
    if not token:
        return False
    try:
        import urllib.request, urllib.parse, urllib.error
        data = urllib.parse.urlencode({"token": token}).encode()
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/revoke", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        logger.warning(f"[yt-oauth] revoke HTTP {e.code} (token mungkin sudah invalid) — lanjut")
        return e.code == 400
    except Exception as e:
        logger.warning(f"[yt-oauth] revoke gagal (non-fatal): {e}")
        return False


def revoke_tenant_tokens(tenant_id: str) -> int:
    """UU PDP: cabut SEMUA refresh-token YouTube tenant di Google SEBELUM hapus data (LIFECYCLE hard-delete).
    Jangan tinggalkan token hidup. Return jumlah token dicabut. Fail-soft (tak pernah raise)."""
    if not tenant_id:
        return 0
    n = 0
    try:
        res = (_sb().table("tenant_youtube_accounts")
               .select("id,google_refresh_token_enc").eq("tenant_id", tenant_id).execute())
        for r in (res.data or []):
            enc = r.get("google_refresh_token_enc")
            if not enc:
                continue
            try:
                tok = decrypt(enc)
            except Exception:
                continue
            if _revoke_google_token(tok):
                n += 1
    except Exception as e:
        logger.warning(f"[yt-oauth] revoke_tenant_tokens gagal (non-fatal): {e}")
    logger.info(f"[yt-oauth] revoke_tenant_tokens tenant={tenant_id}: {n} token dicabut")
    return n


def list_accounts(tenant_id: str) -> dict:
    """Daftar koneksi YouTube tenant (untuk FE Credential + picker channel). Tak bocorkan secret.
    [B11] Batch 1.3: + identitas (nama/foto channel) + used_by (channel MesinViral pemakai) —
    dasar UI 'berwajah' + cegatan redundant di picker."""
    sb = _sb()
    res = (sb.table("tenant_youtube_accounts")
           .select("id,label,status,yt_channel_id,yt_channel_title,yt_channel_thumb,google_client_id,google_refresh_token_enc")
           .eq("tenant_id", tenant_id).order("created_at").execute())
    # Peta pemakaian: youtube_account_id → daftar channel MesinViral (id+nama)
    used: dict[str, list[dict]] = {}
    try:
        chs = (sb.table("channels").select("id,channel_name,youtube_account_id")
               .eq("tenant_id", tenant_id).not_.is_("youtube_account_id", "null").execute())
        for c in (chs.data or []):
            used.setdefault(str(c["youtube_account_id"]), []).append(
                {"id": str(c["id"]), "channel_name": c.get("channel_name") or "Channel"})
    except Exception as e:
        logger.warning(f"[yt-oauth] map used_by gagal (non-fatal): {e}")
    out = []
    for r in (res.data or []):
        out.append({
            "id": r["id"], "label": r.get("label") or "YouTube",
            "connected": bool(r.get("google_refresh_token_enc")),
            "has_client": bool(r.get("google_client_id")),
            "status": r.get("status"), "yt_channel_id": r.get("yt_channel_id"),
            "yt_channel_title": r.get("yt_channel_title"),
            "yt_channel_thumb": r.get("yt_channel_thumb"),
            "used_by": used.get(str(r["id"]), []),
        })
    return {"ok": True, "accounts": out}
