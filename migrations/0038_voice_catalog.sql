-- 0038 — voice_catalog (Phase 10.6). Katalog voice TTS (mock "Voice Templates" tak punya tabel).
-- Voice ElevenLabs/edge per nama+lang+niche-default. tts_profiles = kelas provider; ini = voice individual.
-- RLS ON + public-read (tenant onboarding pilih voice) seperti katalog lain; tulis = service_role/admin.
create table if not exists public.voice_catalog (
  voice_key text primary key,
  provider_key text not null,
  display_name text not null,
  locale text,
  gender text,
  niche_default text,          -- niche_id default (opsional)
  preview_url text,
  is_active boolean not null default true,
  sort_order integer not null default 100,
  updated_at timestamptz not null default now()
);
create index if not exists idx_voice_catalog_active on public.voice_catalog (locale, is_active);
alter table public.voice_catalog enable row level security;
do $$ begin
  if not exists (select 1 from pg_policy where polname='voice_catalog_read' and polrelid='public.voice_catalog'::regclass) then
    create policy voice_catalog_read on public.voice_catalog for select using (true);
  end if;
end $$;
