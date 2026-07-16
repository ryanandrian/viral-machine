"""
[TG-LINK] Pendengar /start bot Telegram — menuntaskan "Hubungkan Telegram 1-klik" (ketok owner 2026-07-16).

Loop long-poll `getUpdates` (webhook bot TERVERIFIKASI KOSONG 2026-07-16 → polling AMAN, nol konflik).
Tugas TUNGGAL: pesan `/start <token>` → verifikasi (telegram_link.verify_link_token) → catat
`tenant_configs.telegram_chat_id` + `telegram_enabled=true` → balas konfirmasi DWIBAHASA.
Selain itu (token invalid/kedaluwarsa, /start polos, pesan lain) → balasan penuntun singkat.

Ketahanan (anti-ranjau):
  • offset PERSISTEN di app_config `ops_tg_update_offset` (kolom int `value`) → restart/deploy tidak
    memproses ulang pesan lama; PERTAMA KALI (belum ada offset) → DRAIN antrean lama TANPA ditindak
    (token basi tak boleh mengikat apa pun).
  • fail-soft total: error apa pun di satu update → log + lanjut; error loop → tidur lalu ulang.
  • idempoten: token sah utk tenant yang sama boleh dipakai ulang dlm TTL (update chat_id = aman).
"""

import json
import os
import time
import urllib.parse
import urllib.request

from loguru import logger

_OFFSET_KEY = "ops_tg_update_offset"


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _api(method: str, http_timeout: int = 35, params: dict | None = None):
    """params = parameter API Telegram (boleh berisi 'timeout' long-poll — TIDAK bentrok dgn
    http_timeout urllib; http_timeout WAJIB > long-poll timeout agar koneksi tak putus duluan)."""
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not tok:
        raise RuntimeError("TELEGRAM_BOT_TOKEN tidak di-set")
    qs = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"https://api.telegram.org/bot{tok}/{method}" + (f"?{qs}" if qs else "")
    return json.loads(urllib.request.urlopen(url, timeout=http_timeout).read())


def _send(chat_id, text: str) -> None:
    try:
        _api("sendMessage", http_timeout=20, params={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.warning(f"[TgLinker] balas gagal (non-fatal): {e}")


def _get_offset(sb):
    try:
        r = sb.table("app_config").select("value").eq("key", _OFFSET_KEY).limit(1).execute().data
        return int(r[0]["value"]) if r else None
    except Exception:
        return None


def _set_offset(sb, offset: int) -> None:
    try:
        sb.table("app_config").upsert({
            "key": _OFFSET_KEY, "value": int(offset),
            "description": "OPS (otomatis, jangan diubah manual): offset getUpdates bot Telegram (linker 1-klik)",
        }).execute()
    except Exception as e:
        logger.warning(f"[TgLinker] simpan offset gagal (non-fatal): {e}")


# Balasan dwibahasa (bot tak tahu bahasa tenant → dua bahasa ringkas, aturan §3.5).
_MSG_OK = ("✅ Terhubung! Notifikasi MesinViral untuk akun Anda kini aktif di chat ini.\n"
           "✅ Connected! MesinViral notifications for your account are now active in this chat.")
_MSG_EXPIRED = ("⏱ Tautan kedaluwarsa. Buka MesinViral → Integrasi → klik \"Hubungkan Telegram\" lagi.\n"
                "⏱ Link expired. Open MesinViral → Integrations → click \"Connect Telegram\" again.")
_MSG_INVALID = ("⚠️ Tautan tidak dikenali. Gunakan tombol \"Hubungkan Telegram\" di halaman Integrasi MesinViral.\n"
                "⚠️ Link not recognized. Use the \"Connect Telegram\" button on MesinViral's Integrations page.")
_MSG_PLAIN = ("👋 Halo! Untuk menghubungkan notifikasi: buka MesinViral → menu Integrasi → klik \"Hubungkan Telegram\".\n"
              "👋 Hi! To connect notifications: open MesinViral → Integrations → click \"Connect Telegram\".")


def _handle_update(sb, u: dict) -> None:
    msg = u.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return
    if not text.startswith("/start"):
        _send(chat_id, _MSG_PLAIN)
        return
    parts = text.split(maxsplit=1)
    if len(parts) == 1:                      # /start polos (tanpa token)
        _send(chat_id, _MSG_PLAIN)
        return
    from src.utils.telegram_link import verify_link_token
    tenant_id, reason = verify_link_token(parts[1])
    if not tenant_id:
        _send(chat_id, _MSG_EXPIRED if reason == "expired" else _MSG_INVALID)
        logger.info(f"[TgLinker] token ditolak ({reason}) chat={chat_id}")
        return
    r = (sb.table("tenant_configs")
           .update({"telegram_chat_id": str(chat_id), "telegram_enabled": True})
           .eq("tenant_id", tenant_id).execute())
    if r.data:
        _send(chat_id, _MSG_OK)
        logger.info(f"[TgLinker] ✅ terhubung: tenant={tenant_id} chat={chat_id}")
    else:                                     # tenant tak ditemukan (mis. akun terhapus) — jujur
        _send(chat_id, _MSG_INVALID)
        logger.warning(f"[TgLinker] tenant {tenant_id} tak ditemukan saat link (chat={chat_id})")


def run_once(sb) -> int:
    """Satu siklus long-poll. Return jumlah update diproses."""
    offset = _get_offset(sb)
    if offset is None:
        # PERTAMA KALI: drain antrean lama TANPA ditindak (token/pesan basi tak boleh mengikat).
        d = _api("getUpdates", http_timeout=20, params={"limit": 100})
        ups = d.get("result") or []
        offset = (ups[-1]["update_id"] + 1) if ups else 0
        _set_offset(sb, offset)
        logger.info(f"[TgLinker] init: drain {len(ups)} update lama tanpa tindak; offset={offset}")
        return 0
    d = _api("getUpdates", http_timeout=35, params={"offset": offset, "timeout": 25, "limit": 100})
    ups = d.get("result") or []
    for u in ups:
        try:
            _handle_update(sb, u)
        except Exception as e:
            logger.warning(f"[TgLinker] update {u.get('update_id')} gagal (lanjut): {e}")
    if ups:
        _set_offset(sb, ups[-1]["update_id"] + 1)
    return len(ups)


def run_forever() -> None:
    logger.info("[TgLinker] start — long-poll getUpdates (Hubungkan Telegram 1-klik)")
    sb = _sb()
    while True:
        try:
            run_once(sb)
        except Exception as e:
            logger.warning(f"[TgLinker] loop error (tidur 10s): {e}")
            time.sleep(10)
