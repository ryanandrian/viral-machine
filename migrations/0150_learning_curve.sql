-- 0150 — [B17-F0] Kurva Belajar: RPC kohort minggu-publish per-channel/tenant + knob config
-- ============================================================================
-- Program Bukti Kecerdasan F0 (PROGRAM_BUKTI_KECERDASAN.md §2/§2b/§2c; ketok owner 2026-07-11).
-- Menjawab: "apakah video yang DIBUAT minggu ini lebih baik dari minggu lalu?"
--  • KOHORT = minggu-PUBLISH video (bukan kalender-views) → kurva naik = keputusan mesin membaik,
--    bukan video lama menabung views (§2b anti-tipu).
--  • Metrik UTAMA = retensi (avg_view_pct snapshot TERBARU per video — stabil terhadap umur).
--  • Views WAJIB BER-JENDELA (§2c.3): "views N hari pertama" = snapshot TERAKHIR dalam jendela
--    umur video, dihitung dari sejarah snapshot harian video_analytics (9.431 baris live).
--    Video yang jendelanya belum genap (terlalu muda) DIEKSKLUSI dari metrik views (jujur).
--  • Pola aman teruji: latest-per-video distinct on (0056/0148) + scope auth.uid() + guard
--    channel-nyata; agregasi set-based PENUH di DB (bebas jebakan cap-1000 jalur REST, §2.2b).
--  • p_channel_id NULL = seluruh channel tenant (tertimbang volume otomatis — agregat per-video);
--    berisi = per-channel (guard kepemilikan lewat filter tenant di subquery channels).
-- Knob config (no-hardcode §3.3): learning_curve_window_days · learning_curve_marker_date
-- (garis penanda "mesin disehatkan") · learning_curve_metrics (toggle metrik FE).
-- ============================================================================

create or replace function public.get_channel_learning_curve(p_channel_id uuid default null)
returns table(
  week_start    date,
  videos        int,
  retention_avg numeric,
  retention_n   int,
  views7d_avg   numeric,
  views7d_n     int
)
language sql security definer set search_path = public stable as $$
  with win as (
    -- jendela views (hari) dari config; fail-soft 7 (kegagalan baca ≠ kurva mati)
    select coalesce((select value from app_config where key = 'learning_curve_window_days'), 7) as days
  ),
  vids as (
    -- kohort: video PUBLISHED milik tenant (opsional 1 channel), dibucket per minggu-publish.
    -- video_id unik terverifikasi live 2026-07-11 (206 baris = 206 unik, nol duplikat).
    select v.video_id, v.published_at, (date_trunc('week', v.published_at))::date as wk
    from videos v
    where v.channel_id in (
            select c.id from channels c
            where c.tenant_id = (auth.uid())::text
              and (p_channel_id is null or c.id = p_channel_id))
      and v.status = 'published'
      and v.published_at is not null
      and coalesce(v.video_id, '') <> ''
  ),
  latest as (
    -- retensi: bacaan VALID terakhir per video (pola 0056 + filter avg_view_pct>0).
    -- Snapshot era-analytics-buta (pra-fix B16) menulis 0 = bacaan HILANG, bukan retensi 0 —
    -- verified live 2026-07-11: 12 video minggu 1-Jun snapshot-terbarunya 0 padahal bacaan valid
    -- 21-24 Jun ada (cakupan naik 150→194/206 video). Dipagari least(...,100): Shorts yang
    -- di-loop bisa >100% (max live 1261%) — konsisten konvensi tampilan widget insight lain.
    select distinct on (va.video_id) va.video_id, least(va.avg_view_pct, 100) as avg_view_pct
    from video_analytics va
    join vids on vids.video_id = va.video_id
    where va.avg_view_pct > 0
    order by va.video_id, va.analytics_date desc nulls last, va.collected_at desc nulls last
  ),
  early as (
    -- views ber-jendela: snapshot TERAKHIR dengan analytics_date ≤ publish + N hari;
    -- video lebih muda dari N hari dieksklusi (jendela belum genap = angka setengah matang)
    select distinct on (va.video_id) va.video_id, va.views
    from video_analytics va
    join vids on vids.video_id = va.video_id
    cross join win
    where va.analytics_date <= (vids.published_at::date + win.days)
      and vids.published_at <= now() - make_interval(days => win.days)
    order by va.video_id, va.analytics_date desc nulls last, va.collected_at desc nulls last
  )
  select vids.wk,
         count(*)::int,
         round((avg(latest.avg_view_pct))::numeric, 1),
         count(latest.video_id)::int,
         round((avg(early.views))::numeric, 0),
         count(early.views)::int
  from vids
  left join latest on latest.video_id = vids.video_id
  left join early  on early.video_id  = vids.video_id
  group by vids.wk
  order by vids.wk;
$$;

revoke all     on function public.get_channel_learning_curve(uuid) from public;
revoke execute on function public.get_channel_learning_curve(uuid) from anon;
grant  execute on function public.get_channel_learning_curve(uuid) to authenticated;

-- Knob config (idempotent; admin-editable via System Configuration — label dwibahasa di CFG_META FE)
insert into app_config (key, value, value_text, description) values
  ('learning_curve_window_days', 7, null,
   'Kurva Belajar: jendela metrik views = N hari pertama per video (anti bias-umur).'),
  ('learning_curve_marker_date', 0, '2026-07-11',
   'Kurva Belajar: tanggal garis penanda "mesin disehatkan" (YYYY-MM-DD; kosongkan utk sembunyikan).'),
  ('learning_curve_metrics', 0, '["retention","views7d"]',
   'Kurva Belajar: metrik toggle yang tampil (urutan = default pertama).')
on conflict (key) do nothing;
