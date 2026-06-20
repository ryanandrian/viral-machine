-- 0061_voice_catalog_baku.sql
-- F1-01 (REMEDIASI §10.B): voice_catalog jadi single-source identitas voice + field baku TTS.
-- Aditif & reversible. voice_catalog masih KOSONG dan BELUM dibaca BE (map hardcode dipakai s/d F1-03)
-- => NOL dampak ke produksi ryan.

-- 1) Perkaya voice_catalog dengan field baku (label portabel lintas provider TTS).
alter table voice_catalog
  add column if not exists age              text,
  add column if not exists accent           text,
  add column if not exists language         text,                         -- label bahasa manusiawi (English/Indonesian); 'locale' = kode (en-US) tetap ada
  add column if not exists use_case         text,
  add column if not exists description      text,
  add column if not exists default_settings jsonb not null default '{}'::jsonb,  -- delivery baku {stability,similarity_boost,style,speed}
  add column if not exists tenant_id        text;                          -- NULL = voice platform; terisi = voice BYOK milik tenant

comment on column voice_catalog.tenant_id        is 'NULL = voice platform (semua tenant); terisi = voice BYOK milik tenant tsb';
comment on column voice_catalog.default_settings is 'Param delivery baku TTS {stability,similarity_boost,style,speed}; LLM override per-naskah saat produksi';
comment on column voice_catalog.language         is 'Label bahasa manusiawi (mis. English). Kode lokal/region tetap di kolom locale (mis. en-US).';

-- 2) tts_profiles: rentang valid param per provider (server validasi/clamp tts_params dari LLM).
alter table tts_profiles
  add column if not exists param_schema jsonb;

update tts_profiles set param_schema = '{"speed":[0.7,1.2],"stability":[0,1],"style":[0,1],"similarity_boost":[0,1]}'::jsonb where provider_key = 'elevenlabs';
update tts_profiles set param_schema = '{"speed":[0.25,4.0]}'::jsonb                                                     where provider_key = 'openai_tts';
update tts_profiles set param_schema = '{"rate":[-50,100],"pitch":[-50,50],"volume":[-50,50]}'::jsonb                    where provider_key = 'edge_tts';
