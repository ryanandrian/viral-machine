"""
Loader `app_config` — business param GLOBAL admin-editable (no-hardcode, [[feedback_no_hardcode]]).

key→int (mis. trial_duration_days). Admin ubah via DB/panel → no redeploy. Cache TTL 300s,
fallback aman ke default. Untuk caps per-tier pakai `plan_limits` (bukan ini).
"""

import os
import time

from loguru import logger

_TTL = 300
_CACHE = {"data": None, "ts": 0.0}


def _load() -> None:
    if _CACHE["data"] is not None and (time.time() - _CACHE["ts"]) < _TTL:
        return
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        rows = sb.table("app_config").select("key,value,value_text").execute().data or []
        # value_text (0125) menang bila terisi — baris teks/JSON; else value (integer).
        _CACHE.update(data={r["key"]: (r.get("value_text") if r.get("value_text") is not None else r["value"])
                            for r in rows}, ts=time.time())
    except Exception as e:
        logger.warning(f"[app_config] load gagal ({e}) — pakai default")
        if _CACHE["data"] is None:
            _CACHE["data"] = {}


def get_int(key: str, default: int) -> int:
    """Nilai int business-config. Tak ada/gagal → default (fail-safe)."""
    _load()
    v = (_CACHE["data"] or {}).get(key)
    try:
        return int(v) if v is not None else int(default)
    except Exception:
        return int(default)


def get_text(key: str, default: str = "") -> str:
    """Nilai TEKS business-config (dari value_text). Kosong/tak ada → default (fail-safe)."""
    _load()
    v = (_CACHE["data"] or {}).get(key)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return default


def get_json(key: str, default=None):
    """Nilai JSON business-config (dari value_text, 0125). Tak ada/tak-valid → default (fail-safe).

    Belum ada kenop berbentuk JSON yang dipakai hari ini (diperiksa 2026-08-02) — fungsi ini
    melengkapi trio pembaca `get_int`/`get_text`/`get_json` supaya kenop JSON pertama tak perlu
    menambah jalur baca baru. Bukan sisa kode mati."""
    import json
    _load()
    v = (_CACHE["data"] or {}).get(key)
    if not isinstance(v, str) or not v.strip():
        return default
    try:
        return json.loads(v)
    except Exception:
        logger.warning(f"[app_config] {key} bukan JSON valid — pakai default")
        return default
