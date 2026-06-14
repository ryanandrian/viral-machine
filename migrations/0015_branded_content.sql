-- 0015 — Branded Content (MULTI_FORMAT §6/§9): logo overlay + soft-sell CTA + link deskripsi.
-- Field per-channel, NULLABLE = non-breaking (null → tanpa branding, perilaku sekarang).
-- Anti-hard-sell TETAP: soft_sell hanya izinkan SATU sebutan brand halus (§6).

ALTER TABLE channels ADD COLUMN IF NOT EXISTS landing_link   TEXT;             -- URL di deskripsi (pinned comment mustahil → pakai ini)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS link_position  TEXT DEFAULT 'bottom';  -- top | bottom
ALTER TABLE channels ADD COLUMN IF NOT EXISTS cta_mode       TEXT DEFAULT 'implicit'; -- implicit | soft_sell
ALTER TABLE channels ADD COLUMN IF NOT EXISTS brand_name     TEXT;             -- utk soft-sell ("... bersama [brand]")
ALTER TABLE channels ADD COLUMN IF NOT EXISTS brand_cta_text TEXT;             -- override teks CTA soft-sell (opsional)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS brand_logo     TEXT;             -- path/URL logo (storage) utk overlay
ALTER TABLE channels ADD COLUMN IF NOT EXISTS logo_position  TEXT DEFAULT 'top-right';
ALTER TABLE channels ADD COLUMN IF NOT EXISTS logo_size      NUMERIC DEFAULT 0.12;    -- fraksi lebar video (0-1)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS logo_opacity   NUMERIC DEFAULT 0.85;    -- 0-1
