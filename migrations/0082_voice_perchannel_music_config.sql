-- 0082 — Konsolidasi VOICE per-channel + MUSIC 3-mode (EXPAND, additive/aman)
-- Regulasi final owner 2026-06-23 (REMEDIASI §3#3/#24, §10.B/§10.G/§10.H, item [FX]).
-- VOICE: niche = provider-AGNOSTIK (tanpa voice). voice_profile → narration_persona (gaya narasi, BUKAN pemilih suara).
--   EXPAND: tambah narration_persona + salin isi. DROP voice_profile/voice_defaults/voice_key di 0083 (SETELAH BE berhenti baca).
-- MUSIC: niches.music_config jsonb = kebijakan 3-mode {mode: fixed|random|auto, mood?, track_id?}. Default 'auto' (= perilaku existing: deteksi mood per-naskah via mood_priority). NON-BREAKING.

ALTER TABLE niches ADD COLUMN IF NOT EXISTS narration_persona jsonb DEFAULT '{}'::jsonb;
UPDATE niches SET narration_persona = COALESCE(voice_profile, '{}'::jsonb)
  WHERE (narration_persona IS NULL OR narration_persona = '{}'::jsonb) AND voice_profile IS NOT NULL;

ALTER TABLE niches ADD COLUMN IF NOT EXISTS music_config jsonb DEFAULT '{"mode":"auto"}'::jsonb;
UPDATE niches SET music_config = '{"mode":"auto"}'::jsonb WHERE music_config IS NULL;

-- admin_te (channel edge internal) — set voice_key channel (model voice=channel; konsistensi gerbang aktivasi).
UPDATE channels SET voice_key = 'en-US-GuyNeural'
  WHERE tts_provider = 'edge_tts' AND voice_key IS NULL;
