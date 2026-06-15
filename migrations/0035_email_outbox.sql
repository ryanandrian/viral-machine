-- 0035 — email_outbox (Phase 10.1). Admin "Kirim email" = ANTRE di sini → worker Python proses
-- (resolve email tenant via Auth admin API + send_email SMTP, fail-soft). Owner pilih platform-queue.
-- RLS ON tanpa policy → service_role ONLY (admin enqueue via route; worker proses). PHASE10 §3.
create table if not exists public.email_outbox (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  subject text not null,
  body text not null,
  status text not null default 'pending',  -- pending | sent | failed
  created_by text,                          -- admin uid
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  error text,
  constraint chk_email_outbox_status check (status in ('pending','sent','failed'))
);
create index if not exists idx_email_outbox_pending on public.email_outbox (created_at) where status = 'pending';
create index if not exists idx_email_outbox_tenant on public.email_outbox (tenant_id, created_at desc);

alter table public.email_outbox enable row level security;
-- sengaja tanpa policy: service_role only (admin route enqueue, worker proses). anon/authenticated diblok.
