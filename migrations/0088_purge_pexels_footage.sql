-- 0088: Purge Pexels / stock-footage (fosil v1) — Visual v2 = GENERATOR AI saja
-- ============================================================================
-- Owner 2026-06-24: Pexels = LIBRARY stok gambar/video (footage), BUKAN generator AI.
-- Visual v2 hanya generator AI: visual_mode 'ai_image:<model>' atau 'ai_video:<model>'.
-- Nilai footage lama 'video' + provider 'pexels' + kolom fallback footage = dibuang.
--
-- Catatan: 'ai_video:<model>' (video GENERATOR) TETAP warga kelas-satu (beda dari footage 'video').
-- Hanya nilai footage bare 'video' dan provider 'pexels' yang discrub.

-- channels: visual_mode footage 'video' → null (paksa rekonfigurasi ke generator AI; gerbang akan
--           tandai 'jenis visual' kurang sampai tenant pilih ai_image:/ai_video:)
update channels set visual_mode = null where visual_mode = 'video';

-- tenant_configs: footage 'video' → null; provider footage 'pexels' → null (legacy; sumber kebenaran = channels)
update tenant_configs set visual_mode = null where visual_mode = 'video';
update tenant_configs set visual_provider = null where visual_provider = 'pexels';

-- TUTUP vektor reintroduksi: DEFAULT kolom masih 'video'/'pexels' → baris baru memunculkan footage lagi.
-- Drop default → tenant baru NULL (sumber kebenaran = channels.visual_mode generator AI).
alter table tenant_configs alter column visual_mode     drop default;
alter table tenant_configs alter column visual_provider drop default;

-- drop kolom fosil v1: visual_fallback_mode (fallback footage, default 'video') — tak dikonsumsi kode pasca-purge
alter table tenant_configs drop column if exists visual_fallback_mode;
