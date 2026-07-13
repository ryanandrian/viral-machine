-- 0159 — TUTUP AKSES PUBLIK LANGSUNG ke company_profile (temuan keamanan 2026-07-13, mandat owner).
-- SEBELUM: policy SELECT `true` → kunci publik (anon, tertanam di browser) bisa membaca SEMUA kolom
-- termasuk admin_telegram_chat_id / NPWP / NIB / telepon — melanggar least-privilege.
-- SESUDAH: RLS tetap AKTIF tanpa policy SELECT → anon & authenticated TERTUTUP total.
-- Jalur yang TETAP JALAN (kunci server / service_role, bypass RLS — diverifikasi grep seluruh repo):
--   invoice API · /api/contact · /api/public/company (pintu resmi whitelist: website,email,legal_name —
--   kini +legal_name utk © footer/auth) · /api/admin/company-profile · worker Python (telegram admin).
-- Pembaca kunci-publik langsung satu-satunya (footer/auth, belum pernah ter-deploy) sudah dialihkan
-- ke pintu resmi di commit yang sama → NOL dampak produksi.
BEGIN;

DROP POLICY IF EXISTS company_profile_read ON company_profile;

COMMIT;
