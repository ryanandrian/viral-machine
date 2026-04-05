-- ============================================================
-- Migration s85: tambah visual_style + visual_fallbacks ke niches
-- Jalankan di Supabase SQL Editor
-- ============================================================

ALTER TABLE niches
  ADD COLUMN IF NOT EXISTS visual_style     JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS visual_fallbacks JSONB DEFAULT '[]';

-- universe_mysteries
UPDATE niches SET
  visual_style = '{
    "base_style":    "NASA documentary photography style, cosmic scale",
    "color_palette": "deep blacks, cold blues, nebula purples, star whites",
    "atmosphere":    "infinite void of space, cosmic loneliness, vast scale"
  }',
  visual_fallbacks = '[
    "A single star sharpening into focus against absolute black void, cold blue light",
    "Radio telescope dish rotating under star-dense night sky, amber warning lights",
    "Milky Way galaxy arching overhead, time-lapse compression, infinite scale",
    "Deep field imagery showing galaxy after galaxy, overwhelming scale",
    "Primordial cosmic energy, abstract light formations in deep space",
    "Human silhouette beneath infinite star field, camera pulling back at speed"
  ]'
WHERE niche_id = 'universe_mysteries';

-- dark_history
UPDATE niches SET
  visual_style = '{
    "base_style":    "historical documentary photography, period-accurate",
    "color_palette": "desaturated, sepia undertones, deep shadows, blood reds",
    "atmosphere":    "weight of history, moral gravity, ominous inevitability"
  }',
  visual_fallbacks = '[
    "Ancient ruins emerging from fog at dawn, weight of centuries visible",
    "Medieval castle silhouette against stormy sky, lightning in distance",
    "Candlelit map table with strategic documents, shadows concealing intent",
    "Archaeological excavation revealing buried artifacts, earth and mystery",
    "Desaturated crowd scene at pivotal historical moment, moral weight",
    "Single torch illuminating dark stone corridor leading to hidden chamber"
  ]'
WHERE niche_id = 'dark_history';

-- ocean_mysteries
UPDATE niches SET
  visual_style = '{
    "base_style":    "deep sea documentary photography, National Geographic quality",
    "color_palette": "deep ocean blues and blacks, bioluminescent greens and blues",
    "atmosphere":    "crushing depth, alien beauty, ancient and unknowable"
  }',
  visual_fallbacks = '[
    "Bioluminescent particles drifting in absolute ocean darkness, alien beauty",
    "Massive silhouette emerging from deep ocean murk, overwhelming scale",
    "Coral reef ecosystem at the boundary of light and darkness",
    "Shipwreck resting on ocean floor, encrusted with decades of silence",
    "Looking up from ocean floor at distant surface light, crushing depth",
    "Deep sea environment with impossible anatomy, alien and ancient"
  ]'
WHERE niche_id = 'ocean_mysteries';

-- fun_facts
UPDATE niches SET
  visual_style = '{
    "base_style":    "vibrant documentary photography, engaging and dynamic",
    "color_palette": "bold saturated colors, energetic, eye-catching",
    "atmosphere":    "surprising discovery, playful wonder, instant delight"
  }',
  visual_fallbacks = '[
    "Colorful world landmark from unexpected aerial perspective, vibrant",
    "Science laboratory experiment with dramatic visual result, surprising",
    "Nature phenomenon captured at peak moment, visually astonishing",
    "Human brain visualization with neural activity, colorful and dynamic",
    "Extreme microscopic world revealing hidden beauty, unexpected scale",
    "Urban aerial view revealing geometric patterns invisible from ground"
  ]'
WHERE niche_id = 'fun_facts';

-- Verifikasi
SELECT niche_id,
       visual_style->>'base_style'        AS base_style,
       jsonb_array_length(visual_fallbacks) AS fallback_count
FROM niches
ORDER BY niche_id;
