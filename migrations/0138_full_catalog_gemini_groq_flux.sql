-- 0138_full_catalog_gemini_groq_flux.sql (2026-07-06)
-- KATALOG LENGKAP provider baru (owner: jangan hanya yang gratis — semua model ber-protokol
-- kompatibel ditampilkan; tenant yang memilih gratis vs premium).
--   LLM Gemini/Groq: protokol chat OpenAI-compatible teruji standar → AKTIF.
--   Image Together (FLUX schnell/dev/1.1-pro): protokol images kompatibel tapi transport kita
--     BELUM teruji kunci nyata → NONAKTIF (konsisten flux-schnell-free; aktivasi 1 klik pasca-uji).
--   TTS Groq (PlayAI, protokol OpenAI audio.speech + base_url — patch openai_tts): NONAKTIF
--     s.d. uji + kalibrasi delivery_wps.
--   Gemini TTS/Image(Imagen)/Video(Veo): protokol Google generateContent ≠ adapter kita —
--     TIDAK diseed (butuh adapter baru; item terpisah, jangan seed yang pasti tak jalan).

begin;

-- LLM Gemini (pelengkap gemini-2.5-flash yang sudah ada)
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('gemini-3-pro-preview', 'gemini', 'llm', 'gemini-3-pro-preview',
   'Gemini 3 Pro (Preview)', 'premium', true, 28,
   '{"unit":"per_token","note":"Premium — flagship Google; berbayar (ada kuota preview terbatas)"}'),
  ('gemini-2.5-pro', 'gemini', 'llm', 'gemini-2.5-pro',
   'Gemini 2.5 Pro', 'premium', true, 29,
   '{"unit":"per_token","note":"Premium — penalaran terkuat keluarga 2.5; berbayar"}'),
  ('gemini-2.5-flash-lite', 'gemini', 'llm', 'gemini-2.5-flash-lite',
   'Gemini 2.5 Flash-Lite — hemat', 'basic', true, 32,
   '{"unit":"per_token","approx_usd":0,"note":"Paling hemat; termasuk kuota gratis harian AI Studio"}')
on conflict (model_key) do nothing;

-- LLM Groq (pelengkap llama-3.3-70b-versatile)
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('openai-gpt-oss-120b', 'groq', 'llm', 'openai/gpt-oss-120b',
   'GPT-OSS 120B (Groq)', 'standard', true, 33,
   '{"unit":"per_token","note":"Model terbuka OpenAI di Groq — cepat; free tier tersedia"}'),
  ('openai-gpt-oss-20b', 'groq', 'llm', 'openai/gpt-oss-20b',
   'GPT-OSS 20B (Groq) — cepat', 'basic', true, 34,
   '{"unit":"per_token","approx_usd":0,"note":"Ringan & sangat cepat; free tier tersedia"}'),
  ('llama-3.1-8b-instant', 'groq', 'llm', 'llama-3.1-8b-instant',
   'Llama 3.1 8B Instant (Groq)', 'basic', true, 35,
   '{"unit":"per_token","approx_usd":0,"note":"Tercepat & termurah; free tier tersedia"}'),
  ('kimi-k2-instruct', 'groq', 'llm', 'moonshotai/kimi-k2-instruct',
   'Kimi K2 (Groq)', 'standard', true, 36,
   '{"unit":"per_token","note":"Kualitas penulisan kuat; free tier terbatas"}')
on conflict (model_key) do nothing;

-- Image Together — keluarga FLUX penuh (NONAKTIF s.d. transport lulus uji kunci nyata)
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('flux-schnell', 'together', 'image', 'black-forest-labs/FLUX.1-schnell',
   'FLUX.1 Schnell (Together)', 'standard', false, 31,
   '{"unit":"per_image","approx_usd":0.0027,"note":"Cepat & murah; NONAKTIF s.d. lulus uji kunci nyata"}'),
  ('flux-dev', 'together', 'image', 'black-forest-labs/FLUX.1-dev',
   'FLUX.1 Dev (Together)', 'premium', false, 32,
   '{"unit":"per_image","approx_usd":0.025,"note":"Kualitas tinggi; NONAKTIF s.d. lulus uji kunci nyata"}'),
  ('flux-1.1-pro', 'together', 'image', 'black-forest-labs/FLUX.1.1-pro',
   'FLUX 1.1 Pro (Together)', 'premium', false, 33,
   '{"unit":"per_image","approx_usd":0.04,"note":"Flagship FLUX; NONAKTIF s.d. lulus uji kunci nyata"}')
on conflict (model_key) do nothing;

-- TTS Groq (PlayAI — protokol OpenAI audio.speech via base_url; patch openai_tts 2026-07-06)
insert into tts_profiles (provider_key, display_name, adapter, tts_class, delivery_wps, has_word_timeframe, speed_param, is_active, param_schema) values
  ('groq', 'Groq PlayAI TTS', 'openai_speech', 'fast_fallback', 2.5, false, 'speed', true, '{"speed":[0.5,2.0]}')
on conflict (provider_key) do nothing;
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('playai-tts', 'groq', 'tts', 'playai-tts',
   'PlayAI TTS (Groq)', 'standard', false, 40,
   '{"unit":"per_char","note":"Free tier tersedia; NONAKTIF s.d. uji + kalibrasi tempo"}')
on conflict (model_key) do nothing;
insert into voice_catalog (voice_key, provider_key, display_name, locale, language, gender, is_active, sort_order) values
  ('Fritz-PlayAI',  'groq', 'Fritz (PlayAI)',  'en-US', 'English', 'male',   true, 120),
  ('Arista-PlayAI', 'groq', 'Arista (PlayAI)', 'en-US', 'English', 'female', true, 121)
on conflict (voice_key) do nothing;

commit;
