# 🎯 SISA KERJA MENUJU GO-LIVE — Backlog Tunggal + Plan vs Realisasi

> **File ini = SATU-SATUNYA daftar kerja belum-tuntas + progress-nya.** Dibuat 2026-07-01 dari audit menyeluruh (**verified: DB LIVE + kode BE `file:baris` + FE tenant/admin + `git log` + `ssh vps`**). Sesi baru **fokus & eksekusi dari sini** — tanpa audit ulang, tanpa asumsi.
>
> **CARA PAKAI (WAJIB):**
> 1. Ambil item ⬜/🟡 pada kelompok prioritas terendah nomornya (A dulu). Baca **TUJUAN · KONTEKS · BUKTI · PLAN · DONE-BILA**.
> 2. **CEK-ULANG BUKTI dulu** (`file:baris`/query DB) sebelum ubah kode — anchor di sini dari audit 2026-07-01; tetap verifikasi karena kode bisa bergerak. Anchor bertanda **[cek-baris]** = nomor baris dari dokumen sumber, belum di-grep-ulang sesi ini → grep dulu.
> 3. Kerja: **LOKAL → validasi 100% → commit → push → `git pull` VPS + rebuild + restart.** JANGAN ngoding di VPS. JANGAN sentuh v1 (sudah pensiun). JANGAN drop `channels.niche_pool`/`niche_mode` (AKTIF).
> 4. Selesai + tervalidasi → **isi kolom REALISASI** (status + commit + bukti) di item ini. Update juga dokumen SPEC terkait bila perlu.
> 5. Legend status: **⬜ belum · 🟡 sebagian · ✅ selesai+validasi · ⏳ data-gated · 🔒 nunggu keputusan/aksi owner.**
>
> **Sumber kebenaran status = FILE INI.** Dokumen lain (REMEDIASI/CHANNEL_LOCK/QC/TREND/MULTI_FORMAT/DEPLOY_RUNBOOK/CUSTOM_NICHE/ONBOARDING_FUNNEL/**PAYMENT_AND_TENANT_GATE_ARCHITECTURE**/**LIFECYCLE_NURTURE_ARCHITECTURE**) = **SPEC/ARSIP** (rujuk untuk detail arsitektur; jangan pakai marker `[ ]` mereka sbg daftar kerja).
>
> **🔗 RANTAI KANONIK BILLING & SIKLUS-HIDUP (jangan miss-link):** `SISA_KERJA` (backlog/status = **HUB**) → **`PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`** (arsitektur bayar Midtrans + gate `trial→active→grace→suspended`; **SELESAI + deployed `04cf0a2`**) → **`LIFECYCLE_NURTURE_ARCHITECTURE.md`** (LANJUTAN: nurture trial-lapse + dunning `suspended→blocked→deleted`+hapus-data; **rencana, belum build**). Pemetaan item: **[A1]/[E1]** (Midtrans) → PAYMENT · **[B8]** (/feedback) + **[B9]** (mesin siklus-hidup) → LIFECYCLE · **[D1]** (funnel) ⟷ LIFECYCLE.

---

## 🧭 §0. UNTUK SESI BARU — BACA INI DULU (peta sistem + akses; agar nol asumsi)

**Urutan paham (5 menit) sebelum eksekusi:**
1. **Framing v1/v2** → memory `decisions_v1_v2_migration`: v1 = mesin lama (PENSIUN). v2 = yang kita kerjakan, **LIVE di VPS** (`mesinviral.com`). DB v2 sendiri.
2. **Model produk** (JANGAN keliru): **1 user = 1 tenant = MULTI channel** (kuota `plan_limits`: starter 1/pro 3/business 10). **NICHE = DNA konten** (voice/visual/musik/narasi — dibuat admin atau Business niche-studio). **CHANNEL = brand-skin + operasional** (caption/hashtag/bahasa/logo + pilih AI-model+voice+akun). **TENANT = akun** (plan/billing/kredensial). Detail: memory `decisions_niche_owns_content_config` + `decisions_niche_model`.
3. **Cara mesin jalan** (BUKAN cron — 1 proses `scripts/worker_decoupled.py`, 7 thread): **PRODUCER** (loop, jaga stok buffer `content_inventory`, TAK publish) → **PIPELINE** (`orchestrator/pipeline.py`: script→hook→prompt-gambar→TTS→visual→render→QC) → **PUBLISHER** (loop, saat slot `channels.publish_slots` due → ambil `ready` tertua → upload YouTube → tulis `videos`+`production_runs`) → **self_learning** (analytics→`channel_insights`). Peta tabel/fosil TERVERIFIKASI = memory `reference_be_pipeline_tables_fossils`. Bisnis/pricing = `DESAIN_PRODUK_SAAS.md`.
4. **Kredensial (model POOL, FINAL)**: kunci AI di `tenant_ai_accounts` (per-vendor `key_group`), koneksi YouTube di `tenant_youtube_accounts`, channel tunjuk via `channels.{llm,tts,visual,youtube}_account_id`. `.env` = HANYA platform. Detail = `CHANNEL_LOCK_ACTIVATION_PLAN.md`.

**Akses (verified — pakai via tindakan, jangan asumsi tak-bisa):**
- **DB v2**: psycopg2 pooler `aws-1-ap-southeast-1.pooler.supabase.com:5432`, db `postgres`, user `postgres.atliatnjhysdibmfypul`. **Password** = di `SUPABASE-CONNECTION.md` (gitignored) atau skrip `scratchpad/apply_*.py` lama. **JANGAN print password di chat** (redact `sed -E 's/Rad@[0-9]*/***/g'`).
- **VPS**: `ssh vps` (alias; `rad4vm@103.103.22.227`, key `~/.ssh/vps_key`). Repo worker `~/viral-machine-v2`, FE `~/mesinviral-web`. Service `mv-worker`/`mv-web`/`mv-webhook`. Log worker = `~/viral-machine-v2/worker.log` (bukan journald) — memory `reference_vps_logs`.
- **S3** (aset/video/logo) = Biznet bucket `mesinviral-assets`, kredensial `S3-CONNECTION.md`. Supabase = DB saja.
- **Repo lokal** = `/home/rad/viral-machine`, branch `v2-backend`. FE = `apps/web` (Next.js 16; `npm --prefix apps/web run build`). `.md` di-exclude dari VPS (sparse-checkout).

