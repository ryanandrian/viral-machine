-- 0057 — Ringkasan insight tenant (AGREGAT lintas-channel) untuk dashboard
-- ============================================================================
-- Perbaikan: kartu Compliance & Self-Learning sebelumnya ambil 1 channel terbaru saja
-- → SALAH untuk tenant multi-channel (Business s/d 10 channel). RPC ini agregat
-- "insight TERBARU per channel" lalu rata-rata/jumlah. SECURITY DEFINER, scope auth.uid().
-- ============================================================================

create or replace function public.get_tenant_insights_summary()
returns table(
  channels_count   int,
  compliance_avg   numeric,
  videos_analyzed  int,
  last_learned     timestamptz,
  top_niche        text
)
language sql security definer set search_path = public stable as $$
  with latest as (
    -- insight TERBARU per channel milik tenant, HANYA channel yang masih nyata di `channels`
    -- (drop orphan/legacy channel_id v1 yang tak punya baris channels → cegah double-count).
    select distinct on (ci.channel_id)
           ci.channel_id, ci.compliance, ci.niche_weights, ci.videos_analyzed, ci.computed_at
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  niche_agg as (
    select key as niche, sum((value)::numeric) as w
    from latest, jsonb_each_text(coalesce(niche_weights, '{}'::jsonb))
    group by key
    order by w desc
    limit 1
  )
  select
    (select count(*)::int from latest),
    (select round(avg((compliance->>'score')::numeric), 1)
       from latest where compliance ? 'score'),
    (select coalesce(sum(videos_analyzed), 0)::int from latest),
    (select max(computed_at) from latest),
    (select niche from niche_agg);
$$;

revoke all     on function public.get_tenant_insights_summary() from public;
revoke execute on function public.get_tenant_insights_summary() from anon;
grant  execute on function public.get_tenant_insights_summary() to authenticated;
