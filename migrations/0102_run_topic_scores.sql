-- 0102 — get_run_topic_scores: dimensi skor viral per run (utk breakdown #5 di Run Detail)
-- ============================================================================
-- Dimensi (topic_scores) sebuah run bisa ada di `videos` (sudah terbit) ATAU `content_inventory`
-- (masih di buffer/antrean, belum terbit). RPC satu-pintu: ambil dari videos (by run_id) dulu,
-- fallback content_inventory (by metadata.run_id). Tenant-scoped (auth.uid()) — FE tak perlu
-- filter json rapuh. Return jsonb {search_volume,...} atau null bila run belum punya dimensi.
-- Additive, read-only. SECURITY DEFINER.
-- ============================================================================

create or replace function public.get_run_topic_scores(p_run_id text)
returns jsonb
language sql security definer set search_path = public stable as $$
  select coalesce(
    (select v.topic_scores
       from videos v
      where v.run_id = p_run_id
        and v.tenant_id = (auth.uid())::text
        and v.topic_scores ? 'search_volume'
      limit 1),
    (select ci.metadata->'script'->'topic_scores'
       from content_inventory ci
      where ci.metadata->>'run_id' = p_run_id
        and ci.tenant_id = (auth.uid())::text
        and (ci.metadata->'script'->'topic_scores') ? 'search_volume'
      limit 1)
  );
$$;

revoke all     on function public.get_run_topic_scores(text) from public, anon;
grant  execute on function public.get_run_topic_scores(text) to authenticated;
