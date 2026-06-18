-- 0058 — Analytics RPC server-side (data nyata, tenant-scoped, agregat efisien)
-- ============================================================================
-- Page /analytics kelas-pro: jawab "tumbuh?", "apa yang berhasil?", "perbanyak/hindari apa?".
-- Semua dihitung dari SNAPSHOT TERBARU per video (views kumulatif). SECURITY DEFINER + auth.uid().
-- Engagement = (likes+comments)/views ×100. Retensi = avg_view_pct (hanya video yang ada datanya).
-- ============================================================================

-- (1) Overview KPI
create or replace function public.get_tenant_analytics_overview()
returns table(videos int, total_views bigint, total_likes bigint, total_comments bigint,
  total_followers bigint, avg_retention numeric, avg_engagement numeric,
  videos_30d int, views_30d bigint, retention_videos int)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, views, likes, comments, avg_view_pct, published_at
    from video_analytics where tenant_id = (auth.uid())::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last)
  select
    (select count(*)::int from latest),
    (select coalesce(sum(views),0)::bigint from latest),
    (select coalesce(sum(likes),0)::bigint from latest),
    (select coalesce(sum(comments),0)::bigint from latest),
    (select coalesce(sum(subscriber_count),0)::bigint from channels where tenant_id=(auth.uid())::text),
    (select round(avg(avg_view_pct)::numeric,1) from latest where avg_view_pct > 0),
    (select round((sum(likes)+sum(comments))::numeric / nullif(sum(views),0) * 100, 2) from latest),
    (select count(*)::int from latest where published_at >= now() - interval '30 days'),
    (select coalesce(sum(views),0)::bigint from latest where published_at >= now() - interval '30 days'),
    (select count(*)::int from latest where avg_view_pct > 0);
$$;

-- (2) Performa per-niche (apa yang berhasil)
create or replace function public.get_tenant_analytics_by_niche()
returns table(niche text, videos int, views bigint, avg_retention numeric, avg_engagement numeric)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, niche, views, likes, comments, avg_view_pct
    from video_analytics where tenant_id=(auth.uid())::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last)
  select niche::text, count(*)::int, coalesce(sum(views),0)::bigint,
    round((avg(avg_view_pct) filter (where avg_view_pct>0))::numeric,1),
    round((sum(likes)+sum(comments))::numeric/nullif(sum(views),0)*100,2)
  from latest where niche is not null group by niche order by sum(views) desc;
$$;

-- (3) Views/video per bulan-terbit (tren)
create or replace function public.get_tenant_analytics_monthly()
returns table(month text, views bigint, videos int)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, views, published_at
    from video_analytics where tenant_id=(auth.uid())::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last)
  select to_char(published_at,'YYYY-MM'), coalesce(sum(views),0)::bigint, count(*)::int
  from latest where published_at is not null group by 1 order by 1;
$$;

-- (4) Video teratas (tabel sortable di FE: views/retensi/engagement)
create or replace function public.get_tenant_top_videos()
returns table(video_id text, title text, niche text, views bigint, retention numeric, engagement numeric, published_at timestamp)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, title, niche, views, likes, comments, avg_view_pct, published_at
    from video_analytics where tenant_id=(auth.uid())::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last)
  select video_id, title, niche::text, coalesce(views,0)::bigint,
    case when avg_view_pct>0 then round(avg_view_pct::numeric,1) else null end,
    case when views>0 then round((coalesce(likes,0)+coalesce(comments,0))::numeric/views*100,2) else null end,
    published_at
  from latest order by views desc nulls last limit 30;
$$;

-- (5) Pembelajaran mesin (hook/topik teratas + pola dihindari) dari insight channel NYATA terbaru
create or replace function public.get_tenant_learning()
returns table(top_hooks jsonb, top_topics jsonb, avoid_patterns jsonb, performance_grade text, computed_at timestamptz)
language sql security definer set search_path = public stable as $$
  select top_hooks, top_topics, avoid_patterns, performance_grade, computed_at
  from channel_insights
  where tenant_id=(auth.uid())::text
    and channel_id in (select id::text from channels where tenant_id=(auth.uid())::text)
  order by computed_at desc limit 1;
$$;

do $$ declare f text;
begin
  foreach f in array array['get_tenant_analytics_overview()','get_tenant_analytics_by_niche()',
    'get_tenant_analytics_monthly()','get_tenant_top_videos()','get_tenant_learning()'] loop
    execute format('revoke all on function public.%s from public', f);
    execute format('revoke execute on function public.%s from anon', f);
    execute format('grant execute on function public.%s to authenticated', f);
  end loop;
end $$;