### 🎯 VISI / MISI (WAJIB paham — arah tiap keputusan) — sumber: `DESAIN_PRODUK_SAAS.md §1/§8/§9` + memory `project_vision`
- **Tagline/misi:** *"Mesin produksi konten YouTube Shorts otomatis yang **belajar dari channelmu sendiri**."* Untuk **faceless creator (Indonesia-first)** yang mau scale ke 5+ video/hari — video viral-grade harian + adaptasi real-time dari analytics channel mereka.
- **3 pembeda / MOAT:** (1) **BYOK transparan** (tenant bawa kunci AI sendiri, tanpa vendor lock-in, jauh lebih murah/video) · (2) **Self-learning loop** dari YouTube Analytics post-publish (tak ada kompetitor lakukan — moat 12-18 bln) · (3) **Indonesia-first** (UI ID, Midtrans, niche kurasi, concierge).
- **Prinsip NON-NEGOTIABLE:** kualitas>kuantitas (lebih baik tak produksi daripada jelek) · **no silent degradation** (gagal→tenant tahu via Telegram+dashboard) · **diversity/compliance-first** (bertahan dari YouTube AI-slop crackdown Jan 2026 = **PILAR SURVIVAL**, bukan opsional) · self-learning · **almost fully config-driven (no-hardcode)** · transparansi (BYOK + biaya AI terlihat + log auditable).
- **⭐ TUJUAN OWNER = SEGERA JUALAN (go-to-market).** Ukuran "SELESAI" yang BENAR = **produk bisa DIJUAL ke tenant baru**, BUKAN menyempurnakan internal/ryan. Pertanyaan pemandu tiap saat: *"apakah ini memblok tenant berbayar pertama?"* Tidak → DEFER (pasca-launch). STOP rabbit-hole perfeksionisme. (memory `project_audit_setup_gaps_2026_06_23`)

### 📏 ATURAN KERJA LENGKAP — 18 memory (WAJIB patuh; tiap `[[...]]` = file memory) — pelanggaran = ditegur owner
**A. Sebelum bertindak — paham & disiplin**
1. **[[feedback_comprehend_before_work]]** ⛔ — paham **1000%** peta (DB/BE/FE/koneksi/progress/prioritas) SEBELUM menyentuh apa pun. Darurat = containment dulu, baru diagnosa (jangan menebak komponen).
2. **[[feedback_post_compaction]]** — pasca-compaction JANGAN "bayi baru lahir": percayai summary+memory, baca URUTAN KANONIK berurut, tulis peta-state, lanjut thread aktif — jangan re-investigasi yang sudah jelas.
3. **[[feedback_analysis_discipline]]** — **NOL asumsi.** Trace end-to-end dgn angka nyata; baca kode sebelum klaim; **build PASS ≠ running well** (validasi RUNTIME sebelum klaim selesai).
4. **[[feedback_master_docs_first]]** — kuasai dokumen dulu; **GROUND TRUTH = KODE + DB LIVE** (dok bisa drift/aspiratif — jangan kutip dok sbg bukti perilaku); kontradiksi→terbaru+konfirmasi; hormati banner "JANGAN ANALISA ULANG"; FE = referensi backend.
5. **[[feedback_review_whole_remediation_before_item]]** 🔗 — sebelum kerjakan 1 item: review SELURUH dokumen terkait + cek DEPENDS + item yang menumpang seam (hindari rework).

**B. Cara memutuskan & komunikasi**
6. **[[feedback_workflow]]** — **propose dulu + tunggu approval** untuk perubahan; saat ditanya: jawab+opsi+rekomendasi+tunggu konfirmasi (jangan langsung bongkar kode).
7. **[[feedback_owner_delegates_expert_decisions]]** — owner delegasi teknis: putuskan yang reversible/jelas; **propose untuk yang berisiko/fork bisnis**. North-star = produk **LAKU + skala ribuan tenant + viral NYATA**.
8. **[[feedback_plain_language]]** 🗣️ — owner **non-teknis**: bahasa dampak bukan mekanisme; nol jargon; status = checklist sederhana.
9. **[[feedback_no_silent_ui_changes]]** 🚫🎨 — JANGAN tambah/ubah/hapus elemen UI tanpa izin owner. Tugas BE/logika = ubah itu SAJA; usul dulu bila perlu UI.
10. **[[feedback_define_done_no_scope_creep]]** — tarik garis tegas **SELESAI / poles-opsional / wajib-jualan**; defer opsional; menjelaskan ≠ tugas baru; jangan bingkai follow-up sbg "cacat".

**C. Standar kualitas & teknis**
11. **[[feedback_world_class_quality]]** 🏆 — DB/BE/FE semua TERBAIK; reuse/relokasi UI bagus yang ada (jangan bikin lebih jelek); nol-duplikat; "selesai" = kualitas + lama-dibereskan + tervalidasi.
12. **[[feedback_no_hardcode]]** — AI/pricing/business = config-driven (`pricing_config`/`app_config`/DB); no silent fallback (gagal→stop+notify); nol literal nominal/model di kode.
13. **[[feedback_design_for_multichannel_scale]]** — asumsi default **tenant MULTI-channel**; atribusi data **per-entitas** (per-video/run), bukan "channel tenant"; ryan (1 channel) = test, bukan patokan.
14. **[[feedback_all_assets_on_s3]]** 🗄️ — semua aset/media di **S3** (`mesinviral-assets`); Supabase = DB saja. **JANGAN keputusan biaya/infra tanpa izin owner.**

**D. Validasi & deploy**
15. **[[feedback_local_test_batch_deploy]]** ⚡ — validasi PENUH di LOKAL (dev box mampu render-test/build/DDL); deploy VPS **1× di akhir task** (rebuild FE VPS lambat), jangan per-langkah.
16. **[[feedback_vps_clean]]** — VPS = runtime bersih (`.md` di-exclude sparse-checkout); alur lokal→commit→push→`git pull` VPS+restart.
17. **[[feedback_vps_ssh_long_commands]]** — perintah VPS lama/menunggu = **detached + poll** (SSH nganggur diputus→error 255); jangan foreground.
18. **[[feedback_f4_locked_gate]]** — *(GERBANG SUDAH TERBUKA — F4 durasi SELESAI `8670fc3`)*; prinsip tetap: durasi = hulu, hilir rusak bila hulu meleset.

**⛔ PANTANGAN keras:** JANGAN sentuh v1 (pensiun; arsip+DB disimpan) · JANGAN drop `channels.niche_pool`/`niche_mode` (AKTIF) · JANGAN ngoding di VPS.

---

## 📸 SNAPSHOT KONDISI LIVE (verified 2026-07-01 — baseline; JANGAN kerjakan ulang)
- **v2 LIVE di VPS**, v1 PENSIUN. `mv-web`+`mv-worker`+`mv-webhook` = **active**. `mesinviral.com`=200, `/api/youtube/oauth/callback`=302. Worker HEAD `8d44f01`, web HEAD `ee01575`, branch `v2-backend`, migrasi terakhir ~0107.
- **Mesin produktif**: `videos`=273 (185 published), `production_runs`=130. 2 channel (ryan aktif, kumala belum lengkap).
- **DB v2** = `atliatnjhysdibmfypul` (pooler `aws-1-ap-southeast-1.pooler.supabase.com:5432`, user `postgres.atliatnjhysdibmfypul`). Migrasi via psycopg2 pooler.
- **SUDAH SELESAI & LIVE (terbukti — nol re-work):** wiring FE Phase 9-10 (tenant+admin) · kredensial **model POOL** (`tenant_ai_accounts` key_group + `tenant_youtube_accounts`; channel `*_account_id`; fosil `tenant_credentials`/`channel_credentials`/`channels.*_key_enc`/`token_path` DI-DROP migr 0090/0095) · **lock aktivasi** (trigger `channels_activation_gate` BEFORE INSERT/UPDATE, fungsi `channel_missing`) · config per-channel + voice per-channel (migr 0082/0083) · **Cacat-B durasi-via-speed** (F4, `8670fc3`, migr 0078/0079) · image-gen per-preset 2-tahap + VISUAL DNA (`e964a9e`) · trend cache (0048)+source_weights (0049)+YouTube velocity · self-learning loop (`viral_score_weights` hidup, `21f41fe`) · niche/hashtag remediasi (BATCH 1-5) · **alur custom-niche A-Z** (`e263e1a`, concierge/manual) · niche origin (studio/request/admin) · OAuth PLATFORM Google (`GOOGLE_CLIENT_ID/SECRET` .env; ryan verified) · compliance/AI-slop defense (DiversityEngine + ComplianceScorer + ai_disclosure) · onboarding credential-first (setup 2-langkah) · bersih FE (notif/config/danger dihapus, Pustaka Niche).
- **Peran:** owner = konsep/bisnis + gate eksternal; Claude = detail teknis. Ryan = tenant test (grandfathered). **Acceptance sebenarnya = tenant BARU dari nol.**

