"""
Uji regresi PERMANEN — [B17 §6 A1] Otak Analis (mode bayangan). Hermetik (nol DB/LLM/jaringan).

Jalankan:  python -m unittest tests.test_channel_analyst

Yang dijaga:
  A. validate_decisions — menu TERTUTUP ditegakkan: type liar/di-luar-batas/DITOLAK;
     niche_mix & focus_recommendation HARAM utk channel fixed; prediksi terukur WAJIB
     (tanpa prediksi = hakim A2 tak bisa mengadili = fake-smart).
  B. is_due — siklus interval; tanpa riwayat = due; timestamp rusak tak memblokir.
  C. clean_json_response — pagar markdown ```json dibuang.
  D. Konstanta batas menu terkunci (ubah = keputusan sadar → ubah uji ini).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.channel_analyst import (   # noqa: E402
    HORIZON_DAYS_RANGE,
    MAX_DECISIONS,
    MAX_HOOK_SHARE,
    MAX_MIX_SHIFT_PCT,
    MAX_TOPIC_DIRECTION,
    clean_json_response,
    is_due,
    validate_decisions,
)

CTX_RANDOM = {"niche_mode": "random", "niche_pool": ["universe_mysteries", "fun_facts", "dark_history"]}
CTX_FIXED  = {"niche_mode": "fixed", "niche_pool": []}
PRED = {"metric": "retention_avg", "direction": "up", "horizon_days": 14}


def _d(dtype, detail):
    return {"type": dtype, "detail": detail, "reason_codes": ["per_niche.x=1"], "prediction": dict(PRED)}


class TestValidateDecisions(unittest.TestCase):
    def test_valid_full_menu_random_channel(self):
        ds = [
            _d("topic_direction", {"directive": "Lean into unresolved-mystery endings"}),
            _d("hook_pattern", {"pattern": "question", "target_share": 0.3}),
            _d("content_type_mix", {"content_type": "history", "shift_pct": 10}),
            _d("niche_mix", {"niche": "universe_mysteries", "share_hint": 0.5}),
            _d("duration_note", {"note": "45s underperforms 30s on end_ratio"}),
            _d("focus_recommendation", {"niche": "universe_mysteries", "why": "subs 3.5x"}),
        ]
        ok, err = validate_decisions(ds, CTX_RANDOM)
        self.assertTrue(ok, err)

    def test_rejects_out_of_menu_and_bounds(self):
        self.assertFalse(validate_decisions([_d("hack_youtube", {})], CTX_RANDOM)[0])
        self.assertFalse(validate_decisions(
            [_d("hook_pattern", {"pattern": "question", "target_share": MAX_HOOK_SHARE + 0.01})], CTX_RANDOM)[0])
        self.assertFalse(validate_decisions(
            [_d("content_type_mix", {"content_type": "history", "shift_pct": MAX_MIX_SHIFT_PCT + 1})], CTX_RANDOM)[0])
        too_many = [_d("topic_direction", {"directive": f"d{i}"}) for i in range(MAX_TOPIC_DIRECTION + 1)]
        self.assertFalse(validate_decisions(too_many, CTX_RANDOM)[0])
        self.assertFalse(validate_decisions([], CTX_RANDOM)[0])
        self.assertFalse(validate_decisions(
            [_d("duration_note", {"note": "x"})] * (MAX_DECISIONS + 1), CTX_RANDOM)[0])

    def test_niche_decisions_forbidden_on_fixed_channel(self):
        ok, err = validate_decisions([_d("niche_mix", {"niche": "universe_mysteries", "share_hint": 0.3})], CTX_FIXED)
        self.assertFalse(ok)
        ok, _ = validate_decisions([_d("focus_recommendation", {"niche": "universe_mysteries", "why": "w"})], CTX_FIXED)
        self.assertFalse(ok)

    def test_niche_must_be_in_pool(self):
        ok, _ = validate_decisions([_d("niche_mix", {"niche": "bukan_pool", "share_hint": 0.3})], CTX_RANDOM)
        self.assertFalse(ok)

    def test_prediction_mandatory_and_bounded(self):
        d = _d("topic_direction", {"directive": "x"}); d.pop("prediction")
        self.assertFalse(validate_decisions([d], CTX_RANDOM)[0])
        d = _d("topic_direction", {"directive": "x"}); d["prediction"]["metric"] = "vibes"
        self.assertFalse(validate_decisions([d], CTX_RANDOM)[0])
        d = _d("topic_direction", {"directive": "x"}); d["prediction"]["horizon_days"] = HORIZON_DAYS_RANGE[1] + 1
        self.assertFalse(validate_decisions([d], CTX_RANDOM)[0])
        d = _d("topic_direction", {"directive": "x"}); d["reason_codes"] = []
        self.assertFalse(validate_decisions([d], CTX_RANDOM)[0])


class TestIsDue(unittest.TestCase):
    NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    def test_no_history_is_due(self):
        self.assertTrue(is_due(None, 7, self.NOW))

    def test_interval_respected(self):
        self.assertFalse(is_due((self.NOW - timedelta(days=6)).isoformat(), 7, self.NOW))
        self.assertTrue(is_due((self.NOW - timedelta(days=7)).isoformat(), 7, self.NOW))

    def test_bad_timestamp_does_not_block(self):
        self.assertTrue(is_due("bukan-tanggal", 7, self.NOW))


class TestCleanJson(unittest.TestCase):
    def test_strips_fences(self):
        self.assertEqual(clean_json_response('```json\n{"a":1}\n```'), '{"a":1}')
        self.assertEqual(clean_json_response('{"a":1}'), '{"a":1}')
        self.assertEqual(clean_json_response('```\n[1]\n```'), '[1]')


class TestPromptDeclaresAllBounds(unittest.TestCase):
    """Regresi insiden validasi-vs-prompt 18-Jul: batas yang DITEGAKKAN validator WAJIB
    DINYATAKAN di prompt — kalau tidak, LLM mustahil patuh (rejected beruntun sia-sia)."""

    def test_random_channel_prompt_states_share_hint_bounds(self):
        from src.intelligence.channel_analyst import ChannelAnalyst
        _, user = ChannelAnalyst._build_prompt({"x": 1}, CTX_RANDOM)
        self.assertIn("share_hint", user)
        self.assertIn("0..0.6", user)
        self.assertIn(str(MAX_HOOK_SHARE), user)
        self.assertIn(str(MAX_MIX_SHIFT_PCT), user)

    def test_fixed_channel_prompt_forbids_niche_decisions(self):
        from src.intelligence.channel_analyst import ChannelAnalyst
        _, user = ChannelAnalyst._build_prompt({"x": 1}, CTX_FIXED)
        self.assertIn("FORBIDDEN", user)


class TestMenuConstantsLocked(unittest.TestCase):
    def test_locked(self):
        self.assertEqual(MAX_DECISIONS, 6)
        self.assertEqual(MAX_TOPIC_DIRECTION, 3)
        self.assertEqual(MAX_HOOK_SHARE, 0.4)
        self.assertEqual(MAX_MIX_SHIFT_PCT, 20)
        self.assertEqual(HORIZON_DAYS_RANGE, (7, 30))


if __name__ == "__main__":
    unittest.main(verbosity=2)
