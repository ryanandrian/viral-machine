-- Migration 0002 — AI Provider/Model Catalog (DB-driven, admin-managed)
-- Ref: directive 2026-06-13 (provider+format param API config-driven via super-admin,
--      nol hardcode nama provider di business logic) + MULTI_FORMAT_STUDIO §5b (ai_models
--      terunifikasi) + PROGRESS Phase 1.3. Target: v2 (atliatnjhysdibmfypul).
-- JANGAN apply ke v1 sampai cutover.
--
-- Tujuan: super-admin bisa menambah provider AI baru + model-nya (lengkap quality/cost +
-- format parameter API) lewat DB tanpa redeploy → tenant punya makin banyak pilihan
-- (lebih banyak kategori kreator terlayani). Pemilihan provider 100% dari DB; kode hanya
-- punya ADAPTER per-protokol transport (bukan per-vendor).

-- ── ai_providers: spesifikasi transport sebuah vendor AI ─────────────────────────
CREATE TABLE IF NOT EXISTS public.ai_providers (
  provider_key          text PRIMARY KEY,                 -- 'anthropic','openai',... (admin-defined)
  display_name          text NOT NULL,
  adapter               text NOT NULL,                    -- protokol transport (kode): 'anthropic_messages'|'openai_chat'|'replicate'|'generic_rest'
  base_url              text,                              -- untuk openai_chat/generic_rest (NULL = default SDK)
  auth_type             text NOT NULL DEFAULT 'api_key',   -- 'api_key'|'bearer'|'header'
  request_param_schema  jsonb NOT NULL DEFAULT '{}'::jsonb,-- override format param vendor (rename param, supports_json, temp_range, dst). Kosong = pakai default protokol.
  is_active             boolean NOT NULL DEFAULT true,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

-- ── ai_models: model yang ditawarkan, per komponen produksi ──────────────────────
CREATE TABLE IF NOT EXISTS public.ai_models (
  model_key       text PRIMARY KEY,                        -- key stabil (admin-defined), dirujuk tenant_configs.llm_models
  provider_key    text NOT NULL REFERENCES public.ai_providers(provider_key) ON DELETE RESTRICT,
  component       text NOT NULL,                           -- 'llm'|'tts'|'image'|'video'
  model_id        text NOT NULL,                           -- string model untuk panggilan API vendor
  display_name    text NOT NULL,
  quality_tier    text NOT NULL DEFAULT 'standard',        -- 'fast'|'standard'|'premium'
  cost_hint       jsonb NOT NULL DEFAULT '{}'::jsonb,      -- transparansi harga BYOK: {unit, input_per_mtok, output_per_mtok,...}
  default_params  jsonb NOT NULL DEFAULT '{}'::jsonb,      -- override per-model: {temperature, max_tokens,...}
  is_active       boolean NOT NULL DEFAULT true,
  sort_order      integer NOT NULL DEFAULT 100,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_models_component_active
  ON public.ai_models (component) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_ai_models_provider
  ON public.ai_models (provider_key);

-- ── RLS: katalog = config global non-sensitif (TANPA API key) → public read,
--     tulis hanya service_role/admin (tak ada policy write → hanya bypass service_role) ──
ALTER TABLE public.ai_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_models    ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ai_providers_read ON public.ai_providers;
CREATE POLICY ai_providers_read ON public.ai_providers FOR SELECT USING (true);

DROP POLICY IF EXISTS ai_models_read ON public.ai_models;
CREATE POLICY ai_models_read ON public.ai_models FOR SELECT USING (true);

-- ── Seed: provider + model LLM yang dipakai SEKARANG (component='llm') ────────────
-- (Komponen image/tts/video ditambah di phase masing-masing — tabel sudah generic.)
INSERT INTO public.ai_providers (provider_key, display_name, adapter, base_url) VALUES
  ('anthropic', 'Anthropic Claude', 'anthropic_messages', NULL),
  ('openai',    'OpenAI GPT',       'openai_chat',        NULL)
ON CONFLICT (provider_key) DO NOTHING;

INSERT INTO public.ai_models
  (model_key, provider_key, component, model_id, display_name, quality_tier, cost_hint, default_params, sort_order) VALUES
  ('claude-sonnet-4-6',          'anthropic', 'llm', 'claude-sonnet-4-6',          'Claude Sonnet 4.6', 'premium',
     '{"unit":"per_mtok","input":3,"output":15}'::jsonb, '{"max_tokens":2000}'::jsonb, 10),
  ('claude-haiku-4-5-20251001',  'anthropic', 'llm', 'claude-haiku-4-5-20251001',  'Claude Haiku 4.5',  'fast',
     '{"unit":"per_mtok","input":1,"output":5}'::jsonb,  '{"max_tokens":1200}'::jsonb, 20),
  ('gpt-4o',                     'openai',    'llm', 'gpt-4o',                      'GPT-4o',            'premium',
     '{"unit":"per_mtok","input":2.5,"output":10}'::jsonb, '{"max_tokens":2000}'::jsonb, 30),
  ('gpt-4o-mini',                'openai',    'llm', 'gpt-4o-mini',                 'GPT-4o mini',       'fast',
     '{"unit":"per_mtok","input":0.15,"output":0.6}'::jsonb, '{"max_tokens":1200}'::jsonb, 40)
ON CONFLICT (model_key) DO NOTHING;
