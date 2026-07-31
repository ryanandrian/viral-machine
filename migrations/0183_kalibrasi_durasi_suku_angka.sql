-- 0183 — Suku ANGKA pada model durasi: angka diucapkan jauh lebih panjang daripada hurufnya
--
-- MASALAH YANG DISELESAIKAN
-- Model per-huruf (0182) menghitung "1348" sebagai 4 huruf. Kenyataannya suara membacakannya
-- "seribu tiga ratus empat puluh delapan" — enam kata. Diukur langsung (id-ID-GadisNeural, baseline
-- produksi):
--
--     "Pada tahun 1348 wabah itu datang."     27 huruf → 4,94 detik
--     "Pada tahun itu wabah besar datang."    28 huruf → 3,24 detik
--                                             ────────────────────────
--     satu tahun empat-angka                            +1,70 detik
--
-- Akibatnya naskah niche sejarah (penuh tahun) diramal terlalu pendek. Pada satu naskah dark_history
-- preset 90 dtk, ramalan meleset puluhan detik — dan meleset ke arah yang paling merugikan: mesin
-- menyangka naskah masih KURANG panjang, lalu menyuruh penulis menambah, sehingga video jadi
-- kepanjangan.
--
-- YANG DIUKUR — leave-one-out pada render yang SAMA (nol render baru), 5-suku vs 6-suku:
--
--     suara                     5-suku            6-suku (+angka)     hasil
--     en-US-JennyNeural  n=60   0,96 dtk · 88%    0,84 dtk · 97%      lebih baik
--     id-ID-GadisNeural  n=38   1,17 dtk · 84%    1,02 dtk · 89%      lebih baik
--     en-US-Christopher  n=30   1,05 dtk · 80%    1,00 dtk · 90%      lebih baik
--     en-US-GuyNeural    n=30   0,94 dtk · 90%    0,86 dtk · 90%      lebih baik
--     id-ID-ArdiNeural   n=46   1,09 dtk · 89%    1,10 dtk · 89%      setara
--
-- Koefisiennya konsisten lintas suara: 0,123–0,184 detik per digit, DI ATAS biaya hurufnya. Konsisten
-- itu penting — artinya ini sifat cara angka dibacakan, bukan kebetulan satu suara.
--
-- Kolom ini boleh kosong. Kosong = `duration_model` memakai angka bawaan terukur (0,1315 dtk/digit),
-- jadi suara yang belum dikalibrasi tetap ikut terkoreksi — beda dengan mengabaikan angka sama sekali.

ALTER TABLE tts_pace_calibration
  ADD COLUMN IF NOT EXISTS sec_per_digit numeric(7,5);

COMMENT ON COLUMN tts_pace_calibration.sec_per_digit IS
  'Detik TAMBAHAN per digit angka, di atas biaya hurufnya — "1348" (4 huruf) dibacakan sebagai enam kata. Terukur 0,12-0,18 dtk/digit di lima suara produksi (0183).';
