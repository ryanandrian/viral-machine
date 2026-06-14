-- 0029: enable Supabase Realtime on `channels` (Phase 9.2 vertical slice).
-- D2 Channels subscribes to tenant-scoped row changes (live re-sync). Realtime honors
-- the existing RLS SELECT policy (tenant_id = auth.uid()), so a client only receives
-- changes for its own rows. Idempotent: safe to re-run.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'channels'
  ) THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.channels';
  END IF;
END $$;

-- Ensure UPDATE events carry full row (default REPLICA IDENTITY = PK is enough for
-- new-row payload; FULL would also include old values — not needed for live re-sync).

-- RLS WRITE policy: tenant may UPDATE its own channel rows (toggle is_active, edit
-- channel settings from FE via anon key). Mirrors the existing SELECT policy's casting.
-- Phase 4.3 only created SELECT policies (service_all dropped) → FE writes were blocked.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'channels' AND policyname = 'channels_tenant_update'
  ) THEN
    EXECUTE 'CREATE POLICY channels_tenant_update ON public.channels FOR UPDATE '
         || 'USING (tenant_id = (auth.uid())::text) '
         || 'WITH CHECK (tenant_id = (auth.uid())::text)';
  END IF;
END $$;
