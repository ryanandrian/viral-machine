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
_CACHE = {"profiles": None, "presets": None, "tts": None, "branding": None, "ts": 0.0}
_BRANDING_DEFAULTS = {"logo_max_w_px": 220, "logo_min_w_px": 96, "logo_max_h_px": 220,
                      "logo_min_h_px": 48, "logo_margin_px": 28, "logo_default_opacity": 0.85}


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
        tts = {r["provider_key"]: r for r in sb.table("tts_profiles").select("*").execute().data}
        brow = sb.table("branding_config").select("*").eq("id", 1).execute().data or []
        _CACHE.update(profiles=profiles, presets=presets, tts=tts,
                      branding=(brow[0] if brow else {}), ts=time.time())
    except Exception as e:
        logger.warning(f"[format_catalog] load gagal ({e}) — pakai fallback default")
        if _CACHE["profiles"] is None:
            _CACHE.update(profiles={}, presets={}, tts={}, branding={})


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


def effective_wps(format_key, tts_provider, default: float = 2.4) -> float:
    """WPS efektif untuk word-budget = **delivery rate TTS provider** (dominan; kata/detik suara).
    Inilah solusi 2-kelas TTS (owner): ElevenLabs-class ~1.8 vs edge ~2.6. Fallback ke WPS
    format (§3) bila provider tak ada di tts_profiles, lalu default. Calibrate delivery_wps via data."""
    if tts_provider:
        _load()
        tp = (_CACHE["tts"] or {}).get(tts_provider)
        try:
            if tp and tp.get("delivery_wps") is not None:
                return float(tp["delivery_wps"])
        except Exception:
            pass
    return format_wps(format_key, default)


def tts_class(tts_provider, default: str = "timed") -> str:
    """Kelas TTS provider: 'timed' (word-timeframe, default) | 'fast_fallback' (edge)."""
    if not tts_provider:
        return default
    _load()
    tp = (_CACHE["tts"] or {}).get(tts_provider)
    return (tp.get("tts_class") if tp else None) or default


def branding_config() -> dict:
    """Bounds UKURAN logo + margin + opacity = PLATFORM (admin, DB). Tenant ikut (tak set ukuran).
    Fallback default bila tabel/baris tak ada. Koordinat overlay diturunkan dari sini + posisi tenant."""
    _load()
    out = dict(_BRANDING_DEFAULTS)
    b = _CACHE.get("branding") or {}
    for k in _BRANDING_DEFAULTS:
        if b.get(k) is not None:
            out[k] = b[k]
    return out


def tts_speed_param(tts_provider):
    """Nama knob speed utk closed-loop ('speed'/'rate'/None). None → provider tak bisa speed-adjust (§0)."""
    if not tts_provider:
        return None
    _load()
    tp = (_CACHE["tts"] or {}).get(tts_provider)
    return tp.get("speed_param") if tp else None
