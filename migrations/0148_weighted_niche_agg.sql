-- 0148 — Insight agregat lintas-channel = TERTIMBANG VOLUME (2 RPC: dashboard + /insights)
-- ============================================================================
-- Konsep owner (2026-07-11): menu utama & dashboard = potret SELURUH channel (tot/avg);
-- insight per-channel hidup di tab Channel Detail (channel_insights langsung, tak berubah).
-- Insiden: bobot niche dijumlah lintas-channel TANPA menimbang ukuran sampel → channel uji
-- (23 baris snapshot / 4 video, islami 0.778) mengalahkan channel produksi (200 video).
-- Fix di DUA titik yang sama-sama cacat:
--   (1) get_tenant_insights_summary (kartu dashboard) — niche_agg × videos_analyzed (top-1).
--   (2) get_tenant_insights_agg (menu utama /insights) — nw × videos_analyzed lalu
--       DINORMALISASI kembali ke 0..1 (FE insights-view menampilkan nilai sebagai persen —
--       baris 123: (w*100).toFixed(1)% — skala mentah akan tampil "7663%"; verified 2026-07-11).
-- Verifikasi pra-apply data live: islami 0.778×23=17.9 < dark_history 0.435×200=87.0.
-- Signature & grants kedua fungsi TIDAK berubah → nol perubahan FE.
-- Catatan: nilai tertimbang akurat penuh setelah P5 (videos_analyzed = video unik, bukan baris).
-- ============================================================================

-- (1) Dashboard summary — dari 0057; HANYA blok niche_agg yang berubah.
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
    select distinct on (ci.channel_id)
           ci.channel_id, ci.compliance, ci.niche_weights, ci.videos_analyzed, ci.computed_at
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  niche_agg as (
    -- 0148: tertimbang volume — bobot ternormalisasi per-channel × video dianalisis channel itu.
    select key as niche, sum((value)::numeric * greatest(coalesce(videos_analyzed, 0), 0)) as w
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

-- (2) Menu utama /insights — dari 0101; HANYA blok nw yang berubah (tertimbang + normalisasi 0..1).
create or replace function public.get_tenant_insights_agg()
returns jsonb
language plpgsql security definer set search_path = public stable as $$
declare result jsonb;
begin
  with latest as (
    select distinct on (ci.channel_id) ci.channel_id, ci.performance_grade, ci.videos_analyzed,
           ci.niche_weights, ci.top_hooks, ci.avoid_patterns, ci.content_type_perf, ci.top_topics, ci.computed_at
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  nw_raw as ( -- 0148: bobot niche tertimbang volume (dulu: jumlah bobot ternormalisasi antar-channel = bisa dibajak channel kecil)
    select key as niche, sum((value)::numeric * greatest(coalesce(videos_analyzed, 0), 0)) as w
    from latest, jsonb_each_text(coalesce(niche_weights, '{}'::jsonb))
    group by key
  ),
  nw as ( -- normalisasi kembali ke 0..1 (kontrak tampilan FE: nilai = proporsi, dirender sbg persen)
    select niche,
           case when (select sum(w) from nw_raw) > 0
                then round(w / (select sum(w) from nw_raw), 4)
                else 0 end as w
    from nw_raw
  ),
  hk_all as (
    select h, coalesce((h->>'views')::numeric, 0) as v, lower(trim(h->>'hook')) as hook_key
    from latest, jsonb_array_elements(coalesce(top_hooks, '[]'::jsonb)) as h
    where coalesce(h->>'hook', '') <> ''
  ),
  hk as (
    select distinct on (hook_key) h, v from hk_all
    order by hook_key, v desc
  ),
  hk_top as ( select h from hk order by v desc limit 10 ),
  ap as (
    select distinct p from latest, jsonb_array_elements_text(coalesce(avoid_patterns, '[]'::jsonb)) as p
  ),
  ctp as (
    select key as ct,
           sum((value->>'count')::numeric)                                                                        as cnt,
           sum(coalesce((value->>'retention_count')::numeric, 0))                                                  as ret_cnt,
           sum(coalesce((value->>'avg_view_pct')::numeric, 0) * coalesce((value->>'retention_count')::numeric, 0)) as wret,
           sum(coalesce((value->>'avg_views')::numeric, 0) * (value->>'count')::numeric)                           as wviews
    from latest, jsonb_each(coalesce(content_type_perf, '{}'::jsonb))
    group by key
  ),
  tt_all as (
    select t, coalesce((t->>'composite_score')::numeric, 0) as cs, lower(trim(t->>'title')) as title_key
    from latest, jsonb_array_elements(coalesce(top_topics, '[]'::jsonb)) as t
    where coalesce(t->>'title', '') <> ''
  ),
  tt as (
    select distinct on (title_key) t, cs from tt_all
    order by title_key, cs desc
  ),
  tt_top as ( select t from tt order by cs desc limit 8 ),
  rep as (
    select performance_grade from latest order by videos_analyzed desc nulls last limit 1
  )
  select jsonb_build_object(
    'performance_grade', coalesce((select performance_grade from rep), 'learning'),
    'videos_analyzed',   coalesce((select sum(videos_analyzed) from latest), 0),
    'channels_count',    (select count(*) from latest),
    'niche_weights',     coalesce((select jsonb_object_agg(niche, w) from nw), '{}'::jsonb),
    'top_hooks',         coalesce((select jsonb_agg(h) from hk_top), '[]'::jsonb),
    'avoid_patterns',    coalesce((select jsonb_agg(p) from ap), '[]'::jsonb),
    'content_type_perf', coalesce((select jsonb_object_agg(ct, jsonb_build_object(
                            'avg_view_pct',    case when ret_cnt > 0 then round(wret / ret_cnt, 1) else 0 end,
                            'avg_views',       case when cnt > 0 then round(wviews / cnt) else 0 end,
                            'count',           cnt::int,
                            'retention_count', ret_cnt::int
                          )) from ctp), '{}'::jsonb),
    'top_topics',        coalesce((select jsonb_agg(t) from tt_top), '[]'::jsonb),
    'computed_at',       (select max(computed_at) from latest)
  ) into result;
  return result;
end $$;

revoke all     on function public.get_tenant_insights_agg() from public, anon;
grant  execute on function public.get_tenant_insights_agg()   to authenticated;
