"""
PerformanceAnalyzer — Komputasi channel insights dari video_analytics.

s84c: Agregasi mingguan untuk self-learning feedback loop.
  Input  : video_analytics table (per-video metrics)
  Output : channel_insights table (aggregated patterns)

Lifecycle:
  insufficient_data (<5)  → AI estimation murni
  learning (5–20)         → Inject top topics, tidak adjust score
  optimizing (21–50)      → Full historical_factor + niche weights
  peak (50+)              → Hook pattern extraction + A/B ready
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Minimum video per niche sebelum insights dianggap valid
MIN_VIDEOS_FOR_INSIGHTS = 5


class PerformanceAnalyzer:
    """
    Compute channel_insights dari video_analytics.

    Cara pakai:
        analyzer = PerformanceAnalyzer()
        result = analyzer.compute_and_store(tenant_id="ryan_andrian")
        print(result)  # {"grade": "learning", "videos_analyzed": 12, ...}
    """

    def __init__(self):
        self._supabase = self._init_supabase()

    def _init_supabase(self):
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                return create_client(url, key)
            logger.warning("[Analyzer] SUPABASE_URL/KEY tidak ada")
            return None
        except Exception as e:
            logger.warning(f"[Analyzer] Supabase init gagal: {e}")
            return None

    # ── Public API ────────────────────────────────────────────────────────

    def compute_and_store(self, tenant_id: str, channel_id: Optional[str] = None) -> dict:
        """
        Compute insights dari video_analytics dan upsert ke channel_insights.

        Returns:
            dict: {grade, videos_analyzed, niche_weights, top_hooks_count,
                   avoid_patterns_count, content_types_analyzed}
        """
        if not self._supabase:
            logger.error("[Analyzer] Supabase tidak tersedia — abort")
            return {"grade": "error", "videos_analyzed": 0}

        channel_id = channel_id or tenant_id
        logger.info(f"[Analyzer] Computing insights | tenant={tenant_id}")

        # 1. Ambil semua video analytics yang punya data cukup
        rows = self._fetch_analytics(tenant_id)
        n = len(rows)
        logger.info(f"[Analyzer] {n} videos dengan analytics data")

        grade = self._compute_grade(n)

        if grade == "insufficient_data":
            logger.warning(
                f"[Analyzer] Hanya {n} videos — butuh min {MIN_VIDEOS_FOR_INSIGHTS}. "
                f"Simpan grade=insufficient_data"
            )
            self._upsert_insights(tenant_id, channel_id, {
                "videos_analyzed":   n,
                "grade":             "insufficient_data",
                "niche_weights":     {},
                "top_hooks":         [],
                "content_type_perf": {},
                "avoid_patterns":    [],
                "top_topics":        [],
            })
            return {"grade": grade, "videos_analyzed": n}

        # 2. Compute semua insights
        niche_weights     = self._compute_niche_weights(rows)
        top_hooks         = self._compute_top_hooks(rows)
        content_type_perf = self._compute_content_type_perf(rows)
        avoid_patterns    = self._compute_avoid_patterns(rows, content_type_perf)
        top_topics        = self._compute_top_topics(rows)

        insights = {
            "videos_analyzed":   n,
            "grade":             grade,
            "niche_weights":     niche_weights,
            "top_hooks":         top_hooks,
            "content_type_perf": content_type_perf,
            "avoid_patterns":    avoid_patterns,
            "top_topics":        top_topics,
        }

        self._upsert_insights(tenant_id, channel_id, insights)

        logger.info(
            f"[Analyzer] Done | grade={grade} | niches={len(niche_weights)} "
            f"| top_hooks={len(top_hooks)} | avoid={len(avoid_patterns)}"
        )
        return {
            "grade":                  grade,
            "videos_analyzed":        n,
            "niche_weights":          niche_weights,
            "top_hooks_count":        len(top_hooks),
            "avoid_patterns_count":   len(avoid_patterns),
            "content_types_analyzed": len(content_type_perf),
        }

    # ── Data fetching ─────────────────────────────────────────────────────

    def _fetch_analytics(self, tenant_id: str) -> list:
        """Ambil semua rows dari video_analytics yang sudah punya views > 0."""
        try:
            result = (
                self._supabase
                .table("video_analytics")
                .select(
                    "video_id, niche, content_type, hook_text, title, "
                    "views, watch_time_mins, avg_view_pct, ctr, "
                    "likes, comments, subscriber_gain, published_at"
                )
                .eq("tenant_id", tenant_id)
                .gt("views", 0)
                .order("published_at", desc=True)
                .limit(200)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning(f"[Analyzer] Fetch analytics gagal: {e}")
            return []

    # ── Grade computation ─────────────────────────────────────────────────

    def _compute_grade(self, n: int) -> str:
        if n < MIN_VIDEOS_FOR_INSIGHTS:
            return "insufficient_data"
        elif n < 21:
            return "learning"
        elif n < 51:
            return "optimizing"
        else:
            return "peak"

    # ── Insight computations ──────────────────────────────────────────────

    def _compute_niche_weights(self, rows: list) -> dict:
        """
        Hitung weight per niche berdasarkan subscriber_gain.
        Niche yang lebih banyak convert ke subscriber dapat weight lebih tinggi.
        Fallback ke views jika subscriber_gain semua 0.
        """
        niche_subs = {}
        niche_views = {}

        for row in rows:
            niche = row.get("niche") or "unknown"
            niche_subs[niche]  = niche_subs.get(niche, 0)  + (row.get("subscriber_gain") or 0)
            niche_views[niche] = niche_views.get(niche, 0) + (row.get("views") or 0)

        # Gunakan subscriber_gain jika ada data, fallback ke views
        total_subs = sum(niche_subs.values())
        if total_subs > 0:
            raw = {n: v / total_subs for n, v in niche_subs.items()}
        else:
            total_views = sum(niche_views.values())
            if total_views == 0:
                return {}
            raw = {n: v / total_views for n, v in niche_views.items()}

        # Round dan sort descending
        weights = {k: round(v, 3) for k, v in sorted(raw.items(), key=lambda x: -x[1])}
        logger.debug(f"[Analyzer] Niche weights: {weights}")
        return weights

    def _compute_top_hooks(self, rows: list, top_n: int = 10) -> list:
        """
        Ambil top hooks berdasarkan CTR, dengan fallback ke views jika CTR semua 0.
        Ekstrak pola dari hook text.
        """
        hooks_data = []
        for row in rows:
            hook = (row.get("hook_text") or "").strip()
            if not hook:
                continue
            hooks_data.append({
                "hook":             hook,
                "ctr":              row.get("ctr") or 0.0,
                "views":            row.get("views") or 0,
                "avg_view_pct":     row.get("avg_view_pct") or 0.0,
                "subscriber_gain":  row.get("subscriber_gain") or 0,
            })

        if not hooks_data:
            return []

        # Sort by CTR desc, fallback ke views
        has_ctr = any(h["ctr"] > 0 for h in hooks_data)
        if has_ctr:
            hooks_data.sort(key=lambda x: x["ctr"], reverse=True)
        else:
            hooks_data.sort(key=lambda x: x["views"], reverse=True)

        top = hooks_data[:top_n]

        # Tambah extracted pattern untuk tiap hook
        for item in top:
            item["pattern"] = self._extract_hook_pattern(item["hook"])

        return top

    def _extract_hook_pattern(self, hook: str) -> str:
        """
        Ekstrak pola structural dari hook text.
        Contoh: "The object NASA found that defies physics"
               → "[Entity] [authority] found that [defies] [domain]"
        """
        hook_lower = hook.lower()

        # Pola berdasarkan trigger words
        if re.search(r"\b(defies?|challenges?|breaks?|violates?)\b", hook_lower):
            return "entity_defies_authority"
        if re.search(r"\b(never told|never knew|don.t know|doesn.t know)\b", hook_lower):
            return "hidden_knowledge"
        if re.search(r"\b(nasa|scientists?|researchers?|experts?)\b.*\b(found|discovered|revealed)\b", hook_lower):
            return "authority_discovery"
        if re.search(r"\b(why|how|what)\b.{0,30}\b(actually|really|truly)\b", hook_lower):
            return "reframe_assumption"
        if re.search(r"\b(most|more than|over \d+|killed more)\b", hook_lower):
            return "superlative_claim"
        if re.search(r"^\d+\b", hook_lower):
            return "listicle"
        if "?" in hook:
            return "question"

        return "statement"

    def _compute_content_type_perf(self, rows: list) -> dict:
        """
        Agregasi avg_view_pct dan views per content_type.
        Content type di-infer dari niche jika kolom content_type kosong.
        """
        ct_data: dict = {}

        for row in rows:
            ct = row.get("content_type") or self._infer_content_type(
                row.get("hook_text", ""), row.get("niche", "")
            )
            avg_view = row.get("avg_view_pct") or 0.0
            views    = row.get("views") or 0

            if ct not in ct_data:
                ct_data[ct] = {"total_avg_view": 0.0, "total_views": 0, "count": 0}

            ct_data[ct]["total_avg_view"] += avg_view
            ct_data[ct]["total_views"]    += views
            ct_data[ct]["count"]          += 1

        result = {}
        for ct, d in ct_data.items():
            count        = d["count"]
            avg_view_pct = round(d["total_avg_view"] / count, 1) if count else 0.0
            result[ct] = {
                "avg_view_pct":      avg_view_pct,
                "avg_views":         round(d["total_views"] / count),
                "count":             count,
                "has_retention_data": avg_view_pct > 0,
            }

        logger.debug(f"[Analyzer] Content type perf: {result}")
        return result

    def _infer_content_type(self, hook: str, niche: str) -> str:
        """Infer content type dari hook text jika kolom content_type kosong."""
        hook_lower = (hook or "").lower()
        if re.search(r"^\d+\b|\b\d+ (things?|facts?|ways?|reasons?)\b", hook_lower):
            return "listicle"
        if "?" in hook:
            return "question"
        if re.search(r"\b(mystery|secret|hidden|unknown|forgotten)\b", hook_lower):
            return "mystery"
        if re.search(r"\b(history|historical|ancient|war|crime|murder)\b", hook_lower):
            return "history"
        if re.search(r"\b(fact|facts|did you know|actually)\b", hook_lower):
            return "facts"
        # Fallback ke niche
        return niche or "unknown"

    def _compute_avoid_patterns(self, rows: list, content_type_perf: dict) -> list:
        """
        Tentukan pattern/keyword yang harus dihindari berdasarkan avg_view_pct.
        HANYA dijalankan jika ada data full analytics (has_full_analytics=True).
        Jika semua avg_view_pct=0 (basic stats only) → return [] agar tidak salah penalize.
        """
        # Guard: pastikan ada data avg_view_pct yang nyata sebelum compute avoid
        rows_with_retention = [r for r in rows if (r.get("avg_view_pct") or 0) > 0]
        if not rows_with_retention:
            logger.info(
                "[Analyzer] avg_view_pct semua 0 (basic stats only) — "
                "skip avoid patterns. Aktifkan yt-analytics scope untuk full insights."
            )
            return []

        avoid = []

        # Content types dengan retention buruk (hanya dari rows dengan data nyata)
        for ct, perf in content_type_perf.items():
            if perf["count"] >= 3 and perf["avg_view_pct"] < 40.0:
                avoid.append(ct)
                logger.debug(
                    f"[Analyzer] Avoid content type '{ct}': "
                    f"avg_view={perf['avg_view_pct']}% count={perf['count']}"
                )

        # Hook patterns dengan performa buruk
        hook_pattern_perf: dict = {}
        for row in rows_with_retention:
            hook    = row.get("hook_text", "")
            pattern = self._extract_hook_pattern(hook)
            avg_v   = row.get("avg_view_pct") or 0.0

            if pattern not in hook_pattern_perf:
                hook_pattern_perf[pattern] = {"total": 0.0, "count": 0}
            hook_pattern_perf[pattern]["total"] += avg_v
            hook_pattern_perf[pattern]["count"] += 1

        for pattern, d in hook_pattern_perf.items():
            if d["count"] >= 3:
                avg = d["total"] / d["count"]
                if avg < 35.0 and pattern not in avoid:
                    avoid.append(pattern)
                    logger.debug(
                        f"[Analyzer] Avoid hook pattern '{pattern}': "
                        f"avg_view={avg:.1f}% count={d['count']}"
                    )

        return avoid

    def _compute_top_topics(self, rows: list, top_n: int = 10) -> list:
        """
        Top topics berdasarkan kombinasi views + subscriber_gain.
        Composite score: views * 0.4 + subscriber_gain * 1000 * 0.6
        """
        topics = []
        for row in rows:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            views   = row.get("views") or 0
            subs    = row.get("subscriber_gain") or 0
            avg_v   = row.get("avg_view_pct") or 0.0
            score   = views * 0.4 + subs * 1000 * 0.6

            topics.append({
                "title":            title,
                "niche":            row.get("niche") or "",
                "views":            views,
                "subscriber_gain":  subs,
                "avg_view_pct":     avg_v,
                "composite_score":  round(score, 1),
                "hook_pattern":     self._extract_hook_pattern(row.get("hook_text", "")),
            })

        topics.sort(key=lambda x: x["composite_score"], reverse=True)
        return topics[:top_n]

    # ── Storage ───────────────────────────────────────────────────────────

    def _upsert_insights(self, tenant_id: str, channel_id: str, insights: dict):
        """Insert row baru ke channel_insights (keep history, tidak replace)."""
        if not self._supabase:
            return
        try:
            row = {
                "tenant_id":         tenant_id,
                "channel_id":        channel_id,
                "computed_at":       datetime.now(timezone.utc).isoformat(),
                "videos_analyzed":   insights["videos_analyzed"],
                "performance_grade": insights["grade"],
                "niche_weights":     insights["niche_weights"],
                "top_hooks":         insights["top_hooks"],
                "content_type_perf": insights["content_type_perf"],
                "avoid_patterns":    insights["avoid_patterns"],
                "top_topics":        insights["top_topics"],
            }
            self._supabase.table("channel_insights").insert(row).execute()
            logger.info(
                f"[Analyzer] Insights stored | grade={insights['grade']} "
                f"| videos={insights['videos_analyzed']}"
            )
        except Exception as e:
            logger.error(f"[Analyzer] Upsert insights gagal: {e}")

    # ── Load latest insights (dipakai NicheSelector) ──────────────────────

    def load_latest_insights(self, tenant_id: str) -> Optional[dict]:
        """
        Load insights terbaru untuk tenant.
        Dipanggil oleh NicheSelector setiap pipeline run.

        Returns None jika grade=insufficient_data atau tidak ada data.
        """
        if not self._supabase:
            return None
        try:
            result = (
                self._supabase
                .table("channel_insights")
                .select("*")
                .eq("tenant_id", tenant_id)
                .order("computed_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return None

            row = rows[0]
            grade = row.get("performance_grade", "insufficient_data")
            if grade == "insufficient_data":
                logger.debug("[Analyzer] Insights grade=insufficient_data — skip injection")
                return None

            logger.info(
                f"[Analyzer] Loaded insights | grade={grade} "
                f"| videos={row.get('videos_analyzed')} "
                f"| computed={row.get('computed_at', '')[:10]}"
            )
            return row

        except Exception as e:
            logger.warning(f"[Analyzer] Load insights gagal: {e}")
            return None


if __name__ == "__main__":
    logger.info("Testing PerformanceAnalyzer...")
    analyzer = PerformanceAnalyzer()
    result = analyzer.compute_and_store("ryan_andrian")
    print(f"\nResult: {result}")

    insights = analyzer.load_latest_insights("ryan_andrian")
    if insights:
        print(f"Grade         : {insights.get('performance_grade')}")
        print(f"Videos        : {insights.get('videos_analyzed')}")
        print(f"Niche weights : {insights.get('niche_weights')}")
        print(f"Top hooks     : {len(insights.get('top_hooks', []))} hooks")
        print(f"Avoid patterns: {insights.get('avoid_patterns')}")
    else:
        print("No actionable insights yet (insufficient data)")
