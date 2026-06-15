-- 0040 — Support subsystem (Phase 10.9). support_tickets + support_messages.
-- Tenant: buat/lihat/balas tiket SENDIRI (client RLS = auth.uid()). Admin: kelola semua via service_role.
-- Realtime support_messages (live chat). Pola RLS = tenant_id=(auth.uid())::text (konsisten v2).

create table if not exists public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  subject text not null,
  status text not null default 'open',          -- open | pending | resolved
  priority text not null default 'normal',
  assigned_to text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_support_status check (status in ('open','pending','resolved'))
);
create index if not exists idx_support_tickets_tenant on public.support_tickets (tenant_id, updated_at desc);
create index if not exists idx_support_tickets_status on public.support_tickets (status, updated_at desc);

create table if not exists public.support_messages (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid not null references public.support_tickets(id) on delete cascade,
  sender text not null,                          -- tenant | admin
  body text not null,
  created_at timestamptz not null default now(),
  constraint chk_support_sender check (sender in ('tenant','admin'))
);
create index if not exists idx_support_messages_ticket on public.support_messages (ticket_id, created_at);

alter table public.support_tickets enable row level security;
alter table public.support_messages enable row level security;

-- Tenant: tiket sendiri (read/insert/update-status-reopen). Admin pakai service_role (bypass).
do $$ begin
  if not exists (select 1 from pg_policy where polname='support_tickets_tenant_read' and polrelid='public.support_tickets'::regclass) then
    create policy support_tickets_tenant_read on public.support_tickets for select using (tenant_id = (auth.uid())::text);
  end if;
  if not exists (select 1 from pg_policy where polname='support_tickets_tenant_insert' and polrelid='public.support_tickets'::regclass) then
    create policy support_tickets_tenant_insert on public.support_tickets for insert with check (tenant_id = (auth.uid())::text);
  end if;
  -- Pesan: tenant baca pesan tiket miliknya; insert pesan (sender='tenant') ke tiket miliknya.
  if not exists (select 1 from pg_policy where polname='support_messages_tenant_read' and polrelid='public.support_messages'::regclass) then
    create policy support_messages_tenant_read on public.support_messages for select
      using (ticket_id in (select id from public.support_tickets where tenant_id = (auth.uid())::text));
  end if;
  if not exists (select 1 from pg_policy where polname='support_messages_tenant_insert' and polrelid='public.support_messages'::regclass) then
    create policy support_messages_tenant_insert on public.support_messages for insert
      with check (sender = 'tenant' and ticket_id in (select id from public.support_tickets where tenant_id = (auth.uid())::text));
  end if;
end $$;

-- Realtime live-chat (RLS men-scope event).
do $$ begin
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and tablename='support_messages') then
    alter publication supabase_realtime add table public.support_messages;
  end if;
end $$;
