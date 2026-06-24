-- 0091: Pool kredensial tenant-wide (AI keys + YouTube connections) + backfill
-- ============================================================================
-- Arsitektur: CHANNEL_LOCK_ACTIVATION_PLAN.md §0.8.B. Kredensial tenant pindah dari per-channel-inline
-- (channels.*_key_enc) + OAuth (channel_credentials/tenant_credentials) → POOL tenant-wide.
-- Channel menugaskan: penyedia+model (sudah di channels.*) + youtube_account_id + platform_channel_id (target).
-- Status 'valid' utk backfill (kunci/OAuth existing = TERBUKTI jalan di produksi). Validate-early utk yang baru.

-- 1) Pool kunci AI (per tenant × penyedia; boleh >1/penyedia) ----------------
create table if not exists tenant_ai_accounts (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    text not null,
  provider_key text not null,                       -- → ai_providers (openai/anthropic/elevenlabs/replicate/…)
  label        text not null default '',
  key_enc      text,                                -- Fernet (master key server-only)
  status       text not null default 'unchecked' check (status in ('valid','invalid','unchecked')),
  validated_at timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists idx_tai_tenant_provider on tenant_ai_accounts (tenant_id, provider_key);

-- 2) Pool koneksi YouTube (per tenant; 1..N akun Google) --------------------
create table if not exists tenant_youtube_accounts (
  id                       uuid primary key default gen_random_uuid(),
  tenant_id                text not null,
  label                    text not null default '',
  google_client_id         text,
  google_client_secret_enc text,
  google_refresh_token_enc text,
  google_access_token_enc  text,
  token_expiry             timestamptz,
  yt_channel_id            text,                     -- info (channel YT yg terdeteksi saat connect)
  status                   text not null default 'unchecked' check (status in ('valid','invalid','unchecked')),
  validated_at             timestamptz,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);
create index if not exists idx_tya_tenant on tenant_youtube_accounts (tenant_id);

-- 3) channels: ref koneksi YouTube (target = platform_channel_id yg sudah ada) -
alter table channels add column if not exists youtube_account_id uuid references tenant_youtube_accounts(id) on delete set null;

-- 4) RLS: tenant baca miliknya (tulis via service_role/vault = bypass) -------
alter table tenant_ai_accounts      enable row level security;
alter table tenant_youtube_accounts enable row level security;
drop policy if exists tai_sel on tenant_ai_accounts;
create policy tai_sel on tenant_ai_accounts for select using (tenant_id = (auth.uid())::text);
drop policy if exists tya_sel on tenant_youtube_accounts;
create policy tya_sel on tenant_youtube_accounts for select using (tenant_id = (auth.uid())::text);

-- 5) BACKFILL kunci AI dari channels.*_key_enc (dedup per tenant×penyedia) ----
insert into tenant_ai_accounts (tenant_id, provider_key, label, key_enc, status, validated_at)
select distinct on (tenant_id, provider_key)
       tenant_id, provider_key, 'Backfill ' || provider_key, key_enc, 'valid', now()
from (
  select tenant_id, llm_library  as provider_key, llm_key_enc    as key_enc
    from channels where llm_key_enc    is not null and coalesce(llm_library,'')  <> ''
  union all
  select tenant_id, tts_provider, tts_key_enc
    from channels where tts_key_enc    is not null and coalesce(tts_provider,'') <> ''
  union all
  select c.tenant_id, m.provider_key, c.visual_key_enc
    from channels c join ai_models m on m.model_key = split_part(c.visual_mode, ':', 2)
    where c.visual_key_enc is not null and (c.visual_mode like 'ai_image:%' or c.visual_mode like 'ai_video:%')
) src
where coalesce(provider_key,'') <> '' and key_enc is not null
order by tenant_id, provider_key, key_enc;

-- 6) BACKFILL koneksi YouTube: dari channel_credentials (per-channel) → pool + link channel
do $$
declare r record; new_id uuid;
begin
  for r in select * from channel_credentials where google_refresh_token_enc is not null loop
    insert into tenant_youtube_accounts
      (tenant_id, label, google_client_id, google_client_secret_enc, google_refresh_token_enc, google_access_token_enc, token_expiry, yt_channel_id, status, validated_at)
    values
      (r.tenant_id, 'Backfill YouTube', r.google_client_id, r.google_client_secret_enc, r.google_refresh_token_enc, r.google_access_token_enc, r.token_expiry, r.yt_channel_id, 'valid', now())
    returning id into new_id;
    update channels set youtube_account_id = new_id where id = r.channel_id;
  end loop;
  -- fallback: tenant punya tenant_credentials tapi channel belum ter-link (tak ada channel_credentials)
  for r in select tc.* from tenant_credentials tc where tc.google_refresh_token_enc is not null
           and exists (select 1 from channels c where c.tenant_id = tc.tenant_id and c.youtube_account_id is null) loop
    insert into tenant_youtube_accounts
      (tenant_id, label, google_client_id, google_client_secret_enc, google_refresh_token_enc, google_access_token_enc, token_expiry, status, validated_at)
    values
      (r.tenant_id, 'Backfill YouTube (tenant)', r.google_client_id, r.google_client_secret_enc, r.google_refresh_token_enc, r.google_access_token_enc, r.token_expiry, 'valid', now())
    returning id into new_id;
    update channels set youtube_account_id = new_id where tenant_id = r.tenant_id and youtube_account_id is null;
  end loop;
end $$;
