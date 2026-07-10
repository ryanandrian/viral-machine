-- 0149 — [B16] kolom `scopes` di pool koneksi YouTube (akar retensi mati sejak 24 Jun)
-- ============================================================================
-- Loader `tenant_credentials._row_to_creds` membaca r.get("scopes") sejak era pool,
-- tapi kolomnya TAK PERNAH ADA → selalu [] → gerbang scope kolektor analytics
-- (`channel_analytics._init_clients`) mematikan Layer Full (retensi/watch/subs-gain)
-- utk SEMUA koneksi & tenant. Publisher selamat krn fallback SCOPES; analytics tidak.
-- Probe API 2026-07-11 membuktikan token ryan×2 PUNYA grant analytics (data dijawab).
-- Fix: kolom nullable (non-breaking; NULL = perilaku hari ini) + callback simpan granted
-- scopes (youtube_oauth._store_tokens) + backfill 3 koneksi eksisting via probe API.
-- ============================================================================
alter table tenant_youtube_accounts add column if not exists scopes text[];
comment on column tenant_youtube_accounts.scopes is
  'Scope OAuth yang DIBERIKAN Google saat consent (granted, bukan requested). Diisi callback _store_tokens sejak 0149; NULL = koneksi lama pra-0149 (backfilled via probe). Dipakai gerbang Layer-Full analytics.';
