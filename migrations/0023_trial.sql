-- 0023 — Trial enforcement (Phase 8, DESAIN §3). Trial 7-hari + limit 5 video total + platform-AI.
-- subscription_status='trial' + current_period_end = akhir trial (now+7d) + trial_started_at = anchor
-- penghitungan kuota video trial. Expiry trial → 'suspended' (wajib langganan), BUKAN grace.
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ;
