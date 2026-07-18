"""
Uji regresi PERMANEN — [B17 §6 M2] Dua-sinyal loop (ketok K2):
nilai retensi TERSIMPAN di channel_insights = completion (cap 100); sinyal tonton-ulang
terpisah = video_retention_curves.loop_factor (M1). Hermetik (nol DB/jaringan).

Jalankan:  python -m unittest tests.test_analyzer_completion_cap

Yang dijaga:
  A. _compute_top_hooks   — avg_view_pct tersimpan ≤100 (loop 1261% → 100); urutan TETAP by views.
  B. _compute_top_topics  — avg_view_pct tersimpan ≤100; composite_score & ranking TIDAK berubah
                            (score tak memakai avg_view_pct — nol regresi ranking).
  C. _compute_avoid_patterns — SENGAJA tak diubah M2 (cap akan mengubah perilaku belajar):
                            nilai >100 tidak menciptakan avoid palsu (≥40 tetap ≥40).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.performance_analyzer import PerformanceAnalyzer  # noqa: E402


def _row(hook, title, views, avg_view_pct, subs=0, ct="mystery"):
    return {"hook_text": hook, "title": title, "views": views, "avg_view_pct": avg_view_pct,
            "subscriber_gain": subs, "ctr": 0.0, "niche": "universe_mysteries",
            "content_type": ct, "has_full_analytics": True}


class TestCompletionCap(unittest.TestCase):
    def setUp(self):
        # __init__ hanya menyiapkan klien supabase (None bila env kosong) — metode _compute_* murni.
        self.an = PerformanceAnalyzer()

    def test_top_hooks_capped_and_sorted_by_views(self):
        rows = [
            _row("Hook loop gila", "V1", views=100, avg_view_pct=1261.0),
            _row("Hook biasa",     "V2", views=900, avg_view_pct=42.4),
            _row("Hook loop wajar", "V3", views=500, avg_view_pct=102.5),
        ]
        hooks = self.an._compute_top_hooks(rows)
        by_hook = {h["hook"]: h for h in hooks}
        self.assertEqual(by_hook["Hook loop gila"]["avg_view_pct"], 100.0)   # cap
        self.assertEqual(by_hook["Hook loop wajar"]["avg_view_pct"], 100.0)  # cap
        self.assertEqual(by_hook["Hook biasa"]["avg_view_pct"], 42.4)        # utuh
        # urutan TETAP by views (ctr semua 0 → fallback views) — cap tak menyentuh ranking
        self.assertEqual([h["hook"] for h in hooks],
                         ["Hook biasa", "Hook loop wajar", "Hook loop gila"])

    def test_top_topics_capped_ranking_unchanged(self):
        rows = [
            _row("h", "Topik loop", views=100, avg_view_pct=500.0, subs=2),
            _row("h", "Topik juara subs", views=50, avg_view_pct=60.0, subs=10),
        ]
        topics = self.an._compute_top_topics(rows)
        by_title = {t["title"]: t for t in topics}
        self.assertEqual(by_title["Topik loop"]["avg_view_pct"], 100.0)
        self.assertEqual(by_title["Topik juara subs"]["avg_view_pct"], 60.0)
        # ranking by composite (views*0.4 + subs*1000*0.6) — tak tersentuh cap
        self.assertEqual(topics[0]["title"], "Topik juara subs")
        self.assertAlmostEqual(by_title["Topik loop"]["composite_score"],
                               100 * 0.4 + 2 * 1000 * 0.6, places=1)

    def test_avoid_patterns_behavior_unchanged_by_loops(self):
        # 3+ video 'history' ber-loop >100 → TIDAK di-avoid (nilai tinggi = bagus, bukan buruk)
        rows = [_row("h", f"V{i}", views=10, avg_view_pct=120.0, ct="history") for i in range(4)]
        ct_perf = self.an._compute_content_type_perf(rows)
        avoid = self.an._compute_avoid_patterns(rows, ct_perf)
        self.assertNotIn("history", avoid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
