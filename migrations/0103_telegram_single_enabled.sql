-- 0103: Telegram = SATU sumber kebenaran toggle (telegram_enabled).
-- `telegram_notify_enabled` adalah kolom YATIM: hanya dibaca telegram_notifier._chat_id_for_tenant,
-- tak pernah ditulis FE/RPC manapun → toggle UI tak berpengaruh (bug). BE kini baca telegram_enabled
-- di SEMUA jalur notifikasi (commit menyertai). Kolom redundan ini dibuang (no junk).
-- Trigger lock-aktivasi (0092/0094) memakai telegram_enabled → tak terdampak.

ALTER TABLE tenant_configs DROP COLUMN IF EXISTS telegram_notify_enabled;
