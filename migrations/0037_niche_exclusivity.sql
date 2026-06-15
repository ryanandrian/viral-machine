-- 0037 — Niche exclusivity + monthly-release (Phase 10.3). Per decisions_niche_model:
-- public-after-90d, permanent-private, monthly release cycle. TAG-POOL TIDAK di sini (epik pipeline,
-- butuh videos.topic_tags + assignment — MULTI_FORMAT §0 / PROGRESS Phase 6.4 deferred).
-- niches RLS=OFF (katalog global, admin via service_role; public-read onboarding tetap).

alter table public.niches
  add column if not exists access_type text not null default 'public',
  add column if not exists exclusive_to text,            -- tenant_id pemilik eksklusif
  add column if not exists exclusive_until timestamptz,  -- public-90d: kapan jadi publik
  add column if not exists released_at timestamptz,      -- kapan masuk katalog publik
  add column if not exists release_scheduled_at timestamptz;

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'chk_niche_access_type') then
    alter table public.niches add constraint chk_niche_access_type
      check (access_type in ('public','pending','private'));
  end if;
end $$;

-- Penjadwalan rilis bulanan (admin curate 1-2 niche/bulan → public catalog).
create table if not exists public.niche_releases (
  id uuid primary key default gen_random_uuid(),
  niche_id varchar not null references public.niches(niche_id) on delete cascade,
  scheduled_at timestamptz not null,
  announced boolean not null default false,
  status text not null default 'scheduled',  -- scheduled | released | cancelled
  created_by text,
  created_at timestamptz not null default now()
);
create index if not exists idx_niche_releases_sched on public.niche_releases (scheduled_at);
alter table public.niche_releases enable row level security;
-- service_role only (admin). (Publik baca niches langsung; jadwal rilis = internal.)
