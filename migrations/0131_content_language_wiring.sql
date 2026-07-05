-- 0131_content_language_wiring.sql (2026-07-05)
-- BAHASA KONTEN end-to-end — menutup janji landing "Konten Multi-Bahasa" yang selama ini
-- tidak tersambung ke mesin (audit 2026-07-05):
--   1) channels.content_language: backfill + DEFAULT 'en-US' + NOT NULL + FK katalog
--   2) Katalog bahasa = HANYA aksara Latin (keputusan owner 2026-07-05) → Thai dihapus
--   3) Seed voice Indonesia (edge_tts — nama voice publik resmi Microsoft, tier gratis)
--   4) Voice OpenAI/ElevenLabs ditandai 'Multilingual' (fakta vendor: OpenAI TTS multibahasa;
--      ElevenLabs premade berbicara lintas bahasa via model eleven_multilingual_v2)
--   5) channel_missing(): + guard 'bahasa konten' (readiness, sumber kebenaran tunggal DB)

begin;

-- 1) channels.content_language — wajib terisi & valid terhadap katalog
update channels set content_language = 'en-US'
 where content_language is null or content_language = '';
alter table channels alter column content_language set default 'en-US';
alter table channels alter column content_language set not null;
alter table channels
  add constraint channels_content_language_fkey
  foreign key (content_language) references content_languages(locale);

-- 2) Hanya bahasa beraksara Latin di katalog (Thai = aksara non-Latin → dihapus)
delete from content_languages where locale = 'th-TH';

-- 3) Voice Indonesia — edge_tts (voice publik stabil Microsoft). delivery_wps 2.2 = seed awal
--    konservatif utk tempo bicara ID; DIKALIBRASI dari pengukuran audio nyata saat validasi
--    (pace_locked biarkan default agar kalibrasi F5-01 boleh menimpa).
insert into voice_catalog (voice_key, provider_key, display_name, locale, language, gender, delivery_wps, is_active, sort_order)
values
  ('id-ID-ArdiNeural',  'edge_tts', 'Ardi (Edge)',  'id-ID', 'Indonesian', 'male',   2.2, true, 110),
  ('id-ID-GadisNeural', 'edge_tts', 'Gadis (Edge)', 'id-ID', 'Indonesian', 'female', 2.2, true, 111)
on conflict (voice_key) do nothing;

-- 4) Voice multibahasa ditandai jujur (dipakai FE utk kecocokan bahasa channel)
update voice_catalog set language = 'Multilingual'
 where provider_key in ('openai_tts', 'elevenlabs');

-- 5) Readiness gate: bahasa konten wajib (identik utk FE & worker — no drift)
CREATE OR REPLACE FUNCTION public.channel_missing(ch channels)
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_miss text[] := '{}';
  vm text; v_auth text; v_mkey text; v_vprov text; has_yt boolean; has_tg boolean;
begin
  if ch.niche is null or ch.niche = '' then v_miss := array_append(v_miss, 'niche'); end if;

  -- Bahasa konten (0131): wajib terisi — menentukan bahasa naskah/judul/deskripsi/suara
  if coalesce(ch.content_language,'') = '' then v_miss := array_append(v_miss, 'bahasa konten'); end if;

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
end $function$;

commit;
