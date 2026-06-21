-- 0073 — Tier-Plan config-driven (owner 2026-06-21): nama tier + fasilitas Niche Studio per-tier,
-- adjustable di Admin tanpa redeploy (no-hardcode). Melengkapi knob yang SUDAH config-driven:
--   • harga/bln  → pricing_config (plan_starter/pro/business; admin Pricing, +audit/rollback)
--   • channel    → plan_limits.max_channels (admin Pricing "Batas paket")
--   • video/hari → plan_limits.max_videos_per_day (admin Pricing "Batas paket")
--   • trial hari → app_config.trial_duration_days (admin-editable, public-read)
-- Yang DITAMBAH di sini (sebelumnya hardcode di FE):
--   • display_name → nama tier yang dilihat pelanggan (Landing/Billing/sidebar)
--   • niche_studio → saklar fasilitas Niche Studio PER-TIER (ganti app_config.niche_studio_min_rank
--                    yang berbasis-rank global → kini boolean per-tier, lebih fleksibel)
--   • sort_order   → urutan tampil tier (Landing/Admin)
-- Aditif + backfill = perilaku sekarang DIPERTAHANKAN (nol perubahan sampai admin mengubah nilai).
-- plan_limits RLS = public-read (verified) → Landing (anon) bisa render dari sini.
-- ============================================================================
alter table plan_limits add column if not exists display_name text;
alter table plan_limits add column if not exists niche_studio boolean not null default false;
alter table plan_limits add column if not exists sort_order   integer not null default 0;

-- Backfill = state sekarang (nama kapital + Niche Studio hanya Business, sesuai niche_studio_min_rank=3)
update plan_limits set display_name = 'Trial',    sort_order = 0, niche_studio = false where plan_type = 'trial';
update plan_limits set display_name = 'Starter',  sort_order = 1, niche_studio = false where plan_type = 'starter';
update plan_limits set display_name = 'Pro',      sort_order = 2, niche_studio = false where plan_type = 'pro';
update plan_limits set display_name = 'Business', sort_order = 3, niche_studio = true  where plan_type = 'business';
