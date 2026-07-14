-- 0161: [B6] F1 — jeda-akhir (trailing silence) per-PRESET durasi.
-- Masalah: trailing default 2.5s (tenant_configs.trailing_silence) = 31% dari video 8 detik.
-- Solusi: knob admin per-preset; NULL = perilaku lama (ikut setelan channel/tenant) → NOL dampak
-- pada preset existing sampai admin mengisinya. Dibaca BE mulai fase F2 (gerbang durasi + renderer).
ALTER TABLE duration_presets
  ADD COLUMN IF NOT EXISTS trailing_silence_override numeric
  CHECK (trailing_silence_override IS NULL OR (trailing_silence_override >= 0 AND trailing_silence_override <= 10));

COMMENT ON COLUMN duration_presets.trailing_silence_override IS
  '[B6] Jeda akhir (detik) khusus preset ini; NULL = ikut trailing_silence channel/tenant. Preset ultra-pendek (8s) disarankan ~1.0.';

-- Nilai awal utk preset 8s (preset masih is_active=false — tak berdampak produksi).
UPDATE duration_presets SET trailing_silence_override = 1.0 WHERE seconds = 8;