---

# 🔑 KELOMPOK A — GATE EKSTERNAL / OWNER *(SATU-SATUNYA pemblokir MULAI JUALAN)*
> Hanya owner yang bisa eksekusi (butuh dashboard/akun/browser); Claude siapkan materi + pandu. Spec: `PROGRESS.md §GATE CUTOVER` + `DEPLOY_RUNBOOK.md` + `GOOGLE_OAUTH_PLATFORM_MIGRATION.md`.

### [A1] Midtrans PRODUKSI — 🔒⬜ *(PEMBLOKIR UTAMA JUALAN)*
- **TUJUAN:** tenant bisa BAYAR sewa (subscription) + add-on custom-niche → uang masuk.
- **KONTEKS:** BE pembayaran (Snap redirect) SUDAH jadi & lulus e2e sandbox — `src/billing/midtrans.py` (`snap_create_transaction` env-driven sandbox/prod · `verify_signature` SHA512 · `handle_notification`→aktivasi), tabel `payments` (migr 0022), webhook route di `mv-webhook`. **Arsitektur lengkap = `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`.** ⚠️ **Switch sandbox↔production = ubah `MIDTRANS_ENV` di `.env` + restart** (§3.2 doc; BUKAN tombol admin — tombol itu = [B1], belum ada). **✅ Verified 2026-07-02: kunci PRODUKSI Server+Client SUDAH ADA di `.env` VPS (format `Mid-server-`/`Mid-client-` valid) + merchant dibagi dgn aiwa yang SUDAH LIVE produksi → merchant approved.** Jadi [A1] ≈ **flip `MIDTRANS_ENV=production` + restart + 1 transaksi konfirmasi** — bukan "cari kunci". Pemblokir tersisa = KEPUTUSAN owner KAPAN go-live (idealnya bareng [A2]✓ + [A4] verifikasi Google + [A5] smoke-test).
- **BUKTI kondisi sekarang (verified DB 2026-07-01):** `payments`=**0 baris**; `.env` `MIDTRANS_ENV`=sandbox. → produksi belum pernah jalan. **Verified 2026-07-02 (VPS `.env`):** `MIDTRANS_PRODUCTION_SERVER_KEY`+`_CLIENT_KEY` **ADA & format valid** → kunci produksi SIAP; tinggal flip+restart+konfirmasi.
- **PLAN (aksi owner + Claude bantu):**
  - Owner: dapatkan **Server key + Client key PRODUKSI** Midtrans; isi ke `.env` VPS + `MIDTRANS_ENV=production`; daftar **Notification URL** (payment/recurring/pay-account) + Finish/Error URL → `https://mesinviral.com/api/webhooks/midtrans`.
  - Claude: verifikasi route webhook `mv-webhook` menerima notifikasi prod; restart `mv-webhook`+`mv-worker` (baca env baru).
- **DONE-BILA:** 1 transaksi nyata (sandbox→prod) → webhook masuk → `payments` terisi + `tenant_configs.subscription_status`→active. FE Billing tombol Snap enabled (kini disabled+note gate).
- **DEPENDS:** — (BE siap). **Nyambung:** [E1] add-on custom-niche.
- **REALISASI:** ⬜ *(belum; gate owner)*

### [A2] Supabase Auth — SMTP + Google provider — ✅ *(validated 2026-07-01)*
- **TUJUAN:** email auth (verify/reset) ber-brand + terkirim andal; "Daftar dengan Google" jalan untuk tenant publik.
- **KONTEKS:** kode auth (signup/verify/reset/OAuth callback) SUDAH jalan (Phase 9.1, runtime-validated). Kurang = konfig dashboard Supabase.
- **BUKTI:** reset email dulu kena rate-limit default Supabase (bukan bug kode); Google provider status di dashboard = belum aktif. SMTP tersedia (`mail.lumite.biz.id:465`, di `S3-CONNECTION.md`).
- **PLAN (aksi owner):** Supabase Dashboard `atliatnjhysdibmfypul` → Authentication → (1) **custom SMTP** `mail.lumite.biz.id` (host/port/user/pass/from) · (2) **Google provider** = Client ID/Secret app lumite (`153190496639-i41l1fp3...`).
- **DONE-BILA:** signup email verify terkirim ber-brand; "Daftar dengan Google" e2e sukses (redirect `mesinviral.com`, bukan localhost — bug ini sudah fix `a18d451`).
- **REALISASI:** ✅ **SELESAI + VALIDATED 2026-07-01** (owner setting di dashboard Supabase; Claude validasi otomatis dari server, bukan tebakan). (1) **Custom SMTP lumite** dibuktikan END-TO-END: trigger `POST /auth/v1/recover` (200) → email masuk inbox `mesinviral@lumite.biz.id` (dibaca via IMAP) dgn **From: `Mesin Viral <mesinviral@lumite.biz.id>`** (bukan `noreply@…supabase.io`) → SMTP lumite aktif & dipakai Supabase. (2) **Google provider** valid: `GET /auth/v1/authorize?provider=google` → 302 ke `accounts.google.com` dgn `client_id=153190496639-i41l1f…` (app lumite) + `redirect_uri=…supabase.co/auth/v1/callback` benar + scope `email profile` → provider aktif & terwire benar. Yang TAK-testable headless = klik-pilih-akun interaktif utk PUBLIK (butuh browser + app di Production) → menyusul saat **[A4] publish**; selama Testing hanya test-user (normal). Catatan minor (poles opsional, non-blocker): template email auth Supabase masih bhs Inggris ("Reset your password"). **Investigasi link-reset 2026-07-01 (owner lapor "link tak benar"):** alur RESET dari SITUS (PKCE) TERBUKTI benar — verify → `…/auth/callback?code=…&next=%2Fauth%3Fview%3Dreset` → callback `exchangeCodeForSession` (route.ts:33-36) → form set-password (same-device OK). Gejala owner = klik EMAIL TES raw-API (tanpa PKCE → jatuh ke beranda/fragment `#access_token` yg tak terbaca server), BUKAN alur situs. ⚠️ **KELEMAHAN NYATA (hardening, non-blocker):** PKCE reset gagal **LINTAS-ALAT** (minta di laptop, buka email di HP → tak ada code_verifier → "link tidak valid"). ✅ **DIBERESKAN 2026-07-01 (commit `db3d859`, deployed + LIVE-validated) — world-class in-code:** reset email kini **DIKIRIM SENDIRI oleh mv-web** (bukan Supabase): route `/api/auth/forgot-password` → `admin.generate_link` (service_role) → link **`token_hash`** → `/auth/callback` `verifyOtp` → **JALAN DI SEMUA ALAT** (tak butuh browser asal; PKCE dibuang utk reset). Template email **ID/EN ber-brand di kode** (`apps/web/src/lib/email/templates.ts`) + pengirim SMTP (`smtp.ts`, nodemailer, config env, anti-enumeration). **Template Supabase reset TAK dipakai lagi.** Validasi LIVE (nol asumsi): POST→email brand `mesinviral@lumite.biz.id`→link `mesinviral.com/auth/callback`→callback 307 `/auth?view=reset` (nol error). **Konfirmasi SIGNUP:** template ID/EN SUDAH dibuat (siap), tapi **wiring MENYUSUL** — signup masih `supabase.auth.signUp` (template Supabase); wiring butuh cek dulu setelan Supabase "Confirm email" (nol asumsi) → item berikutnya.

