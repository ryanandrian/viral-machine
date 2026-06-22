-- 0081 — F5-01 fondasi: pace PER-VOICE di voice_catalog (no-hardcode voice; tiap voice deskripsikan dirinya).
-- delivery_wps voice = kata/detik efektif @speed 1.0 (satuan SAMA dgn tts_profiles.delivery_wps tapi level VOICE).
-- Resolusi estimator: voice_catalog.delivery_wps (bila NOT NULL & ∈[1.0,4.0]) → tts_profiles[provider].delivery_wps
-- (fallback engine) → 2.4 (default). NULL = "ikut engine" = perilaku sekarang PERSIS (non-breaking).
-- Admin set/RESET-ke-NULL via Catalog>Voice. F5-01 (nanti) tulis otomatis dari tts_delivery_samples.
alter table voice_catalog
  add column if not exists delivery_wps    numeric,                     -- pace voice (NULL=ikut engine). guard [1.0,4.0] di app.
  add column if not exists pace_sample_n   integer not null default 0,  -- jumlah sampel pembentuk (F5-01 percaya bila ≥ ambang)
  add column if not exists pace_updated_at timestamptz,                 -- kapan terakhir dikalibrasi
  add column if not exists pace_locked     boolean not null default false; -- true = admin kunci → F5-01 JANGAN timpa otomatis

comment on column voice_catalog.delivery_wps is 'Pace voice (kata/dtk @speed 1.0). NULL = pakai default engine (tts_profiles.delivery_wps). Override per-voice (mis. Arnold lebih cepat) — DATA, bukan hardcode. Guard app [1.0,4.0]. F5-01 isi otomatis (kecuali pace_locked).';
