-- 0050: Circuit-breaker §4b/F7 (QC_CONTENT_ARCHITECTURE) — pause produksi per-channel.
-- OPSI C / penutup INSIDEN RUNAWAY 2026-06-17: N produksi beruntun gagal/bermasalah → producer
-- STOP channel ini (skip di plan_and_submit) + alarm Telegram seketika. Auto-recover saat 1 direct
-- sukses (producer.run_direct melepas flag). Non-breaking: nullable/default, loader lama aman.
-- Idempotent.
alter table public.channels add column if not exists production_paused boolean not null default false;
alter table public.channels add column if not exists production_paused_at timestamptz;
alter table public.channels add column if not exists production_paused_reason text;

comment on column public.channels.production_paused is
  'Circuit-breaker §4b/F7: true = produksi channel dihentikan otomatis (gagal beruntun). Dilepas saat 1 direct sukses.';
