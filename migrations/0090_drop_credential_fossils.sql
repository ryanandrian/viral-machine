-- 0090: DROP fosil kredensial lama + brankas + kolom v1 mati
-- ============================================================================
-- Pasca pindah ke kunci per-channel inline (channels.{llm,tts,visual}_key_enc, migr 0089).
-- ⚠️ JALANKAN TERAKHIR: setelah 0088+0089 applied + BE/FE deploy + ryan tervalidasi (produksi OK).
-- Verified grep 2026-06-24: NOL pembaca kode (BE+FE) untuk semua kolom/tabel di bawah.
-- (visual_provider sebagai DICT-KEY in-memory tetap dipakai assembler = visual_mode; KOLOM DB-nya mati.)

-- 1) Brankas multi-akun (diganti channels.*_key_enc) + ref account_id di channels
drop table if exists tenant_api_accounts cascade;

alter table channels
  drop column if exists llm_account_id,
  drop column if exists tts_account_id,
  drop column if exists image_account_id,
  drop column if exists video_account_id;

-- 2) Kunci tenant-level (diganti per-channel inline) + plaintext lama (sudah NULL sejak 0044)
alter table tenant_configs
  drop column if exists llm_api_key_enc,
  drop column if exists tts_api_key_enc,
  drop column if exists visual_api_key_enc,
  drop column if exists llm_api_key,
  drop column if exists tts_api_key,
  drop column if exists visual_api_key,
  drop column if exists youtube_api_key_enc,
  drop column if exists youtube_api_key;

-- 3) Kolom fosil v1 MATI (nol pembaca terverifikasi)
alter table tenant_configs
  drop column if exists visual_provider,       -- legacy; sumber kebenaran = visual_mode
  drop column if exists visual_max_clip_mb,    -- cap download footage (Pexels dibuang)
  drop column if exists production_on_api_error,-- v1 fallback behavior
  drop column if exists tts_fallback_provider; -- v1 TTS fallback (no-fallback policy)
