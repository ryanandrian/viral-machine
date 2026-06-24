"""
Vault kredensial tenant (POOL, model 2026-06-24) — TERENKRIPSI Fernet, service_role.
Arsitektur: CHANNEL_LOCK_ACTIVATION_PLAN.md.

- Kunci AI per penyedia → tabel `tenant_ai_accounts` (tenant-wide; channel pilih penyedia+model).
- Koneksi YouTube → `tenant_youtube_accounts` (di-isi oleh OAuth flow webhook_app).
- Telegram chat → `tenant_configs.telegram_chat_id`.

VALIDATE-EARLY (§0.7): saat tenant simpan kredensial → UJI NYATA → simpan status valid/invalid + validated_at.
Master key (ENCRYPTION_KEY) HANYA di server ini; tak pernah ke frontend.
"""

import os
from datetime import datetime, timezone

import httpx
from loguru import logger

from src.utils.crypto import encrypt


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Uji-nyata kunci AI per penyedia (validate-early). Tak ada entri → 'unchecked' (validasi saat produksi). ──
def _ai_test(provider_key: str, key: str):
    spec = {
        "openai":     ("GET", "https://api.openai.com/v1/models",      {"Authorization": f"Bearer {key}"}),
        "openai_tts": ("GET", "https://api.openai.com/v1/models",      {"Authorization": f"Bearer {key}"}),
        "anthropic":  ("GET", "https://api.anthropic.com/v1/models",   {"x-api-key": key, "anthropic-version": "2023-06-01"}),
        "elevenlabs": ("GET", "https://api.elevenlabs.io/v1/user",     {"xi-api-key": key}),
        "replicate":  ("GET", "https://api.replicate.com/v1/account",  {"Authorization": f"Token {key}"}),
    }.get(provider_key)
    return spec


def validate_ai_key(provider_key: str, key: str) -> str:
    """Return status: 'valid' | 'invalid' | 'unchecked'. Uji ringan (cek auth) tanpa biaya generate."""
    if not (key and key.strip()):
        return "invalid"
    spec = _ai_test(provider_key, key)
    if not spec:
        return "unchecked"   # penyedia baru tanpa test → biarkan; tervalidasi saat produksi
    method, url, headers = spec
    try:
        with httpx.Client(timeout=12) as cl:
            r = cl.request(method, url, headers=headers)
        return "valid" if r.status_code == 200 else "invalid"
    except Exception as e:
        logger.warning(f"[vault] validate_ai_key {provider_key} gagal: {e}")
        return "invalid"


def set_ai_account(tenant_id: str, provider_key: str, key: str, label: str = "") -> dict:
    """Simpan/replace kunci AI 1 penyedia ke pool (1 per penyedia, default) + UJI. Return {ok,status}."""
    if not tenant_id or not provider_key:
        raise ValueError("tenant_id & provider_key wajib")
    status = validate_ai_key(provider_key, key)
    row = {
        "tenant_id": tenant_id, "provider_key": provider_key,
        "label": (label or provider_key)[:80], "key_enc": encrypt(key.strip()),
        "status": status, "validated_at": _now(), "updated_at": _now(),
    }
    sb = _sb()
    ex = (sb.table("tenant_ai_accounts").select("id")
          .eq("tenant_id", tenant_id).eq("provider_key", provider_key).limit(1).execute())
    if ex.data:
        sb.table("tenant_ai_accounts").update(row).eq("id", ex.data[0]["id"]).execute()
    else:
        sb.table("tenant_ai_accounts").insert(row).execute()
    logger.info(f"[vault] set_ai_account tenant={tenant_id} provider={provider_key} status={status}")
    return {"ok": True, "status": status}


def list_ai_accounts(tenant_id: str) -> dict:
    """Status kunci AI per penyedia (untuk FE Credential — TIDAK kembalikan nilai kunci)."""
    if not tenant_id:
        raise ValueError("tenant_id wajib")
    r = (_sb().table("tenant_ai_accounts").select("provider_key,label,status,validated_at")
         .eq("tenant_id", tenant_id).execute())
    return {"ok": True, "accounts": r.data or []}


def validate_telegram(tenant_id: str, chat_id: str) -> dict:
    """Kirim pesan TES via bot platform → bukti chat_id benar + bot sudah di-Start. Simpan bila sukses."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"ok": False, "error": "Bot Telegram platform belum dikonfigurasi"}
    if not (chat_id and str(chat_id).strip()):
        return {"ok": False, "error": "chat_id kosong"}
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": str(chat_id).strip(),
                             "text": "✅ MesinViral: Telegram tersambung. Anda akan menerima notifikasi di sini."},
                       timeout=10)
        ok = r.status_code == 200 and (r.json() or {}).get("ok")
        if ok:
            _sb().table("tenant_configs").update(
                {"telegram_chat_id": str(chat_id).strip(), "telegram_enabled": True, "updated_at": _now()}
            ).eq("tenant_id", tenant_id).execute()
            return {"ok": True}
        err = (r.json() or {}).get("description", "gagal kirim")
        return {"ok": False, "error": f"Telegram menolak: {err} (pastikan sudah tekan Start di bot)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
