-- 0158 — KONTEN MARKETING ADMIN-EDITABLE (finalisasi_tier_plan Tahap 4, 2026-07-13).
-- (1) marketing_blocks: blok narasi bebas dwibahasa (judul + baris [{id,en}]) — dipakai ILUSTRASI
--     BIAYA PER VIDEO di landing (keputusan owner: statis ber-label periode, admin-editable, TANPA
--     data hidup). Seed = angka verifikasi DB 2026-07-13 (run ber-harga, racikan aktif per channel).
-- (2) plan_matrix_rows: tabel perbandingan fitur /pricing ("Compare all features") — baris jadi DATA.
--     Nilai sel: "true"/"false" → ikon ✓/✗ · token "auto:max_channels|auto:max_videos_per_day|
--     auto:niche_studio" → FAKTA live dari plan_limits (fakta tak pernah jadi teks bebas) · selain
--     itu = teks. Seed = PERSIS isi hardcode kartu /pricing hari ini (nol regresi ID; label EN baru =
--     pemenuhan dwibahasa yang selama ini bolong).
-- RLS: publik boleh BACA (halaman marketing anon); tulis hanya service_role (route admin Next).
BEGIN;

CREATE TABLE IF NOT EXISTS marketing_blocks (
  key        TEXT PRIMARY KEY,
  title_id   TEXT,
  title_en   TEXT,
  lines      JSONB NOT NULL DEFAULT '[]'::jsonb,
  sort_order INT  NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE marketing_blocks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketing_blocks_read ON marketing_blocks;
CREATE POLICY marketing_blocks_read ON marketing_blocks FOR SELECT USING (true);

INSERT INTO marketing_blocks (key, title_id, title_en, lines, sort_order) VALUES
('cost_illustration_head',
 'Biaya nyata per video — ilustrasi penggunaan real 8–12 Juli 2026',
 'Real cost per video — illustration from actual usage, 8–12 July 2026',
 '[{"id":"Dua channel produksi sungguhan, dua racikan model — biaya diukur mesin per video. Biaya AI (BYOK) dibayar langsung ke provider, bukan ke kami.","en":"Two real production channels, two model mixes — costs metered per video. AI costs (BYOK) are paid straight to providers, not to us."}]'::jsonb, 0),
('cost_profile_premium',
 'Racikan Premium — RAD The Explorer',
 'Premium mix — RAD The Explorer',
 '[{"id":"LLM: GPT-4o + GPT-4o-mini (OpenAI)","en":"LLM: GPT-4o + GPT-4o-mini (OpenAI)"},
   {"id":"Suara: ElevenLabs Turbo v2.5","en":"Voice: ElevenLabs Turbo v2.5"},
   {"id":"Visual: gpt-image-1-mini (OpenAI)","en":"Visuals: gpt-image-1-mini (OpenAI)"},
   {"id":"Biaya AI terukur: ±Rp 1.270 / video (rata-rata 18 video)","en":"Metered AI cost: ±Rp 1,270 / video (18-video average)"}]'::jsonb, 1),
('cost_profile_free',
 'Racikan Gratis — Mesin Viral (Test)',
 'Free mix — Mesin Viral (Test)',
 '[{"id":"LLM: Llama-3.3-70B (Groq)","en":"LLM: Llama-3.3-70B (Groq)"},
   {"id":"Suara: Edge-TTS (gratis)","en":"Voice: Edge-TTS (free)"},
   {"id":"Visual: FLUX-1 Schnell (Cloudflare)","en":"Visuals: FLUX-1 Schnell (Cloudflare)"},
   {"id":"Nilai terukur ±Rp 190 / video — dengan kunci tier gratis & dalam kuota harian, tagihan provider: Rp 0","en":"Metered value ±Rp 190 / video — with free-tier keys within daily quotas, your provider bill: Rp 0"}]'::jsonb, 2),
('cost_footnote', NULL, NULL,
 '[{"id":"Ditambah langganan per video (setelan saat ini): Business Rp 699rb ÷ 1.500 video/bln ≈ Rp 466 · Pro ≈ Rp 1.293 · Starter ≈ Rp 4.967. Angka ilustrasi — dapat berubah mengikuti paket & racikan model.","en":"Plus subscription per video (current settings): Business Rp 699K ÷ 1,500 videos/mo ≈ Rp 466 · Pro ≈ Rp 1,293 · Starter ≈ Rp 4,967. Illustrative figures — vary with plan & model mix."}]'::jsonb, 3)
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS plan_matrix_rows (
  id         SERIAL PRIMARY KEY,
  sort_order INT NOT NULL DEFAULT 0,
  is_group   BOOLEAN NOT NULL DEFAULT FALSE,
  label_id   TEXT NOT NULL,
  label_en   TEXT NOT NULL,
  v_starter  TEXT, v_pro TEXT, v_business TEXT, v_enterprise TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE plan_matrix_rows ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS plan_matrix_rows_read ON plan_matrix_rows;
CREATE POLICY plan_matrix_rows_read ON plan_matrix_rows FOR SELECT USING (true);

INSERT INTO plan_matrix_rows (sort_order, is_group, label_id, label_en, v_starter, v_pro, v_business, v_enterprise)
SELECT * FROM (VALUES
  (10,  TRUE,  'Produksi', 'Production', NULL, NULL, NULL, NULL),
  (20,  FALSE, 'Channel', 'Channels', 'auto:max_channels', 'auto:max_channels', 'auto:max_channels', '∞'),
  (30,  FALSE, 'Video / hari', 'Videos / day', 'auto:max_videos_per_day', 'auto:max_videos_per_day', 'auto:max_videos_per_day', 'custom'),
  (40,  FALSE, 'Self-learning engine', 'Self-learning engine', 'true', 'true', 'true', 'true'),
  (50,  FALSE, 'BYOK (bawa API keys)', 'BYOK (bring your own keys)', 'true', 'true', 'true', 'true'),
  (60,  FALSE, 'Multi-channel paralel', 'Parallel multi-channel', 'false', 'true', 'true', 'true'),
  (70,  TRUE,  'AI & Kualitas', 'AI & Quality', NULL, NULL, NULL, NULL),
  (80,  FALSE, 'Niche tersedia', 'Niches available', '3', 'semua', 'semua', 'semua'),
  (90,  FALSE, 'Niche Studio (DNA kustom)', 'Niche Studio (custom DNA)', 'auto:niche_studio', 'auto:niche_studio', 'auto:niche_studio', 'true'),
  (100, FALSE, 'Quality Gate kustom', 'Custom Quality Gate', 'false', 'true', 'true', 'true'),
  (110, FALSE, 'Compliance detail', 'Compliance detail', 'false', 'true', 'true', 'true'),
  (120, FALSE, 'Custom voice (ElevenLabs)', 'Custom voice (ElevenLabs)', 'false', 'true', 'true', 'true'),
  (130, FALSE, 'Captions style kustom', 'Custom caption styles', 'false', 'true', 'true', 'true'),
  (140, FALSE, 'Hashtags kustom', 'Custom hashtags', 'false', 'true', 'true', 'true'),
  (150, TRUE,  'Kolaborasi & Integrasi', 'Collaboration & Integrations', NULL, NULL, NULL, NULL),
  (160, FALSE, 'Telegram & Email notif', 'Telegram & Email notifications', 'true', 'true', 'true', 'true'),
  (170, FALSE, 'Webhook', 'Webhook', 'false', 'false', 'true', 'true'),
  (180, FALSE, 'Priority queue', 'Priority queue', 'false', 'false', 'true', 'true'),
  (190, FALSE, 'API access', 'API access', 'false', 'false', 'true', 'true'),
  (200, TRUE,  'Dukungan', 'Support', NULL, NULL, NULL, NULL),
  (210, FALSE, 'Support', 'Support', 'Email', 'Priority', 'Priority', 'Dedicated')
) AS seed(sort_order, is_group, label_id, label_en, v_starter, v_pro, v_business, v_enterprise)
WHERE NOT EXISTS (SELECT 1 FROM plan_matrix_rows);

COMMIT;
