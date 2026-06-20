-- 0065_edge_voice_rates.sql
-- F1-05 (faithful): kembalikan rate edge_tts per voice = map lama (Guy +10%, Jenny +15%, Christopher +5%)
-- supaya channel ber-edge (mis. admin_te) tak berubah kecepatan setelah voice single-source.
-- Aditif/data-fix; baseline delivery dibaca BE dari voice_catalog.default_settings (F1-05).
update voice_catalog set default_settings = '{"rate":"+10%","pitch":"+0Hz","volume":"+0%"}'::jsonb where voice_key='en-US-GuyNeural';
update voice_catalog set default_settings = '{"rate":"+15%","pitch":"+0Hz","volume":"+0%"}'::jsonb where voice_key='en-US-JennyNeural';
update voice_catalog set default_settings = '{"rate":"+5%","pitch":"+0Hz","volume":"+0%"}'::jsonb  where voice_key='en-US-ChristopherNeural';
