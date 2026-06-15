-- 0044: Enkripsi API key AI at-rest (owner 2026-06-15: "seluruh kredensial tenant AMAN" = nilai jual).
-- SEBELUM: llm/visual/tts/youtube_api_key = PLAINTEXT di tenant_configs (keputusan lama Phase 4.1).
-- SESUDAH: kolom *_enc (Fernet, src/utils/crypto.py) — DITULIS hanya lewat server pemegang-kunci
-- (webhook_app /api/keys/set, service_role). Master key (ENCRYPTION_KEY) TAK pernah ke frontend.
-- Worker baca via load_tenant_config → decrypt (_eff_key, prefer *_enc → fallback plaintext transisi).
--
-- set_tenant_config: BUANG 4 param key (p_llm/visual/tts/youtube_api_key) → RPC TAK BISA LAGI
-- menulis key plaintext. Kolom non-rahasia (library/provider/voice/timezone/handle/telegram) tetap.

alter table public.tenant_configs
  add column if not exists llm_api_key_enc     text,
  add column if not exists visual_api_key_enc  text,
  add column if not exists tts_api_key_enc     text,
  add column if not exists youtube_api_key_enc text;

-- Recreate RPC tanpa param key (drop versi 11-arg lama).
drop function if exists public.set_tenant_config(text,text,text,text,text,text,text,text,text,text,boolean);

create or replace function public.set_tenant_config(
  p_llm_library      text default null,
  p_tts_provider     text default null,
  p_tts_voice        text default null,
  p_timezone         text default null,
  p_display_handle   text default null,
  p_telegram_chat_id text default null,
  p_telegram_enabled boolean default null
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.tenant_configs set
    llm_library      = coalesce(p_llm_library,      llm_library),
    llm_provider     = coalesce(p_llm_library,      llm_provider),  -- jaga flat sinkron
    tts_provider     = coalesce(p_tts_provider,     tts_provider),
    tts_voice        = coalesce(p_tts_voice,        tts_voice),
    timezone         = coalesce(p_timezone,         timezone),
    display_handle   = coalesce(p_display_handle,   display_handle),
    telegram_chat_id = coalesce(p_telegram_chat_id, telegram_chat_id),
    telegram_enabled = coalesce(p_telegram_enabled, telegram_enabled),
    updated_at       = now()
  where tenant_id = (auth.uid())::text;  -- HANYA baris milik pemanggil
end;
$$;

revoke all     on function public.set_tenant_config(text,text,text,text,text,text,boolean) from public;
revoke execute on function public.set_tenant_config(text,text,text,text,text,text,boolean) from anon;
grant  execute on function public.set_tenant_config(text,text,text,text,text,text,boolean) to authenticated;
