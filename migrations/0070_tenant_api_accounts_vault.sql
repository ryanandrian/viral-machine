-- 0070 — F2-09: AI key = VAULT multi-akun per provider, assignment per-channel-per-elemen (§3.19/§10.F)
-- ============================================================================
-- SEBELUM: key per-TENANT tunggal di tenant_configs.{llm,tts,visual}_api_key_enc (Fernet).
-- TARGET: tenant boleh >1 akun/provider; tiap CHANNEL pilih akun untuk tiap elemen (LLM/TTS/image/video).
-- Untuk ribuan tenant MULTI-channel (bukan asumsi 1 tenant=1 channel/1 key).
--
-- NON-BREAKING: kolom ref di channels NULLABLE → BE fallback ke tenant_configs.*_enc bila NULL
-- (ryan tetap jalan SEBELUM & SESUDAH BE diubah). Backfill: bikin 1 akun "Default <elemen>" per
-- tenant dari *_enc lama (COPY enc — TANPA dekripsi, master-key tak tersentuh) + arahkan channel tenant
-- ke akun itu. Idempotent (guard NOT EXISTS).
-- ============================================================================

create table if not exists tenant_api_accounts (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    text not null,
  component    text not null check (component in ('llm','tts','image','video')),
  provider     text,                 -- mis. anthropic/openai/elevenlabs (label teknis, opsional)
  label        text not null,        -- nama akun yg dilihat tenant, mis. "OpenAI akun-1"
  key_enc      text,                 -- Fernet (master-key server-only); ditulis via route server (encrypt)
  status       text not null default 'active' check (status in ('active','invalid','disabled')),
  validated_at timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists idx_api_accounts_tenant on tenant_api_accounts (tenant_id, component);

alter table tenant_api_accounts enable row level security;
drop policy if exists api_accounts_owner on tenant_api_accounts;
create policy api_accounts_owner on tenant_api_accounts
  for all to authenticated
  using (tenant_id = (auth.uid())::text)
  with check (tenant_id = (auth.uid())::text);
revoke all on tenant_api_accounts from anon;

-- Ref akun per-elemen di channels (nullable → fallback tenant_configs.*_enc).
alter table channels
  add column if not exists llm_account_id   uuid references tenant_api_accounts(id) on delete set null,
  add column if not exists tts_account_id   uuid references tenant_api_accounts(id) on delete set null,
  add column if not exists image_account_id uuid references tenant_api_accounts(id) on delete set null,
  add column if not exists video_account_id uuid references tenant_api_accounts(id) on delete set null;

-- Backfill: akun "Default" per komponen dari tenant_configs.*_enc + arahkan channel tenant.
do $$
declare r record; aid uuid;
begin
  for r in select tenant_id, llm_api_key_enc, llm_library, tts_api_key_enc, tts_provider, visual_api_key_enc
           from tenant_configs loop
    if r.llm_api_key_enc is not null
       and not exists (select 1 from tenant_api_accounts a where a.tenant_id = r.tenant_id and a.component='llm') then
      insert into tenant_api_accounts(tenant_id, component, provider, label, key_enc)
        values (r.tenant_id, 'llm', r.llm_library, 'Default LLM', r.llm_api_key_enc) returning id into aid;
      update channels set llm_account_id = aid where tenant_id = r.tenant_id and llm_account_id is null;
    end if;
    if r.tts_api_key_enc is not null
       and not exists (select 1 from tenant_api_accounts a where a.tenant_id = r.tenant_id and a.component='tts') then
      insert into tenant_api_accounts(tenant_id, component, provider, label, key_enc)
        values (r.tenant_id, 'tts', r.tts_provider, 'Default TTS', r.tts_api_key_enc) returning id into aid;
      update channels set tts_account_id = aid where tenant_id = r.tenant_id and tts_account_id is null;
    end if;
    if r.visual_api_key_enc is not null
       and not exists (select 1 from tenant_api_accounts a where a.tenant_id = r.tenant_id and a.component='image') then
      insert into tenant_api_accounts(tenant_id, component, provider, label, key_enc)
        values (r.tenant_id, 'image', 'image', 'Default Image', r.visual_api_key_enc) returning id into aid;
      update channels set image_account_id = aid where tenant_id = r.tenant_id and image_account_id is null;
    end if;
  end loop;
end $$;
