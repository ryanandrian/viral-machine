-- 0093: AI model VENDOR / key-group + akun AI per-elemen di channel
-- Keputusan FINAL owner 2026-06-25 (CHANNEL_LOCK_ACTIVATION_PLAN.md blok "KEPUTUSAN FINAL").
-- Inti:
--  * openai + openai_tts = vendor 'openai' (1 kunci OpenAI sk-... melayani GPT+image+TTS → tenant isi SEKALI).
--  * tenant_ai_accounts boleh >1 baris per (tenant, key_group) — label beda (Utama/Cadangan). (Tak ada unique constraint → aman.)
--  * channels.{llm,tts,visual}_account_id = akun yg ditugaskan per elemen (NULL → auto akun tunggal valid vendor itu).

-- 1) ai_providers.key_group (vendor). openai_tts → openai; lainnya = provider_key sendiri.
alter table ai_providers add column if not exists key_group text;
update ai_providers set key_group = case provider_key when 'openai_tts' then 'openai' else provider_key end
 where key_group is null;

-- 2) tenant_ai_accounts.key_group — backfill dari provider_key via mapping ai_providers.
alter table tenant_ai_accounts add column if not exists key_group text;
update tenant_ai_accounts t set key_group = coalesce(p.key_group, t.provider_key)
  from ai_providers p where p.provider_key = t.provider_key and t.key_group is null;
update tenant_ai_accounts set key_group = provider_key where key_group is null;  -- defensif

-- 3) channels: akun AI per-elemen.
alter table channels add column if not exists llm_account_id    uuid references tenant_ai_accounts(id) on delete set null;
alter table channels add column if not exists tts_account_id    uuid references tenant_ai_accounts(id) on delete set null;
alter table channels add column if not exists visual_account_id uuid references tenant_ai_accounts(id) on delete set null;

-- 4) Backfill channel existing → akun tunggal valid per vendor elemen (grandfather ryan tetap jalan).
-- LLM (vendor dari channels.llm_library)
update channels c set llm_account_id = a.id
  from ai_providers p, tenant_ai_accounts a
 where c.llm_account_id is null and coalesce(c.llm_library,'') <> ''
   and p.provider_key = c.llm_library
   and a.tenant_id = c.tenant_id and a.key_group = p.key_group and a.status = 'valid';
-- TTS (vendor dari channels.tts_provider)
update channels c set tts_account_id = a.id
  from ai_providers p, tenant_ai_accounts a
 where c.tts_account_id is null and coalesce(c.tts_provider,'') <> ''
   and p.provider_key = c.tts_provider
   and a.tenant_id = c.tenant_id and a.key_group = p.key_group and a.status = 'valid';
-- Visual (vendor dari provider model di visual_mode = 'ai_image:'/'ai_video:'<model_key>)
update channels c set visual_account_id = a.id
  from ai_models m, ai_providers p, tenant_ai_accounts a
 where c.visual_account_id is null and c.visual_mode ~ '^(ai_image|ai_video):'
   and m.model_key = split_part(c.visual_mode, ':', 2)
   and p.provider_key = m.provider_key
   and a.tenant_id = c.tenant_id and a.key_group = p.key_group and a.status = 'valid';
