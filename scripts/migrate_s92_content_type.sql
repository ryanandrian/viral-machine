-- s92: content_type per tenant — short (Shorts 9:16) vs long (regular 16:9)
-- Dipakai untuk menentukan dimensi thumbnail yang benar saat upload ke YouTube.
-- Default 'short' karena long form belum diimplementasi.

ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS content_type VARCHAR DEFAULT 'short';

-- Update semua tenant yang ada ke 'short' (eksplisit, tidak bergantung DEFAULT)
UPDATE tenant_configs
  SET content_type = 'short'
  WHERE content_type IS NULL;
