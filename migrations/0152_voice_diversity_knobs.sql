-- 0152 — Knob formula Voice Diversity sadar-volume (compliance; mandat owner 2026-07-11)
-- ============================================================================
-- Formula baru di src/analytics/compliance.py::_voice_diversity (pengganti target-5 kasar):
-- k_exp = clamp(1 + log2(volume_bulanan / V0), 1, K) · skor = min(100, 100(1+H)/(1+ln k_exp)).
-- V0 = ambang volume/bulan yang masih wajar utk 1 suara · K = ekspektasi suara maksimum.
-- Admin-editable via System Configuration (label dwibahasa di CFG_META FE). Fail-soft ke
-- default yang sama di kode bila baris hilang. Data sumber videos.voice_id diisi pipeline
-- mulai 2026-07-11 (fill-forward; sejarah tak di-backfill — suara pernah berganti).
-- ============================================================================

insert into app_config (key, value, description) values
  ('voice_div_volume_baseline', 60,
   'Voice Diversity: volume publish/bulan yang masih wajar utk 1 suara (di bawah ini skor=100).'),
  ('voice_div_max_expected', 3,
   'Voice Diversity: ekspektasi jumlah suara maksimum pada volume sangat tinggi (pagar log2).')
on conflict (key) do nothing;
