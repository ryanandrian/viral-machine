-- 0126 — Temuan kualitas owner 2026-07-05 (System Configuration):
-- (a) PISAHKAN STATUS MESIN dari KONFIGURASI. `ai_price_synced_at`/`ai_price_stale_alerted_at` = penanda
--     status internal price_sync yang nyasar di app_config → tampil di admin sbg "config" epoch mentah
--     yang bisa diedit (salah tempat). Rumah baru = `system_state` (service_role-only; RLS tanpa policy).
--     Informasinya utk admin tampil manusiawi + read-only di Kesehatan Sistem.
-- (b) Kurs USD→IDR: disinkron OTOMATIS harian oleh mesin (price_sync.sync_fx_rate) dari kurs pasar publik;
--     `usd_idr_rate_locked`=1 (diset otomatis saat admin edit manual) → mesin berhenti menimpa.

-- (a) tabel status mesin
CREATE TABLE IF NOT EXISTS system_state (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE system_state ENABLE ROW LEVEL SECURITY;  -- tanpa policy = hanya service_role (pola tabel internal)

-- pindahkan status yang telanjur nyasar (idempotent)
INSERT INTO system_state (key, value, updated_at)
SELECT key, value::text, updated_at FROM app_config
WHERE key IN ('ai_price_synced_at', 'ai_price_stale_alerted_at')
ON CONFLICT (key) DO NOTHING;
DELETE FROM app_config WHERE key IN ('ai_price_synced_at', 'ai_price_stale_alerted_at');

-- (b) kunci kurs manual (0 = auto-sync harian; 1 = admin kelola sendiri)
INSERT INTO app_config (key, value, description) VALUES
  ('usd_idr_rate_locked', 0,
   'Kunci kurs manual: 1 = mesin TIDAK menimpa kurs (Anda kelola sendiri; otomatis jadi 1 saat kurs diedit manual); 0 = kurs disinkron otomatis harian dari kurs pasar. / Manual FX lock: 1 = engine never overwrites the rate (auto-set when edited manually); 0 = rate auto-synced daily from market data.')
ON CONFLICT (key) DO NOTHING;