### [A3] Rotasi semua secret dev — 🔒⬜
- **TUJUAN:** secret yang dipakai saat dev tidak bocor ke produksi publik.
- **PLAN:** rotate: DB password (`Rad@...` → baru; update `.env` + semua skrip), `SUPABASE` service_role + anon, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET` (worker==mv-web WAJIB sama), `SMTP_*`, `MIDTRANS_*`, ElevenLabs key ryan. Update `.env` VPS + `.env.local` mv-web + restart.
- **DONE-BILA:** semua service tetap jalan dgn secret baru; secret lama invalid.
- **DEPENDS:** paling akhir sebelum publik (agar tak rotate 2×). Terkait [B1] (system-secrets bisa jadi tempat kelola).
- **REALISASI:** ⬜

### [A4] Verifikasi Google app + kumala reconnect — 🔒⬜
- **TUJUAN:** pelanggan asing lihat brand MesinViral (bukan warning "unverified"); refresh-token permanen (bukan kedaluwarsa 7 hari mode Testing).
- **KONTEKS:** materi SIAP di `GOOGLE_OAUTH_PLATFORM_MIGRATION.md` — justifikasi scope (§8a, 3 scope: youtube.upload/readonly/yt-analytics.readonly), shot-list demo video (§8b), `/privacy`+`/terms` sudah LIVE & patuh. Scope SENSITIVE (bukan Restricted → tanpa CASA berbayar).
- **PLAN (aksi owner):** Google Auth Platform (akun `lumite.biz.id@gmail.com`, project `mesin-viral`) → Publish app (Testing→Production) → Verification Center → submit (justifikasi §8a + demo video §8b). Timeline ~10 hari. ~~+ kumala reconnect~~ → **kumala reconnect YouTube = ✅ SELESAI (owner konfirmasi 2026-07-01)**. Sisa A4 = HANYA Langkah 9 (publish + submit verifikasi).
- **DONE-BILA:** app verified (warning hilang, token permanen).
- **REALISASI:** ⬜ *(gate owner; Claude bisa bantu rekam demo/teks)*

### [A5] Smoke-test live end-to-end (tenant baru dari nol) — 🔒⬜
- **TUJUAN:** bukti acceptance utama CHANNEL_LOCK — tenant BARU (bukan ryan) bisa jalan penuh.
- **PLAN (owner + Claude):** signup tenant uji baru → `/integrations` isi kunci AI + connect YouTube (OAuth consent 1× nyata di browser) + Telegram → `/channels/[id]` set niche/model/voice/jadwal → semua 🟢 → Aktifkan → produksi + publish + analytics jalan. + transaksi Midtrans 1× + email egress dari VPS.
- **DONE-BILA:** tenant baru sampai aktif + 1 video publish + bayar — mulus, nol error mentah.
- **DEPENDS:** A1, A2, A4.
- **REALISASI:** ⬜ *(butuh browser owner untuk OAuth consent)*

### [A6] Email deliverability ke EKSTERNAL — ✅ *(RESOLVED 2026-07-02: SPF fix owner + Message-ID/Date fix kode → app-email MASUK INBOX Gmail, verified)*
- **TUJUAN:** email transaksional (verifikasi daftar, reset password, nurture, tagihan) **sampai inbox pelanggan Gmail/eksternal**, bukan bounce.
- **BUKTI (bounce Gmail 550-5.7.26, verified):** kirim ke `kumala.rw22c@gmail.com` DITOLAK — *"sender is unauthenticated… DKIM = did not pass … SPF [lumite.biz.id] with ip: [103.193.179.117] = did not pass"*. Relay keluar = `relay.idcloudhost.com` (`103.193.179.117`) yang **TIDAK ada di SPF** lumite (SPF cuma `103.76.121.147/180`+`103.123.62.104`+antispamcloud) + DKIM `default` terpublish tapi relay tak menandatangani lumite dgn selector itu. Kirim ke lumite-internal (mesinviral@lumite) "berhasil" karena tak lewat cek-auth Gmail → menyesatkan.
- **DAMPAK:** SEMUA email ke pelanggan nyata (mayoritas Gmail) bounce → memblok signup/verify/reset/billing. Sistem/kode BENAR; ini murni DNS/mail-domain (kendali owner).
- **✅ SOLUSI PASTI (verified 2026-07-02):** akar = relay keluar `relay.idcloudhost.com` (`103.193.179.117`) TAK ada di SPF lumite; `include:spf.antispamcloud.com` juga tak memuatnya. **`spf.idcloudhost.com` = `v=spf1 ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148 ~all`** (memuat relay). **FIX: edit TXT SPF lumite.biz.id (cPanel→Zone Editor, BUKAN tombol Repair yg melewatkan smarthost)** → tambah `ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148` (atau `include:spf.idcloudhost.com`). SPF-only cukup (Gmail: SPF OR DKIM). Record final: `v=spf1 ip4:103.76.121.147 ip4:103.76.121.180 ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148 include:spf.antispamcloud.com +a +mx +ip4:103.123.62.104 ~all`. DKIM (d=lumite.biz.id ditandatangani tapi gagal verifikasi — selector/kunci tak selaras) = poles terpisah utk DMARC. Opsi world-class: provider transaksional (SES/SendGrid/Postmark). Claude uji-ulang pasca-propagasi.
- **DONE-BILA:** kirim ke Gmail → masuk inbox, header SPF=pass & DKIM=pass, nol bounce.
- **DEPENDS:** — (mandiri, DNS). **Nyambung:** [A2] auth email · [A5] smoke-test · [B9] nurture · [A1] tagihan.
- **✅ RESOLVED — AKAR SEBENARNYA (verified INBOX 2026-07-02, commit `ebb5d90`, deployed mv-worker):** DUA sebab, keduanya beres:
  **(1) SPF** — relay `relay.idcloudhost.com` (103.193.179.117) tak terdaftar → owner tambah `103.193.179.117/147/148` ke SPF → Gmail **SPF=pass, DMARC=pass** (via SPF; walau DKIM=fail). **(2) CACAT KODE** — `email.py::send_email` membangun pesan **TANPA `Message-ID`+`Date`** (RFC 5322) → Gmail buang diam-diam sbg malformed (webmail Roundcube sampai karena header lengkap; email app cuma 632 byte). Fix `ebb5d90`: `make_msgid`+`formatdate` (domain selaras From). **Verified: `notify_payment_receipt` + tes → MASUK INBOX kumala** (bukan spam). Header Gmail email Roundcube membuktikan spf=pass/dmarc=pass/dkim=fail.
  ⚠️ **KOREKSI catatan lama saya:** kesimpulan *"app-mail mati di outbound idcloudhost"* + *"provider transaksional WAJIB"* = **SALAH/keras-kepala**. Penyebab nyata = **cacat header di kode kita sendiri** — bisa & sudah diperbaiki tanpa provider. **DKIM=fail (relay) = poles OPSIONAL** (penempatan-inbox lebih baik / DMARC-strict), non-blocker. Provider transaksional = peningkatan reputasi jangka-panjang, **bukan keharusan**. Pelajaran: bila OUTPUT APLIKASI kita gagal, **periksa output kita sendiri (byte/header) DULU** sebelum menyalahkan infra. [[feedback_inspect_our_output_before_blaming_infra]]
- **REALISASI (2026-07-02):** 🟢 **BOUNCE TERATASI** — owner tambah 3 IP relay idcloudhost ke SPF (`103.193.179.117/147/148`) + TTL→300. Verified: uji ke `kumala.rw22c@gmail.com` (tag MVCHECK/recheck) → **NOL bounce** = Gmail TERIMA (SPF lolos). 🟡 **TAPI masuk Spam/Promosi, bukan Inbox** (kumala lapor tak lihat di Inbox) — sebab **DKIM masih gagal** (sig `d=lumite s=default`, kunci `default._domainkey` terpublish TAPI Gmail "DKIM did not pass" → kunci publik tak cocok dgn yg dipakai relay/SpamExperts menandatangani ulang) + reputasi domain baru. **SISA (agar INBOX, penting utk verify/reset/tagihan pelanggan):** (a) mark "Not spam" + reputasi, (b) perbaiki DKIM via support idcloudhost (relay invalidasi tanda tangan), **atau (c) ⭐ pakai provider transaksional (SES/SendGrid/Postmark) = solusi world-class andal utk SaaS.** Keputusan (c) = owner (biaya/infra); Claude siap integrasi bila disetujui.

---

# 🛠️ KELOMPOK B — DEV *(Claude kerjakan; pasca-launch/hardening — TIDAK memblok jualan)*

### [B1] System-secrets admin panel (S1-S4) — ⬜
- **TUJUAN:** secret operasional (Midtrans/SMTP/S3/YouTube-platform-key) editable + rotatable dari admin panel, bukan hanya file `.env`.
- **KONTEKS/BUKTI (verified DB 2026-07-01):** tabel **`system_secrets` TIDAK ADA**; semua secret operasional dari `.env` (interim sah). Spec lengkap = `PROGRESS.md §ADMIN SYSTEM SECRETS`.
- **PLAN:**
  - **S1 (DB):** migr `system_secrets` (`key` PK, `value_enc` Fernet, `category`, `updated_by`, `updated_at`) — RLS **service-role only** (pola `tenant_ai_accounts`). Update `DB_SCHEMA_V2.md`.
  - **S2 (BE):** `src/config/system_secrets.py` — baca DB (Fernet decrypt) → **fallback env** (transisi mulus). Worker/webhook pakai untuk **Kategori A** (Midtrans/SMTP/S3/`YOUTUBE_PLATFORM_API_KEY`/opsional `OAUTH_STATE_SECRET`).
  - **S3 (FE admin):** `/admin/integrations` (service-role, `requireSuperAdmin`) — status set/kosong (masked) + set/rotate + **"Test koneksi"** (reuse pola Test Lab) + audit→`admin_audit`. **Kategori B read-only** (env-managed: `ENCRYPTION_KEY`/service_role+DB-pw/`MV_INTERNAL_SECRET` — chicken-egg, TAK bisa di-DB).
  - **S4:** seed nilai env→DB + validasi (worker baca DB; rotate dari panel berlaku; restart-safe).
- **DONE-BILA:** admin set/rotate secret Kategori A dari panel → worker pakai nilai baru tanpa edit file; Kategori B ditolak edit.
- **REALISASI:** ⬜

### [B2] Cost-tracking REAL per-konten (BYOK) — ⬜
- **TUJUAN:** tampilkan biaya produksi VALID per-video (REAL dari pemakaian), label "biaya provider AI/BYOK — bukan biaya kami". Spec = REMEDIASI **F5-03**.
- **BUKTI kondisi sekarang:** tak ada cost-tracking. Satu-satunya harga = `ai_models.cost_hint` (admin-editable). GAP: (a) adapter LLM `complete()` tak kembalikan token usage; (b) `tts_profiles` tanpa cost_hint; (c) `production_runs` tanpa kolom cost (cuma `run_metadata` jsonb). FE = "Biaya AI coming-soon".
- **PLAN:** (1) adapter LLM (anthropic+openai) kembalikan `usage{input,output tokens}`; pipeline kumpulkan per run. (2) tangkap jumlah gambar (=visual_beats) + karakter TTS. (3) DB: `tts_profiles +cost_hint` (per-char); simpan biaya aktual `production_runs.run_metadata.cost` (breakdown llm/image/tts). (4) hitung Σ. (5) FE kartu "Biaya AI" (dashboard) + kolom Runs — REAL pasca-produksi (ganti coming-soon), label BYOK.
- **DONE-BILA:** tiap run baru tulis biaya breakdown nyata; FE tampil per-konten.
- **REALISASI:** ⬜

### [B3] Sapu hardcode sisa — ⬜  (REMEDIASI **F5-02**)
- **TUJUAN:** nol hardcode kritis; semua config-driven.
- **PLAN + anchor [cek-baris] (grep dulu):** Ken-Burns motion per-role/zoom `ai_image.py:~417-463` → `niches.motion_profiles` (kolom baru) · `BASE_NICHE_TIERS` `billing/limits.py:~59` → `app_config` · `OPTIMAL_PUBLISH_SLOTS` `tenant_config.py:~82-88` → `app_config`.
- **DONE-BILA:** grep hardcode kritis bersih; perilaku produksi identik (uji ryan).
- **REALISASI:** ⬜

### [B4] Pivot Analytics FE → kinerja-mesin — ⬜  (REMEDIASI **F5-05**)
- **TUJUAN:** `/analytics` jangan duplikat YouTube Studio; fokus KINERJA MESIN (success-rate/QC/durasi trend, self-learning niche/hook, biaya per-konten) + link YT Studio.
- **BUKTI:** `/analytics` kini mayoritas re-display YT-mentah (RPC overview/by_niche/monthly/top_videos) = redundan Studio. Arsitektur BE benar (`performance_analyzer`→`channel_insights` = pola mesin).
- **PLAN:** pivot FE `/analytics` ke metrik mesin + retensi/engagement sbg efektivitas mesin; raw views/likes → link Studio. `channels/[id]` sudah link Studio.
- **DONE-BILA:** nol re-display YT-mentah redundan; ryan tetap tampil benar.
- **REALISASI:** ⬜

### [B5] Sapu fosil inert — ⬜
- **BUKTI (verified 2026-07-01):** `channels.production_cron` (kolom masih ada; dimuat ke dataclass `tenant_config.py:539` tapi v2 pakai loop+`publish_slots`, TAK menjadwalkan) · tabel `pipeline_queue` (ADA tapi cuma disebut di komentar `producer.py:92,269`, tak dibaca). ⚠️ **`channels.niche_pool`/`niche_mode` = AKTIF, JANGAN drop.**
- **PLAN:** setelah pastikan nol pembaca (grep) → migr drop `production_cron` + evaluasi drop `pipeline_queue`. Hati-hati, nilai rendah — kerjakan hanya bila bersih.
- **DONE-BILA:** kolom/tabel fosil hilang, nol regresi.
- **REALISASI:** ⬜

### [B6] ai_video 8s (render mode text-to-video) — ⬜ *(DITUNDA)*
- **BUKTI (verified):** file `src/production/ai_video.py` **TIDAK ADA**; `visual_mode='ai_video:*'` belum jalan. Preset 8s butuh ini.
- **PLAN:** bangun provider text-to-video (BYOK: Kling/Runway/Luma/Veo/Sora — 9:16, 5-8s, async) + integrasi `visual_assembler` (branch single-clip, skip xfade) + `video_renderer` (durasi sync). Spec `MULTI_FORMAT_STUDIO.md §5`. Adapter via registry F5-06 yang sudah ada.
- **DONE-BILA:** preset 8s produksi 1 klip ai_video + audio + publish.
- **REALISASI:** ⬜ *(prioritas rendah; 8s bukan preset utama)*

### [B7] Go-live checklist teknis — ⬜  (REMEDIASI **F5-04**)
- **PLAN:** regression e2e semua preset × beberapa niche × multi-channel; **regenerate `DB_SCHEMA_V2.md`** (stale berhenti ~0043; live ~0107 — jauh beda) via psycopg2 introspeksi; pastikan ryan stabil.
- **DONE-BILA:** semua hijau; `DB_SCHEMA_V2.md` cocok DB live.
- **REALISASI:** ⬜

### [B8] Halaman `/feedback` (masukan trial-lapse) — perbaiki link MATI di email — ✅ *(SELESAI + LIVE-validated 2026-07-03)*
- **TUJUAN:** tenant yang trial habis (dan siapa pun penerima email trial-lapse) punya halaman masukan NYATA ber-brand → kumpulkan alasan tak-upgrade (lead insight berharga) + hilangkan kesan buruk link mati. **Keputusan owner 2026-07-01: Opsi B (halaman sendiri, bukan Google Form).**
- **KONTEKS:** email `notify_trial_lapse` (`src/utils/email.py:92-101`) mengajak isi survei ke `_survey_url()` → default `https://mesinviral.com/feedback` (`email.py:72-73`), TAPI rute `/feedback` **TIDAK ADA** di FE → **404 LIVE** ke tenant nyata (dilaporkan owner: email trial-lapse yang diterima). Trial-expired ditandai **LEAD marketing** (`billing/renewal.py:49`) → masukan ini punya nilai bisnis. Kata "feedback" lain di FE hanya copy marketing (`(marketing)/page.tsx:168`) + widget docs "Apakah artikel ini membantu" (`docs/page.tsx:47`) — **bukan** halaman.
- **BUKTI (verified 2026-07-01):** `curl -L https://mesinviral.com/feedback` → **HTTP 404**. `find/grep apps/web/src/app` → nol rute `/feedback`. Saklar `TRIAL_SURVEY_URL` sudah ada (env-override, default arahkan ke halaman ini → nol perubahan email saat halaman hidup).
- **PLAN (world-class; propose rincian sebelum koding — [[feedback_workflow]] + [[feedback_world_class_quality]]):**
  - **FE:** halaman **publik** `/feedback` (marketing group — penerima email mungkin belum login) — form ber-brand: alasan belum upgrade (pilihan terkurasi + isian bebas) + pesan + email (prefill bila token/login) + i18n ID/EN (pola Bi seperti halaman lain). Sukses → state terima-kasih (bukan reload). Reuse komponen/kelas UI yang ada (jangan bikin versi lebih jelek).
  - **Atribusi:** email sisipkan token/ref tenant (mis. `?ref=<token>`) agar masukan terhubung ke lead/tenant tanpa tenant mengetik ulang.
  - **DB (no-hardcode, RLS service-role):** simpan submission — putuskan saat propose: perluas `leads` (trial-expired sudah lead) ATAU tabel `feedback_submissions` dedicated. Update `DB_SCHEMA_V2.md`.
  - **Notifikasi + admin:** Telegram admin saat masuk + tampil di admin panel (reuse pola **Leads** `/admin`, Phase 10.1) — jangan bikin subsistem duplikat.
  - **Email:** pertahankan `TRIAL_SURVEY_URL` (default kini VALID) → link email otomatis hidup, nol link mati.
