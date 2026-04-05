-- ============================================================
-- Migration s84c: channel_insights table + ALTER video_analytics
-- Jalankan di Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Tambah kolom yang kurang di video_analytics
ALTER TABLE video_analytics
  ADD COLUMN IF NOT EXISTS channel_id     VARCHAR,
  ADD COLUMN IF NOT EXISTS content_type   VARCHAR,
  ADD COLUMN IF NOT EXISTS views_per_sub  FLOAT   DEFAULT 0,
  ADD COLUMN IF NOT EXISTS analytics_date DATE    DEFAULT CURRENT_DATE;

-- 2. Tabel aggregated insights (computed mingguan oleh PerformanceAnalyzer)
CREATE TABLE IF NOT EXISTS channel_insights (
  insight_id        UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         TEXT      NOT NULL,
  channel_id        VARCHAR,
  computed_at       TIMESTAMP DEFAULT NOW(),
  videos_analyzed   INT       DEFAULT 0,
  niche_weights     JSONB     DEFAULT '{}',
  top_hooks         JSONB     DEFAULT '[]',
  content_type_perf JSONB     DEFAULT '{}',
  avoid_patterns    JSONB     DEFAULT '[]',
  top_topics        JSONB     DEFAULT '[]',
  performance_grade VARCHAR   DEFAULT 'insufficient_data'
);

CREATE INDEX IF NOT EXISTS idx_channel_insights_tenant
  ON channel_insights(tenant_id);

CREATE INDEX IF NOT EXISTS idx_channel_insights_computed
  ON channel_insights(tenant_id, computed_at DESC);

-- Disable RLS
ALTER TABLE channel_insights DISABLE ROW LEVEL SECURITY;

-- Verifikasi
SELECT 'channel_insights' AS tabel, COUNT(*) AS rows FROM channel_insights;
SELECT 'video_analytics columns' AS info,
       column_name
FROM information_schema.columns
WHERE table_name = 'video_analytics'
ORDER BY ordinal_position;
