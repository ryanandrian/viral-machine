# Migrasi Kredensial PLATFORM Google: akun ryan → akun perusahaan (lumite)

> **Status:** PLAN — siap dieksekusi. Belum ada yang diubah saat dokumen ini dibuat.
> **Dibuat:** 2026-06-26 · **Sumber kebenaran tunggal** untuk migrasi OAuth platform.
> **Aturan kerja:** tidak boleh merusak fitur/arsitektur mesinviral.com; semua langkah Console di bawah
> sudah disesuaikan dengan UI Google **terbaru ("Google Auth Platform")**, dikonfirmasi dari dokumentasi
> resmi Google (lihat §9 Sumber). NOL asumsi liar.

---

## 0. Inti masalah (kenapa migrasi ini ada)

Yang kita pindahkan adalah **KREDENSIAL PLATFORM** — yaitu **satu** aplikasi OAuth Google milik
MesinViral yang dipakai **semua tenant** untuk dua pintu:

1. **"Daftar dengan Google"** (login/registrasi) — lewat Supabase Auth.
2. **"Hubungkan dengan Google"** (menyambung channel YouTube tenant) — lewat webhook kita.

Selama ini aplikasi OAuth itu menumpang di **akun Google pribadi `ryan.andrian.diputra@gmail.com`**
(project Google Cloud `viral-machine-490714`). ryan adalah **tenant** (pelanggan uji), bukan pemilik
platform — jadi memakai akunnya sebagai identitas platform itu **rancu** dan tidak layak jual:
nama "ryan.andrian.diputra@gmail.com" tampil ke setiap calon pelanggan di layar izin Google.

**Tujuan:** pindahkan aplikasi OAuth platform ke **akun perusahaan `lumite.biz.id@gmail.com`** (dikonfirmasi
Owner 2026-06-26), lalu **verifikasi ke Google** agar pelanggan asing melihat brand MesinViral (bukan nama
ryan) dan tidak melihat layar peringatan "unverified app". Semua langkah di §3 dilakukan saat login ke akun itu.

---

## 1. Seberapa besar dampaknya ke sistem? (KECIL — arsitektur tidak berubah)

| Yang berubah | Lokasi | Siapa | Catatan |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (2 nilai) | `.env` lokal **dan** VPS `/home/rad4vm/viral-machine-v2/.env` | **Claude** | restart `mv-webhook` + `mv-worker` |
| Client ID + Secret provider Google | **Supabase Dashboard** → Authentication → Providers → Google | **Owner** | untuk pintu "Daftar dengan Google" |
| **Perubahan kode** | — | — | **TIDAK ADA** (arsitektur OAuth Platform sudah dibangun; kunci dibaca dari `.env`) |

**Dampak data (wajib tahu):** mengganti aplikasi Google = **semua token YouTube lama jadi tidak berlaku**
(token terikat ke aplikasi penerbitnya). Jadi setelah migrasi:
- **ryan harus klik "Hubungkan dengan Google" sekali lagi** untuk menyambung ulang channel-nya.
- Tenant uji lain yang sudah connect (mis. kumala) juga reconnect.
- Ini **tidak** merusak produksi — hanya 1× reconnect per channel. (Saat ini di DB: ryan = tersambung valid;
  kumala = belum selesai connect, jadi tak terdampak.)

---

## 2. Apa yang aplikasi kita lakukan ke Google/YouTube (fakta dari kode — untuk justifikasi scope)

Diverifikasi langsung di `src/distribution/youtube_publisher.py` + `src/analytics/channel_analytics.py`:

| Operasi nyata | Untuk apa | Scope yang dibutuhkan |
|---|---|---|
| `videos().insert` | Upload video ke channel **milik tenant sendiri** | `youtube.upload` |
| `thumbnails().set` | Pasang thumbnail kustom video | `youtube.upload` |
| `channels().list(mine=true)` | Baca info & statistik channel sendiri | `youtube.readonly` |
| `youtubeAnalytics.reports` | Baca metrik performa video sendiri (views/retensi) | `yt-analytics.readonly` |
| `channels().update(brandingSettings)` | Update **deskripsi channel sendiri** — fitur opsional, non-kritis | `youtube` (kelola penuh) |

