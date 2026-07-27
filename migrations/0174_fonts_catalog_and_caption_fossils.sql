-- 0174 — Katalog font jadi SATU sumber + sapu fosil caption_style
--
-- SEBELUM (bukti audit 2026-07-27):
--   * Tiga daftar font yang berbeda: FE hardcode 5 nama · BE hardcode 1 nama (FONT_FILES) ·
--     tabel `fonts` berisi 1 baris dan TIDAK dibaca siapa pun. Akibatnya 4 dari 5 pilihan font
--     di layar tenant tidak ada di server render → diam-diam diganti DejaVu Sans (26% lebih lebar).
--   * caption_style menyimpan 4 kunci yang TIDAK PERNAH dibaca mesin: margin_v, max_lines,
--     bold_keywords, outline_alpha. Layar Caption menulis balik objek utuh setiap Simpan,
--     jadi fosil itu bereproduksi sendiri dan tak pernah mati.
-- SESUDAH: tabel `fonts` = satu-satunya daftar (FE & BE membacanya), fosil disapu bersih.

BEGIN;

-- 1) URL file font (dipakai FE utk @font-face agar pratinjau memakai huruf yang BENAR-BENAR dipakai
--    mesin render). Pola sama dgn channels.brand_logo: URL penuh disimpan, bukan dirakit di klien.
ALTER TABLE fonts ADD COLUMN IF NOT EXISTS file_url TEXT;

-- 2) Katalog 5 font — file fisik sudah ada di S3 mesinviral-assets/fonts/ (public-read) DAN di
--    /usr/local/share/fonts pada VPS render (fc-cache sudah disegarkan). Semua SIL Open Font License.
INSERT INTO fonts (name, file_name, file_url, is_active) VALUES
  ('Anton',      'Anton-Regular.ttf',      'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/Anton-Regular.ttf',      TRUE),
  ('Bebas Neue', 'BebasNeue-Regular.ttf',  'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/BebasNeue-Regular.ttf',  TRUE),
  ('Montserrat', 'Montserrat-Regular.ttf', 'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/Montserrat-Regular.ttf', TRUE),
  ('Oswald',     'Oswald-Regular.ttf',     'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/Oswald-Regular.ttf',     TRUE),
  ('Poppins',    'Poppins-Regular.ttf',    'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/Poppins-Regular.ttf',    TRUE)
ON CONFLICT DO NOTHING;

-- Baris 'Anton' sudah ada sejak 2026-04 (file_name benar, file_url kosong) → lengkapi, jangan gandakan.
UPDATE fonts SET file_url = 'https://nos.wjv-1.neo.id/mesinviral-assets/fonts/Anton-Regular.ttf'
 WHERE name = 'Anton' AND (file_url IS NULL OR file_url = '');

-- Nama font WAJIB unik: ia dipakai sebagai kunci pencarian oleh FE (pilihan) & BE (nama file).
CREATE UNIQUE INDEX IF NOT EXISTS ux_fonts_name ON fonts (name);

-- 3) Sapu 4 kunci fosil dari SEMUA penyimpan style teks.
UPDATE channels
   SET caption_style = caption_style - 'margin_v' - 'max_lines' - 'bold_keywords' - 'outline_alpha'
 WHERE caption_style ?| array['margin_v','max_lines','bold_keywords','outline_alpha'];

UPDATE tenant_configs
   SET caption_style = caption_style - 'margin_v' - 'max_lines' - 'bold_keywords' - 'outline_alpha'
 WHERE caption_style ?| array['margin_v','max_lines','bold_keywords','outline_alpha'];

UPDATE tenant_configs
   SET hook_title_style = hook_title_style - 'outline_alpha'
 WHERE hook_title_style ? 'outline_alpha';

COMMIT;
