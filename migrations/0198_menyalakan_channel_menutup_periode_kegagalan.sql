-- 0198 — MENYALAKAN CHANNEL WAJIB MENUTUP PERIODE KEGAGALAN (+ jejak waktu perubahan)
-- SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8k butir 2 & 3.
--
-- ═══ BUG (terukur 14-Agu 2026, dari keluhan tenant yang dilaporkan owner) ═══
-- Migrasi 0197 (§8c) menetapkan aturan: **SETIAP jalur yang membuka kembali produksi wajib mencatat
-- titik pemulihan**, karena tanpa itu kegagalan hari sebelumnya masih terhitung dan siklus penjadwal
-- berikutnya langsung mengerem lagi. Aturan itu dipasang pada jalur pelepas rem — tapi ada satu jalur
-- yang membuka produksi dan TIDAK PERNAH ikut: **saklar aktif/nonaktif channel.**
--
-- Akibatnya terukur pada dua channel tenant BERBAYAR (tenant yang sama, dua hari berurutan):
-- BISIK NUSANTARA dan Thetangga Property dibanjiri kabar gagal (30 & 23 kegagalan) sampai tenantnya
-- MEMATIKAN SENDIRI channelnya. Keduanya kini menyimpan hitungan kegagalan **12**. Begitu tenant
-- menyalakannya kembali — bahkan besok, bahkan setelah jatah penyedianya pulih — mesin akan
-- mengeremnya **seketika, tanpa satu percobaan produksi pun**, lalu mengirim kabar "produksi
-- dihentikan". Tenant sudah dirugikan sekali; ini merugikannya kedua kali.
--
-- ═══ CACAT KEDUA yang ikut ditutup: JAM PERUBAHAN TIDAK TEREKAM ═══
-- Saklar menulis `is_active` saja. Tak ada pencatat otomatis, sehingga `updated_at` BASI: catatan
-- waktu BISIK NUSANTARA masih tertanggal 13-Agu padahal banjirnya 14-Agu. Diagnosa insiden jadi
-- sepenuhnya bergantung pada ingatan owner/tenant — dan itu sudah terjadi: satu-satunya sebab kami
-- tahu tenant mematikan channelnya adalah karena owner memberitahukannya.
--
-- ═══ KENAPA TRIGGER, BUKAN 2 BARIS DI LAYAR ═══
-- Ketetapan owner 14-Agu: *"pastikan setiap perbaikan sedapat mungkin bersifat GENERIK, karena AI
-- model dan AI vendor akan terus bertambah."* Prinsip yang sama berlaku untuk JALUR: menulisnya di
-- layar hanya menutup layar yang ada HARI INI. Jalur admin, API, skrip pemulihan, dan layar yang
-- belum dibuat akan melewatinya — persis cara cacat ini lahir (0197 menutup 3 jalur, melewatkan 1).
-- Trigger menutup SETIAP jalur, termasuk yang belum ada, tanpa satu baris kode aplikasi.
--
-- ═══ KENAPA INI TIDAK MELUMPUHKAN REM (dan bukan pintu belakang) ═══
-- Trigger ini TIDAK menyentuh `production_paused`. Channel yang sedang DIREM tetap direm walau
-- dimatikan-dinyalakan — penjadwal melewatinya karena remnya masih menyala, dan tenant tetap harus
-- menekan "Pulihkan produksi". Yang ditutup hanyalah PERIODE HITUNGAN, sehingga channel yang remnya
-- tidak menyala tidak dihukum atas kegagalan dari periode yang sudah ia tinggalkan.
-- Keputusan owner [B25] ("pemulihan = keputusan TENANT") utuh.
--
-- ═══ TIDAK BERBENTURAN dengan trigger yang sudah ada ═══
-- `channels_rem_readonly` (0195, BEFORE UPDATE) menolak pemanggil ber-sesi mengubah
-- `production_paused` / `production_paused_at` / `production_paused_reason`. Trigger ini tidak
-- menyentuh satu pun dari ketiganya. Namanya juga membuatnya berjalan LEBIH DULU secara alfabetis
-- (`channels_catat_...` < `channels_rem_readonly`), jadi hasilnya diperiksa penjaga itu, bukan
-- sebaliknya — dan lolos, karena kolom yang disentuh berbeda.
--
-- ═══ NOL KOLOM BARU, NOL DATA TENANT DISENTUH ═══
-- Memakai `production_resumed_at` (0197) dan `updated_at` yang sudah ada. Baris tenant tidak diubah
-- oleh migrasi ini — ia hanya mengubah apa yang terjadi pada perubahan BERIKUTNYA. Karena itu dua
-- channel yang menyimpan hitungan 12 sembuh SENDIRI saat tenantnya menyalakannya, tanpa kami
-- menyentuh datanya.

CREATE OR REPLACE FUNCTION public.trg_channels_catat_pengaktifan()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
begin
  -- (1) Channel dinyalakan (mati/kosong -> hidup) = jalur yang MEMBUKA produksi ⇒ periode kegagalan
  --     lama ditutup, sesuai aturan 0197. Syarat sengaja ketat: hanya pada PERUBAHAN, hanya ke arah
  --     menyala. Update lain (niche, jadwal, suara, rem) tidak menyentuh titik pemulihan.
  if NEW.is_active IS TRUE and coalesce(OLD.is_active, false) IS FALSE then
    NEW.production_resumed_at := now();
  end if;

  -- (2) Jejak waktu, tanpa kecuali. Sebelum ini `updated_at` hanya terisi bila pemanggil ingat
  --     menuliskannya — dan saklar aktif tidak pernah ingat, sehingga jam kejadian hilang justru
  --     pada perubahan yang paling penting untuk diagnosa insiden.
  NEW.updated_at := now();

  return NEW;
end
$function$;

COMMENT ON FUNCTION public.trg_channels_catat_pengaktifan() IS
  'Menyalakan channel = jalur yang membuka produksi ⇒ tutup periode hitungan kegagalan '
  '(production_resumed_at), aturan migrasi 0197. Berlaku untuk SETIAP jalur — layar tenant, admin, '
  'API, skrip, dan jalur yang belum ada — karena dipasang di database, bukan di aplikasi. TIDAK '
  'menyentuh production_paused: channel yang direm tetap direm, pemulihan tetap keputusan tenant '
  '([B25]). Juga mencatat updated_at pada setiap perubahan (dulu basi: saklar aktif tak menuliskannya).';

DROP TRIGGER IF EXISTS channels_catat_pengaktifan ON channels;
CREATE TRIGGER channels_catat_pengaktifan
  BEFORE UPDATE ON channels
  FOR EACH ROW
  EXECUTE FUNCTION public.trg_channels_catat_pengaktifan();
