-- 0020 — Compliance Score (Phase 7, DESAIN §9.3 — AI Slop Defense / SURVIVAL).
-- Skor 0-100 per-channel + 5 dimensi (diversity konten produksi) → feed widget D20.
-- Disimpan di channel_insights (rumah insights per-channel; satu row = performance + compliance).
ALTER TABLE channel_insights ADD COLUMN IF NOT EXISTS compliance JSONB DEFAULT '{}'::jsonb;
