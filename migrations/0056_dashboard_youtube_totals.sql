-- 0056 — Dashboard: total YouTube (views/likes/followers) + auto-refresh realtime
-- ============================================================================
-- Konteks (owner 2026-06-19): rombak KPI dashboard tenant jadi data NYATA tenant-wide.
--  • Total Views / Likes = jumlah dari video_analytics, SNAPSHOT TERBARU per video
--    (sum mentah = over-count antar-snapshot → SALAH). RPC server-side (RLS via auth.uid()).
--  • Total Followers = subscriberCount channel (BARU; diisi worker self_learning fail-soft).
--  • Realtime production_runs → dashboard auto-refresh smooth (pola sama /runs).
-- ============================================================================

-- (1) Kolom subscriberCount per channel (diisi worker; fail-soft). Nullable = non-breaking.
alter table channels add column if not exists subscriber_count    bigint;
alter table channels add column if not exists subscriber_count_at  timestamptz;

-- (2) RPC totals tenant-wide (SECURITY DEFINER, scope auth.uid()). Views/Likes = latest-per-video.
create or replace function public.get_tenant_youtube_totals()
returns table(total_views bigint, total_likes bigint, total_followers bigint)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, views, likes
    from video_analytics
    where tenant_id = (auth.uid())::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last
  )
  select
    (select coalesce(sum(views), 0)::bigint from latest),
    (select coalesce(sum(likes), 0)::bigint from latest),
    (select coalesce(sum(subscriber_count), 0)::bigint
       from channels where tenant_id = (auth.uid())::text);
$$;

revoke all     on function public.get_tenant_youtube_totals() from public;
revoke execute on function public.get_tenant_youtube_totals() from anon;
grant  execute on function public.get_tenant_youtube_totals() to authenticated;

-- (3) Realtime untuk production_runs (auto-refresh dashboard). Idempotent.
do $$ begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='production_runs'
  ) then
    alter publication supabase_realtime add table production_runs;
  end if;
end $$;