**Yang TIDAK pernah dilakukan** (dicek di seluruh `src/`): tidak ada auto-like, auto-subscribe,
auto-comment, atau rekayasa engagement. Mesin naskah bahkan **melarang** menyuruh penonton "like/subscribe".
→ Ini membuat aplikasi **patuh**: tenant menyambung channel sendiri, dengan izin, kita hanya upload + baca data.

> **Rekomendasi minimisasi scope (opsional, keputusan Owner):** scope terberat `youtube` (kelola penuh)
> **hanya** dipakai untuk update deskripsi channel (non-kritis). Jika dilepas, kita cukup minta **3 scope**
> (`youtube.upload` + `youtube.readonly` + `yt-analytics.readonly`) → justifikasi lebih sederhana, approval
> lebih mulus. Tradeoff: kehilangan auto-update deskripsi channel. **Belum dieksekusi** — lihat §6 (tugas B4).

---

## 3. PANDUAN LANGKAH-DEMI-LANGKAH untuk OWNER (di Google Cloud Console)

> Login ke Google pakai akun **`lumite.biz.id@gmail.com`**.
> UI Google sekarang bernama **"Google Auth Platform"** (bukan lagi halaman tunggal "OAuth consent screen").
> Menunya: **Branding · Audience · Clients · Data Access · Verification Center**.

### LANGKAH 1 — Buat Project baru
1. Buka **https://console.cloud.google.com** (pastikan pojok kiri atas akunnya `lumite.biz.id@gmail.com`).
2. Klik pemilih project (kiri atas) → **"New Project"**.
3. **Project name:** `MesinViral` (atau `mesinviral-prod`). **Create**.
4. Pastikan project baru itu yang aktif (terpilih di pojok kiri atas).

### LANGKAH 2 — Aktifkan API yang dipakai
1. Menu (☰) → **APIs & Services → Library**.
2. Cari & **Enable** ketiga ini satu per satu:
   - **YouTube Data API v3**
   - **YouTube Analytics API**
   - **YouTube Reporting API** (opsional, untuk laporan lanjutan)

### LANGKAH 3 — Konfigurasi "Branding" (identitas yang tampil ke pengguna)
1. Menu (☰) → **Google Auth Platform** → **Branding** (kalau diminta "Get started", isi wizard singkat).
2. Isi:
   - **App name:** `MesinViral`
   - **User support email:** `mesinviral@lumite.biz.id`
   - **App logo:** unggah logo MesinViral (PNG, 120×120 px; tidak melanggar merek). *(Claude bisa bantu siapkan file logo bila perlu.)*
   - **App home page:** `https://mesinviral.com`
   - **Privacy policy URL:** `https://mesinviral.com/privacy`  ← *(halaman ini akan Claude buat — §6 tugas B1)*
   - **Terms of service URL:** `https://mesinviral.com/terms`  ← *(Claude buat — §6 tugas B2)*
   - **Authorized domains:** `mesinviral.com`
   - **Developer contact email:** `mesinviral@lumite.biz.id`
3. **Save**.

> Catatan: halaman `/privacy` dan `/terms` **harus sudah live** sebelum submit verifikasi. Beri tahu Claude
> untuk menerbitkannya (§6) sebelum Anda mengisi URL ini — kalau URL belum live, Google menolak.

### LANGKAH 4 — "Audience" (tipe pengguna + test user)
1. **Google Auth Platform → Audience**.
2. **User type:** pilih **External** (karena pelanggan di luar organisasi).
3. **Test users:** klik **"Add users"** → tambahkan email akun yang akan Anda pakai untuk test e2e
   (mis. `kumala.rw22c@gmail.com` dan akun Anda sendiri). **Maks 100 test user.**
4. **Publishing status:** untuk sekarang biarkan **"Testing"** dulu (untuk test internal). Tombol
   **"Publish app"** (pindah ke *In production*) dipakai nanti — lihat §5 & §7.

> ⚠️ **Penting (fakta resmi Google):** di mode **Testing**, izin yang diberikan test user **kedaluwarsa
> dalam 7 hari** — termasuk refresh token. Artinya saat test internal, koneksi YouTube bisa minta
> re-consent tiap minggu. Ini **normal** dan hilang setelah app di-*publish* + terverifikasi.

