-- 0031: set_tenant_config — SECURITY DEFINER RPC (Phase 9.3 increment 2).
-- Jalur tulis AMAN untuk tenant_configs: RLS row-level tak bisa batasi kolom, dan
-- tenant_configs mencampur config + billing/comp (plan_type/subscription_status/
-- is_developer/discount_pct). RPC ini = whitelist KOLOM CONFIG saja + scope auth.uid()
-- → tenant TAK pernah bisa ubah kolom billing/comp (anti self-upgrade/self-comp).
-- Dipanggil FE via anon client (authed): supabase.rpc('set_tenant_config', {...}).
-- AI keys = RLS-protected, tak dienkripsi (keputusan Phase 4.1, BYOK). OAuth/credentials
-- (sensitif, Fernet) = jalur terpisah (tenant_credentials, increment 2b).
create or replace function public.set_tenant_config(
  p_llm_api_key      text default null,
  p_visual_api_key   text default null,
  p_tts_api_key      text default null,
  p_youtube_api_key  text default null,
  p_llm_library      text default null,
  p_tts_provider     text default null,
  p_tts_voice        text default null,
  p_timezone         text default null
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.tenant_configs set
    llm_api_key     = coalesce(p_llm_api_key,     llm_api_key),
    visual_api_key  = coalesce(p_visual_api_key,  visual_api_key),
    tts_api_key     = coalesce(p_tts_api_key,     tts_api_key),
    youtube_api_key = coalesce(p_youtube_api_key, youtube_api_key),
    llm_library     = coalesce(p_llm_library,     llm_library),
    llm_provider    = coalesce(p_llm_library,     llm_provider),  -- jaga flat sinkron dgn library
    tts_provider    = coalesce(p_tts_provider,    tts_provider),
    tts_voice       = coalesce(p_tts_voice,       tts_voice),
    timezone        = coalesce(p_timezone,        timezone),
    updated_at      = now()
  where tenant_id = (auth.uid())::text;  -- HANYA baris milik pemanggil
end;
$$;

-- hanya user login (authenticated) yang boleh panggil; anon/public tidak.
-- (Supabase auto-grant execute ke anon/authenticated/service_role → cabut anon eksplisit.
--  Walau anon aman secara fungsional [auth.uid()=NULL → 0 baris], cabut = defense-in-depth.)
revoke all on function public.set_tenant_config(text,text,text,text,text,text,text,text) from public;
revoke execute on function public.set_tenant_config(text,text,text,text,text,text,text,text) from anon;
grant execute on function public.set_tenant_config(text,text,text,text,text,text,text,text) to authenticated;
