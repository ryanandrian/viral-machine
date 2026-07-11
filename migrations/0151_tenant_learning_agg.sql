-- 0151 — get_tenant_learning: baris-terbaru-menang → AGREGAT semua channel (kelas bug 0148 yang terlewat)
-- ============================================================================
-- Insiden owner 2026-07-11 malam (tenant ryan, /analytics): badge "insufficient_data" + Hook teratas
-- kosong + Topik teratas kosong. AKAR (direproduksi sbg tenant): fungsi 0058 `order by computed_at
-- desc limit 1` = insight channel PALING BARU se-tenant — MVT (2 video, grade insufficient_data,
-- hooks/topics kosong) dihitung 158ms SETELAH RAD (201 video, peak, 10+10) → MVT menimpa segalanya.
-- Kelas bug sama dgn yang 0148 perbaiki di get_tenant_insights_summary & get_tenant_insights_agg;
-- fungsi ketiga ini terlewat karena hidup di migrasi berbeda (0058).
-- Sapu kelas 2026-07-11: 0057/0101/0068(2) sudah tertimbang via 0148 ✓ · get_tenant_compliance_agg
-- = agregat semua-channel (bukan latest-wins, bagian verifikasi total 11 Jul) ✓ · SISA = fungsi ini.
-- FIX: pola PERSIS 0148 — hook/topik gabungan lintas channel (dedup by teks, urut performa),
-- avoid_patterns union distinct, grade representatif = channel ber-video terbanyak.
-- Signature & grants TIDAK berubah → nol perubahan FE.
-- ============================================================================

create or replace function public.get_tenant_learning()
returns table(top_hooks jsonb, top_topics jsonb, avoid_patterns jsonb, performance_grade text, computed_at timestamptz)
language sql security definer set search_path = public stable as $$
  with latest as (
    -- insight TERBARU per channel milik tenant, hanya channel nyata (pola guard 0057/0148)
    select distinct on (ci.channel_id) ci.channel_id, ci.performance_grade, ci.videos_analyzed,
           ci.top_hooks, ci.top_topics, ci.avoid_patterns, ci.computed_at
    from channel_insights ci
    where ci.tenant_id = (auth.uid())::text
      and ci.channel_id in (select id::text from channels where tenant_id = (auth.uid())::text)
    order by ci.channel_id, ci.computed_at desc
  ),
  hk_all as (
    select h, coalesce((h->>'views')::numeric, 0) as v, lower(trim(h->>'hook')) as k
    from latest, jsonb_array_elements(coalesce(latest.top_hooks, '[]'::jsonb)) as h
    where coalesce(h->>'hook', '') <> ''
  ),
  hk as ( select distinct on (k) h, v from hk_all order by k, v desc ),
  hk_top as ( select h from hk order by v desc limit 10 ),
  tt_all as (
    select t, coalesce((t->>'composite_score')::numeric, (t->>'views')::numeric, 0) as cs,
           lower(trim(t->>'title')) as k
    from latest, jsonb_array_elements(coalesce(latest.top_topics, '[]'::jsonb)) as t
    where coalesce(t->>'title', '') <> ''
  ),
  tt as ( select distinct on (k) t, cs from tt_all order by k, cs desc ),
  tt_top as ( select t from tt order by cs desc limit 10 ),
  ap as (
    select distinct p from latest, jsonb_array_elements_text(coalesce(latest.avoid_patterns, '[]'::jsonb)) as p
  ),
  rep as ( -- grade representatif = channel dgn video dianalisis terbanyak (pola 0148)
    select latest.performance_grade as g from latest order by latest.videos_analyzed desc nulls last limit 1
  )
  select coalesce((select jsonb_agg(h) from hk_top), '[]'::jsonb),
         coalesce((select jsonb_agg(t) from tt_top), '[]'::jsonb),
         coalesce((select jsonb_agg(p) from ap),     '[]'::jsonb),
         (select g from rep),
         (select max(latest.computed_at) from latest);
$$;

revoke all     on function public.get_tenant_learning() from public;
revoke execute on function public.get_tenant_learning() from anon;
grant  execute on function public.get_tenant_learning() to authenticated;
