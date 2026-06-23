-- 0083 — VOICE per-channel (CONTRACT): REPLACE channel_readiness RPC + DROP fosil voice niche
-- §10.B/§10.H FINAL (owner 2026-06-23). BE (cea2555) + FE (3308047, deployed) sudah TIDAK membaca
-- niches.voice_defaults/voice_key/voice_profile. RPC 0067 masih → REPLACE dulu (voice=channels.voice_key), baru DROP.

-- 1) REPLACE RPC: voice readiness = channels.voice_key WAJIB (voice = channel, NO fallback niche).
create or replace function channel_readiness(p_channel_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  ch       channels%rowtype;
  tc       tenant_configs%rowtype;
  v_miss   text[] := '{}';
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

  -- voice (PER-CHANNEL, §10.B FINAL): channels.voice_key WAJIB (voice = channel, no fallback niche)
  if ch.voice_key is null then v_miss := v_miss || 'voice'; end if;

  if tc.llm_api_key_enc is null then v_miss := v_miss || 'API key LLM'; end if;
  if ch.tts_provider in ('elevenlabs','openai_tts') and tc.tts_api_key_enc is null then v_miss := v_miss || 'API key TTS'; end if;
  if (vm like 'ai_image:%' or vm like 'ai_video:%') and tc.visual_api_key_enc is null then v_miss := v_miss || 'API key visual'; end if;

  select exists(select 1 from channel_credentials where channel_id = p_channel_id and google_refresh_token_enc is not null)
      or exists(select 1 from tenant_credentials  where tenant_id  = ch.tenant_id  and google_refresh_token_enc is not null)
    into has_yt;
  if not has_yt then v_miss := v_miss || 'koneksi YouTube'; end if;

  return jsonb_build_object('ready', array_length(v_miss,1) is null, 'missing', to_jsonb(v_miss));
end $$;
revoke all on function channel_readiness(uuid) from public, anon;
grant execute on function channel_readiness(uuid) to authenticated;

-- 2) DROP fosil voice niche (niche = provider-agnostik, tak punya voice). narration_persona (0082) menyimpan data persona.
ALTER TABLE niches DROP COLUMN IF EXISTS voice_defaults;
ALTER TABLE niches DROP COLUMN IF EXISTS voice_key;
ALTER TABLE niches DROP COLUMN IF EXISTS voice_profile;
