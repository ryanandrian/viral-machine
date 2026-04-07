-- ============================================================
-- Migration s87: Stage 3 — Viral Score Weight Adaptif
-- + Performance Attribution
-- Jalankan di Supabase SQL Editor
-- ============================================================

-- 1. videos: simpan 5 skor dimensi saat produksi (untuk korelasi S3-A)
ALTER TABLE videos
  ADD COLUMN IF NOT EXISTS topic_scores   JSONB   DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS insights_grade VARCHAR DEFAULT '';

-- 2. tenant_configs: simpan adaptive weights hasil komputasi (S3-A)
--    Struktur JSON:
--    {
--      "weights": {search_volume, trend_momentum, emotional_trigger,
--                  competition_gap, evergreen_potential},
--      "videos_analyzed": 45,
--      "alpha": 0.83,
--      "correlations": {...},
--      "computed_at": "2026-04-07"
--    }
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS viral_score_weights JSONB DEFAULT '{}';

-- Verifikasi
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'videos'
  AND column_name IN ('topic_scores', 'insights_grade')
ORDER BY column_name;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenant_configs'
  AND column_name = 'viral_score_weights';
