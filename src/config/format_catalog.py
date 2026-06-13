"""
Loader katalog Multi-Format — `format_profiles` + `duration_presets` (MULTI_FORMAT §3/§4).

Config-driven (admin-managed via DB). **WPS = properti FORMAT (admin), tenant tak set** —
tenant hanya pilih durasi/format; WPS dipakai internal untuk word-budget. Cache TTL ringan,
fallback aman (gagal load → default §3). Pola sama src/providers/llm/catalog.py.
"""

import os
import time
from loguru import logger

_TTL = 300
_CACHE = {"profiles": None, "presets": None, "ts": 0.0}


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _load() -> None:
    if _CACHE["profiles"] is not None and (time.time() - _CACHE["ts"]) < _TTL:
        return
    try:
        sb = _sb()
        profiles = {r["format_key"]: r for r in sb.table("format_profiles").select("*").execute().data}
        presets = {int(r["seconds"]): r for r in sb.table("duration_presets").select("*").execute().data}
        _CACHE.update(profiles=profiles, presets=presets, ts=time.time())
    except Exception as e:
        logger.warning(f"[format_catalog] load gagal ({e}) — pakai fallback default")
        if _CACHE["profiles"] is None:
            _CACHE.update(profiles={}, presets={})


def format_wps(format_key, default: float = 2.4) -> float:
    """WPS per-format (§3: viral/listicle 2.4, edukasi 2.2, motivasi 1.6). None/unknown → default."""
    if not format_key:
        return default
    _load()
    row = (_CACHE["profiles"] or {}).get(format_key)
    try:
        return float(row["default_wps"]) if row and row.get("default_wps") is not None else default
    except Exception:
        return default


def default_preset_seconds(default: int = 45):
    """Preset default platform (duration_presets.is_default) — utk seed channel baru (onboarding/UI)."""
    _load()
    for sec, row in (_CACHE["presets"] or {}).items():
        if row.get("is_default"):
            return sec
    return default


def preset_visual_beats(seconds, default: int = 6) -> int:
    """visual_beats utk preset (dipakai QC clip_count relatif — F2c)."""
    if not seconds:
        return default
    _load()
    row = (_CACHE["presets"] or {}).get(int(seconds))
    try:
        return int(row["visual_beats"]) if row and row.get("visual_beats") is not None else default
    except Exception:
        return default
