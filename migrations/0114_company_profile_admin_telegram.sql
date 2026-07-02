-- 0114 — company_profile: kolom admin_telegram_chat_id (setelan owner/platform, no-hardcode).
-- Dipakai notify_admin (Telegram) utk kirim alert "lead panas" ke owner. Editable via /admin/company-profile.
-- ADITIF & TERISOLASI — TIDAK menyentuh System Config (app_config) yang vital. Kosong = alarm mati (fail-soft).
alter table public.company_profile add column if not exists admin_telegram_chat_id text;
comment on column public.company_profile.admin_telegram_chat_id is
  'Telegram chat_id admin/owner penerima notifikasi tenant (mis. lead panas). Kosong = alarm dimatikan.';
