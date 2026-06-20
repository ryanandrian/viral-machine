-- 0063_voice_defaults_multimodel.sql
-- F1-07 (REMEDIASI §10.E): pondasi multi-AI-model BE-ready.
-- Aditif & NOL dampak runtime (BE belum baca voice_defaults s/d F1-05; map hardcode masih dipakai).
-- Keputusan (audit): opsi TTS = tts_profiles (registry existing) + voice = voice_catalog; TTS TIDAK
-- dipaksa ke ai_models (FK ai_providers LLM-centric). video → ai_models saat ai_video dibangun.

-- 1) Seed voice_catalog: voice edge_tts + openai_tts (EL sudah di F1-02). Sumber = map hardcode lama
--    (edge NICHE_VOICES, openai OPENAI_VOICES) → DATA terkurasi (admin bisa tune via /admin/catalog).
insert into voice_catalog
  (voice_key, provider_key, display_name, locale, language, gender, age, accent, use_case, description, default_settings, niche_default, is_active, sort_order)
values
  -- edge_tts (gratis)
  ('en-US-GuyNeural',        'edge_tts','Guy (Edge)',        'en-US','English','male',  'middle-aged','american','narration','Deep, authoritative', '{"rate":"+0%","pitch":"+0Hz","volume":"+0%"}'::jsonb,'universe_mysteries',true,110),
  ('en-US-JennyNeural',      'edge_tts','Jenny (Edge)',      'en-US','English','female','young',      'american','narration','Energetic, upbeat',   '{"rate":"+0%","pitch":"+0Hz","volume":"+0%"}'::jsonb,'fun_facts',         true,120),
  ('en-US-ChristopherNeural','edge_tts','Christopher (Edge)','en-US','English','male',  'middle-aged','american','narration','Dramatic, intense',   '{"rate":"+0%","pitch":"+0Hz","volume":"+0%"}'::jsonb,'dark_history',      true,130),
  -- openai_tts
  ('onyx','openai_tts','Onyx (OpenAI)','en-US','English','male',  'middle-aged','american','narration','Deep, authoritative','{"speed":1.0}'::jsonb,'universe_mysteries',true,210),
  ('nova','openai_tts','Nova (OpenAI)','en-US','English','female','young',      'american','narration','Upbeat, friendly',   '{"speed":1.0}'::jsonb,'fun_facts',         true,220),
  ('fable','openai_tts','Fable (OpenAI)','en-US','English','male', 'middle-aged','british', 'narration','Dramatic',           '{"speed":1.0}'::jsonb,'dark_history',      true,230)
on conflict (voice_key) do nothing;

-- 2) niches.voice_defaults: default voice per provider TTS (Opsi 2 §10.B). Pra-isi saat tenant pilih
--    TTS model di channel-config; boleh diganti. Isi = map lama (EL=F1-02, edge/openai di atas).
alter table niches add column if not exists voice_defaults jsonb not null default '{}'::jsonb;

update niches set voice_defaults = '{"elevenlabs":"pNInz6obpgDQGcFmaJgB","edge_tts":"en-US-GuyNeural","openai_tts":"onyx"}'::jsonb        where niche_id='universe_mysteries';
update niches set voice_defaults = '{"elevenlabs":"21m00Tcm4TlvDq8ikWAM","edge_tts":"en-US-JennyNeural","openai_tts":"nova"}'::jsonb       where niche_id='fun_facts';
update niches set voice_defaults = '{"elevenlabs":"VR6AewLTigWG4xSOukaG","edge_tts":"en-US-ChristopherNeural","openai_tts":"fable"}'::jsonb where niche_id='dark_history';
update niches set voice_defaults = '{"elevenlabs":"EXAVITQu4vr4xnSDxMaL","edge_tts":"en-US-GuyNeural","openai_tts":"onyx"}'::jsonb         where niche_id='ocean_mysteries';

comment on column niches.voice_defaults is 'Default voice per provider TTS {provider_key: voice_key} (Opsi 2). Pra-isi di channel-config; tenant boleh ganti. voice FINAL = channels.voice_key.';

-- 3) tts_profiles.display_name — untuk pemilih TTS model di FE (ramah pemula).
alter table tts_profiles add column if not exists display_name text;
update tts_profiles set display_name = 'ElevenLabs'              where provider_key='elevenlabs';
update tts_profiles set display_name = 'OpenAI TTS'             where provider_key='openai_tts';
update tts_profiles set display_name = 'Microsoft Edge (gratis)' where provider_key='edge_tts';
