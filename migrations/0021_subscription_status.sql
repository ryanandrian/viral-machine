-- 0021 — Subscription state gate (Phase 8a, DESAIN §4/§8). Monetisasi: unpaid → STOP produksi.
-- Menutup field `status` yang [[decisions_auth_rbac]] rencanakan (plan_type sudah ada, status belum).
-- subscription_status: active | trial | grace | suspended | cancelled. DEFAULT 'active' (back-compat).
-- current_period_end: akhir periode bayar (untuk grace/expiry; diisi webhook Midtrans Phase 8b).
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active';
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;
UPDATE tenant_configs SET subscription_status = 'active' WHERE subscription_status IS NULL;
