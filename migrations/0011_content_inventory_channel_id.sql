-- Migration 0011 — Phase 5: content_inventory (buffer) + channel_id propagation
-- Ref: decisions_production_scaling §2 (decouple producer/publisher + buffer Biznet S3) +
-- PROGRESS Phase 5 (multi-channel). Target: v2. JANGAN apply ke v1 sampai cutover.

-- ── content_inventory: source-of-truth status video siap-tayang di buffer (Biznet S3) ──
-- Producer isi (status producing→ready); Publisher ambil (ready→publishing→published).
CREATE TABLE IF NOT EXISTS public.content_inventory (
  id           bigserial PRIMARY KEY,
  tenant_id    text NOT NULL,
  channel_id   text,
  niche        text,
  s3_key       text,                                  -- lokasi MP4 di Biznet S3 (null sebelum upload)
  status       text NOT NULL DEFAULT 'producing',     -- producing|ready|publishing|published|failed
  metadata     jsonb NOT NULL DEFAULT '{}'::jsonb,     -- run_id, topic, viral_score, duration, dll
  produced_at  timestamptz,
  target_slot  timestamptz,
  expires_at   timestamptz,                            -- freshness guard (buffer depth per-niche)
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ci_channel_status ON public.content_inventory (channel_id, status);
CREATE INDEX IF NOT EXISTS idx_ci_tenant ON public.content_inventory (tenant_id);
CREATE INDEX IF NOT EXISTS idx_ci_ready ON public.content_inventory (status, target_slot) WHERE status = 'ready';

-- RLS: tenant-private (tenant_id=auth.uid()), tulis service_role only.
ALTER TABLE public.content_inventory ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS content_inventory_tenant_read ON public.content_inventory;
CREATE POLICY content_inventory_tenant_read ON public.content_inventory
  FOR SELECT USING (tenant_id = (auth.uid())::text);

-- ── channel_id propagation: lengkapi tabel yang belum punya (multi-channel) ──
ALTER TABLE public.production_runs ADD COLUMN IF NOT EXISTS channel_id text;
ALTER TABLE public.pipeline_queue  ADD COLUMN IF NOT EXISTS channel_id text;
