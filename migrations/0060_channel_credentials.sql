-- 0060 — channel_credentials: OAuth YouTube PER-CHANNEL (multi-channel: Pro 3, Business 10)
-- ============================================================================
-- Gap arsitektur: tenant_credentials PK=tenant_id → 1 channel YouTube per tenant, padahal tier
-- menjual multi-channel. Solusi: tabel BARU per-channel (PK channels.id). tenant_credentials
-- DIBIARKAN utuh sbg FALLBACK (ryan/produksi lama tak putus). BE prefer channel_credentials → fallback.
-- service_role only (RLS ON tanpa policy — sama seperti tenant_credentials; FE tak pernah baca raw).
-- ============================================================================

create table if not exists channel_credentials (
  channel_id                uuid primary key references channels(id) on delete cascade,
  tenant_id                 text not null,
  google_client_id          text,
  google_client_secret_enc  text,
  google_refresh_token_enc  text,
  google_access_token_enc   text,
  token_expiry              timestamptz,
  yt_channel_id             text,                       -- YouTube channel id (UC...) hasil OAuth (mine=true)
  scopes                    jsonb not null default '[]'::jsonb,
  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now()
);

alter table channel_credentials enable row level security;  -- service_role only (tanpa policy)
create index if not exists idx_channel_creds_tenant on channel_credentials(tenant_id);

-- Backfill: kredensial existing tenant → channel TERTUA-nya (1 OAuth lama = 1 channel).
-- ryan: tenant_credentials → channel_credentials(channel_id=410d4538...). Tenant multi-channel:
-- hanya channel pertama yang ter-backfill; channel lain connect sendiri nanti (per-channel OAuth).
insert into channel_credentials (channel_id, tenant_id, google_client_id, google_client_secret_enc,
  google_refresh_token_enc, google_access_token_enc, token_expiry, yt_channel_id, scopes, created_at, updated_at)
select c.id, tc.tenant_id, tc.google_client_id, tc.google_client_secret_enc,
       tc.google_refresh_token_enc, tc.google_access_token_enc, tc.token_expiry, tc.channel_id, tc.scopes,
       tc.created_at, now()
from tenant_credentials tc
join channels c on c.tenant_id = tc.tenant_id
where tc.google_refresh_token_enc is not null
  and c.id = (select c2.id from channels c2 where c2.tenant_id = tc.tenant_id order by c2.created_at asc limit 1)
on conflict (channel_id) do nothing;
