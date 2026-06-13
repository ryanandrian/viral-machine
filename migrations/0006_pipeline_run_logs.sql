-- Migration 0006 — Phase 3: pipeline_run_logs (DB-based logging, UI-ready)
-- Ref: PROGRESS Phase 3. Target: v2. JANGAN apply ke v1 sampai cutover.
-- Log produksi per-tenant ke DB → siap untuk UI (Realtime live-tail D5) + persist error
-- (menutup DB-persist yang di-defer dari Phase 2). pipeline_errors/qc_failed_videos TIDAK
-- ada di v2 → tak ada yang dikonsolidasi; tabel ini sumber baru.

CREATE TABLE IF NOT EXISTS public.pipeline_run_logs (
  id          bigserial PRIMARY KEY,
  tenant_id   text NOT NULL,
  channel_id  text,                              -- placeholder Phase 5 (multi-channel)
  queue_id    text,                              -- pipeline_queue.id (loose, nullable utk run standalone)
  run_id      text,
  level       text NOT NULL DEFAULT 'INFO',      -- INFO|WARNING|ERROR|...
  step        text,                              -- niche|script|hook|tts|visual|render|publish|...
  category    text,                              -- dari PipelineError.category (Phase 2) bila error
  message     text NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prl_tenant_created ON public.pipeline_run_logs (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prl_run ON public.pipeline_run_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_prl_level ON public.pipeline_run_logs (level) WHERE level <> 'INFO';

-- RLS forward-compatible (decisions_auth_rbac: tenant_id = auth.uid()). Dormant sampai Phase 4
-- (belum ada auth user). WORKER tulis pakai service_role (bypass RLS). Frontend baca anon+auth.uid().
ALTER TABLE public.pipeline_run_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS prl_tenant_read ON public.pipeline_run_logs;
CREATE POLICY prl_tenant_read ON public.pipeline_run_logs
  FOR SELECT USING (tenant_id = (auth.uid())::text);
-- (Tidak ada INSERT policy → hanya service_role yang boleh menulis. Aman.)
