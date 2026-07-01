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
> **Sumber kebenaran status = FILE INI.** Dokumen lain (REMEDIASI/CHANNEL_LOCK/QC/TREND/MULTI_FORMAT/DEPLOY_RUNBOOK/CUSTOM_NICHE/ONBOARDING_FUNNEL) = **SPEC/ARSIP** (rujuk untuk detail arsitektur; jangan pakai marker `[ ]` mereka sbg daftar kerja).

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

**Aturan kerja keras (memory `feedback_*`):** paham dulu sebelum kerja · propose dulu utk perubahan besar · nol-asumsi (bukti file:baris/DB) · no-hardcode · bahasa sederhana ke owner (non-teknis) · **JANGAN ubah UI tanpa izin owner** · validasi PENUH di lokal, deploy per-batch.

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
- **KONTEKS:** BE pembayaran (Snap redirect) SUDAH jadi & lulus e2e sandbox — `src/billing/midtrans.py` (`snap_create_transaction` env-driven sandbox/prod · `verify_signature` SHA512 · `handle_notification`→aktivasi), tabel `payments` (migr 0022), webhook route di `mv-webhook`. Yang kurang HANYA kredensial+konfig PRODUKSI.
- **BUKTI kondisi sekarang (verified DB 2026-07-01):** `payments`=**0 baris**; `.env` `MIDTRANS_ENV`=sandbox. → produksi belum pernah jalan.
- **PLAN (aksi owner + Claude bantu):**
  - Owner: dapatkan **Server key + Client key PRODUKSI** Midtrans; isi ke `.env` VPS + `MIDTRANS_ENV=production`; daftar **Notification URL** (payment/recurring/pay-account) + Finish/Error URL → `https://mesinviral.com/api/webhooks/midtrans`.
  - Claude: verifikasi route webhook `mv-webhook` menerima notifikasi prod; restart `mv-webhook`+`mv-worker` (baca env baru).
- **DONE-BILA:** 1 transaksi nyata (sandbox→prod) → webhook masuk → `payments` terisi + `tenant_configs.subscription_status`→active. FE Billing tombol Snap enabled (kini disabled+note gate).
- **DEPENDS:** — (BE siap). **Nyambung:** [E1] add-on custom-niche.
- **REALISASI:** ⬜ *(belum; gate owner)*

### [A2] Supabase Auth — SMTP + Google provider — 🔒⬜
- **TUJUAN:** email auth (verify/reset) ber-brand + terkirim andal; "Daftar dengan Google" jalan untuk tenant publik.
- **KONTEKS:** kode auth (signup/verify/reset/OAuth callback) SUDAH jalan (Phase 9.1, runtime-validated). Kurang = konfig dashboard Supabase.
- **BUKTI:** reset email dulu kena rate-limit default Supabase (bukan bug kode); Google provider status di dashboard = belum aktif. SMTP tersedia (`mail.lumite.biz.id:465`, di `S3-CONNECTION.md`).
- **PLAN (aksi owner):** Supabase Dashboard `atliatnjhysdibmfypul` → Authentication → (1) **custom SMTP** `mail.lumite.biz.id` (host/port/user/pass/from) · (2) **Google provider** = Client ID/Secret app lumite (`153190496639-i41l1fp3...`).
- **DONE-BILA:** signup email verify terkirim ber-brand; "Daftar dengan Google" e2e sukses (redirect `mesinviral.com`, bukan localhost — bug ini sudah fix `a18d451`).
- **REALISASI:** ⬜ *(gate owner)*

