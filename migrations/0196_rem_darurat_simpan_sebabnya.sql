-- 0196 — Rem darurat channel MENYIMPAN SEBABNYA (kelas error), bukan hanya "gagal 3×"
-- SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8a (celah terbuka) + §9 (kontrak tampilan per-kelas).
--
-- MASALAH (terukur pada tenant BERBAYAR, bukan teori)
-- Saat rem darurat menyala, sistem SUDAH TAHU kelas errornya — `inventory.latest_failure()` membacanya
-- justru untuk memutuskan apakah harus mengerem cepat. Tapi kelas itu **dibuang**: yang tersimpan hanya
-- kalimat generik "3x produksi beruntun gagal/bermasalah".
--
-- Akibatnya layar & notifikasi hanya bisa menganjurkan tebakan ("mis. saldo/kredensial AI"), dan tenant
-- tak pernah tahu pertanyaan yang paling menentukan: **apakah ini pulih sendiri, atau saya harus
-- bertindak?**
--   • Bang Us-Dat (berbayar) mati ±44 jam karena jatah harian penyedia habis — sebab yang pulih sendiri
--     keesokan harinya. Ia bahkan sudah 2× produksi sukses sesudahnya; remnya tetap menyala.
--   • BISIK NUSANTARA (berbayar) mati dengan pola yang sama sehari kemudian.
--
-- Migrasi ini TIDAK mengubah perilaku apa pun. Ia hanya menyediakan tempat agar informasi yang sudah
-- dimiliki sistem berhenti dibuang. Yang memakainya: panel pemulihan per-KELAS di layar channel.
--
-- KENAPA KELAS, BUKAN NAMA PENYEDIA (arahan owner 2026-08-03)
-- Katalog penyedia & model akan terus bertambah. Kelas error berjumlah tujuh dan stabil. Penyedia baru
-- cukup dipetakan ke kelas di registry (§4 SSOT) → otomatis mendapat pesan & anjuran yang benar tanpa
-- satu baris kode UI baru. Menyimpan nama penyedia di sini akan mengundang percabangan per-merek.

ALTER TABLE channels ADD COLUMN IF NOT EXISTS production_paused_class text;

COMMENT ON COLUMN channels.production_paused_class IS
  'Kelas error (src/exceptions.py ErrorClass) dari kegagalan yang MENYALAKAN rem darurat: '
  'account_billing · quota_exhausted · auth_invalid · model_unavailable · rate_limit · transient · '
  'unknown. NULL = rem menyala sebelum kolom ini ada, atau kelasnya tak terbaca. Dipakai layar & '
  'notifikasi untuk memilih penjelasan + anjuran PER-KELAS (tidak pernah per nama penyedia). '
  'SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §9.';

-- Kolom ini ditulis MESIN (jalur produksi), sama seperti production_paused* lainnya, dan sudah
-- terlindung trigger `channels_rem_readonly` (migr 0195): pemanggil ber-sesi tak bisa mengubah rem.
-- Kolom baru ini sengaja TIDAK ditambahkan ke daftar trigger tsb — ia hanya keterangan, bukan saklar;
-- yang menentukan produksi berhenti/jalan tetap `production_paused`. Mengunci keterangan tanpa mengunci
-- saklarnya hanya menambah permukaan tanpa menambah keamanan.
