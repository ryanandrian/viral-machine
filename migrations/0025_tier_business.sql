-- 0025 — Rename tier tertinggi → 'business' (keputusan owner 2026-06-14: Trial→Starter→Pro→Business).
-- Samakan naming nyasar: plan_limits 'agency' + pricing_config 'plan_scale' → 'business'/'plan_business'.
-- Enterprise = ditunda V3. "agency"/"scale" sbg KATA di copy/CSS TIDAK diubah (itu deskriptif, bukan tier).
UPDATE plan_limits     SET plan_type = 'business' WHERE plan_type = 'agency';
UPDATE pricing_config  SET key = 'plan_business', description = 'Langganan Business / bulan'
       WHERE key = 'plan_scale';
UPDATE tenant_configs  SET plan_type = 'business' WHERE plan_type = 'agency';
