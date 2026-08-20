# Channel Lock Activation — Arsitektur & Plan vs Realisasi

> ✅🔒 **CLOSED sbg backlog aktif (2026-07-01).** Fase 0-9 = SELESAI+deployed (`06c5e90`/`bb80162`). Satu-satunya sisa (acceptance tenant-baru-dari-nol e2e = butuh browser owner) sudah masuk **[`SISA_KERJA_GO_LIVE.md`](SISA_KERJA_GO_LIVE.md)** (A5). **Dokumen ini = SPEC arsitektur kredensial/lock (rujukan), bukan backlog.**

> Status: **ARSITEKTUR DISETUJUI owner 2026-06-24** (A/B/C/D + trend-radar=platform + 2-page + pool).
> Dokumen ini = acuan resmi tunggal.
> **🔄 AUDIT REKONSILIASI 2026-07-01 (verified DB+kode):** model POOL = **SUDAH TERIMPLEMENTASI** — `tenant_ai_accounts` + `tenant_youtube_accounts` ADA; fosil `tenant_credentials`/`channel_credentials` = TIADA; `channels.{llm,tts,visual}_account_id` ADA; lock `channel_missing` dipakai (`readiness.py`); channel-detail redesign (Overview/Kesiapan/Jadwal) LIVE. Banner "DEVIASI §3" + "SEDANG DIKERJAKAN" (§391) = **BASI**. Sisa kecil bila ada → daftar master `PROGRESS.md` blok AUDIT 2026-07-01.

---

# ⭐ KEPUTUSAN FINAL — TERKUNCI 2026-06-25 (COMPACTION-PROOF; JANGAN dibuka ulang, expert sudah putuskan)

> Owner serahkan keputusan ke Claude (expert) + minta SEGERA dibereskan & terdokumentasi agar tak mentah lagi
> pasca-compaction. Ini ringkas-mutlak; detail di §0.4/§0.5/§2. **Bangun PERSIS ini.**

**1. Dua halaman:** Credential (`/integrations`, tenant-wide) + Channel Setting (`/channels/[id]`, per-channel).

**2. AI = model VENDOR / key-group (FINAL):**
- Kredensial di-key per **VENDOR (`key_group`)**, BUKAN provider mentah. **`openai` + `openai_tts` = vendor `openai`**
  (satu kunci OpenAI `sk-…` melayani GPT + image + TTS — **FAKTA**: endpoint beda, **kunci SAMA**; bukti `api_key_vault.py:34-35`
  validasi identik). Vendor lain: `anthropic`, `elevenlabs`, `replicate`. `edge_tts` = gratis (tanpa kunci).
- Tenant boleh **>1 kunci per vendor** (label, mis. "OpenAI Utama/Cadangan"). **Tenant isi kunci OpenAI SEKALI** → otomatis dipakai semua elemen yg dilayani vendor itu (tak dobel).
- **Credential UI per ELEMEN** (Penulis Naskah/LLM · Pengisi Suara/TTS · Pembuat Visual): tiap elemen tampilkan penyedia
  yg melayaninya (katalog `ai_models.component`) + kunci vendornya + tombol **"Tambah kunci"** (banyak). **Nilai kunci TAMPIL APA ADANYA** (decrypt, `type=text`, TIDAK di-mask).
- **Channel Setting** per elemen: penyedia → model → **akun** (auto bila 1 akun vendor; pilih bila >1).
- **Replicate = OPSI** (aktifkan model image-nya di katalog agar muncul). Katalog-driven (tambah provider/model = nol koding).

