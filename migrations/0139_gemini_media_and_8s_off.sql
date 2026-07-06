-- 0139_gemini_media_and_8s_off.sql (2026-07-06)
-- A. Preset 8s (render_mode ai_video) DINONAKTIFKAN sementara (owner: video-gen belum tersedia).
--    Data-driven: FE & format_catalog memfilter is_active — nol perubahan kode. Aktifkan lagi saat video-gen hadir.
-- B. Keluarga media Gemini via adapter BARU (kunci SAMA dgn LLM Gemini, key_group 'gemini'):
--    - Image: gemini-2.5-flash-image (transport _generate_gemini) — NONAKTIF s.d. lulus uji kunci nyata.
--    - TTS  : gemini-2.5-flash-preview-tts (adapter gemini_speech) + profil + 4 voice prebuilt
--             (multibahasa incl. id-ID) — profil & model NONAKTIF s.d. uji + kalibrasi delivery_wps.
begin;

update duration_presets
   set is_active = false,
       notes = 'ai_video belum tersedia — 8s dinonaktifkan sementara (owner 2026-07-06); aktifkan saat video-gen hadir'
 where seconds = 8;

insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('gemini-2.5-flash-image', 'gemini', 'image', 'gemini-2.5-flash-image',
   'Gemini Flash Image (Nano Banana)', 'standard', false, 34,
   '{"unit":"per_image","approx_usd":0.039,"note":"Termasuk kuota gratis harian AI Studio; NONAKTIF s.d. lulus uji kunci nyata"}'),
  ('gemini-2.5-flash-preview-tts', 'gemini', 'tts', 'gemini-2.5-flash-preview-tts',
   'Gemini Flash TTS', 'standard', false, 41,
   '{"unit":"per_char","note":"Free tier AI Studio tersedia; NONAKTIF s.d. uji + kalibrasi tempo"}')
on conflict (model_key) do nothing;

insert into tts_profiles (provider_key, display_name, adapter, tts_class, delivery_wps, has_word_timeframe, speed_param, is_active, param_schema) values
  ('gemini', 'Gemini TTS', 'gemini_speech', 'fast_fallback', 2.4, false, null, false, '{}')
on conflict (provider_key) do nothing;

insert into voice_catalog (voice_key, provider_key, display_name, locale, language, gender, is_active, sort_order) values
  ('Kore',   'gemini', 'Kore (Gemini)',   'en-US', 'Multilingual', 'female', true, 130),
  ('Puck',   'gemini', 'Puck (Gemini)',   'en-US', 'Multilingual', 'male',   true, 131),
  ('Charon', 'gemini', 'Charon (Gemini)', 'en-US', 'Multilingual', 'male',   true, 132),
  ('Aoede',  'gemini', 'Aoede (Gemini)',  'en-US', 'Multilingual', 'female', true, 133)
on conflict (voice_key) do nothing;

commit;