- **DONE-BILA:** klik link di email trial-lapse → halaman `/feedback` hidup (bukan 404); kirim masukan → tersimpan di DB + admin bisa lihat + Telegram masuk; email tetap arahkan ke sini.
- **DEPENDS:** — (mandiri). **Nyambung:** admin **Leads** (Phase 10.1), email `notify_trial_lapse`; halaman ini **di-reuse [B9] LIFECYCLE** utk feedback 1-klik (`?reason=`).
- **REALISASI:** ✅ **SELESAI + LIVE-validated 2026-07-03** (commit `3927c41`). Verifikasi menemukan 2 gap → keduanya DIBERESKAN: (1) **Notif Telegram admin saat masukan masuk** (sebelumnya TIDAK ADA): method `TelegramNotifier.notify_admin_feedback` (reuse `notify_admin` → `company_profile.admin_telegram_chat_id`) + endpoint internal `webhook_app` `POST /api/feedback/notify-admin` (X-Internal-Secret; token bot hanya sisi Python) + route `/api/feedback` panggil `vault()` pasca-insert (fail-soft, tak blokir submit). (2) **Atribusi `?ref=`**: `notify_trial_lapse`/`notify_trial_ending` sebelumnya kirim link POLOS (`_survey_url()`) → kini `_feedback_url(tenant_id, "trial_lapse"/"trial_ending")` (jalur nurture [B9] sudah benar sejak awal). Yang sudah benar & TIDAK disentuh: halaman `/feedback` (baca `?ref/?source/?reason`), API insert, `/admin/feedback`, migr 0110. **Bukti LIVE e2e:** POST `/api/feedback` produksi → `{"ok":true}` + row DB dgn `tenant_id` dari ref + log mv-webhook `[Telegram] ✓ Notifikasi terkirim` + pesan masuk ke Telegram admin; row tes dihapus. Deploy: mv-worker+mv-webhook restart, mv-web rebuild+restart, situs 200.

