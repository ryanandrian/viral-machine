-- 0142_catalog_sweep_remaining.sql (2026-07-06)
-- Sapu TUNTAS model ber-protokol identik dari provider terdaftar (audit owner):
--   AKTIF: Gemini 2.0 Flash/Lite (protokol sama, kuota gratis harian LEBIH BESAR dari 2.5 —
--          penting utk tenant hemat) + Llama 4 Scout/Maverick di Groq (chat standar).
--   NONAKTIF ber-alasan (bukan dibuang):
--     gpt-5-nano       = reasoning family (param temperature) — ikut nasib gpt-5
--     gpt-4o-mini-tts  = audio.speech SAMA tapi dukungan param `speed` belum pasti → uji kunci dulu
--     eleven_v3        = model EL terbaru; dukungan convert_with_timestamps (kontrak adapter kita:
--                        caption karaoke) belum terverifikasi → uji kunci dulu
--   SENGAJA TIDAK diseed (protokol/kontrak BEDA — bukan kelupaan):
--     dall-e-3 (nilai param quality standard/hd ≠ low/medium/high milik pipeline)
--     deepseek-r1-distill @groq (keluaran <think> merusak kontrak JSON naskah)
begin;
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('gemini-2.0-flash',      'gemini', 'llm', 'gemini-2.0-flash',      'Gemini 2.0 Flash — gratis harian besar', 'standard', true, 33,
   '{"unit":"per_token","approx_usd":0,"note":"Kuota gratis harian AI Studio terbesar — andalan tenant hemat"}'),
  ('gemini-2.0-flash-lite', 'gemini', 'llm', 'gemini-2.0-flash-lite', 'Gemini 2.0 Flash-Lite',                  'basic',    true, 34,
   '{"unit":"per_token","approx_usd":0,"note":"Ringan & termurah; kuota gratis harian"}'),
  ('llama-4-scout',    'groq', 'llm', 'meta-llama/llama-4-scout-17b-16e-instruct',    'Llama 4 Scout (Groq)',    'standard', true, 37,
   '{"unit":"per_token","note":"Generasi Llama 4 — cepat di Groq; free tier tersedia"}'),
  ('llama-4-maverick', 'groq', 'llm', 'meta-llama/llama-4-maverick-17b-128e-instruct', 'Llama 4 Maverick (Groq)', 'standard', true, 38,
   '{"unit":"per_token","note":"Llama 4 terkuat di Groq; free tier tersedia"}'),
  ('gpt-5-nano', 'openai', 'llm', 'gpt-5-nano', 'GPT-5 Nano', 'basic', false, 23,
   '{"unit":"per_token","note":"NONAKTIF: reasoning family menolak param temperature adapter — ikut gpt-5"}'),
  ('gpt-4o-mini-tts', 'openai_tts', 'tts', 'gpt-4o-mini-tts', 'GPT-4o Mini TTS', 'standard', false, 42,
   '{"unit":"per_char","note":"NONAKTIF: dukungan param speed belum pasti — uji kunci dulu"}'),
  ('eleven_v3', 'elevenlabs', 'tts', 'eleven_v3', 'ElevenLabs v3', 'premium', false, 43,
   '{"unit":"per_char","note":"NONAKTIF: word-timestamps (kontrak caption karaoke) belum terverifikasi di v3 — uji kunci dulu"}')
on conflict (model_key) do nothing;
commit;
