"""
SATU SUMBER kosakata "peran adegan" (beat roles) — owner 2026-07-05 [B3/Fase2].

Sebelumnya kosakata tersebar di ~10 tempat (script_engine 6 dict, tts_engine, video_renderer,
ai_image, FE) dgn penyimpang MATI `core_facts_2`. Modul ini = titik-baca TUNGGAL untuk BE.

Sumber kebenaran = tabel DB `content_beats` (migr 0128). Dibaca via `_load()` (cache TTL, fallback
ke `_CANON` = konstanta identik lama). NON-BREAKING: DB kosong/gagal → `_CANON` → perilaku sama persis.
Kanonik = 8 peran (urutan naratif). `core_facts_2` DIBUANG (tak pernah tercapai; preset maks 7 segmen).

Pemilihan segmen per-preset TETAP di `duration_presets.beats` (subset kosakata ini) — bukan di sini.
"""

import os
import time

from loguru import logger

# Fallback kanonik — IDENTIK seed 0128 & konstanta lama (bukti derive==current).
# (key, sort, label_upper, weight, default_timing_sec, motion_index)
_CANON = [
    ("hook",              1, "HOOK",              3,  3,  0),
    ("mystery_drop",      2, "MYSTERY DROP",      5,  5,  1),
    ("build_up",          3, "BUILD-UP",          12, 12, 2),
    ("pattern_interrupt", 4, "PATTERN INTERRUPT", 2,  2,  1),
    ("core_facts",        5, "CORE FACT",         15, 15, 3),
    ("curiosity_bridge",  6, "CURIOSITY BRIDGE",  3,  3,  2),
    ("climax",            7, "CLIMAX",            8,  8,  5),
    ("cta",               8, "CTA",               3,  3,  5),
]

_TTL = 300
_CACHE = {"vocab": None, "ts": 0.0}


def _from_canon() -> list:
    return [{"beat_key": k, "sort_order": so, "label_upper": lu,
             "weight": w, "default_timing_sec": t, "motion_index": mi} for (k, so, lu, w, t, mi) in _CANON]


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
                      "motion_index": int(r["motion_index"])} for r in rows]
    except Exception as e:
        logger.debug(f"[beats] load DB gagal ({e}) — pakai fallback konstanta")
    if not vocab:
        vocab = _from_canon()
    _CACHE.update(vocab=vocab, ts=time.time())
    return vocab


# ── Accessor turunan (dipakai konsumen; menggantikan dict tersebar) ──────────────
def all_beats() -> list:
    """Daftar key peran terurut (menggantikan _ALL_SECTIONS)."""
    return [b["beat_key"] for b in _load()]


def weights() -> dict:
    """Bobot anggaran-kata per peran (menggantikan _BEAT_WEIGHT)."""
    return {b["beat_key"]: b["weight"] for b in _load()}


def timing_defaults() -> dict:
    """Durasi default per bagian (menggantikan _DEFAULT_SECTION_TIMING)."""
    return {b["beat_key"]: b["default_timing_sec"] for b in _load()}


def labels_upper() -> dict:
    """Label huruf-besar utk prompt naskah (menggantikan _ROLE_LABEL)."""
    return {b["beat_key"]: b["label_upper"] for b in _load()}


def motion_map() -> dict:
    """Peran → indeks gerak default (menggantikan _ROLE_MOTION di ai_image)."""
    return {b["beat_key"]: b["motion_index"] for b in _load()}


def beats_for_n(n: int) -> list:
    """Subset peran utk N adegan (fallback bila duration_presets.beats kosong; menggantikan _BEATS_FOR_N).
    Pola lama: 3=hook/core/cta; naik bertahap. Dibangun dari kosakata kanonik terurut, di-clamp [3, len]."""
    keys = all_beats()
    n = max(3, min(len(keys), int(n)))
    # Cetakan naratif (subset by-N) — konsisten dgn _BEATS_FOR_N lama utk 3..8.
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
