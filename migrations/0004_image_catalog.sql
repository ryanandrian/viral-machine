-- Migration 0004 — Phase 1.3: katalog model IMAGE → DB (component='image')
-- Ref: SOFTCODE §3 + AI Provider Catalog directive (2026-06-13). Target: v2.
-- Pindahkan AI_IMAGE_MODELS (hardcode di ai_image.py) ke ai_models. Admin bisa
-- tambah model image lewat DB tanpa redeploy. ai_image dispatch pada platform=provider_key.
-- JANGAN apply ke v1 sampai cutover.

-- Provider Replicate (image). adapter='replicate' = penanda platform (bukan LLM adapter).
INSERT INTO public.ai_providers (provider_key, display_name, adapter, base_url) VALUES
  ('replicate', 'Replicate', 'replicate', NULL)
ON CONFLICT (provider_key) DO NOTHING;

-- Seed model image (mirror AI_IMAGE_MODELS lama; default_params.size utk OpenAI image).
INSERT INTO public.ai_models
  (model_key, provider_key, component, model_id, display_name, quality_tier, cost_hint, default_params, sort_order) VALUES
  ('gpt-image-1-mini', 'openai', 'image', 'gpt-image-1-mini',
     'GPT Image 1 Mini', 'fast',
     '{"unit":"per_image","approx_usd":0.015}'::jsonb,
     '{"size":"1024x1536"}'::jsonb, 10),
  ('flux-schnell', 'replicate', 'image', 'black-forest-labs/flux-schnell',
     'FLUX schnell', 'fast',
     '{"unit":"per_image","approx_usd":0.003}'::jsonb,
     '{}'::jsonb, 20),
  ('stable-diffusion', 'replicate', 'image',
     'stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf',
     'Stable Diffusion', 'standard',
     '{"unit":"per_image","approx_usd":0.002}'::jsonb,
     '{}'::jsonb, 30)
ON CONFLICT (model_key) DO NOTHING;
