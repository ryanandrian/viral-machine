-- 0110 — Masukan/feedback tenant (tujuan link email trial-lapse & reminder + halaman /feedback publik).
-- Alasan churn TERSTRUKTUR (data actionable) + saran bebas. Anonim boleh (tenant belum login saat klik email).
CREATE TABLE IF NOT EXISTS feedback_submissions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   text,                                   -- opsional (dari ?ref / sesi) — anonim boleh
  reason      text,                                   -- price | features | results | not_ready | other
  message     text,
  email       text,                                   -- opsional (bila diisi pengunjung)
  source      text DEFAULT 'feedback_page',           -- feedback_page | trial_lapse | trial_ending | ...
  created_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback_submissions (created_at DESC);

-- Service-role only (insert via API server, baca via admin). Tanpa policy = tenant/anon TAK akses langsung.
ALTER TABLE feedback_submissions ENABLE ROW LEVEL SECURITY;
