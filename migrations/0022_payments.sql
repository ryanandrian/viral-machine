-- 0022 — Payments/orders (Phase 8b, Midtrans Snap). Audit + invoice history (feed D13 Billing).
-- 1 row per transaksi checkout. order_id = referensi Midtrans (unik). Webhook update status.
CREATE TABLE IF NOT EXISTS payments (
  order_id            TEXT PRIMARY KEY,                  -- referensi Midtrans (kita generate)
  tenant_id           TEXT NOT NULL,
  plan_type           TEXT,                              -- paket yang dibeli (starter|pro|agency)
  gross_amount        INTEGER NOT NULL,                  -- IDR (dari pricing_config)
  currency            TEXT DEFAULT 'IDR',
  status              TEXT DEFAULT 'pending',            -- pending|settlement|capture|deny|expire|cancel|refund
  payment_type        TEXT,                              -- gopay|qris|bank_transfer|credit_card|...
  snap_token          TEXT,
  fraud_status        TEXT,
  period_start        TIMESTAMPTZ,
  period_end          TIMESTAMPTZ,                       -- akhir langganan (untuk current_period_end tenant)
  raw_notification    JSONB,                             -- payload webhook terakhir (audit)
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id, created_at DESC);

-- RLS: tenant lihat invoice sendiri; service_role (worker/webhook) full. Selaras pola tenant tables.
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS payments_tenant_read ON payments;
CREATE POLICY payments_tenant_read ON payments FOR SELECT USING (tenant_id = auth.uid()::text);
