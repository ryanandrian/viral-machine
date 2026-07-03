-- 0115 — Showcase (pengganti /demo): keputusan owner 2026-07-03.
-- /demo lama (iframe route internal + "open live screen") TIDAK MASUK AKAL utk calon tenant belum-login
-- (semua tab menampilkan halaman login). Diganti: (1) screenshot halaman tenant (4-8, admin-managed) +
-- (2) galeri contoh konten hasil mesin (video MP4 di S3, TANPA batas — bertambah seiring niche baru).
-- Dwibahasa ID/EN di level konten (kolom *_en). RLS: publik baca hanya is_active (pola demo_tours/blog_posts).

CREATE TABLE IF NOT EXISTS showcase_screens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text,                       -- label layar (ID), mis. "Dashboard"
  title_en    text,
  caption     text,                       -- 1 kalimat keterangan (ID)
  caption_en  text,
  image_url   text NOT NULL,              -- S3 mesinviral-assets/showcase-screens/
  sort_order  integer DEFAULT 0,
  is_active   boolean DEFAULT true,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS showcase_videos (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title          text,                    -- judul konten (ID)
  title_en       text,
  description    text,                    -- keterangan singkat (ID)
  description_en text,
  niche_label    text,                    -- label niche bebas, mis. "Ocean Mystery"
  video_url      text NOT NULL,           -- S3 mesinviral-assets/showcase-videos/ (MP4 9:16)
  poster_url     text,                    -- opsional (thumbnail sebelum play)
  sort_order     integer DEFAULT 0,
  is_active      boolean DEFAULT true,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now()
);

ALTER TABLE showcase_screens ENABLE ROW LEVEL SECURITY;
ALTER TABLE showcase_videos  ENABLE ROW LEVEL SECURITY;
CREATE POLICY showcase_screens_public_read ON showcase_screens FOR SELECT USING (is_active = true);
CREATE POLICY showcase_videos_public_read  ON showcase_videos  FOR SELECT USING (is_active = true);

-- demo_tours = fosil /demo lama (iframe tour). Pembaca lama (page /demo + CMS tab Demo) dihapus di commit yang sama.
DROP TABLE IF EXISTS demo_tours;
