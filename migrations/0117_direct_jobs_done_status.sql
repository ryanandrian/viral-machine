-- 0117 — Test niche TANPA publish (keputusan owner 2026-07-04, Fase 1 Test Lab).
-- direct_jobs test admin kini berakhir 'done' (video jadi → S3/buffer, TIDAK di-upload YouTube).
-- 'published' tetap utk jalur direct tenant (test/retry) yang memang publish private.
ALTER TABLE direct_jobs DROP CONSTRAINT IF EXISTS direct_jobs_status_check;
ALTER TABLE direct_jobs ADD CONSTRAINT direct_jobs_status_check
  CHECK (status = ANY (ARRAY['pending'::text, 'producing'::text, 'published'::text, 'done'::text, 'failed'::text]));