### LANGKAH 5 — "Data Access" (pilih scope)
1. **Google Auth Platform → Data Access** → **"Add or remove scopes"**.
2. Tambahkan scope berikut (cari di kotak filter, centang):
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
   - `https://www.googleapis.com/auth/youtube` *(hanya bila fitur update-deskripsi-channel dipertahankan — lihat §2 rekomendasi minimisasi)*
3. **Update → Save**. Keempat (atau ketiga) scope ini tergolong **"Sensitive"** — butuh verifikasi, **tapi
   TIDAK butuh security assessment mahal** (itu hanya untuk scope "Restricted" seperti Gmail/Drive).

### LANGKAH 6 — Buat "Client" OAuth (Web application) → dapat Client ID + Secret
1. **Google Auth Platform → Clients** (atau **APIs & Services → Credentials**) → **"Create client"**.
2. **Application type:** **Web application**.
3. **Name:** `MesinViral Web`.
4. **Authorized JavaScript origins:** (boleh dikosongkan; tidak wajib untuk alur kita)
5. **Authorized redirect URIs** → **"Add URI"** dua kali, isi PERSIS (tanpa spasi/typo):
   ```
   https://atliatnjhysdibmfypul.supabase.co/auth/v1/callback
   https://mesinviral.com/api/youtube/oauth/callback
   ```
   - URI #1 = pintu **"Daftar dengan Google"** (Supabase Auth).
   - URI #2 = pintu **"Hubungkan dengan Google"** (webhook YouTube kita).
6. **Create**. Google menampilkan **Client ID** + **Client Secret** — **salin/Download JSON SEKARANG**
   (Secret tidak bisa dilihat lagi setelah ini).
7. **Kirim file/nilai itu ke Claude** (lewat `client_secret.json` di project, seperti sebelumnya — sudah
   di-gitignore). Claude akan tukar `.env` lokal + VPS (§6 tugas B5).

> Catatan resmi Google: perubahan redirect URI bisa butuh **5 menit s/d beberapa jam** untuk aktif.

### LANGKAH 7 — Verifikasi kepemilikan domain (Search Console)
1. Buka **https://search.google.com/search-console** dengan akun **`lumite.biz.id@gmail.com`** yang sama.
2. **Add property → Domain** → ketik `mesinviral.com`.
3. Google beri **TXT record** → tambahkan ke DNS domain `mesinviral.com` (di panel registrar/DNS Anda) → **Verify**.
   *(Bila butuh, Claude bantu jelaskan cara pasang TXT di penyedia DNS Anda.)*
4. Domain harus terverifikasi di akun yang **sama** dengan project Google Auth Platform.

### LANGKAH 8 — Update Supabase (pintu "Daftar dengan Google")
1. Buka **Supabase Dashboard** project `atliatnjhysdibmfypul` → **Authentication → Providers → Google**.
2. Ganti **Client ID** + **Client Secret** dengan yang BARU (dari Langkah 6).
3. **Save**. *(Tanpa ini, "Daftar dengan Google" akan error `redirect_uri_mismatch`.)*

### LANGKAH 9 — (untuk GO-LIVE publik) Submit verifikasi ke Google
> Lakukan **setelah** halaman `/privacy` & `/terms` live (§6) dan domain terverifikasi (Langkah 7).
1. **Google Auth Platform → Audience → "Publish app"** (Testing → **In production**).
2. **Google Auth Platform → Verification Center** → ikuti "Prepare for verification" / submit:
   - Pastikan Branding (§3) lengkap & URL live.
   - **Scope justification** — tempel teks dari §8 dokumen ini.
   - **Demo video** (unlisted di YouTube) — ikuti shot-list §8.
3. Submit. **Timeline resmi Google: hingga ~10 hari** setelah materi lengkap. Status dipantau di Verification Center.

---

## 4. Untuk TEST SEKARANG (real, bukan dummy) — tidak perlu tunggu verifikasi

Setelah Langkah 1–8 selesai (app masih mode **Testing**):
- Tambahkan akun test sebagai **Test user** (Langkah 4).
- Saat "Hubungkan dengan Google" memunculkan peringatan → **Advanced → Go to mesinviral.com (unsafe) → lanjut**.
- **Upload-nya 100% NYATA** ke channel YouTube asli. Yang belum "nyata" hanya layar peringatan
  (hilang setelah verifikasi). Token Testing kedaluwarsa 7 hari (re-consent mingguan) — wajar.

