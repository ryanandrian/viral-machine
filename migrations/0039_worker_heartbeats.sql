-- 0039 — worker_heartbeats (Phase 10.8). E3 System Health: status thread worker_decoupled.
-- worker (v2, belum di VPS) upsert tiap ~15s; di dev kosong (worker belum jalan) = jujur "menunggu deploy".
-- RLS ON tanpa policy → service_role ONLY (system page baca via server component service_role).
create table if not exists public.worker_heartbeats (
  worker_name text primary key,
  status text not null default 'up',     -- up | down
  current_job text,
  node text,
  last_heartbeat_at timestamptz not null default now()
);
alter table public.worker_heartbeats enable row level security;
-- sengaja tanpa policy: service_role only.
