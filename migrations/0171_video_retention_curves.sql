-- 0171: [B17 §6 M1] LAPIS 1 "MATA" — kurva retensi per-momen (YouTube Audience Retention, 100 titik/video).
-- Kenapa: rata-rata retensi tak bisa mengajarkan CRAFT (probe 18-Jul: video 42,4% ternyata hook-nya HEBAT
-- [watchRatio 1,24] tapi penonton kabur massal t=0,05→0,25 — pelajaran itu tak terlihat di rata-rata).
-- Fondasi dosir Otak Analis (A1). ADDITIVE murni: nol perubahan pada rantai belajar eksisting.
-- Penulis: HANYA src/analytics/retention_curves.py (worker service_role, koneksi OAuth per-channel —
-- pelajaran akar saga retensi-0: token terikat identitas channel). FE TIDAK membaca tabel ini (M1 internal).
-- 1 request API = 1 video (syarat resmi); kebijakan umur/refresh/limit = kenop app_config di bawah (no-hardcode).
CREATE TABLE IF NOT EXISTS video_retention_curves (
  video_id         text        PRIMARY KEY,          -- YouTube video id (videos.video_id)
  tenant_id        text        NOT NULL,
  channel_id       text        NOT NULL,             -- channels.id (atribusi per-channel sejak lahir)
  status           text        NOT NULL CHECK (status IN ('ok','empty')),  -- empty = API balas 0 titik (video muda/sepi) → retry terkendali
  curve            jsonb,                            -- [[elapsed_ratio, audience_watch_ratio, relative_retention_performance|null] × ≤100]; NULL saat empty
  hook_hold        numeric,                          -- rata watchRatio 5 titik awal (t≤0,05) — "hook menahan penonton?"
  mid_exit         numeric,                          -- elapsed_ratio pertama saat watchRatio < 0,5 (NULL = tak pernah — sangat baik)
  loop_factor      numeric,                          -- rata max(0, watchRatio−1) — porsi tonton-ulang (K2 dua-sinyal)
  end_ratio        numeric,                          -- watchRatio titik terakhir (t=1,0)
  rel_perf_avg     numeric,                          -- rata relativeRetentionPerformance (pembanding vs video YouTube sedurasi)
  points           integer,                          -- jumlah titik tersimpan (audit kelengkapan)
  views_at_fetch   integer,                          -- konteks volume saat pengambilan
  video_age_days   integer,                          -- umur video saat pengambilan (dasar keputusan refresh-final)
  attempt_count    integer     NOT NULL DEFAULT 1,
  first_attempt_at timestamptz NOT NULL DEFAULT now(),
  fetched_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vrc_channel ON video_retention_curves (channel_id);
-- Pola 0163: RLS aktif TANPA policy = tertutup total utk anon/authenticated; worker service_role bypass.
ALTER TABLE video_retention_curves ENABLE ROW LEVEL SECURITY;

-- Kenop kebijakan (angka bisnis = DB, bukan kode; label+kartu admin = app-config/page.tsx grup "Retention Curves").
INSERT INTO app_config (key, value, description) VALUES
  ('retention_curve_min_age_days',     3,  'Lapis-1 Mata: umur minimum video (hari) sebelum kurva retensi per-momen diambil — kurva video terlalu muda kosong (bukti probe 18-Jul).'),
  ('retention_curve_refresh_age_days', 14, 'Lapis-1 Mata: saat video melewati umur ini, kurva diambil ULANG sekali (kurva matang) lalu final — maks 2 fetch seumur hidup video.'),
  ('retention_curve_max_per_run',      50, 'Lapis-1 Mata: batas request kurva per channel per siklus self-learning (pengaman kuota API; 1 request = 1 video).'),
  ('retention_curve_give_up_age_days', 45, 'Lapis-1 Mata: video sepi yang kurvanya tetap kosong berhenti dicoba setelah umur ini (hari) — anti-request sia-sia selamanya.')
ON CONFLICT (key) DO NOTHING;
