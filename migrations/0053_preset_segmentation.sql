-- 0053 — Segmentasi konten per preset = SINGLE-SOURCE (anti-drift)
-- ============================================================================
-- Konteks: struktur beat per preset sebelumnya HARDCODE di script_engine (_BEATS_FOR_N) +
-- visual_beats di duration_presets → dua tempat, rawan drift. Migrasi ini menjadikan
-- `duration_presets.beats` (urutan beat/segmentasi) SUMBER TUNGGAL yang dibaca:
--   • mesin  : script_engine._beats_for_preset() (fallback _BEATS_FOR_N bila kolom kosong)
--   • tenant : panel preset-picker (tampilkan segmentasi + "cocok untuk" + glosarium)
--   • admin  : panel duration_presets (edit tanpa redeploy)
--
-- Struktur BARU (lean, progresif +1 beat — keputusan owner 2026-06-18):
--   8s=core · 15s=hook-core · 30s=hook-core-cta · 45s=+climax · 60s=+buildup ·
--   75s=+mystery · 90s=+bridge.  visual_beats di-set = len(beats) → QC clip_count konsisten.
-- (8s = ai_video, belum dibangun → desain ke depan.)
-- ============================================================================

alter table public.duration_presets add column if not exists beats       jsonb;
alter table public.duration_presets add column if not exists use_case    text;   -- "cocok untuk" (ID, bahasa awam)
alter table public.duration_presets add column if not exists use_case_en text;

update public.duration_presets set beats = '["core_facts"]'::jsonb, visual_beats = 1,
  use_case = 'Kutipan atau satu fakta mengejutkan', use_case_en = 'A quote or one surprising fact'           where seconds = 8;
update public.duration_presets set beats = '["hook","core_facts"]'::jsonb, visual_beats = 2,
  use_case = 'Satu fakta cepat pemancing penasaran', use_case_en = 'One quick, curiosity-sparking fact'      where seconds = 15;
update public.duration_presets set beats = '["hook","core_facts","cta"]'::jsonb, visual_beats = 3,
  use_case = 'Fakta singkat dengan ajakan', use_case_en = 'A short fact with a call to action'               where seconds = 30;
update public.duration_presets set beats = '["hook","core_facts","climax","cta"]'::jsonb, visual_beats = 4,
  use_case = 'Fakta dengan momen kejutan', use_case_en = 'A fact with a surprise moment'                     where seconds = 45;
update public.duration_presets set beats = '["hook","build_up","core_facts","climax","cta"]'::jsonb, visual_beats = 5,
  use_case = 'Cerita utuh yang padat (paling ideal)', use_case_en = 'A complete, tight story (ideal)'        where seconds = 60;
update public.duration_presets set beats = '["hook","mystery_drop","build_up","core_facts","climax","cta"]'::jsonb, visual_beats = 6,
  use_case = 'Cerita dengan sentuhan misteri', use_case_en = 'A story with a touch of mystery'               where seconds = 75;
update public.duration_presets set beats = '["hook","mystery_drop","build_up","core_facts","curiosity_bridge","climax","cta"]'::jsonb, visual_beats = 7,
  use_case = 'Pembahasan mendalam dan lengkap', use_case_en = 'An in-depth, complete discussion'             where seconds = 90;

-- Glosarium beat (label awam dwibahasa) — untuk tooltip di panel tenant/admin (anti-jargon).
create table if not exists public.beat_glossary (
  beat_key   text primary key,
  label_id   text not null,
  label_en   text not null,
  desc_id    text not null,
  desc_en    text not null,
  sort_order integer not null default 100,
  updated_at timestamptz not null default now()
);

insert into public.beat_glossary (beat_key, label_id, label_en, desc_id, desc_en, sort_order) values
  ('hook',             'Pemikat',   'Hook',             'Kalimat pembuka yang langsung menghentikan scroll & bikin penasaran', 'Opening line that stops the scroll and sparks curiosity', 1),
  ('mystery_drop',     'Misteri',   'Mystery',          'Lapisan teka-teki yang menambah rasa penasaran',                      'A layer of mystery that deepens curiosity',              2),
  ('build_up',         'Pengantar', 'Build-up',         'Membangun konteks/ketegangan sebelum inti',                           'Builds context/tension before the core',                 3),
  ('pattern_interrupt','Kejutan',   'Pattern interrupt','Pemutus ritme agar penonton fokus lagi',                              'A rhythm-breaker that re-grabs attention',               4),
  ('core_facts',       'Inti',      'Core',             'Fakta atau pesan utama video',                                        'The main fact or message of the video',                  5),
  ('core_facts_2',     'Inti 2',    'Core fact 2',      'Fakta utama kedua',                                                   'A second main fact',                                     6),
  ('curiosity_bridge', 'Penasaran', 'Curiosity bridge', 'Jembatan singkat yang menahan penonton menuju puncak',                'A short bridge that holds the viewer toward the climax', 7),
  ('climax',           'Puncak',    'Climax',           'Momen paling mengejutkan / memuncak',                                 'The most surprising, peak moment',                       8),
  ('cta',              'Ajakan',    'Call to action',   'Dorongan halus di akhir tanpa memaksa',                               'A gentle nudge at the end, never pushy',                 9)
on conflict (beat_key) do update set
  label_id = excluded.label_id, label_en = excluded.label_en,
  desc_id  = excluded.desc_id,  desc_en  = excluded.desc_en,
  sort_order = excluded.sort_order, updated_at = now();

alter table public.beat_glossary enable row level security;
drop policy if exists beat_glossary_read on public.beat_glossary;
create policy beat_glossary_read on public.beat_glossary for select using (true);
