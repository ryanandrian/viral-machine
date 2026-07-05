-- 0130 — Gerbang pesan niche custom per-tier jadi CONFIG-DRIVEN (keputusan owner 2026-07-05).
-- TEMUAN: RLS insert niche_requests hanya cek kepemilikan (tenant_id = auth.uid()) — tenant TRIAL
--   bisa mengajukan pesanan niche custom, padahal keputusan owner: trial TIDAK boleh mengajukan.
-- FIX: plan_limits.can_request_custom_niche (admin-tunable, pola identik full_niche_catalog 0124)
--   + RLS insert niche_requests diperketat: hanya tier dengan flag = true.
--   Seed: tier BERBAYAR (starter/pro/business) = boleh; trial = tidak.

BEGIN;

ALTER TABLE plan_limits ADD COLUMN IF NOT EXISTS can_request_custom_niche BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE plan_limits SET can_request_custom_niche = (plan_type IN ('starter', 'pro', 'business'));

-- RLS: pesanan hanya dari tenant yang tier-nya berhak (config-driven, bukan daftar tier hardcode).
DROP POLICY IF EXISTS niche_requests_tenant_insert ON niche_requests;
CREATE POLICY niche_requests_tenant_insert ON niche_requests
  FOR INSERT
  WITH CHECK (
    tenant_id = (auth.uid())::text
    AND EXISTS (
      SELECT 1
      FROM tenant_configs tc
      JOIN plan_limits pl ON pl.plan_type = tc.plan_type
      WHERE tc.tenant_id = (auth.uid())::text
        AND COALESCE(pl.can_request_custom_niche, FALSE)
    )
  );

COMMIT;
