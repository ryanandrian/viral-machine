-- 0182 — Kalibrasi durasi PER-HURUF: alat ukur yang menggantikan tebakan
--
-- MASALAH YANG DISELESAIKAN
-- Diukur 2026-07-31 dari 294 produksi nyata: hanya 22% video mendarat di batas titik-tengah owner
-- (preset 60s: 49/227 · preset 90s: 3/10 dengan median 31 detik KEPENDEKAN · preset 15s: 1/6 dengan
-- median 18 detik KEPANJANGAN). Rantai sebabnya:
--
--   1. Estimator durasi meramal `kata ÷ (delivery_wps × 1,10) + Σ jeda_benih`, dengan angka jeda yang
--      BENIH — komentar aslinya sendiri menulis "SEED ... F5-01 kalibrasi per provider → DB", dan
--      kalibrasi itu hanya pernah dikerjakan untuk `delivery_wps`, TIDAK untuk angka jedanya.
--      Diuji pada 60 render naskah produksi: salah rata-rata 7,01 detik; hanya 10% akurat ±2 detik.
--   2. Karena taksirannya salah, anggaran kata salah, dan LLM hanya memenuhi 63–75% anggaran
--      (preset 60s: diminta 149 kata, ditulis 111 · preset 90s: diminta 228, ditulis 144).
--   3. Satu-satunya tambalan yang tersedia: MEMPERLAMBAT SUARA. Terukur dari 59 render terbaru:
--      41% mentok di batas paling lambat (0,70) dan NOL render berjalan di kecepatan normal.
--      Durasi tetap salah, dan mood narasi — barang yang dijual produk ini — rusak.
--      Owner MELARANG tuas kecepatan (keputusan 2026-07-29).
--
-- YANG DIUKUR (leave-one-out: tiap naskah diramal oleh angka yang di-fit TANPA naskah itu, sehingga
-- angka kesalahan yang dilaporkan adalah kesalahan pada data yang belum pernah dilihat)
--
--   suara en-US-JennyNeural (n=60 naskah produksi)   suara id-ID-ArdiNeural (n=46)
--     estimator lama      7,01 dtk · 10% akurat        2,76 dtk · 45%
--     model per KATA      1,55 dtk · 68%               1,84 dtk · 64%
--     model per HURUF     0,96 dtk · 88%  ← dipakai    1,09 dtk · 89%  ← dipakai
--     model per VOKAL     1,27 dtk · 82%               2,04 dtk · 73%
--
-- Suara mengucap HURUF, bukan kata: kata panjang butuh waktu lebih lama, dan panjang kata berbeda
-- antar bahasa (terukur: Inggris 5,07 huruf/kata · Indonesia 5,77). Bentuk rumusnya TIDAK berubah
-- (bicara + jeda per tanda baca) — yang berubah satuan bicaranya dan semua angkanya dikalibrasi.
--
-- Kalibrasi PER-NICHE juga diuji dan TIDAK menang (1,17 dtk) — memecah data per niche membuat tiap
-- sel terlalu tipis. Karena itu angka disimpan pada baris (voice_key, '*'); kunci tabel ini sudah
-- (voice_key, niche) sehingga bila kelak satu niche punya cukup sampel, baris per-niche bisa dipakai
-- TANPA mengubah bentuk apa pun. Niche tetap berdampak lewat jalurnya sendiri (persona narasi, gaya,
-- avoid, visual, musik) — bukan lewat koefisien durasi.
--
-- YANG DIUBAH DI SINI — hanya MENAMBAH kolom, semuanya boleh kosong:
--   • tts_delivery_samples.chars  — jumlah huruf naskah tiap render (bahan kalibrasi; tanpa ini
--     model per-huruf tak bisa dihitung dari data produksi)
--   • tts_pace_calibration.*      — tujuh koefisien + angka kesalahan luar-sampel
--
-- KOSONG = PERILAKU LAMA PERSIS. Modul `src/production/duration_model.py` memakai angka BAWAAN
-- terukur bila baris kalibrasi belum ada, dan angka di luar pagar kewajaran DIBUANG (bukan di-clamp
-- diam-diam) supaya data rusak tidak menyelinap jadi angka yang tampak masuk akal.
--
-- Tabel ini DITULIS MESIN (pace_calibration.py) dan tidak pernah diedit admin — sama seperti kolom
-- `delivery_wps` yang sudah ada di sini. Karena itu tidak ada permukaan admin baru yang lahir dari
-- migrasi ini; yang admin lihat & edit tetap `voice_catalog.delivery_wps` dan `tts_profiles`.

ALTER TABLE tts_delivery_samples
  ADD COLUMN IF NOT EXISTS chars integer;

COMMENT ON COLUMN tts_delivery_samples.chars IS
  'Jumlah huruf/angka naskah (tanpa spasi & tanda baca) — bahan kalibrasi model durasi per-huruf (0182).';

ALTER TABLE tts_pace_calibration
  ADD COLUMN IF NOT EXISTS sec_per_char        numeric(8,5),
  ADD COLUMN IF NOT EXISTS sec_per_sentence    numeric(7,3),
  ADD COLUMN IF NOT EXISTS sec_per_ellipsis    numeric(7,3),
  ADD COLUMN IF NOT EXISTS sec_per_comma       numeric(7,3),
  ADD COLUMN IF NOT EXISTS sec_per_em_dash     numeric(7,3),
  ADD COLUMN IF NOT EXISTS chars_per_word      numeric(6,3),
  ADD COLUMN IF NOT EXISTS words_per_sentence  numeric(6,3),
  ADD COLUMN IF NOT EXISTS calib_error_secs    numeric(7,3);

COMMENT ON COLUMN tts_pace_calibration.sec_per_char IS
  'Detik per huruf (waktu bicara murni). Model: detik = a*huruf + b*kalimat + c*elipsis + d*koma + e*em_dash (0182).';
COMMENT ON COLUMN tts_pace_calibration.sec_per_sentence IS
  'Detik hening tiap akhir kalimat. Terukur 0,60–1,31 dtk; benih lama di kode 0,35 = ~3x terlalu kecil (0182).';
COMMENT ON COLUMN tts_pace_calibration.sec_per_ellipsis IS
  'Detik hening tiap tanda "..." — terukur 0,80–1,38 dtk (benih lama 0,75). Inilah sebab prompt melarang elipsis (0182).';
COMMENT ON COLUMN tts_pace_calibration.sec_per_comma IS
  'Detik hening tiap koma/titik-koma/titik-dua — terukur 0,22–0,27 dtk (benih lama 0,12) (0182).';
COMMENT ON COLUMN tts_pace_calibration.sec_per_em_dash IS
  'Detik hening tiap em-dash — terukur 0,09–0,44 dtk (benih lama 0,55) (0182).';
COMMENT ON COLUMN tts_pace_calibration.chars_per_word IS
  'Huruf per kata (median naskah nyata) — dipakai menerjemahkan target detik jadi perintah JUMLAH KATA ke penulis (0182).';
COMMENT ON COLUMN tts_pace_calibration.words_per_sentence IS
  'Kata per kalimat alami (median naskah nyata) — menjaga perintah jumlah kalimat tetap menghasilkan narasi wajar (0182).';
COMMENT ON COLUMN tts_pace_calibration.calib_error_secs IS
  'Kesalahan LUAR-SAMPEL (leave-one-out) angka di baris ini, detik. Transparansi: dipakai alarm drift & audit (0182).';
