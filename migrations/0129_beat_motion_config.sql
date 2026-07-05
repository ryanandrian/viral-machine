-- 0129 — Fase 2 motion (arah) per-segmen, level SYSTEM (owner 2026-07-05). Perluas content_beats:
--   motion_mode: 'fix' (arah tetap dipilih admin) | 'cerdas' (mesin variasikan otomatis, anti-monoton)
--   motion_dir : arah default saat fix (zoom_in/zoom_out/pan_lr/pan_rl/pan_ud/pan_du/pan_diag/pan_diag_rev/still)
--   motion_rate: laju zoom/detik (utk arah zoom; pan pakai konstanta). DEFAULT = nilai Fase 1 PERSIS.
-- Default SEMUA = mode 'fix' + arah & rate saat ini → NOL perubahan perilaku sampai admin ubah ke 'cerdas'.
-- Durasi TAK tersentuh (arah hanya cara gambar bergerak di dalam durasi yg dipaku `-t`).

ALTER TABLE content_beats ADD COLUMN IF NOT EXISTS motion_mode TEXT NOT NULL DEFAULT 'fix';
ALTER TABLE content_beats ADD COLUMN IF NOT EXISTS motion_dir  TEXT;
ALTER TABLE content_beats ADD COLUMN IF NOT EXISTS motion_rate NUMERIC NOT NULL DEFAULT 0.04;

-- Seed arah + rate = pemetaan Fase 1 PERSIS (hook zoom-in 0.05, dst.) → default = perilaku sekarang.
UPDATE content_beats SET motion_dir='zoom_in',  motion_rate=0.050 WHERE beat_key='hook';
UPDATE content_beats SET motion_dir='zoom_out', motion_rate=0.035 WHERE beat_key='mystery_drop';
UPDATE content_beats SET motion_dir='pan_diag', motion_rate=0.000 WHERE beat_key='build_up';
UPDATE content_beats SET motion_dir='zoom_out', motion_rate=0.035 WHERE beat_key='pattern_interrupt';
UPDATE content_beats SET motion_dir='zoom_in',  motion_rate=0.030 WHERE beat_key='core_facts';
UPDATE content_beats SET motion_dir='pan_diag', motion_rate=0.000 WHERE beat_key='curiosity_bridge';
UPDATE content_beats SET motion_dir='zoom_out', motion_rate=0.050 WHERE beat_key='climax';
UPDATE content_beats SET motion_dir='zoom_out', motion_rate=0.050 WHERE beat_key='cta';
