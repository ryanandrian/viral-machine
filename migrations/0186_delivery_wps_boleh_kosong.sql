-- 0186 — `delivery_wps` (penggaris LAMA) boleh kosong
--
-- MASALAH YANG DISELESAIKAN
-- `tts_pace_calibration.delivery_wps` adalah penggaris generasi lama: satu angka "kata per detik".
-- Ia sudah DIGANTI oleh model per-huruf (0182/0183) dan hanya tetap diisi agar jalur cadangan tak mati.
-- Tapi kolomnya NOT NULL, sehingga suara BARU tidak bisa punya baris koefisien tanpa lebih dulu
-- mengarang satu angka kata/detik. Terbukti menghalangi 2026-08-01: pengukuran biaya jeda untuk
-- en-US-JennyNeural ditolak DB karena baris barunya tak punya `delivery_wps`.
--
-- Mengarang angka untuk memenuhi batasan kolom adalah cara paling halus menanam ranjau: angka itu
-- nantinya dibaca jalur cadangan sebagai kalibrasi yang sah. Lebih baik KOSONG — jalur cadangan sudah
-- memeriksa `is not None` sebelum memakainya (tenant_config.py), jadi kosong berarti "pakai bawaan
-- terukur", yang memang benar.
--
-- Aman untuk kode yang SEDANG BERJALAN di server: ia membaca kolom ini lewat
-- `val is not None and 1.0 <= val <= 4.0` — nilai kosong sudah ditangani sejak awal.

ALTER TABLE tts_pace_calibration
  ALTER COLUMN delivery_wps DROP NOT NULL;

COMMENT ON COLUMN tts_pace_calibration.delivery_wps IS
  'PENGGARIS LAMA (kata/detik) — digantikan model per-huruf 0182/0183; tetap diisi untuk jalur cadangan preset di luar tangga. Boleh KOSONG: lebih baik kosong (→ angka bawaan terukur) daripada angka karangan yang terbaca sebagai kalibrasi sah (0186).';
