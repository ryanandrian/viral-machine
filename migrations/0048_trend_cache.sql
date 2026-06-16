-- 0048: TREND RADAR F1 — trend_cache (decouple + cache + shared).
-- TREND_RADAR_ARCHITECTURE.md §3 Pilar-1 + §5. Memecahkan M1 (429 IP-based):
-- fetch 1× per (niche, geo, source, timeframe) per TTL oleh TrendRefresher (worker),
-- produce BACA cache → NOL fetch eksternal di hot-path → request_sumber KONSTAN vs jumlah tenant.
-- Data SHARED lintas-tenant (per niche+geo, bukan per-tenant) → service-role only.

create table if not exists public.trend_cache (
  id          bigint generated always as identity primary key,
  cache_key   text not null unique,           -- "{niche}|{geo}|{source}|{timeframe}"
  niche       text not null,
  geo         text not null default 'US',
  source      text not null,                  -- google_trends | youtube | google_news | wikipedia | hackernews | youtube_autocomplete | ...
  timeframe   text,
  signals     jsonb not null default '[]'::jsonb,
  fetched_at  timestamptz not null default now(),
  ttl_sec     integer not null default 43200, -- default 12 jam; refresher pakai app_config.trend_cache_ttl_sec
  created_at  timestamptz not null default now()
);
create index if not exists idx_trend_cache_niche_geo on public.trend_cache (niche, geo);
create index if not exists idx_trend_cache_fetched   on public.trend_cache (fetched_at);

-- RLS: service-role only (worker refresher tulis, produce baca). Sengaja TANPA policy
-- → anon/authenticated tak akses; FE tak perlu trend_cache.
alter table public.trend_cache enable row level security;

-- Config TrendRefresher (no-hardcode; app_config.value = integer). Idempotent tanpa butuh unique-constraint.
insert into public.app_config (key, value, description)
select v.key, v.value, v.description
from (values
  ('trend_cache_ttl_sec',     43200, 'TTL cache tren (detik) sebelum basi — TrendRefresher fetch ulang. Default 12 jam.'),
  ('trend_refresh_pacing_ms', 3000,  'Jeda antar-request sumber eksternal di TrendRefresher (ms) — jaga di bawah rate-limit (anti-429).')
) as v(key, value, description)
where not exists (select 1 from public.app_config a where a.key = v.key);
