-- Migration s81: Tambah kolom Telegram ke tenant_configs
-- Jalankan di Supabase Dashboard → SQL Editor
-- URL: https://supabase.com/dashboard/project/hiwkgxhkjanggeskjjen/sql/new

-- 1. Tambah kolom baru
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS telegram_enabled  BOOLEAN      DEFAULT true,
  ADD COLUMN IF NOT EXISTS telegram_chat_id  VARCHAR(50),
  ADD COLUMN IF NOT EXISTS channel_name      VARCHAR(100) DEFAULT '';

-- 2. Update tenant aktif: ryan_andrian
UPDATE tenant_configs
SET
  telegram_enabled = true,
  telegram_chat_id = '8699847842',
  channel_name     = 'RAD The Explorer'
WHERE tenant_id = 'ryan_andrian';

-- 3. Verifikasi
SELECT tenant_id, channel_name, telegram_enabled, telegram_chat_id
FROM tenant_configs
WHERE tenant_id = 'ryan_andrian';
