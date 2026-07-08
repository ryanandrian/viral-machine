-- 0146 — [B11] Batch 1: pagar multi-channel YouTube (MULTI_YOUTUBE_CHANNEL_ARCHITECTURE.md §3)
-- (1) Koneksi "berwajah": simpan nama + foto channel YouTube saat connect (konfirmasi visual tenant).
-- (2) Anti-duplikat: 1 channel YouTube nyata tak bisa terhubung 2x utk tenant yang sama.
-- (3) Anti-tabrakan target: 2 channel MesinViral tak bisa menunjuk 1 channel YouTube yang sama.
-- Aman utk data live (verified 2026-07-08): pool = 2 baris (ryan+kumala, yt_channel_id unik);
-- channels.platform_channel_id terisi hanya 1 baris (ryan) → nol konflik saat create index.

alter table tenant_youtube_accounts
  add column if not exists yt_channel_title text,
  add column if not exists yt_channel_thumb text;

comment on column tenant_youtube_accounts.yt_channel_title is
  'Nama channel YouTube (snippet.title) saat consent — konfirmasi visual tenant, anti salah-pilih brand.';
comment on column tenant_youtube_accounts.yt_channel_thumb is
  'URL thumbnail channel YouTube (snippet.thumbnails.default) saat consent.';

-- Backfill nama utk koneksi lama: ambil dari channels.channel_name yang menunjuk target sama
-- (channel_name di-sync dari YouTube oleh sync_channel_meta → representatif).
update tenant_youtube_accounts a
   set yt_channel_title = c.channel_name
  from channels c
 where a.yt_channel_title is null
   and a.yt_channel_id is not null
   and c.tenant_id = a.tenant_id
   and c.platform_channel_id = a.yt_channel_id;

-- (2) unik per tenant per channel YouTube (parsial: baris belum-consent yt_channel_id NULL tetap boleh banyak)
create unique index if not exists ux_tya_tenant_ytchannel
  on tenant_youtube_accounts (tenant_id, yt_channel_id)
  where yt_channel_id is not null;

-- (3) unik target: 1 channel YouTube nyata ↔ maks 1 channel MesinViral per tenant
create unique index if not exists ux_channels_tenant_target
  on channels (tenant_id, platform_channel_id)
  where platform_channel_id is not null and platform_channel_id <> '';
