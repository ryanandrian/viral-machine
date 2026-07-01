-- 0109 — Knob siklus penagihan (app_config) — SEMUA admin-editable via System Configuration (no-hardcode).
-- Muncul otomatis di /admin/app-config (editor app_config generik). Angka = default best-practice.
INSERT INTO app_config (key, value, description) VALUES
  ('billing_grace_days', 7,
   'Masa tenggang (hari) setelah langganan berakhir — mesin MASIH jalan sambil menunggu pembayaran, sebelum dihentikan.'),
  ('trial_reminder_days_before', 1,
   'Kirim email pengingat upgrade berapa HARI SEBELUM masa trial berakhir (0 = matikan pengingat trial).'),
  ('renewal_reminder_days_before', 3,
   'Kirim email pengingat perpanjangan berapa HARI SEBELUM langganan berbayar berakhir (0 = matikan).'),
  ('checkout_expiry_hours', 24,
   'Berapa JAM link pembayaran Midtrans berlaku sebelum kedaluwarsa.')
ON CONFLICT (key) DO NOTHING;

-- Penanda anti-kirim-ulang reminder (per-tenant, per-siklus). NULL = belum dikirim untuk siklus berjalan.
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS trial_reminder_sent_at   timestamptz,
  ADD COLUMN IF NOT EXISTS renewal_reminder_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS suspend_notified_at      timestamptz;

COMMENT ON COLUMN tenant_configs.trial_reminder_sent_at   IS 'Kapan pengingat H-x trial terakhir dikirim (anti-dobel).';
COMMENT ON COLUMN tenant_configs.renewal_reminder_sent_at IS 'Kapan pengingat perpanjangan terakhir dikirim (di-reset saat siklus baru/aktivasi).';
COMMENT ON COLUMN tenant_configs.suspend_notified_at      IS 'Kapan notifikasi suspend dikirim (anti-dobel).';
