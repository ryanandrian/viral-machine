-- 0074 — Hapus app_config.niche_studio_min_rank (ORPHAN sejak tier-config 0073).
-- Gating Niche Studio kini PER-TIER via plan_limits.niche_studio (bukan rank global) → key ini
-- tak dibaca kode mana pun (verified grep src/ + apps/web = 0 referensi). Bersihkan (no-orphan,
-- selaras owner "jangan buat tapi tak dipakai").
delete from app_config where key = 'niche_studio_min_rank';
