"""
compute_viral_weights.py — S3-A: Adaptive Viral Score Weight Computation

Jalankan bulanan (atau manual) per tenant:
  python scripts/compute_viral_weights.py [tenant_id]

Alur:
  1. Join videos + video_analytics per channel
  2. Hitung performance_score per video:
       avg_view_pct × 0.30 + ctr × 0.25 + subscriber_gain_norm × 0.25
       + views_norm × 0.15 + like_rate × 0.05
  3. Hitung Pearson correlation tiap dimensi vs performance_score
  4. Normalisasi jadi weights baru (sum = 1.0, min 0)
  5. Blend dengan default weights berdasarkan jumlah video (alpha)
  6. Simpan ke tenant_configs.viral_score_weights
  7. Cetak attribution report (pre-insights vs post-insights)

MIN_VIDEOS = 20  — di bawah ini tidak ada adaptasi
TARGET_VIDEOS = 50 — di atas ini weights 100% computed
"""

import os
import sys
import math
from datetime import datetime, timezone
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────

MIN_VIDEOS    = 20
TARGET_VIDEOS = 50

DEFAULT_WEIGHTS = {
    "search_volume":     0.25,
    "trend_momentum":    0.25,
    "emotional_trigger": 0.20,
    "competition_gap":   0.15,
    "evergreen_potential": 0.15,
}

DIMENSIONS = list(DEFAULT_WEIGHTS.keys())

