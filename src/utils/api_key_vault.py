"""
Vault tulis API key AI tenant TERENKRIPSI (Fernet) ke tenant_configs.*_enc — service_role.

Owner 2026-06-15: seluruh kredensial tenant terenkripsi at-rest = nilai jual. Master key
(ENCRYPTION_KEY) HANYA di server ini (Python) — tak pernah ke frontend/Vercel (sejalan Opsi A
YouTube OAuth). Postgres tak punya master key → RPC set_tenant_config TAK lagi bisa tulis key
(migr 0044 buang param key). Jalur tulis key satu-satunya = lewat sini (webhook_app /api/keys/set).

Hanya kolom WHITELIST yang ditulis (tak pernah billing/comp). Plaintext kolom lama di-null-kan.
"""

import os
from datetime import datetime, timezone
from loguru import logger

from src.utils.crypto import encrypt

SECRET_KEYS = ("llm_api_key", "visual_api_key", "tts_api_key", "youtube_api_key")  # → *_enc (Fernet)
PASSTHROUGH = ("llm_library", "tts_provider")  # non-rahasia; pasangan key (provider/library)


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def set_api_keys(tenant_id: str, payload: dict) -> dict:
    """Enkripsi & simpan key yang ada di payload. Mengembalikan {ok, set:[kolom key]}.
    Key kosong/None diabaikan (idempoten — tak menimpa key lama dengan kosong)."""
    if not tenant_id:
        raise ValueError("tenant_id wajib")
    upd: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    set_keys = []
    for k in SECRET_KEYS:
        v = payload.get(k)
        if v and str(v).strip():
            upd[f"{k}_enc"] = encrypt(str(v).strip())
            upd[k] = None  # pastikan plaintext lama kosong
            set_keys.append(k)
    for k in PASSTHROUGH:
        v = payload.get(k)
        if v:
            upd[k] = v
    if payload.get("llm_library"):
        upd["llm_provider"] = payload["llm_library"]  # jaga flat sinkron (spt RPC)
    _sb().table("tenant_configs").update(upd).eq("tenant_id", tenant_id).execute()
    logger.info(f"[key-vault] tenant={tenant_id} set keys={set_keys}")
    return {"ok": True, "set": set_keys}


# ── F2-09: vault MULTI-akun (tenant_api_accounts) — encrypt + insert akun baru ──
ALLOWED_COMPONENTS = ("llm", "tts", "image", "video")


def add_api_account(tenant_id: str, component: str, label: str, key: str, provider: str | None = None) -> dict:
    """Tambah AKUN API ke vault (tenant_api_accounts), key TERENKRIPSI (Fernet, server-only).
    Dipakai FE pemilih akun per-channel-per-elemen (F2-09). Return {ok, id}."""
    if not tenant_id:
        raise ValueError("tenant_id wajib")
    if component not in ALLOWED_COMPONENTS:
        raise ValueError(f"component invalid: {component}")
    if not (key and str(key).strip()):
        raise ValueError("key wajib")
    row = {
        "tenant_id": tenant_id,
        "component": component,
        "provider": (str(provider).strip() or None) if provider else None,
        "label": (str(label).strip() or f"{component} key")[:80],
        "key_enc": encrypt(str(key).strip()),
        "status": "active",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    res = _sb().table("tenant_api_accounts").insert(row).execute()
    aid = (res.data or [{}])[0].get("id")
    logger.info(f"[key-vault] tenant={tenant_id} add account component={component} id={aid}")
    return {"ok": True, "id": aid}
