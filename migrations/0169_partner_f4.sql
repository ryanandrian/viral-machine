-- 0169: [B21] F4 — Telegram agen (mekanisme 1-klik yang sama dgn tenant, ketok owner 2026-07-17)
alter table agents add column if not exists telegram_chat_id text;
comment on column agents.telegram_chat_id is '[B21-F4] chat Telegram agen (1-klik linker); terisi = notifikasi komisi aktif';
