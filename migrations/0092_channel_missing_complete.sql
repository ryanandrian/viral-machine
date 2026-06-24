-- 0092: Gerbang channel_missing LENGKAP (validate-early + pool + Telegram + jadwal + YouTube)
-- ============================================================================
-- Arsitektur: CHANNEL_LOCK_ACTIVATION_PLAN.md §0.8.C. Satu sumber kebenaran; dipakai trigger
-- channels_activation_gate + RPC channel_readiness (FE) + channel_missing_by_id (worker) — nol drift.
-- Kunci dicek dari POOL tenant (tenant_ai_accounts, status='valid'), provider-aware (auth_type).
-- Model LLM/TTS/Visual wajib VALID di katalog; voice valid; jadwal ≥1; YouTube account valid + target;
-- Telegram tenant tersambung. (Yang tak bisa dipra-validasi: kredit/kuota & QC → saat produksi.)

create or replace function channel_missing(ch channels)
returns text[] language plpgsql security definer set search_path = public stable as $$
declare
  v_miss text[] := '{}';
  vm text; v_auth text; v_mkey text; v_vprov text; has_yt boolean; has_tg boolean;
begin
  if ch.niche is null or ch.niche = '' then v_miss := array_append(v_miss, 'niche'); end if;

  -- LLM (naskah): penyedia + model(valid katalog) + kunci(pool, provider-aware)
  if coalesce(ch.llm_library,'') = '' then
    v_miss := array_append(v_miss, 'penyedia naskah');
  else
    if not exists(select 1 from ai_models where model_key=ch.llm_model and provider_key=ch.llm_library and component='llm' and is_active)
      then v_miss := array_append(v_miss, 'model naskah'); end if;
    select auth_type into v_auth from ai_providers where provider_key=ch.llm_library and is_active;
    if v_auth is null then v_miss := array_append(v_miss, 'penyedia naskah');
    elsif v_auth <> 'none' and not exists(select 1 from tenant_ai_accounts where tenant_id=ch.tenant_id and provider_key=ch.llm_library and status='valid' and key_enc is not null)
      then v_miss := array_append(v_miss, 'kunci naskah'); end if;
  end if;

  -- TTS (suara): penyedia + model + voice + kunci(pool)
  if coalesce(ch.tts_provider,'') = '' then
    v_miss := array_append(v_miss, 'penyedia suara');
  else
    if not exists(select 1 from ai_models where model_key=ch.tts_model and provider_key=ch.tts_provider and component='tts' and is_active)
      then v_miss := array_append(v_miss, 'model suara'); end if;
    if not exists(select 1 from voice_catalog where voice_key=ch.voice_key and provider_key=ch.tts_provider and is_active)
      then v_miss := array_append(v_miss, 'karakter suara'); end if;
    select auth_type into v_auth from ai_providers where provider_key=ch.tts_provider and is_active;
    if v_auth is null then v_miss := array_append(v_miss, 'penyedia suara');
    elsif v_auth <> 'none' and not exists(select 1 from tenant_ai_accounts where tenant_id=ch.tenant_id and provider_key=ch.tts_provider and status='valid' and key_enc is not null)
      then v_miss := array_append(v_miss, 'kunci suara'); end if;
  end if;

  -- Visual: WAJIB generator (ai_image:/ai_video:) + model valid + kunci(pool)
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
      elsif v_auth <> 'none' and not exists(select 1 from tenant_ai_accounts where tenant_id=ch.tenant_id and provider_key=v_vprov and status='valid' and key_enc is not null)
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
