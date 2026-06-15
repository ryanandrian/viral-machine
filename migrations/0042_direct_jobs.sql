-- 0042 — direct_jobs (Phase: Direct/On-demand produce, V2). "1 mesin, 2 mode": jalur prioritas yang
-- di-drain producer SEBELUM stok-buffer (semaphore core yang SAMA → anti-OOM utuh). 3 tujuan:
--   admin_test (admin uji niche di channel internal) · test (tenant preview config, private) · retry (re-run gagal).
-- Producer set logger.contextualize(tenant_id, run_id) → pipeline_run_logs (live-tail D5 by run_id) + tulis production_runs.
create table if not exists public.direct_jobs (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  channel_id text not null,
  job_type text not null default 'test',           -- test | retry | admin_test
  niche text,                                       -- override niche (admin_test)
  source_run_id text,                               -- run yang di-retry
  publish_privacy text not null default 'private',  -- test = private
  status text not null default 'pending',           -- pending | producing | published | failed
  run_id text,                                      -- link ke production_runs.run_id (live-tail)
  error text,
  requested_by text,                                -- uid pemicu
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  constraint chk_direct_jobs_status check (status in ('pending','producing','published','failed')),
  constraint chk_direct_jobs_type check (job_type in ('test','retry','admin_test'))
);
create index if not exists idx_direct_jobs_pending on public.direct_jobs (created_at) where status = 'pending';
create index if not exists idx_direct_jobs_tenant on public.direct_jobs (tenant_id, created_at desc);

alter table public.direct_jobs enable row level security;
-- Tenant: lihat + buat job miliknya (test/retry channel sendiri). Admin (admin_test) via service_role.
do $$ begin
  if not exists (select 1 from pg_policy where polname='direct_jobs_tenant_read' and polrelid='public.direct_jobs'::regclass) then
    create policy direct_jobs_tenant_read on public.direct_jobs for select using (tenant_id = (auth.uid())::text);
  end if;
  if not exists (select 1 from pg_policy where polname='direct_jobs_tenant_insert' and polrelid='public.direct_jobs'::regclass) then
    create policy direct_jobs_tenant_insert on public.direct_jobs for insert with check (tenant_id = (auth.uid())::text);
  end if;
end $$;
-- live status (Antre→Berjalan→Selesai) untuk FE
do $$ begin
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and tablename='direct_jobs') then
    alter publication supabase_realtime add table public.direct_jobs;
  end if;
end $$;
