-- 0153 — Tombol Help kontekstual = SOFTCODE (mandat owner 2026-07-11; ganti pasangan hardcode FE)
-- ============================================================================
-- Pemetaan lokasi-tombol → artikel panduan pindah ke DB, dikelola admin panel (Content →
-- Tombol Help; dropdown HANYA artikel published = anti-human-error di titik input).
-- Registry LOKASI tetap di kode (apps/web/src/lib/help-links.ts — titik fisik tombol memang
-- hidup di halaman); yang softcode = artikel TUJUANNYA. Seed = pasangan yang berlaku saat ini
-- → nol perubahan perilaku saat tayang.
-- `help_links_effective` = view yang MENGGUGURKAN tujuan bila artikelnya tidak published →
-- pembaca tenant otomatis jatuh ke bawaan (fail-soft ditegakkan di satu titik, bukan di tiap FE).
-- ============================================================================

create table if not exists help_links (
  location_key text primary key,
  article_slug text not null,
  updated_at   timestamptz not null default now()
);

alter table help_links enable row level security;
drop policy if exists help_links_read on help_links;
create policy help_links_read on help_links for select to authenticated using (true);
revoke all on help_links from anon;  -- anon tak berurusan (RLS sudah menyaring 0 baris; ini merapikan grant default)
-- tulis = service-role saja (route admin ber-guard super-admin; RLS tanpa policy insert/update)

-- Seed = pasangan hardcode yang berlaku 2026-07-11 (idempotent; sengaja TIDAK menimpa editan admin)
insert into help_links (location_key, article_slug) values
  ('integrations',   'api-keys'),
  ('niches',         'niches'),
  ('channels',       'membuat-channel'),
  ('channel-new',    'membuat-channel'),
  ('channel-detail', 'pengaturan-channel'),
  ('runs',           'runs-produksi'),
  ('review',         'review-video'),
  ('analytics',      'analytics'),
  ('schedule',       'schedule'),
  ('compliance',     'ai-slop-defense'),
  ('insights',       'self-learning'),
  ('niche-studio',   'niche-studio'),
  ('billing',        'billing'),
  ('settings',       'kelola-akun'),
  ('support',        'bantuan'),
  ('onboarding',     'onboarding')
on conflict (location_key) do nothing;

-- View EFEKTIF: slug gugur (null) bila artikel tak lagi published → pembaca pakai bawaan.
create or replace view help_links_effective as
  select h.location_key,
         case when exists (select 1 from docs_articles d
                           where d.slug = h.article_slug and d.status = 'published')
              then h.article_slug end as article_slug
  from help_links h;

revoke all on help_links_effective from public, anon;
grant select on help_links_effective to authenticated;
