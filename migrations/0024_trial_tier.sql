-- 0024 — Trial sebagai TIER ke-4 (keputusan owner 2026-06-14). Caps reuse mekanisme plan_limits.
-- Trial = BYOK + time-boxed 7 hari (BUKAN free-tier permanen — selaras DESAIN §3). Lapse → trial_expired.
-- Caps trial (per-tier, admin-editable via plan_limits): 1 channel, 1 video/hari.
INSERT INTO plan_limits (plan_type, max_videos_per_day, max_channels)
VALUES ('trial', 1, 1)
ON CONFLICT (plan_type) DO NOTHING;

-- app_config: business-knob global admin-editable (no-hardcode). Durasi trial (plan_limits tak punya waktu).
CREATE TABLE IF NOT EXISTS app_config (
  key         TEXT PRIMARY KEY,
  value       INTEGER NOT NULL,
  description TEXT,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO app_config (key, value, description) VALUES
  ('trial_duration_days', 7, 'Lama trial gratis (hari) — admin-editable')
ON CONFLICT (key) DO NOTHING;

ALTER TABLE app_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS app_config_read ON app_config;
CREATE POLICY app_config_read ON app_config FOR SELECT USING (true);  -- public-read (admin-managed)
