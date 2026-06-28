-- 0098 — Standardisasi SATUAN analytics (all-time) + RPC per-channel
-- ============================================================================
-- Kesepakatan owner 2026-06-28 (Opsi A, all-time): SATU definisi per angka, dipakai di SEMUA layar
-- (header channel / card / main / dashboard) → tenant tak bingung (sebelumnya "total video" = 117/176/180).
--   • Views/Engagement/Retensi/Komentar = video_analytics SNAPSHOT TERBARU per video (all-time)
--   • Video terbit                       = videos.status='published'  (BUKAN production_runs / analytics-distinct)
--   • Followers                          = channels.subscriber_count
-- Perubahan:
--   (1) get_tenant_analytics_overview.videos → dari videos.published (dulu: distinct video_analytics)
--   (2) get_channel_analytics(uuid) BARU    → versi per-channel utk header Manage (all-time, latest-per-video)
-- Tipe: channels.id & videos.channel_id = uuid; video_analytics.channel_id = text (cast p_channel_id::text).
-- ============================================================================

-- (1) Overview tenant (semua channel) — `videos` kini = VIDEO TERBIT (videos.published).
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
    (select count(*)::int from videos where tenant_id=(auth.uid())::text and status='published'),
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
revoke all     on function public.get_tenant_analytics_overview() from public, anon;
grant  execute on function public.get_tenant_analytics_overview() to authenticated;

-- (2) Per-channel analytics (header Manage channel). All-time, latest-per-video.
-- Ownership: semua subquery di-filter tenant_id=auth.uid() → channel milik orang lain balas 0 (aman).
create or replace function public.get_channel_analytics(p_channel_id uuid)
returns table(published_videos int, total_views bigint, total_likes bigint, total_comments bigint,
  avg_retention numeric, avg_engagement numeric, subscriber_count bigint)
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (video_id) video_id, views, likes, comments, avg_view_pct
    from video_analytics
    where tenant_id = (auth.uid())::text and channel_id = p_channel_id::text
    order by video_id, analytics_date desc nulls last, collected_at desc nulls last)
  select
    (select count(*)::int from videos
       where tenant_id=(auth.uid())::text and channel_id=p_channel_id and status='published'),
    (select coalesce(sum(views),0)::bigint from latest),
    (select coalesce(sum(likes),0)::bigint from latest),
    (select coalesce(sum(comments),0)::bigint from latest),
    (select round(avg(avg_view_pct)::numeric,1) from latest where avg_view_pct > 0),
    (select round((sum(likes)+sum(comments))::numeric / nullif(sum(views),0) * 100, 2) from latest),
    (select coalesce(subscriber_count,0)::bigint from channels
       where id=p_channel_id and tenant_id=(auth.uid())::text);
$$;
revoke all     on function public.get_channel_analytics(uuid) from public, anon;
grant  execute on function public.get_channel_analytics(uuid) to authenticated;
