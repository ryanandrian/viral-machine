-- 0078 — Kalibrasi P (pace dasar EL) ke 1.97 per DATA TERUKUR §10.D (V1: 189 kata/111.5s @speed0.86
-- → base÷speed = 1.97 wps @speed 1.0). Sebelumnya 1.8 (estimasi lama, ~9% rendah → est durasi over →
-- naskah agak pendek). Dipakai §10.A sebagai seed P ke LLM + gate durasi. F5-01 akan self-calibrate
-- dari tts_delivery_samples (data nyata) menggantikan seed ini. edge/openai tak diubah.
update tts_profiles set delivery_wps = 1.97 where provider_key = 'elevenlabs';
