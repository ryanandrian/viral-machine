-- Migration 0005 — Phase 1.5: music_default_mood config (SOFTCODE §5)
-- Ref: PROGRESS Phase 1.5. Target: v2. JANGAN apply ke v1 sampai cutover.
-- Ganti hardcode mood 'dramatic' di music_selector → kolom config per-tenant.
-- NULLABLE, TANPA default global: kosong → mood any-active (graceful), bukan 'dramatic' global.

ALTER TABLE public.tenant_configs
  ADD COLUMN IF NOT EXISTS music_default_mood text;
