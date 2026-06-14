-- 0019 — AI Disclosure (Phase 6.3, DESAIN §9.2 — AI Slop Defense / compliance).
-- Set YouTube Data API `status.containsSyntheticMedia` (field RESMI terverifikasi, sejak 2024-10-30;
-- wajib per kebijakan YouTube efektif Mei 2025). Per-channel toggle, DEFAULT TRUE (ON) = compliance-first.
-- FE: toggle di channel settings (Phase 9-10), default ON. Tenant boleh matikan bila konten bukan A/S.
ALTER TABLE channels ADD COLUMN IF NOT EXISTS ai_disclosure BOOLEAN DEFAULT TRUE;
UPDATE channels SET ai_disclosure = TRUE WHERE ai_disclosure IS NULL;
