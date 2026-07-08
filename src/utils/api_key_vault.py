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

from src.utils.crypto import encrypt, decrypt


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Uji-nyata kunci AI per penyedia (validate-early). Tak ada entri → 'unchecked' (validasi saat produksi). ──
def _ai_test(provider_key: str, key: str):
    if provider_key == "cloudflare":
        # Kunci gabungan 'ACCOUNT_ID:API_TOKEN'. Uji = list model Workers AI — memvalidasi SEKALIGUS
        # account_id + token + izin Workers AI (validate-early). Format salah → URL/Bearer cacat → invalid.
        acct, _, tok = key.partition(":")
        base = "https://api.cloudflare.com/client/v4"
        try:
            from src.providers.llm.catalog import get_providers
            base = (((get_providers().get("cloudflare") or {}).get("base_url")) or base).rstrip("/")
        except Exception:
            pass
        return ("GET", f"{base}/accounts/{acct.strip()}/ai/models/search", {"Authorization": f"Bearer {tok.strip()}"})
    spec = {
        "openai":     ("GET", "https://api.openai.com/v1/models",      {"Authorization": f"Bearer {key}"}),
        "openai_tts": ("GET", "https://api.openai.com/v1/models",      {"Authorization": f"Bearer {key}"}),
        "anthropic":  ("GET", "https://api.anthropic.com/v1/models",   {"x-api-key": key, "anthropic-version": "2023-06-01"}),
        "elevenlabs": ("GET", "https://api.elevenlabs.io/v1/user",     {"xi-api-key": key}),
    }.get(provider_key)
    if spec:
        return spec
    # NO-HARDCODE (owner 2026-07-06, temuan status 'Tersimpan'): provider OpenAI-compatible ber-base_url
    # (Gemini/Groq/Together/dst) diuji GENERIK via GET {base_url}/models Bearer — dari katalog, bukan peta.
    try:
        from src.providers.llm.catalog import get_providers
        row = get_providers().get(provider_key) or {}
        base = (row.get("base_url") or "").rstrip("/")
        if base and (row.get("auth_type") == "api_key"):
            return ("GET", f"{base}/models", {"Authorization": f"Bearer {key}"})
    except Exception as e:
        logger.warning(f"[vault] resep uji generik {provider_key} gagal dibangun: {e}")
    return None


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
        if r.status_code == 200:
            return "valid"
        # ElevenLabs SCOPED key (terverifikasi 2026-07-06): kunci hidup & bisa TTS, tapi tak punya izin
        # user_read/voices_read → endpoint uji balas 401 "missing_permission". Itu = kunci TERDAFTAR & usable.
        if provider_key == "elevenlabs" and r.status_code == 401 and "missing_permission" in (r.text or ""):
            return "valid"
        return "invalid"
    except Exception as e:
        logger.warning(f"[vault] validate_ai_key {provider_key} gagal: {e}")
        return "invalid"


def _key_group(sb, provider_key: str) -> str:
    """Vendor key-group penyedia (openai_tts→openai). Fallback = provider_key sendiri."""
    try:
        pr = sb.table("ai_providers").select("key_group").eq("provider_key", provider_key).limit(1).execute()
        if pr.data and pr.data[0].get("key_group"):
            return pr.data[0]["key_group"]
    except Exception:
        pass
    return provider_key


def set_ai_account(tenant_id: str, provider_key: str, key: str, label: str = "", account_id: str | None = None) -> dict:
    """Simpan kunci AI ke pool (model VENDOR §0.4). account_id → EDIT baris itu; else → INSERT baru (BOLEH >1/vendor).
    key_group (vendor) diturunkan dari katalog. UJI kunci (validate-early). Return {ok,status,id}."""
    if not tenant_id or not provider_key:
        raise ValueError("tenant_id & provider_key wajib")
    status = validate_ai_key(provider_key, key)
    sb = _sb()
    row = {
        "tenant_id": tenant_id, "provider_key": provider_key, "key_group": _key_group(sb, provider_key),
        "label": (label or provider_key)[:80], "key_enc": encrypt(key.strip()),
        "status": status, "validated_at": _now(), "updated_at": _now(),
    }
    if account_id:
        sb.table("tenant_ai_accounts").update(row).eq("id", account_id).eq("tenant_id", tenant_id).execute()
        new_id = account_id
    else:
        r = sb.table("tenant_ai_accounts").insert(row).execute()
        new_id = (r.data or [{}])[0].get("id")
    logger.info(f"[vault] set_ai_account tenant={tenant_id} provider={provider_key} kg={row['key_group']} status={status} edit={account_id is not None}")
    return {"ok": True, "status": status, "id": new_id}


def delete_ai_account(tenant_id: str, account_id: str) -> dict:
    """Hapus 1 kunci AI dari pool (FE 'hapus'). channels.*_account_id → NULL otomatis (FK on delete set null)."""
    if not tenant_id or not account_id:
        raise ValueError("tenant_id & account_id wajib")
    _sb().table("tenant_ai_accounts").delete().eq("id", account_id).eq("tenant_id", tenant_id).execute()
    return {"ok": True}


def list_ai_accounts(tenant_id: str) -> dict:
    """Akun kunci AI per penyedia untuk FE Credential. TAMPIL APA ADANYA (kesepakatan owner §0.4):
    kembalikan nilai kunci ter-DECRYPT agar tenant bisa periksa/copy (bukan write-only)."""
    if not tenant_id:
        raise ValueError("tenant_id wajib")
    r = (_sb().table("tenant_ai_accounts").select("id,provider_key,key_group,label,status,validated_at,key_enc")
         .eq("tenant_id", tenant_id).order("provider_key").execute())
    out = []
    for a in (r.data or []):
        key = ""
        try:
            key = decrypt(a.get("key_enc") or "") if a.get("key_enc") else ""
        except Exception as e:
            logger.warning(f"[vault] decrypt key_enc gagal id={a.get('id')}: {e}")
        out.append({"id": a["id"], "provider_key": a["provider_key"], "key_group": a.get("key_group"),
                    "label": a.get("label"), "status": a.get("status"), "validated_at": a.get("validated_at"), "key": key})
    return {"ok": True, "accounts": out}


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
