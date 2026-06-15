-- 0045: PERBAIKAN PRODUCE & PUBLISH (pra-cutover) — Area A1-A3 (ADITIF, nol risiko).
-- Luruskan DB ke arsitektur §12c + model terkunci (lihat PROGRESS.md §PERBAIKAN PRODUCE & PUBLISH).
-- A4 (migrasi data) + A5 (drop fosil V1) = langkah terpisah (A5 setelah BE/FE lepas).

-- A1 — target stok ready per-channel (§12c: tren=1, evergreen=3-5). NULL → BE pakai default env.
alter table public.channels
  add column if not exists buffer_depth integer;

-- A2 — DIBATALKAN: kolom pemilik niche SUDAH ADA = `niches.exclusive_to` (migr 0037, Phase 10).
-- Pakai `exclusive_to` (+ `exclusive_until`/`released_at`/`access_type`). Tak perlu kolom baru.

-- A3 — pengajuan custom niche oleh tenant (form C4): judul + clue/masukan tenant.
create table if not exists public.niche_requests (
  request_id    uuid primary key default gen_random_uuid(),
  tenant_id     text not null,
  channel_id    uuid references public.channels(id) on delete set null,  -- opsional
  request_type  text not null check (request_type in ('public_90d','private')),
  title         text not null,
  clues         jsonb not null default '{}'::jsonb,   -- referensi/gaya/keyword/contoh dari tenant
  status        text not null default 'pending' check (status in ('pending','approved','rejected','live')),
  price_key     text,                                  -- key pricing_config (custom_niche_public_90d|custom_niche_private)
  niche_id      text,                                  -- diisi admin saat niche dibuat
  admin_note    text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

alter table public.niche_requests enable row level security;

-- Tenant: BACA + AJUKAN milik sendiri. UPDATE/DELETE = service_role (admin) — tak ada policy = tertutup.
drop policy if exists niche_requests_tenant_read   on public.niche_requests;
drop policy if exists niche_requests_tenant_insert on public.niche_requests;
create policy niche_requests_tenant_read   on public.niche_requests
  for select using (tenant_id = (auth.uid())::text);
create policy niche_requests_tenant_insert on public.niche_requests
  for insert with check (tenant_id = (auth.uid())::text);

create index if not exists idx_niche_requests_tenant on public.niche_requests(tenant_id);
create index if not exists idx_niche_requests_status on public.niche_requests(status);
