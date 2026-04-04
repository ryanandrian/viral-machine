-- ============================================================
-- Migration s84: niches table + production_schedules table
-- Jalankan di Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Tabel niches — registry semua niche yang tersedia
CREATE TABLE IF NOT EXISTS niches (
  niche_id         VARCHAR  PRIMARY KEY,
  name             VARCHAR  NOT NULL,
  keywords         JSONB    NOT NULL DEFAULT '[]',
  style            VARCHAR  DEFAULT '',
  target_emotion   VARCHAR  DEFAULT '',
  hook_templates   JSONB    DEFAULT '[]',
  default_hashtags JSONB    DEFAULT '[]',
  is_active        BOOLEAN  DEFAULT true,
  created_at       TIMESTAMP DEFAULT NOW()
);

-- Seed 4 niche aktif (dari config.py NICHES dict)
INSERT INTO niches (niche_id, name, keywords, style, target_emotion, hook_templates) VALUES
(
  'universe_mysteries',
  'Universe Mysteries',
  '["space","universe","galaxy","black hole","nasa","cosmos","astronomy"]',
  'mysterious and awe-inspiring',
  'wonder and curiosity',
  '["Scientists just discovered something that changes everything...","NASA captured something they can''t explain...","This is what exists beyond the observable universe..."]'
),
(
  'fun_facts',
  'Mind-Blowing Facts',
  '["did you know","facts","amazing","incredible","surprising","world record"]',
  'energetic and surprising',
  'surprise and excitement',
  '["Did you know that...","This fact will blow your mind...","Most people don''t know this, but..."]'
),
(
  'dark_history',
  'Dark History',
  '["history","mystery","ancient","secret","civilization","unsolved"]',
  'dramatic and intriguing',
  'intrigue and suspense',
  '["This historical secret was hidden for centuries...","The real story behind this event is terrifying...","History books never told you this..."]'
),
(
  'ocean_mysteries',
  'Ocean Mysteries',
  '["ocean","deep sea","marine","underwater","creature","abyss"]',
  'mysterious and fascinating',
  'fascination and fear',
  '["Something massive lives in the deep ocean...","Scientists found this at the bottom of the sea...","This creature shouldn''t exist, but it does..."]'
)
ON CONFLICT (niche_id) DO NOTHING;

-- 2. Tabel production_schedules — jadwal produksi per channel
--    channel_id = tenant_id untuk sementara (multi-channel Item 7)
CREATE TABLE IF NOT EXISTS production_schedules (
  schedule_id      UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id       VARCHAR  NOT NULL,
  tenant_id        TEXT     NOT NULL,
  cron_expression  VARCHAR  NOT NULL,          -- '0 13 * * *'
  niche_id         VARCHAR  REFERENCES niches(niche_id),  -- NULL = AI/rotation pilih
  niche_focus      TEXT     DEFAULT NULL,      -- 'Gadget dan Teknologi Terkini'
  is_active        BOOLEAN  DEFAULT true,
  created_at       TIMESTAMP DEFAULT NOW()
);

-- Index untuk query cepat per tenant/channel
CREATE INDEX IF NOT EXISTS idx_prod_schedules_tenant
  ON production_schedules(tenant_id, is_active);

CREATE INDEX IF NOT EXISTS idx_prod_schedules_channel
  ON production_schedules(channel_id, is_active);

-- Seed jadwal 5x/hari untuk ryan_andrian (semua niche_id NULL = rotation/AI pilih)
-- Cron UTC: 07:00, 10:00, 13:00, 17:00, 00:00
INSERT INTO production_schedules (channel_id, tenant_id, cron_expression, niche_id, niche_focus) VALUES
('ryan_andrian', 'ryan_andrian', '0 7 * * *',  NULL, NULL),
('ryan_andrian', 'ryan_andrian', '0 10 * * *', NULL, NULL),
('ryan_andrian', 'ryan_andrian', '0 13 * * *', NULL, NULL),
('ryan_andrian', 'ryan_andrian', '0 17 * * *', NULL, NULL),
('ryan_andrian', 'ryan_andrian', '0 0 * * *',  NULL, NULL)
ON CONFLICT DO NOTHING;

-- 3. Tambah kolom rotasi ke tenant_configs
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS default_niche_rotation JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS niche_rotation_index   INT   DEFAULT 0;

-- Seed rotasi default ryan_andrian
UPDATE tenant_configs
SET default_niche_rotation = '["universe_mysteries","fun_facts","dark_history","ocean_mysteries"]'
WHERE tenant_id = 'ryan_andrian'
  AND (default_niche_rotation IS NULL OR default_niche_rotation = '[]');

-- 4. Verifikasi
SELECT 'niches' AS tabel, count(*) AS rows FROM niches
UNION ALL
SELECT 'production_schedules', count(*) FROM production_schedules
UNION ALL
SELECT 'tenant_configs (dengan rotation)', count(*)
  FROM tenant_configs WHERE default_niche_rotation != '[]';
