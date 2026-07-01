-- 0111 — Durasi periode langganan → app_config (NO-HARDCODE; sebelumnya _PERIOD_DAYS=30 hardcode di kode).
-- Muncul di System Configuration (grup "Langganan, Trial & Penagihan"), admin-editable.
INSERT INTO app_config (key, value, description) VALUES
  ('subscription_period_days', 30,
   'Durasi satu periode langganan berbayar (hari). Default 30 = bulanan. Menentukan current_period_end saat pembayaran lunas.')
ON CONFLICT (key) DO NOTHING;
