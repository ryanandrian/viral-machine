-- 0016 — Branding config PLATFORM (admin, DB): bounds UKURAN logo + margin + opacity default.
-- Arahan owner: UKURAN logo = platform tetapkan (tenant ikut); POSISI = tenant pilih (channel.logo_position).
-- Koordinat overlay diturunkan dari (channel.logo_position + margin DB) — BUKAN hardcode.
-- Single-row (id=1), admin-editable. RLS public-read (FE preview baca bounds).

CREATE TABLE IF NOT EXISTS branding_config (
  id                   INT PRIMARY KEY DEFAULT 1,
  logo_max_w_px        INT     DEFAULT 220,   -- bounds lebar maks (≈20% dari 1080)
  logo_min_w_px        INT     DEFAULT 96,
  logo_max_h_px        INT     DEFAULT 220,
  logo_min_h_px        INT     DEFAULT 48,
  logo_margin_px       INT     DEFAULT 28,    -- jarak dari tepi (koordinat dari config, bukan hardcode)
  logo_default_opacity NUMERIC DEFAULT 0.85,
  updated_at           TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT branding_config_single_row CHECK (id = 1)
);

ALTER TABLE branding_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS branding_config_read ON branding_config;
CREATE POLICY branding_config_read ON branding_config FOR SELECT USING (true);

INSERT INTO branding_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
