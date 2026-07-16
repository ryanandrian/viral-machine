-- 0167: [EKSPRESI VOKAL] niches.voice_expression — gaya-baca narator PER-NICHE resmi (ketok owner 2026-07-16).
-- Akar: kenop warisan tenant_configs.tts_voice_settings AKTIF (94/94 render EL memakainya) tapi buta-layar
-- + hanya 4 niche template + tersalin per-tenant. Kolom ini = rumah resminya (global per-niche, ber-UI di
-- editor DNA admin+studio). Bentuk: {"style": 0..1, "stability": 0..1} — TANPA speed (milik mesin durasi).
-- NULL = ikut karakter bawaan suara (voice_catalog.default_settings) → 43 niche lain nol perubahan.
-- Urutan baca EL: bawaan-suara ⊕ voice_expression(niche) ⊕ warisan-tenant (warisan TERAKHIR = suara
-- channel berjalan IDENTIK; pembongkaran warisan = fase terpisah ber-ketok).
ALTER TABLE niches
  ADD COLUMN IF NOT EXISTS voice_expression jsonb;

-- Seed 4 niche template = PERSIS nilai yang berbunyi hari ini (dari template warisan; bukti log 94/94).
UPDATE niches SET voice_expression = '{"style": 0.55, "stability": 0.28}'::jsonb WHERE niche_id = 'dark_history'       AND voice_expression IS NULL;
UPDATE niches SET voice_expression = '{"style": 0.35, "stability": 0.50}'::jsonb WHERE niche_id = 'fun_facts'          AND voice_expression IS NULL;
UPDATE niches SET voice_expression = '{"style": 0.40, "stability": 0.35}'::jsonb WHERE niche_id = 'ocean_mysteries'    AND voice_expression IS NULL;
UPDATE niches SET voice_expression = '{"style": 0.50, "stability": 0.30}'::jsonb WHERE niche_id = 'universe_mysteries' AND voice_expression IS NULL;
