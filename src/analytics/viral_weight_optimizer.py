"""
ViralWeightOptimizer (S3-A) — bobot dimensi viral-score ADAPTIF per tenant (self-improvement).

Loop: korelasi Pearson tiap dimensi topik (`videos.topic_scores`) vs performance NYATA
(`video_analytics`) → bobot baru → di-blend dgn baseline `VIRAL_SCORE_WEIGHTS` menurut sample size
→ simpan ke `tenant_configs.viral_score_weights`. Dibaca `NicheSelector._get_blended_weights`
(gate ≥20 video). Per-TENANT (kolom di tenant_configs; reader baca per tenant_id).

Dijalankan oleh `self_learning` loop (mv-worker) — PENGGANTI cron v1 `compute_viral_weights.py`
(fosil dihapus 2026-06-28). Baseline = SATU sumber (config.VIRAL_SCORE_WEIGHTS), tanpa duplikat hardcode.
NB: `ctr` per-video tak tersedia di YouTube API (selalu 0) → performance score nyata dari
avg_view_pct + subscriber_gain + views + like_rate (degradasi jujur, bukan error).
"""

import math
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.intelligence.config import VIRAL_SCORE_WEIGHTS

# Baseline = SATU sumber kebenaran (config.py) — identik dgn yg dibaca NicheSelector.
DEFAULT_WEIGHTS = VIRAL_SCORE_WEIGHTS
DIMENSIONS      = list(DEFAULT_WEIGHTS.keys())

# Komposisi performance score (internal optimizer).
PERF_WEIGHTS = {
    "avg_view_pct":         0.30,
    "ctr":                  0.25,
    "subscriber_gain_norm": 0.25,
    "views_norm":           0.15,
    "like_rate":            0.05,
}

MIN_PAIRED    = 5    # < ini: data terlalu sedikit → skip (tak menulis)
MIN_VIDEOS    = 20   # < ini: blend = 100% baseline (selaras gate reader NicheSelector)
TARGET_VIDEOS = 50   # ≥ ini: blend = 100% computed


def _pearson(x: list, y: list) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num   = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _minmax_normalize(values: list) -> list:
    if not values:
        return values
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [50.0] * len(values)
    return [100.0 * (v - vmin) / (vmax - vmin) for v in values]


def _compute_performance_scores(rows: list) -> list:
    """performance_score 0–100 per video dari video_analytics rows (urutan = rows)."""
    views_norm = _minmax_normalize([r.get("views") or 0 for r in rows])
    subs_norm  = _minmax_normalize([r.get("subscriber_gain") or 0 for r in rows])
    scores = []
    for i, r in enumerate(rows):
        avg_view_pct = min(100.0, r.get("avg_view_pct") or 0.0)
        ctr          = min(100.0, (r.get("ctr") or 0.0) * 100)  # ctr 0–1 → %; nyatanya selalu 0 (lihat header)
        views        = max(1, r.get("views") or 1)
        like_rate    = min(100.0, ((r.get("likes") or 0) / views) * 100)
        scores.append(round(
            avg_view_pct * PERF_WEIGHTS["avg_view_pct"]
            + ctr        * PERF_WEIGHTS["ctr"]
            + subs_norm[i] * PERF_WEIGHTS["subscriber_gain_norm"]
            + views_norm[i] * PERF_WEIGHTS["views_norm"]
            + like_rate  * PERF_WEIGHTS["like_rate"], 2))
    return scores


def _compute_weights(dim_scores: dict, perf_scores: list) -> tuple:
    """Pearson tiap dimensi vs performance → bobot (korelasi positif; min 5% agar tak hilang; sum=1.0)."""
    correlations = {}
    for dim in DIMENSIONS:
        x = dim_scores.get(dim, [])
        correlations[dim] = round(_pearson(x, perf_scores), 4) if len(x) == len(perf_scores) else 0.0
    MIN_WEIGHT = 0.05
    raw   = {dim: max(MIN_WEIGHT, corr) for dim, corr in correlations.items()}
    total = sum(raw.values())
    weights = {dim: round(v / total, 4) for dim, v in raw.items()}
    diff = round(1.0 - sum(weights.values()), 4)
    if diff:
        weights[max(weights, key=weights.get)] += diff
    return weights, correlations


