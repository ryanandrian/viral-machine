-- ============================================================
-- Migration s89: emotion_scoring_criteria per niche
-- Field khusus untuk kriteria scoring emotional_peak di ScriptAnalyzer.
-- Lebih spesifik dari voice_profile — dirancang sebagai scoring guide,
-- bukan writing guide. Admin bisa update tanpa sentuh kode.
-- Jalankan di Supabase SQL Editor
-- ============================================================

-- 1. Tambah kolom
ALTER TABLE niches
    ADD COLUMN IF NOT EXISTS emotion_scoring_criteria TEXT DEFAULT '';

-- 2. Isi per niche — kriteria spesifik untuk GPT analyzer
UPDATE niches SET emotion_scoring_criteria =
'Score 80+ if the climax delivers EXISTENTIAL AWE — viewer feels simultaneously insignificant and connected to something infinite. Valid techniques: scale contrast (a human lifetime vs 13.8 billion years), reversal (the universe behaves against all intuition), infinite implication (this one fact changes what it means to be human). Score LOW for generic ''amazing discovery'' language without specific revelatory weight. Score LOW if the viewer is told what to feel instead of caused to feel it.'
WHERE niche_id = 'universe_mysteries';

UPDATE niches SET emotion_scoring_criteria =
'Score 80+ if the climax creates MORAL WEIGHT — the specific gravity of real suffering or systemic evil made undeniable. Valid techniques: a specific name, date, or detail that collapses abstract history into visceral reality, a perpetrator detail so banal it is more disturbing than cruelty, an uncomfortable parallel to today. Viewer should feel complicit in a world where this happened. Score LOW for vague ''shocking facts'' without human specificity. Score LOW for horror without reflection.'
WHERE niche_id = 'dark_history';

UPDATE niches SET emotion_scoring_criteria =
'Score 80+ if the climax creates PRIMAL FEAR AND ALIEN WONDER — the deep ocean is more foreign than space and it is completely real. Valid techniques: pressure scale (crushing force vs human fragility), darkness as absolute (no light has ever reached there), biological wrongness (this creature should not exist by any logic we know). Score LOW for surface-level creature observations without genuine unease. Score LOW if the viewer feels ''interesting'' instead of ''disturbed''.'
WHERE niche_id = 'ocean_mysteries';

UPDATE niches SET emotion_scoring_criteria =
'Score 80+ if the climax creates the IRRESISTIBLE URGE TO SHARE — the fact is so counterintuitive that the viewer''s first instinct is to tell someone. The ''wait, WHAT?'' moment followed immediately by ''I have to show this to someone''. Valid techniques: everyday object revealed as extraordinary, number so absurd it breaks intuition, implication that changes how viewer sees something they encounter daily. Score LOW if interesting but not shareable. Score LOW if the reaction is ''cool'' not ''impossible''.'
WHERE niche_id = 'fun_facts';

-- 3. Verifikasi
SELECT niche_id, LEFT(emotion_scoring_criteria, 80) AS criteria_preview
FROM niches
ORDER BY niche_id;
