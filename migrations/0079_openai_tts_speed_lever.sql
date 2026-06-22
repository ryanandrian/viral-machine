-- 0079 — Pilihan A (owner 2026-06-22): aktifkan LEVER KECEPATAN untuk OpenAI TTS (durasi-via-speed
-- benar-benar multi-provider, bukan EL-only). Sebelumnya openai_tts.speed_param = NULL → gate F4
-- (tts_speed_range) memberi rentang (1.0,1.0) = tanpa lever → durasi openai hanya bertumpu pada
-- jumlah-kata + atempo. Set 'speed' → gate memakai param_schema.speed ([0.25,4.0], sudah ada) →
-- gate solve speed → provider OpenAI menerapkannya (kode: speech.create(speed=...)).
-- edge_tts sudah 'rate'. NON-BREAKING: S=1.0 = perilaku lama; tak ada tenant openai_tts saat ini.
update tts_profiles set speed_param = 'speed' where provider_key = 'openai_tts';
