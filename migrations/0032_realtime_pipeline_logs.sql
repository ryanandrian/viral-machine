-- 0032: enable Supabase Realtime on `pipeline_run_logs` (Phase 9.3 D5 live-tail).
-- D5 Run Detail subscribe log baru per-run (live-tail). Realtime hormati RLS SELECT existing
-- (pipeline_run_logs_tenant_read: tenant_id = auth.uid()) → client hanya terima log tenant-nya.
-- INSERT log = service_role (worker) — TIDAK ada policy INSERT untuk tenant (FE hanya baca+subscribe).
-- Idempotent.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'pipeline_run_logs'
  ) THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.pipeline_run_logs';
  END IF;
END $$;
