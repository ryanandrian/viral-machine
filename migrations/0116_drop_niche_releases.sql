-- 0116 — HAPUS TUNTAS "Jadwal Rilis Bulanan" (keputusan owner 2026-07-04).
-- Fakta terverifikasi: penjadwal HANYA menulis (niche_releases + niches.release_scheduled_at + set
-- access_type='pending') — TIDAK ADA eksekutor (worker/cron/route) yang merilis pada tanggalnya →
-- niche 'pending' tersembunyi selamanya (jebakan). niche_releases = 0 baris (tak pernah dipakai).
-- FE card + route /api/admin/niche-releases + opsi 'pending' dihapus di commit yang sama.

DROP TABLE IF EXISTS niche_releases;
ALTER TABLE niches DROP COLUMN IF EXISTS release_scheduled_at;

-- 'pending' keluar dari enum access_type (tak ada penulis lagi; 0 baris pending saat migrasi).
ALTER TABLE niches DROP CONSTRAINT IF EXISTS chk_niche_access_type;
ALTER TABLE niches ADD CONSTRAINT chk_niche_access_type
  CHECK (access_type = ANY (ARRAY['public'::text, 'private'::text]));
