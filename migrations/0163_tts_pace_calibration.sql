-- 0163: [DURASI-F2] tabel kalibrasi pace per (voice × niche) — dari render NYATA (tts_delivery_samples).
-- Kenapa tabel BARU (bukan kolom di voice_catalog): granularitas niche (data 2026-07-15: voice SAMA
-- beda niche pace nyata beda s/d 25% — Ardi: legenda 2.53 vs radiant 2.00 wps). voice_catalog tetap
-- lapisan per-voice milik ADMIN (pace_locked dihormati: voice terkunci TIDAK ditulis/dibaca kalibrasi).
-- Konsumsi (F2 langkah-2, script_engine): (voice×niche) → voice_catalog.delivery_wps → tts_profiles.
-- Tabel KOSONG = perilaku lama persis (nol regresi). niche '*' = agregat per-voice (fallback tengah).
-- Penulis: HANYA src/production/pace_calibration.py (worker, service_role). FE tidak membaca tabel ini.
CREATE TABLE IF NOT EXISTS tts_pace_calibration (
  voice_key    text        NOT NULL,
  niche        text        NOT NULL DEFAULT '*',
  delivery_wps numeric     NOT NULL CHECK (delivery_wps >= 1.0 AND delivery_wps <= 4.0),  -- guard = rentang admin voice_catalog
  sample_n     integer     NOT NULL CHECK (sample_n > 0),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (voice_key, niche)
);
ALTER TABLE tts_pace_calibration ENABLE ROW LEVEL SECURITY;  -- worker pakai service_role (bypass); tanpa policy = tertutup utk anon/authenticated
