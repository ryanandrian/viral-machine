-- ============================================================
-- Migration s84b: video_analytics table
-- Jalankan di Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

CREATE TABLE IF NOT EXISTS video_analytics (
  video_id           VARCHAR   PRIMARY KEY,   -- YouTube video ID
  tenant_id          TEXT      NOT NULL,
  niche              VARCHAR,                  -- dari videos table
  title              TEXT,
  hook_text          TEXT,
  -- Basic metrics (YouTube Data API v3 — selalu tersedia)
  views              INT       DEFAULT 0,
  likes              INT       DEFAULT 0,
  comments           INT       DEFAULT 0,
  -- Full metrics (YouTube Analytics API v2 — butuh yt-analytics scope)
  watch_time_mins    INT       DEFAULT 0,
  avg_view_pct       FLOAT     DEFAULT 0,     -- audience retention %
  ctr                FLOAT     DEFAULT 0,     -- card click rate %
  subscriber_gain    INT       DEFAULT 0,
  -- Status
  has_full_analytics BOOLEAN   DEFAULT false, -- true jika Analytics API berhasil
  published_at       TIMESTAMP,
  fetched_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_analytics_tenant
  ON video_analytics(tenant_id);

CREATE INDEX IF NOT EXISTS idx_video_analytics_niche
  ON video_analytics(tenant_id, niche);

CREATE INDEX IF NOT EXISTS idx_video_analytics_published
  ON video_analytics(published_at DESC);

-- Disable RLS (backend service table)
ALTER TABLE video_analytics DISABLE ROW LEVEL SECURITY;

-- Verifikasi
SELECT 'video_analytics' AS tabel, COUNT(*) AS rows FROM video_analytics;
