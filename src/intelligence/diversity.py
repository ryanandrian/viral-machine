"""
Diversity Engine (Phase 6.2, 🥇 CORE MOAT — AI Slop Defense §9.1).

Rotasi algoritmik PER-CHANNEL untuk hindari "output seragam" (risiko demonetisasi
YouTube AI-policy 2026): voice / hook-pattern / music-mood / visual-seed. Melengkapi
niche diversity guard yang SUDAH ADA (`schedule_manager._apply_diversity_guard`).

Pola = LRU lookback (cermin niche-guard): pilih kandidat yang paling LAMA tak dipakai
di N produksi terakhir channel (`videos` dimensi tracking, migrasi 0018). Config-driven
(`diversity_config`: lookback + toggle per-dimensi). FAIL-SOFT: tanpa channel_id / data /
toggle off / 1 kandidat → kembalikan kandidat pertama (= perilaku sekarang, non-breaking).
Quality tetap dijaga di hulu (ScriptAnalyzer/skor hook) — diversity = nudge, bukan override.
"""

import os
import random

from loguru import logger

from src.config.format_catalog import diversity_config

# dimensi → kolom tracking di `videos` (0018). 'niche' = kolom videos.niche → rotasi niche random
# (decisions_niche_model: random = putar SELURUH entitlement) via mekanisme yang sama dgn dimensi lain.
# Catatan: bergantung videos.channel_id terisi (lihat write_video di pipeline/publisher).
_DIM_COLUMN = {
    "voice":  "voice_id",
    "hook":   "hook_pattern",
    "music":  "music_mood",
    "visual": "visual_seed",
    "niche":  "niche",
}


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


class DiversityEngine:
    def __init__(self, supabase=None):
        self._sb = supabase
        if self._sb is None:
            try:
                self._sb = _sb()
            except Exception:
                self._sb = None

    # ── lookback per-channel ─────────────────────────────────────────────────
    def _recent_values(self, channel_id, column, limit):
        """Nilai dimensi dari N produksi terakhir channel (terbaru duluan)."""
        if not self._sb or not channel_id:
            return []
        try:
            res = (
                self._sb.table("videos")
                .select(column)
                .eq("channel_id", channel_id)
                .order("published_at", desc=True)
                .limit(int(limit))
                .execute()
            )
            return [r[column] for r in (res.data or []) if r.get(column) is not None]
        except Exception as e:
            logger.debug(f"[Diversity] recent '{column}' ch={channel_id} gagal: {e}")
            return []

    # ── LRU pick generik (voice / hook / music) ──────────────────────────────
    def pick(self, channel_id, dimension, candidates):
        """
        Pilih nilai dari `candidates` yang paling LAMA tak dipakai (LRU) di channel.
        dimension ∈ {'voice','hook','music'}. Fail-soft → candidates[0].
        """
        candidates = [c for c in (candidates or []) if c is not None]
        if not candidates:
            return None
        cfg = diversity_config()
        if len(candidates) == 1 or not cfg.get(f"{dimension}_rotation_enabled", True):
            return candidates[0]
        column = _DIM_COLUMN.get(dimension)
        if not column:
            return candidates[0]
        recent = self._recent_values(channel_id, column, cfg.get("lookback_window") or 6)
        if not recent:
            return candidates[0]

        def lru_score(v):
            # index kemunculan TERBARU (0=baru saja, makin kecil makin buruk);
            # tak muncul sama sekali → paling prioritas (len(recent)).
            for i, r in enumerate(recent):
                if r == v:
                    return i
            return len(recent)

        chosen = max(candidates, key=lru_score)
        if chosen != candidates[0]:
            logger.info(f"[Diversity] {dimension} rotate ch={channel_id}: '{candidates[0]}' → '{chosen}'")
        return chosen

    # ── hook pool dari config (∩ kandidat yang dihasilkan) ───────────────────
    def hook_pattern_pool(self):
        cfg = diversity_config()
        return list(cfg.get("hook_pattern_pool") or [])

    def pick_hook_pattern(self, channel_id, available=None):
        """
        Sarankan hook-pattern yang LRU dari pool (∩ `available` jika diberi —
        formula yang benar-benar dihasilkan optimizer). None bila rotasi off/kosong.
        Bersifat PREFERENSI: pemanggil tetap utamakan skor (quality-first).
        """
        cfg = diversity_config()
        if not cfg.get("hook_rotation_enabled", True):
            return None
        pool = self.hook_pattern_pool()
        if available:
            pool = [p for p in pool if p in set(available)] or list(available)
        if not pool:
            return None
        return self.pick(channel_id, "hook", pool)

    # ── visual seed (vary fingerprint, hindari N terakhir) ───────────────────
    def pick_seed(self, channel_id):
        """Seed image-gen acak yang TIDAK ada di N seed terakhir channel. None bila off."""
        cfg = diversity_config()
        if not cfg.get("visual_rotation_enabled", True):
            return None
        recent = set(self._recent_values(channel_id, "visual_seed", cfg.get("lookback_window") or 6))
        for _ in range(8):
            s = random.randint(1, 2_147_483_647)
            if s not in recent:
                return s
        return random.randint(1, 2_147_483_647)
