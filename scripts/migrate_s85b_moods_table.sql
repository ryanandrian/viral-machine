-- ============================================================
-- Migration s85b: buat tabel moods + seed dari MOOD_KEYWORDS
-- Jalankan di Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS moods (
    mood_id    TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    keywords   JSONB DEFAULT '[]',
    is_active  BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO moods (mood_id, name, keywords) VALUES
  ('dramatic',      'Dramatic',      '["shocking","incredible","unbelievable","changed everything","nobody expected"]'),
  ('mysterious',    'Mysterious',    '["unknown","mystery","unexplained","secret","hidden","discovered"]'),
  ('tense',         'Tense',         '["danger","threat","warning","critical","urgent","countdown"]'),
  ('ominous',       'Ominous',       '["dark","evil","betrayal","conspiracy","cover-up","forbidden"]'),
  ('dark',          'Dark',          '["death","massacre","tragedy","catastrophe","destruction"]'),
  ('upbeat',        'Upbeat',        '["amazing","fun","surprising","interesting","cool","wow"]'),
  ('inspirational', 'Inspirational', '["wonder","beautiful","incredible","miraculous","stunning"]'),
  ('energetic',     'Energetic',     '["fast","quick","rapid","explosive","powerful","breakthrough"]'),
  ('calm',          'Calm',          '["peaceful","gentle","quiet","deep","vast","infinite"]'),
  ('eerie',         'Eerie',         '["strange","weird","unsettling","alien","bizarre","uncanny"]'),
  ('epic',          'Epic',          '["enormous","massive","universe","galaxy","civilization","ancient"]'),
  ('suspense',      'Suspense',      '["what if","imagine","but here","nobody knows","the truth"]'),
  ('happy',         'Happy',         '["happy","joy","celebrate","wonderful","great","best"]'),
  ('ambient',       'Ambient',       '["space","cosmos","float","drift","endless","eternal"]'),
  ('playful',       'Playful',       '["play","game","funny","laugh","silly","joke"]')
ON CONFLICT (mood_id) DO NOTHING;

-- Verifikasi
SELECT mood_id, name, jsonb_array_length(keywords) AS keyword_count, is_active
FROM moods
ORDER BY mood_id;
