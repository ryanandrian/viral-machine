-- 0178 — Status alarm drift durasi: satu kunci JSON (median + sedang-alarm? + waktu alarm terakhir)
--
-- SEBAB (laporan owner 2026-07-28): lima hari berturut menerima peringatan yang terasa identik.
-- Angkanya sebenarnya MEMBAIK terus (12,8 → 12,3 → 11,5 → 11,5 → 10,4%) berkat koreksi otomatis,
-- tapi pesan hanya menyebut angka hari itu tanpa pembanding — penyembuhan terbaca sebagai kemacetan.
-- Dan ketika akhirnya normal (27 Jul), tak ada kabar apa pun.
--
-- Untuk menyebut ARAH pergerakan, pemeriksaan perlu mengingat angka sebelumnya; untuk mengabari
-- PEMULIHAN, ia perlu tahu sedang-alarm-atau-tidak. Kunci lama hanya menyimpan waktu, jadi diganti
-- satu kunci JSON. Nilai waktu lama diwariskan supaya rem 24 jam tidak ter-reset oleh migrasi ini.

BEGIN;

INSERT INTO app_config (key, value, value_text, description)
SELECT 'ops_drift_alarm_state', 0,
       json_build_object('last_at', value_text, 'median', NULL, 'alarming', true)::text,
       'OPS (otomatis, jangan diubah manual): status alarm drift durasi — median terakhir, sedang-alarm?, waktu alarm terakhir'
  FROM app_config WHERE key = 'ops_drift_alarm_last_at'
ON CONFLICT (key) DO NOTHING;

-- Bila kunci lama tak ada (lingkungan baru), tetap sediakan status kosong yang sah.
INSERT INTO app_config (key, value, value_text, description)
VALUES ('ops_drift_alarm_state', 0, '{}',
        'OPS (otomatis, jangan diubah manual): status alarm drift durasi — median terakhir, sedang-alarm?, waktu alarm terakhir')
ON CONFLICT (key) DO NOTHING;

-- Kunci lama tak dibaca kode mana pun lagi → buang, jangan tinggalkan penanda basi.
DELETE FROM app_config WHERE key = 'ops_drift_alarm_last_at';

COMMIT;
