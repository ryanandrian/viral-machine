-- 0145_test_result_ttl.sql
-- Batas usang kartu hasil uji channel (owner 2026-07-08: "sampai kapan pesan hasil muncul?").
-- FE channel menyembunyikan kartu hasil uji setelah N jam (selain tombol Tutup per-test + terganti
-- test baru). Admin-editable, no-hardcode; FE fail-soft ke 24 bila baris tak terbaca.

INSERT INTO app_config (key, value, description)
VALUES ('test_result_ttl_hours', 24, 'Berapa jam kartu hasil uji channel tetap tampil sejak selesai (FE fail-soft 24)')
ON CONFLICT (key) DO NOTHING;
