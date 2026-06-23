-- 0089: Kunci AI per-channel INLINE + RPC readiness provider-aware + trigger gerbang aktivasi
-- ============================================================================
-- Owner 2026-06-24: tiap CHANNEL wajib lengkap Penyedia + Model + Kunci untuk SETIAP
-- elemen AI (LLM=naskah, TTS=suara, Visual=gambar/video). NOL fallback — belum lengkap →
-- tak ready → tak boleh aktif → tak boleh produksi. Kunci boleh sama/beda antar channel,
-- tapi DICATAT EKSPLISIT per elemen per channel.
--
-- Akar "berantakan" (terverifikasi DB live): kunci tabrakan dua tempat —
--   produksi pakai brankas tenant_api_accounts (via channels.*_account_id),
--   tapi RPC channel_readiness cek tenant_configs.*_api_key_enc (lapisan BERBEDA).
--   + fallback diam-diam tenant_config.py._overlay_account_key.
--
-- Fix: kunci pindah ke kolom INLINE channels.{llm,tts,visual}_key_enc (Fernet) = SATU tempat.
-- Brankas + kolom account_id + tenant_configs key = dipensiun (di-drop di 0090 setelah BE/FE pindah & ryan tervalidasi).
-- Edge TTS gratis (ai_providers.auth_type='none') → tak butuh kunci (gerbang provider-aware).

-- 1) Kolom kunci inline per-channel (Fernet, ditulis via route server encrypt) ----------
alter table channels
  add column if not exists llm_key_enc    text,
  add column if not exists tts_key_enc    text,
  add column if not exists visual_key_enc text;

-- 2) Backfill kunci existing (ryan) dari brankas akun yang ditunjuk → kolom inline ------
update channels c set llm_key_enc = a.key_enc
  from tenant_api_accounts a
 where c.llm_account_id = a.id and a.key_enc is not null and c.llm_key_enc is null;
update channels c set tts_key_enc = a.key_enc
  from tenant_api_accounts a
 where c.tts_account_id = a.id and a.key_enc is not null and c.tts_key_enc is null;
update channels c set visual_key_enc = a.key_enc
  from tenant_api_accounts a
 where c.image_account_id = a.id and a.key_enc is not null and c.visual_key_enc is null;

-- 2b) Backfill cadangan dari tenant_configs (channel yang dulu pakai jalur fallback tenant) --
update channels c set llm_key_enc = tc.llm_api_key_enc
  from tenant_configs tc
 where c.tenant_id = tc.tenant_id and c.llm_key_enc is null and tc.llm_api_key_enc is not null;
update channels c set tts_key_enc = tc.tts_api_key_enc
  from tenant_configs tc
 where c.tenant_id = tc.tenant_id and c.tts_key_enc is null and tc.tts_api_key_enc is not null
   and c.tts_provider in ('elevenlabs','openai_tts');
update channels c set visual_key_enc = tc.visual_api_key_enc
  from tenant_configs tc
 where c.tenant_id = tc.tenant_id and c.visual_key_enc is null and tc.visual_api_key_enc is not null
   and (c.visual_mode like 'ai_image:%' or c.visual_mode like 'ai_video:%');

-- 2c) Backfill MODEL TTS eksplisit (model wajib per elemen) — channel yang tts_provider set
--     tapi tts_model kosong → default katalog (sort_order terkecil aktif). Mis. edge_tts → edge-neural.
update channels c set tts_model = (
    select m.model_key from ai_models m
     where m.component='tts' and m.provider_key = c.tts_provider and m.is_active
     order by m.sort_order limit 1)
 where c.tts_provider is not null and (c.tts_model is null or c.tts_model = '');

-- 3) Helper: daftar elemen yang KURANG untuk satu channel (dipakai RPC + trigger) -------
--    Provider-aware: kunci wajib HANYA bila penyedia elemen itu auth_type<>'none'.
create or replace function channel_missing(ch channels)
returns text[] language plpgsql security definer set search_path = public stable as $$
declare
  v_miss   text[] := '{}';
  vm       text;
  v_auth   text;
  v_mkey   text;
  v_vprov  text;
  has_yt   boolean;