### [B9] Mesin siklus-hidup & nurture (trial-lapse + suspended→blocked→deleted) — ✅ *(DEPLOYED + LIVE 2026-07-02)*
- **TUJUAN:** selamatkan trial-lapse + pelanggan berhenti-bayar (dunning/win-back) + blokir & **hapus data** yang tak kembali (bebaskan storage) — world-class, no-hardcode, patuh UU PDP.
- **KONTEKS:** SATU mesin (perluas thread `billing_renewal`/`renewal.py`, BUKAN thread baru). Keputusan owner TERKUNCI (nurture 4–5 email/~2–3 mgg; suspended 30h → blocked 30h → deleted; purge S3 video-mentah dini; hot-lead→Telegram admin; ekspor self-service DITUNDA). Reuse `/feedback` [B8] + Leads admin + email lifecycle.
- **SPEC LENGKAP + Plan-vs-Realisasi (13 item) = `LIFECYCLE_NURTURE_ARCHITECTURE.md`** (sumber kebenaran fitur ini).
- **DONE-BILA:** sekuens nurture jalan; `suspended→blocked→deleted` otomatis + peringatan H-30/7/1; purge S3 dini; token YouTube dicabut saat delete; knob tampil di System Config.
- **DEPENDS:** idealnya SETELAH **[A1]** (butuh aliran tenant nyata). **Nyambung:** [B8] /feedback · [D1] funnel · `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` (state machine gate).
- **REALISASI:** ✅ **DEPLOYED + LIVE 2026-07-02** (commit `db589b1`). Mesin lifecycle PENUH LIVE: nurture trial-lapse (5-email config) + suspended→blocked→deleted (30+30h) + purge S3 dini + revoke token YT (UU PDP) + diskon comeback + reaktivasi 1-klik (`/reactivate`) + banner blocked + admin lead_temp. Sweep terverifikasi bersih (nol hapus mendadak; timing di `app_config`). Detail+tracker = `LIFECYCLE_NURTURE_ARCHITECTURE.md §11`. **Follow-up SELESAI 2026-07-03:** ✅ tombol aksi-manual admin (`6a5f798`: Perpanjang trial / Undur hapus / Aktifkan-bersih / Hapus-permanen + ConfirmDialog + footgun Suspend@blocked) · ✅ Telegram admin di-wire ke `company_profile.admin_telegram_chat_id` (`603640e`, migr 0114, editable via `/admin/company-profile` — **bukan env**). **LIFECYCLE = 100% & dokumen di-CLOSE (direkonsiliasi vs realita via 2 verifikator 2026-07-03).**

