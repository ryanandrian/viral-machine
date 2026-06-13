-- 0012 — Multi-Format F1: katalog format_profiles + duration_presets + field channel
-- Sumber angka: MULTI_FORMAT_STUDIO.md §3 (duration presets + WPS per-format) & §4 (format profiles).
-- TERVALIDASI 2026-06-11 — angka diambil apa adanya, BUKAN analisa ulang.
-- Non-breaking: field channel NULLABLE → null = perilaku produksi sekarang (tanpa enforcement).
-- Logika word-budget→preset + LLM-QC + QC relatif = F2 (aktif hanya saat preset di-set).

-- ── Katalog: Format Profiles (§4) — admin-managed, public-read ──
CREATE TABLE IF NOT EXISTS format_profiles (
  format_key       TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  section_template JSONB   DEFAULT '[]'::jsonb,        -- arc: daftar role section (compression-map source)
  default_wps      NUMERIC NOT NULL,                   -- WORDS-PER-SECOND per-format (§3)
  default_cta_mode TEXT    DEFAULT 'implicit',         -- implicit | soft_sell | optional
  render_mode      TEXT    DEFAULT 'image_sequence',   -- image_sequence | ai_video
  is_active        BOOLEAN DEFAULT true,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Katalog: Duration Presets (§3) — admin-managed, public-read ──
CREATE TABLE IF NOT EXISTS duration_presets (
  seconds      INTEGER PRIMARY KEY,
  visual_beats INTEGER NOT NULL,                       -- jumlah beat visual (§3; angka awal, A/B saat live)
  render_mode  TEXT    DEFAULT 'image_sequence',
  notes        TEXT,
  is_active    BOOLEAN DEFAULT true,
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── Pilihan per-channel (NULLABLE = legacy/no-enforcement) ──
ALTER TABLE channels ADD COLUMN IF NOT EXISTS duration_preset INTEGER;  -- rujuk duration_presets.seconds (loose)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS format_profile  TEXT;     -- rujuk format_profiles.format_key (loose)

-- ── RLS: katalog public-read (pola ai_providers/ai_models); service_role bypass utk tulis ──
ALTER TABLE format_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE duration_presets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS format_profiles_read  ON format_profiles;
DROP POLICY IF EXISTS duration_presets_read ON duration_presets;
CREATE POLICY format_profiles_read  ON format_profiles  FOR SELECT USING (true);
CREATE POLICY duration_presets_read ON duration_presets FOR SELECT USING (true);

-- ── Seed format_profiles (§4) ──
INSERT INTO format_profiles (format_key, name, default_wps, default_cta_mode, render_mode, section_template) VALUES
  ('viral_mystery',        'Viral Mystery',          2.4, 'implicit',  'image_sequence',
     '["hook","mystery_drop","build_up","pattern_interrupt","core_facts","curiosity_bridge","climax","cta"]'),
  ('educational_softsell', 'Educational Soft-Sell',  2.2, 'soft_sell', 'image_sequence',
     '["hook","masalah","insight","tips","soft_cta"]'),
  ('listicle_facts',       'Listicle Facts',         2.4, 'implicit',  'image_sequence',
     '["hook","fact_1","fact_2","fact_3","payoff"]'),
  ('motivational_quote',   'Motivational Quote',     1.6, 'optional',  'ai_video',
     '["affirmation"]')
ON CONFLICT (format_key) DO NOTHING;

-- ── Seed duration_presets (§3 — 8/15/30/45/60/75/90s) ──
INSERT INTO duration_presets (seconds, visual_beats, render_mode, notes) VALUES
  ( 8, 1, 'ai_video',       'ultra-short: butuh ai_video + bypass QC 45s (fase C)'),
  (15, 3, 'image_sequence', 'ultra-short: skema section ringkas + QC relatif (fase C)'),
  (30, 5, 'image_sequence', 'feasible — section_timing preset + compression-map'),
  (45, 6, 'image_sequence', 'feasible'),
  (60, 7, 'image_sequence', 'feasible'),
  (75, 8, 'image_sequence', 'feasible'),
  (90, 9, 'image_sequence', 'feasible (>180s? tidak; naikkan QC max bila perlu)')
ON CONFLICT (seconds) DO NOTHING;
