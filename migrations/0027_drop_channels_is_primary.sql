-- 0027 — Drop channels.is_primary: vestigial clone-V1, NOL referensi di FE/backend v2/dokumentasi → mubazir.
-- Prinsip: backend/DB melayani FE; tak ada field tanpa dasar FE/spec.
ALTER TABLE channels DROP COLUMN IF EXISTS is_primary;
