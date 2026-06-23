-- 0086 — Bersih fosil musik: drop r2_key (nama Cloudflare R2 v1) + pixabay_id + netralkan source default.
-- object_key (opak §10.G) = sumber tunggal kunci S3 Biznet Gio. BE selector (d005306) + FE catalog/upload (928da8d)
-- sudah pakai object_key (deployed). Dead-code _download_from_r2 + config.r2_* + R2 env-readers dihapus (commit BE).
ALTER TABLE music_library DROP COLUMN IF EXISTS r2_key;
ALTER TABLE music_library DROP COLUMN IF EXISTS pixabay_id;
ALTER TABLE music_library ALTER COLUMN source DROP DEFAULT;
