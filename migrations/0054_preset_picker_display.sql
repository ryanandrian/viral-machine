-- 0054 — Preset-picker display: render_mode + glosarium istilah-pendek (term)
-- ============================================================================
-- Mendukung tampilan 2 tabel di preset-picker (tenant + admin), tetap SINGLE-SOURCE:
--   • duration_presets.render_mode → kolom "Render" (8s=ai_video, 15-90s=image_seq) — no-hardcode di FE.
--   • beat_glossary.term (nama-pendek) → kolom "Istilah" + dipakai FE menurunkan string "Segmentasi"
--     (mis. 60s beats[hook,build_up,core_facts,climax,cta] → "hook-buildup-core-climax-cta").
--     CATATAN: duration_presets.beats TETAP memakai key penuh (core_facts/build_up/…) karena MESIN
--     (script_engine) membacanya untuk produksi. `term` murni lapisan TAMPILAN — produksi tak berubah.
-- ============================================================================

-- ── Render mode per preset ───────────────────────────────────────────────
alter table public.duration_presets add column if not exists render_mode text;
update public.duration_presets set render_mode = 'ai_video'  where seconds = 8;
update public.duration_presets set render_mode = 'image_seq' where seconds in (15, 30, 45, 60, 75, 90);

-- ── Glosarium: istilah-pendek + kata-kata FINAL (owner-approved) ──────────
alter table public.beat_glossary add column if not exists term text;

-- Rapikan ke 7 istilah TERPAKAI lintas-preset (buang fosil yang tak dipakai preset mana pun).
delete from public.beat_glossary where beat_key in ('pattern_interrupt', 'core_facts_2');

update public.beat_glossary set term='hook',    label_id='Pemikat',   label_en='Hook',
  desc_id='Kalimat pembuka yang langsung menghentikan scroll & bikin penasaran',
  desc_en='Opening line that instantly stops the scroll and sparks curiosity',
  sort_order=1 where beat_key='hook';
update public.beat_glossary set term='core',    label_id='Inti',      label_en='Core',
  desc_id='Fakta atau pesan utama video',
  desc_en='The main fact or message of the video',
  sort_order=2 where beat_key='core_facts';
update public.beat_glossary set term='buildup', label_id='Pengantar', label_en='Build-up',
  desc_id='Membangun konteks/ketegangan sebelum inti',
  desc_en='Builds context/tension before the core',
  sort_order=3 where beat_key='build_up';
update public.beat_glossary set term='mystery', label_id='Misteri',   label_en='Mystery',
  desc_id='Lapisan teka-teki yang menambah penasaran',
  desc_en='A layer of mystery that deepens curiosity',
  sort_order=4 where beat_key='mystery_drop';
update public.beat_glossary set term='bridge',  label_id='Penasaran', label_en='Curiosity bridge',
  desc_id='Jembatan singkat yang menahan penonton menuju puncak',
  desc_en='A short bridge that holds the viewer toward the climax',
  sort_order=5 where beat_key='curiosity_bridge';
update public.beat_glossary set term='climax',  label_id='Puncak',    label_en='Climax',
  desc_id='Momen paling mengejutkan / memuncak',
  desc_en='The most surprising, peak moment',
  sort_order=6 where beat_key='climax';
update public.beat_glossary set term='cta',     label_id='Ajakan',    label_en='Call-to-action',
  desc_id='Dorongan halus di akhir (menyimak lagi / mengikuti), tanpa memaksa',
  desc_en='A gentle nudge at the end (watch again / follow), never pushy',
  sort_order=7 where beat_key='cta';
