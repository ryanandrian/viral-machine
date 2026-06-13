-- Migration 0010 — Alignment: pricing_config + content_languages (kontrak frontend + decisions)
-- Ref: decisions_niche_model (pricing_config) + decisions_content_language (content_languages).
-- Target: v2. Tabel CONFIG/CATALOG SHARED (admin-managed) → RLS public-READ, tulis service_role.
-- Frontend sudah referensi {{pricing.*}} + katalog bahasa; tabel ini menyelaraskan DB↔frontend.

-- ── pricing_config: single source semua harga (subscription/add-on/one-time) ──
CREATE TABLE IF NOT EXISTS public.pricing_config (
  key             text PRIMARY KEY,
  value_idr       integer NOT NULL,
  value_usd_cents integer,
  description     text,
  category        text,            -- 'subscription'|'add_on'|'one_time'
  active          boolean NOT NULL DEFAULT true,
  effective_from  timestamptz NOT NULL DEFAULT now(),
  effective_until timestamptz,
  updated_by      text,
  updated_at      timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.pricing_config (key, value_idr, value_usd_cents, description, category) VALUES
  ('plan_starter',            149000,  900, 'Starter plan monthly',          'subscription'),
  ('plan_pro',                349000, 2200, 'Pro plan monthly',              'subscription'),
  ('plan_scale',              699000, 4400, 'Scale plan monthly',            'subscription'),
  ('custom_niche_public_90d', 299000, 1900, 'Custom niche public after 90d', 'add_on'),
  ('custom_niche_private',   1499000, 9400, 'Custom niche permanent private','add_on'),
  ('voice_pack',               99000,  620, 'Voice pack ElevenLabs',         'add_on'),
  ('niche_audit',             499000, 3100, 'Channel niche audit',           'one_time'),
  ('concierge_setup',         399000, 2500, 'Concierge BYOK setup',          'one_time'),
  ('priority_queue',           99000,  620, 'Priority queue monthly',        'add_on')
ON CONFLICT (key) DO NOTHING;

-- ── content_languages: katalog bahasa konten (per-channel) ──
CREATE TABLE IF NOT EXISTS public.content_languages (
  locale                  text PRIMARY KEY,        -- BCP-47
  display_name            text NOT NULL,
  tts_providers_supported jsonb NOT NULL DEFAULT '[]'::jsonb,
  quality_tier            text NOT NULL DEFAULT 'experimental',  -- 'official'|'experimental'
  caption_font            text,
  is_active               boolean NOT NULL DEFAULT false,
  sort_order              integer NOT NULL DEFAULT 100,
  updated_at              timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.content_languages (locale, display_name, tts_providers_supported, quality_tier, is_active, sort_order) VALUES
  ('id-ID','Bahasa Indonesia','["elevenlabs","openai_tts","edge_tts"]','official',true,10),
  ('en-US','English',         '["elevenlabs","openai_tts","edge_tts"]','official',true,20),
  ('ms-MY','Bahasa Malaysia', '["elevenlabs","edge_tts"]','experimental',false,30),
  ('fil-PH','Filipino',       '["elevenlabs","edge_tts"]','experimental',false,40),
  ('th-TH','ภาษาไทย',         '["elevenlabs","edge_tts"]','experimental',false,50),
  ('vi-VN','Tiếng Việt',      '["elevenlabs","edge_tts"]','experimental',false,60)
ON CONFLICT (locale) DO NOTHING;

-- RLS public-read (ditampilkan di landing/pricing/onboarding). Tulis = service_role only.
ALTER TABLE public.pricing_config     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_languages  ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pricing_config_read ON public.pricing_config;
CREATE POLICY pricing_config_read ON public.pricing_config FOR SELECT USING (true);
DROP POLICY IF EXISTS content_languages_read ON public.content_languages;
CREATE POLICY content_languages_read ON public.content_languages FOR SELECT USING (true);
