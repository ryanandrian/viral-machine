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
        rows = sb.table("app_config").select("key,value").execute().data or []
        _CACHE.update(data={r["key"]: r["value"] for r in rows}, ts=time.time())
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