def _blend_weights(computed: dict, n: int) -> tuple:
    """Blend computed dgn baseline by sample size. Returns (blended, alpha)."""
    if n < MIN_VIDEOS:
        return dict(DEFAULT_WEIGHTS), 0.0
    alpha = min(1.0, (n - MIN_VIDEOS) / (TARGET_VIDEOS - MIN_VIDEOS))
    blended = {
        dim: round((1 - alpha) * DEFAULT_WEIGHTS[dim] + alpha * computed.get(dim, DEFAULT_WEIGHTS[dim]), 4)
        for dim in DIMENSIONS
    }
    diff = round(1.0 - sum(blended.values()), 4)
    if diff:
        blended[max(blended, key=blended.get)] += diff
    return blended, alpha


class ViralWeightOptimizer:
    """Hitung & simpan bobot viral-score adaptif per tenant. Fail-soft (tak pernah crash caller)."""

    def __init__(self, supabase=None):
        self._sb = supabase or self._init_supabase()

    @staticmethod
    def _init_supabase():
        import os
        try:
            from supabase import create_client
            url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
            return create_client(url, key) if url and key else None
        except Exception as e:
            logger.warning(f"[ViralWeights] Supabase init gagal: {e}")
            return None

    def compute_and_store(self, tenant_id: str) -> dict:
        """Korelasi dimensi→performa → bobot → tenant_configs.viral_score_weights. Return ringkasan."""
        if not self._sb:
            return {"tenant_id": tenant_id, "status": "no_supabase"}
        try:
            videos = (self._sb.table("videos")
                      .select("video_id, topic_scores, insights_grade")
                      .eq("tenant_id", tenant_id).eq("status", "published")
                      .not_.is_("topic_scores", "null").execute().data) or []
            videos = [v for v in videos if v.get("topic_scores")]
            if not videos:
                return {"tenant_id": tenant_id, "status": "no_topic_scores"}

            video_ids = [v["video_id"] for v in videos if v.get("video_id")]
            analytics = (self._sb.table("video_analytics")
                         .select("video_id, views, likes, ctr, avg_view_pct, subscriber_gain")
                         .in_("video_id", video_ids).execute().data) or []
            amap = {a["video_id"]: a for a in analytics}

            paired = []
            for v in videos:
                a = amap.get(v.get("video_id"))
                ts = v.get("topic_scores") or {}
                if a and all(ts.get(dim) is not None for dim in DIMENSIONS):
                    paired.append({"video": v, "analytics": a})

            n = len(paired)
            if n < MIN_PAIRED:
                return {"tenant_id": tenant_id, "status": "insufficient_data", "n": n}

            dim_scores  = {dim: [p["video"]["topic_scores"][dim] for p in paired] for dim in DIMENSIONS}
            perf_scores = _compute_performance_scores([p["analytics"] for p in paired])
            computed, correlations = _compute_weights(dim_scores, perf_scores)
            blended, alpha = _blend_weights(computed, n)

            meta = {
                "weights":         blended,
                "videos_analyzed": n,
                "alpha":           round(alpha, 4),
                "correlations":    correlations,
                "computed_at":     datetime.now(timezone.utc).date().isoformat(),
            }
            self._sb.table("tenant_configs").update(
                {"viral_score_weights": meta}).eq("tenant_id", tenant_id).execute()
            logger.info(f"[ViralWeights] tenant={tenant_id} n={n} alpha={alpha:.2f} weights={blended}")
            return {"tenant_id": tenant_id, "status": "ok", "n": n, "alpha": alpha, "weights": blended}
        except Exception as e:
            logger.warning(f"[ViralWeights] compute gagal tenant={tenant_id} (non-fatal): {e}")
            return {"tenant_id": tenant_id, "status": "error", "error": str(e)}
