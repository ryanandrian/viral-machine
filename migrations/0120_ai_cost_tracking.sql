-- 0120 — B2 BYOK cost-tracking (owner 2026-07-04): harga satuan model AI + kurs tampilan.
-- pricing = {in_per_1m, out_per_1m, per_image, per_1m_chars, source, synced_at} USD — diisi OTOMATIS
-- price_sync (feed komunitas LiteLLM, harian via janitor); pricing_locked=true = override admin
-- (sinkron tak menimpa; wajib utk model di luar feed, mis. ElevenLabs).
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS pricing jsonb;
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS pricing_locked boolean DEFAULT false;

-- Kurs tampilan USD→IDR (FE menampilkan Rupiah; biaya disimpan USD). Admin-editable di System Config.
INSERT INTO app_config (key, value, description)
VALUES ('usd_idr_rate', 16500, 'Kurs USD→IDR utk TAMPILAN biaya AI BYOK (biaya disimpan USD; ubah sesuai kurs berjalan)')
ON CONFLICT (key) DO NOTHING;
