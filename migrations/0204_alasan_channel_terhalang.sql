-- 0204 — ALASAN BERSTRUKTUR di samping label kesiapan channel (Batch A langkah 1).
-- Rencana & bukti: /home/rad/.claude/plans/cozy-booping-shell.md  ·  SSOT: AI_ERROR_MANAGEMENT §1/§9
--
-- ═══ PERSOALAN ═══
-- `channel_missing()` mengembalikan LABEL PENDEK (16 teks yang mungkin). Satu label menampung
-- keadaan yang tindakannya BEDA JAUH:
--     'model naskah'  =  (a) tenant belum memilih model, ATAU
--                        (b) model pilihannya sudah DIPENSIUNKAN penyedianya
-- Tenant tak bisa tahu mana yang menimpanya. Itu sebabnya 4 channel diam 4 hari (17-Agu):
-- yang lewat pintu produksi dapat pesan jelas (MODEL_UNAVAILABLE), yang diam hanya dapat label.
--
-- ═══ KENAPA LABELNYA TIDAK DIUBAH ═══
-- Label itu dipakai MESIN sebagai kunci: checklist 7 baris di layar tenant mencocokkan katanya
-- (`channels/[id]/page.tsx:920-928` → has("naskah"), has("suara"), has("visual"), …).
-- Mengubah teksnya membuat checklist itu SALAH (hijau padahal rusak) — kelas kerusakan 17-Agu.
-- Karena itu: ke-16 teks TIDAK DISENTUH. Yang ditambahkan adalah jawaban KEDUA di sebelahnya.
--
--     SEKARANG : { ready:false, missing:["model naskah"] }
--     SESUDAH  : { ready:false, missing:["model naskah"],   ← IDENTIK, byte per byte
--                  reasons:[{slot,code,model,provider,provider_name}] }   ← BARU
--
-- Enam pembaca lama hanya membaca `.ready`/`.missing` ⇒ kunci baru mereka abaikan. Aman SECARA
-- KONSTRUKSI, bukan secara harapan.
--
-- ═══ LINGKUP SENGAJA SEMPIT ═══
-- Fungsi ini HANYA menjawab keadaan yang bisa diukur pasti: baris katalog yang ditunjuk channel
-- sudah TIDAK AKTIF, atau TIDAK ADA. Keadaan lain (kunci belum diisi, jadwal kosong, dst) tetap
-- label-saja — tidak diklaim lebih dari yang bisa dibuktikan.
-- Diketahui-belum-tercakup: model AKTIF tapi `provider_key`-nya ≠ `channels.llm_library`
-- (paket campuran). Gerbang tetap menahannya lewat label; alasan berstrukturnya belum dibuat.

begin;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 1) FUNGSI BARU. `channel_missing()` TIDAK disentuh sama sekali.
--    Kosakata `code` mengikuti `src/exceptions.py` (ErrorClass) supaya nol kosakata baru:
--      model_unavailable   → baris katalog ADA tapi is_active=false (lazim: vendor mematikannya)
--      model_not_in_catalog→ baris katalog TIDAK ADA (di-rename/dihapus)
--      voice_unavailable   → suara pilihan tenant tidak aktif / tidak ada
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.channel_blockers(ch channels)
returns jsonb
language plpgsql
stable
security definer
set search_path to 'public'
as $function$
declare
  v_out  jsonb := '[]'::jsonb;
  v_mkey text;
  v_akt  boolean;
  v_prov text;
  v_nama text;
