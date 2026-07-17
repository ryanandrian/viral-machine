"""
[TG-LINK] "Hubungkan Telegram" 1-klik — token deep-link (ketok owner 2026-07-16).

Masalah yang dijawab: tenant kesulitan menemukan chat-ID Telegram (keluhan owner). Solусi standar
industri: tombol di /integrations membuka `t.me/<bot>?start=<token>`; saat tenant menekan START,
bot menerima token → mesin mencatat chat_id ke tenant yang benar OTOMATIS. Tenant tak pernah
melihat/menyalin angka apa pun.

DESAIN TOKEN (stateless — nol tabel/migrasi):
  format : hex32(tenant_uuid) + "_" + base36(exp_epoch) + "_" + hmac16
  charset: [0-9a-z_] ✓ batas resmi payload start Telegram (≤64 char, A-Za-z0-9_-) — total 57.
  kunci  : HMAC-SHA256, key = sha256(SUPABASE_KEY + "|tg-link") — SUPABASE_KEY (service-role) sudah
           ada di env worker & webhook (SATU proses bahasa: semua logika token di Python; FE hanya proxy).
  TTL    : env TELEGRAM_LINK_TTL_MIN (default 15 menit).
KEAMANAN (jujur): siapa pun yang membuka link SEBELUM kedaluwarsa bisa mengikat chat-nya ke tenant itu
(menerima notifikasinya). Mitigasi: token hanya diterbitkan dalam sesi login tenant (route authed),
TTL pendek, dan setiap pengikatan dibalas konfirmasi di Telegram + terlihat di layar Integrasi.

Bot username: dari getMe (cache proses) — NO-HARDCODE nama bot; gagal → error jujur.
"""

import base64
import hashlib
import hmac
import os
import time

from loguru import logger

_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _key() -> bytes:
    sk = os.getenv("SUPABASE_KEY", "")
    if not sk:
        raise RuntimeError("SUPABASE_KEY tidak di-set — token link Telegram tak bisa dibuat/diverifikasi.")
    return hashlib.sha256((sk + "|tg-link").encode()).digest()


def _b36(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n, 36)
        s = _B36[r] + s
    return s or "0"


def _b36_dec(s: str) -> int:
    n = 0
    for c in s:
        n = n * 36 + _B36.index(c)
    return n


def _sign(payload: str) -> str:
    return hmac.new(_key(), payload.encode(), hashlib.sha256).hexdigest()[:16]


def make_link_token(tenant_id: str) -> str:
    """Token deep-link utk tenant (TTL env TELEGRAM_LINK_TTL_MIN, default 15 mnt)."""
    hex32 = tenant_id.replace("-", "").lower()
    if len(hex32) != 32:
        raise ValueError("tenant_id bukan UUID valid")
    ttl_min = int(os.getenv("TELEGRAM_LINK_TTL_MIN", "15"))
    exp = _b36(int(time.time()) + ttl_min * 60)
    payload = f"{hex32}_{exp}"
    return f"{payload}_{_sign(payload)}"


def verify_link_token(token: str):
    """Return (tenant_id, None) bila sah; (None, alasan) bila tidak. TIDAK melempar (dipakai di loop bot)."""
    try:
        hex32, exp36, sig = token.strip().split("_")
        payload = f"{hex32}_{exp36}"
        if not hmac.compare_digest(_sign(payload), sig):
            return None, "invalid_signature"
        if _b36_dec(exp36) < int(time.time()):
            return None, "expired"
        if len(hex32) != 32:
            return None, "bad_tenant"
        tid = f"{hex32[0:8]}-{hex32[8:12]}-{hex32[12:16]}-{hex32[16:20]}-{hex32[20:32]}"
        return tid, None
    except Exception:
        return None, "malformed"


_BOT_USERNAME = {"v": None}


def bot_username() -> str:
    """Username bot dari getMe (cache proses) — no-hardcode. Gagal → RuntimeError (jujur)."""
    if _BOT_USERNAME["v"]:
        return _BOT_USERNAME["v"]
    import json
    import urllib.request
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not tok:
        raise RuntimeError("TELEGRAM_BOT_TOKEN tidak di-set.")
    d = json.loads(urllib.request.urlopen(
        f"https://api.telegram.org/bot{tok}/getMe", timeout=20).read())
    u = (d.get("result") or {}).get("username")
    if not u:
        raise RuntimeError(f"getMe tanpa username: {str(d)[:120]}")
    _BOT_USERNAME["v"] = u
    logger.info(f"[TgLink] bot username: @{u}")
    return u


# ── [B21-F4] varian AGEN (mekanisme sama persis — ketok owner 2026-07-17) ─────────────────────
# Token agen = "ag" + hex32(agent_uuid) → panjang bagian-1 = 34 (tenant = 32) → kompatibel-mundur:
# verify_link_token lama tetap menolak token agen ("bad_tenant"), verifier baru membedakan kind.

def make_link_token_agent(agent_id: str) -> str:
    """Token deep-link utk AGEN (TTL sama dgn tenant)."""
    hex32 = agent_id.replace("-", "").lower()
    if len(hex32) != 32:
        raise ValueError("agent_id bukan UUID valid")
    ttl_min = int(os.getenv("TELEGRAM_LINK_TTL_MIN", "15"))
    exp = _b36(int(time.time()) + ttl_min * 60)
    payload = f"ag{hex32}_{exp}"
    return f"{payload}_{_sign(payload)}"


def verify_link_token_any(token: str):
    """Return (kind, principal_id, None) — kind 'tenant'|'agent' — atau (None, None, alasan)."""
    try:
        part1, exp36, sig = token.strip().split("_")
        payload = f"{part1}_{exp36}"
        if not hmac.compare_digest(_sign(payload), sig):
            return None, None, "invalid_signature"
        if _b36_dec(exp36) < int(time.time()):
            return None, None, "expired"
        if part1.startswith("ag") and len(part1) == 34:
            kind, hex32 = "agent", part1[2:]
        elif len(part1) == 32:
            kind, hex32 = "tenant", part1
        else:
            return None, None, "bad_principal"
        pid = f"{hex32[0:8]}-{hex32[8:12]}-{hex32[12:16]}-{hex32[16:20]}-{hex32[20:32]}"
        return kind, pid, None
    except Exception:
        return None, None, "malformed"
