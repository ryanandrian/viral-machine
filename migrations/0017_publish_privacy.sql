-- 0017 — Publish privacy per-channel (trial-safe): private | public | unlisted. DEFAULT 'private'.
-- Arahan owner: tenant uji config dgn konten PRIVATE dulu; saat cocok → ubah ke public (app/Studio).
-- Konten tak hilang (private tetap di channel; tenant bisa flip manual di YouTube Studio).
-- Dipakai youtube_publisher saat submit (privacyStatus). FE: channel settings tab (Phase 9-10).

ALTER TABLE channels ADD COLUMN IF NOT EXISTS publish_privacy TEXT DEFAULT 'private';

-- Channel existing (ryan = tester) → default private (sengaja, sampai config cocok).
UPDATE channels SET publish_privacy = 'private' WHERE publish_privacy IS NULL;
