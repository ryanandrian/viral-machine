-- 0087: TTS jadi warga kelas-satu di katalog ai_providers/ai_models (POINT 1).
-- Tujuan: hapus hardcode model TTS (eleven_turbo_v2_5 di elevenlabs.py:121) → model TTS
-- config-driven dari channels.tts_model + TAMPIL di admin Catalog (Providers + AI Models).
-- cost_hint = SATUAN saja (per_char / free); rate diisi admin di F5-03 (jangan asal harga).
-- ryan TETAP IDENTIK: backfill channels.tts_model = model yang dipakai sekarang.

-- 1) Provider TTS (FK target ai_models). adapter = protokol TTS (selaras tts_profiles.adapter).
insert into ai_providers (provider_key, display_name, adapter, auth_type, is_active) values
  ('elevenlabs', 'ElevenLabs',              'elevenlabs',    'api_key', true),
  ('openai_tts', 'OpenAI TTS',              'openai_speech', 'api_key', true),
  ('edge_tts',   'Microsoft Edge (gratis)', 'edge',         'none',    true)
on conflict (provider_key) do nothing;

-- 2) Model TTS (component='tts'). sort_order=1 = DEFAULT provider (dipakai config-layer bila
--    channels.tts_model kosong). cost_hint satuan-saja (rate menyusul F5-03).
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, cost_hint, is_active, sort_order) values
  ('eleven_turbo_v2_5',     'elevenlabs', 'tts', 'eleven_turbo_v2_5',     'ElevenLabs Turbo v2.5',     'standard', '{"unit":"per_char"}', true, 1),
  ('eleven_multilingual_v2','elevenlabs', 'tts', 'eleven_multilingual_v2','ElevenLabs Multilingual v2','premium',  '{"unit":"per_char"}', true, 2),
  ('eleven_flash_v2_5',     'elevenlabs', 'tts', 'eleven_flash_v2_5',     'ElevenLabs Flash v2.5',     'fast',     '{"unit":"per_char"}', true, 3),
  ('tts-1',                 'openai_tts', 'tts', 'tts-1',                 'OpenAI TTS (standard)',     'standard', '{"unit":"per_char"}', true, 1),
  ('tts-1-hd',              'openai_tts', 'tts', 'tts-1-hd',              'OpenAI TTS HD',             'premium',  '{"unit":"per_char"}', true, 2),
  ('edge-neural',           'edge_tts',   'tts', 'edge-neural',           'Edge Neural (gratis)',      'standard', '{"unit":"free"}',     true, 1)
on conflict (model_key) do nothing;

-- 3) Backfill: channel ElevenLabs yang tts_model kosong → eksplisit ke model yang dipakai sekarang
--    (eleven_turbo_v2_5) → perilaku NOL regresi. (Edge tak butuh model_id → biarkan.)
update channels set tts_model = 'eleven_turbo_v2_5'
 where tts_provider = 'elevenlabs' and (tts_model is null or tts_model = '');
