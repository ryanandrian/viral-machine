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
_CACHE = {"profiles": None, "presets": None, "tts": None, "branding": None, "diversity": None, "ts": 0.0}
_BRANDING_DEFAULTS = {"logo_max_w_px": 220, "logo_min_w_px": 96, "logo_max_h_px": 220,
                      "logo_min_h_px": 48, "logo_margin_px": 28, "logo_default_opacity": 0.85}
_DIVERSITY_DEFAULTS = {"lookback_window": 6, "voice_rotation_enabled": True,
                       "hook_rotation_enabled": True, "music_rotation_enabled": True,
                       "visual_rotation_enabled": True,
                       "hook_pattern_pool": ["question", "impossible_claim", "you_dont_know",
                                             "number_shock", "story_open"]}


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
        drow = sb.table("diversity_config").select("*").eq("id", 1).execute().data or []
        _CACHE.update(profiles=profiles, presets=presets, tts=tts,
                      branding=(brow[0] if brow else {}),
                      diversity=(drow[0] if drow else {}), ts=time.time())
    except Exception as e:
        logger.warning(f"[format_catalog] load gagal ({e}) — pakai fallback default")
        if _CACHE["profiles"] is None:
            _CACHE.update(profiles={}, presets={}, tts={}, branding={}, diversity={})


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


def preset_beats(seconds) -> list | None:
    """Urutan beat (SEGMENTASI) per preset = SINGLE-SOURCE dari `duration_presets.beats` (jsonb) —
    dibaca mesin + panel tenant + panel admin agar konsisten (anti-drift). None bila kolom belum ada
    / kosong → caller fallback ke _BEATS_FOR_N (non-breaking sebelum migrasi)."""
    if not seconds:
        return None
    _load()
    row = (_CACHE["presets"] or {}).get(int(seconds))
    b = row.get("beats") if row else None
    return list(b) if isinstance(b, list) and b else None


def preset_render_mode(seconds, default=None):
    """render_mode preset ('image_seq'|'ai_video') dari duration_presets — [B6] F2: dipakai gerbang
    koherensi STEP 0 (preset ai_video ⇄ visual_mode ai_video:*) + cabang prompt STEP 4.5."""
    if not seconds:
        return default
    _load()
    row = (_CACHE["presets"] or {}).get(int(seconds))
    return (row.get("render_mode") if row else None) or default


def preset_trailing_override(seconds):
    """[B6] F1 (migr 0161): jeda-akhir KHUSUS preset (detik) — None bila admin tak mengisi."""
    if not seconds:
        return None
    _load()
    row = (_CACHE["presets"] or {}).get(int(seconds))
    v = row.get("trailing_silence_override") if row else None
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def effective_trailing(seconds, fallback: float) -> float:
    """Jeda-akhir EFEKTIF = override preset (bila ada) else setelan channel/tenant. SATU rumus utk
    ketiga pemakai (script_engine budget · pipeline gerbang durasi · renderer) — anti-drift."""
    o = preset_trailing_override(seconds)
    return o if o is not None else float(fallback)


def effective_overhead(seconds, run_config, trailing_fallback: float = 2.5) -> float:
    """[DURASI-F4] Overhead render TOTAL (detik non-suara di video final) = trailing efektif
    (override preset > setelan tenant) + loop-ending BERSIH (loop_duration − 0.5 xfade, bila enabled —
    identik `_add_loop_ending` renderer: new = main + loop − 0.5).
    SATU rumus utk EMPAT pemakai: naskah (script_engine budget) · korektor atempo (pipeline STEP 5) ·
    gerbang durasi pra-visual · window `_fit_duration`. Kelanjutan DURASI-3: dulu hanya TRAILING yang
    disatukan; komponen LOOP terlewat di korektor+gerbang → korektor bisa meregang audio yang sudah
    benar (terparah di preset 8s: ±12%). `run_config` None → trailing saja (fail-safe, tanpa loop)."""
    trail = effective_trailing(seconds, float(getattr(run_config, "trailing_silence", trailing_fallback) or trailing_fallback) if run_config else trailing_fallback)
    loopn = 0.0
    if run_config is not None and getattr(run_config, "loop_ending_enabled", True):
        try:
            loopn = max(0.0, float(getattr(run_config, "loop_ending_duration", 1.5) or 1.5) - 0.5)
        except (TypeError, ValueError):
            loopn = 0.0
    return max(0.0, trail + loopn)


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


def diversity_config() -> dict:
    """Config Diversity Engine (Phase 6.2, §9.1) = PLATFORM (admin, DB single-row).
    lookback + toggle per-dimensi + hook_pattern_pool. Fallback default bila tabel/baris tak ada."""
    _load()
    out = dict(_DIVERSITY_DEFAULTS)
    d = _CACHE.get("diversity") or {}
    for k in _DIVERSITY_DEFAULTS:
        if d.get(k) is not None:
            out[k] = d[k]
    return out


def tts_speed_param(tts_provider):
    """Nama knob speed utk closed-loop ('speed'/'rate'/None). None → provider tak bisa speed-adjust (§0)."""
    if not tts_provider:
        return None
    _load()
    tp = (_CACHE["tts"] or {}).get(tts_provider)
    return tp.get("speed_param") if tp else None


def tts_adapter(tts_provider, default=None):
    """Nama PROTOKOL transport TTS (registry kode `TTS_ADAPTERS`) per provider — DB-driven
    (`tts_profiles.adapter`, migr 0080). Dipakai `build_tts_provider` (F5-06). None → caller fallback."""
    if not tts_provider:
        return default
    _load()
    tp = (_CACHE["tts"] or {}).get(tts_provider)
    return (tp.get("adapter") if tp else None) or default


def tts_speed_range(tts_provider, default=(0.7, 1.2)):
    """Rentang PENGALI-KECEPATAN efektif per provider — GENERIK (dari `param_schema`/`speed_param`, DB).
    Dipakai gate durasi §10.A untuk clamp speed lintas-provider (BUKAN hardcode EL [0.7,1.2]):
      • 'speed' → param_schema['speed']  (EL [0.7,1.2] · openai [0.25,4.0])
      • 'rate'  → 1 + rate%/100          (edge [-50,100]% → pengali [0.5,2.0])
      • None    → (1.0,1.0)              (provider tak bisa speed-adjust)
    Provider tak dikenal → default. Caller boleh meng-intersect dgn comfort-band mutu suara."""
    if not tts_provider:
        return default
    _load()
    tp = (_CACHE["tts"] or {}).get(tts_provider)
    if not tp:
        return default
    sp = tp.get("speed_param")
    sch = tp.get("param_schema") or {}
    try:
        rng = sch.get("speed") if sp == "speed" else None
        if sp == "speed" and isinstance(rng, (list, tuple)) and len(rng) == 2:
            return (float(rng[0]), float(rng[1]))
        rt = sch.get("rate") if sp == "rate" else None
        if sp == "rate" and isinstance(rt, (list, tuple)) and len(rt) == 2:
            return (1.0 + float(rt[0]) / 100.0, 1.0 + float(rt[1]) / 100.0)
        if sp is None:
            return (1.0, 1.0)
    except Exception:
        pass
    return default
