-- Migration 0009 — Phase 4.3 FIX: hapus policy permissive 'service_all' (BOCOR multi-tenant)
-- Ref: PHASE4_DESIGN. Target: v2. JANGAN apply ke v1 sampai cutover.
--
-- 'service_all' (ALL, role public, USING(true)) di-clone dari v1 single-tenant → membuat
-- SIAPA PUN (anon) bisa baca/tulis SEMUA row → RLS tenant percuma. Di v2 multi-tenant WAJIB
-- dihapus. service_role (worker/backend) TETAP bypass RLS otomatis (rolbypassrls) → aman tanpa
-- policy ini. Setelah drop: anon tak bisa baca; tenant baca via auth.uid() (tenant_read).

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tenant_configs','channels','pipeline_queue','production_runs','video_analytics','videos'
  ] LOOP
    EXECUTE format('DROP POLICY IF EXISTS service_all ON public.%I', t);
  END LOOP;
END $$;

-- dedup: pipeline_run_logs punya 2 policy SELECT identik (prl_tenant_read dari 0006 +
-- pipeline_run_logs_tenant_read dari 0008) → simpan yang konsisten penamaan.
DROP POLICY IF EXISTS prl_tenant_read ON public.pipeline_run_logs;

-- plan_limits = config tier SHARED (tanpa tenant_id). 'service_all' (ALL,public,USING true)
-- mengizinkan anon MENULIS tier limits → ganti: public READ saja, tulis = service_role.
DROP POLICY IF EXISTS service_all ON public.plan_limits;
DROP POLICY IF EXISTS plan_limits_read ON public.plan_limits;
CREATE POLICY plan_limits_read ON public.plan_limits FOR SELECT USING (true);
