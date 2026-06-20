-- 0067_channel_readiness_rpc.sql
-- F2-01/F2-07 (§10.E.7): RPC readiness untuk FE (wizard checklist + Manage status).
-- Tenant-scoped (auth.uid) SECURITY DEFINER → tenant cek channel SENDIRI; baca key-presence
-- (tenant_configs *_enc) + OAuth (channel/tenant_credentials) tanpa expose nilai. Single-source FE.
-- Producer (service_role) tetap pakai Python channel_readiness (F1-08); kriteria sama (§10.E.7) — JAGA SINKRON.

create or replace function channel_readiness(p_channel_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  ch       channels%rowtype;
  tc       tenant_configs%rowtype;
  v_miss   text[] := '{}';
  v_vkey   text;
  vm       text;
  has_yt   boolean;
begin
  select * into ch from channels where id = p_channel_id and tenant_id = (auth.uid())::text;
  if not found then
    return jsonb_build_object('ready', false, 'missing', jsonb_build_array('akses/channel'), 'error', true);
  end if;
  select * into tc from tenant_configs where tenant_id = ch.tenant_id;

  if ch.niche is null or ch.niche = '' then v_miss := v_miss || 'niche'; end if;
  if ch.llm_model is null then v_miss := v_miss || 'model LLM'; end if;
  if ch.tts_provider is null then v_miss := v_miss || 'model/voice TTS'; end if;
  vm := coalesce(ch.visual_mode, '');
  if vm = '' then v_miss := v_miss || 'mode visual'; end if;

  -- voice resolvable: channels.voice_key → niches.voice_defaults[tts_provider]
  v_vkey := ch.voice_key;
  if v_vkey is null and ch.niche is not null and ch.tts_provider is not null then
    select (voice_defaults ->> ch.tts_provider) into v_vkey from niches where niche_id = ch.niche;
  end if;
  if v_vkey is null then v_miss := v_miss || 'voice'; end if;

  -- credential per provider (key per-tenant; cek _enc ada, tak expose nilai)
  if tc.llm_api_key_enc is null then v_miss := v_miss || 'API key LLM'; end if;
  if ch.tts_provider in ('elevenlabs','openai_tts') and tc.tts_api_key_enc is null then v_miss := v_miss || 'API key TTS'; end if;
  if (vm like 'ai_image:%' or vm like 'ai_video:%') and tc.visual_api_key_enc is null then v_miss := v_miss || 'API key visual'; end if;

  -- YouTube OAuth (channel_credentials → fallback tenant_credentials)
  select exists(select 1 from channel_credentials where channel_id = p_channel_id and google_refresh_token_enc is not null)
      or exists(select 1 from tenant_credentials  where tenant_id  = ch.tenant_id  and google_refresh_token_enc is not null)
    into has_yt;
  if not has_yt then v_miss := v_miss || 'koneksi YouTube'; end if;

  return jsonb_build_object('ready', array_length(v_miss,1) is null, 'missing', to_jsonb(v_miss));
end $$;

revoke all on function channel_readiness(uuid) from public, anon;
grant execute on function channel_readiness(uuid) to authenticated;
