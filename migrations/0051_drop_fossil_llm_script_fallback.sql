-- 0051: Bersih fosil (F1) — DROP tenant_configs.llm_script_fallback.
-- Fosil cross-library fallback warisan V1 yang sudah di-deprecate Phase 1.1 (no silent cross-provider
-- fallback). Diverifikasi 2026-06-17: NOL pembaca di kode (src/scripts/apps) — hanya muncul di migr 0001.
-- Aman di-drop. Idempotent.
alter table public.tenant_configs drop column if exists llm_script_fallback;
