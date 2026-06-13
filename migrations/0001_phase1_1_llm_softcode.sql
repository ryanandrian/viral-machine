-- Migration 0001 — Phase 1.1 SOFTCODE LLM config
-- Ref: PROGRESS.md §1.1 + decisions_v1_v2_migration.
-- Tambah llm_library (text) + llm_models (jsonb per-task) ke tenant_configs, backfill dari kolom flat.
-- DEPRECATE llm_script_fallback (silent cross-library fallback) — kolom TIDAK dihapus (back-compat), hanya tak dipakai kode v2.
-- Target: v2 (atliatnjhysdibmfypul). JANGAN apply ke v1 sampai cutover (v1 produksi pakai skema lama).
-- Apply: psycopg2/psql ke v2 via Session pooler.

ALTER TABLE public.tenant_configs
  ADD COLUMN IF NOT EXISTS llm_library text,
  ADD COLUMN IF NOT EXISTS llm_models  jsonb;

-- Backfill: petakan provider→library, model flat→per-task. Default per-library aman.
UPDATE public.tenant_configs SET
  llm_library = CASE
    WHEN lower(coalesce(llm_provider,'')) IN ('claude','anthropic') THEN 'anthropic'
    WHEN lower(coalesce(llm_provider,'')) IN ('openai','gpt')        THEN 'openai'
    ELSE 'anthropic'
  END,
  llm_models = CASE
    WHEN lower(coalesce(llm_provider,'')) IN ('openai','gpt') THEN jsonb_build_object(
      'script',   coalesce(nullif(llm_model,''), 'gpt-4o'),
      'utility',  'gpt-4o-mini',
      'rewrite',  'gpt-4o-mini',
      'analyzer', 'gpt-4o-mini',
      'fallback', 'gpt-4o-mini'
    )
    ELSE jsonb_build_object(
      'script',   coalesce(nullif(llm_model,''), 'claude-sonnet-4-6'),
      'utility',  'claude-haiku-4-5-20251001',
      'rewrite',  'claude-haiku-4-5-20251001',
      'analyzer', 'claude-haiku-4-5-20251001',
      'fallback', 'claude-haiku-4-5-20251001'
    )
  END
WHERE llm_models IS NULL;