begin
  if ch.niche is null or ch.niche = '' then v_miss := array_append(v_miss, 'niche'); end if;

  -- LLM (naskah): penyedia + model + kunci(provider-aware)
  if ch.llm_library is null or ch.llm_library = '' then
    v_miss := array_append(v_miss, 'penyedia naskah');
  else
    if ch.llm_model is null or ch.llm_model = '' then v_miss := array_append(v_miss, 'model naskah'); end if;
    select auth_type into v_auth from ai_providers where provider_key = ch.llm_library and is_active;
    if v_auth is null then
      v_miss := array_append(v_miss, 'penyedia naskah');
    elsif v_auth <> 'none' and (ch.llm_key_enc is null or ch.llm_key_enc = '') then
      v_miss := array_append(v_miss, 'kunci naskah');
    end if;
  end if;

  -- TTS (suara): penyedia + model + karakter suara + kunci(provider-aware)
  if ch.tts_provider is null or ch.tts_provider = '' then
    v_miss := array_append(v_miss, 'penyedia suara');
  else
    if ch.tts_model is null or ch.tts_model = '' then v_miss := array_append(v_miss, 'model suara'); end if;
    if ch.voice_key is null or ch.voice_key = '' then v_miss := array_append(v_miss, 'karakter suara'); end if;
    select auth_type into v_auth from ai_providers where provider_key = ch.tts_provider and is_active;
    if v_auth is null then
      v_miss := array_append(v_miss, 'penyedia suara');
    elsif v_auth <> 'none' and (ch.tts_key_enc is null or ch.tts_key_enc = '') then
      v_miss := array_append(v_miss, 'kunci suara');
    end if;
  end if;

  -- Visual: WAJIB generator AI (ai_image:/ai_video:) → model + kunci(provider-aware).
  -- Footage/library (mis. bare 'video' Pexels) dibuang di v2 → nilai non-generator = tak lengkap.
  vm := coalesce(ch.visual_mode, '');
  if vm not like 'ai_image:%' and vm not like 'ai_video:%' then
    v_miss := array_append(v_miss, 'jenis visual');
  else
    v_mkey := split_part(vm, ':', 2);
    if v_mkey = '' then
      v_miss := array_append(v_miss, 'model visual');
    else
      select provider_key into v_vprov from ai_models where model_key = v_mkey and is_active;
      if v_vprov is null then
        v_miss := array_append(v_miss, 'model visual');
      else
        select auth_type into v_auth from ai_providers where provider_key = v_vprov and is_active;
        if v_auth is null then
          v_miss := array_append(v_miss, 'penyedia visual');
        elsif v_auth <> 'none' and (ch.visual_key_enc is null or ch.visual_key_enc = '') then
          v_miss := array_append(v_miss, 'kunci visual');
        end if;
      end if;
    end if;
  end if;

  -- YouTube OAuth (per-channel; fallback legacy tenant_credentials)
  select exists(select 1 from channel_credentials where channel_id = ch.id and google_refresh_token_enc is not null)
      or exists(select 1 from tenant_credentials  where tenant_id  = ch.tenant_id and google_refresh_token_enc is not null)
    into has_yt;
  if not has_yt then v_miss := array_append(v_miss, 'koneksi YouTube'); end if;

  return v_miss;
end $$;

-- 4) RPC channel_readiness — dipakai FE (RLS pemilik via auth.uid()) --------------------
create or replace function channel_readiness(p_channel_id uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  ch     channels%rowtype;
  v_miss text[];
begin
  select * into ch from channels where id = p_channel_id and tenant_id = (auth.uid())::text;
  if not found then
    return jsonb_build_object('ready', false, 'missing', jsonb_build_array('akses/channel'), 'error', true);
  end if;
  v_miss := channel_missing(ch);
  return jsonb_build_object('ready', array_length(v_miss,1) is null, 'missing', to_jsonb(v_miss));
end $$;

-- 4b) RPC channel_missing_by_id — dipakai WORKER (service_role, tanpa auth.uid()) supaya
--     producer & gerbang pakai LOGIKA IDENTIK dgn FE (akar bug "BE vs DB beda lapisan" hilang).
create or replace function channel_missing_by_id(p_channel_id uuid)
returns text[] language plpgsql security definer set search_path = public stable as $$
declare ch channels%rowtype;
begin
  select * into ch from channels where id = p_channel_id;
  if not found then return array['akses/channel']; end if;
  return channel_missing(ch);
end $$;

-- 5) Trigger gerbang aktivasi: DB tolak is_active=true bila channel belum lengkap -------
--    (penjaga terakhir; FE & worker tetap cek, tapi DB tak bisa di-bypass).
--    Menyala saat: INSERT is_active=true, atau UPDATE transisi false→true.
--    (channels.is_active TIDAK pernah ditulis worker — hanya FE; verified grep 2026-06-24.)
create or replace function trg_channels_activation_gate()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_miss text[];
begin
  if NEW.is_active and (TG_OP = 'INSERT' or not coalesce(OLD.is_active, false)) then
    v_miss := channel_missing(NEW);
    if array_length(v_miss,1) is not null then
      raise exception 'Channel belum lengkap — tak bisa diaktifkan. Kurang: %', array_to_string(v_miss, ', ')
        using errcode = 'check_violation';
    end if;
  end if;
  return NEW;
end $$;

drop trigger if exists channels_activation_gate on channels;
create trigger channels_activation_gate
  before insert or update on channels
  for each row execute function trg_channels_activation_gate();
