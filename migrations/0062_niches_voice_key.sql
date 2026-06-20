-- 0062_niches_voice_key.sql
-- F1-02 (REMEDIASI §10.B): binding niche -> 1 voice identity + seed voice_catalog.
-- Aditif. niches.voice_key BELUM dibaca BE (jalur tts_voice_per_niche -> map hardcode dipakai s/d F1-03)
-- => NOL dampak produksi ryan. default_settings = BASELINE (BE DEFAULTS); override ryan tetap di
--    tenant_configs.tts_voice_settings (di-rekonsiliasi di F1-03, butuh konfirmasi owner).

-- 1) Seed voice_catalog: 4 voice ElevenLabs platform (tenant_id NULL). Sumber: map+DEFAULTS BE saat ini.
insert into voice_catalog
  (voice_key, provider_key, display_name, locale, language, gender, age, accent, use_case, description, default_settings, niche_default, is_active, sort_order)
values
  ('pNInz6obpgDQGcFmaJgB','elevenlabs','Adam','en-US','English','male','middle-aged','american','narration','Deep, authoritative — misteri & sains',  '{"speed":0.87,"style":0.50,"stability":0.30,"similarity_boost":0.75}'::jsonb,'universe_mysteries',true,10),
  ('21m00Tcm4TlvDq8ikWAM','elevenlabs','Rachel','en-US','English','female','young','american','narration','Energetic, friendly',                       '{"speed":0.90,"style":0.35,"stability":0.50,"similarity_boost":0.80}'::jsonb,'fun_facts',         true,20),
  ('VR6AewLTigWG4xSOukaG','elevenlabs','Arnold','en-US','English','male','middle-aged','american','narration','Dramatic — sejarah kelam',             '{"speed":0.83,"style":0.55,"stability":0.28,"similarity_boost":0.75}'::jsonb,'dark_history',      true,30),
  ('EXAVITQu4vr4xnSDxMaL','elevenlabs','Bella','en-US','English','female','young','american','narration','Calm, mysterious — misteri laut',          '{"speed":0.86,"style":0.40,"stability":0.35,"similarity_boost":0.75}'::jsonb,'ocean_mysteries',   true,40)
on conflict (voice_key) do nothing;

-- 2) niches.voice_key (nullable) + binding 1-voice-per-niche.
alter table niches add column if not exists voice_key text;

update niches set voice_key = 'VR6AewLTigWG4xSOukaG' where niche_id = 'dark_history';
update niches set voice_key = 'pNInz6obpgDQGcFmaJgB' where niche_id = 'universe_mysteries';
update niches set voice_key = '21m00Tcm4TlvDq8ikWAM' where niche_id = 'fun_facts';
update niches set voice_key = 'EXAVITQu4vr4xnSDxMaL' where niche_id = 'ocean_mysteries';

-- 3) FK (nullable): niche.voice_key harus voice valid di katalog.
alter table niches drop constraint if exists niches_voice_key_fkey;
alter table niches add constraint niches_voice_key_fkey
  foreign key (voice_key) references voice_catalog(voice_key) on update cascade on delete set null;

comment on column niches.voice_key is 'Identitas voice niche (FK voice_catalog). 1 voice per niche (branding, no-random). Dibaca BE mulai F1-03.';
