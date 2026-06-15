-- 0033: perluas whitelist set_tenant_config (Settings B5) — + display_handle, telegram_chat_id,
-- telegram_enabled (semua kolom CONFIG non-privilege; TETAP tak pernah sentuh billing/comp).
-- DROP versi 8-arg lama lalu CREATE 11-arg (named-param RPC → call subset tetap jalan).
drop function if exists public.set_tenant_config(text,text,text,text,text,text,text,text);

create or replace function public.set_tenant_config(
  p_llm_api_key      text default null,
  p_visual_api_key   text default null,
  p_tts_api_key      text default null,
  p_youtube_api_key  text default null,
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
    llm_api_key      = coalesce(p_llm_api_key,      llm_api_key),
    visual_api_key   = coalesce(p_visual_api_key,   visual_api_key),
    tts_api_key      = coalesce(p_tts_api_key,      tts_api_key),
    youtube_api_key  = coalesce(p_youtube_api_key,  youtube_api_key),
    llm_library      = coalesce(p_llm_library,      llm_library),
    llm_provider     = coalesce(p_llm_library,      llm_provider),
    tts_provider     = coalesce(p_tts_provider,     tts_provider),
    tts_voice        = coalesce(p_tts_voice,        tts_voice),
    timezone         = coalesce(p_timezone,         timezone),
    display_handle   = coalesce(p_display_handle,   display_handle),
    telegram_chat_id = coalesce(p_telegram_chat_id, telegram_chat_id),
    telegram_enabled = coalesce(p_telegram_enabled, telegram_enabled),
    updated_at       = now()
  where tenant_id = (auth.uid())::text;
end;
$$;

revoke all     on function public.set_tenant_config(text,text,text,text,text,text,text,text,text,text,boolean) from public;
revoke execute on function public.set_tenant_config(text,text,text,text,text,text,text,text,text,text,boolean) from anon;
grant  execute on function public.set_tenant_config(text,text,text,text,text,text,text,text,text,text,boolean) to authenticated;
