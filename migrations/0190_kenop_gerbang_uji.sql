-- 0190 — Kenop GERBANG UJI PRODUKSI (SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10d)
--
-- MASALAH YANG DISELESAIKAN (deep-dive 2026-08-02, perintah owner)
-- Empat pintu di aplikasi menghasilkan video JADI tanpa pernah memeriksa status langganan:
--   1. "Uji produksi channel"  → mengunggah video PRIVAT ke YouTube Studio milik tenant
--   2. "Uji niche" (Niche Studio) → menyajikan tautan unduh video jadi
--   3. "Jalankan ulang" di halaman riwayat → mengunggah video PRIVAT ke YouTube tenant
--   4. Pratinjau stok gudang → tautan unduh video yang belum terbit
-- Video privat di YouTube Studio bisa diubah menjadi Publik oleh pemiliknya kapan saja. Artinya
-- tenant yang masa cobanya sudah habis tetap bisa memanen konten tanpa pernah berlangganan.
-- Bukti nyata di data produksi: satu tenant berstatus masa-coba (jatah resmi 1 video/hari) menekan
-- tombol uji 11 kali dan 7 di antaranya berhasil terbit.
--
-- Yang bocor adalah NILAI, bukan biaya: biaya AI ditanggung kunci tenant sendiri (BYOK) — tidak ada
-- satu pun jalur yang menjatuhkan biaya AI ke kunci platform.
--
-- KENAPA JADI KENOP, BUKAN ANGKA DI KODE
-- Owner harus bisa menggeser kebijakan ini tanpa deploy: menambah status yang boleh menguji,
-- mengubah jatah, mengganti cara menghitung, bahkan MEMATIKAN seluruh gerbang seketika bila ada
-- yang meleset. `test_gate_enabled = 0` mengembalikan perilaku persis seperti sebelum migrasi ini.
--
-- Migrasi ini HANYA menanam kenop; perilakunya diaktifkan oleh 0191 (fungsi + aturan akses).

INSERT INTO app_config (key, value, value_text, description) VALUES

 ('test_gate_enabled', 1, NULL,
  'SAKLAR INDUK gerbang uji. 1 = tenant yang langganannya tidak aktif TIDAK bisa menjalankan uji '
  'produksi / uji niche / jalankan-ulang. 0 = gerbang dimatikan total, perilaku kembali seperti '
  'sebelum gerbang dipasang (jaring pengaman: bisa dimatikan seketika tanpa deploy).'),

 ('test_allowed_statuses', 0, '["active","trial"]',
  'Daftar status langganan yang BOLEH menjalankan uji. Ditulis sebagai daftar dalam tanda kurung '
  'siku. Pilihan yang sah: active, trial, grace, trial_expired, suspended, cancelled, blocked. '
  'Catatan: status "grace" (masa tenggang) sengaja TIDAK termasuk — produksi rutinnya tetap jalan, '
  'tapi tombol ujinya dikunci sampai tagihan dibayar.'),

 ('trial_test_quota', 3, NULL,
  'Jatah uji untuk tenant masa coba (berapa video uji yang boleh dihasilkan sepanjang masa coba). '
  '0 = tanpa batas. Tenant berbayar tidak dibatasi kenop ini.'),

 ('trial_test_quota_counts', 0, 'success',
  'Apa yang memotong jatah uji masa coba. "success" = hanya uji yang BERHASIL menghasilkan video '
  '(uji yang gagal karena kredensial/kuota tidak menghukum tenant). "all" = setiap percobaan '
  'memotong jatah, berhasil maupun gagal.'),

 ('trial_quota_reset_on_extend', 1, NULL,
  'Saat admin memperpanjang masa coba seseorang secara sengaja, apakah jatah ujinya ikut segar '
  'kembali? 1 = ya (perpanjangan admin berarti memang sedang diberi kesempatan). 0 = tidak, jatah '
  'tetap dihitung sejak masa coba pertama kali dimulai.'),

 ('auto_resume_on_reactivate', 1, NULL,
  'Saat langganan tenant aktif kembali (bayar, atau diaktifkan admin), apakah channel yang berstatus '
  '"Dihentikan sistem" otomatis dijalankan lagi? 1 = ya, tenant tidak perlu menekan apa pun. '
  '0 = tidak, tenant harus memulihkan channelnya sendiri.')

ON CONFLICT (key) DO NOTHING;
