-- 0218 — Gerbang kelengkapan channel menjaga DUA pintu, bukan satu.
--
-- KEJADIAN (owner, 6–11 Sep 2026): channel `RAD The Explorer` diam 6 hari, stok terkuras. Tenant
-- mengganti penyedia suara ElevenLabs→OpenAI; layar MENGOSONGKAN model & karakter suara (benar —
-- voice lama tak sah di penyedia baru), tombol Simpan MENERIMANYA, channel jatuh tak-lengkap, mesin
-- melewatinya, dan alarm yang sampai ke tenant hanya "Buffer kosong" tanpa pernah menyebut sebabnya.
--
-- AKAR — SATU titik. Gerbang ini menjaga pintu "MENGAKTIFKAN" (tak lengkap ⇒ ditolak + kurangnya
-- disebut), tapi syaratnya `NEW.is_active and (INSERT or not OLD.is_active)` ⇒ channel yang SUDAH
-- aktif tak pernah diperiksa lagi. Terukur: 4 channel separuh di sistem SEMUANYA nonaktif (gerbang
-- menolak mereka aktif), sementara channel aktif bisa jatuh separuh kapan saja.
--
-- KENAPA DI SINI, BUKAN DI LAYAR: `channel_missing()` = SUMBER KEBENARAN TUNGGAL yang sudah dipakai
-- layar DAN mesin. Memagari di layar = menulis aturan KEDUA (pasti melenceng seiring waktu) dan hanya
-- menutup satu pintu dari banyak (kartu suara · naskah · visual · layar admin · API · skrip). Satu
-- pagar di sini menutup semuanya dengan aturan yang sama.
--
-- TIGA HAL YANG PAGAR INI HARAM RUSAK:
--  1. ANTI-SANDERA — channel yang SUDAH tak lengkap wajib TETAP bisa disimpan. Channel bisa jatuh
--     tak-lengkap tanpa tenant menyentuhnya (model pilihannya dinonaktifkan admin di katalog); pagar
--     yang menolak SEMUA penyimpanan saat tak lengkap membuat tenant mustahil memperbaiki channelnya.
--     ⇒ syarat `channel_missing(OLD)` KOSONG: hanya perubahan yang MENJATUHKAN yang ditolak.
--  2. MESIN TETAP BEBAS — `youtube_oauth.py` mengosongkan `youtube_account_id` saat izin Google
--     dicabut; itu MENJATUHKAN kelengkapan dan itu SAH (channel berkoneksi mati wajib bisa
--     dihentikan sistem). Pembeda = `auth.uid()`, pola yang sudah dipakai `trg_channels_rem_readonly`:
--     mesin (service_role) → NULL → bebas; tenant (authenticated) → dipagari.
--  3. NONAKTIF TETAP BEBAS disiapkan bertahap — di situ pintu 1 sudah berjaga di jalan keluarnya.
--
-- BEBAN: `channel_missing()` ≈8 kueri dan mesin meng-UPDATE `channels` cukup sering (rem · stok ·
-- resumed_at · subscribers). Karena itu pintu 2 didahului pagar MURAH: hanya jalan bila salah satu
-- kolom yang menentukan kelengkapan benar-benar berubah. UPDATE mesin nol menyentuhnya ⇒ nol beban baru.
--
-- Pintu 1 disalin PERSIS dari versi sebelumnya — nol perubahan perilaku aktivasi.

create or replace function public.trg_channels_activation_gate()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_miss     text[];
  v_miss_old text[];
begin
  -- ── PINTU 1 (sejak 20-Jun) — MENGAKTIFKAN channel. TIDAK diubah. ─────────────
  if NEW.is_active and (TG_OP = 'INSERT' or not coalesce(OLD.is_active, false)) then
    v_miss := channel_missing(NEW);
    if array_length(v_miss,1) is not null then
      raise exception 'Channel belum lengkap — tak bisa diaktifkan. Kurang: %', array_to_string(v_miss, ', ')
        using errcode = 'check_violation';
    end if;
    return NEW;
  end if;

  -- ── PINTU 2 (11-Sep) — perubahan TENANT yang MENJATUHKAN channel aktif ───────
  if TG_OP = 'UPDATE'
     and NEW.is_active and coalesce(OLD.is_active, false)
     and auth.uid() is not null                      -- mesin (service_role) bebas — RANJAU 2
     and (                                           -- pagar MURAH sebelum ≈8 kueri
          NEW.niche               is distinct from OLD.niche
       or NEW.content_language    is distinct from OLD.content_language
       or NEW.llm_library         is distinct from OLD.llm_library
       or NEW.llm_model           is distinct from OLD.llm_model
       or NEW.llm_account_id      is distinct from OLD.llm_account_id
       or NEW.tts_provider        is distinct from OLD.tts_provider
       or NEW.tts_model           is distinct from OLD.tts_model
       or NEW.voice_key           is distinct from OLD.voice_key
       or NEW.tts_account_id      is distinct from OLD.tts_account_id
       or NEW.visual_mode         is distinct from OLD.visual_mode
       or NEW.visual_account_id   is distinct from OLD.visual_account_id
       or NEW.publish_slots       is distinct from OLD.publish_slots
       or NEW.youtube_account_id  is distinct from OLD.youtube_account_id
       or NEW.platform_channel_id is distinct from OLD.platform_channel_id
     )
  then
    v_miss := channel_missing(NEW);
    if array_length(v_miss,1) is not null then
      v_miss_old := channel_missing(OLD);
      -- ANTI-SANDERA (RANJAU 1): hanya tolak bila SEBELUMNYA lengkap.
      if array_length(v_miss_old,1) is null then
        raise exception 'Perubahan ini membuat channel belum lengkap sehingga produksi akan berhenti. Lengkapi dulu: %',
          array_to_string(v_miss, ', ')
          using errcode = 'check_violation';
      end if;
    end if;
  end if;

  return NEW;
end
$function$;

comment on function public.trg_channels_activation_gate() is
  'Gerbang kelengkapan channel, DUA pintu: (1) mengaktifkan channel tak-lengkap ⇒ tolak [20-Jun]; '
  '(2) perubahan TENANT yang menjatuhkan channel AKTIF dari lengkap→tak-lengkap ⇒ tolak [0218, 11-Sep]. '
  'Mesin (auth.uid() NULL) bebas — pencabutan koneksi YouTube wajib bisa menjatuhkan kelengkapan. '
  'Channel yang SUDAH tak lengkap tetap bisa disimpan (anti-sandera).';