### [A3] Rotasi semua secret dev — 🔒⬜
- **TUJUAN:** secret yang dipakai saat dev tidak bocor ke produksi publik.
- **PLAN:** rotate: DB password (`Rad@...` → baru; update `.env` + semua skrip), `SUPABASE` service_role + anon, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET` (worker==mv-web WAJIB sama), `SMTP_*`, `MIDTRANS_*`, ElevenLabs key ryan. Update `.env` VPS + `.env.local` mv-web + restart.
- **DONE-BILA:** semua service tetap jalan dgn secret baru; secret lama invalid.
- **DEPENDS:** paling akhir sebelum publik (agar tak rotate 2×). Terkait [B1] (system-secrets bisa jadi tempat kelola).
- **REALISASI:** ⬜

### [A4] Verifikasi Google app + kumala reconnect — 🔒⬜
- **TUJUAN:** pelanggan asing lihat brand MesinViral (bukan warning "unverified"); refresh-token permanen (bukan kedaluwarsa 7 hari mode Testing).
- **KONTEKS:** materi SIAP di `GOOGLE_OAUTH_PLATFORM_MIGRATION.md` — justifikasi scope (§8a, 3 scope: youtube.upload/readonly/yt-analytics.readonly), shot-list demo video (§8b), `/privacy`+`/terms` sudah LIVE & patuh. Scope SENSITIVE (bukan Restricted → tanpa CASA berbayar).
- **PLAN (aksi owner):** Google Auth Platform (akun `lumite.biz.id@gmail.com`, project `mesin-viral`) → Publish app (Testing→Production) → Verification Center → submit (justifikasi §8a + demo video §8b). Timeline ~10 hari. + kumala reconnect YouTube (tak mendesak — channel belum unlock).
- **DONE-BILA:** app verified (warning hilang, token permanen).
- **REALISASI:** ⬜ *(gate owner; Claude bisa bantu rekam demo/teks)*

### [A5] Smoke-test live end-to-end (tenant baru dari nol) — 🔒⬜
- **TUJUAN:** bukti acceptance utama CHANNEL_LOCK — tenant BARU (bukan ryan) bisa jalan penuh.
- **PLAN (owner + Claude):** signup tenant uji baru → `/integrations` isi kunci AI + connect YouTube (OAuth consent 1× nyata di browser) + Telegram → `/channels/[id]` set niche/model/voice/jadwal → semua 🟢 → Aktifkan → produksi + publish + analytics jalan. + transaksi Midtrans 1× + email egress dari VPS.
- **DONE-BILA:** tenant baru sampai aktif + 1 video publish + bayar — mulus, nol error mentah.
- **DEPENDS:** A1, A2, A4.
- **REALISASI:** ⬜ *(butuh browser owner untuk OAuth consent)*

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
- **REALISASI:** 🔒 nunggu keputusan owner.

### [D2] Multi-platform (Reels/TikTok) — 🔒⬜
- **KONTEKS:** kini YouTube-only (cukup untuk launch, Starter=YouTube). Reels(Pro)/TikTok(Business) = fitur tier. Spec `MULTI_FORMAT_STUDIO.md §7`.
- **BUKTI:** belum ada abstraksi publisher (`youtube_publisher.py` saja; `pipeline.py` hardcode YouTube). `publish_platforms` field ada tapi tak dipakai.
- **KENDALA EKSTERNAL (masuk perencanaan):** audit TikTok 2-4 minggu (tanpa audit=private), Meta App Review IG 2-4 minggu.
- **PLAN (setelah diputuskan):** `distribution/base_publisher.py` + refactor loop `publish_platforms` + `reels_publisher.py`/`tiktok_publisher.py` (BYO-CC) + tier-gating.
- **REALISASI:** 🔒 nunggu keputusan owner + audit eksternal.

---

# 📌 KELOMPOK E — MENUMPANG GATE

### [E1] Add-on custom-niche via Midtrans live — ⬜ *(kerjakan BARENG [A1])*
- **KONTEKS:** lifecycle custom-niche SUDAH jalan (concierge/manual "Tandai lunas"). Pondasi bayar disiapkan (`niche_requests.paid_at`/`order_id`/status `awaiting_payment`). Spec persis = `CUSTOM_NICHE_REQUEST_FLOW.md §7`.
- **PLAN:** (1) generalisasi `midtrans.snap_create_transaction` dari plan_type → `price_key` add-on (insert `payments` kategori add-on + `order_id`). (2) `niche_requests.order_id` ← order_id Midtrans. (3) `handle_notification`: settlement add-on → set `paid_at` + `awaiting_payment`→`in_progress` **otomatis** (ganti manual). (4) tombol bayar Snap di Pustaka Niche. (5) teruskan/hapus jalur concierge sesuai kebutuhan.
- **DONE-BILA:** tenant bayar custom-niche via Snap → status auto-maju + niche mulai dibangun.
- **DEPENDS:** [A1] Midtrans produksi.
- **REALISASI:** ⬜

---

## 🧭 URUTAN REKOMENDASI (efektif menuju jualan)
1. **[A1] Midtrans prod** (+ Claude siapkan **[A4]** materi verifikasi Google + pandu **[A2]**) → buka pintu jualan. Bareng: **[E1]**.
2. **[B1] system-secrets + [A3] rotasi** — hardening pra-publik.
3. **[A5] smoke-test** tenant-baru e2e (validasi acceptance).
4. Sisa **[B2-B7]** — poles pasca fungsi jualan aktif.
5. **[D1] funnel** setelah owner putuskan; **[C]** matang otomatis; **[B6]/[D2]** prioritas terendah.

## ⛔ PANTANGAN (agar tak muncul "bug"/kerancuan)
- JANGAN sentuh v1 (pensiun; arsip+DB disimpan). JANGAN drop `niche_pool`/`niche_mode`. JANGAN ngoding di VPS.
- JANGAN anggap marker `[ ]`/⬜ di dokumen SPEC lain sbg daftar kerja — **hanya FILE INI** otoritatif.
- Test-job jangan makan kuota publish live (private/tak-terhitung-cap).

---
### Changelog
- **2026-07-01** — dibuat dari audit menyeluruh (verified DB/BE/FE/git/VPS). Konsolidasi seluruh sisa-kerja + Plan-vs-Realisasi. Semua dokumen lain di-CLOSE jadi SPEC/arsip + ber-banner ke sini. Memory (`MEMORY.md`) arahkan sesi baru ke file ini.