---

# ⏳ KELOMPOK C — DATA-GATED *(mekanisme SIAP; matang seiring data pasca-cutover — bukan "koding besar")*

### [C1] Closed-loop kalibrasi durasi — 🟡  (REMEDIASI **F5-01**)
- **TUJUAN:** pace `P` (wps efektif) per voice×speed di-update otomatis dari data render nyata → durasi makin presisi.
- **BUKTI (verified DB):** `tts_delivery_samples`=**48 baris DITULIS** (`tts_engine._log_delivery_sample`) tapi **BELUM DIBACA** kode. Fondasi SELESAI: `voice_catalog.delivery_wps`/`pace_sample_n`/`pace_updated_at`/`pace_locked` (migr 0081) + estimator voice-first + FE admin editable.
- **PLAN:** hitung wps efektif per (voice_key, speed) dari `tts_delivery_samples` (EWMA) → update `voice_catalog.delivery_wps` bila `pace_sample_n` cukup + **hormati `pace_locked`** (jangan timpa yang admin-kunci). Jalankan di thread `self_learning` (cadence).
- **DONE-BILA:** pace per-voice ter-update dari data nyata; durasi presisi naik; pace_locked dihormati.
- **REALISASI:** 🟡 fondasi + logging live; EWMA consumer belum. *(Butuh akumulasi sampel — pasca lebih banyak produksi.)*

### [C2] Self-learning deepening + trend F3/F4 — 🟡  (TREND_RADAR **F3/F4**)
- **TUJUAN:** kalibrasi `source_weights` (bobot sumber trend) dari outcome nyata per (niche,geo) + panen sinyal Analytics kaya (retensi/trafficSource/searchTerms) + agregat lintas-tenant anonim (cold-start moat).
- **BUKTI:** loop inti hidup (`viral_score_weights`/`historical_factor`); `channel_analytics` sebagian sinyal sudah. CTR per-video=0 PERMANEN (batas API YouTube, bukan bug).
- **PLAN:** F3 ukur-dimensi lanjutan (`videos.list topicDetails` sudah; kalibrasi `competition_gap`/`emotional_trigger` dari angka) + F4 umpan-balik outcome eksplisit + agregat lintas-tenant. **Butuh akumulasi analytics nyata pasca-cutover.**
- **DONE-BILA:** bobot ter-kalibrasi dari data; seleksi topik makin tajam terukur.
- **REALISASI:** 🟡 mekanisme siap; aktivasi = DATA (post-cutover).

---

# 🔒 KELOMPOK D — KEPUTUSAN OWNER *(belum bisa dimulai tanpa jawaban)*

### [D1] Growth funnel ("pikat dulu, todong belakangan") — 🔒⬜
- **KONTEKS:** onboarding SETUP (credential-first) SUDAH LIVE. Growth-funnel (video-gratis/galeri contoh/kartu buka-kunci/kredit-trial/banner konversi) BELUM dibangun. Spec = `ONBOARDING_FUNNEL_PLAN.md`.
- **BUKTI:** DB nol kolom/tabel credit/free-video; FE galeri/unlock/banner tak ada. Sebagian blocker plan itu sudah RESOLVED (OAuth platform, `voice_catalog` 10 baris, webhook live) → plan perlu diselaraskan dulu.
- **KEPUTUSAN OWNER DIBUTUHKAN (`ONBOARDING_FUNNEL_PLAN.md §9`):** traktir video gratis atau strict-BYOK (A1/A2)? · kuota gratis 1 atau 3? · watermark ya/tidak? · setuju update DESAIN §3/§5 ke hybrid?
- **PLAN (setelah keputusan):** ledger kredit-trial (DB) + jalur LLM platform-murah (trial) + FE galeri/unlock-cards/modal-video-pertama/banner. Selaraskan ke model credential-first.
- **REALISASI:** 🔒 nunggu keputusan owner. **Nyambung:** `LIFECYCLE_NURTURE_ARCHITECTURE.md` (mesin nurture/dunning melengkapi funnel; sebagian keputusan owner sudah TERKUNCI di sana).

### [D2] Multi-platform (Reels/TikTok) — 🔒⬜
- **KONTEKS:** kini YouTube-only (cukup untuk launch, Starter=YouTube). Reels(Pro)/TikTok(Business) = fitur tier. Spec `MULTI_FORMAT_STUDIO.md §7`.
- **BUKTI:** belum ada abstraksi publisher (`youtube_publisher.py` saja; `pipeline.py` hardcode YouTube). `publish_platforms` field ada tapi tak dipakai.
- **KENDALA EKSTERNAL (masuk perencanaan):** audit TikTok 2-4 minggu (tanpa audit=private), Meta App Review IG 2-4 minggu.
- **PLAN (setelah diputuskan):** `distribution/base_publisher.py` + refactor loop `publish_platforms` + `reels_publisher.py`/`tiktok_publisher.py` (BYO-CC) + tier-gating.
- **REALISASI:** 🔒 nunggu keputusan owner + audit eksternal.

---

