"""
SATU SUMBER kosakata "peran adegan" (beat roles) — owner 2026-07-05 [B3/Fase2].

Sumber kebenaran = tabel DB `content_beats` (migr 0128/0129). Dibaca via `_load()` (cache TTL,
fallback ke `_CANON` = konstanta identik lama). NON-BREAKING: DB kosong/gagal → `_CANON` → sama persis.
Kanonik = 8 peran. `core_facts_2` DIBUANG. Pemilihan segmen per-preset = `duration_presets.beats` (subset).

Fase 2 (0129): motion per-segmen (level system) — mode 'fix' (arah tetap) | 'cerdas' (variasi otomatis).
`resolve_motion_sequence()` menerjemahkan config → arah konkret per adegan (anti dua-adegan-searah-berturut).
"""

import os
import time

from loguru import logger

# Fallback kanonik — IDENTIK seed 0128/0129 & konstanta lama (bukti derive==current).
# (key, sort, label_upper, weight, default_timing_sec, motion_index, motion_mode, motion_dir, motion_rate)
_CANON = [
    ("hook",              1, "HOOK",              3,  3,  0, "fix", "zoom_in",  0.050),
    ("mystery_drop",      2, "MYSTERY DROP",      5,  5,  1, "fix", "zoom_out", 0.035),
    ("build_up",          3, "BUILD-UP",          12, 12, 2, "fix", "pan_diag", 0.000),
    ("pattern_interrupt", 4, "PATTERN INTERRUPT", 2,  2,  1, "fix", "zoom_out", 0.035),
    ("core_facts",        5, "CORE FACT",         15, 15, 3, "fix", "zoom_in",  0.030),
    ("curiosity_bridge",  6, "CURIOSITY BRIDGE",  3,  3,  2, "fix", "pan_diag", 0.000),
    ("climax",            7, "CLIMAX",            8,  8,  5, "fix", "zoom_out", 0.050),
    ("cta",               8, "CTA",               3,  3,  5, "fix", "zoom_out", 0.050),
]

_TTL = 300
_CACHE = {"vocab": None, "ts": 0.0}


def _from_canon() -> list:
    return [{"beat_key": k, "sort_order": so, "label_upper": lu, "weight": w, "default_timing_sec": t,
             "motion_index": mi, "motion_mode": mo, "motion_dir": md, "motion_rate": float(mr)}
            for (k, so, lu, w, t, mi, mo, md, mr) in _CANON]


def _load() -> list:
    """Kosakata beat terurut. DB `content_beats` (is_active) → fallback `_CANON`. Cache TTL, fail-safe."""
    if _CACHE["vocab"] is not None and (time.time() - _CACHE["ts"]) < _TTL:
        return _CACHE["vocab"]
    vocab = None
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        rows = (sb.table("content_beats").select("*").eq("is_active", True)
                .order("sort_order").execute().data) or []
        if rows:
            vocab = [{"beat_key": r["beat_key"], "sort_order": r["sort_order"],
                      "label_upper": r["label_upper"], "weight": int(r["weight"]),
                      "default_timing_sec": int(r["default_timing_sec"]),
                      "motion_index": int(r["motion_index"]),
                      "motion_mode": r.get("motion_mode") or "fix",
                      "motion_dir": r.get("motion_dir") or "zoom_in",
                      # JANGAN pakai `or` — motion_rate 0.0 sah (peran pan) & 0.0 falsy → bug. Cek None eksplisit.
                      "motion_rate": float(r["motion_rate"]) if r.get("motion_rate") is not None else 0.04}
                     for r in rows]
    except Exception as e:
        logger.debug(f"[beats] load DB gagal ({e}) — pakai fallback konstanta")
    if not vocab:
        vocab = _from_canon()
    _CACHE.update(vocab=vocab, ts=time.time())
    return vocab


# ── Accessor turunan ─────────────────────────────────────────────────────────────
def all_beats() -> list:
    return [b["beat_key"] for b in _load()]


def weights() -> dict:
    return {b["beat_key"]: b["weight"] for b in _load()}


def timing_defaults() -> dict:
    return {b["beat_key"]: b["default_timing_sec"] for b in _load()}


def labels_upper() -> dict:
    return {b["beat_key"]: b["label_upper"] for b in _load()}


def motion_map() -> dict:
    """Peran → indeks gerak default (kompat lama; Fase 2 pakai resolve_motion_sequence)."""
    return {b["beat_key"]: b["motion_index"] for b in _load()}


def motion_config() -> dict:
    """Peran → {mode, dir, rate} (Fase 2, level system dari content_beats)."""
    return {b["beat_key"]: {"mode": b["motion_mode"], "dir": b["motion_dir"], "rate": b["motion_rate"]}
            for b in _load()}


def beats_for_n(n: int) -> list:
    """Subset peran utk N adegan (fallback bila duration_presets.beats kosong). Identik _BEATS_FOR_N lama 3..8."""
    keys = all_beats()
    n = max(3, min(len(keys), int(n)))
    TEMPLATES = {
        3: ["hook", "core_facts", "cta"],
        4: ["hook", "build_up", "core_facts", "cta"],
        5: ["hook", "build_up", "core_facts", "climax", "cta"],
        6: ["hook", "mystery_drop", "build_up", "core_facts", "climax", "cta"],
        7: ["hook", "mystery_drop", "build_up", "core_facts", "curiosity_bridge", "climax", "cta"],
        8: ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "curiosity_bridge", "climax", "cta"],
    }
    tmpl = TEMPLATES.get(n)
    return [k for k in tmpl if k in keys] if tmpl else keys[:n]


# ── Fase 2: resolusi arah motion per adegan (fix/cerdas) ─────────────────────────
# Kandidat arah per NIAT peran utk mode 'cerdas' (hormati momen; variasikan arah). Urutan = prioritas.
_CERDAS_CANDIDATES = {
    "zoom_in":  ["zoom_in", "pan_lr", "pan_du"],       # push-in (hook/core) → tetap zoom-in, alternatif pan
    "zoom_out": ["zoom_out", "pan_ud", "pan_rl"],      # reveal (mystery/climax/cta) → zoom-out, alternatif pan
    "pan_diag": ["pan_lr", "pan_ud", "pan_rl", "pan_du", "pan_diag", "pan_diag_rev"],  # eksplorasi → rotasi penuh
}


def resolve_motion_sequence(roles: list) -> list:
    """Terjemahkan config motion → arah konkret per adegan (urut). Fase 2, level system.
      - mode 'fix'   → pakai arah tetap config (default = perilaku Fase 1 PERSIS).
      - mode 'cerdas'→ pilih arah cerdas: hormati niat peran + TAK sama dgn adegan sebelumnya (anti-monoton).
    Deterministik (berbasis posisi). Return list of {dir, rate}. Peran tak dikenal → default aman zoom_in."""
    cfg = motion_config()
    out, prev = [], None
    for i, role in enumerate(roles or []):
        c = cfg.get(role) or {"mode": "fix", "dir": "zoom_in", "rate": 0.04}
        rate = c["rate"]
        if c["mode"] == "cerdas":
            pool = _CERDAS_CANDIDATES.get(c["dir"], ["zoom_in", "zoom_out", "pan_lr"])
            rot = pool[i % len(pool):] + pool[:i % len(pool)]          # rotasi by posisi → variasi antar-adegan
            d = next((x for x in rot if x != prev), rot[0])            # anti dua-adegan-searah-berturut
        else:
            d = c["dir"]
        out.append({"dir": d, "rate": rate})
        prev = d
    return out