→ Verifikasi (§9, Langkah 9) berjalan **paralel** dan hanya diperlukan untuk **pelanggan publik**.

---

## 5. Mode Testing vs In production (ringkas, fakta resmi)

| | **Testing** | **In production (verified)** |
|---|---|---|
| Siapa bisa pakai | maks 100 test user terdaftar | siapa pun punya Akun Google |
| Layar peringatan "unverified" | **Ya** (bisa ditembus via Advanced) | **Tidak** |
| Refresh token | **kedaluwarsa 7 hari** | permanen |
| Cocok untuk | test internal Anda | jualan ke pelanggan |

---

## 6. TUGAS CLAUDE di mesinviral.com (yang harus saya lengkapi — semua memenuhi kebijakan Google/YouTube)

> Masalah saat ini: privasi hanya **tab JavaScript di `/about`** (tidak punya URL `/privacy` sendiri) dan
> isinya **belum** memenuhi syarat Google/YouTube. Tidak ada halaman **Terms of Service** sama sekali.
> Google mewajibkan URL privacy/terms yang **langsung bisa diakses** dan berisi disclosure tertentu.

| ID | Tugas | Status |
|---|---|---|
| **B1** | Buat halaman **`/privacy`** (URL sendiri, bukan tab) dengan konten **patuh Google API + YouTube API** (§7) — bilingual sesuai pola situs | ✅ **SELESAI** — LIVE `https://mesinviral.com/privacy` (HTTP 200); server component+metadata; link Limited Use+revoke+Google Privacy+YouTube ToS terverifikasi |
| **B2** | Buat halaman **`/terms`** (URL sendiri) — termasuk pernyataan tunduk pada **YouTube Terms of Service** | ✅ **SELESAI** — LIVE `https://mesinviral.com/terms` (HTTP 200); link YouTube ToS + Google Privacy terverifikasi |
| **B3** | Tambahkan link **Privacy** & **Terms** di footer marketing + arahkan tab lama `/about` "Privacy" ke `/privacy` | ✅ **SELESAI** — footer Legal → `/privacy`+`/terms` (Refund disembunyikan); tab Privacy lama di `/about` dihapus (anti-duplikat); commit `8c8b6cc` |
| **B4** | *(opsional, nunggu keputusan Owner §2)* Minimisasi scope: lepas `youtube` penuh → 3 scope | ⬜ belum (nunggu keputusan Owner) |
| **B5** | Tukar `GOOGLE_CLIENT_ID/SECRET` di `.env` lokal + VPS + restart `mv-webhook`/`mv-worker` | ⬜ nunggu Client baru dari Owner (Langkah 6) |

> ✅ **Catatan deploy B1–B3 (2026-06-27):** commit `8c8b6cc`, build VPS sukses, `mv-web` restart, kedua URL HTTP 200 dengan seluruh link wajib. **Halaman siap diisi di Branding (Langkah 3) & verifikasi (Langkah 9).**

> B1–B3 = halaman web baru (aman, **tidak** menyentuh fitur berjalan). B5 = setelah Owner kirim Client baru.

---

## 7. Syarat KONTEN privacy/terms agar TIDAK melanggar (fakta resmi Google/YouTube)

Halaman `/privacy` **wajib** memuat (akan Claude tulis di B1):
1. **Data apa yang diakses/dikumpulkan/disimpan/digunakan/dibagikan** — termasuk: email & nama akun,
   data channel YouTube yang dihubungkan, metrik performa, dan **kunci API tenant (terenkripsi)**.
2. **Link ke Google Privacy Policy** → `https://policies.google.com/privacy` *(wajib YouTube API).*
3. **Link ke YouTube Terms of Service** → `https://www.youtube.com/t/terms` *(wajib YouTube API).*
4. **Cara mencabut akses (revoke):** arahkan ke halaman keamanan Google
   `https://myaccount.google.com/permissions` + lewat MesinViral (tombol Hapus koneksi).
5. **Penghapusan data:** kami **menghapus Authorized Data dalam 7 hari** setelah pencabutan akses
   *(wajib YouTube API).*
6. **Kepatuhan Google API Services User Data Policy** termasuk **Limited Use** (data Google hanya untuk
   menyediakan/mengembangkan fitur yang dilihat pengguna; tidak dijual; tidak untuk iklan).
