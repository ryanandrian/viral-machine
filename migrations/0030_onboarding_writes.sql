-- 0030: Onboarding write-path (Phase 9.3 Area 2.1) — SAFE tables only via client RLS.
-- channels + production_schedules = 100% config columns (no billing/comp) → aman ditulis
-- tenant via anon + RLS (tenant_id = auth.uid()).
--
-- ⚠️ SENGAJA TIDAK menambah policy UPDATE/INSERT untuk `tenant_configs`:
-- tenant_configs MENCAMPUR kolom config (niche/keys/voice) DENGAN kolom billing/comp
-- (plan_type, subscription_status, is_developer, discount_pct). RLS = row-level (tak bisa
-- batasi kolom) → blanket UPDATE = tenant bisa self-upgrade/self-comp = lubang anti-abuse.
-- Tulisan tenant_configs HARUS lewat server-route ber-whitelist kolom (service_role) — increment 2.
--
-- Idempotent. tenant_id = TEXT (auth.uid()::text), mirror policy SELECT existing.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='channels' AND policyname='channels_tenant_insert') THEN
    EXECUTE 'CREATE POLICY channels_tenant_insert ON public.channels FOR INSERT '
         || 'WITH CHECK (tenant_id = (auth.uid())::text)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='production_schedules' AND policyname='production_schedules_tenant_insert') THEN
    EXECUTE 'CREATE POLICY production_schedules_tenant_insert ON public.production_schedules FOR INSERT '
         || 'WITH CHECK (tenant_id = (auth.uid())::text)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='production_schedules' AND policyname='production_schedules_tenant_update') THEN
    EXECUTE 'CREATE POLICY production_schedules_tenant_update ON public.production_schedules FOR UPDATE '
         || 'USING (tenant_id = (auth.uid())::text) WITH CHECK (tenant_id = (auth.uid())::text)';
  END IF;
END $$;

-- content_language per-channel (decisions_content_language: channel.content_language).
-- Onboarding C4 set bahasa konten; FK lunak ke content_languages.locale (tak di-enforce kini).
ALTER TABLE public.channels ADD COLUMN IF NOT EXISTS content_language TEXT;
