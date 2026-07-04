-- 0123 — Kolom audit pembayaran (owner 2026-07-04: "jangan dibiarkan ada bug"):
-- transaction_id (referensi transaksi Midtrans) + paid_at (waktu settlement nyata).
-- Sebelumnya data ini hanya terkubur di raw_notification (JSONB) — kini kolom kelas-satu
-- agar ledger bisa di-query/rekonsiliasi tanpa bongkar JSON. Diisi _apply_settlement.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

-- Backfill dari raw_notification untuk transaksi yang sudah terjadi (settlement pertama effi).
UPDATE payments SET
  transaction_id = COALESCE(transaction_id, raw_notification->>'transaction_id'),
  paid_at = COALESCE(paid_at,
    ((COALESCE(raw_notification->>'settlement_time', raw_notification->>'transaction_time')) || '+07:00')::timestamptz)
WHERE raw_notification IS NOT NULL
  AND status IN ('settlement', 'capture');
