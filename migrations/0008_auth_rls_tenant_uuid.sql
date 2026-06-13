-- Migration 0008 — Phase 4.2/4.3: display_handle + RLS go-live (tenant_id = auth.uid())
-- Ref: decisions_auth_rbac + PHASE4_DESIGN. Target: v2. JANGAN apply ke v1 sampai cutover.
-- SCHEMA + RLS (idempotent, reusable). Remap DATA tenant_id "ryan_andrian"→UUID = skrip
-- one-time terpisah (lihat journal 2026-06-13). Tabel SHARED (music_library/niches/moods/
-- fonts) TIDAK kena tenant-RLS. Worker tulis pakai service_role (bypass RLS).

-- display_handle utk readability (PK tetap UUID via tenant_id=auth.uid())
ALTER TABLE public.tenant_configs ADD COLUMN IF NOT EXISTS display_handle text;

-- Enable RLS pada tabel tenant privat yang masih OFF
ALTER TABLE public.channel_insights      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.production_schedules  ENABLE ROW LEVEL SECURITY;

-- Policy SELECT seragam tenant_id = auth.uid()::text untuk 9 tabel privat.
-- (Tulis = service_role only → tak ada policy INSERT/UPDATE/DELETE. Frontend baca via auth.uid().)
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tenant_configs','channels','channel_insights','production_runs',
    'production_schedules','video_analytics','videos','pipeline_queue','pipeline_run_logs'
  ] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t||'_tenant_read', t);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR SELECT USING (tenant_id = (auth.uid())::text)',
      t||'_tenant_read', t);
  END LOOP;
END $$;
