-- 0101 — Perluas insight agregat: performa jenis konten + topik pemenang + dedup hook
-- ============================================================================
-- Halaman MAIN /insights (agregat semua channel) sebelumnya hanya menampilkan niche_weights,
-- top_hooks (views), avoid_patterns — padahal channel_insights JUGA menyimpan content_type_perf
-- (retensi per jenis konten) & top_topics (topik pemenang) yang BERNILAI bagi tenant tapi
-- tak pernah di-return. RPC ini menambah keduanya (agregat lintas channel) + dedup top_hooks
-- (hook sama dipakai banyak video → jangan tampil berulang). Bentuk return tetap kompatibel
-- (hanya MENAMBAH field). Per-channel (tab Channel Detail) query channel_insights langsung.
-- Additive: nol perubahan tabel, nol dampak runtime. SECURITY DEFINER, scope auth.uid().
-- ============================================================================

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
  nw as ( -- bobot niche: jumlah lintas channel (FE urut by value)
    select key as niche, sum((value)::numeric) as w
    from latest, jsonb_each_text(coalesce(niche_weights, '{}'::jsonb))
    group by key
  ),
  hk_all as (
    select h, coalesce((h->>'views')::numeric, 0) as v, lower(trim(h->>'hook')) as hook_key
    from latest, jsonb_array_elements(coalesce(top_hooks, '[]'::jsonb)) as h
    where coalesce(h->>'hook', '') <> ''
  ),
  hk as ( -- dedup by teks hook (ambil views tertinggi)
    select distinct on (hook_key) h, v from hk_all
    order by hook_key, v desc
  ),
  hk_top as ( select h from hk order by v desc limit 10 ),
  ap as ( -- pola dihindari: union distinct
    select distinct p from latest, jsonb_array_elements_text(coalesce(avoid_patterns, '[]'::jsonb)) as p
  ),
  ctp as ( -- performa jenis konten: gabung lintas channel (retensi weighted by retention_count, views weighted by count)
    select key as ct,
           sum((value->>'count')::numeric)                                                                       as cnt,
           sum(coalesce((value->>'retention_count')::numeric, 0))                                                 as ret_cnt,
           sum(coalesce((value->>'avg_view_pct')::numeric, 0) * coalesce((value->>'retention_count')::numeric, 0)) as wret,
           sum(coalesce((value->>'avg_views')::numeric, 0) * (value->>'count')::numeric)                          as wviews
    from latest, jsonb_each(coalesce(content_type_perf, '{}'::jsonb))
    group by key
  ),
  tt_all as (
    select t, coalesce((t->>'composite_score')::numeric, 0) as cs, lower(trim(t->>'title')) as title_key
    from latest, jsonb_array_elements(coalesce(top_topics, '[]'::jsonb)) as t
    where coalesce(t->>'title', '') <> ''
  ),
  tt as ( -- dedup by judul (topik sama diproduksi berulang)
    select distinct on (title_key) t, cs from tt_all
    order by title_key, cs desc
  ),
  tt_top as ( select t from tt order by cs desc limit 8 ),
  rep as ( -- grade representatif = channel dgn video terbanyak
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
