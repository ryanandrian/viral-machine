-- 0206 — GERBANG KELAYAKAN KATALOG: baris katalog tak bisa DINYALAKAN sebelum syaratnya lengkap.
-- Rencana: /home/rad/.claude/plans/cozy-booping-shell.md langkah 6c · SSOT: AI_ERROR_MGMT §9c
--
-- ═══ PERSOALAN ═══
-- Menyalakan baris katalog hari ini = saklar berpindah, titik. Tak ada yang memeriksa apakah
-- syaratnya lengkap. Akibatnya yang sudah TERUKUR di lapangan:
--   · penyedia/model setengah-jadi langsung terpapar tenant (POST tak menulis is_active ⇒ bawaan
--     DB `true` — terukur: 0014_tts_profiles.sql:13, 0038_voice_catalog.sql:12)
--   · penyedia tanpa baris `galat_registry.PENYEDIA` ⇒ galat vendor jatuh ke UNKNOWN = BOLEH
--     DIULANG ⇒ kunci salah / saldo habis diulang 3× dan membakar kredit TENANT
--   · model TTS menyala padahal `tts_profiles`-nya mati ⇒ ini ANATOMI insiden TTS Gemini
--   · `delivery_wps` kosong ⇒ jatuh SENYAP ke 2.4 ⇒ anggaran kata salah ⇒ durasi melenceng ⇒
--     QC menolak (kelas kerusakan 18-Agu)
--   · harga kosong ⇒ biaya dilaporkan LEBIH MURAH dari kenyataan, dan produksi tetap jalan
--     (tak ada rem berbasis biaya di mana pun — rem hanya membaca ErrorClass)
--
-- ═══ KEPUTUSAN OWNER YANG MENGIKAT ═══
-- 21-Agu: "sistem harus mencegah admin membuat kesalahan yang berdampak ke tenant."
-- Pembeda penting, dan ia SENGAJA asimetris:
--   MEMATIKAN  = tetap BEBAS (Batch B §9b) — kalau vendor mematikan model, admin WAJIB bisa
--                mematikannya; blokir keras = "kunci tanpa jalur buka" (PAYMENT §10e-2).
--   MENGHIDUPKAN = diperketat.
--
-- ═══ KENAPA DI DB, BUKAN DI API ═══
-- Karena jalur yang MEMUTARI panel-lah yang sudah terbukti dipakai: mesin suara Gemini saya
-- nyalakan lewat SKRIP, bukan lewat panel. Gerbang yang hanya hidup di API tak akan menahan
-- tangan saya sendiri. Di sini ia menahan SEMUA jalur tulis, termasuk skrip dan SQL manual.
--
-- ═══ AMAN SECARA TERUKUR, BUKAN SECARA HARAPAN ═══
-- Diukur pada katalog PRODUKSI sebelum ditulis: 9 penyedia aktif · 41 model aktif · 5 mesin suara
-- aktif · 42 suara aktif = **NOL** yang melanggar 17 syarat di bawah. Jadi memasangnya tidak
-- mengunci satu pun baris yang hari ini hidup. Trigger pun hanya menyala pada TRANSISI ke aktif,
-- jadi baris lama yang sudah aktif tak pernah diperiksa sama sekali (jawaban untuk baris LAMA).

begin;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 1) PEMERIKSA — sepola `channel_missing()`: mengembalikan DAFTAR KODE, bukan kalimat.
--    Kalimatnya milik FE (aturan dwibahasa: API kirim kode, FE menerjemahkan ID/EN).
--    Kosong = layak. Tabel di luar daftar = layak (jangan menghalangi apa yang tak dimengerti).
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.catalog_missing(p_table text, p_key text)
returns text[]
language plpgsql
stable
security definer
set search_path to 'public'
as $function$
declare
  v_out   text[] := '{}';
  v_adapt text;
  v_auth  text;
  v_comp  text;
  v_prov  text;
  v_akt   boolean;
  v_wps   numeric;
  v_price jsonb;
  v_mid   text;
  v_loc   text;
  v_prev  text;
  v_n     int;
