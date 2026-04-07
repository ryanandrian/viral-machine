-- ============================================================
-- Migration s86: tambah kolom voice_profile ke niches table
-- Memindahkan NICHE_VOICE_PROFILE dari Python hardcode → Supabase
-- Jalankan di Supabase SQL Editor
-- ============================================================

ALTER TABLE niches
  ADD COLUMN IF NOT EXISTS voice_profile JSONB DEFAULT '{}';

-- Seed voice_profile untuk 4 niche existing
UPDATE niches SET voice_profile = '{
  "tone":        "authoritative yet awe-inspiring, like a world-class documentary narrator",
  "style":       "dramatic pauses, building tension, sense of cosmic wonder and scale",
  "avoid":       "casual language, humor, sarcasm, weak openers, generic phrases",
  "hook_style":  "impossible_claim or number_shock about space/universe",
  "emotion_arc": "curiosity → shock → wonder → awe"
}'::jsonb WHERE niche_id = 'universe_mysteries';

UPDATE niches SET voice_profile = '{
  "tone":        "serious and grave, like a true crime narrator uncovering hidden truth",
  "style":       "slow reveals, uncomfortable truths, moral weight, eerie calmness",
  "avoid":       "humor, lighthearted tone, casual slang",
  "hook_style":  "story_open or you_dont_know about a dark historical event",
  "emotion_arc": "intrigue → discomfort → shock → sobering realization"
}'::jsonb WHERE niche_id = 'dark_history';

UPDATE niches SET voice_profile = '{
  "tone":        "mysterious and calm yet deeply unsettling",
  "style":       "vast scale descriptions, eerie biological details, scientific credibility",
  "avoid":       "sensationalist claims, unscientific assertions",
  "hook_style":  "impossible_claim or question about ocean depths or creatures",
  "emotion_arc": "curiosity → unease → fascination → profound wonder"
}'::jsonb WHERE niche_id = 'ocean_mysteries';

UPDATE niches SET voice_profile = '{
  "tone":        "enthusiastic and curious, like an excited friend sharing a discovery",
  "style":       "rapid fire delivery, surprising connections, relatable everyday analogies",
  "avoid":       "overly serious tone, academic jargon, slow pacing",
  "hook_style":  "number_shock or question about surprising everyday facts",
  "emotion_arc": "surprise → delight → disbelief → urge to share immediately"
}'::jsonb WHERE niche_id = 'fun_facts';

-- Verifikasi
SELECT niche_id,
       voice_profile->>'tone'       AS tone,
       voice_profile->>'hook_style' AS hook_style
FROM niches
ORDER BY niche_id;
