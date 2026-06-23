-- 0085 — Musik kunci OPAK: r2_key (fosil Cloudflare R2 v1) → object_key (S3 Biznet Gio, opaque 'music/{id}.mp3').
-- §10.G / owner 2026-06-23. Kunci opak = decouple storage dari taksonomi → bunuh kelas-bug double-prefix
-- (path bermakna 'niche/mood/file' diulang di r2_key). EXPAND: add+populate object_key (= 'music/'||id||'.mp3').
-- Selector dialihkan ke object_key (kode); objek S3 di-copy ke key opak (script). r2_key di-DROP migr 0086
-- SETELAH deploy + render-confirm. Aman & reversibel.
ALTER TABLE music_library ADD COLUMN IF NOT EXISTS object_key text;
UPDATE music_library SET object_key = 'music/' || id::text || '.mp3' WHERE object_key IS NULL OR object_key = '';
