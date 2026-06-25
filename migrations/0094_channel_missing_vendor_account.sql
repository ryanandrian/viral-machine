-- 0094: Gerbang channel_missing — model VENDOR/key-group + AKUN per-elemen (CHANNEL_LOCK final 2026-06-25).
-- Menyempurnakan 0092: kunci AI dicek via VENDOR (ai_providers.key_group) + AKUN yg ditugaskan channel
-- (channels.{llm,tts,visual}_account_id). openai_tts pakai kunci vendor openai. Penyedia gratis (auth_type='none') tak butuh kunci.
-- Depends: 0093 (key_group + channels.*_account_id). Trigger + channel_readiness + channel_missing_by_id auto ikut (panggil fungsi sama).

-- Helper: tenant punya kunci AI valid utk elemen ini? (akun ditugaskan ATAU auto akun tunggal vendor)
create or replace function tenant_ai_key_ok(p_tenant text, p_provider text, p_account_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select case
    when coalesce(p_provider,'') = '' then false
    when p_account_id is not null then exists(
      select 1 from tenant_ai_accounts
       where id = p_account_id and tenant_id = p_tenant and status = 'valid' and key_enc is not null)
    else exists(
      select 1 from tenant_ai_accounts a
       where a.tenant_id = p_tenant and a.status = 'valid' and a.key_enc is not null
         and a.key_group = (select coalesce(key_group, p_provider) from ai_providers where provider_key = p_provider))
  end;
$$;

create or replace function channel_missing(ch channels)
returns text[] language plpgsql security definer set search_path = public stable as $$
declare
  v_miss text[] := '{}';
  vm text; v_auth text; v_mkey text; v_vprov text; has_yt boolean; has_tg boolean;
begin
  if ch.niche is null or ch.niche = '' then v_miss := array_append(v_miss, 'niche'); end if;

  -- LLM (naskah): penyedia + model(valid katalog) + kunci(vendor+akun)
  if coalesce(ch.llm_library,'') = '' then
    v_miss := array_append(v_miss, 'penyedia naskah');
  else
    if not exists(select 1 from ai_models where model_key=ch.llm_model and provider_key=ch.llm_library and component='llm' and is_active)
      then v_miss := array_append(v_miss, 'model naskah'); end if;
    select auth_type into v_auth from ai_providers where provider_key=ch.llm_library and is_active;
    if v_auth is null then v_miss := array_append(v_miss, 'penyedia naskah');
    elsif v_auth <> 'none' and not tenant_ai_key_ok(ch.tenant_id, ch.llm_library, ch.llm_account_id)
      then v_miss := array_append(v_miss, 'kunci naskah'); end if;
  end if;

  -- TTS (suara): penyedia + model + voice + kunci(vendor+akun)
  if coalesce(ch.tts_provider,'') = '' then
    v_miss := array_append(v_miss, 'penyedia suara');
  else
    if not exists(select 1 from ai_models where model_key=ch.tts_model and provider_key=ch.tts_provider and component='tts' and is_active)
      then v_miss := array_append(v_miss, 'model suara'); end if;
    if not exists(select 1 from voice_catalog where voice_key=ch.voice_key and provider_key=ch.tts_provider and is_active)
      then v_miss := array_append(v_miss, 'karakter suara'); end if;
    select auth_type into v_auth from ai_providers where provider_key=ch.tts_provider and is_active;
    if v_auth is null then v_miss := array_append(v_miss, 'penyedia suara');
    elsif v_auth <> 'none' and not tenant_ai_key_ok(ch.tenant_id, ch.tts_provider, ch.tts_account_id)
      then v_miss := array_append(v_miss, 'kunci suara'); end if;
  end if;

  -- Visual: WAJIB generator (ai_image:/ai_video:) + model valid + kunci(vendor+akun)
  vm := coalesce(ch.visual_mode,'');
  if vm not like 'ai_image:%' and vm not like 'ai_video:%' then
    v_miss := array_append(v_miss, 'jenis visual');
  else
    v_mkey := split_part(vm, ':', 2);
    select provider_key into v_vprov from ai_models where model_key=v_mkey and is_active;
    if v_vprov is null then v_miss := array_append(v_miss, 'model visual');
    else
      select auth_type into v_auth from ai_providers where provider_key=v_vprov and is_active;
      if v_auth is null then v_miss := array_append(v_miss, 'penyedia visual');
      elsif v_auth <> 'none' and not tenant_ai_key_ok(ch.tenant_id, v_vprov, ch.visual_account_id)
        then v_miss := array_append(v_miss, 'kunci visual'); end if;
    end if;
  end if;

  -- Jadwal posting
  if coalesce(array_length(ch.publish_slots,1),0) = 0 then v_miss := array_append(v_miss, 'jadwal posting'); end if;

  -- Koneksi YouTube (pool valid + target channel)
  select exists(select 1 from tenant_youtube_accounts
                 where id=ch.youtube_account_id and status='valid' and google_refresh_token_enc is not null) into has_yt;
  if ch.youtube_account_id is null or not has_yt or coalesce(ch.platform_channel_id,'') = '' then
    v_miss := array_append(v_miss, 'koneksi YouTube');
  end if;

  -- Telegram (tenant-level): chat_id terisi + aktif
  select exists(select 1 from tenant_configs
                 where tenant_id=ch.tenant_id and coalesce(telegram_chat_id,'') <> '' and coalesce(telegram_enabled,true)) into has_tg;
  if not has_tg then v_miss := array_append(v_miss, 'Telegram'); end if;

  return v_miss;
end $$;
