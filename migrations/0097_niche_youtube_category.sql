-- 0097: Kategori YouTube per-niche → DB (REMEDIASI_NICHE_HASHTAG_POOL.md BATCH 5B).
-- Pindahkan hardcode NICHE_CATEGORY (youtube_publisher.py, 4 niche ryan) → kolom DB, dikelola admin
-- (Niche Library) & tenant Business (Niche Studio). Niche tanpa nilai → publisher fallback "27" (Education).
-- categoryId YouTube: 1 Film&Animation · 10 Music · 20 Gaming · 22 People&Blogs · 23 Comedy ·
-- 24 Entertainment · 25 News&Politics · 26 Howto&Style · 27 Education · 28 Science&Technology.

BEGIN;

ALTER TABLE niches ADD COLUMN IF NOT EXISTS youtube_category_id text;

-- Seed 4 niche ryan dari NICHE_CATEGORY lama (proven, reversible).
UPDATE niches SET youtube_category_id = '28' WHERE niche_id = 'universe_mysteries';
UPDATE niches SET youtube_category_id = '27' WHERE niche_id = 'dark_history';
UPDATE niches SET youtube_category_id = '28' WHERE niche_id = 'ocean_mysteries';
UPDATE niches SET youtube_category_id = '27' WHERE niche_id = 'fun_facts';

COMMIT;
