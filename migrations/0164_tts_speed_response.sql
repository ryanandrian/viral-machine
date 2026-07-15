-- 0164: [DURASI-F2] faktor respons-speed per provider TTS — dari render NYATA.
-- TEMUAN (regresi log-log 45 render EL, R²=0.80): ElevenLabs MELEBIH-LEBIHKAN perintah speed
-- (α≈1.32: diminta 0.8× jadi lebih pelan dari 0.8×; 1.2× jadi lebih cepat). Edge α≈1.02 (patuh).
-- Estimator lama berasumsi α=1 (patuh penuh) → sisa error di niche yang speed-nya bervariasi.
-- Model estimator (script_engine): speech = words / (delivery_wps × _PAUSE_INFLATION × speed^α).
-- Tabel KOSONG / provider tak ada → α=1.0 = perilaku lama persis (nol regresi).
-- Penulis: HANYA src/production/pace_calibration.py (worker, service_role). FE tidak membaca.
CREATE TABLE IF NOT EXISTS tts_speed_response (
  provider   text        PRIMARY KEY,
  alpha      numeric     NOT NULL CHECK (alpha >= 0.5 AND alpha <= 2.0),  -- pagar teknis: di luar ini = data rusak, tolak di penulis
  sample_n   integer     NOT NULL CHECK (sample_n > 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE tts_speed_response ENABLE ROW LEVEL SECURITY;
