-- 0026 — niche dasar (is_base) ADMIN-EDITABLE. trial/starter → HANYA niche is_base. (owner 2026-06-14)
ALTER TABLE niches ADD COLUMN IF NOT EXISTS is_base BOOLEAN DEFAULT false;
UPDATE niches SET is_base = true WHERE niche_id IN ('universe_mysteries','dark_history','ocean_mysteries');