begin
  -- ── ai_providers ────────────────────────────────────────────────────────────────────────────
  if p_table = 'ai_providers' then
    select adapter, auth_type into v_adapt, v_auth from ai_providers where provider_key = p_key;
    if not found then return array['baris_tak_ada']; end if;
    if coalesce(v_adapt,'') = '' then
      v_out := v_out || 'adapter_kosong';
    elsif not exists (select 1 from catalog_valid_values
                       where field in ('llm_adapter','tts_adapter','visual_transport')
                         and value = v_adapt) then
      -- Protokol yang tak dikenal mesin = BUTUH PEKERJAAN KODE, bukan salah ketik admin.
      v_out := v_out || 'adapter_tak_didukung';
    end if;
    if not exists (select 1 from catalog_valid_values where field = 'auth_type' and value = coalesce(v_auth,'')) then
      v_out := v_out || 'auth_type_tak_sah';
    end if;
    -- Tanpa baris registry galat: galat vendor → UNKNOWN → BOLEH DIULANG → kredit TENANT terbakar.
    if not exists (select 1 from catalog_valid_values
                    where field = 'galat_registry_provider' and value = p_key) then
      v_out := v_out || 'tak_ada_di_registry_galat';
    end if;
    return v_out;
  end if;

  -- ── ai_models ───────────────────────────────────────────────────────────────────────────────
  if p_table = 'ai_models' then
    select provider_key, component, model_id, pricing
      into v_prov, v_comp, v_mid, v_price
      from ai_models where model_key = p_key;
    if not found then return array['baris_tak_ada']; end if;

    select is_active into v_akt from ai_providers where provider_key = v_prov;
    if not found then v_out := v_out || 'penyedia_tak_ada';
    elsif not coalesce(v_akt,false) then v_out := v_out || 'penyedia_nonaktif';
    end if;

    -- model_id = ID RESMI vendor (bukan model_key kita). Salah/kosong ⇒ produksi gagal di vendor.
    if coalesce(v_mid,'') = '' then v_out := v_out || 'model_id_kosong'; end if;
    if v_price is null or v_price = '{}'::jsonb then v_out := v_out || 'harga_kosong'; end if;
    if not exists (select 1 from catalog_valid_values where field = 'component' and value = coalesce(v_comp,'')) then
      v_out := v_out || 'component_tak_sah';
    end if;

    -- TTS butuh EMPAT tabel hidup serentak. Inilah anatomi insiden TTS Gemini: penyaringnya cuma
    -- ada di SATU layar tenant; produksi, gerbang DB, tombol Uji & Test Lab tak memeriksanya.
    if v_comp = 'tts' then
      select is_active into v_akt from tts_profiles where provider_key = v_prov;
      if not found then v_out := v_out || 'mesin_suara_tak_ada';
      elsif not coalesce(v_akt,false) then v_out := v_out || 'mesin_suara_mati';
      end if;
      select count(*) into v_n from voice_catalog where provider_key = v_prov and is_active = true;
      if coalesce(v_n,0) = 0 then v_out := v_out || 'nol_suara_aktif'; end if;
    end if;

    -- Video butuh preset ber-render_mode ai_video (1 klip ≠ N beat) — tanpa itu model tak terpakai.
    if v_comp = 'video' then
      select count(*) into v_n from duration_presets where render_mode = 'ai_video' and is_active = true;
      if coalesce(v_n,0) = 0 then v_out := v_out || 'preset_video_tak_ada'; end if;
    end if;
    return v_out;
  end if;

  -- ── tts_profiles (MESIN SUARA) ──────────────────────────────────────────────────────────────
  if p_table = 'tts_profiles' then
    select adapter, delivery_wps into v_adapt, v_wps from tts_profiles where provider_key = p_key;
    if not found then return array['baris_tak_ada']; end if;
    if coalesce(v_adapt,'') = '' then
      v_out := v_out || 'adapter_kosong';
    elsif not exists (select 1 from catalog_valid_values where field = 'tts_adapter' and value = v_adapt) then
      v_out := v_out || 'adapter_tak_didukung';
    end if;
    -- Kosong ⇒ jatuh SENYAP ke 2.4 ⇒ anggaran kata salah ⇒ durasi melenceng ⇒ QC menolak.
    if coalesce(v_wps, 0) <= 0 then v_out := v_out || 'tempo_kosong'; end if;
    select is_active into v_akt from ai_providers where provider_key = p_key;
    if not found then v_out := v_out || 'penyedia_tak_ada';
    elsif not coalesce(v_akt,false) then v_out := v_out || 'penyedia_nonaktif';
    end if;
    return v_out;
  end if;

  -- ── voice_catalog ───────────────────────────────────────────────────────────────────────────
  if p_table = 'voice_catalog' then
    select provider_key, locale, preview_url into v_prov, v_loc, v_prev
      from voice_catalog where voice_key = p_key;
    if not found then return array['baris_tak_ada']; end if;
    select is_active into v_akt from tts_profiles where provider_key = v_prov;
    if not found then v_out := v_out || 'mesin_suara_tak_ada';
    elsif not coalesce(v_akt,false) then v_out := v_out || 'mesin_suara_mati';
    end if;
    if coalesce(v_loc,'')  = '' then v_out := v_out || 'bahasa_kosong'; end if;
    -- Contoh suara sudah DIWAJIBKAN uji yang ada (`test_katalog_suara_tak_menipu.py`) — gerbang ini
    -- hanya membuatnya ditegakkan pada saat penyalaan, bukan menemukan syarat baru.
    if coalesce(v_prev,'') = '' then v_out := v_out || 'contoh_suara_kosong'; end if;
    return v_out;
  end if;

  return v_out;   -- tabel di luar lingkup: layak (jangan menghalangi yang tak dimengerti)
