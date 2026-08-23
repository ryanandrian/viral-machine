-- 0215 — Tarif MASUK `gpt-image-1-mini` dibetulkan ke tarif resmi OpenAI.
--
-- KENAPA. Pemeriksaan 23-Agu atas SEMBILAN tarif yang sungguh dipakai 30 hari terakhir — dibanding
-- satu per satu ke halaman resmi vendornya (OpenAI · Google · Groq). Hasilnya: **8 tepat, 1 salah**.
-- `gpt-image-1-mini` tercatat $2,00 per 1jt token MASUK, tarif resminya **$2,50**; token KELUAR
-- ($8,00) sudah benar. Selisih 25% pada sisi masuk saja ⇒ terukur pada hitung-ulang: **82 dari 246
-- produksi**, biaya **+0,47%…+1,46%**. Kecil, tapi salah — dan hanya bisa ditemukan dengan membuka
-- halaman resmi vendor, sebab tak ada mesin yang bisa menangkap nilai yang salah-tapi-masuk-akal
-- (§7e). 1 channel aktif memakainya.
--
-- KENAPA DIKUNCI. Angkanya datang dari umpan harga publik, dan umpan itulah yang keliru. Tanpa kunci,
-- sinkron harian besok menimpanya kembali ke $2,00 dan hasil pemeriksaan manusia ini hangus. Catatan
-- asal + tanggal wajib (§7c, dijaga G13) supaya siapa pun bisa memeriksanya ulang nanti.
--
-- YANG TIDAK DISENTUH: delapan baris lain (terbukti tepat, dibiarkan otomatis agar tetap mengikuti
-- perubahan vendor) · formula · riwayat biaya tenant (angka tersimpan per produksi tidak ditulis
-- ulang; yang benar berlaku mulai produksi berikutnya).
--
-- AMBANG: tepat 1 baris berubah · hanya kunci `in_per_1m` yang bergeser · nol formula bergerak.

begin;

create temp table _sebelum_0215 on commit drop as
  select model_key, pricing, pricing_locked, pricing_model from public.ai_models;

update public.ai_models set
  pricing = pricing
            || jsonb_build_object('in_per_1m', 2.50)
            || jsonb_build_object('source', 'manual', 'synced_at', now(),
                 'note', 'tarif resmi OpenAI (developers.openai.com/api/docs/pricing, cek '
                         '2026-08-23): $2,50 per 1jt token MASUK + $8,00 per 1jt token gambar '
                         'KELUAR. DIKUNCI: umpan harga publik mencatat masukannya $2,00 (25% '
                         'terlalu murah) — tanpa kunci, sinkron harian menimpanya kembali.'),
  pricing_locked = true
where model_key = 'gpt-image-1-mini';

do $$
declare n_berubah int; n_formula int; n_kunci int;
begin
  select count(*) into n_berubah
    from public.ai_models m join _sebelum_0215 s using (model_key)
   where m.pricing::text <> s.pricing::text
      or coalesce(m.pricing_locked, false) <> coalesce(s.pricing_locked, false);
  if n_berubah <> 1 then
    raise exception 'AMBANG 0215: % baris berubah, seharusnya TEPAT 1 — dibatalkan', n_berubah;
  end if;

  select count(*) into n_formula
    from public.ai_models m join _sebelum_0215 s using (model_key)
   where coalesce(m.pricing_model, '') <> coalesce(s.pricing_model, '');
  if n_formula <> 0 then
    raise exception 'AMBANG 0215: % formula bergeser — migrasi ini haram menyentuh formula', n_formula;
  end if;

  -- kunci tarif SELAIN in_per_1m haram bergerak (out_per_1m sudah benar, jangan ikut tersentuh)
  select count(*) into n_kunci
    from public.ai_models m join _sebelum_0215 s using (model_key)
   where (m.pricing - 'note' - 'synced_at' - 'source' - 'in_per_1m')::text
      <> (s.pricing - 'note' - 'synced_at' - 'source' - 'in_per_1m')::text;
  if n_kunci <> 0 then
    raise exception 'AMBANG 0215: % baris kunci tarif lain ikut bergeser — dibatalkan', n_kunci;
  end if;

  if (select count(*) from public.ai_models
       where (pricing->>'source') = 'manual'
         and (coalesce(pricing_locked, false) = false
              or coalesce(pricing->>'note', '') !~ '20[0-9][0-9]')) > 0 then
    raise exception 'AMBANG 0215: masih ada harga ketikan-tangan tanpa kunci atau tanpa tanggal';
  end if;
end $$;

commit;