# 📌 KELOMPOK E — MENUMPANG GATE

### [E1] Add-on custom-niche via Midtrans live — ⬜ *(kerjakan BARENG [A1])*
- **KONTEKS:** lifecycle custom-niche SUDAH jalan (concierge/manual "Tandai lunas"). Pondasi bayar disiapkan (`niche_requests.paid_at`/`order_id`/status `awaiting_payment`). Spec persis = `CUSTOM_NICHE_REQUEST_FLOW.md §7` + arsitektur bayar/settlement = `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §3`.
- **PLAN:** (1) generalisasi `midtrans.snap_create_transaction` dari plan_type → `price_key` add-on (insert `payments` kategori add-on + `order_id`). (2) `niche_requests.order_id` ← order_id Midtrans. (3) `handle_notification`: settlement add-on → set `paid_at` + `awaiting_payment`→`in_progress` **otomatis** (ganti manual). (4) tombol bayar Snap di Pustaka Niche. (5) teruskan/hapus jalur concierge sesuai kebutuhan.
- **DONE-BILA:** tenant bayar custom-niche via Snap → status auto-maju + niche mulai dibangun.
- **DEPENDS:** [A1] Midtrans produksi.
- **REALISASI:** ⬜

---

## 🧭 URUTAN REKOMENDASI (efektif menuju jualan)
1. **[A1] Midtrans prod** (+ Claude siapkan **[A4]** materi verifikasi Google + pandu **[A2]**) → buka pintu jualan. Bareng: **[E1]**.
2. **[B1] system-secrets + [A3] rotasi** — hardening pra-publik.
3. **[A5] smoke-test** tenant-baru e2e (validasi acceptance).
4. Sisa **[B2-B8]** — poles pasca fungsi jualan aktif. *(**[B8]** = fix link mati email trial-lapse; bug live customer-facing, layak didahulukan meski bukan pemblokir jualan.)*
5. **[D1] funnel** + **[B9] siklus-hidup/nurture** (`LIFECYCLE_NURTURE_ARCHITECTURE.md`) setelah [A1] go-live & ada aliran tenant nyata; **[C]** matang otomatis; **[B6]/[D2]** prioritas terendah.

## ⛔ PANTANGAN (agar tak muncul "bug"/kerancuan)
- JANGAN sentuh v1 (pensiun; arsip+DB disimpan). JANGAN drop `niche_pool`/`niche_mode`. JANGAN ngoding di VPS.
- JANGAN anggap marker `[ ]`/⬜ di dokumen SPEC lain sbg daftar kerja — **hanya FILE INI** otoritatif.
- Test-job jangan makan kuota publish live (private/tak-terhitung-cap).

---
### Changelog
- **2026-07-04** — **Sesi poles marketing + admin (arahan owner, di luar nomor backlog; semua LIVE):** (1) `/demo` → **`/showcase`** (migr 0115: showcase_screens+showcase_videos + drop demo_tours; iframe login-trap dibuang; screenshot + galeri video contoh admin-managed via CMS; redirect 301). (2) Blog **feature image** (S3 `blog-cover/`, migr—; +fix ACL public-read laten upload-logo; nginx `client_max_body_size 100m`). (3) Marketing: footer Lumite · trial-days dari `app_config` (nilai live=3!) · kalkulator AI palsu → blok BYOK jujur "mulai Rp 0" · kontak kirim-server → `company_profile.email` (no-hardcode) · tab Status & badge footer → kondisi NYATA worker_heartbeats · fix nav highlight (hardcode `active=\"Fitur\"` sejak awal) · sub-judul rata tengah. (4) Admin: System Health dibersihkan dari fosil `pipeline_queue` → stok buffer per channel + query tahan >1000 · **Jadwal Rilis Bulanan DIHAPUS TUNTAS** (migr 0116 — penjadwal tanpa eksekutor=jebakan pending). (5) **Test Lab Fase 1 DIBANGUN ULANG** (migr 0117): uji-produksi niche admin **TANPA YouTube** (S3+TTL 3 hari, tonton di drawer Pustaka Niche), kunci via vault validate-early NYATA, pilihan provider/model/voice LENGKAP dari katalog DB, ConfirmDialog; sebelumnya rusak e2e (form buang kunci diam-diam + route baca kolom drop-0090). **Menyusul (disepakati): Fase 2 audit properti niche (fokus Music+Scoring, library 28 track) memakai alat ini · Fase 3 test niche utk tenant Business di Niche Studio (kredensial sendiri).** Acceptance Fase 1 = owner isi kunci AI di Test Lab → jalankan 1 test dari Pustaka Niche.
- **2026-07-03 (2)** — **[B8] TUNTAS ✅** (commit `3927c41`): notif Telegram admin utk masukan `/feedback` (baru dibangun, reuse notify_admin/vault) + atribusi `?ref=&source=` di email trial_lapse/trial_ending (sebelumnya link polos). LIVE-validated e2e (DB row + Telegram terkirim + log mv-webhook). Sisa pemblokir jualan tetap = **[A1]** (aksi owner).
- **2026-07-03** — **[B9] follow-up TUNTAS + arch docs CLOSED.** Tombol aksi-manual admin `/admin/tenants` (`6a5f798`) + Telegram admin via `company_profile.admin_telegram_chat_id` (`603640e`, migr 0114 — no-hardcode, editable owner). Bonus (permintaan owner): **menu Company Profile** `/admin/company-profile` (view/edit data perusahaan invoice + Telegram ID admin) + **fix badge Support** hardcode "4" → hitung tiket belum-selesai nyata (`1863239`). `LIFECYCLE_NURTURE` & `PAYMENT_AND_TENANT_GATE` **diverifikasi vs realita (2 verifikator read-only) → direkonsiliasi (5 discrepancy diperbaiki) → CLOSED.** Fokus tunggal tetap file ini; pemblokir jualan = **[A1] Midtrans produksi** (aksi owner).
- **2026-07-01** — dibuat dari audit menyeluruh (verified DB/BE/FE/git/VPS). Konsolidasi seluruh sisa-kerja + Plan-vs-Realisasi. Semua dokumen lain di-CLOSE jadi SPEC/arsip + ber-banner ke sini. Memory (`MEMORY.md`) arahkan sesi baru ke file ini.
- **2026-07-01** — tambah **[B8]** (halaman `/feedback` — perbaiki link MATI di email trial-lapse; keputusan owner Opsi B halaman-sendiri). Bug live customer-facing terverifikasi (`/feedback` → 404; email `email.py:92-101` mengarah ke sana). Urutan rekomendasi + Changelog disesuaikan.
- **2026-07-02** — **rantai kanonik billing & siklus-hidup dibereskan (anti miss-link)**: daftarkan `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` (SELESAI+deployed `04cf0a2`) + `LIFECYCLE_NURTURE_ARCHITECTURE.md` (rencana) ke peta dokumen; tambah item **[B9]** (mesin siklus-hidup/nurture); cross-link [A1]/[E1]→PAYMENT, [B8]/[B9]/[D1]→LIFECYCLE. Klarifikasi [A1]: switch = `MIDTRANS_ENV` `.env`+restart (bukan tombol admin=[B1]); pemblokir = kunci PRODUKSI approved.