begin
  -- ── naskah (llm) ──────────────────────────────────────────────────────────────────────────
  if coalesce(ch.llm_model, '') <> '' then
    select m.is_active, m.provider_key, p.display_name
      into v_akt, v_prov, v_nama
      from ai_models m
      left join ai_providers p on p.provider_key = m.provider_key
     where m.model_key = ch.llm_model and m.component = 'llm'
     limit 1;
    if not found then
      v_out := v_out || jsonb_build_object(
        'slot','llm', 'code','model_not_in_catalog', 'model', ch.llm_model,
        'provider', coalesce(ch.llm_library,''), 'provider_name', null);
    elsif not coalesce(v_akt, false) then
      v_out := v_out || jsonb_build_object(
        'slot','llm', 'code','model_unavailable', 'model', ch.llm_model,
        'provider', v_prov, 'provider_name', v_nama);
    end if;
  end if;

  -- ── suara (tts): model ────────────────────────────────────────────────────────────────────
  if coalesce(ch.tts_model, '') <> '' then
    select m.is_active, m.provider_key, p.display_name
      into v_akt, v_prov, v_nama
      from ai_models m
      left join ai_providers p on p.provider_key = m.provider_key
     where m.model_key = ch.tts_model and m.component = 'tts'
     limit 1;
    if not found then
      v_out := v_out || jsonb_build_object(
        'slot','tts', 'code','model_not_in_catalog', 'model', ch.tts_model,
        'provider', coalesce(ch.tts_provider,''), 'provider_name', null);
    elsif not coalesce(v_akt, false) then
      v_out := v_out || jsonb_build_object(
        'slot','tts', 'code','model_unavailable', 'model', ch.tts_model,
        'provider', v_prov, 'provider_name', v_nama);
    end if;
  end if;

  -- ── suara (tts): karakter suara ───────────────────────────────────────────────────────────
  if coalesce(ch.voice_key, '') <> '' then
    select v.is_active, v.provider_key, p.display_name
      into v_akt, v_prov, v_nama
      from voice_catalog v
      left join ai_providers p on p.provider_key = v.provider_key
     where v.voice_key = ch.voice_key
     limit 1;
    if not found then
      v_out := v_out || jsonb_build_object(
        'slot','voice', 'code','model_not_in_catalog', 'model', ch.voice_key,
        'provider', coalesce(ch.tts_provider,''), 'provider_name', null);
    elsif not coalesce(v_akt, false) then
      v_out := v_out || jsonb_build_object(
        'slot','voice', 'code','voice_unavailable', 'model', ch.voice_key,
        'provider', v_prov, 'provider_name', v_nama);
    end if;
  end if;

  -- ── visual: model di balik prefix ai_image:/ai_video: ─────────────────────────────────────
  -- Pencarian TANPA filter `component`, meniru `channel_missing()` apa adanya (jangan berdivergensi).
  v_mkey := split_part(coalesce(ch.visual_mode,''), ':', 2);
  if coalesce(v_mkey,'') <> '' then
    select m.is_active, m.provider_key, p.display_name
      into v_akt, v_prov, v_nama
      from ai_models m
      left join ai_providers p on p.provider_key = m.provider_key
     where m.model_key = v_mkey
     limit 1;
    if not found then
      v_out := v_out || jsonb_build_object(
        'slot','visual', 'code','model_not_in_catalog', 'model', v_mkey,
        'provider', '', 'provider_name', null);
    elsif not coalesce(v_akt, false) then
      v_out := v_out || jsonb_build_object(
        'slot','visual', 'code','model_unavailable', 'model', v_mkey,
        'provider', v_prov, 'provider_name', v_nama);
    end if;
  end if;

  return v_out;
end $function$;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 2) Pintu untuk WORKER (service_role) — sepadan dengan `channel_missing_by_id` yang sudah ada.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.channel_blockers_by_id(p_channel_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path to 'public'
as $function$
declare ch channels%rowtype;
begin
  select * into ch from channels where id = p_channel_id;
  if not found then return '[]'::jsonb; end if;
  return channel_blockers(ch);
end $function$;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 3) `channel_readiness` — DUA kunci lama DIPERTAHANKAN PERSIS, satu kunci baru ditambahkan.
--    Cabang "tak ditemukan" (akses/channel) juga dipertahankan apa adanya + reasons kosong,
--    supaya pembaca baru tak pernah menemui kunci yang tiada.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create or replace function public.channel_readiness(p_channel_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  ch     channels%rowtype;
  v_miss text[];
begin
  select * into ch from channels where id = p_channel_id and tenant_id = (auth.uid())::text;
  if not found then
    return jsonb_build_object('ready', false, 'missing', jsonb_build_array('akses/channel'),
                              'error', true, 'reasons', '[]'::jsonb);
  end if;
  v_miss := channel_missing(ch);
  return jsonb_build_object('ready', array_length(v_miss,1) is null, 'missing', to_jsonb(v_miss),
                            'reasons', channel_blockers(ch));
end $function$;

-- Hak pakai: mengikuti pola fungsi kesiapan yang sudah ada (tenant login lewat RPC; worker service_role).
revoke all     on function public.channel_blockers_by_id(uuid) from public;
revoke execute on function public.channel_blockers_by_id(uuid) from anon;
grant  execute on function public.channel_blockers_by_id(uuid) to authenticated;

commit;
