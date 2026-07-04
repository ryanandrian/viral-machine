-- 0119 — Test niche utk TENANT (Niche Studio; NICHE_DNA F5, disepakati owner 2026-07-04).
-- job_type baru 'test_nopub': produksi penuh TANPA publish memakai kredensial+channel tenant sendiri.
-- Video test (admin & tenant) kini pakai content_inventory.status='test' (tak pernah diklaim publisher;
-- TTL janitor; TIDAK mengotori antrean /review). content_inventory TIDAK punya CHECK status → nol DDL.
-- ⚠️ constraint ganda beda nama (pola sama insiden 0117): chk_direct_jobs_type LAMA ikut di-drop.
ALTER TABLE direct_jobs DROP CONSTRAINT IF EXISTS direct_jobs_job_type_check;
ALTER TABLE direct_jobs DROP CONSTRAINT IF EXISTS chk_direct_jobs_job_type;
ALTER TABLE direct_jobs DROP CONSTRAINT IF EXISTS chk_direct_jobs_type;
ALTER TABLE direct_jobs ADD CONSTRAINT direct_jobs_job_type_check
  CHECK (job_type = ANY (ARRAY['test'::text, 'retry'::text, 'admin_test'::text, 'test_nopub'::text]));
