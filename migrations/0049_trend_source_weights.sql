-- 0049: TREND RADAR F2 — source_weights (config-driven, no-hardcode). TREND_RADAR_ARCHITECTURE.md §2b.
-- Bobot = persen kontribusi/representasi tiap sumber ke seleksi topik. app_config.value = integer (persen).
-- Default §2b (dikalibrasi self-improvement F4 dari outcome). YouTube velocity PRIMER.
-- Data-only (tak ubah skema). Idempotent.
insert into public.app_config (key, value, description)
select v.key, v.value, v.description
from (values
  ('trend_weight_youtube',  45, 'Bobot sumber YouTube velocity (persen) — PRIMER. TREND_RADAR §2b.'),
  ('trend_weight_trends',   30, 'Bobot sumber Google Trends (persen) — sekunder.'),
  ('trend_weight_news',     13, 'Bobot sumber Google News (persen) — moderat/niche-flag.'),
  ('trend_weight_wikipedia', 7, 'Bobot sumber Wikipedia (persen) — rendah/filter-only (kandidat drop).'),
  ('trend_weight_hackernews',5, 'Bobot sumber HackerNews (persen) — tech-niche-only (kandidat drop).')
) as v(key, value, description)
where not exists (select 1 from public.app_config a where a.key = v.key);