**3. YouTube = OAuth PLATFORM (FINAL — buang BYO-CC):**
- Platform punya **1 Google OAuth app** (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` di `.env` PLATFORM). Tenant cukup klik
  **"Hubungkan dengan Google"** — **TANPA** Redirect URI / Client ID / Secret (tenant tak pegang hal teknis).
- Kumpulan koneksi (1..N akun Google) di Credential; channel pilih **koneksi + channel tujuan**. 1 koneksi = publish + analitik.
- Prasyarat owner (eksternal, di luar kode): daftar OAuth app + **verifikasi Google** (scope upload YouTube; pra-verifikasi ~100 akun uji). ryan **connect ulang** via app platform.

**4. DB target:** `ai_providers.key_group` · `tenant_ai_accounts(tenant_id, key_group, label, key_enc, status, validated_at)` =
banyak baris/vendor · `channels.{llm,tts,visual}_account_id` + `youtube_account_id` · `tenant_youtube_accounts` (token OAuth platform).
**Drop fosil:** `channel_credentials`, `tenant_credentials`, `channels.{llm,tts,visual}_key_enc`, `channels.token_path`.

**5. Sisanya (tetap):** Lock di DB (`channel_missing`, identik FE/worker/trigger) · validate-early (🟢=terverifikasi bekerja) ·
**Kartu Kesiapan & Aktivasi di tab OVERVIEW** (Aktif enabled saat semua 🟢) · indikator 🔴/🟢 + `<ChannelStatusBadge>` ·
onboarding = **pengarah** (lengkapi Credential→Channel; onboarded = channel pertama semua 🟢) · Telegram per-tenant (validate-early) ·
trend-radar = `YOUTUBE_PLATFORM_API_KEY` platform · `.env` = HANYA platform · **nol dual-state** (acceptance = TENANT BARU dari nol).

**Urutan build:** DB (key_group + tenant_ai_accounts vendor + channels account cols + youtube OAuth platform) → BE (resolve per akun + readback + OAuth platform) → FE (Credential per-elemen multi-key + tampil-apa-adanya + YouTube "Hubungkan dengan Google"; Channel pemilih akun) → gate → validasi tenant-baru → drop fosil.

---

# §0. ARSITEKTUR CHANNEL LOCK ACTIVATION

## 0.1 Prinsip inti
- **Lock = di DATABASE** (trigger `channels_activation_gate` → `channel_missing`). Tak bisa di-bypass jalur mana pun.
- **2 halaman saja** (UX): **Page Credential** (tenant-wide) + **Page Channel Setting** (per-channel).
- **Kredensial = model "kumpulan" (pool)**, ditugaskan per-channel. Konsisten untuk AI & YouTube.
- **`.env` = HANYA platform.** Kredensial tenant **sepenuhnya di DB**. Nol fosil.
- **Indikator 🔴/🟢** di FE; tombol Aktifkan hidup hanya saat semua 🟢. Tiap indikator link ke konfigurasinya.

## 0.2 Dua jenis kredensial (sifat beda)
| Jenis | Untuk | Sifat | Kategori |
|---|---|---|---|
| **Kunci AI** (LLM/TTS/Visual) | bayar penyedia AI (BYOK) | 1 kunci/penyedia dipakai banyak channel | per-TENANT (pool) |
| **Koneksi YouTube** (OAuth) | publish + analitik akun sendiri | bisa banyak akun Google per tenant | per-TENANT (pool), ditugaskan per-channel |
| **`YOUTUBE_PLATFORM_API_KEY`** | trend-radar (baca tren publik) | global, bukan milik tenant | PLATFORM (.env) |

## 0.3 Keputusan trend-radar = PLATFORM account (analisis kuota)
Tren bersifat **global per-niche**, di-cache (`trend_cache`, key `niche|geo|source`). Pemakaian API =
**O(niche × region ÷ TTL), KONSTAN vs jumlah tenant** (terbukti `trend_refresher.py:5`; produce hanya baca cache).
→ Pakai **API-key platform** (`.env`). Per-tenant = duplikasi masif + friksi onboarding (salah).
**Kuota resmi Google (granular, dicek 2026-06 dari developers.google.com):** 10.000 unit/hari (umum) +
**bucket TERPISAH 100 `search.list`/hari** + 100 `videos.insert`/hari. Trend-radar/scan = 1 `search.list`
(BUCKET PENGIKAT) + 1 `videos.list` (~1 unit). → batas ≈ **100 scan (niche×region)/hari**; `videos.list`
nyaris tak menyentuh 10k. Karena O(niche×region÷TTL) konstan vs tenant → platform aman.
Scale lever: naikkan TTL → frugal active-only (sudah) → **ajukan "Audit & Quota Extension Form" ke Google**
(granular system mempermudah kenaikan `search.list`) → shard multi-project.
Beban milik-tenant (publish/analitik) pakai **OAuth tenant** → masuk kuota project tenant (terdistribusi alami).

## 0.4 Model kredensial AI (FINAL — hasil diskusi owner 2026-06-25; SAMA POLA dgn YouTube)
- **Page Credential → "Kumpulan Akun AI":** tenant tempel kunci API **per penyedia**. Daftar penyedia **otomatis
  bertambah** (katalog `ai_providers`/`ai_models`, nol kode tiap tambah provider/model). Penyedia gratis (Edge) tanpa kunci.
  **BOLEH >1 AKUN per penyedia** (mis. "OpenAI Utama", "OpenAI Cadangan") — tiap akun punya **label**. (BUKAN "opsi lanjutan" — ini bagian inti.)
- **Page Channel Setting:** tiap elemen pilih **penyedia → model → AKUN**. Kalau tenant cuma punya **1 akun** penyedia
  itu → **otomatis terpakai** (tak perlu pilih). Kalau **>1** → tenant **pilih akun**. Mendukung **sama/beda antar channel**
  (channel A: OpenAI/gpt-4o; channel B: Anthropic/claude) — bahkan **kunci berbeda untuk penyedia sama** (pilih akun beda).
- **🔓 KREDENSIAL TAMPIL APA ADANYA (kesepakatan owner — WAJIB):** nilai kunci/secret disimpan terenkripsi (Fernet)
  TAPI **bisa dibaca-balik & ditampilkan TANPA mask** (`type=text`, field ter-prefill nilai decrypt) ke tenant pemilik —
  agar mudah diperiksa & copy. **BUKAN write-only.** Berlaku kunci AI + Client ID/Secret YouTube + Telegram chat_id.
- **Penjelasan elemen ke tenant:**
  - **LLM (Penulis Naskah):** AI penulis cerita/hook/narasi. Makin pintar model → naskah makin bagus.
  - **TTS (Pengisi Suara):** Text-to-Speech, ubah naskah jadi suara narator (pilih penyedia + karakter suara).
  - **Image & Video Generator (Pembuat Visual):** buat gambar/video tiap adegan. Video-gen kini khusus preset 8 detik;
    gambar untuk semua durasi. (Penyedia bertambah seiring waktu, mis. Seedance/Veo3.)

## 0.5 Model kredensial YouTube (dukung 3 skenario tenant)
- **Page Credential → "Koneksi YouTube":** tenant connect **1..N akun Google** (kumpulan koneksi).
- **Page Channel Setting:** tiap channel pilih **koneksi mana** + **YouTube channel tujuan**.
- Menutup: (1) 1 akun→banyak channel, (2) banyak akun→1 channel each, (3) banyak akun→banyak channel.
- 1 koneksi melayani **publish + analitik** sekaligus.

## 0.6 Pembersihan `.env` (platform-only)
Buang dari `.env` (lokal+VPS) — tenant→DB / fosil (audit terverifikasi):
- Tenant nyasar: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `REPLICATE_API_TOKEN`, `TELEGRAM_CHAT_ID`.
- Fosil: `R2_*` (storage sudah S3).
- Kode: buang HANYA **fallback** `or os.getenv("REPLICATE_API_TOKEN")` di `ai_image.py:97` → jadi
  `visual_api_key` saja (gagal-jujur bila kosong). ⚠️ **Replicate TETAP penyedia OPSI** (image, & video nanti) —
  bukan dibuang; tenant isi kunci Replicate sendiri (BYOK) di Page Credential. Runtime tetap set token SDK
  Replicate dari kunci tenant (`ai_image.py:353`), bukan dari env. (OPENAI/ANTHROPIC env juga BUKAN penghapusan
  penyedia — hanya token tenant nyasar; penyedia tetap di katalog.)
- TETAP (platform): `ENCRYPTION_KEY`, `SUPABASE_*`, `S3_*`, `MV_INTERNAL_SECRET`, `OAUTH_STATE_SECRET`,
  `YOUTUBE_OAUTH_REDIRECT_URI`, `APP_BASE_URL`, `YOUTUBE_PLATFORM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `SMTP_*`,
  `MIDTRANS_*`, `PRODUCER_MAX_RENDER`.

## 0.7 Prinsip VALIDASI SEDINI MUNGKIN (validate-early) — owner 2026-06-24
Apa pun yang **bisa** divalidasi saat dikonfigurasi, **divalidasi saat itu** (di Page Credential / Channel Setting).
Indikator **🟢 = TERVERIFIKASI BEKERJA**, bukan sekadar "terisi". Hanya yang **tak bisa** dipra-validasi
(kredit/kuota habis, hasil QC konten) yang baru ketahuan saat produksi (fail jujur).
- Mekanisme: saat tenant simpan kredensial → BE **uji nyata** → simpan **status (valid/invalid) + validated_at**.
  Gerbang DB (`channel_missing`) cek **status=valid**, bukan cuma "ada". (Pool kunci AI & koneksi punya kolom
  `status`/`validated_at`.)

| Syarat | Bisa divalidasi config-time? | Cara validasi |
|---|---|---|
| Kunci AI (LLM/TTS/Visual) | ✅ YA | test-call murah ke penyedia (mis. list models / akun) → kunci valid? |
| Koneksi YouTube | ✅ YA | OAuth selesai + `channels.list(mine=true)` → akun & akses ok? |
| **Telegram chat_id** | ✅ YA | bot kirim **pesan tes** → terkirim? (sekaligus bukti tenant sudah Start bot + id benar) |
| Niche | ✅ YA | ada di katalog |
| Penyedia + model (tiap elemen) | ✅ YA | ada + aktif di katalog |
| Voice | ✅ YA | ada + aktif di katalog (+ preview) |
| Jadwal posting | ✅ YA | format jam valid (HH:MM) |
| Kredit/kuota penyedia cukup | ❌ TIDAK | hanya saat produksi (kunci valid tapi saldo habis) |
| Kualitas konten (QC) | ❌ TIDAK | hanya saat produksi |

---

# §0.8 PETA KONKRET (current-state + target) — agar sesi lain eksekusi TANPA riset ulang

## A. KONDISI SEKARANG (live 2026-06-24) = titik mulai
**DB (Supabase v2 ref `atliatnjhysdibmfypul`; migrasi terakhir 0090; BARU mulai 0091):**
- `channels` kolom config AI per-channel SUDAH ada: `llm_library, llm_model, tts_provider, tts_model, voice_key,
  visual_mode, image_quality`. Kunci INLINE: `llm_key_enc, tts_key_enc, visual_key_enc` (Fernet) ⚠️ akan PINDAH ke pool.
  `is_active` default false; `platform_channel_id` = target YT channel.
- Gate DB LIVE (migr 0089): `channel_missing(ch channels)→text[]` · RPC `channel_readiness(p_channel_id)` (FE, filter
  auth.uid) · RPC `channel_missing_by_id(p_channel_id)` (worker) · trigger `channels_activation_gate` BEFORE INSERT/UPDATE.
- OAuth YouTube di DUA tempat: `channel_credentials`(per-channel) + `tenant_credentials`(tenant) → jadi pool.
- Telegram: `tenant_configs.telegram_chat_id` + `telegram_enabled`.
- Katalog: `ai_providers`(provider_key, display_name, adapter, **auth_type**) · `ai_models`(model_key, provider_key,
  **component** llm/tts/image/video, model_id, is_active) · `voice_catalog`(voice_key, provider_key, is_active) · `tts_profiles`.

**BE (`/home/rad/viral-machine/src`):**
- `config/tenant_config.py` — `load_tenant_config(tenant_id, channel_id, niche)`; `_apply_channel_overlay` baca
  `channels.*_key_enc` via `_set_channel_key` (→ ganti: baca pool `tenant_ai_accounts`).
- `orchestrator/readiness.py` — `channel_readiness(sb, ch)` panggil RPC `channel_missing_by_id`.
- `orchestrator/producer.py:~358` — skip channel non-ready.
- `distribution/youtube_publisher.py` + `analytics/channel_analytics.py` — OAuth via
  `utils/tenant_credentials.load_google_credentials(tenant_id, channel_id)` (→ ganti: resolve dari pool + target).
- `utils/api_key_vault.py` — `set_channel_key/get_channel_keys` (→ ganti: pool). `_sb()` service_role + `crypto.encrypt/decrypt`.
- `billing/webhook_app.py` (service mv-webhook :8088) — route `/api/channels/key`, `/api/channels/keys/get`,
  `/api/youtube/oauth/*`. Auth header `x-internal-secret`=`MV_INTERNAL_SECRET`.
- `providers/visual/ai_image.py:97` fallback `os.getenv("REPLICATE_API_TOKEN")` (buang; Replicate tetap opsi);
  `:353` set `os.environ["REPLICATE_API_TOKEN"]=self.api_key` (tetap).
- `intelligence/trend_radar.py` — `YOUTUBE_PLATFORM_API_KEY` (platform, JANGAN sentuh).
- `utils/telegram_notifier.py:28` bot_token env (platform, tetap); `:29` `system_chat_id` fallback (buang).

**FE (`/home/rad/viral-machine/apps/web/src`):**
- `components/app-shell.tsx` — sidebar nav (integrations, channels, …).
- `app/(app)/integrations/page.tsx` — **Page Credential (KANDIDAT)**; kini YouTube(tenant-OAuth)+Telegram; TAMBAH section Kunci AI + pool koneksi YouTube.
- `app/(app)/channels/[id]/page.tsx` — **Channel Setting**; panel "Produksi AI" (penyedia→model→kunci inline), `pausePlay()` gate, `load()` RPC `channel_readiness`, `effectiveStatus()`.
- `app/(app)/channels/page.tsx` — daftar channel; `toggleActive()`; badge Active/Paused.
- `app/(app)/config/[tab]/page.tsx` — tab `niches` + `notifications` (TETAP); tab AI-key sudah dibuang.
- `app/api/channels/[id]/keys/route.ts` — route kunci → `vault()` (`lib/youtube.ts`, BASE `MV_API_BASE`/localhost:8088).
- `app/onboarding/page.tsx` — buat channel pertama (draft).
- Pola route dinamis: `export async function POST(req, { params }: { params: Promise<{id:string}> })` + `const {id}=await params`. Auth: `createClient()` + `supabase.auth.getUser()`.

## B. SKEMA DB TARGET (yang dibangun di migr 0091+)
**Tabel BARU `tenant_ai_accounts`** (pool kunci AI):
`id uuid pk · tenant_id text · provider_key text(→ai_providers) · label text · key_enc text(Fernet) ·
status text('valid'|'invalid'|'unchecked') · validated_at timestamptz · created_at · updated_at`. RLS `tenant_id=auth.uid()`.
**Tabel BARU `tenant_youtube_accounts`** (pool koneksi YouTube):
`id uuid pk · tenant_id text · label text · google_client_id text · google_client_secret_enc text ·
google_refresh_token_enc text · google_access_token_enc text · token_expiry · status · validated_at · created_at · updated_at`. RLS `tenant_id=auth.uid()`.
**`channels`:** TAMBAH `youtube_account_id uuid`(→tenant_youtube_accounts) + **`llm_account_id`/`tts_account_id`/`visual_account_id` uuid**(→tenant_ai_accounts). Resolusi: NULL → **auto akun tunggal valid** penyedia itu; bila tenant punya >1 akun penyedia → channel **WAJIB tunjuk akun** (NULL = tak ready). Pertahankan `platform_channel_id`(target). DROP (akhir): `llm_key_enc,tts_key_enc,visual_key_enc`.
> ⚠️ `tenant_ai_accounts` mendukung **banyak baris per (tenant,provider)** (label beda). JANGAN dedup ke 1/penyedia (backfill 0091 lama men-dedup — perlu dikoreksi agar selaras §0.4).
**Telegram:** tetap `tenant_configs.telegram_chat_id`; tambah `telegram_validated_at`/status (validate-early §0.7).
**DROP fosil (akhir, setelah pool jalan):** `channel_credentials`, `tenant_credentials`.

## C. LOGIKA GERBANG `channel_missing(ch)` (TARGET — pseudocode, satu-satunya sumber kebenaran)
```
miss=[]
if !ch.niche: +niche
-- LLM:  if !ch.llm_library:+penyedia naskah
         elif !valid_model(ch.llm_model,'llm',ch.llm_library):+model naskah
         elif needs_key(ch.llm_library) & !tenant_valid_key(ch.tenant_id,ch.llm_library):+kunci naskah
-- TTS:  provider=ch.tts_provider; +model suara / +karakter suara(voice valid) / +kunci suara (sama pola)
-- Visual: provider=ai_models[model dlm visual_mode].provider_key; vm wajib 'ai_image:'/'ai_video:'; +model/+kunci visual
if !ch.publish_slots: +jadwal posting
if !ch.youtube_account_id | !yt_valid(ch.youtube_account_id) | !ch.platform_channel_id: +koneksi YouTube
if !tenant_telegram_valid(ch.tenant_id): +Telegram
return miss
-- needs_key(p)         = ai_providers.auth_type<>'none'
-- tenant_valid_key(t,p)= EXISTS tenant_ai_accounts(t,p,status='valid')
-- valid_model(m,comp,p)= EXISTS ai_models(model_key=m,component=comp,provider_key=p,is_active)
-- yt_valid(id)         = tenant_youtube_accounts(id).status='valid'
-- tenant_telegram_valid= tenant_configs.telegram_chat_id set & validated
```
Trigger + `channel_readiness` + `channel_missing_by_id` semua pakai `channel_missing` ini (nol drift).

---

# §1. TABEL PERSYARATAN CHANNEL AKTIF + PENEMPATAN FE

| # | Syarat (🔴/🟢) | Lingkup | Page FE | DB |
|---|---|---|---|---|
| 1 | Kunci AI penyedia LLM | tenant (pool) | **Credential** | tabel pool kunci AI |
| 2 | Kunci AI penyedia TTS (Edge=gratis) | tenant (pool) | **Credential** | tabel pool kunci AI |
| 3 | Kunci AI penyedia Visual | tenant (pool) | **Credential** | tabel pool kunci AI |
| 4 | Koneksi YouTube (≥1 akun) | tenant (pool) | **Credential** | tabel pool koneksi YT |
| 4b | **Telegram tersambung** (chat_id, validated via pesan tes) | tenant | **Credential** | tenant_configs.telegram_chat_id |
| 5 | Niche | channel | **Channel Setting** | channels.niche |
| 6 | LLM: penyedia + model + **akun** | channel | **Channel Setting** | channels.llm_library/llm_model/**llm_account_id** |
| 7 | TTS: penyedia + model + voice + **akun** | channel | **Channel Setting** | channels.tts_provider/tts_model/voice_key/**tts_account_id** |
| 8 | Visual: generator + model + **akun** | channel | **Channel Setting** | channels.visual_mode/**visual_account_id** |
| 9 | Jadwal tayang (≥1 slot) | channel | **Channel Setting** | channels.publish_slots |
| 10 | Pilih koneksi YouTube + channel tujuan | channel | **Channel Setting** | channels.* (yt connection ref + target) |

**Gerbang:** channel boleh aktif bila semua di atas terpenuhi (provider-aware: penyedia gratis tak butuh kunci;
model wajib valid di katalog). Logika SATU sumber = fungsi DB `channel_missing` (dipakai trigger + FE + worker).

---

# §2. UI/UX (tenant-friendly)

## 2.1 Page Credential ("Akun & Koneksi saya") — perluas `/integrations` yang ADA
- Section **Kumpulan Akun AI**: per penyedia (katalog) + penjelasan elemen (0.4) + tag "dipakai untuk". **Boleh >1 akun/penyedia**
  (label + "Tambah akun"). Tiap akun: field kunci **TAMPIL APA ADANYA** (`type=text`, prefill nilai decrypt, TIDAK di-mask) +
  "Simpan & Uji" → badge valid/invalid (validate-early). Gratis (Edge) = tanpa field.
- Section **Koneksi YouTube**: kumpulan koneksi — "Tambah koneksi" (OAuth), 1..N akun Google. Tiap akun tampil channel-nya + status. (Client ID/Secret tampil apa adanya bila BYO-CC.)
- Section **Telegram** (sudah ada) tetap — chat_id tampil apa adanya + uji.

## 2.2 Page Channel Setting (`/channels/[id]`) — CARD TERPISAH, urut alur isi
> REVISI owner 2026-06-25: (a) **YouTube (koneksi+target) MASUK kartu pertama** "Pengaturan Channel"
> karena = jati-diri & tujuan channel (jangan menggantung di paling bawah). (b) **Kesiapan & Aktivasi
> PINDAH ke tab OVERVIEW** (lihat §2.3) — tab Setting = murni isi konfigurasi. (c) Jadwal = **tab terpisah**
> dalam halaman channel (PINTU 2; PINTU 1 = menu `/schedule` semua-channel). Buang checkbox `is_active` lama.

**Tab SETTING — kartu konfigurasi (urut):**
1. **Pengaturan Channel (identitas & tujuan)** — nama · **Koneksi YouTube (pilih dari pool) + Channel tujuan** (terisi-otomatis dari `yt_channel_id` koneksi, boleh ubah) · niche · bahasa · privasi
2. **Durasi & Format** — preset
3. **Penulis Naskah (LLM)** — penyedia → model → **akun** (auto bila 1 akun; pilih bila >1). Link "Lengkapi di Kredensial" bila belum ada akun.
4. **Pengisi Suara (TTS)** — penyedia → model → voice → **akun**
5. **Pembuat Visual** — generator → model → kualitas → **akun**
6. **Branding & Caption** (opsional)
7. **Operasional & mutu** (musik, QC) — opsional lanjutan

**Tab JADWAL** (pintu 2): slot tayang channel ini (sudah ada).
**Tab OVERVIEW**: kartu **Kesiapan & Aktivasi** (§2.3).

## 2.3 Indikator (D) — kartu Kesiapan di tab OVERVIEW (REVISI 2026-06-25)
- **Tab Overview → kartu "Kesiapan & Aktivasi"** (naikkan kartu readiness yg SUDAH ada di Overview, bukan bikin baru):
  tiap syarat 🔴/🟢 + link ke lokasi konfigurasinya; tombol **Aktifkan** ENABLED hanya saat **semua 🟢**.
- **Daftar channel (`/channels`):** tiap card status ringkas (🔴 belum lengkap / 🟢 siap / ● Aktif / ⏸ Dijeda / ⛔ Dihentikan)
  — komponen bersama `<ChannelStatusBadge>` (satu sumber `effectiveStatus`+`channel_missing`, tanpa drift). Card = status-first,
  aksi state-driven (belum lengkap→"Lengkapi"→Overview; siap→Aktifkan ter-gate; aktif→Kelola+Jeda; dihentikan→Pulihkan),
  sinyal NYATA saja (Video=`videos` published, tren=`production_runs`/`video_analytics`; empty-state untuk channel baru; NOL angka palsu/error mentah).
- Pesan "kurang apa" dari `channel_missing` (string: niche·penyedia/model/kunci naskah·penyedia/model/karakter/kunci suara·jenis/model/penyedia/kunci visual·jadwal posting·koneksi YouTube·Telegram) → dipetakan ke kalimat manusiawi + tautan.
- ⚠️ Sumber data card TERVERIFIKASI BE (audit 2026-06-25): Video terbit=`videos`(published/channel) BUKAN `production_runs`; kuota=`published_today_count`; lihat memory `reference_be_pipeline_tables_fossils`.

---

# §3. PLAN vs REALISASI

Format: tiap fase punya **Plan** (yang akan dilakukan) & **Realisasi** (diisi saat dikerjakan).

> 🔴 **DEVIASI HARUS DILURUSKAN (audit owner 2026-06-25)** — implementasi sebelumnya MENYIMPANG dari §0.4:
> 1. **AI level-AKUN belum ada.** DB: tambah `channels.{llm,tts,visual}_account_id`; `tenant_ai_accounts` izinkan >1/penyedia
>    (backfill 0091 yg men-dedup perlu dikoreksi). BE `_set_key_from_pool` → resolve per **akun yang ditunjuk channel**
>    (NULL→auto bila tunggal). Gate `channel_missing` → cek akun valid yg ditugaskan. FE kartu AI → tambah **pemilih akun** (auto bila 1).
> 2. **"Tampil apa adanya" belum ada.** BE: endpoint **decrypt readback** (kunci AI + YT client id/secret). FE: prefill `type=text`, bukan write-only.
> Fase 4/5/6 Realisasi di bawah = SEBELUM koreksi ini; harus di-update setelah diluruskan.
>
> **PROGRES KOREKSI (2026-06-25):**
> - ✅ **Migr 0093 APPLIED LIVE** (guarded, ryan `[]` sebelum+sesudah) — `ai_providers.key_group` (openai_tts→openai) · `tenant_ai_accounts.key_group` · `channels.{llm,tts,visual}_account_id` + backfill ryan (3 akun). **NOL tabel baru** (hanya add column).
> - ✅ **Migr 0094 APPLIED LIVE** — `channel_missing` + helper `tenant_ai_key_ok` (vendor key-group + akun-ditugaskan/auto). ryan ready, openai_tts auto-pakai kunci openai ✓. (0092 di-skip — 0094 menggantikan.)
> - ✅ **BE** `tenant_config._set_key_from_pool(...,account_id)` = resolusi akun-ditugaskan + vendor key-group (py_compile OK).
> - ✅ **BE** `api_key_vault.list_ai_accounts` = baca-balik (decrypt) "tampil apa adanya"; **FE** `/integrations` prefill `type=text` (ryan keys ter-decrypt ✓, vault :8088 nyala).
> - ✅ **BE vault**: `set_ai_account` vendor/multi(+account_id) · `delete_ai_account` · `list_ai_accounts` baca-balik(+key_group) · webhook route `/api/credentials/ai`(+account_id)+`/ai/delete`. py_compile OK. Vault lokal :8088 jalan (launcher `scratchpad/run_vault.py`).
> - ✅ **YouTube OAuth PLATFORM**: `GOOGLE_CLIENT_ID/SECRET` di `.env` LOKAL (di-source dari app developer `963179529813-…` yg tersimpan di DB ryan — kredensial PLATFORM, swappable; tenant tak pegang). `.env` VPS perlu 2 kunci sama saat deploy.
>
> 🟧 **STATE MID-BUILD (2026-06-25) — lanjut PERSIS dari sini (anti-compaction):**
> - `src/billing/youtube_oauth.py` SUDAH diubah ke OAuth Platform: `_platform_client()` (env), `_create_account()` (tanpa client creds), `init_connection(tenant_id, account_id, label, ret)` (TANPA client_id/secret), `handle_callback` pakai `_platform_client()`. (`_save_client`/`_load_client` DIBUANG.)
> - ⚠️ **BELUM diselaraskan (rantai jadi tak konsisten sampai diselesaikan — JANGAN restart vault dulu):**
>   1. `src/billing/webhook_app.py` `_yt_init` masih kirim `client_id/client_secret` ke `init_connection` → **HAPUS** arg itu (panggil `init_connection(tenant_id, account_id=…, label=…, ret=…)`).
>   2. `src/utils/tenant_credentials.py` `load_google_credentials`/`_row_to_creds` masih bangun creds dari `account.google_client_id/secret` → ganti pakai **`os.getenv('GOOGLE_CLIENT_ID'/'GOOGLE_CLIENT_SECRET')`** + refresh_token akun.
>   3. FE `apps/web/src/app/api/youtube/connect/route.ts` + `onboarding` + `/integrations` masih kirim/minta `client_id/secret` → FE jadi tombol **"Hubungkan dengan Google"** saja (POST `{label}` tanpa client creds).
> - ✅ **(a) Rantai OAuth Platform SELESAI** (youtube_oauth+webhook+Next connect+FE tombol "Hubungkan dengan Google"; init kembalikan authorize_url tanpa client tenant; build PASS).
> - ✅ **(b) FE `/integrations` per-elemen multi-kunci SELESAI** (3 kartu LLM/TTS/Visual; vendor map via `ai_providers.key_group`; Tambah/Edit(+account_id)/Hapus(`/api/credentials/ai/delete`); nilai `type=text` tampil-apa-adanya; build PASS, HTTP 200). Route Next: GET/POST(+account_id) + `/ai/delete` baru.
> - ✅ **(c) FE `/channels/[id]` pemilih AKUN per-elemen SELESAI** (kartu LLM/TTS/Visual: penyedia→model(→voice)→**akun** auto-bila-1/pilih-bila->1; simpan `channels.{llm,tts,visual}_account_id`; build PASS). ✅ **Regresi ryan: worker dapat 3 kunci** (vendor-sharing visual=openai ✓).
> - ✅ **(d) Onboarding** dibetulkan: kunci → POOL `/api/credentials/ai` (endpoint per-channel MATI dibuang), copy fallback-platform diralat. (Rework penuh ke "pengarah 2-langkah" = ranah FUNNEL, ditunda.)
> - **SISA (butuh DEPLOY / manual — gated):** (e) **verify tenant-baru e2e** (signup→Kredensial→Channel→Aktif→produksi; OAuth consent butuh browser = langkah owner). (f) **drop fosil 0095** — DITUNDA sampai SETELAH deploy BE baru ke VPS (VPS worker lama mungkin masih baca tabel lama) + **fix FE admin test-lab** (`apps/web/.../admin/test-lab/*` masih baca `tenant_credentials`). 0095 sudah ditulis+rollback-test, apply pasca-deploy.
>
> 🟩 **STATUS: KODE Fase 5-9 SELESAI & tervalidasi lokal (2026-06-25)** — DB 0093/0094 LIVE · BE pool+vendor+OAuth-platform · FE Credential per-elemen multi-kunci · Channel picker akun · **Fase 7: komponen status bersama `lib/channel-status.tsx` + daftar `/channels` world-class (badge nyata, aktivasi ter-gate+ramah, handle benar, Video terbit nyata) + detail di-DRY** · onboarding keys→pool · admin test-lab lepas `tenant_credentials` · **NOL pembaca tabel fosil (FE+BE)** → 0095 drop-ready. Semua build PASS + regresi ryan AMAN.
✅ **DEPLOYED LIVE ke VPS (2026-06-25, commit `06c5e90`)** — git pull (worker+web repo) · `.env` VPS isi `GOOGLE_CLIENT_ID/SECRET` (mv-webhook EnvironmentFile + mv-worker load_dotenv) · mv-web rebuilt (✓ 23.4s) · restart mv-webhook/mv-worker/mv-web (semua active) · mesinviral.com=200. **Migr 0095 APPLIED** (drop channel_credentials/tenant_credentials/*_key_enc/token_path + null client-creds baris YT) → **NOL dual-state**. **Regresi ryan AMAN**: channel_missing=[], YouTube creds resolve (client_id .env + refresh pool → publish OK), worker restart bersih (nol error).
✅ **CLEANUP + EVALUASI MENYELURUH SELESAI (2026-06-25, commit `bb80162`, deployed):**
- **onboarding → PENGARAH** (2-langkah Kredensial→Channel, sinyal nyata; wizard mock + endpoint mati dibuang).
- **admin test-lab → POOL** (tak baca kolom tenant_configs yg didrop 0090).
- **SAPU FOSIL:** buang file-fallback `token_youtube.json` di youtube_publisher + channel_analytics (no-fallback, nol dual-state) · sapu komentar/docstring usang (BYO-CC→OAuth Platform; tenant_credentials/channel_credentials=DI-DROP 0095; niches.voice_*=DI-DROP 0083) di BE+FE+marketing.
- **EVALUASI PENUH HIJAU:** ryan gate=[] · kunci AI dari pool · YouTube creds resolve · **nol pembaca tabel fosil** (FE+BE) · `.env` lokal+VPS **platform-only** (backup VPS dihapus) · build PASS · py_compile PASS · 3 service VPS active · mesinviral.com=200 · worker nol error.

**SISA = HANYA milik owner (tak bisa otomatis):** verify tenant-baru dari NOL e2e (signup→Kredensial→Channel→Aktif→produksi+publish; OAuth consent = klik browser Anda).
> - **ATURAN restart server lokal:** `:3000` via `scratchpad/run_web.py` (muat root `.env` → S3+Google tak putus); vault `:8088` via `scratchpad/run_vault.py`.

### Fase 0 — Fondasi (SEBAGIAN SUDAH, sesi 2026-06-24)
- **Plan:** purge Pexels (visual=generator AI), kolom config AI per-channel, gate DB awal (trigger+RPC), BE no-fallback, FE provider→model.
- **Realisasi:** ✅ DEPLOYED (migr 0088-0090, commit 9ee571b). ⚠️ Kunci masih per-channel-inline → akan PINDAH ke pool (Fase 2). Gate/no-fallback/provider-aware TETAP dipakai.

> Tiap fase: langkah KONKRET per area (file/migrasi/fungsi di §0.8). Validasi LOKAL dulu (rollback-test DB +
> py_compile/import + `next build`), deploy per-batch (urut aman), isi **Realisasi** saat dikerjakan.

### Fase 1 — Bersihkan `.env` (platform-only) [aman, standalone]
- **BE:** `ai_image.py:97` → `self.api_key = config.get("visual_api_key") or ""` (buang `os.getenv REPLICATE`);
  bila kosong + platform replicate → `raise VisualError` (gagal jujur). `telegram_notifier.py:29` → buang
  `system_chat_id` (chat_id WAJIB dari tenant_config; kalau kosong → skip kirim, log info).
- **ENV (lokal+VPS `/home/rad4vm/viral-machine-v2/.env`):** hapus baris `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `REPLICATE_API_TOKEN`, `TELEGRAM_CHAT_ID`, `R2_ACCESS_KEY/SECRET_KEY/BUCKET/ENDPOINT`.
- **Validasi:** `python -m py_compile`; load_tenant_config ryan OK; grep env bersih. **Deploy:** push → VPS pull +
  edit .env + restart mv-worker/mv-webhook.
- **Realisasi:** ✅ **LOKAL DONE + tervalidasi (2026-06-24).** `ai_image.py` kunci visual = `visual_api_key` saja
  (fallback `os.getenv REPLICATE` dibuang; Replicate tetap opsi; `:348` set-env dari kunci tenant tetap).
  `telegram_notifier.py` buang `system_chat_id` (chat_id wajib DB; kosong=skip). `.env` lokal ditulis ulang =
  HANYA platform (buang OPENAI/ANTHROPIC/REPLICATE_API_TOKEN/TELEGRAM_CHAT_ID/R2_*). Validasi runtime: telegram
  no system_chat_id ✓, ai_image no-fallback ✓, ryan load 3 kunci ✓ (sumber `channels.*_key_enc`, blm berubah), grep env BERSIH ✓.
  ⏳ **VPS .env + restart = ditunda ke deploy batch (Fase 9).**

### Fase 2 — DB: buat pool + backfill (migr `0091_credential_pools.sql`)
- **DB:** CREATE `tenant_ai_accounts` + `tenant_youtube_accounts` (skema §0.8.B) + RLS. ALTER `channels` ADD
  `youtube_account_id uuid`. **Backfill:** (a) tiap `channels.{llm,tts,visual}_key_enc` → INSERT `tenant_ai_accounts`
  (tenant, provider dari channel, key_enc, status='unchecked'); dedup per (tenant,provider). (b)
  `channel_credentials`/`tenant_credentials` → INSERT `tenant_youtube_accounts` + set `channels.youtube_account_id`.
- **Validasi:** rollback-test → ryan punya baris pool kunci (openai, elevenlabs) + 1 youtube account + channel ter-link.
- **Realisasi:** ✅ **DITULIS + rollback-test PASS (2026-06-24)** `migrations/0091_credential_pools.sql`.
  Buat `tenant_ai_accounts` + `tenant_youtube_accounts` (+ index + RLS select tenant) + `channels.youtube_account_id`.
  Backfill: ryan → AI accounts {openai, elevenlabs} status='valid' (dedup per tenant×penyedia; openai dari llm+visual
  satu baris), 1 youtube account 'valid', channel ter-link. ⏳ APPLY ke live = deploy batch Fase 9 (belum di-apply).

### Fase 3 — DB: lengkapi gerbang (migr `0092_channel_missing_complete.sql`)
- **DB:** CREATE OR REPLACE `channel_missing(ch)` = pseudocode §0.8.C (tambah: model valid-katalog LLM/TTS, voice valid,
  jadwal, youtube_account_id+valid+target, Telegram valid; kunci dicek dari `tenant_ai_accounts` status='valid'
  provider-aware). RPC `channel_readiness`/`channel_missing_by_id` + trigger sudah otomatis ikut (panggil fungsi sama).
- **Validasi:** rollback-test → ryan `channel_missing` sesuai (status pool 'unchecked' → mungkin perlu validasi Fase 5);
  channel kurang → tertahan trigger.
- **Realisasi:** ✅ **DITULIS + rollback-test (0091+0092) PASS (2026-06-24)** `migrations/0092_channel_missing_complete.sql`.
  `channel_missing` lengkap (model valid-katalog LLM/TTS/Visual · voice valid · kunci dari `tenant_ai_accounts`
  status='valid' provider-aware · jadwal ≥1 · `youtube_account_id` valid + `platform_channel_id` · Telegram chat+enabled).
  Hasil: **ryan = [] (ready)**; Admin Test = [kunci naskah, jenis visual, jadwal posting, koneksi YouTube, Telegram];
  trigger loloskan re-aktivasi ryan. (Backfill 0091 set pool status='valid' → ryan lolos.) ⏳ APPLY = deploy batch Fase 9.

### Fase 4 — BE: baca kredensial dari pool + validate-early
- **BE:** `tenant_config._apply_channel_overlay` → resolve kunci per elemen dari `tenant_ai_accounts`
  (tenant + provider channel, status valid) — buang `_set_channel_key` baca `channels.*_key_enc`.
  `youtube_publisher`/`channel_analytics`/`tenant_credentials.load_google_credentials` → resolve dari
  `tenant_youtube_accounts` (via `channels.youtube_account_id`) + `platform_channel_id`.
  `api_key_vault.py` → `set_ai_account(tenant,provider,key)` + `validate_ai_key(provider,key)` (test-call) +
  `set_youtube`/`validate` + `validate_telegram(chat_id)` (kirim pesan tes). `webhook_app.py` route baru:
  `/api/credentials/ai`, `/api/credentials/ai/validate`, `/api/credentials/youtube`, `/api/credentials/telegram/test`.
- **Validasi:** uji produksi ryan (config-level identik) — kunci dari pool, no-fallback.
- **Realisasi:** ✅ **DONE + tervalidasi LIVE (2026-06-24; 0091 sudah di-apply ke live, additif aman).**
  `tenant_config`: `_set_key_from_pool` + `_visual_provider` → kunci LLM/TTS/Visual dari `tenant_ai_accounts`
  (provider-aware, status='valid'); buang `_set_channel_key` (channels.*_key_enc). `tenant_credentials.py`:
  `load_google_credentials`/`save_google_access_token` → dari `tenant_youtube_accounts` via `channels.youtube_account_id`
  (+`_account_id_for`). `api_key_vault.py`: `set_ai_account`+`validate_ai_key`(test-call openai/anthropic/elevenlabs/
  replicate; unknown→unchecked)+`list_ai_accounts`+`validate_telegram`(pesan tes). `webhook_app.py`: route
  `/api/credentials/ai`, `/ai/list`, `/telegram/test`. **Validasi:** ryan kunci+OAuth dari pool ✓; validate-early
  real→valid, bogus→invalid, provider-baru→unchecked ✓; compile+nol stray ✓.
  ⏳ **YouTube OAuth flow tulis ke pool = Fase 5** (connect via Credential page). Deploy BE = batch Fase 9.

### Fase 5 — FE: Page Credential (perluas `/integrations`)
- **FE:** `integrations/page.tsx` + Next routes. Section **Kunci AI**: list penyedia dari `ai_providers` (gratis=tanpa
  field) + penjelasan elemen (§0.4) + field kunci + tombol "Uji" → `/api/credentials/ai/validate` → badge 🟢/🔴
  (status disimpan). Section **Koneksi YouTube**: list `tenant_youtube_accounts` + "Tambah akun" (OAuth) + status.
  Section **Telegram**: chat_id + "Kirim pesan tes" → validate. Pakai kelas design-system yang ADA.
- **Validasi:** `next build`; isi kunci → uji → 🟢; webhook lokal jalan.
- **Realisasi:** 🔄 **PARSIAL (2026-06-24):**
  ✅ Next routes: `apps/web/src/app/api/credentials/ai/route.ts` (GET list + POST set) + `.../telegram/route.ts` (POST test).
  ✅ `/integrations` (judul→"Kredensial & Koneksi"): section **Kunci AI** (penyedia katalog yg punya model aktif, gratis
     disaring, field kunci + "Simpan & Uji" → validate-early → badge Valid/Tidak valid/Tersimpan/Belum) + tag "dipakai untuk".
  ✅ **Telegram validate-early**: `saveTelegram` → `/api/credentials/telegram` (pesan tes; hanya tersimpan bila terkirim).
  ✅ **YouTube OAuth → POOL DONE:** `youtube_oauth.py` rewrite account-based (`tenant_youtube_accounts`): state bawa
     `account_id`, `_save_client`/`_store_tokens`/`_load_client`/`disconnect`/`list_accounts` ke pool; `init_connection`
     account_id None=koneksi baru; status='valid' saat callback. webhook routes + Next routes (`connect`/`disconnect`/
     `status`) + FE YouTube section = POOL (daftar koneksi + "Tambah koneksi" + per-akun hapus; bisa banyak akun Google).
  ✅ **`next build` PASS** + BE py_compile PASS. ⏳ Runtime OAuth dance e2e (tenant connect nyata) = saat deploy/verify Fase 9.
  **FASE 5 SELESAI.**

### Fase 6 — FE: Channel Setting (card terpisah + urut §2.2 REVISI 2026-06-25)
- **FE:** `channels/[id]/page.tsx` tab Setting — urut kartu §2.2: **(1) Pengaturan Channel = nama + KONEKSI YouTube(pool)+target + niche + bahasa + privasi (buang checkbox is_active)** → (2) Durasi → (3) LLM → (4) TTS → (5) Visual → (6) Branding&Caption → (7) Operasional. Tiap elemen AI: penyedia→model (kunci dari pool, TAK isi di sini); link "Lengkapi di Kredensial" bila pool kosong. Kesiapan&Aktivasi BUKAN di sini (→ Overview, Fase 7). Jadwal tetap tab.
  - **Bereskan dead-code:** hapus state `keys`, fungsi `saveAi` lama, pemuat GET `/api/channels/[id]/keys`, dan **HAPUS file route `apps/web/src/app/api/channels/[id]/keys/route.ts`** (panggil endpoint vault yg TAK ADA → mati). Ganti dgn `saveLlm/saveTts/saveVisual` (hanya tulis penyedia/model/voice ke `channels`). Tambah pemilih `youtube_account_id` (dari `/api/youtube/status`) + simpan bareng `platform_channel_id`.
- **Validasi:** `next build`; ryan tampil benar; pilih penyedia/model jalan.
- **Realisasi:** ✅ **SELESAI + DEPLOYED (verified audit 2026-07-01)** — Channel Setting card-terpisah + pemilih AKUN per-elemen (llm/tts/visual `account_id`, auto-bila-1/pilih-bila->1) + YouTube di kartu identitas + Kesiapan di Overview. FE `channels/[id]/page.tsx:116-429` (verified). Bagian dari deploy `06c5e90`/`bb80162`.

### Fase 7 — FE: indikator 🔴/🟢 + lock konsisten (Kesiapan di OVERVIEW)
- **FE:** komponen bersama `lib/channel-status.ts` + `<ChannelStatusBadge>` (pindah `effectiveStatus`); dipakai
  `channels/[id]` (badge header), `channels/page.tsx` (card daftar), `dashboard`. RPC batch `channels_readiness_mine()` (migr baru) utk daftar.
  **Kartu "Kesiapan & Aktivasi" di tab OVERVIEW** (naikkan kartu readiness yg sudah ada): tiap syarat 🔴/🟢 + link ke konfigurasinya (peta string `channel_missing`→kalimat+tautan); tombol Aktifkan enabled hanya semua 🟢.
  **Card daftar `/channels` (redesign world-class):** status-first + aksi state-driven + sinyal nyata (Video=`videos` published, sparkline produksi=`production_runs`) + empty-state + overflow ⋯ + perbaiki handle (`youtube.com/channel/{id}`, bukan `@platform_channel_id`).
  `toggleActive` (daftar) + semua jalur: pre-check readiness, tangkap error DB → pesan ramah (nol error mentah).
- **Validasi:** `next build`; channel belum-lengkap → 🔴 + tombol mati + pesan ramah; lengkap → 🟢 + aktif.
- **Realisasi:** ✅ **SELESAI + DEPLOYED (verified audit 2026-07-01)** — komponen status bersama `lib/channel-status.tsx` + `<ChannelStatusBadge>`, daftar `/channels` world-class (badge nyata, aktivasi ter-gate), kartu Kesiapan & Aktivasi di Overview. Bagian deploy `06c5e90`/`bb80162`.

### Fase 8 — Onboarding = PENGARAH 2-langkah (SIMPLIFIKASI owner 2026-06-25)
- **Keputusan:** onboarding TIDAK lagi wizard yg menduplikasi konfigurasi. Cukup **pengarah**: arahkan tenant baru
  melengkapi **(1) Page Kredensial** (`/integrations`: kunci AI + koneksi YouTube + Telegram, semua 🟢) lalu
  **(2) Page Channel** (`/channels/[id]`: niche/LLM/TTS/Visual/jadwal/YouTube). **Onboarded = channel pertama semua
  indikator 🟢.** Pakai SINYAL SAMA (`channel_missing` + status pool), nol mock, nol drift.
- **FE:** rombak `onboarding/page.tsx` jadi guide ringkas 2-checklist (Kredensial → Channel) yg membaca status nyata
  (kredensial pool + `channel_readiness`); auto-buat channel draft (atau arahkan `/channels/new`). **BUANG:** wizard mock
  niche/voice/bahasa (hardcode baris 50-77), pemanggilan endpoint MATI `/api/channels/${cid}/keys` (baris 166), copy
  "fallback kredensial platform" (baris 353, langgar no-fallback). Kunci kalau diisi di onboarding → pool `/api/credentials/ai`.
- **Catatan:** rework mendalam katalog niche/voice di onboarding = ranah FUNNEL (setelah remediasi), bukan epik lock.
- **Realisasi:** ✅ **SELESAI + DEPLOYED (verified audit 2026-07-01)** — `onboarding/page.tsx` = pengarah 2-langkah (Kredensial → Channel; baca `channel_readiness` + status AI/YouTube/Telegram nyata; wizard mock + endpoint mati dibuang). Bagian deploy `bb80162`. *(Growth-funnel video-gratis = ranah `ONBOARDING_FUNNEL_PLAN.md`, decision-gated — lihat PROGRESS AUDIT [D].)*

### Fase 9 — Validasi total, deploy, drop fosil (migr `0093_drop_legacy_credentials.sql`)
> Fosil TERVERIFIKASI audit BE 2026-06-25 (memory `reference_be_pipeline_tables_fossils`): worker baca 0× `channel_credentials`/`tenant_credentials` (grep terbukti); kredensial YouTube hidup = `tenant_youtube_accounts` (via `channels.youtube_account_id`); kunci AI hidup = `tenant_ai_accounts`.
- **Validasi:** e2e (ryan + 1 channel uji dari nol via onboarding sampai 🟢 & aktif), `next build` PASS, rollback-test semua migrasi. Apply 0092 (belum live).
- **Deploy:** urut aman (DB additif 0091/0092 → kode BE+FE → verifikasi ryan → drop 0093).
- **DB drop (0093):** `channels.{llm,tts,visual}_key_enc` · `channels.token_path` · tabel `channel_credentials`, `tenant_credentials`.
- **Bereskan sebelum drop:** FE admin test-lab (`apps/web/.../admin/test-lab/{route,test/route}.ts`) masih baca `tenant_credentials` → pindah ke pool/atau matikan; matikan fallback file `token_youtube.json` di `youtube_publisher.py`/`channel_analytics.py` (bahaya multi-tenant); sapu komentar usang (tenant_config.py:534-540, TTS adapters niches.voice_*).
- **Di LUAR epik lock (catat ke remediasi multi-channel):** `channels.content_language` orphan (bahasa run masih `tenant_configs.language`); `performance_analyzer` insight per-tenant (bleed antar-channel — ✅ FIX `3bd32ee`).
- **Realisasi:** ✅ **SELESAI + DEPLOYED (verified audit 2026-07-01)** — **migr 0095 APPLIED** (drop `channel_credentials`/`tenant_credentials`/`*_key_enc`/`token_path`); NOL dual-state; nol pembaca fosil (FE+BE); `.env` platform-only; regresi ryan aman. Deploy `06c5e90`. **SISA (bukan epik lock) = acceptance tenant-baru-dari-nol e2e = butuh browser owner (OAuth consent) → PROGRESS §GATE D1.**

---

# §4. DEFINITION OF DONE (kriteria "bungkus" — TUNTAS, nol sisa)

> 🎯 **ACCEPTANCE UTAMA (owner 2026-06-24): TENANT BARU dari NOL — BUKAN ryan.** ryan = tenant TEST (grandfathered).
> Yang menentukan SELESAI = **tenant baru** bisa: daftar → Page Credential (isi kunci AI + connect YouTube + Telegram,
> SEMUA tervalidasi 🟢) → Channel Setting (pilih penyedia+model+voice+jadwal+YouTube) → **semua indikator 🟢** →
> **Aktifkan** → produksi + publish + analitik jalan. Kalau tenant baru TAK bisa sampai aktif mulus → **BELUM selesai**.
> ⚠️ **NOL DUAL-STATE / "saklar setengah ON":** keadaan akhir = sistem 100% di model baru, jalur lama DIBUANG.
> Bahaya yang DIHINDARI: demi ryan, jalur lama dibiarkan hidup → tenant real bermasalah. → Hijrah PENUH, lalu drop fosil.

Pekerjaan ini dianggap SELESAI hanya bila SEMUA terpenuhi & tervalidasi:
1. **`.env` (lokal+VPS) = 100% platform.** Nol kredensial tenant, nol fosil. (cek: grep tak ada
   OPENAI/ANTHROPIC/REPLICATE/TELEGRAM_CHAT_ID/R2_*.)
2. **Kredensial tenant 100% di DB** (pool kunci AI + pool koneksi YouTube). ryan ter-backfill, tervalidasi.
3. **Gerbang lock = di DB** (`channel_missing`) + identik dipakai trigger/FE/worker. Cek lengkap: niche · LLM/TTS/
   Visual penyedia+model(valid katalog)+voice · kunci penyedia ada di pool (provider-aware) · jadwal · koneksi YouTube+target.
4. **2 halaman saja**: Credential (pool kunci AI + koneksi YouTube) + Channel Setting (card terpisah, urut alur).
5. **Indikator 🔴/🟢** di tiap card channel + card Kesiapan; tombol Aktifkan enabled HANYA semua 🟢; tiap indikator
   ada link ke konfigurasinya; semua jalur aktivasi pesan ramah (nol error mentah).
6. **NO-FALLBACK** total (termasuk Replicate env-fallback dibuang; Replicate tetap OPSI BYOK).
7. **Tervalidasi end-to-end — TENANT BARU (acceptance utama)**: buat tenant uji BARU dari nol → setup penuh →
   semua 🟢 → aktif → produksi+publish+analitik jalan. (ryan grandfathered = cek regresi, bukan tolok ukur.)
   Channel belum-lengkap TIDAK bisa aktif (DB tolak).
8. **Fosil di-drop** (kolom `channels.*_key_enc`, tabel `channel_credentials`/`tenant_credentials`) — nol bangkai,
   **nol dual-state**: sistem hanya punya SATU jalur (pool + gerbang baru). Tak ada kode/DB jalur lama tersisa.
9. **Tak ada bug/error terkait lock/kredensial** setelah deploy (dipantau 1 siklus produksi+publish tenant baru + ryan).

# §5. KEPUTUSAN TELEGRAM (FINAL, owner 2026-06-24)
- **Notif Telegram = murni per-tenant dari DB** (`tenant_configs.telegram_chat_id`). Tiap tenant connect bot →
  simpan chat_id sendiri. Tenant belum isi → belum dapat notif (diberi petunjuk), TIDAK nyasar ke chat siapa pun.
- **Buang `TELEGRAM_CHAT_ID` dari `.env`** + buang fallback `system_chat_id` di `telegram_notifier.py:29`.
- **Bot token tetap platform** (`.env` `TELEGRAM_BOT_TOKEN`, 1 bot semua tenant).
- (Alert sistem ke admin = TIDAK dibutuhkan sekarang; bila perlu nanti pakai `ADMIN_TELEGRAM_CHAT_ID` = chat owner.)

# §6. TERKAIT (guardrail, agar tak muncul "bug" lain)
- **Test job tidak boleh memakan kuota publish live** (insiden 2026-06-24: test music/vocal publish → kuota 3/hari
  habis → slot 06:00 WIB skip). Pastikan jalur test private tak terhitung cap harian / tak publish ke channel live.
  (Scope terpisah, tapi dicatat agar dituntaskan dalam paket "channel jalan benar".)

---

## Catatan keputusan owner (2026-06-24)
A,B,C ✅ · D ✅ (indikator 🔴/🟢 per card + aktivasi enabled saat semua hijau + link tiap indikator) ·
trend-radar = **platform account** (analisis kuota §0.3, angka resmi Google) · card channel-setting terpisah & urut ·
`.env` platform-only, kredensial tenant 100% di DB · **Replicate = OPSI (bukan dibuang); hanya env-fallback yang dibuang.**

---

# §7. KLAIM CHANNEL YOUTUBE — kuncian anti trial-berulang *(dibuka 2026-08-20, SSOT kerja aktif)*

> **Sesi baru / pasca-compacting: baca §7 ini saja, lalu lanjut dari baris ⬜ pertama di §7f.**
> Acuan alur OAuth yang sah = **`src/billing/youtube_oauth.py`** (bukan `PER_CHANNEL_OAUTH_MIGRATION §6` — sudah basi).

## §7a. Persoalan (ketokan owner 2026-08-20)

Tenant masa coba boleh mendaftar ulang — itu haknya. Yang **tidak** boleh: membawa channel YouTube yang
sudah terdaftar di akun lain, sehingga masa coba bisa diputar tanpa batas dengan email baru. Owner:
*"kuncinya bukan di pendaftaran, tapi di integrasi."*

**Terukur di lapangan 2026-08-20 (jangan audit ulang):**

| Fakta | Angka |
|---|---|
| Dua indeks unik yang ada di-scope **per-tenant**, bukan global (`migrations/0146`) | `(tenant_id, platform_channel_id)` · `(tenant_id, yt_channel_id)` |
| `disconnect()` **MENGHAPUS** baris pool → kuncian di tabel itu akan lenyap | `youtube_oauth.py:304` |
| Jangkar `trial_started_at` mengikat **AKUN**, bukan channel; 2 dari 18 tenant bahkan kosong | akun baru = jangkar baru |
| Channel dipakai >1 tenant hari ini | **0** (dari 15 koneksi ber-identitas / 21 total) — lubang masih bersih |
| Tenant dengan >1 channel di satu akun Google | **4 tenant**, satu di antaranya **4 channel** |
| Tabel pool **tidak menyimpan** email/akun Google | ⇒ mengunci per-akun-Google **mustahil secara data** |
| Koneksi tanpa identitas (`yt_channel_id` NULL) | **6** — tak bisa diklaim, jangan disentuh |
| Trend-radar | **kunci API biasa** (`YOUTUBE_PLATFORM_API_KEY`), **bukan OAuth** ⇒ tidak lewat callback, **tidak ikut terkunci** |

## §7b. Arsitektur

**Satu catatan klaim per channel YouTube. Kunci ditegakkan DATABASE, bukan baris `if`** — baris `if` bisa
dilupakan sesi berikutnya dan **kalah pada perlombaan** (dua akun menyambung di detik yang sama).

```
tabel youtube_channel_claims
  yt_channel_id     text  PRIMARY KEY   <- DI SINI kuncian itu hidup
  tenant_id         text  NOT NULL      <- pemilik sekarang
  yt_channel_title  text                <- agar admin bisa membacanya
  claimed_at        timestamptz
  TANPA foreign key · TANPA cascade     <- SENGAJA, lihat §7c
```

**Titik periksa = SATU:** `handle_callback` (`youtube_oauth.py`), tepat di `_find_existing_connection`,
di dalam layanan `mv-webhook` (:8088).

**URUTAN OPERASI (menentukan — salah urut = bug):**
1. Identitas channel dibaca. *(Gagal baca sudah ditolak jujur hari ini — `identity_failed`. Nol kerja baru.)*
2. **Klaim diperiksa LEBIH DULU** daripada dedup se-tenant. Kalau dedup jalan dulu, alur
   "sudah terhubung → segarkan token" bisa mendahului penolakan.
3. Klaim milik **tenant lain** → **TOLAK**: placeholder dibuang, token **TIDAK** disimpan,
   **token TIDAK dicabut ke Google** (alasan di §7c-1), balas **KODE** `?youtube=channel_claimed`.
4. Klaim **milik tenant ini** atau **belum ada** → jalan seperti hari ini (dedup/simpan tak diubah).
5. Klaim ditulis **SESUDAH** token tersimpan sukses. Bila penulisan klaim bentrok (perlombaan),
   koneksi yang baru tersimpan **dibatalkan** — tidak meninggalkan setengah keadaan.

**Jalur buka (mandat owner "setiap kunci punya jalur buka", `PAYMENT §10e-2`):**

| Kunci | Jalur buka yang sah |
|---|---|
| Klaim channel YouTube | **admin "Lepas klaim"** (tercatat `admin_audit`) · **saklar induk** `app_config.channel_claim_enabled = 0` (seketika, tanpa deploy) |

Tenant **sengaja tidak** diberi jalur — ketokan owner: *"tidak ada alasan tenant memindahkan channel ke akun
MesinViral lain kecuali memang berniat curang."* Tiga kejadian sah (pemulihan akun · agensi menyerahkan ke
klien · channel benar-benar dijual) semuanya lewat pintu admin.

## §7c. EMPAT TEMUAN EVALUASI FINAL — dua di antaranya akan melahirkan bug baru

**1. JANGAN cabut token ke Google saat menolak.** Rencana awal saya mencabutnya. Tapi 4 tenant hari ini punya
beberapa channel di **satu akun Google**; mencabut refresh token berisiko membatalkan grant lain dari akun
yang sama ⇒ merusak koneksi tenant yang sedang sehat. **Menolak = cukup tidak menyimpan + buang placeholder.**

**2. Celah di antara migrasi dan deploy.** Koneksi yang terjadi **setelah** isi-mundur tapi **sebelum** penjaga
hidup tidak punya klaim ⇒ channelnya bisa diklaim akun lain kelak. **Penutup: isi-mundur dijalankan ULANG
sesudah BE deploy** (idempoten) sebagai bagian tetap dari tahap deploy, bukan pilihan.

**3. Saklar induk belum ada.** Konvensi owner: tiap gerbang punya saklar di `app_config` yang bisa dimatikan
seketika tanpa deploy. Tanpa itu, kalau penjaga salah menolak di produksi, satu-satunya jalan = deploy ulang.
⇒ tambah kenop **`channel_claim_enabled`** (1 = aktif). *(Nama disamakan dgn gaya kenop yang sudah ada: `test_gate_enabled`, `nurture_enabled`.)*

**4. Urutan periksa** — sudah masuk §7b langkah 2.

**5. TABRAKAN PDP ⟷ KUNCIAN — tidak terpikir saat merencanakan; ditangkap penjaga lama saat dikerjakan.**
`tests/test_purge_pdp_lengkap.py` menuntut TIAP tabel ber-`tenant_id` punya keputusan retensi, dan
`youtube_channel_claims` langsung membuatnya merah. Persoalannya nyata: hak hapus data (UU PDP) menuntut
pengenal tenant dibuang, kuncian menuntut klaim BERTAHAN. Kalau klaim ikut terhapus, penyalahguna dapat
jalan pintas **paling mudah**: hapus akun → daftar baru → sambung channel yang sama.
**Jalan tengah (pola yang SUDAH dipakai `tenant_configs` & `feedback_submissions`):** baris **disimpan**,
`tenant_id` **dianonimkan** ke `__dihapus__` ⇒ nol pengenal tenant tersisa, channel tetap terkunci,
pelepasan tetap hanya lewat admin. Terdaftar di `_KEEP_TABLES` (`renewal.py`) + `LIFECYCLE §4.2` baris SISAKAN.

## §7d. Yang kuncian ini TIDAK menutup (kejujuran, bukan janji)

Kuncian ini menghentikan **produksi gratis berkelanjutan ke channel nyata** — untuk menerbitkan, tenant WAJIB
menyambung channel, dan di situ ia ditolak. Yang **tidak** dihentikan: pendaftar ulang yang **tak pernah**
menyambung YouTube tetap memperoleh jatah uji akunnya (`app_config.trial_test_quota`, kini **3**) dalam bentuk
video uji yang bisa diunduh. Jangkarnya akun, dan akun baru = jatah baru. Menutup itu butuh jangkar lain
(nomor telepon/pembayaran) = **keputusan produk terpisah, di luar §7 ini.**

## §7e. Batas kerja

**Tidak disentuh:** pipa produksi · penerbitan · niche/DNA · pembayaran · pendaftaran · gerbang uji ·
`tests/test_gerbang_tetap_terpasang.py`. **Nol berkas `.md` baru** (§1.1) — dokumen menempel di sini,
`PAYMENT §10e-2` (matriks), dan artikel panduan **#12 `connect-youtube`** (published, sort 27 — diff → ketok → tayang).

## §7f. TAHAPAN & PROGRESS *(update kolom Status saat kerja — ini yang dibaca sesi berikutnya)*

| # | Tahap | Berkas / sasaran | Status |
|---|---|---|---|
| T0 | Verifikasi pra-kode: trend-radar tidak lewat OAuth | — | ✅ **SELESAI** — kunci API, bukan OAuth |
| T1 | Migrasi `0203`: tabel klaim (PK, tanpa FK/cascade) + isi-mundur + pemeriksaan gagal-berisik | `migrations/0203_klaim_channel_youtube.sql` | ✅ **SELESAI & TERPASANG DI DB** — 15 klaim terisi, 0 FK, 0 bentrok |
| T2 | RLS service-role saja | migrasi sama | ✅ **SELESAI** — RLS nyala, **0 policy**, hak anon/authenticated dicabut |
| T3 | Kenop `channel_claim_enabled` (saklar induk) + label dwibahasa di layar admin | migrasi sama + `admin/(panel)/app-config/page.tsx` | ✅ **SELESAI** — nilai live = 1 |
| T4 | Penjaga di `handle_callback` (urutan §7b, kode `channel_claimed`) | `src/billing/youtube_oauth.py` | ✅ **SELESAI** — `klaim_pemilik_lain` · `klaim_catat` · `KlaimTakTerbaca` (fail-closed) |
| T5 | Terjemahan kode galat ID/EN | `(app)/integrations` + `(app)/channels/[id]` | ✅ **SELESAI** — `channel_claimed` & `claim_check_failed` |
| T6 | Kartu klaim + tombol **"Lepas klaim"** + jejak `admin_audit` | `api/admin/channel-claims/route.ts` + `admin/(panel)/tenants/page.tsx` | ✅ **SELESAI** — pakai `ConfirmDialog` yang sudah ada (nol komponen baru) |
| T7a | Uji + sabotase | `tests/test_klaim_channel_tak_bisa_dicolong.py` | ✅ **SELESAI** — 16 uji · 9 dibuktikan MERAH dulu · 6 sabotase semua merah |
| T7b | Dokumen: §7 ini · `LIFECYCLE §4.2` · `_KEEP_TABLES` · `PAYMENT §10e-2` | — | ✅ **SELESAI** |
| T7c | Artikel panduan tenant **#12 `connect-youtube`** — butir baru di *Jebakan umum*, dwibahasa | `docs_articles` | ✅ **SELESAI & TAYANG** (redaksi diketok owner 20-Agu; tetap `published`) |
| T7d | **Deploy BE + FE** + **isi-mundur DIULANG** (temuan §7c-2) | skrip resmi | ✅ **TERPASANG 20-Agu** — `deploy_be` OK (`mv-worker`+`mv-webhook` active, health 200) · `deploy_fe` OK (situs 200) · commit `79c7317` · isi-mundur ulang: 15→15, **0 koneksi ber-identitas tanpa klaim** |

**Bukti terukur (2026-08-20):** 1191 uji hijau · build FE lulus · tabel klaim 15 baris · `channel_claim_enabled = 1` ·
0 foreign key · 0 policy RLS.

**§7h. BUKTI DI SERVER — dijalankan pasca-deploy pada DATA NYATA (bukan simulasi):**

| Skenario | Hasil di server |
|---|---|
| Akun BARU menyambung channel yang sudah diklaim (`THETANGGA PROPERTY`) | **DITOLAK** — pemilik dikenali |
| Pemilik SAH menyambung ulang channelnya sendiri | **BOLEH** (penjaga tidak kebablasan) |
| Channel yang belum pernah diklaim | **BOLEH** |
| Penjaga & saklar induk di server | ada · `channel_claim_enabled = 1` |

⇒ **§7 TUNTAS.** Sisa pekerjaan: nihil. Yang tetap terbuka menurut §7d (di luar §7 ini) = pendaftar ulang
yang tak pernah menyambung YouTube; itu keputusan produk terpisah, bukan sisa kerja §7.

## §7g. Bukti yang diwajibkan (uji MERAH dulu, lalu sabotase)

1. Tenant B menyambung channel milik tenant A → **ditolak**. **Wajib dibuktikan MERAH** di kode sekarang (hari ini berhasil).
2. Tenant A cabut → sambung ulang channelnya sendiri → **tetap boleh**.
3. Satu akun Google, dua channel milik tenant sama → **dua-duanya boleh** (jangan ulangi insiden §3b `PER_CHANNEL_OAUTH_MIGRATION`).
4. Koneksi tanpa identitas → **tak tersentuh**.
5. Saklar induk `channel_claim_enabled = 0` → penjaga diam, alur kembali seperti sebelum §7.
6. **Sabotase:** penjaga dilepas → uji 1 merah · kunci primer dilepas → uji perlombaan merah · saklar diabaikan → uji 5 merah.
   Tidak merah ⇒ ujinya palsu, dibuang.

Hermetik: nol jaringan.
