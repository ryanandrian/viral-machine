-- 0064_channels_per_channel_config.sql
-- F1-04 (REMEDIASI §4/§10.E): pindahkan pilihan AI-model + voice + brand-skin + operasional ke CHANNEL.
-- Aditif & NOL dampak runtime: kolom baru BELUM dibaca BE (komponen masih baca tenant_configs s/d F1-05).
-- Backfill = salin nilai tenant_configs ke channel(s) tenant → saat F1-05 baca channel, perilaku IDENTIK.
-- Refinement (audit kode): visual_mode meng-encode mode+model image (ai_image:gpt-image-1-mini) → TIDAK
-- ada kolom image_model/video_model terpisah (redundan). video → visual_mode 'ai_video:*' saat dibangun.

-- 1) Kolom per-channel (nullable; NULL = belum dikonfigurasi → dipakai gerbang aktivasi F1-08).
alter table channels
  add column if not exists llm_model              text,
  add column if not exists llm_library            text,
  add column if not exists tts_provider           text,
  add column if not exists tts_model              text,
  add column if not exists voice_key              text,           -- pilihan FINAL voice; NULL → resolve via niches.voice_defaults[tts_provider]
  add column if not exists visual_mode            text,           -- 'video' | 'ai_image:<model>' | 'ai_video:<model>'
  add column if not exists image_quality          text,
  add column if not exists caption_style          jsonb,          -- styling subtitle on-screen (font/ukuran/posisi/warna/dll)
  add column if not exists niche_hashtags         jsonb,
  add column if not exists music_enabled          boolean,
  add column if not exists music_volume           numeric,
  add column if not exists music_default_mood     text,
  add column if not exists script_min_viral_score integer,
  add column if not exists script_max_retry       integer;

comment on column channels.voice_key   is 'Voice FINAL channel (ref voice_catalog). NULL → resolve via niches.voice_defaults[tts_provider] (Opsi 2). Channel multi-niche (niche_mode=random) biarkan NULL.';
comment on column channels.caption_style is 'Styling subtitle on-screen (font/ukuran/posisi/warna/highlight/outline). Per-channel, diatur tenant. BUKAN deskripsi YouTube.';

-- 2) FK voice_key → voice_catalog (nullable, integritas; on delete set null).
alter table channels drop constraint if exists channels_voice_key_fkey;
alter table channels add constraint channels_voice_key_fkey
  foreign key (voice_key) references voice_catalog(voice_key) on update cascade on delete set null;

-- 3) Backfill dari tenant_configs (kedua tenant_id = TEXT). voice_key & tts_model SENGAJA NULL
--    (voice di-resolve per-niche via voice_defaults = perilaku sekarang persis; tts_model default engine).
update channels c set
  llm_model              = t.llm_model,
  llm_library            = t.llm_library,
  tts_provider           = t.tts_provider,
  visual_mode            = t.visual_mode,
  image_quality          = t.image_quality,
  caption_style          = t.caption_style,
  niche_hashtags         = t.niche_hashtags,
  music_enabled          = t.music_enabled,
  music_volume           = t.music_volume,
  music_default_mood     = t.music_default_mood,
  script_min_viral_score = t.script_min_viral_score,
  script_max_retry       = t.script_max_retry
from tenant_configs t
where t.tenant_id = c.tenant_id;
