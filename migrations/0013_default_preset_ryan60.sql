-- 0013 — Default duration preset (DB-driven, BUKAN hardcode) + channel ryan = 60s (ikut V1)
-- Arahan owner: default platform = 45s (tengah), disimpan di DB (admin bisa ubah flag).
-- Channel owner (ryan, tenant #1) = 60s mengikuti V1 (~1 menit), format viral_mystery.

-- Flag default platform di katalog (admin flip utk ganti default; resolver: channel.preset ?? default)
ALTER TABLE duration_presets ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT false;
UPDATE duration_presets SET is_default = (seconds = 45);   -- 45s = default; sisanya false

-- Channel ryan (tenant pertama) ikut V1: 60s + viral_mystery (WPS per-format §3 = 2.4)
UPDATE channels
   SET duration_preset = 60,
       format_profile  = 'viral_mystery'
 WHERE tenant_id = (SELECT tenant_id FROM tenant_configs LIMIT 1);
