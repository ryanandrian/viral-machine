"""
Uji regresi PERMANEN — [B17 §6 M1] Lapis 1 "Mata": kolektor kurva retensi per-momen.
Hermetik (nol DB / nol jaringan): murni logika.

Jalankan:  python -m unittest tests.test_retention_curves    (dari root repo)
       atau python tests/test_retention_curves.py

Yang dijaga (regresi bila salah satu berubah):
  A. compute_features — 4 fitur turunan benar utk kurva normal / loop>1 / pendek / kosong,
     dan relPerf parsial → rata dari yang ada saja (None bila tak ada — jujur, bukan 0 palsu).
  B. decide_action — kontrak siklus hidup per-video: maks 2 fetch seumur hidup (muda → matang
     → FINAL) · 'empty' retry ber-jeda ≥24 jam · give-up melewati umur config · timestamp
     rusak TIDAK memblokir retry.
  C. load_knobs — fail-soft ke default saat DB tumbang; nilai tak-masuk-akal (≤0/NULL) ditolak.
  D. Konstanta definisi fitur terkunci (mengubahnya = keputusan sadar → ubah uji ini).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# root repo di sys.path (agar `import src...` jalan saat dipanggil langsung)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.retention_curves import (   # noqa: E402
    EMPTY_RETRY_MIN_HOURS,
    HOOK_BUCKETS,
    KNOB_DEFAULTS,
    MID_EXIT_THRESHOLD,
    compute_features,
    decide_action,
    load_knobs,
)

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
K = dict(KNOB_DEFAULTS)  # min_age=3 · refresh=14 · max_per_run=50 · give_up=45


def _curve(values, rel=None):
    """Kurva sintetis dari daftar watchRatio; ratio = (i+1)/n."""
    n = len(values)
    return [[round((i + 1) / max(n, 1), 4), v, (rel[i] if rel else None)]
            for i, v in enumerate(values)]


# ─────────────────────────── A. compute_features ───────────────────────────
class TestComputeFeatures(unittest.TestCase):
    def test_normal_decay(self):
        vals = [1.0, 0.9, 0.8, 0.7, 0.6, 0.4, 0.3, 0.25, 0.2, 0.1]
        f = compute_features(_curve(vals, rel=[0.5] * 10))
        self.assertEqual(f["points"], 10)
        self.assertAlmostEqual(f["hook_hold"], sum(vals[:HOOK_BUCKETS]) / HOOK_BUCKETS, places=4)
        self.assertAlmostEqual(f["mid_exit"], 0.6, places=4)   # titik pertama < 0.5 = indeks-6 (ratio 0.6)
        self.assertEqual(f["loop_factor"], 0.0)                # tak ada nilai > 1
        self.assertAlmostEqual(f["end_ratio"], 0.1, places=4)
        self.assertAlmostEqual(f["rel_perf_avg"], 0.5, places=4)

    def test_looping_video(self):
        # Pola probe nyata mkY_T6aUsc8: watchRatio > 1 di paruh awal (tonton-ulang)
        vals = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.5]
        f = compute_features(_curve(vals))
        expected = sum(max(0.0, v - 1.0) for v in vals) / len(vals)
        self.assertAlmostEqual(f["loop_factor"], expected, places=4)
        self.assertIsNone(f["mid_exit"])          # 0.5 == ambang, BUKAN < ambang
        self.assertIsNone(f["rel_perf_avg"])      # relPerf absen semua → None jujur

    def test_never_drops_below_half(self):
        f = compute_features(_curve([1.0, 0.9, 0.8, 0.75, 0.7]))
        self.assertIsNone(f["mid_exit"])
        self.assertAlmostEqual(f["end_ratio"], 0.7, places=4)

    def test_short_curve_and_empty(self):
        f = compute_features(_curve([0.8, 0.6]))  # < HOOK_BUCKETS titik → rata yang ada
        self.assertAlmostEqual(f["hook_hold"], 0.7, places=4)
        self.assertEqual(f["points"], 2)
        e = compute_features([])
        self.assertEqual(e, {"hook_hold": None, "mid_exit": None, "loop_factor": None,
                             "end_ratio": None, "rel_perf_avg": None, "points": 0})

    def test_partial_rel_perf(self):
        rows = _curve([1.0, 0.8, 0.6, 0.55, 0.52])
        rows[0][2], rows[1][2] = 0.4, 0.6          # sisanya None
        f = compute_features(rows)
        self.assertAlmostEqual(f["rel_perf_avg"], 0.5, places=4)


# ─────────────────────────── B. decide_action ───────────────────────────
class TestDecideAction(unittest.TestCase):
    def test_too_young_then_first_fetch(self):
        self.assertEqual(decide_action(K["retention_curve_min_age_days"] - 1, None, K, NOW), "too_young")
        self.assertEqual(decide_action(K["retention_curve_min_age_days"], None, K, NOW), "fetch")

    def test_young_curve_waits_refreshes_once_then_final(self):
        row_young = {"status": "ok", "video_age_days": 4, "fetched_at": NOW.isoformat()}
        self.assertEqual(decide_action(10, row_young, K, NOW), "wait_refresh")
        self.assertEqual(decide_action(K["retention_curve_refresh_age_days"], row_young, K, NOW), "fetch")
        row_mature = {"status": "ok", "video_age_days": K["retention_curve_refresh_age_days"],
                      "fetched_at": NOW.isoformat()}
        self.assertEqual(decide_action(100, row_mature, K, NOW), "final")   # maks 2 fetch seumur hidup

    def test_empty_cooldown_retry_giveup(self):
        fresh = {"status": "empty", "video_age_days": 5,
                 "fetched_at": (NOW - timedelta(hours=EMPTY_RETRY_MIN_HOURS - 1)).isoformat()}
        self.assertEqual(decide_action(5, fresh, K, NOW), "cooldown")
        stale = {"status": "empty", "video_age_days": 5,
                 "fetched_at": (NOW - timedelta(hours=EMPTY_RETRY_MIN_HOURS + 1)).isoformat()}
        self.assertEqual(decide_action(6, stale, K, NOW), "fetch")
        self.assertEqual(decide_action(K["retention_curve_give_up_age_days"] + 1, stale, K, NOW), "give_up")

    def test_empty_bad_timestamp_does_not_block_retry(self):
        row = {"status": "empty", "video_age_days": 5, "fetched_at": "bukan-tanggal"}
        self.assertEqual(decide_action(6, row, K, NOW), "fetch")


# ─────────────────────────── C. load_knobs fail-soft ───────────────────────────
class _BoomTable:
    def select(self, *_a, **_k): raise RuntimeError("db down")


class _BoomSB:
    def table(self, *_a, **_k): return _BoomTable()


class _StubExec:
    def __init__(self, data): self.data = data


class _StubQuery:
    def __init__(self, data): self._d = data
    def select(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def execute(self): return _StubExec(self._d)


class _StubSB:
    def __init__(self, rows): self._rows = rows
    def table(self, _name): return _StubQuery(self._rows)


class TestLoadKnobs(unittest.TestCase):
    def test_db_down_falls_back_to_defaults(self):
        self.assertEqual(load_knobs(_BoomSB()), KNOB_DEFAULTS)

    def test_reads_values_and_rejects_invalid(self):
        rows = [
            {"key": "retention_curve_min_age_days", "value": 5},
            {"key": "retention_curve_max_per_run", "value": 0},           # ≤0 → default
            {"key": "retention_curve_refresh_age_days", "value": None},   # NULL → default
        ]
        k = load_knobs(_StubSB(rows))
        self.assertEqual(k["retention_curve_min_age_days"], 5)
        self.assertEqual(k["retention_curve_max_per_run"], KNOB_DEFAULTS["retention_curve_max_per_run"])
        self.assertEqual(k["retention_curve_refresh_age_days"], KNOB_DEFAULTS["retention_curve_refresh_age_days"])


# ─────────────────────────── D. konstanta definisi terkunci ───────────────────────────
class TestFeatureDefinitionConstants(unittest.TestCase):
    def test_locked(self):
        self.assertEqual(HOOK_BUCKETS, 5)
        self.assertEqual(MID_EXIT_THRESHOLD, 0.5)
        self.assertEqual(EMPTY_RETRY_MIN_HOURS, 24)


if __name__ == "__main__":
    unittest.main(verbosity=2)
