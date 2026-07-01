-- 0113 — LIFECYCLE & NURTURE (B9): kolom penanda siklus-hidup + knob app_config (NO-HARDCODE).
-- Additive & nullable → aman, reversible, nol dampak ke perilaku existing (kolom baru tak dibaca sampai BE siap).
-- Sumber kebenaran = LIFECYCLE_NURTURE_ARCHITECTURE.md §3 (knob) + §4.1 (kolom). Status baru subscription_status
-- ('blocked','deleted') = TEXT tanpa CHECK → tak perlu ALTER constraint.

-- ── §4.1 Penanda lifecycle di tenant_configs (semua nullable; anti-dobel & audit) ──
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS lead_temp                text,          -- 'hot' | 'warm' | 'cold' (dihitung saat trial_expired)
  ADD COLUMN IF NOT EXISTS nurture_step             int DEFAULT 0, -- langkah sekuens nurture terakhir terkirim (anti-dobel)
  ADD COLUMN IF NOT EXISTS nurture_last_sent_at     timestamptz,
  ADD COLUMN IF NOT EXISTS suspended_at             timestamptz,   -- kapan masuk suspended (mulai hitung window)
  ADD COLUMN IF NOT EXISTS blocked_at               timestamptz,   -- kapan akun dikunci (blocked)
  ADD COLUMN IF NOT EXISTS deletion_scheduled_at    timestamptz,   -- tanggal hapus data terjadwal
  ADD COLUMN IF NOT EXISTS raw_assets_purged_at     timestamptz,   -- kapan file video mentah S3 dihapus dini
  ADD COLUMN IF NOT EXISTS winback_offer_pct        int,           -- % diskon comeback aktif utk tenant ini (null=none)
  ADD COLUMN IF NOT EXISTS winback_offer_expires_at timestamptz,   -- kedaluwarsa diskon comeback
  ADD COLUMN IF NOT EXISTS deletion_warn_sent       int DEFAULT 0; -- bitmask/counter langkah peringatan hapus terkirim

-- ── §3 Knob app_config (admin-editable via System Configuration; value integer, no-hardcode) ──
INSERT INTO app_config (key, value, description) VALUES
  ('nurture_enabled',                1,  'Master ON/OFF mesin tindak-lanjut (nurture) trial-lapse. 1=nyala, 0=mati.'),
  ('nurture_trial_extend_days',      3,  'Perpanjang trial 1-klik dari email (hari). 0 = matikan tuas ini.'),
  ('winback_discount_pct',           0,  'Diskon comeback bulan pertama utk lead lapsed (%). 0 = matikan (harga normal).'),
  ('winback_discount_valid_days',    3,  'Masa berlaku diskon comeback sejak ditawarkan (hari) — ciptakan urgensi.'),
  ('nurture_step1_days',             2,  'Email nurture ke-1: dikirim H+x hari setelah trial habis.'),
  ('nurture_step2_days',             5,  'Email nurture ke-2: H+x hari setelah trial habis.'),
  ('nurture_step3_days',             9,  'Email nurture ke-3: H+x hari setelah trial habis.'),
  ('nurture_step4_days',             16, 'Email nurture ke-4: H+x hari setelah trial habis.'),
  ('nurture_step5_days',             30, 'Email nurture ke-5 (terakhir): H+x hari setelah trial habis.'),
  ('suspend_window_days',            30, 'Lama status "suspended" (produksi stop, data utuh, bisa aktif-lagi) sebelum akun dikunci (blocked).'),
  ('suspend_dunning1_days',          0,  'Email penagihan suspended ke-1: H+x hari setelah masuk suspended.'),
  ('suspend_dunning2_days',          7,  'Email penagihan suspended ke-2: H+x hari setelah masuk suspended.'),
  ('suspend_dunning3_days',          14, 'Email penagihan suspended ke-3: H+x hari setelah masuk suspended.'),
  ('suspend_dunning4_days',          21, 'Email penagihan suspended ke-4: H+x hari setelah masuk suspended.'),
  ('suspend_dunning5_days',          28, 'Email penagihan suspended ke-5: H+x hari setelah masuk suspended.'),
  ('block_retention_days',           30, 'Lama data disimpan setelah akun dikunci (blocked) sebelum DIHAPUS permanen (hari).'),
  ('deletion_warn1_days',            30, 'Peringatan hapus ke-1: H-x hari sebelum penghapusan data.'),
  ('deletion_warn2_days',            7,  'Peringatan hapus ke-2: H-x hari sebelum penghapusan data.'),
  ('deletion_warn3_days',            1,  'Peringatan hapus ke-3 (terakhir): H-x hari sebelum penghapusan data.'),
  ('s3_raw_purge_after_suspend_days',0,  'Hapus file video mentah di storage setelah masuk suspended (hari). 0 = segera (video sudah aman di YouTube).')
ON CONFLICT (key) DO NOTHING;
