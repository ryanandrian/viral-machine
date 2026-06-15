-- 0043 — Content CMS (admin-managed Blog/Docs/Demo). Marketing pages baca dari DB (public-read published),
-- admin tulis via service_role. Body = markdown (text). Konsisten pola pricing_config/niches (admin-managed).

create table if not exists public.blog_posts (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  title text not null, title_en text,
  excerpt text, excerpt_en text,
  body text not null default '', body_en text,
  category text, cover text,
  status text not null default 'draft',   -- draft | published
  published_at timestamptz,
  sort_order integer not null default 100,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  constraint chk_blog_status check (status in ('draft','published'))
);
create index if not exists idx_blog_pub on public.blog_posts (status, published_at desc);

create table if not exists public.docs_articles (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  grp text not null default 'Lainnya', grp_en text,
  title text not null, title_en text,
  body text not null default '', body_en text,
  status text not null default 'draft',
  sort_order integer not null default 100,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  constraint chk_docs_status check (status in ('draft','published'))
);
create index if not exists idx_docs_pub on public.docs_articles (status, grp, sort_order);

create table if not exists public.demo_tours (
  id uuid primary key default gen_random_uuid(),
  label text not null, label_en text,
  href text not null,
  heading text, heading_en text, caption text, caption_en text,
  bullets jsonb not null default '[]'::jsonb, bullets_en jsonb not null default '[]'::jsonb,
  is_active boolean not null default true,
  sort_order integer not null default 100,
  updated_at timestamptz not null default now()
);

alter table public.blog_posts enable row level security;
alter table public.docs_articles enable row level security;
alter table public.demo_tours enable row level security;

-- public-read HANYA yang published/active; tulis = service_role (admin route).
do $$ begin
  if not exists (select 1 from pg_policy where polname='blog_public_read' and polrelid='public.blog_posts'::regclass) then
    create policy blog_public_read on public.blog_posts for select using (status = 'published');
  end if;
  if not exists (select 1 from pg_policy where polname='docs_public_read' and polrelid='public.docs_articles'::regclass) then
    create policy docs_public_read on public.docs_articles for select using (status = 'published');
  end if;
  if not exists (select 1 from pg_policy where polname='demo_public_read' and polrelid='public.demo_tours'::regclass) then
    create policy demo_public_read on public.demo_tours for select using (is_active = true);
  end if;
end $$;
