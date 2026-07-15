-- 0162: [DURASI-F1] INSTRUMENTASI tts_delivery_samples — buat error estimator TERUKUR per render.
-- Masalah: sampel lama hanya simpan (words, audio_secs, speed, niche, voice, preset) → TIDAK bisa
-- membandingkan TAKSIRAN model vs AKTUAL, dan tidak bisa memvalidasi model-jeda (teks tak tersimpan).
-- Akibatnya kalibrasi pace (F2) = tebakan. Kolom di bawah membuat semua itu terukur dari data nyata.
-- Semua NULLABLE + additif → baris lama tetap NULL, NOL dampak baca lain (hanya tts_engine yang menulis tabel ini).
--   • predicted_secs  = taksiran model (_duration_est.est_seconds) → banding vs raw_audio_secs = ERROR estimator
--   • raw_audio_secs  = durasi audio MENTAH sebelum atempo/_fit_duration (pembanding sah; audio_secs = SETELAH koreksi)
--   • target_secs     = target audio (preset − trailing) → meleset langsung terhitung
--   • pause_secs      = jeda yang model taksir (_duration_est.pause_seconds)
--   • pause_counts    = rincian tanda-jeda dari teks {em_dash,ellipsis,sentence,comma,linebreak} → validasi/kalibrasi model-jeda (F2)
ALTER TABLE tts_delivery_samples
  ADD COLUMN IF NOT EXISTS predicted_secs numeric,
  ADD COLUMN IF NOT EXISTS raw_audio_secs numeric,
  ADD COLUMN IF NOT EXISTS target_secs    numeric,
  ADD COLUMN IF NOT EXISTS pause_secs     numeric,
  ADD COLUMN IF NOT EXISTS pause_counts   jsonb;
