-- 0143_model_audit_2026-07-06.sql
-- REKAM audit vendor+model AI 2026-07-06 (mandat owner 4-butir).
-- Setiap model aktif DIEKSEKUSI NYATA lewat adapter produksi (build_llm_provider /
-- build_tts_provider / AIImageProvider) memakai kunci pool tenant. Bukan asumsi.
-- Hasil disimpan permanen di cost_hint.audit (tahan compaction).
--   22 AKTIF (LULUS) : 12 LLM, 8 TTS, 2 gambar.
--   10 NONAKTIF     : 4 Claude (tanpa kunci), 4 Gemini (429 kuota), 2 Replicate (402 kredit).
-- Mutasi ini SEBELUMNYA diterapkan langsung ke DB live; file ini merekamnya sesuai konvensi repo.
-- Idempoten: keyed by model_key, merge cost_hint (kunci lain dipertahankan).

BEGIN;

-- [AKTIF ] gpt-image-1
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-image-1';

-- [AKTIF ] gpt-image-1-mini
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-image-1-mini';

-- [AKTIF ] gemini-2.5-flash
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gemini-2.5-flash';

-- [AKTIF ] gemini-2.5-flash-lite
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gemini-2.5-flash-lite';

-- [AKTIF ] gpt-4.1
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4.1';

-- [AKTIF ] gpt-4.1-mini
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4.1-mini';

-- [AKTIF ] gpt-4.1-nano
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4.1-nano';

-- [AKTIF ] gpt-4o
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4o';

-- [AKTIF ] gpt-4o-mini
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4o-mini';

-- [AKTIF ] llama-3.1-8b-instant
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'llama-3.1-8b-instant';

-- [AKTIF ] llama-3.3-70b-versatile
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'llama-3.3-70b-versatile';

-- [AKTIF ] llama-4-scout
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'llama-4-scout';

-- [AKTIF ] openai-gpt-oss-120b
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'openai-gpt-oss-120b';

-- [AKTIF ] openai-gpt-oss-20b
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'openai-gpt-oss-20b';

-- [AKTIF ] edge-neural
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
  , pricing = '{"source": "manual", "in_per_1m": null, "per_image": null, "synced_at": "2026-07-06T00:00:00Z", "out_per_1m": null, "per_1m_chars": 0}'::jsonb
  , pricing_locked = true
WHERE model_key = 'edge-neural';

-- [AKTIF ] eleven_flash_v2_5
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'eleven_flash_v2_5';

-- [AKTIF ] eleven_multilingual_v2
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'eleven_multilingual_v2';

-- [AKTIF ] eleven_turbo_v2_5
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'eleven_turbo_v2_5';

-- [AKTIF ] eleven_v3
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'eleven_v3';

-- [AKTIF ] gpt-4o-mini-tts
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'gpt-4o-mini-tts';

-- [AKTIF ] tts-1
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'tts-1';

-- [AKTIF ] tts-1-hd
UPDATE ai_models SET
  is_active = true,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','LULUS uji adapter produksi 2026-07-06')
WHERE model_key = 'tts-1-hd';

-- [NONAKT] flux-schnell
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 402 kredit Replicate habis (auth OK) — topup utk uji')
WHERE model_key = 'flux-schnell';

-- [NONAKT] stable-diffusion
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 402 kredit Replicate habis (auth OK) — topup utk uji')
WHERE model_key = 'stable-diffusion';

-- [NONAKT] claude-haiku-4-5-20251001
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: kunci Anthropic tidak ada di pool — belum bisa dibuktikan')
WHERE model_key = 'claude-haiku-4-5-20251001';

-- [NONAKT] claude-opus-4-8
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: kunci Anthropic tidak ada di pool — belum bisa dibuktikan')
WHERE model_key = 'claude-opus-4-8';

-- [NONAKT] claude-sonnet-4-6
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: kunci Anthropic tidak ada di pool — belum bisa dibuktikan')
WHERE model_key = 'claude-sonnet-4-6';

-- [NONAKT] claude-sonnet-5
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: kunci Anthropic tidak ada di pool — belum bisa dibuktikan')
WHERE model_key = 'claude-sonnet-5';

-- [NONAKT] gemini-2.0-flash
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 429 kuota kunci saat uji (model dikenali server) — uji ulang saat kuota tersedia')
WHERE model_key = 'gemini-2.0-flash';

-- [NONAKT] gemini-2.0-flash-lite
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 429 kuota kunci saat uji (model dikenali server) — uji ulang saat kuota tersedia')
WHERE model_key = 'gemini-2.0-flash-lite';

-- [NONAKT] gemini-2.5-pro
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 429 — free tier AI Studio tanpa kuota model Pro; butuh kunci berbayar utk uji')
WHERE model_key = 'gemini-2.5-pro';

-- [NONAKT] gemini-3-pro-preview
UPDATE ai_models SET
  is_active = false,
  cost_hint = COALESCE(cost_hint,'{}'::jsonb) || jsonb_build_object('audit','NONAKTIF 2026-07-06: 429 — free tier AI Studio tanpa kuota model Pro; butuh kunci berbayar utk uji')
WHERE model_key = 'gemini-3-pro-preview';

COMMIT;
