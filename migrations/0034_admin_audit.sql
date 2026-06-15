-- 0034 — admin_audit (Phase 10.0 fondasi). Jejak aksi admin sensitif (impersonate, suspend,
-- credit/refund, edit pricing, transition niche). RLS ON tanpa policy → service_role ONLY
-- (admin baca/tulis via route-handler service_role). PHASE10_ADMIN_WIRING.md §0/§3.
create table if not exists public.admin_audit (
  id uuid primary key default gen_random_uuid(),
  admin_uid text not null,
  action text not null,
  target_tenant text,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_admin_audit_created on public.admin_audit (created_at desc);
create index if not exists idx_admin_audit_target on public.admin_audit (target_tenant);

alter table public.admin_audit enable row level security;
-- sengaja TANPA policy: hanya service_role (bypass RLS) yang akses. anon/authenticated diblok.
