# Channel Lock Activation — Arsitektur & Plan vs Realisasi

> Status: **ARSITEKTUR DISETUJUI owner 2026-06-24** (A/B/C/D + trend-radar=platform + 2-page + pool).
> Implementasi: **belum mulai** (Plan vs Realisasi di §3). Dokumen ini = acuan resmi.

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

## 0.4 Model kredensial AI (matang, extensible)
- **Page Credential → "Kunci AI":** tenant tempel kunci **per penyedia**. Daftar penyedia **otomatis bertambah**
  seiring platform menambah dukungan (katalog `ai_providers`/`ai_models`, nol kode). Penyedia gratis (Edge) tanpa kunci.
  (Opsi >1 akun/penyedia = lanjutan; default 1/penyedia.)
- **Page Channel Setting:** tiap elemen pilih **penyedia → model** (boleh **sama/beda antar channel**). Kunci
  otomatis dari kumpulan kunci tenant untuk penyedia itu.
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
**`channels`:** TAMBAH `youtube_account_id uuid`(→tenant_youtube_accounts) + `ai_*_account_id uuid` opsional (jika >1 akun/penyedia; NULL→auto akun tunggal). Pertahankan `platform_channel_id`(target). DROP (akhir): `llm_key_enc,tts_key_enc,visual_key_enc`.
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
| 6 | LLM: penyedia + model | channel | **Channel Setting** | channels.llm_library/llm_model |
| 7 | TTS: penyedia + model + voice | channel | **Channel Setting** | channels.tts_provider/tts_model/voice_key |
| 8 | Visual: generator + model | channel | **Channel Setting** | channels.visual_mode |
| 9 | Jadwal tayang (≥1 slot) | channel | **Channel Setting** | channels.publish_slots |
| 10 | Pilih koneksi YouTube + channel tujuan | channel | **Channel Setting** | channels.* (yt connection ref + target) |

**Gerbang:** channel boleh aktif bila semua di atas terpenuhi (provider-aware: penyedia gratis tak butuh kunci;
model wajib valid di katalog). Logika SATU sumber = fungsi DB `channel_missing` (dipakai trigger + FE + worker).

---

# §2. UI/UX (tenant-friendly)

## 2.1 Page Credential ("Akun & Koneksi") — perluas `/integrations` yang ADA
- Section **Kunci AI**: daftar per penyedia (katalog), tiap penyedia 1 field kunci + tag "dipakai untuk: LLM/Visual/…"
  + penjelasan elemen (0.4). Gratis (Edge) = tanpa field. Status tersimpan/belum.
- Section **Koneksi YouTube**: daftar akun Google tersambung + "Tambah akun" (OAuth). Tiap akun tampil YouTube channel-nya.
- Section **Telegram** (sudah ada) tetap.

## 2.2 Page Channel Setting (`/channels/[id]`) — CARD TERPISAH, urut alur isi
1. **Niche & Format** (niche, bahasa, durasi preset)
2. **Penulis Naskah (LLM)** — penyedia → model
3. **Pengisi Suara (TTS)** — penyedia → model → voice
4. **Pembuat Visual** — generator → model → kualitas
5. **Jadwal Tayang** — slot
6. **YouTube** — pilih koneksi + channel tujuan
7. **Branding & Caption** (opsional)
8. **Kesiapan & Aktivasi** (card terakhir) — checklist 🔴/🟢 tiap syarat + link ke lokasinya; tombol **Aktifkan**
   ENABLED hanya saat **semua 🟢**.

## 2.3 Indikator (D)
- **Daftar channel:** tiap card channel tampil status ringkas (🔴 belum lengkap / 🟢 siap / Aktif / Dijeda / Dihentikan)
  — pakai komponen status bersama (`<ChannelStatusBadge>`, satu sumber, tanpa drift).
- **Channel Setting card "Kesiapan":** tiap syarat 🔴/🟢 + link; aktivasi terkunci sampai semua 🟢.
- Pesan "kurang apa" dari `channel_missing` (dinamis), dipetakan ke kalimat manusiawi + tautan.

---

# §3. PLAN vs REALISASI

Format: tiap fase punya **Plan** (yang akan dilakukan) & **Realisasi** (diisi saat dikerjakan).

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
- **Realisasi:** _(kosong)_

### Fase 6 — FE: Channel Setting (card terpisah + urut §2.2)
- **FE:** `channels/[id]/page.tsx` — pisah jadi card urut: Niche&Format → LLM → TTS → Visual → Jadwal → YouTube
  (pilih `youtube_account_id` + `platform_channel_id`) → Branding → Kesiapan&Aktivasi. Tiap elemen: penyedia→model
  (kunci dari pool, tak isi di sini); link "Lengkapi kunci di Credential" bila pool kosong. Buang checkbox is_active lama.
- **Validasi:** `next build`; ryan tampil benar; pilih penyedia/model jalan.
- **Realisasi:** _(kosong)_

### Fase 7 — FE: indikator 🔴/🟢 + lock konsisten
- **FE:** komponen bersama `lib/channel-status.ts` + `<ChannelStatusBadge>` (pindah `effectiveStatus`); dipakai
  `channels/[id]`, `channels/page.tsx`, `dashboard`. RPC batch `channels_readiness_mine()` (migr) utk daftar.
  Card "Kesiapan": tiap syarat 🔴/🟢 + link ke konfigurasinya; tombol Aktifkan enabled hanya semua 🟢.
  `toggleActive` (daftar) + semua jalur: pre-check readiness, tangkap error DB → pesan ramah (nol error mentah).
- **Validasi:** `next build`; channel belum-lengkap → 🔴 + tombol mati + pesan ramah; lengkap → 🟢 + aktif.
- **Realisasi:** _(kosong)_

### Fase 8 — Onboarding & data existing (jangan putus)
- **FE/BE:** `onboarding/page.tsx` → kunci AI saat onboarding masuk **pool** (`/api/credentials/ai`), channel pertama
  draft non-aktif. Validasi ryan (sudah ter-backfill Fase 2) tetap ready → produksi+publish+analitik jalan.
- **Realisasi:** _(kosong)_

### Fase 9 — Validasi total, deploy, drop fosil (migr `0093_drop_legacy_credentials.sql`)
- **Validasi:** e2e (ryan + 1 channel uji dari nol via onboarding sampai 🟢 & aktif), `next build` PASS, rollback-test semua migrasi.
- **Deploy:** urut aman (DB additif 0091/0092 → kode BE+FE → verifikasi ryan → drop 0093).
- **DB drop (0093):** `channels.{llm,tts,visual}_key_enc`; tabel `channel_credentials`, `tenant_credentials` (setelah pool jalan).
- **Realisasi:** _(kosong)_

---

# §4. DEFINITION OF DONE (kriteria "bungkus" — TUNTAS, nol sisa)

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
7. **Tervalidasi end-to-end**: ryan produksi+publish+analitik jalan; channel baru dari onboarding bisa di-setup
   sampai hijau & aktif; channel belum-lengkap TIDAK bisa aktif (DB tolak).
8. **Fosil di-drop** (kolom/tabel kunci lama) — nol bangkai.
9. **Tak ada bug/error terkait lock/kredensial** setelah deploy (dipantau 1 siklus produksi+publish).

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
