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
-- menutup satu pintu dari banyak (kartu suara · naskah · visual · layar admin · API · skrip).
--
-- TIGA HAL YANG PAGAR INI HARAM RUSAK — masing-masing diikat uji penjaga:
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
-- BEBAN — DIUKUR, bukan ditaksir (11-Sep, DB live, rata-rata 20 percobaan):
--   simpan tanpa pagar 58,4 ms · mesin memperbarui data 58,1 ms (**nol tambahan** — `auth.uid()`
--   gugur lebih dulu, `channel_missing` tak pernah dipanggil) · tenant menyimpan setelan 61,1 ms
--   (**+2,6 ms**, terjadi beberapa kali sehari). `channel_missing(OLD)` hanya dipanggil bila NEW
--   sudah tak lengkap (hubung-singkat `and`) ⇒ penyimpanan normal = SATU panggilan.
--
-- RANCANGAN PERTAMA DIBUANG (pertanyaan owner: "apa ini tidak over-engineering?"). Versi pertama
-- mendahului pemeriksaan dengan daftar 14 nama kolom penentu kelengkapan sebagai penghemat. Diukur:
-- penghematannya **di bawah derau** (±0,4 ms dari 58 ms), sementara daftar itu **RANJAU PEMBUSUKAN** —
-- begitu kelak ada syarat kelengkapan baru, daftarnya wajib diperbarui; sekali lupa, pagar ini bocor
-- SENYAP dan tak ada yang menjerit. Menukar 25 baris + risiko basi permanen dengan 2,6 ms = keliru.
-- Pintu 1 disalin PERSIS dari versi sebelumnya — nol perubahan perilaku aktivasi.

create or replace function public.trg_channels_activation_gate()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare v_miss text[];
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
     and auth.uid() is not null                       -- mesin bebas (RANJAU 2)
  then
    v_miss := channel_missing(NEW);
    -- ANTI-SANDERA (RANJAU 1): `channel_missing(OLD)` hanya diperiksa bila NEW sudah tak lengkap.
    if array_length(v_miss,1) is not null
       and array_length(channel_missing(OLD),1) is null then
      raise exception 'Perubahan ini membuat channel belum lengkap sehingga produksi akan berhenti. Lengkapi dulu: %',
        array_to_string(v_miss, ', ')
        using errcode = 'check_violation';
    end if;
  end if;

  return NEW;
end
$function$;

comment on function public.trg_channels_activation_gate() is
  'Gerbang kelengkapan channel, DUA pintu: (1) mengaktifkan channel tak-lengkap ⇒ tolak [20-Jun]; '
  '(2) perubahan TENANT yang menjatuhkan channel AKTIF dari lengkap→tak-lengkap ⇒ tolak [0218, 11-Sep]. '
  'Mesin (auth.uid() NULL) bebas — pencabutan koneksi YouTube wajib bisa menjatuhkan kelengkapan. '
  'Channel yang SUDAH tak lengkap tetap bisa disimpan (anti-sandera). Beban terukur: mesin nol, tenant +2,6 ms.';