7. **Pernyataan enkripsi** (kunci & token disimpan terenkripsi Fernet, tak pernah masuk log).

Halaman `/terms` **wajib** memuat:
- Pengguna setuju **tunduk pada YouTube Terms of Service** saat memakai MesinViral *(wajib YouTube API).*
- Link ke Google Privacy Policy.

---

## 8. Materi submit verifikasi (siap pakai)

### 8a. Justifikasi scope (tempel di Verification Center)
- **youtube.upload** — "Used to upload videos that the user creates within MesinViral to the user's own
  YouTube channel, and to set the custom thumbnail. This is the core function of the product. A narrower
  scope does not allow uploading."
- **youtube.readonly** — "Used to read the user's own channel info and statistics to confirm the connected
  channel and display basic stats in the dashboard."
- **yt-analytics.readonly** — "Used to fetch the user's own video performance metrics (views, retention,
  likes, comments) to power per-channel self-learning insights. This is the narrowest scope for analytics."
- **youtube** *(hanya bila dipertahankan)* — "Used solely to update the user's own channel description
  (brandingSettings) as an optional branding convenience."

### 8b. Shot-list video demo (unlisted di YouTube)
1. Tampilkan halaman `https://mesinviral.com` (homepage) — sebutkan nama app **MesinViral**.
2. Tampilkan tombol **"Hubungkan dengan Google"** → klik → tampilkan layar **consent Google**
   (perlihatkan **Client ID** cocok dengan yang diverifikasi).
3. Setujui izin → kembali ke app.
4. Tunjukkan **penggunaan tiap scope**: produksi video → **upload** ke channel; tampilkan **statistik**
   (analytics); (bila ada) tampilkan **deskripsi channel** ter-update.
5. Tunjukkan cara **revoke** (tombol Hapus koneksi + link ke Google permissions).

---

## 9. URUTAN EKSEKUSI (siapa, kapan)

1. **Owner:** konfirmasi ejaan akun Gmail (§0).
2. **Claude:** kerjakan **B1–B3** (halaman `/privacy` + `/terms` + footer) → deploy → URL live.
3. **Owner:** Console **Langkah 1–7** (project, API, Branding pakai URL yang sudah live, Audience+test user,
   Data Access, Client+redirect, domain verification).
4. **Owner:** kirim **Client ID/Secret baru** → **Claude:** B5 (tukar `.env` lokal+VPS, restart, swap selesai).
5. **Owner:** **Langkah 8** (Supabase Dashboard Google provider).
6. **ryan + tenant test:** reconnect YouTube (1× klik).
7. **Owner + Claude:** **TEST e2e real** (mode Testing, tembus warning) — validasi mesin penuh.
8. **Paralel (go-live publik):** **Langkah 9** submit verifikasi (justifikasi §8a + video §8b) → ≤10 hari.

---

## 10. Pernyataan kepatuhan (ringkas)

✅ Scope YouTube = **Sensitive**, bukan Restricted → **tanpa** security assessment (CASA) berbayar.
✅ Aplikasi hanya upload ke channel milik tenant + baca data tenant sendiri; **tidak ada** rekayasa engagement.
✅ Semua syarat administratif (domain, privacy, terms, consent screen, justifikasi, video demo) **bisa dipenuhi**.
✅ Privacy/terms akan memuat seluruh disclosure & link wajib (§7) → **tidak melanggar** kebijakan.
⚠️ Catatan bisnis (bukan penghalang verifikasi): kebijakan **konten "inauthentic/mass-produced"** YouTube
   memengaruhi **monetisasi channel tenant** — alasan kita punya sistem QC/kualitas viral.

---

## 11. Sumber resmi Google (verifikasi, bukan ingatan)
- Sensitive scope verification — https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification
- Restricted scope (perbandingan CASA) — https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- Konfigurasi OAuth consent (Google Auth Platform) — https://developers.google.com/workspace/guides/configure-oauth-consent
- Buat OAuth Client — https://support.google.com/cloud/answer/6158849
- Publishing status / Audience — https://support.google.com/cloud/answer/15549945
- YouTube API Developer Policies (disclosure wajib) — https://developers.google.com/youtube/terms/developer-policies
- OAuth App Verification Help — https://support.google.com/cloud/answer/13463073
