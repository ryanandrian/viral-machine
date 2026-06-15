-- 0036 — pricing_audit (Phase 10.2). Riwayat perubahan pricing_config (untuk audit + ROLLBACK nyata).
-- pricing_config punya updated_by/updated_at tapi tanpa histori → tabel ini simpan old/new snapshot.
-- RLS ON tanpa policy → service_role ONLY (admin via route). PHASE10_ADMIN_WIRING.md §3.
create table if not exists public.pricing_audit (
  id uuid primary key default gen_random_uuid(),
  key text not null,
  old_value jsonb,
  new_value jsonb not null,
  changed_by text,
  changed_at timestamptz not null default now()
);
create index if not exists idx_pricing_audit_key on public.pricing_audit (key, changed_at desc);

alter table public.pricing_audit enable row level security;
-- sengaja tanpa policy: service_role only.
