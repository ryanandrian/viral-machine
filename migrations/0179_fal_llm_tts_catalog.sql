-- 0179 — fal.ai sebagai jalur alternatif untuk NASKAH & SUARA (didaftarkan NONAKTIF)
--
-- Tujuan: tenant yang sudah punya kunci fal (untuk gambar & video) bisa memakai kunci yang SAMA
-- untuk penulis naskah dan pengisi suara — tanpa kunci OpenAI/Anthropic/ElevenLabs terpisah.
--
-- SEMUA baris di sini is_active = FALSE. Selama nonaktif, model TIDAK MUNCUL di layar tenant dan
-- secara teknis tak bisa dipilih — jadi produksi yang sedang berjalan mustahil terpengaruh.
-- Diaktifkan hanya setelah terbukti lewat uji rantai penuh sampai video jadi.
--
-- Pola penyedia meniru pasangan `openai` + `openai_tts` yang sudah ada: penyedia terpisah per
-- protokol, tapi key_group SAMA ('fal') sehingga kunci fal milik tenant otomatis terpakai — tenant
-- tidak perlu memasukkan kunci baru.
--
-- Harga (endpoint resmi fal, diperiksa 2026-07-28):
--   any-llm                        $0,001 per PERMINTAAN  (bukan per token)
--   elevenlabs/tts/turbo-v2.5      $0,05 per 1.000 karakter
--   elevenlabs/tts/multilingual-v2 $0,10 per 1.000 karakter

BEGIN;

-- 1) Penyedia: naskah & suara lewat fal (kunci berbagi dgn penyedia visual `fal`).
INSERT INTO ai_providers (provider_key, display_name, adapter, auth_type, key_group, is_active)
VALUES
  ('fal_llm', 'fal.ai — Penulis Naskah', 'fal_any_llm', 'api_key', 'fal', FALSE),
  ('fal_tts', 'fal.ai — Pengisi Suara',  'fal_tts',     'api_key', 'fal', FALSE)
ON CONFLICT (provider_key) DO NOTHING;

-- 2) Profil TTS: adapter protokol dibaca dari sini (bukan hardcode di kode).
--    tts_class='timed' + has_word_timeframe=TRUE: fal meneruskan penanda waktu ElevenLabs
--    (per karakter → digabung jadi per kata oleh adaptor), jadi sekelas ElevenLabs langsung —
--    BUKAN 'fast_fallback' seperti penyedia yang timing-nya diperkirakan.
--    delivery_wps 1.97 = angka ElevenLabs; modelnya memang model yang sama, hanya lewat fal.
INSERT INTO tts_profiles (provider_key, display_name, adapter, tts_class, delivery_wps,
                          has_word_timeframe, speed_param, is_active)
VALUES ('fal_tts', 'fal.ai (ElevenLabs)', 'fal_tts', 'timed', 1.97, TRUE, 'speed', FALSE)
ON CONFLICT (provider_key) DO NOTHING;

-- 3) Model NASKAH — hanya yang TERBUKTI jalan pada uji nyata 2026-07-28.
--    Yang ditolak & sengaja TIDAK didaftarkan: deepseek-v3.1-terminus (37,7 dtk — sepuluh kali
--    lebih lambat), gpt-5-nano (menolak jalan tanpa mode penalaran), claude-3-5-haiku (404).
INSERT INTO ai_models (model_key, model_id, provider_key, component, display_name, quality_tier, cost_hint, is_active, sort_order, pricing)
VALUES
  ('anthropic/claude-haiku-4.5', 'anthropic/claude-haiku-4.5', 'fal_llm', 'llm', 'Claude Haiku 4.5 (via fal)', 'fast', '{"unit":"per_request","approx_usd":0.001,"audit":"LULUS uji nyata fal 2026-07-28 (4,2 dtk, JSON via parser toleran)"}'::jsonb, FALSE, 10,
   '{"source":"manual","per_request_usd":0.001,"note":"fal any-llm: tarif per permintaan, bukan per token (cek 2026-07-28). Uji nyata 4,2 dtk."}'::jsonb),
  ('google/gemini-2.5-flash', 'google/gemini-2.5-flash', 'fal_llm', 'llm', 'Gemini 2.5 Flash (via fal)', 'standard', '{"unit":"per_request","approx_usd":0.001,"audit":"LULUS uji nyata fal 2026-07-28 (3,5 dtk — tercepat)"}'::jsonb, FALSE, 20,
   '{"source":"manual","per_request_usd":0.001,"note":"fal any-llm: tarif per permintaan. Uji nyata 3,5 dtk — tercepat."}'::jsonb),
  ('openai/gpt-4o-mini', 'openai/gpt-4o-mini', 'fal_llm', 'llm', 'GPT-4o mini (via fal)', 'fast', '{"unit":"per_request","approx_usd":0.001,"audit":"LULUS uji nyata fal 2026-07-28 (6,8 dtk, JSON langsung bersih)"}'::jsonb, FALSE, 30,
   '{"source":"manual","per_request_usd":0.001,"note":"fal any-llm: tarif per permintaan. Uji nyata 6,8 dtk — JSON paling patuh."}'::jsonb)
ON CONFLICT (model_key) DO NOTHING;

-- 4) Model SUARA — penanda waktu per karakter fal digabung jadi per kata oleh adaptor,
--    sehingga presisi karaoke setara ElevenLabs langsung (terverifikasi 2026-07-28).
INSERT INTO ai_models (model_key, model_id, provider_key, component, display_name, quality_tier, cost_hint, is_active, sort_order, pricing)
VALUES
  ('fal-ai/elevenlabs/tts/turbo-v2.5', 'fal-ai/elevenlabs/tts/turbo-v2.5', 'fal_tts', 'tts', 'ElevenLabs Turbo v2.5 (via fal)', 'fast', '{"unit":"per_request","approx_usd":0.001,"audit":"LULUS uji nyata fal 2026-07-28 (4,2 dtk, JSON via parser toleran)"}'::jsonb, FALSE, 10,
   '{"source":"manual","per_1m_chars":50.0,"note":"fal $0,05 per 1.000 karakter (cek 2026-07-28) — separuh harga multilingual."}'::jsonb),
  ('fal-ai/elevenlabs/tts/multilingual-v2', 'fal-ai/elevenlabs/tts/multilingual-v2', 'fal_tts', 'tts', 'ElevenLabs Multilingual v2 (via fal)', 'premium', '{"unit":"per_1k_chars","approx_usd":0.10,"audit":"harga resmi fal 2026-07-28; belum diuji panggil"}'::jsonb, FALSE, 20,
   '{"source":"manual","per_1m_chars":100.0,"note":"fal $0,10 per 1.000 karakter (cek 2026-07-28)."}'::jsonb)
ON CONFLICT (model_key) DO NOTHING;

COMMIT;
