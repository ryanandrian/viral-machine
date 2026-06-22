-- 0080 — F5-06 (Provider Adapter Registry): kolom `adapter` di tts_profiles = nama PROTOKOL transport
-- (bukan vendor). Resolver build_tts_provider(provider_key) → tts_profiles.adapter → TTS_ADAPTERS[adapter]
-- (kode), mirror pola LLM (ai_providers.adapter). Tambah provider TTS baru pada protokol yg sama = baris DB;
-- protokol baru = 1 adaptor di kode. NON-BREAKING: kolom aditif; resolver punya fallback map utk NULL.
alter table tts_profiles add column if not exists adapter text;

update tts_profiles set adapter = 'elevenlabs'    where provider_key = 'elevenlabs'  and adapter is null;
update tts_profiles set adapter = 'openai_speech'  where provider_key = 'openai_tts'  and adapter is null;
update tts_profiles set adapter = 'edge'           where provider_key = 'edge_tts'    and adapter is null;

comment on column tts_profiles.adapter is 'Nama PROTOKOL transport TTS (registry kode TTS_ADAPTERS). provider baru protokol sama = baris DB tanpa koding; protokol baru = +1 adaptor. Mirror ai_providers.adapter (LLM).';