# Performance score composition
PERF_WEIGHTS = {
    "avg_view_pct":        0.30,
    "ctr":                 0.25,
    "subscriber_gain_norm":0.25,
    "views_norm":          0.15,
    "like_rate":           0.05,
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _pearson(x: list, y: list) -> float:
    """Pearson correlation coefficient antara dua list float."""
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num    = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den_x  = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y  = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _minmax_normalize(values: list) -> list:
    """Min-max normalisasi ke 0–100."""
    if not values:
        return values
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [50.0] * len(values)
    return [100.0 * (v - vmin) / (vmax - vmin) for v in values]


def _compute_performance_scores(rows: list) -> list:
    """
    Hitung performance_score 0–100 per video dari video_analytics rows.
    Returns list float sesuai urutan rows.
    """
    views_raw = [r.get("views") or 0 for r in rows]
    subs_raw  = [r.get("subscriber_gain") or 0 for r in rows]

    views_norm = _minmax_normalize(views_raw)
    subs_norm  = _minmax_normalize(subs_raw)

    scores = []
    for i, r in enumerate(rows):
        avg_view_pct = min(100.0, r.get("avg_view_pct") or 0.0)
        ctr          = min(100.0, (r.get("ctr") or 0.0) * 100)  # ctr biasanya 0–1, konversi ke %
        likes        = r.get("likes") or 0
        views        = max(1, r.get("views") or 1)
        like_rate    = min(100.0, (likes / views) * 100)

        score = (
            avg_view_pct          * PERF_WEIGHTS["avg_view_pct"] +
            ctr                   * PERF_WEIGHTS["ctr"] +
            subs_norm[i]          * PERF_WEIGHTS["subscriber_gain_norm"] +
            views_norm[i]         * PERF_WEIGHTS["views_norm"] +
            like_rate             * PERF_WEIGHTS["like_rate"]
        )
        scores.append(round(score, 2))
    return scores


def _compute_weights(dim_scores: dict, perf_scores: list) -> dict:
    """
    Hitung Pearson correlation tiap dimensi vs performance_score.
    Normalisasi korelasi positif menjadi weights (sum = 1.0).
    Dimensi dengan korelasi negatif → weight 0 (tidak dihapus, hanya dikecilkan ke min).
    """
    correlations = {}
    for dim in DIMENSIONS:
        x = dim_scores.get(dim, [])
        if len(x) != len(perf_scores):
            correlations[dim] = 0.0
            continue
        correlations[dim] = round(_pearson(x, perf_scores), 4)

    logger.info(f"Correlations: {correlations}")

    # Hanya ambil korelasi positif sebagai bobot
    MIN_WEIGHT = 0.05  # setiap dimensi minimal 5% agar tidak hilang sepenuhnya
    raw = {dim: max(MIN_WEIGHT, corr) for dim, corr in correlations.items()}
    total = sum(raw.values())
    weights = {dim: round(v / total, 4) for dim, v in raw.items()}

    # Koreksi rounding agar tepat sum = 1.0
    diff = round(1.0 - sum(weights.values()), 4)
    if diff:
        top_dim = max(weights, key=weights.get)
        weights[top_dim] = round(weights[top_dim] + diff, 4)

    return weights, correlations


def _blend_weights(computed: dict, n: int) -> tuple:
    """
    Blend computed weights dengan default berdasarkan sample size.
    Returns (blended_weights, alpha)
    """
    if n < MIN_VIDEOS:
        return DEFAULT_WEIGHTS.copy(), 0.0

    alpha = min(1.0, (n - MIN_VIDEOS) / (TARGET_VIDEOS - MIN_VIDEOS))

    blended = {
        dim: round((1 - alpha) * DEFAULT_WEIGHTS[dim] + alpha * computed.get(dim, DEFAULT_WEIGHTS[dim]), 4)
        for dim in DIMENSIONS
    }

    # Koreksi rounding
    diff = round(1.0 - sum(blended.values()), 4)
    if diff:
        top_dim = max(blended, key=blended.get)
        blended[top_dim] = round(blended[top_dim] + diff, 4)

    return blended, alpha


# ── Main computation ────────────────────────────────────────────────────────

def compute_for_tenant(tenant_id: str, sb) -> dict:
    """
    Jalankan full weight computation untuk satu tenant.
    Returns dict hasil untuk logging/reporting.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Computing viral weights for tenant: {tenant_id}")

    # 1. Load videos dengan topic_scores dari DB
    videos_result = (
        sb.table("videos")
        .select("id, video_id, topic_scores, insights_grade, published_at")
        .eq("tenant_id", tenant_id)
        .eq("status", "published")
        .not_.is_("topic_scores", "null")
        .execute()
    )
    videos = [v for v in (videos_result.data or []) if v.get("topic_scores")]
    logger.info(f"Videos dengan topic_scores: {len(videos)}")

    if not videos:
        logger.warning("Tidak ada video dengan topic_scores — skip (perlu produksi ulang pasca s87)")
        return {"tenant_id": tenant_id, "status": "no_data"}

    # 2. Load video_analytics untuk video-video tersebut
    video_ids = [v["video_id"] for v in videos if v.get("video_id")]
    analytics_result = (
        sb.table("video_analytics")
        .select("video_id, views, likes, ctr, avg_view_pct, subscriber_gain")
        .in_("video_id", video_ids)
        .execute()
    )
    analytics_map = {a["video_id"]: a for a in (analytics_result.data or [])}
    logger.info(f"Analytics tersedia: {len(analytics_map)} dari {len(video_ids)} video")

    # 3. Gabungkan — hanya video yang punya keduanya
    paired = []
    for v in videos:
        vid   = v.get("video_id")
        analy = analytics_map.get(vid)
        if not analy:
            continue
        ts = v.get("topic_scores") or {}
        if not all(ts.get(dim) is not None for dim in DIMENSIONS):
            continue
        paired.append({"video": v, "analytics": analy})

    n = len(paired)
    logger.info(f"Paired (video + analytics): {n}")

    if n < 5:
        logger.warning(f"Data terlalu sedikit ({n} video) — minimal 5 untuk perhitungan")
        return {"tenant_id": tenant_id, "status": "insufficient_data", "n": n}

    # 4. Susun array per dimensi + hitung performance scores
    dim_scores  = {dim: [p["video"]["topic_scores"][dim] for p in paired] for dim in DIMENSIONS}
    perf_scores = _compute_performance_scores([p["analytics"] for p in paired])

    logger.info(f"Avg performance score: {sum(perf_scores)/len(perf_scores):.1f}/100")

    # 5. Hitung weights dari korelasi
    computed_weights, correlations = _compute_weights(dim_scores, perf_scores)
    blended_weights,  alpha        = _blend_weights(computed_weights, n)

    logger.info(f"Alpha (blend): {alpha:.2f} (n={n}, min={MIN_VIDEOS}, target={TARGET_VIDEOS})")
    logger.info(f"Default weights : {DEFAULT_WEIGHTS}")
    logger.info(f"Computed weights: {computed_weights}")
    logger.info(f"Blended weights : {blended_weights}")

    # 6. Simpan ke tenant_configs
    meta = {
        "weights":         blended_weights,
        "videos_analyzed": n,
        "alpha":           round(alpha, 4),
        "correlations":    correlations,
        "computed_at":     datetime.now(timezone.utc).date().isoformat(),
    }
    try:
        sb.table("tenant_configs").update(
            {"viral_score_weights": meta}
        ).eq("tenant_id", tenant_id).execute()
        logger.info(f"✅ viral_score_weights disimpan ke tenant_configs")
    except Exception as e:
        logger.error(f"Gagal simpan weights: {e}")

    # 7. Attribution report (S3-B) — pre vs post insights
    pre_insights  = [p for p in paired if not p["video"].get("insights_grade") or
                     p["video"]["insights_grade"] == "insufficient_data"]
    post_insights = [p for p in paired if p["video"].get("insights_grade") and
                     p["video"]["insights_grade"] != "insufficient_data"]

    def avg_perf(subset):
        if not subset:
            return None
        scores = _compute_performance_scores([p["analytics"] for p in subset])
        return round(sum(scores) / len(scores), 1)

    pre_avg  = avg_perf(pre_insights)
    post_avg = avg_perf(post_insights)

    logger.info(f"\n── Attribution Report ──")
    logger.info(f"  Pre-insights  ({len(pre_insights)} videos): avg score = {pre_avg or 'N/A'}")
    logger.info(f"  Post-insights ({len(post_insights)} videos): avg score = {post_avg or 'N/A'}")
    if pre_avg and post_avg:
        delta = round(post_avg - pre_avg, 1)
        sign  = "+" if delta >= 0 else ""
        logger.info(f"  Delta: {sign}{delta} ({'✅ improvement' if delta > 0 else '⚠️  no improvement yet'})")

    return {
        "tenant_id":       tenant_id,
        "status":          "ok",
        "n":               n,
        "alpha":           alpha,
        "blended_weights": blended_weights,
        "correlations":    correlations,
        "pre_avg":         pre_avg,
        "post_avg":        post_avg,
    }


def main():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL/KEY tidak tersedia")
        sb = create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase init gagal: {e}")
        sys.exit(1)

    # Tentukan tenant(s) yang diproses
    if len(sys.argv) > 1:
        tenant_ids = [sys.argv[1]]
    else:
        # Proses semua tenant aktif
        result     = sb.table("tenant_configs").select("tenant_id").execute()
        tenant_ids = [r["tenant_id"] for r in (result.data or [])]

    if not tenant_ids:
        logger.warning("Tidak ada tenant ditemukan")
        sys.exit(0)

    logger.info(f"Processing {len(tenant_ids)} tenant(s): {tenant_ids}")

    results = []
    for tid in tenant_ids:
        try:
            res = compute_for_tenant(tid, sb)
            results.append(res)
        except Exception as e:
            logger.error(f"Error untuk tenant {tid}: {e}")
            results.append({"tenant_id": tid, "status": "error", "error": str(e)})

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    for r in results:
        status = r.get("status")
        alpha  = r.get("alpha", 0)
        n      = r.get("n", 0)
        pre    = r.get("pre_avg", "-")
        post   = r.get("post_avg", "-")
        logger.info(
            f"  {r['tenant_id']}: {status} | n={n} | α={alpha:.2f} | "
            f"perf pre={pre} → post={post}"
        )


if __name__ == "__main__":
    main()
