-- 0216 — Harga TERKUNCI diberi TANGGAL PEMERIKSAAN yang sebenarnya.
--
-- KENAPA. Alarm harga-basi kini ikut menjaga baris TERKUNCI (ketokan owner 24-Agu: *"jangan hanya
-- berfikir saat ini, tapi berfikir kedepannya"* — gembok tanpa pemeriksaan umur = pengecualian
-- permanen, dan pengecualian permanen adalah cara sistem yang benar membusuk). Alarm itu memakai
-- `pricing.synced_at` sebagai "kapan angka ini terakhir dipastikan".
--
-- Masalahnya: enam baris punya tanggal yang TIDAK mewakili kenyataan.
--   • empat baris (3 ElevenLabs + Edge) nilainya DIBANDINGKAN ke halaman resmi vendor pada 23-Agu,
--     tapi migr 0214 hanya menambahkan catatan asal — `synced_at`-nya masih Juli.
--   • dua baris (veo, Cloudflare) TIDAK PUNYA tanggal sama sekali ⇒ mustahil pernah terdeteksi tua.
-- Tanpa migrasi ini, alarm baru berbunyi di hari pertama untuk baris yang justru BARU diperiksa —
-- alarm palsu, dan alarm palsu mengajari admin mengabaikan alarm sungguhan.
--
-- Tanggalnya disetel ke **23-Agu-2026**, bukan `now()`: itu tanggal pemeriksaan yang SUNGGUH terjadi
-- (tercatat di catatan asal tiap baris). Mengaku diperiksa hari ini padahal tidak = memundurkan
-- jamnya sendiri.
--
-- NOL nilai tarif disentuh. NOL formula bergeser. NOL kunci berubah.
-- AMBANG: tepat 6 baris berubah · hanya `synced_at` yang bergerak · sesudahnya nol baris terkunci
-- yang berumur > 30 hari.

begin;

create temp table _sebelum_0216 on commit drop as
  select model_key, pricing, pricing_locked, pricing_model from public.ai_models;

update public.ai_models
   set pricing = pricing || jsonb_build_object('synced_at', '2026-08-23T12:00:00+00:00')
 where coalesce(pricing_locked, false)
   and coalesce(pricing->>'note', '') like '%2026-08-23%'
   and (pricing->>'synced_at' is null or (pricing->>'synced_at') < '2026-08-23');

do $$
declare n_berubah int; n_nilai int; n_tua int;
begin
  select count(*) into n_berubah
    from public.ai_models m join _sebelum_0216 s using (model_key)
   where m.pricing::text <> s.pricing::text;
  if n_berubah <> 6 then
    raise exception 'AMBANG 0216: % baris berubah, seharusnya TEPAT 6 — dibatalkan', n_berubah;
  end if;

  -- hanya synced_at yang boleh bergerak: bandingkan sisa objeknya
  select count(*) into n_nilai
    from public.ai_models m join _sebelum_0216 s using (model_key)
   where (m.pricing - 'synced_at')::text <> (s.pricing - 'synced_at')::text;
  if n_nilai <> 0 then
    raise exception 'AMBANG 0216: % baris ikut mengubah isi selain tanggal — dibatalkan', n_nilai;
  end if;

  if exists (select 1 from public.ai_models m join _sebelum_0216 s using (model_key)
              where coalesce(m.pricing_locked,false) <> coalesce(s.pricing_locked,false)
                 or coalesce(m.pricing_model,'') <> coalesce(s.pricing_model,'')) then
    raise exception 'AMBANG 0216: kunci atau formula ikut bergeser — dibatalkan';
  end if;

  select count(*) into n_tua from public.ai_models
   where coalesce(pricing_locked, false)
     and (pricing->>'synced_at' is null
          or (pricing->>'synced_at')::timestamptz < now() - interval '30 days');
  if n_tua <> 0 then
    raise exception 'AMBANG 0216: masih ada % harga terkunci tanpa tanggal / lebih tua dari 30 hari', n_tua;
  end if;
end $$;

commit;
