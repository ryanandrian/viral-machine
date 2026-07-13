-- 0160 — [B15] VIDEO TERHAPUS/DI-PRIVATE DI YOUTUBE → KELUAR DARI PEMBELAJARAN (ketok owner 2026-07-14).
-- Pemicu nyata: insiden 2026-07-11 (konten dihapus owner tetap dipelajari mesin) + 2026-07-13
-- (3 video hantu terdeteksi "tidak ditemukan" di sapu, dibuang kuota tiap hari).
-- Status baru `delisted`: di-set OTOMATIS oleh sapu analytics saat YouTube menjawab video tak ada
-- (deleted) atau privacyStatus=private. Efek berantai OTOMATIS via filter status='published' yang
-- sudah ada: sapu analytics berhenti · viral_weight_optimizer · RPC learning_curve (0150) ·
-- compliance · dedup topik (topik boleh dipakai ulang) · hitungan FE. performance_analyzer
-- (baca video_analytics langsung) diberi filter eksplisit di kode. REVERSIBLE: salah tanda →
-- set kembali 'published' (snapshot analytics historis TIDAK dihapus).
BEGIN;

-- Constraint LAMA bernama chk_video_status (ketahuan saat verifikasi terapan — dua-duanya di-drop
-- agar idempotent, lalu satu constraint kanonik dibuat ulang).
ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_video_status;
ALTER TABLE videos DROP CONSTRAINT IF EXISTS videos_status_check;
ALTER TABLE videos ADD CONSTRAINT videos_status_check
  CHECK (status = ANY (ARRAY['published'::text, 'qc_failed'::text, 'failed'::text, 'delisted'::text]));

COMMIT;
