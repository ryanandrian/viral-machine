-- 0014 — TTS Profiles: kelas TTS + delivery WPS NYATA (per arahan owner: 2 kelas TTS).
-- Memecahkan issue F2d (budget over-estimate krn §3 WPS=2.4 ≠ delivery nyata):
-- word-budget = target_detik × effective_wps, di mana effective_wps = delivery rate PROVIDER.
-- Config-driven (admin tambah provider = 1 row). delivery_wps = ESTIMATE awal, KALIBRASI via data
-- nyata (§3 "angka awal, A/B saat live") — paling akurat saat ElevenLabs aktif.

CREATE TABLE IF NOT EXISTS tts_profiles (
  provider_key       TEXT PRIMARY KEY,        -- cocok tts_provider: elevenlabs, edge_tts, openai_tts, ...
  tts_class          TEXT NOT NULL,           -- 'timed' (word-timeframe, default/rekomendasi) | 'fast_fallback'
  delivery_wps       NUMERIC NOT NULL,        -- kata/detik delivery NYATA (sumber word-budget; kalibrasi via data)
  has_word_timeframe BOOLEAN DEFAULT false,   -- timestamp word-level akurat (caption karaoke presisi)?
  speed_param        TEXT,                    -- knob closed-loop speed-adjust: 'speed'|'rate'|NULL(tak didukung)
  is_active          BOOLEAN DEFAULT true,
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tts_profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tts_profiles_read ON tts_profiles;
CREATE POLICY tts_profiles_read ON tts_profiles FOR SELECT USING (true);

-- Seed (delivery_wps = estimate awal dari log V1/test; kalibrasi via data nyata)
INSERT INTO tts_profiles (provider_key, tts_class, delivery_wps, has_word_timeframe, speed_param) VALUES
  ('elevenlabs', 'timed',         1.8, true,  'speed'),   -- default/rekomendasi; word-timeframe akurat; speed-adjust ✓
  ('edge_tts',   'fast_fallback', 2.6, false, 'rate'),    -- opt-in fallback (§4b); timestamp aproksimasi; rate-adjust ✓
  ('openai_tts', 'fast_fallback', 2.6, false, NULL)       -- tak ada param speed → di-exclude closed-loop (§0)
ON CONFLICT (provider_key) DO NOTHING;
