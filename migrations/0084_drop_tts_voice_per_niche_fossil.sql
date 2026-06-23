-- 0084 — Bersih fosil VOICE: drop tenant_configs.tts_voice_per_niche.
-- Fosil v1 (per-niche voice di tenant) — NOL pembaca fungsional (BE hanya load tak-terpakai; FE/RPC nihil).
-- Voice = channels.voice_key (§10.B FINAL). DIPERTAHANKAN: tts_voice (legacy onboarding set_tenant_config — masih wired),
-- tts_voice_settings (delivery-override AKTIF, mis. ryan speed). Music fosil (r2_key/pixabay/tenant_configs.music_*) = urusan music-thread.
ALTER TABLE tenant_configs DROP COLUMN IF EXISTS tts_voice_per_niche;
