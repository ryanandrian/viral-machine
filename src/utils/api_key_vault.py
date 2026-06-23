"""
Vault kunci AI per-CHANNEL TERENKRIPSI (Fernet) → channels.{llm,tts,visual}_key_enc — service_role.

Model bersih (owner 2026-06-24): tiap channel wajib Penyedia + Model + Kunci per elemen
(LLM/TTS/Visual). NOL fallback. Kunci boleh sama/beda antar channel, DICATAT EKSPLISIT per channel.

Master key (ENCRYPTION_KEY) HANYA di server ini (Python) — tak pernah ke frontend. Jalur tulis/baca
kunci satu-satunya = lewat sini (webhook_app /api/channels/key & /api/channels/keys/get).
Owner: kunci TIDAK di-mask di UI (boleh copy-paste) → get_channel_keys mengembalikan plaintext
ke tenant PEMILIK channel (route authed).

(Fosil DIBUANG 2026-06-24: set_api_keys→tenant_configs.*_enc & add_api_account→tenant_api_accounts —
diganti kunci inline per-channel.)
"""

import os
from datetime import datetime, timezone
from loguru import logger

from src.utils.crypto import encrypt, decrypt

# elemen AI → kolom kunci di channels (Fernet)
_CHANNEL_KEY_COL = {"llm": "llm_key_enc", "tts": "tts_key_enc", "visual": "visual_key_enc"}


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def set_channel_key(tenant_id: str, channel_id: str, element: str, key: str) -> dict:
    """Enkripsi & simpan kunci 1 elemen (llm/tts/visual) ke channels.<element>_key_enc (Fernet).
    key kosong → kosongkan kolom (hapus kunci). RLS-aman: filter tenant_id + channel id."""
    if not tenant_id or not channel_id:
        raise ValueError("tenant_id & channel_id wajib")
    col = _CHANNEL_KEY_COL.get(element)
    if not col:
        raise ValueError(f"element invalid: {element} (harus llm/tts/visual)")
    val = encrypt(str(key).strip()) if (key and str(key).strip()) else None
    _sb().table("channels").update(
        {col: val, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", channel_id).eq("tenant_id", tenant_id).execute()
    logger.info(f"[key-vault] channel={channel_id} {element}: {'set' if val else 'cleared'}")
    return {"ok": True, "element": element, "set": bool(val)}


def get_channel_keys(tenant_id: str, channel_id: str) -> dict:
    """Dekripsi kunci per-elemen channel untuk DITAMPILKAN (owner: kunci tak di-mask → copy-paste).
    Hanya tenant pemilik channel (dipanggil via route authed). Return {ok, keys:{llm,tts,visual}}."""
    if not tenant_id or not channel_id:
        raise ValueError("tenant_id & channel_id wajib")
    r = (_sb().table("channels").select("llm_key_enc,tts_key_enc,visual_key_enc")
         .eq("id", channel_id).eq("tenant_id", tenant_id).limit(1).execute())
    row = (r.data or [None])[0] or {}
    out = {}
    for el, col in _CHANNEL_KEY_COL.items():
        enc = row.get(col)
        try:
            out[el] = decrypt(enc) if enc else ""
        except Exception:
            out[el] = ""
    return {"ok": True, "keys": out}
