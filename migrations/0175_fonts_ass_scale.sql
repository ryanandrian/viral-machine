-- 0175 — Faktor skala render per font, supaya PRATINJAU di layar tenant = HASIL video
--
-- SEBAB: libass (mesin subtitle) menskalakan huruf agar (usWinAscent + usWinDescent) = Fontsize,
-- BUKAN em seperti browser. Akibatnya "119px" di mesin render TIDAK sama besarnya dengan "119px"
-- di CSS — selisihnya 31–79% tergantung font (terverifikasi lewat 120 render nyata, 2026-07-27).
-- Tanpa faktor ini, pratinjau caption mustahil cocok dengan video, berapa pun angka skalanya disetel.
--
-- ass_scale = unitsPerEm / (usWinAscent + usWinDescent), dibaca langsung dari file font.
-- Ukuran CSS yang setara = font_size * ass_scale * (lebar_pratinjau / 1080).

BEGIN;

ALTER TABLE fonts ADD COLUMN IF NOT EXISTS ass_scale NUMERIC;

COMMENT ON COLUMN fonts.ass_scale IS
  'unitsPerEm/(usWinAscent+usWinDescent) — pengali agar ukuran huruf di layar = ukuran di video render (libass).';

UPDATE fonts SET ass_scale = 0.576901 WHERE name = 'Anton';       -- 2048/3550
UPDATE fonts SET ass_scale = 0.769231 WHERE name = 'Bebas Neue';  -- 1000/1300
UPDATE fonts SET ass_scale = 0.640205 WHERE name = 'Montserrat';  -- 1000/1562
UPDATE fonts SET ass_scale = 0.587544 WHERE name = 'Oswald';      -- 1000/1702
UPDATE fonts SET ass_scale = 0.567537 WHERE name = 'Poppins';     -- 1000/1762

COMMIT;
