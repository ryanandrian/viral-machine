-- 0068 — Agregat Compliance & Insights lintas-channel (F2-13)
-- ============================================================================
-- Halaman MAIN /compliance & /insights sebelumnya `channel_insights … limit(1)` =
-- ambil 1 channel saja → SALAH untuk tenant multi-channel. RPC ini agregat
-- "insight TERBARU per channel" (distinct on channel_id) lalu rata-rata/gabung,
-- mengembalikan jsonb berbentuk SAMA dengan yang dikonsumsi FE (Compliance/Insights)
-- agar komponen view dipakai-ulang. SECURITY DEFINER, scope auth.uid().
-- Per-channel (tab Channel Detail) TIDAK pakai RPC ini — query channel_insights
-- langsung by channel_id (RLS). Additive: nol perubahan tabel, nol dampak runtime.
-- ============================================================================

-- (1) Compliance agregat → {score, status, dimensions{5}, alert_below, channels_count}
create or replace function public.get_tenant_compliance_agg()
returns jsonb
language sql security definer set search_path = public stable as $$
  with latest as (
    select distinct on (ci.channel_id) ci.channel_id, ci.compliance
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  scored as (
    select (compliance->>'score')::numeric as score,
           compliance->'dimensions'        as dims,
           (compliance->>'alert_below')::numeric as alert_below
    from latest
    where (compliance->>'score') is not null
  ),
  d as ( select dims from scored )
  select jsonb_build_object(
    'score',  (select round(avg(score),1) from scored),
    'status', case when (select count(*) from scored) = 0 then 'insufficient_data' else 'ok' end,
    'dimensions', jsonb_build_object(
      'niche_distribution', (select round(avg((dims->>'niche_distribution')::numeric),1) from d where (dims->>'niche_distribution') is not null),
      'hook_style_spread',  (select round(avg((dims->>'hook_style_spread')::numeric),1)  from d where (dims->>'hook_style_spread')  is not null),
      'voice_diversity',    (select round(avg((dims->>'voice_diversity')::numeric),1)    from d where (dims->>'voice_diversity')    is not null),
      'dup_freshness',      (select round(avg((dims->>'dup_freshness')::numeric),1)      from d where (dims->>'dup_freshness')      is not null),
      'ai_disclosure',      (select round(avg((dims->>'ai_disclosure')::numeric),1)      from d where (dims->>'ai_disclosure')      is not null)
    ),
    'alert_below',    coalesce((select max(alert_below) from scored), 60),
    'channels_count', (select count(*) from latest)
  );
$$;

-- (2) Insights agregat → {performance_grade, videos_analyzed, channels_count,
--     niche_weights, top_hooks, avoid_patterns, computed_at}
create or replace function public.get_tenant_insights_agg()
returns jsonb
language plpgsql security definer set search_path = public stable as $$
declare result jsonb;
begin
  with latest as (
    select distinct on (ci.channel_id) ci.channel_id, ci.performance_grade, ci.videos_analyzed,
           ci.niche_weights, ci.top_hooks, ci.avoid_patterns, ci.computed_at
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  nw as ( -- bobot niche: jumlah lintas channel (FE urut by value)
    select key as niche, sum((value)::numeric) as w
    from latest, jsonb_each_text(coalesce(niche_weights, '{}'::jsonb))
    group by key
  ),
  hk as ( -- hook teratas: gabung lintas channel, urut views desc, ambil 10
    select h from latest, jsonb_array_elements(coalesce(top_hooks, '[]'::jsonb)) as h
    order by coalesce((h->>'views')::numeric, 0) desc
    limit 10
  ),
  ap as ( -- pola dihindari: union distinct
    select distinct p from latest, jsonb_array_elements_text(coalesce(avoid_patterns, '[]'::jsonb)) as p
  ),
  rep as ( -- grade representatif = channel dgn video terbanyak
    select performance_grade from latest order by videos_analyzed desc nulls last limit 1
  )
  select jsonb_build_object(
    'performance_grade', coalesce((select performance_grade from rep), 'learning'),
    'videos_analyzed',   coalesce((select sum(videos_analyzed) from latest), 0),
    'channels_count',    (select count(*) from latest),
    'niche_weights',     coalesce((select jsonb_object_agg(niche, w) from nw), '{}'::jsonb),
    'top_hooks',         coalesce((select jsonb_agg(h) from hk), '[]'::jsonb),
    'avoid_patterns',    coalesce((select jsonb_agg(p) from ap), '[]'::jsonb),
    'computed_at',       (select max(computed_at) from latest)
  ) into result;
  return result;
end $$;

revoke all     on function public.get_tenant_compliance_agg() from public, anon;
revoke all     on function public.get_tenant_insights_agg()   from public, anon;
grant  execute on function public.get_tenant_compliance_agg() to authenticated;
grant  execute on function public.get_tenant_insights_agg()   to authenticated;
