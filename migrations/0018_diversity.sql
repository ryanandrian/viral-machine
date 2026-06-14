-- 0018 — Diversity Engine (Phase 6.2, AI Slop Defense §9.1).
-- Anti "output seragam" → hindari risiko demonetisasi YouTube AI-policy 2026.
-- Dua bagian:
--   (A) TRACKING — videos catat dimensi diversity nyata (voice/hook/music/visual)
--       supaya lookback rotasi bisa hindari N-terakhir per-channel. Nullable = non-breaking.
--   (B) CONFIG  — diversity_config single-row (pola branding_config): platform/admin set
--       lookback + toggle per-dimensi + hook_pattern_pool. NO HARDCODE (config-driven).
-- Niche diversity sudah ada (schedule_manager._apply_diversity_guard) — TIDAK diubah di sini.

-- ── (A) Tracking dimensi diversity di videos (nullable, non-breaking) ─────────
ALTER TABLE videos ADD COLUMN IF NOT EXISTS voice_id    TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hook_pattern TEXT;   -- formula hook yang dipakai (HOOK_FORMULAS key)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS music_mood  TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_seed BIGINT;  -- seed image-gen (vary → fingerprint beda)

-- ── (B) Config platform (single-row id=1, admin-editable, RLS public-read) ────
CREATE TABLE IF NOT EXISTS diversity_config (
  id                      INT PRIMARY KEY DEFAULT 1,
  lookback_window         INT     DEFAULT 6,      -- selaras DIVERSITY_LOOKBACK niche-guard
  voice_rotation_enabled  BOOLEAN DEFAULT TRUE,
  hook_rotation_enabled   BOOLEAN DEFAULT TRUE,
  music_rotation_enabled  BOOLEAN DEFAULT TRUE,
  visual_rotation_enabled BOOLEAN DEFAULT TRUE,
  -- Round-robin pool hook (§9.1). Default = 5 HOOK_FORMULAS existing; admin bisa tambah.
  hook_pattern_pool       JSONB   DEFAULT '["question","impossible_claim","you_dont_know","number_shock","story_open"]'::jsonb,
  updated_at              TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT diversity_config_single_row CHECK (id = 1)
);

ALTER TABLE diversity_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS diversity_config_read ON diversity_config;
CREATE POLICY diversity_config_read ON diversity_config FOR SELECT USING (true);

INSERT INTO diversity_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
