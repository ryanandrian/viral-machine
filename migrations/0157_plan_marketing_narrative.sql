-- 0157 — NARASI MARKETING PER-PAKET + AGREGAT PEMBAYARAN (finalisasi_tier_plan Tahap 3, 2026-07-13).
--
-- (1) plan_limits + kolom narasi (keputusan owner 2026-07-13: "daftar fitur yang dijanjikan tiap tier
--     harus bisa diedit admin via panel — sifatnya narasi"): tagline dwibahasa + badge populer +
--     marketing_features (array [{id,en}] — baris fitur kualitatif; ANGKA fakta channel/video-hari/
--     Niche Studio TETAP dari kolom kuota, tak pernah jadi teks bebas).
--     SEED = teks PERSIS yang hardcode di kartu /pricing hari ini (nol regresi tampilan saat
--     marketing membacanya di Tahap 4; en di-seed = id karena halaman hari ini memang menampilkan
--     satu teks utk kedua bahasa — owner memoles terjemahan dari editor).
--     Idempotent: seed hanya bila tagline_id masih NULL.
--
-- (2) admin_payments_stats(): agregat pendapatan/hitungan SELURUH tabel payments di DB (fix kelas
--     "baca-terpotong-senyap": kartu revenue admin dulu menjumlah maks 500 baris terakhir).
--     SECURITY DEFINER + hanya service_role (route admin Next) yang boleh eksekusi.
BEGIN;

ALTER TABLE plan_limits
  ADD COLUMN IF NOT EXISTS tagline_id TEXT,
  ADD COLUMN IF NOT EXISTS tagline_en TEXT,
  ADD COLUMN IF NOT EXISTS is_popular BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS marketing_features JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE plan_limits SET
  tagline_id = 'Untuk mulai scaling', tagline_en = 'To start scaling',
  is_popular = FALSE,
  marketing_features = '[{"id":"Niche dasar","en":"Niche dasar"},{"id":"Self-learning","en":"Self-learning"},{"id":"Telegram notif","en":"Telegram notif"}]'::jsonb
WHERE plan_type = 'starter' AND tagline_id IS NULL;

UPDATE plan_limits SET
  tagline_id = 'Paling diminati creator serius', tagline_en = 'Most chosen by serious creators',
  is_popular = TRUE,
  marketing_features = '[{"id":"Semua niche","en":"Semua niche"},{"id":"Quality Gate + Compliance","en":"Quality Gate + Compliance"},{"id":"Custom voice","en":"Custom voice"},{"id":"Captions & hashtags","en":"Captions & hashtags"}]'::jsonb
WHERE plan_type = 'pro' AND tagline_id IS NULL;

UPDATE plan_limits SET
  tagline_id = 'Untuk agency & power user', tagline_en = 'For agencies & power users',
  is_popular = FALSE,
  marketing_features = '[{"id":"Priority queue","en":"Priority queue"},{"id":"Multi-channel dashboard","en":"Multi-channel dashboard"},{"id":"Webhook & API","en":"Webhook & API"},{"id":"Quiet hours","en":"Quiet hours"}]'::jsonb
WHERE plan_type = 'business' AND tagline_id IS NULL;

CREATE OR REPLACE FUNCTION admin_payments_stats()
RETURNS TABLE (revenue_idr BIGINT, settled_count BIGINT, pending_count BIGINT, total_count BIGINT)
LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
  SELECT
    COALESCE(SUM(gross_amount) FILTER (WHERE lower(status) IN ('settlement','capture','paid')), 0)::bigint,
    COUNT(*)  FILTER (WHERE lower(status) IN ('settlement','capture','paid'))::bigint,
    COUNT(*)  FILTER (WHERE status = 'pending')::bigint,
    COUNT(*)::bigint
  FROM payments;
$$;
REVOKE ALL ON FUNCTION admin_payments_stats() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION admin_payments_stats() TO service_role;

COMMIT;
