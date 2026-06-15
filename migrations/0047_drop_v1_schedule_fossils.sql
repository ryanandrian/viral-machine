-- 0047: PERBAIKAN PRODUCE & PUBLISH — Area A5 (buang fosil V1, SETELAH BE+FE lepas).
-- production_schedules = sumber kebingungan FE↔BE (FE tulis sini, BE baca channels.publish_slots).
-- Diverifikasi NOL pembaca live (BE: schedule_manager dihapus; FE: halaman Jadwal di-rewrite ke channels).
drop table if exists public.production_schedules;

-- Kolom vestigial DIBIARKAN (loader tenant_config baca dgn default aman — drop = risiko, nilai rendah).
-- Ditandai DEPRECATED agar tak membingungkan sesi berikutnya.
comment on column public.channels.production_cron        is 'DEPRECATED (migr 0047): produksi = buffer-driven (§12c), bukan jadwal-waktu. Tak dipakai.';
comment on column public.channels.niche_pool             is 'DEPRECATED-role (migr 0047): random kini rotasi SELURUH entitlement tenant; niche_pool tak lagi sumber random.';
comment on column public.tenant_configs.publish_slots    is 'DEPRECATED (migr 0047): sumber jadwal kanonik = channels.publish_slots (per-channel). Tak dipakai publisher v2.';
comment on column public.tenant_configs.production_cron  is 'DEPRECATED (migr 0047): tak dipakai (produksi buffer-driven).';
comment on column public.tenant_configs.analytics_cron   is 'DEPRECATED (migr 0047): self_learning cadence tetap (bukan dari sini).';
