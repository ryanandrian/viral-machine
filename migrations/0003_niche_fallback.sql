-- Migration 0003 — Phase 1.2 niche fallback (config-driven, tenant-specific)
-- Ref: PROGRESS Phase 1.2 + keputusan best-practice 2026-06-13 (gate enforcement di hulu,
--      fail-loud di hilir; BUANG default niche GLOBAL 'universe_mysteries').
-- Target: v2 (atliatnjhysdibmfypul). JANGAN apply ke v1 sampai cutover.
--
-- niche_fallback = NULLABLE & TANPA default global. Ini fallback milik TENANT sendiri
-- (dipilih di antara niche-nya) untuk kasus gagal-rotasi internal. Resolusi di kode:
--   niche_fallback -> niche -> niche_pool[0] -> FAIL-LOUD (skip + Telegram).
-- Niche dipastikan ada di hulu (onboarding/schedule gate — follow-up Phase 5/9).

ALTER TABLE public.tenant_configs
  ADD COLUMN IF NOT EXISTS niche_fallback text;
