-- 0136_free_tier_providers.sql (2026-07-06)
-- JALUR TENANT HEMAT (owner): provider AI ber-KREDIT GRATIS HARIAN, kompatibel pipeline.
--   LLM  : Gemini (Google AI Studio) + Groq (Llama 3.3 70B) — endpoint OpenAI-compatible
--          → adapter openai_chat + base_url (NOL kode; by-design adapters.py).
--   TTS  : sudah ada = edge_tts (gratis, tanpa kunci).
--   Image: Together AI FLUX schnell Free — protokol images OpenAI-compatible (patch base_url
--          di ai_image). Model DISEED NONAKTIF sampai lulus uji kunci nyata (anti-bug; aktivasi
--          via admin catalog setelah tes video sukses).
-- Catatan produk: free-tier ada rate/kuota harian & data dapat dipakai provider utk pelatihan —
-- cocok tenant 1-2 video/hari; display_name menandai "(gratis harian)" agar jujur di UI.

begin;

insert into ai_providers (provider_key, display_name, adapter, base_url, auth_type, key_group, is_active) values
  ('gemini',   'Google Gemini (AI Studio)', 'openai_chat',
   'https://generativelanguage.googleapis.com/v1beta/openai/', 'api_key', 'gemini',   true),
  ('groq',     'Groq',                      'openai_chat',
   'https://api.groq.com/openai/v1',                           'api_key', 'groq',     true),
  ('together', 'Together AI',               'openai_images',
   'https://api.together.xyz/v1',                              'api_key', 'together', true)
on conflict (provider_key) do nothing;

insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('gemini-2.5-flash', 'gemini', 'llm', 'gemini-2.5-flash',
   'Gemini 2.5 Flash — gratis harian', 'standard', true, 30,
   '{"unit":"per_token","approx_usd":0,"note":"GRATIS — kuota harian Google AI Studio; rate-limit berlaku; data dapat dipakai Google"}'),
  ('llama-3.3-70b-versatile', 'groq', 'llm', 'llama-3.3-70b-versatile',
   'Llama 3.3 70B (Groq) — gratis harian', 'standard', true, 31,
   '{"unit":"per_token","approx_usd":0,"note":"GRATIS — kuota harian Groq free tier; rate-limit berlaku"}'),
  ('flux-schnell-free', 'together', 'image', 'black-forest-labs/FLUX.1-schnell-Free',
   'FLUX Schnell (Together) — gratis', 'basic', false, 30,
   '{"unit":"per_image","approx_usd":0,"note":"GRATIS — free tier Together AI; NONAKTIF s.d. lulus uji kunci nyata (admin)"}')
on conflict (model_key) do nothing;

commit;