end $function$;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 2) TRIGGER — HANYA pada TRANSISI menjadi aktif.
--    Dua pembatas yang membuatnya tak bisa merusak apa pun yang sekarang hidup:
--      (a) `new.is_active = true`         ⇒ MEMATIKAN tak pernah tertahan
--      (b) `not coalesce(old.is_active,false)` ⇒ baris yang SUDAH aktif tak pernah diperiksa,
--          jadi menyunting harga/nama/urutan pada baris aktif tidak bisa ikut ditolak.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.trg_catalog_activation_gate()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_miss text[];
  v_pk   text;
begin
  if not (coalesce(new.is_active, false) = true and not coalesce(old.is_active, false)) then
    return new;   -- bukan transisi menjadi aktif → lewat tanpa diperiksa sama sekali
  end if;
  v_pk := case tg_table_name
            when 'ai_models'     then new.model_key
            when 'ai_providers'  then new.provider_key
            when 'tts_profiles'  then new.provider_key
            when 'voice_catalog' then new.voice_key
          end;
  v_miss := catalog_missing(tg_table_name::text, v_pk);
  if array_length(v_miss, 1) is not null then
    -- Pesan = DAFTAR KODE, bukan kalimat: API menerjemahkannya jadi `activation_blocked` + detail,
    -- FE menerjemahkan ke ID/EN. Prefix dipakai rute untuk mengenalinya tanpa mencocokkan kalimat.
    raise exception 'CATALOG_ACTIVATION_BLOCKED: %', array_to_string(v_miss, ',')
      using errcode = 'check_violation';
  end if;
  return new;
end $function$;

drop trigger if exists trg_gate_ai_models     on ai_models;
drop trigger if exists trg_gate_ai_providers  on ai_providers;
drop trigger if exists trg_gate_tts_profiles  on tts_profiles;
drop trigger if exists trg_gate_voice_catalog on voice_catalog;

create trigger trg_gate_ai_models     before update on ai_models
  for each row execute function trg_catalog_activation_gate();
create trigger trg_gate_ai_providers  before update on ai_providers
  for each row execute function trg_catalog_activation_gate();
create trigger trg_gate_tts_profiles  before update on tts_profiles
  for each row execute function trg_catalog_activation_gate();
create trigger trg_gate_voice_catalog before update on voice_catalog
  for each row execute function trg_catalog_activation_gate();

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 3) SATU PINTU BACA untuk panel: kelayakan SELURUH baris katalog dalam sekali jalan.
--    Kenapa bukan memanggil `catalog_missing` per baris: katalog produksi = 9 penyedia + 46 model
--    + 6 mesin suara + 44 suara = 105 panggilan tiap layar dibuka. Ini satu.
--    Gunanya BUKAN menolak — menolak sudah dikerjakan trigger. Gunanya MENCEGAH: admin melihat
--    apa yang kurang SEBELUM menyentuh saklar, bukan menabrak dinding sesudah menekan.
--    Hanya menyebut baris yang BELUM layak; baris layak tak ikut (payload tetap kecil).
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.catalog_missing_all()
returns jsonb
language plpgsql
stable
security definer
set search_path to 'public'
as $function$
declare
  v_out jsonb := '{}'::jsonb;
  r     record;
  v_m   text[];
begin
  for r in
    select 'ai_providers'  as tbl, provider_key as key from ai_providers
    union all select 'ai_models',     model_key    from ai_models
    union all select 'tts_profiles',  provider_key from tts_profiles
    union all select 'voice_catalog', voice_key    from voice_catalog
  loop
    v_m := catalog_missing(r.tbl, r.key);
    if array_length(v_m, 1) is not null then
      v_out := jsonb_set(v_out, array[r.tbl], coalesce(v_out -> r.tbl, '{}'::jsonb)
                         || jsonb_build_object(r.key, to_jsonb(v_m)), true);
    end if;
  end loop;
  return v_out;
end $function$;

-- Hak pakai: pemeriksa dibaca panel admin lewat service_role; tenant tak pernah memanggilnya.
revoke all on function public.catalog_missing(text, text) from public, anon, authenticated;
revoke all on function public.catalog_missing_all() from public, anon, authenticated;

commit;
