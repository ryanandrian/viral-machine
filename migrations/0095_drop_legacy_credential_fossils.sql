-- 0095: DROP fosil kredensial (CHANNEL_LOCK §3 Fase 9 — NOL dual-state).
-- ⚠️ APPLY HANYA SETELAH: (1) BE baru ter-deploy ke VPS (worker baca tenant_ai_accounts + tenant_youtube_accounts,
--    bukan tabel lama — terverifikasi src baca 0× channel_credentials/tenant_credentials), DAN
--    (2) FE admin test-lab (`apps/web/.../admin/test-lab/{route,test/route}.ts`) tak lagi baca `tenant_credentials`.
-- Aman: worker v2 baru sudah resolve kunci AI dari tenant_ai_accounts (akun+vendor) & YouTube dari tenant_youtube_accounts.

-- 1) Kolom kunci AI inline per-channel (orphan — diganti pool tenant_ai_accounts via 0091/0093).
alter table channels drop column if exists llm_key_enc;
alter table channels drop column if exists tts_key_enc;
alter table channels drop column if exists visual_key_enc;

-- 2) token_path (warisan single-tenant; worker pakai pool, bukan file path).
alter table channels drop column if exists token_path;

-- 3) Tabel kredensial YouTube lama (digantikan tenant_youtube_accounts; worker baca 0×; hanya sumber backfill 0091).
drop table if exists channel_credentials;
-- tenant_credentials: PRASYARAT fix admin test-lab dulu (FE masih baca). Setelah itu:
drop table if exists tenant_credentials;

-- 4) (Opsional, OAuth Platform) client creds per-baris di pool YouTube = artefak BYO-CC; resolusi kini dari .env platform.
--    Aman di-null-kan (env GOOGLE_CLIENT_ID/SECRET menang). Tidak DROP kolom (jaga kompat); cukup kosongkan.
update tenant_youtube_accounts set google_client_id = null, google_client_secret_enc = null
 where google_client_id is not null;
