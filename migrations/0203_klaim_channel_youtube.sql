-- 0203 — KLAIM CHANNEL YOUTUBE: kuncian anti masa-coba-berulang.
-- Rencana, arsitektur, progress, dan bukti wajib: CHANNEL_LOCK_ACTIVATION_PLAN.md §7.
--
-- PERSOALAN (ketokan owner 2026-08-20): tenant masa coba BOLEH mendaftar ulang — itu haknya.
-- Yang tidak boleh: membawa channel YouTube yang sudah terdaftar di akun lain, sehingga masa coba
-- bisa diputar tanpa batas dengan email baru. Kuncinya di INTEGRASI, bukan di pendaftaran.
--
-- KENAPA TABEL BARU, bukan indeks unik global di tabel yang sudah ada:
--   `disconnect()` MENGHAPUS baris `tenant_youtube_accounts` (youtube_oauth.py:304). Kuncian yang
--   menumpang di sana ikut terhapus ⇒ tenant tinggal cabut → daftar akun baru → sambung lagi.
--
-- Terukur sebelum migrasi (2026-08-20): 21 koneksi · 15 ber-identitas · 6 tanpa identitas (dilewati)
--   · 0 channel dipakai >1 tenant.

begin;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 1) GAGAL BERISIK DULU, sebelum menulis apa pun.
--    Kalau satu channel ternyata dipakai >1 tenant, migrasi HARUS mati. Memilih pemenang diam-diam
--    = keputusan produk (siapa kehilangan channelnya) yang tak boleh diambil oleh migrasi.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
do $$
declare n int;
begin
  select count(*) into n from (
    select yt_channel_id
      from tenant_youtube_accounts
     where yt_channel_id is not null and yt_channel_id <> ''
     group by yt_channel_id
    having count(distinct tenant_id) > 1
  ) x;
  if n > 0 then
    raise exception
      'MIGRASI DIBATALKAN: % channel YouTube dipakai >1 tenant. Selesaikan kepemilikannya lewat admin dulu; migrasi tidak boleh memilih pemenang.', n;
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 2) Tabel klaim. Kunci primer = identitas channel ⇒ kuncian ditegakkan DATABASE, bukan baris `if`.
--    Baris `if` bisa dilupakan sesi berikutnya DAN kalah pada perlombaan (dua akun menyambung di
--    detik yang sama). Kunci primer tidak bisa keduanya.
--
--    ⚠️ SENGAJA TANPA FOREIGN KEY & TANPA CASCADE — JANGAN "DIRAPIKAN".
--    Seluruh arsitektur kredensial di sini dirancang bersih-bersih saat dihapus (`disconnect()`
--    menghapus baris pool; `channel_credentials` dulu ON DELETE CASCADE ke `channels.id`).
--    Tabel INI wajib jadi pengecualian: klaim harus bertahan walau koneksi dicabut, channel dihapus,
--    bahkan tenant dihapus. Menambahkan FK/cascade ke tabel ini = menghidupkan kembali lubangnya.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
create table if not exists youtube_channel_claims (
  yt_channel_id    text        primary key,
  tenant_id        text        not null,
  yt_channel_title text,
  claimed_at       timestamptz not null default now()
);

comment on table youtube_channel_claims is
  'Klaim PERMANEN channel YouTube -> satu akun MesinViral. SENGAJA tanpa FK/cascade (bertahan walau koneksi dicabut / channel dihapus / tenant dihapus) - lihat CHANNEL_LOCK_ACTIVATION_PLAN.md §7. Pelepasan HANYA lewat admin.';

create index if not exists ix_ycc_tenant on youtube_channel_claims (tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 3) RLS: tulis & baca HANYA lewat service_role (pola `tenant_youtube_accounts`, migr 0091).
--    NOL policy = nol akses bagi anon/authenticated; service_role melewati RLS.
--    Tenant sengaja TIDAK diberi SELECT: klaim bukan datanya, dan bocornya memberi tahu
--    channel siapa yang sudah terpakai. Ini menutup kelas CELAH A & B (PAYMENT §10e-3):
--    aturan tabel yang hanya memeriksa `tenant_id` pernah membuat tenant menulis atas nama sendiri
--    untuk hal yang bukan haknya.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
alter table youtube_channel_claims enable row level security;
revoke all on table youtube_channel_claims from anon, authenticated;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 4) ISI-MUNDUR — pemilik PERTAMA yang menang (koneksi tertua). Idempoten (aman diulang), dan
--    WAJIB dijalankan ULANG sesudah BE deploy: koneksi yang terjadi di sela antara migrasi dan
--    penjaga-hidup tidak punya klaim (temuan evaluasi final §7c-2).
--    Koneksi tanpa identitas dilewati — tak ada yang bisa diklaim darinya.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
insert into youtube_channel_claims (yt_channel_id, tenant_id, yt_channel_title, claimed_at)
select distinct on (yt_channel_id)
       yt_channel_id, tenant_id, yt_channel_title, coalesce(created_at, now())
  from tenant_youtube_accounts
 where yt_channel_id is not null and yt_channel_id <> ''
 order by yt_channel_id, created_at asc
    on conflict (yt_channel_id) do nothing;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 5) SAKLAR INDUK (temuan evaluasi final §7c-3) — mandat owner: tiap gerbang bisa dimatikan
--    SEKETIKA tanpa deploy. Tanpa ini, penjaga yang salah menolak di produksi hanya bisa
--    dipadamkan lewat deploy ulang. Pola & penamaan mengikuti `test_gate_enabled`.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
insert into app_config (key, value, description) values (
  'channel_claim_enabled', 1,
  'SAKLAR INDUK kuncian klaim channel YouTube. 1 = channel yang sudah terdaftar di akun MesinViral lain TIDAK bisa disambungkan ke akun lain (menutup masa-coba-berulang). 0 = kuncian dimatikan total, perilaku kembali seperti sebelum kuncian dipasang (jaring pengaman: bisa dimatikan seketika tanpa deploy).'
) on conflict (key) do nothing;

commit;
