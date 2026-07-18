-- 0172: [B17 §6 A1] LAPIS 2 "OTAK ANALIS" — buku keputusan per-channel (MODE BAYANGAN, ketok K1/K3/K4 18-Jul).
-- Unit belajar = pasangan KEPUTUSAN–HASIL (§6c.5): analis (LLM BYOK tenant, model task 'utility')
-- membaca DOSIR fakta terukur → keputusan terstruktur menu-tertutup + PREDIKSI → dicatat di sini.
-- BAYANGAN: mode='shadow' = TIDAK ADA konsumen produksi (wiring eksekusi + hakim mekanik = fase A2,
-- gerbang ketok owner pasca-review 2 minggu [K4]). Dosir & respons mentah ikut disimpan = bahan audit
-- mutu keputusan oleh owner. Penulis: HANYA src/intelligence/channel_analyst.py (worker service_role).
CREATE TABLE IF NOT EXISTS channel_decisions (
  id             bigserial   PRIMARY KEY,
  tenant_id      text        NOT NULL,
  channel_id     text        NOT NULL,
  cycle_date     date        NOT NULL,                 -- 1 baris per channel per siklus
  mode           text        NOT NULL DEFAULT 'shadow' CHECK (mode IN ('shadow','active')),
  status         text        NOT NULL DEFAULT 'recorded' CHECK (status IN ('recorded','rejected','judged')),
  decisions      jsonb,                                -- array keputusan LOLOS validasi skema (NULL bila rejected)
  dossier        jsonb,                                -- dosir fakta yang DIBACA analis (audit: keputusan vs fakta)
  raw_response   text,                                 -- respons mentah LLM (audit mutu bayangan; dipangkas 8k)
  model_used     text,
  reject_reason  text,                                 -- alasan bila status='rejected' (gagal jujur, bukan diterima diam2)
  verdict        jsonb,                                -- diisi HAKIM MEKANIK di A2 (prediksi vs angka nyata)
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel_id, cycle_date)
);
CREATE INDEX IF NOT EXISTS idx_cdec_channel ON channel_decisions (channel_id, created_at DESC);
-- Pola 0163/0171: RLS aktif TANPA policy = tertutup total; worker service_role bypass. FE belum membaca (A1 internal).
ALTER TABLE channel_decisions ENABLE ROW LEVEL SECURITY;

-- Kenop (nilai kebijakan = DB; label+kartu admin = app-config/page.tsx grup "Otak Analis").
INSERT INTO app_config (key, value, description) VALUES
  ('analyst_enabled',       1,  'Lapis-2 Otak Analis: saklar global. 1 = analis jalan (mode BAYANGAN sampai A2: hanya mencatat keputusan, NOL efek produksi); 0 = mati.'),
  ('analyst_interval_days', 7,  'Lapis-2: jarak antar siklus analis per channel (hari). Default mingguan.'),
  ('analyst_min_videos',    20, 'Lapis-2: gerbang data — analis hanya jalan bila channel punya minimal N video teranalisis (channel_insights.videos_analyzed); di bawah itu dosir terlalu tipis utk keputusan bermakna.')
ON CONFLICT (key) DO NOTHING;
