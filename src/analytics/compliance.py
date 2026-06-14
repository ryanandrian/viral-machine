"""
Compliance Score (Phase 7, 🛡️ SURVIVAL — DESAIN §9.3 / AI Slop Defense).

Skor 0-100 per-channel dari DIVERSITY konten yang DIPRODUKSI (tabel `videos`) + status
AI-disclosure. Tujuan: deteksi dini profil "mass-produced templated content" yang dihajar
kebijakan YouTube AI-slop (Risk #1, DESAIN §11) SEBELUM channel kena demonetisasi.

5 dimensi (DESAIN §9.3):
  • niche_distribution — sebaran niche (entropy ternormalisasi; variasi = lebih aman)
  • hook_style_spread  — variasi formula hook (`videos.hook_pattern`, dari Diversity 6.2)
  • voice_diversity    — variasi voice (`videos.voice_id`); N/A bila belum ada data (voice-rotation deferred)
  • dup_freshness      — bebas duplikat slug terkini (`videos.topic_slug`)
  • ai_disclosure      — `channels.ai_disclosure` ON (6.3)

Dimensi tanpa data → score None (DIKECUALIKAN dari overall) — jujur, tak mengarang.
Config-driven: COMPLIANCE_LOOKBACK (default 30 video), COMPLIANCE_ALERT_BELOW (default 60, §9.3).
Sumber data = `videos` (produksi), BUKAN `video_analytics` (performa) — compliance ≠ performa.
Feed widget D20 (frontend, Phase 9-10) via `channel_insights.compliance`.
"""

import os
import math
from collections import Counter
from datetime import datetime, timezone

from loguru import logger

# Bobot dimensi (platform logic, tunable). Voice sering N/A → reweight otomatis (mean atas yang ada).
_WEIGHTS = {
    "hook_style_spread":  0.25,
    "dup_freshness":      0.25,
    "ai_disclosure":      0.20,
    "niche_distribution": 0.15,
    "voice_diversity":    0.15,
}


def _lookback() -> int:
    v = os.getenv("COMPLIANCE_LOOKBACK")
    return int(v) if v and v.isdigit() else 30


def alert_threshold() -> int:
    v = os.getenv("COMPLIANCE_ALERT_BELOW")
    return int(v) if v and v.isdigit() else 60


def _min_videos() -> int:
    """Min video produksi (channel-scoped) untuk skor compliance bermakna. <MIN → insufficient_data."""
    v = os.getenv("COMPLIANCE_MIN_VIDEOS")
    return int(v) if v and v.isdigit() else 5


def _normalized_entropy(values: list) -> float | None:
    """Entropy Shannon ternormalisasi (0-100). Variasi tinggi → 100. None bila kosong."""
    vals = [v for v in values if v]
    if not vals:
        return None
    counts = Counter(vals)
    n = len(vals)
    k = len(counts)
    if k <= 1:
        return 0.0  # seragam total → variasi nol
    H = -sum((c / n) * math.log(c / n) for c in counts.values())
    return round(100.0 * H / math.log(k), 1)  # /log(k) = normalisasi ke [0,1]


def _spread_pct(values: list, target: int) -> float | None:
    """% variasi distinct relatif ke target pool (cap 100). None bila tak ada data."""
    vals = [v for v in values if v]
    if not vals:
        return None
    distinct = len(set(vals))
    return round(min(100.0, 100.0 * distinct / max(1, min(target, len(vals)))), 1)


class ComplianceScorer:
    """Hitung Compliance Score per-channel dari produksi nyata. Fail-soft."""

    def __init__(self, supabase=None):
        self._sb = supabase
        if self._sb is None:
            try:
                from supabase import create_client
                self._sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            except Exception:
                self._sb = None

    def _recent_videos(self, channel_id: str, limit: int) -> list:
        if not self._sb or not channel_id:
            return []
        try:
            res = (
                self._sb.table("videos")
                .select("niche,hook_pattern,voice_id,topic_slug,published_at")
                .eq("channel_id", channel_id)
                .eq("status", "published")
                .order("published_at", desc=True)
                .limit(int(limit))
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[Compliance] fetch videos ch={channel_id} gagal: {e}")
            return []

    def _ai_disclosure_on(self, channel_id: str) -> bool:
        if not self._sb or not channel_id:
            return True
        try:
            res = self._sb.table("channels").select("ai_disclosure").eq("id", channel_id).limit(1).execute()
            if res.data:
                v = res.data[0].get("ai_disclosure")
                return True if v is None else bool(v)
        except Exception as e:
            logger.debug(f"[Compliance] ai_disclosure lookup gagal: {e}")
        return True

    def _dup_freshness(self, rows: list) -> float | None:
        """100 bila tak ada duplikat slug di window; turun per duplikat (anti konten berulang)."""
        slugs = [r.get("topic_slug") for r in rows if r.get("topic_slug")]
        if not slugs:
            return None
        counts = Counter(slugs)
        dups = sum(c - 1 for c in counts.values() if c > 1)  # jumlah kemunculan-ulang
        return round(max(0.0, 100.0 - (dups / len(slugs)) * 100.0), 1)

    def compute_for_channel(self, tenant_id: str, channel_id: str) -> dict:
        """
        Return {score, dimensions{dim: 0-100|None}, videos_analyzed, status, computed_at}.
        score = mean berbobot dimensi yang ADA DATANYA (None dikecualikan, bobot dinormalisasi).
        """
        rows = self._recent_videos(channel_id, _lookback())
        n = len(rows)

        dims = {
            "niche_distribution": _normalized_entropy([r.get("niche") for r in rows]),
            "hook_style_spread":  _spread_pct([r.get("hook_pattern") for r in rows], target=6),
            "voice_diversity":    _spread_pct([r.get("voice_id") for r in rows], target=5),
            "dup_freshness":      self._dup_freshness(rows),
            "ai_disclosure":      (100.0 if self._ai_disclosure_on(channel_id) else 40.0),
        }

        # Data produksi channel-scoped < MIN → JANGAN beri skor menyesatkan (mis. 100 dari ai_disclosure saja).
        if n < _min_videos():
            score, status = None, "insufficient_data"
        else:
            # overall = mean berbobot atas dimensi yang punya data (None → skip + renormalisasi bobot)
            avail = {k: v for k, v in dims.items() if v is not None}
            wsum  = sum(_WEIGHTS[k] for k in avail)
            score = round(sum(dims[k] * _WEIGHTS[k] for k in avail) / wsum, 1) if wsum else None
            status = ("at_risk" if (score is not None and score < alert_threshold())
                      else ("healthy" if score is not None else "insufficient_data"))
        result = {
            "score":           score,
            "dimensions":      dims,
            "videos_analyzed": n,
            "status":          status,
            "alert_below":     alert_threshold(),
        }
        logger.info(f"[Compliance] ch={channel_id}: score={score} status={status} n={n} dims={ {k:v for k,v in dims.items()} }")
        return result
