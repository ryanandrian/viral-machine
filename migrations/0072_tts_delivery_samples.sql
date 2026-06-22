-- 0072 — F4-01: observability TTS — sample delivery per render (pondasi kalibrasi pace F5-01)
-- ============================================================================
-- Tiap render TTS sukses → 1 baris (provider, voice, speed, words, audio_secs, preset). Dipakai
-- F5-01 untuk hitung wps efektif per voice_key×speed (EWMA) → ganti seed P=1.97 (akurasi durasi).
-- Internal observability: service_role-only (worker tulis); anon/authenticated revoke. Additive,
-- nol perubahan perilaku produksi.
-- ============================================================================
create table if not exists tts_delivery_samples (
  id          bigserial primary key,
  tenant_id   text,
  channel_id  text,
  niche       text,
  provider    text,
  voice_key   text,
  speed       numeric,
  words       integer,
  audio_secs  numeric,
  preset      integer,
  created_at  timestamptz not null default now()
);
create index if not exists idx_tts_samples_voice on tts_delivery_samples (voice_key, speed);
create index if not exists idx_tts_samples_created on tts_delivery_samples (created_at desc);

alter table tts_delivery_samples enable row level security;  -- tanpa policy → hanya service_role (bypass) yg akses
revoke all on tts_delivery_samples from anon, authenticated;
