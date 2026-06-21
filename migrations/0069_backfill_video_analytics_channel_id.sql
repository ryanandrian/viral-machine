-- 0069 — F1-06: backfill video_analytics.channel_id (MULTI-CHANNEL-correct, per-VIDEO)
-- ============================================================================
-- video_analytics.channel_id 100% NULL (legacy v1). Sumber kebenaran channel per baris =
-- videos.channel_id (terisi 100%), di-link via video_analytics.video_id = videos.video_id
-- (YouTube id, text) — 3606/3606 cocok (verified).
--
-- PER-VIDEO (bukan per-tenant): tiap baris analytics → channel VIDEO-nya. BENAR untuk tenant
-- multi-channel (ribuan tenant × banyak channel) — bukan asumsi "1 tenant = 1 channel".
-- Idempotent (hanya update yang berbeda). Tabel lain (content_inventory/production_runs/
-- channel_insights/videos) sudah 0-NULL (verified). channel_id dibiarkan NULLABLE
-- (tak ALTER NOT NULL — hindari risiko regresi).
-- ============================================================================

update video_analytics va
   set channel_id = v.channel_id::text
  from videos v
 where va.video_id = v.video_id
   and va.channel_id is distinct from v.channel_id::text;
