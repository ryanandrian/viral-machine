-- 0166: [owner 2026-07-16 b] diskon promo BER-TANGGAL-KEDALUWARSA — tenant_configs.discount_until.
-- Kosong (NULL) = diskon tanpa batas (perilaku lama persis). Terisi & lewat → diskon EFEKTIF = 0
-- (dihormati checkout + comp-check + sweep renewal via limits.effective_discount_pct — satu sumber).
-- Kebutuhan: promosi tenant-tenant pertama beberapa bulan tanpa risiko lupa menol-kan manual.
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS discount_until timestamptz;
