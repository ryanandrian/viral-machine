-- 0059 — RPC views per video (untuk kolom Views di /runs) + backfill channel/topic historis
-- ============================================================================
-- /runs: kolom Views kosong krn production_runs tak simpan views (ada di video_analytics).
-- RPC kembalikan views TERBARU per video_id (tenant-scoped) → FE map youtube_video_id→views.
-- ============================================================================

create or replace function public.get_tenant_video_views()
returns table(video_id text, views bigint)
language sql security definer set search_path = public stable as $$
  select distinct on (video_id) video_id, coalesce(views,0)::bigint
  from video_analytics where tenant_id = (auth.uid())::text
  order by video_id, analytics_date desc nulls last, collected_at desc nulls last;
$$;

revoke all     on function public.get_tenant_video_views() from public;
revoke execute on function public.get_tenant_video_views() from anon;
grant  execute on function public.get_tenant_video_views() to authenticated;
