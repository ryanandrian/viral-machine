-- 0128 — SATU SUMBER kosakata "peran adegan" (beat roles) — owner 2026-07-05 [B3/Fase2 prasyarat].
-- Sebelumnya kosakata TERSEBAR di ~10 tempat (script_engine 6 dict, tts_engine, video_renderer, ai_image, FE)
-- dgn penyimpang MATI `core_facts_2` (hanya di 4 kode, tak pernah di data/preset/FE → tak tercapai).
-- Kanonik = 8 peran (urutan naratif). Nilai di-seed IDENTIK dgn konstanta lama (bukti derive==current).
-- Konsumen membaca via format_catalog.beat_vocabulary() (cache + fallback konstanta = NON-BREAKING).
-- Pemilihan segmen per-preset TETAP di duration_presets.beats (subset dari kosakata ini). core_facts_2 DIBUANG.

CREATE TABLE IF NOT EXISTS content_beats (
  beat_key           TEXT PRIMARY KEY,
  sort_order         INT  NOT NULL,
  label_upper        TEXT NOT NULL,          -- dipakai di prompt naskah (mis. "HOOK")
  label_id           TEXT NOT NULL,          -- label ramah (editor DNA) ID
  label_en           TEXT NOT NULL,          -- label ramah EN
  hint_id            TEXT,                   -- penjelasan awam ID
  hint_en            TEXT,                   -- penjelasan awam EN
  weight             INT  NOT NULL,          -- bobot anggaran-kata (_BEAT_WEIGHT)
  default_timing_sec INT  NOT NULL,          -- durasi default per bagian (_DEFAULT_SECTION_TIMING)
  motion_index       INT  NOT NULL,          -- gerak default (0-5, _ROLE_MOTION) — Fase 2 menimpa per-mode
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE content_beats ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS content_beats_read ON content_beats;
CREATE POLICY content_beats_read ON content_beats FOR SELECT USING (true);  -- public-read (editor + mesin)

INSERT INTO content_beats (beat_key, sort_order, label_upper, label_id, label_en, hint_id, hint_en, weight, default_timing_sec, motion_index) VALUES
  ('hook',              1, 'HOOK',              'Hook pembuka',        'Opening hook',   'Detik pertama yang menahan jempol penonton', 'The first seconds that stop the scroll', 3,  3,  0),
  ('mystery_drop',      2, 'MYSTERY DROP',      'Umpan misteri',       'Mystery drop',   'Janji jawaban yang bikin bertahan',          'The promise that keeps them watching',   5,  5,  1),
  ('build_up',          3, 'BUILD-UP',          'Membangun cerita',    'Build up',       'Konteks & ketegangan menuju inti',           'Context & tension toward the core',      12, 12, 2),
  ('pattern_interrupt', 4, 'PATTERN INTERRUPT', 'Kejutan pola',        'Pattern interrupt','Selingan singkat pengusir bosan',          'A quick jolt against boredom',           2,  2,  1),
  ('core_facts',        5, 'CORE FACT',         'Fakta inti',          'Core facts',     'Isi utama yang dijanjikan',                  'The main promised content',              15, 15, 3),
  ('curiosity_bridge',  6, 'CURIOSITY BRIDGE',  'Jembatan penasaran',  'Curiosity bridge','Transisi yang memancing ke klimaks',        'Transition teasing the climax',          3,  3,  2),
  ('climax',            7, 'CLIMAX',            'Klimaks',             'Climax',         'Momen emosi tertinggi',                      'The emotional peak',                     8,  8,  5),
  ('cta',               8, 'CTA',               'Ajakan penutup',      'Closing CTA',    'Penutup + ajakan (ikut cta_mode channel)',   'Closer + call-to-action',                3,  3,  5)
ON CONFLICT (beat_key) DO NOTHING;
