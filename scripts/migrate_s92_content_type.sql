-- s92: content_type per slot schedule — 'short' (Shorts 9:16) vs 'long' (regular 16:9)
-- Sesuai DESIGN.md 8.D.a: "Pilih Jenis Konten" adalah setting per slot di production_schedules.
-- Dipakai untuk menentukan dimensi thumbnail yang benar saat upload ke YouTube.
-- Default 'short' karena long form belum diimplementasi.

ALTER TABLE production_schedules
  ADD COLUMN IF NOT EXISTS content_type VARCHAR DEFAULT 'short';

-- Update semua slot yang ada ke 'short' (eksplisit, tidak bergantung DEFAULT)
UPDATE production_schedules
  SET content_type = 'short'
  WHERE content_type IS NULL;
