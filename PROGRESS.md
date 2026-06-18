# MesinViral — Live Progress & Master Plan

> **Single source of truth** untuk status implementasi. Update setiap selesai sub-phase.
> Dibuat: 2026-06-10 | Update terakhir: 2026-06-18

---

## ⏭️ RESUME POINT — BACA INI DULU SETIAP SESI BARU (jangan salah arah)

**FRAMING FUNDAMENTAL (detail: memory [[decisions_v1_v2_migration]]):**
- **v1 = PRODUKSI LIVE di VPS** — mesin produksi konten single-tenant (`ryan_andrian`) + Supabase. **TANPA SaaS/multitenancy/frontend. Running well. JANGAN DISENTUH.**
- **v2 = YANG KITA KERJAKAN** — SaaS multi-tenant + Multi-Format Studio + frontend. **SEMUA di local dev ini, BELUM ada yang di-pull ke VPS.** Spec = `DESAIN_PRODUK_SAAS.md` + `MULTI_FORMAT_STUDIO.md` + `design-source/`.
- **DB v2 = punya sendiri** (clone penuh skema+data dari v1) — bukan DB v1. **v2 REPLACE v1 penuh di VPS yang sama saat proven.**

**🎯 STATUS TERBARU (2026-06-15) — WIRING FE TUNTAS.** Backend Phase 0-8 ✅. **Frontend SEMUA ter-wiring + tervalidasi** ke Supabase v2: tenant (Phase 9: dashboard/channels/runs/analytics/compliance/insights/schedule/billing/settings/support/config-10-tab/onboarding) · admin penuh (Phase 10: tenants/pricing/niches/catalog/system/support/content-CMS/test-lab/account) · marketing (harga dari pricing_config, konten Blog/Docs/Demo DB-backed via CMS). **Fitur baru:** direct-produce (`direct_jobs`, "1 mesin 2 mode", anti-OOM terverifikasi) · admin Test Lab (validasi kredensial NYATA) · `/channels/new` · CMS. **Nol komponen FE fake/non-functional** (audit 3-area, owner-driven). Branch `v2-backend` (pushed, `main` v1-safe). Migrasi v2 = **0001–0044** (skema penuh: `DB_SCHEMA_V2.md`, 39 tabel + 4 kolom `*_enc`). **🔐 KEAMANAN KREDENSIAL (2026-06-15):** **YouTube OAuth BYO-CC = ✅ TERBANGUN** (alur web per-tenant, Opsi A — enkripsi + dance OAuth di server Python `webhook_app`; master key tak pernah ke Vercel) · **SEMUA API key AI kini TERENKRIPSI at-rest** (Fernet, migr 0044; plaintext lama dimigrasi+di-null; tulis via vault `/api/keys/set`; worker dekripsi saat baca) · landing punya section keamanan (klaim jujur). **➡️ BERIKUTNYA = §PERBAIKAN PRODUCE & PUBLISH (pra-cutover)** — luruskan DB/BE/FE ke §12c (jadwal `channels.publish_slots`, niche per-channel dari entitlement, buang fosil V1, editor niche + form custom-niche). **WAJIB selesai 100% SEBELUM** §GATE CUTOVER. Kedua checklist ada di bawah blok ini. Detail per-fitur: `PHASE10_ADMIN_WIRING.md` + memory `progress_journal` (POSISI TERKINI). *(Catatan historis di bawah = arsip per-phase; status OTORITATIF = baris ini + roadmap §MASTER.)*

**⚡ STATUS TERBARU (2026-06-18) — INI YANG TERKINI (menang atas status 2026-06-15 di atas). Kronologi rinci = memory `progress_journal` entri 06-18 lanjutan-2 s/d 5.** Sesi penyesuaian PRODUKSI per-preset + audit pipeline (semua LOKAL→validasi→commit→push→deploy VPS). Migrasi v2 = **0001-0054**.
> - **✅ Segmentasi per-preset SINGLE-SOURCE** (migr `0053`/`0054`, `05a3339`): `duration_presets.beats`/`use_case`/`render_mode` + tabel BARU `beat_glossary` (term+label dwibahasa). Struktur lean 8=core…90=7beat. LIVE.
> - **✅ Analyzer preset-aware** (`617a33c`): renormalisasi bobot atas beat aktif → ultra-short adil (15s 74→85; 45-90s TAK berubah). LIVE.
> - **✅ FE preset-picker + 2 tabel** (segmentasi+glosarium) di channel-detail (tenant) & admin catalog tab "Durasi" (`fd12f4e`). LIVE.
> - **✅ Kartu landing** "Indonesia-First"→"Beragam Opsi Durasi Konten" dwibahasa (`fabeec3`). LIVE.
> - **✅ D2 PREVIEW /review** presigned Biznet S3 + `<video>` (+@aws-sdk, S3_* di env mv-web) (`adbd4e4`) — **menutup §OPSI C D2**. LIVE (belum diuji putar di browser).
> - **✅ Akurasi durasi — closed-loop atempo** (`e0c42b3`): akar = kecepatan bicara EL bervariasi ±15% (log: 1.43-1.95 wps). Fix = ffmpeg time-stretch audio ke target + skala word_timestamps, **NOL biaya EL ekstra**, clamp [0.80,1.25] (ekstrem→skip jaga suara). **= realisasi closed-loop MULTI_FORMAT §0/§10 + GATE-CUTOVER E3.** Validated LOKAL (sintetis). **✅ TERVERIFIKASI PRODUKSI NYATA (2026-06-18):** worker.log `atempo fit: 68.4s→58.5s factor 1.169` — menangani OVERSHOOT (yg word-budget tak bisa) → masuk window, caption diskala, EL=0. **Sekaligus terbukti live: AUTO-PUBLISH (inv 42 published ke YouTube slot 21:00) + NICHE ROTATION fix (inv 44 producing=dark_history, tak lagi selalu universe) + approve-fix (inv 41 ready+run success).** Semua linchpin go-to-market PROVEN.
> - **✅ Label run** `qc_failed`/`ready_with_issues` → "Perlu Ditinjau" (kuning, bukan merah "Failed") (`b4d844a`). LIVE.
> - **✅ Rotasi niche AKTIF lagi:** backfill `videos.channel_id` (247 baris, dulu NULL = footnote §Phase7) → `DiversityEngine.pick` kini rotate (terbukti run). hook/visual/music = WIRED, dorman menunggu histori publish; voice = deferred by-design (Phase 6.2). **Bukan bug baru.**
> - **buffer_depth ryan 1→3** (DB) → produksi resume.
>
> **KONDISI PRODUKSI NYATA:** ryan (business/active · preset 60s · niche random · visual=`ai_image:gpt-image-1-mini` BUKAN pexels · tts=elevenlabs) — buffer = **2 `ready` (60.2s/52.9s) + 1 `ready_with_issues` (49.1s)**. **AUTO-PUBLISH BELUM PERNAH terjadi** (root: butuh `ready` bersih saat slot; produksi lampau selalu undershoot → `ready_with_issues`). **📍 CHECKPOINT slot 21:00 WIB = percobaan AUTO-PUBLISH PERTAMA ke YouTube + produksi ber-atempo PERTAMA** (owner pantau).
>
> - **✅ Niche rotation = cara V1 (sederhana, owner 2026-06-18):** `_resolve_niche` random → **acak dari entitlement + guard histori** (kalau niche pilihan == 1-2 video terakhir channel di `content_inventory` → acak lagi). Gantikan LRU deterministik (yg collide saat window sama). **VPS produksi SEKUENSIAL (`PRODUCER_MAX_RENDER=1`) → tiap produksi lihat sebelumnya → guard cegah niche berdekatan → rotasi rapi, no klaster.** Validated eksekusi (guard: 0/2000 ulang). *(Catatan: bila kelak scale paralel >1 core, perlu koordinasi antar-batch — belum perlu sekarang.)*
>
> **✅ SELESAI 06-18 (lanjutan):** Opsi-C **C1/C2** publisher reporting (verifikasi kode; checkbox basi) · **run sampah #103-107 DIHAPUS** (06-16 test) · **/runs label sinkron** — migr **0055** (approve→`success`/discard→`failed` REFLEKSI ke `production_runs`; FE /runs ikut keputusan review, tak nyangkut "Perlu Ditinjau") **applied** + run #1 yg sudah di-approve **di-fix langsung** → "Completed". · **🟡 run_direct (test-now) isi `topic`+`elapsed_seconds`+`viral_score`+`llm_provider`** (dulu kosong, beda dari jalur buffer) — **LOKAL, BELUM deploy** (owner cek dulu). Hasil test-now = video PRIVATE YouTube, link di run → /runs/[id] "Buka YouTube".
> **✅ SELESAI 06-19 (DASHBOARD D1 — rombak KPI data-nyata + AppShell + auto-refresh, DEPLOYED `25cfae9` + migr `0056`):** 4 KPI profesional tenant-wide: **Success Rate** (all-time `production_runs`, `qc_failed` dipisah "perlu ditinjau"; ryan 94% = 104/97/6/1) · **Total Views/Likes/Followers YouTube** via RPC `get_tenant_youtube_totals` (SECURITY DEFINER, RLS `auth.uid()`; views/likes = **snapshot-terbaru/video** bukan sum mentah; followers = `channels.subscriber_count` BARU). ryan: Views 34.762 · Likes 1.006 · Followers 162. **Jadwal Hari Ini** kini baca `channels.publish_slots` (zona tenant) — dulu hardcoded kosong. **Auto-refresh SMOOTH**: realtime `production_runs` (debounce 400ms) + re-fetch saat tab aktif, tanpa spinner. **AppShell**: sb-tenant data nyata (display_handle/plan/kanal+inisial), buang "Ganti tenant"+badge"3"; **hapus search+lonceng**; hapus tombol Bantuan bawah (duplikat). **BE**: `ChannelAnalytics.fetch_subscriber_count` (fail-soft, `mine=True`) di loop self_learning 24j. **NOL kode khusus-ryan** — semua tenant-scoped (RLS/per-tenant); v1 ryan terhitung otomatis krn datanya sudah di tabel tenant-nya (tak menyentuh tenant lain). Cadence data: production_runs **live** (FE refresh realtime/fokus); Views/Likes/Followers/Compliance **tiap 24j** (`SELF_LEARNING_INTERVAL_SEC`). **+ Follow-up 3 kartu (deployed `d901a1b`, migr `0057`):** Compliance kini **AGREGAT lintas-channel** (RPC `get_tenant_insights_summary` — insight TERBARU per channel NYATA, `channel_id IN channels tenant` → cegah double-count orphan/legacy v1; formula GENERIK semua tenant, bukan patch ryan) · Self-Learning **di-wire nyata** (video dipelajari + niche teratas + terakhir belajar) · Biaya AI → **"Coming soon"** (worker belum catat cost). **+ NAMA CHANNEL = YouTube (deployed `cfe39c4`):** `sync_channel_meta` (ganti `fetch_subscriber_count`) — `mine=True` → `channels.channel_name`=judul YouTube (WAJIB sama, anti-confuse) + `platform_channel_id` + `subscriber_count`. GENERIK semua tenant (sumber kebenaran nama = YouTube, bukan niche/input), fail-soft, di loop self_learning 24j. ryan diperbaiki: "Ryan Andrian — Universe & Mysteries" (salah) → **"RAD The Explorer"** (UCo5d8bH2MnNdIuwItgPtJ6Q). *(Catatan: onboarding `finish()` masih set channel_name dari niche = placeholder s/d YT connect → sync overwrite; rapikan saat rombak onboarding. Orphan `channel_insights.channel_id='ryan_andrian'` v1 = bersihkan saat rombak `/compliance`.)* **✅ `/analytics` SELESAI (deployed `98b2ff8`, migr `0058`):** ternyata sudah real (label "MOCK" keliru) → **dibangun ulang kelas-pro** via 5 RPC server-side (overview/by-niche/monthly/top-videos/learning; tenant-scoped, agregat efisien, snapshot-terbaru/video). KPI Followers/Views(+30hr)/**Retensi**(+n video ber-data)/**Engagement**/Video/Komentar · Performa per-niche · **Hook & Topik teratas** (MOAT self-learning) · tabel Video teratas sortable. **CTR DIBUANG** (tak tersedia YouTube API). ryan: 158 video, retensi 89,9%, engagement 3,10%. **+ `/runs` & run-detail dibenahi (deployed `2884e55`, migr `0059`):** kolom Views di-wire (RPC `get_tenant_video_views`; sumber video_analytics) · channel_id backfill historis ryan (99 baris→channel nyata) · topic dari YT title · "Durasi"→"Proses"/"Waktu proses" (jelas=waktu proses, bukan durasi konten) · titik-3 mati→ikon Detail (link /runs/[id]) · log query utamakan run_id · kartu Rincian biaya→"Coming soon" · dedup top_hooks/top_topics di /analytics (analyzer hasilkan duplikat). **BERIKUTNYA (owner minta, urut):** (1) benahi page **`/compliance`** (MOCK) + treatment multi-channel penuh + bersihkan orphan `ryan_andrian` · (2) **BE log buffer-run** (`produce_one` tak bind run_id ke `db_log_sink` → log buffer kosong; hanya direct yg log) **+ retensi/pruning `pipeline_run_logs`** (anti-bloat DB) · (3) **BE cost-tracking** (token×harga per run → kartu Biaya AI nyata) · (4) **BE dedup `top_hooks`/`top_topics`** di `performance_analyzer` (sumbernya). 
> **✅ SELESAI 06-19 (REGISTRASI tenant — Google OAuth + email-verify):** **bug redirect nyasar ke `https://localhost:3000/dashboard`** (SSL error pasca signup) **DIPERBAIKI + DEPLOYED** (commit `a18d451`). Akar TERBUKTI (header `Location` asli): Next.js 16 di belakang reverse-proxy me-resolve `new URL(request.url).origin` ke alamat bind server (`localhost:3000`), MENGABAIKAN header `Host` → SEMUA redirect callback (OAuth + verify-email + reset) nyasar ke localhost. Fix `auth/callback/route.ts`: `origin` dihitung dari `x-forwarded-host`/`host` + `x-forwarded-proto` (nginx kirim `Host: mesinviral.com`) + nginx tambah `proxy_set_header X-Forwarded-Host`. **Bonus:** akun baru (0 channel) → `/onboarding` (bukan `/dashboard`). Verifikasi live: `location: https://mesinviral.com/...` (localhost hilang). **Ini juga akar gagal konfirmasi email effi kemarin (1 bug, 2 gejala).** Supabase URL Config sudah benar (Site URL `https://mesinviral.com` + redirect `https://mesinviral.com/**`). Sebelumnya 06-19: **nginx `proxy_buffer_size` 16k** (default ~8k kekecilan utk cookie sesi Supabase → 502 di callback). Provisioning trigger `handle_new_tenant` jalan (akun Google `lumite.biz.id@gmail.com` → tenant_config trial). **Akun test dihapus:** effi@, ryan.andrian.diputra@gmail.com (login tenant) — kredensial YouTube ryan@ (`tenant_credentials`, akun YT `ryan.andrian.diputra@gmail.com`) AMAN/utuh, terpisah dari baris auth.users.
> **BERIKUTNYA (PR terbuka, urut):** (1) verifikasi atempo+auto-publish slot 21:00 · (2) buang fosil **pexels** — **log menyesatkan "visual=pexels" SUDAH diperbaiki → `visual_mode`** (selektor efektif); penghapusan PENUH (jalur `_try_pexels`+`pexels.py`+`get_visual_provider()` mati+kolom `visual_provider`) **MENUNGGU keputusan owner**: `visual_mode="video"`/default/ai_video-unbuilt → jadi apa? (Opsi1 default ai_image / Opsi2 error eksplisit). ryan aman (ai_image:) · (3) §OPSI-C **F2/F3** fosil sisa (drop kolom deprecated + evaluasi `pipeline_queue`). **PRA-PUBLIK:** webhook_app deploy + ADMIN SYSTEM SECRETS S1-S4. **OWNER/eksternal (GATE):** Midtrans prod · Supabase Auth SMTP+Google · DNS api · YouTube OAuth live · rotasi secret. Ditunda: 8s ai_video, swap VPS, koordinasi niche antar-batch (kalau scale paralel).
- **✅ PHASE 0-5 SELESAI:** softcode AI+katalog (1) · exceptions typed (2) · pipeline_run_logs (3) · BYO-CC+Auth(`tenant_id=auth.uid()`)+RLS+OAuth-DB-first (4) · **decouple TERBUKTI end-to-end** (5: producer/publisher/buffer-S3/janitor/worker_decoupled; full loop → publish YouTube private `shorts/7ocW6BPdlVg`).
- **✅ MULTI-FORMAT §12-A (cheap-wins):** F1+F2 durasi preset + QC-LLM relatif (±15% §8) + **effective-WPS per kelas TTS** (tts_profiles; ElevenLabs-class 1.8/edge 2.6 — solusi gap budget); Branded FB1-4 (link deskripsi + soft-sell CTA + logo overlay: **ukuran=bounds platform `branding_config`, posisi=tenant `channel.logo_position`**).
- **✅ publish-privacy** per-channel DEFAULT **private** (trial-safe; tenant flip public saat cocok).
- **✅ PHASE 6.1:** `channel_analytics` OAuth **DB-first** + `self_learning.py` loop (fetch YT analytics + compute insights channel-scoped) thread di `worker_decoupled` (cadence 24j).
- **✅ PHASE 6.2 increment #1 (2026-06-14, anchor DESAIN §9.1):** migr `0018` (videos += voice_id/hook_pattern/music_mood/visual_seed + `diversity_config`) + `diversity.py` (`DiversityEngine` LRU per-channel) + **hook-pattern rotation** (quality-first, re-pilih winner hanya dalam `HOOK_DIVERSITY_TOLERANCE`) + **visual-seed rotation** (Replicate; OpenAI fail-soft) + **music-mood rotation** (LRU atas `niches.mood_priority` niche-safe; mood AKTUAL terekam, bukan proxy LLM) + **TUTUP gap Phase-5**: publisher decoupled kini tulis row `videos` (+4 dim) → histori lookback terisi. niche-rotation sudah ada. **Hanya VOICE rotation yang DEFERRED** (butuh voice-pool catalog + ElevenLabs aktif) — detail `PHASE6_DESIGN.md` §STATUS 6.2. Validasi murah hijau (py_compile · DiversityEngine + `_select_winner` 6/6 + mood-LRU · import).
- **✅ PHASE 6.3 (2026-06-14):** AI Disclosure — YouTube `status.containsSyntheticMedia` (field RESMI terverifikasi sejak 2024-10-30, wajib kebijakan Mei 2025) per-channel **default ON**. Migr `0019` (`channels.ai_disclosure`) + TenantConfig + `youtube_publisher._build_metadata` (terkirim via `part="snippet,status"`). Validasi: DB+threading+field-transmission. **FE gap:** toggle di channel settings (default ON) — Phase 9-10.
- **✅ PHASE 5.5 (kode):** render opt — 5.5a paralel image + 5.5b single-pass concat (1 encode) + fallback 2-pass + preset config-driven. Validasi e2e komprehensif (single≡2-pass 0.0s).
- **✅ PHASE 6.4 (parsial, terverifikasi):** insights **per-channel SUDAH ADA** (6.1 channel-scoped). **per-tag DEFERRED** (terblokir: `videos.topic_tags` belum ada + butuh sistem Layer-2 tag [tag_pool+assign] + histori tag → prematur; sequence dgn niche-UI P9-10). Keputusan expert, terdokumentasi.
- **✅ PHASE 7 (kode, 2026-06-14):** Compliance Score — `src/analytics/compliance.py` `ComplianceScorer` 0-100, 5 dim (niche_distribution/hook_style_spread/voice_diversity/dup_freshness/ai_disclosure), dim tanpa data→N/A excluded, alert <60. migr `0020` (`channel_insights.compliance` jsonb) + wired ke `compute_and_store` (independen grade). **Validasi e2e komprehensif:** SEHAT 86.8/healthy vs SLOP 18.0/at_risk (membedakan AI-slop); real-DB insufficient→None + stored. **Feed widget D20** (FE wiring P9-10). *(Skor ryan insufficient s/d produksi baru: video historis channel_id=null.)*
- **🛠️ PHASE 8 in-progress:** **✅ 8a (2026-06-14)** tier-gating + subscription-gate — migr `0021` (`tenant_configs.subscription_status` default active + `current_period_end`) + `src/billing/limits.py` (can_produce {active/trial/grace}, daily_publish_cap=min(rate,plan ceiling), channel_quota) enforce di **producer** (skip suspended) + **publisher** (skip suspended + cap harian/channel). e2e: units semua status + real ryan(active/cap3) + suspended→False. **Sandbox Midtrans key tertest** (Snap token nyata). **✅ 8b (2026-06-14)** Midtrans **Snap REDIRECT** (hosted page, BUKAN vt-web) — `src/billing/midtrans.py` (snap_create env-driven sandbox/prod + verify_signature SHA512 + handle_notification→aktivasi) + migr `0022` payments (audit→D13) + webhook app minimal (`webhook_app.py`, deploy cutover). e2e NYATA: Snap token sandbox + signed settlement→ryan active + tampered→ditolak + cleanup. **✅ comp-account** (`is_developer`/discount≥100 → GRATIS SELAMANYA, gate selalu active, bypass billing — ryan dev). **✅ renewal/expiry checker (2026-06-14)** `src/billing/renewal.py` (active→grace→suspended saat `current_period_end` lewat; **comp exempt**; thread di `worker_decoupled`, cadence harian). e2e: next_status 9/9 + sweep v2 ryan-exempt. → **siklus monetisasi LENGKAP** (checkout→webhook-aktivasi→tier-gate→renewal/grace/suspend→comp-free). **✅ Trial (2026-06-14, keputusan owner):** trial = **BYOK** (supersede DESAIN §3/§5 platform-managed) → insentif abuse runtuh + infra simpel + trial kualitas-penuh. Tier ke-4 **`'trial'`** di `plan_limits` (caps **1ch/1vid-hari**, admin-edit) + durasi **7hr** di **`app_config`** (admin-edit, no-hardcode). Lifecycle: signup→`start_trial` (BYOK) → lapse→**`trial_expired`** (non-producing = **lead marketing** follow-up/feedback, retensi grace) → bayar→active. migr 0023(`trial_started_at`)/0024(`plan_limits['trial']`+`app_config`) + `src/config/app_config.py`. e2e: caps-via-tier + lifecycle + trial_expired-blocked + comp-exempt. **FE (P9-10):** signup wajib BYOK upfront (hapus skip-keys) + admin "Trial Leads" view + survey. **✅ 8c email (2026-06-14)** `src/utils/email.py` **SMTP** (`smtplib` stdlib, `mail.lumite.biz.id:465` SSL — BUKAN Resend; nol dependency) + resolve email tenant via **Supabase Auth admin API** (opsi A) + 3 notif fail-soft (receipt on-activate idempotent · trial-lapse+survey · suspend-warning) wired ke `midtrans.handle_notification` + `renewal.sweep`. e2e NYATA: resolve ryan→`ryan@lumite.biz.id` + kirim test terkirim + fail-soft. **🎉 PHASE 8 BACKEND PAYMENT SELESAI** (8a/8b/renewal/trial/8c — semua e2e sandbox). **Sisa Phase 8 = CUTOVER ops → §GATE CUTOVER (C1/B2).** FE billing D13 + Trial-Leads = P9-10. **➡️ THREAD AKTIF = PHASE 9-10 wiring frontend (long pole, jalur kritis ke beta). Breakdown: [`PHASE9_FRONTEND_WIRING.md`](PHASE9_FRONTEND_WIRING.md).** **✅ 9.1 FONDASI DONE (2026-06-14):** `apps/web` + Supabase client (browser/server/middleware @supabase/ssr) + `.env.local` v2 (anon, gitignored) + middleware refresh-session (non-breaking). Build PASS + RLS-isolasi tervalidasi (anon: public-read OK, tenant=0). **✅ 9.1 provisioning DONE (2026-06-15, migr 0028):** trigger `on_auth_user_created` (signup→tenant_configs row + trial auto, durasi app_config). e2e: provisioning→gate(trial/cap1)→niche(3 base)→no-custom, cleanup. **✅ Auth page wired (2026-06-15):** `auth/page.tsx` 6 view → `supabase.auth.*` (signUp/signIn/resetPassword/resend/oauth-google), controlled+busy/error, demo-bypass dibuang. **Runtime-validated** (signup→trigger-provision→login OK; reset call benar tapi kena rate-limit email default Supabase → go-live: konfig Auth SMTP→`mail.lumite.biz.id`). **✅ 9.1 TUNTAS (2026-06-15) — RUNTIME-VALIDATED:** (1) `/auth/callback/route.ts` (PKCE `exchangeCodeForSession` + `verifyOtp` fallback + anti open-redirect) — email-verify/reset/OAuth retarget LEWAT callback · (2) middleware **hard-redirect** proteksi (dashboard/channels/runs/analytics/insights/compliance/config/schedule/settings/billing/onboarding/admin → no-session redirect `/auth?next=`; marketing+auth publik) · (3) **reset-password lengkap** (view `reset` baru, `updateUser` — gap desain ditutup, approved owner) · (4) login **onboarded-check** (honor `?next`, else `channels` count RLS → 0=/onboarding, >0=/dashboard). **Validasi `next start`:** publik 200 · protected 307→/auth?next · callback bad-code→error PKCE asli Supabase (exchange beneran jalan) · ryan(1ch)→/dashboard, tenant-baru(0ch,trigger trial)→/onboarding · cleanup bersih · build PASS. ⏳ sisa = **gate owner** (Google OAuth provider config di Supabase; happy-path cookie-session browser → 9.2). **✅ 9.2 VERTICAL SLICE DONE (2026-06-15) — RUNTIME-VALIDATED:** D2 Channels (`(app)/channels/page.tsx`) mock→data v2 NYATA — READ RLS (channels+tenant_configs+plan_limits, quota real, stats `—` placeholder jujur) + WRITE toggle `is_active` (optimistic+RLS) + REALTIME subscribe `channels` (tenant-scoped). migr `0029` (channels→publication `supabase_realtime` + policy `channels_tenant_update` UPDATE — Phase 4.3 cuma SELECT, write FE ke-block tanpa ini). **Validasi (anon key, temp authed user):** build PASS · RLS read-isolasi PASS · WRITE PASS · cross-tenant write-guard PASS · **REALTIME websocket receipt PASS** · cleanup bersih. **Pola stack (client+RLS read+write+realtime) de-risked untuk fan-out 28 layar** — tiap layar WRITE wajib tambah policy UPDATE/INSERT per-tabel; realtime = tambah tabel ke publication. **✅ 9.3 ONBOARDING increment 1 DONE (2026-06-15, runtime-validated):** `apps/web` audit 28 layar (FE-grounded, [`PHASE9`](PHASE9_FRONTEND_WIRING.md) §1.5 + rekonsiliasi) · **Team take-down V2 ditegakkan** (nav "Tim" dihapus + klaim marketing dibuang) · onboarding `Finish`→buat channel pertama (client-RLS; migr `0030` channels INSERT + production_schedules INSERT/UPDATE + `channels.content_language`) · validasi: channel 0→1 RLS, onboarded→/dashboard, **SECURITY self-escalation BLOCKED** (tenant tak bisa set plan_type/is_developer), cross-tenant insert BLOCKED. **🔑 Temuan: `tenant_configs` campur config+billing → tulisan config WAJIB whitelist** (bukan blanket RLS UPDATE). **✅ 9.3 increment 2a DONE (2026-06-15, runtime-validated):** tulisan config via **SECURITY DEFINER RPC `set_tenant_config`** (migr `0031`, whitelist kolom config + scope auth.uid(), **nol service_role di FE**, grant authenticated/revoke anon) — onboarding `finish()` tulis AI keys C3 + voice + timezone via RPC lalu INSERT channel. Validasi: config tertulis whitelisted · **billing/comp UNTOUCHED** · blanket-UPDATE plan_type BLOCKED · channel insert PASS · build PASS. **Pola RPC-whitelist = template semua config-write D8-D19.** **✅ D3 Channel Detail DONE (2026-06-15, runtime-validated):** read channel by-id (RLS) + Settings write (name/content_language/publish_privacy/is_active via channels UPDATE); tab analitik = placeholder jujur (bukan fabricated). Validasi: read-own/read-other-0rows/write/cross-tenant-guard PASS. **✅ D4/D5 Runs DONE (2026-06-15, runtime-validated):** D4 `/runs` list `production_runs` NYATA (ryan 99 row, RLS, status-filter; views/cost="—" → video_analytics 9.4); D5 `/runs/[id]` read run by-id + **log viewer NYATA** (fetch `pipeline_run_logs` + **Realtime live-tail**, queue_id-filter + RLS-scoped) + pipeline 8-step derivasi status/log + rail jujur. migr `0032` (pipeline_run_logs→publication `supabase_realtime`). Validasi: RLS read-isolasi (production_runs + logs, temp user tak lihat data ryan) PASS · **Realtime live-tail receipt PASS** · build PASS. **✅ D1 Dashboard DONE (2026-06-15, runtime-validated):** Recent Runs + Success Rate + Video-hari-ini + activity feed = NYATA (`production_runs` RLS); Compliance gauge real bila `channel_insights.compliance` ada (else "belum cukup data"); Views/Subs/Cost/Self-learning/Schedule = placeholder jujur. Validasi: 4 read RLS execute + isolasi PASS, build PASS. **✅ D13 Billing DONE (2026-06-15, runtime-validated):** plan/status/usage NYATA (tenant_configs+channels+production_runs-bulan-ini) · **harga dari `pricing_config` (no-hardcode terpenuhi)** · invoice dari `payments` (RLS, empty-state) · add-on katalog real · **comp account (is_developer/discount≥100) → gratis** · Snap checkout = GATE cutover (disabled+note). Validasi: read RLS+isolasi + pricing_config public(9 row) PASS, build PASS. **✅ B5 Settings DONE (2026-06-15, runtime-validated) → Area 2.4 TUNTAS:** Profil (email read + display_handle via RPC) · **ganti password NYATA** (`supabase.auth.updateUser`) · Integrasi Telegram (chat_id+enabled via RPC) · lang/theme functional; 2FA/sesi/danger=placeholder. migr `0033` (perluas RPC whitelist 8→11 arg). Validasi: RPC write + password-change re-login + billing-untouched PASS. **🔼 Pushed origin/v2-backend (34 commit ter-backup; `main` v1-safe).** **✅ ADMIN AUTH-GATE DONE (2026-06-15, runtime-validated):** lubang ditutup — `/admin/*` kini **super-admin only**. **Login admin TERPISAH** `/admin/login` (publik, email+pw, tolak non-admin) — keputusan owner. Gate **defense-in-depth**: (1) proxy/middleware (`/admin/*` butuh `app_metadata.role='super_admin'`; no-session→/admin/login, tenant→/dashboard) + (2) **route-group `admin/(panel)/layout.tsx`** = async Server Component re-cek role (enforcement nyata). AdminShell footer → **Logout**. **Akun super-admin TERPISAH = `mesinviral@lumite.biz.id`** (bukan ryan; `app_metadata.role=super_admin` via service_role; **tenant_configs row auto-trigger DIHAPUS** → admin != tenant). Validasi: unauth /admin/*→/admin/login · /admin/login 200 · /dashboard→/auth (tenant flow intact) · service_role: admin role=super_admin+0 tenant-row, ryan not-admin+1 tenant-row · build PASS. **pw admin di-deliver via chat** (owner-approved; SMTP egress diblok dari WSL dev box — 8/8 port timeout — BUKAN bug `email.py` yg fail-soft by design). **🔴 FOLLOW-UP CUTOVER → §GATE CUTOVER (D2 SMTP-egress, A3 middleware→proxy).** **➡️ LANJUT (urutan 9.3 Area 3):** **E1 Tenants + Trial-Leads** (data bypass-RLS via server-route service_role) → **E5 Pricing** → **E2.3 Niche**. *(Tertunda-gate: credentials/OAuth=owner Google; schedule→D7; analytics→9.4.)* FE = **anon+RLS; config-write = RPC whitelist; admin data = server-route service_role**. Migrasi v2 = **0001-0033** (tak nambah — app-layer + auth account).
- **➡️ LALU = 9-10** FE wiring/sinkronisasi (long pole) → **11** beta. *(follow-up: 6.2 voice rotation + 6.4 per-tag saat sistem tag/voice-catalog, ~P9-10.)*
- **🆕 .env (2026-06-14):** root `.env` di-switch v1→v2 (service_role) — dulu run v2 via override inline; kini default v2 (foot-gun worker→v1 hilang). Detail [[project_env_supabase_target]].
- **Keputusan Phase 6 (sudah diputus, default):** cadence fetch+compute 24j (config) · 6.2 voice-rotation pakai voice yang ada dulu (katalog voice = nyambung TTS-catalog-wiring) · AI disclosure = toggle, default ON.
- **Gate owner:** cutover (deploy + flip). *(ElevenLabs re-subscribe / E3 = ✅ SELESAI 2026-06-17: owner topup OpenAI+ElevenLabs ryan, kuota aktif.)* → **§GATE CUTOVER (F1, B1)**.
- **FE gap WAJIB (Phase 9-10), semua OPSIONAL/non-breaking:** format/preset picker · Branded panel (→ status & arsitektur **kanonik**: [`BRANDED_CONTENT_ARCHITECTURE.md`](BRANDED_CONTENT_ARCHITECTURE.md)) · privacy toggle (channel settings, default private) · provider-mgmt UI (E2) · live-tail→pipeline_run_logs · Supabase Auth.

#### Branded Content (CTA · logo · link landing) — status bertahap
> **Sumber kebenaran tunggal = [`BRANDED_CONTENT_ARCHITECTURE.md`](BRANDED_CONTENT_ARCHITECTURE.md)** (spec konsep: `MULTI_FORMAT_STUDIO.md §6`). Bila dokumen lain berbeda → file itu menang.
- [x] **DB** — kolom `channels` (migr `0015_branded_content`): `cta_mode`,`brand_name`,`brand_cta_text`,`brand_logo`,`logo_position`,`logo_size`,`logo_opacity`,`landing_link`,`link_position`.
- [x] **BE — soft-sell CTA** (`script_engine.py:285,355`): `cta_mode='soft_sell'`+`brand_name` → satu sebutan brand halus (hard-sell tetap dilarang).
- [x] **BE — logo overlay** (`video_renderer.py:937` `_overlay_logo`, fail-soft, posisi/ukuran/opacity; image_sequence & ai_video).
- [x] **BE — link landing di deskripsi** (`youtube_publisher.py:153`; `link_position` top\|bottom).
- [ ] **FE** — panel "Branded" di `/channels/[id]`: CTA (radio + `brand_name`) · upload logo + pemilih posisi + slider ukuran/opacity + preview · `landing_link` + posisi. Tulis via RLS UPDATE `channels`.
- [ ] **Storage** — bucket/lokasi upload logo → simpan URL ke `brand_logo` (BE sudah terima URL http).

**JANGAN diulang (sudah dikerjakan):** Phase 0 audit ✅; framing v1/v2 (terkunci); **frontend track ✅ (28 screen)**; **backend Phase 1-5 ✅** (clone DB v2 ✅, decouple terbukti). Deploy backend v2 ke VPS = **cutover** (keputusan operasional owner, bukan "jangan") — v1 tetap jangan disentuh sampai saat itu.

> **🧭 KEPUTUSAN ARAH (2026-06-12, senior call):** frontend track selesai di milestone bersih (audit clean, 28/28 build) → **pivot ke jalur kritis BACKEND** (poles infra next-intl/shadcn/PWA DITUNDA — gold-plating layar mock; next-intl akan rework i18n saat wiring data). **2 gate butuh user:** (1) **PUSH** ke origin (21+ commit belum di-backup — risiko tertinggi), (2) **clone DB v2** (gate eksekusi backend — user buat Supabase project). Rencana Phase 1.1 + rekonsiliasi sudah LOCKED (§1.1) → eksekusi instan saat DB siap.

**Clone DB v2 = ✅ DONE (2026-06-12)** — v1 `hiwkgxhkjanggeskjjen` (produksi, Tokyo) → v2 `atliatnjhysdibmfypul` (Singapore), via **psycopg2 + Session pooler IPv4** (pg_dump tak dipakai: server PG17.6, client default 16; direct conn IPv6-only). 13 tabel + data + 24 constraint + 40 index + 3 seq + 2 func + 8 RLS — **struktur & row count identik (verified)**. pg_cron jobs SENGAJA tak di-clone (v2 dev tak auto-produksi). **Akses dev:** direct psycopg2 ke v2 via pooler (write) — MCP tak jadi dipakai (butuh restart sesi). **Gate backend terbuka.**

> ⛔ **GUARDRAIL WIRING (verified 2026-06-12: apps/web = 100% mock, NOL wiring):** JANGAN tulis satu baris koneksi Supabase pun (client/`@supabase/supabase-js`/`.env`/`NEXT_PUBLIC_SUPABASE_*`/query) SEBELUM clone DB v2 ada & env diarahkan ke **DB baru** (bukan v1). Wiring pertama = clone dulu. Ini supaya wiring tidak pernah nyasar ke DB produksi v1.

---

## 🔧 PERBAIKAN PRODUCE & PUBLISH (PRA-CUTOVER) — luruskan DB/BE/FE ke arsitektur §12c

> **WAJIB SELESAI PENUH SEBELUM §GATE CUTOVER dijalankan.** Centang [x] HANYA bila item **sudah dibuat DAN tervalidasi berjalan 100%**. V1 produksi JANGAN disentuh (semua di v2).

**Kenapa ada (akar masalah, ditemukan saat audit wiring 2026-06-16):** "jadwal" tercerai-berai di 3 tabel & **FE menulis ke tabel beda dari yang dibaca BE** (FE→`production_schedules`, BE→`channels.publish_slots`), plus sisa-sisa V1 (`production_schedules` niche-per-jam, `tenant_configs.publish_slots`, `*.production_cron`, `worker.py`) yang melawan §12c. Akibat: jadwal yang diatur tenant tak dipakai mesin, channel baru tak punya jadwal, niche-per-jam bertentangan dgn rotasi pool.

**Model TERKUNCI (acuan perbaikan):**
- **§12c:** PRODUKSI = digerakkan **defisit buffer** (TANPA jadwal-waktu) · PUBLISH = digerakkan **slot** (jadwal). Hanya PUBLISH yang dijadwalkan.
- **Hierarki:** TENANT (1 tier, 1 timezone) → **N CHANNEL** (≤ `max_channels`). Tiap channel: **niche** (fixed=1 / random=putar **SELURUH entitlement tenant**) + **jadwal publish** (`publish_slots`, N/hari ≤ `max_videos_per_day`). **Niche & jadwal TERPISAH.**
- **Sumber kebenaran jadwal = `channels.publish_slots`** (jam, ditafsir di `tenant_configs.timezone`). Ditulis FE ↔ dibaca BE.
- **Entitlement niche tenant** = niche dasar (trial/starter) / semua-aktif (pro/business) + custom/private milik tenant.

### A. DB
- [x] **A1** — Tambah `channels.buffer_depth` (target stok ready per-channel, §12c "tren=1/evergreen=3-5"; NULL→default env). migr 0045, verified. *(2026-06-16)*
- [x] **A2** — ~~Tambah `niches.exclusive_tenant_id`~~ → **DIBATALKAN**: kolom pemilik niche **SUDAH ADA** = `niches.exclusive_to` (+ `exclusive_until`/`released_at`/`access_type`, migr 0037). Pakai itu; tak perlu kolom baru. *(2026-06-16)*
- [x] **A3** — Tabel baru `niche_requests` (pengajuan custom niche): `tenant_id, channel_id, request_type(public_90d|private), title, clues jsonb, status, price_key, niche_id, admin_note, ...` + RLS tenant-own (insert/read), admin via service_role. migr 0045. **Validated** (temp authed user: insert own ✓, read scoped ✓, cross-tenant insert blocked ✓). *(2026-06-16)*
- [x] **A4** — Migrasi data ryan V1→V2: channel `niche_mode` fixed→**random** (sesuai V1; business=entitlement 4 niche), `publish_slots` `['20:00']`→**`['06:00','21:00']`** (konversi V1 `['14:00','23:00']` UTC→WIB, momen US-peak sama), `buffer_depth`=3 (§12c). Hapus 5 baris `production_schedules` stale (channel_id string lama). *(2026-06-16; data-only)*
- [x] **A5** — Fosil V1 dipensiunkan (migr 0047, setelah BE+FE lepas — verified nol pembaca kode): **`production_schedules` DI-DROP**. Kolom vestigial (`channels.production_cron`/`niche_pool`, `tenant_configs.publish_slots`/`production_cron`/`analytics_cron`) DIBIARKAN tapi `COMMENT … DEPRECATED` (loader baca default aman; drop=risiko, nilai rendah). DB_SCHEMA=39 tabel. *(2026-06-16)*
- *(Di luar scope: `niches.tag_pool` / Layer-2 sub-tag = epik terpisah.)*

### B. BE
- [x] **B1** — niche: ScheduleManager Layer-1 (`production_schedules`) **DIBUANG** dari `pipeline.py`. `niche_mode=fixed`→`channels.niche`; `random`→rotasi **seluruh entitlement** (`entitled_niches` = katalog per-tier + `exclusive_to`) via `DiversityEngine.pick(channel,"niche",...)`. helper baru `limits.entitled_niches`. **Validated** (business=4, trial=3 base, pick OK). *(2026-06-16)*
- [x] **B2** — Producer baca `channels.buffer_depth` (kode `ch.get("buffer_depth") or default`; ryan=3 verified).
- [x] **B3** — RPC `set_channel_niche` (niche ⊆ entitlement) + `set_channel_publish_slots` (≤ tier cap), SECURITY DEFINER scope auth.uid() (migr 0046). **Validated** (base ok/non-base trial ditolak · 1 slot ok/2 ditolak · channel-bukan-milik ditolak · persist).
- [x] **B4** — Publisher TANPA perubahan (tetap baca `channels.publish_slots`+`tenant_configs.timezone`+`daily_publish_cap`) → nol regresi. compileall src PASS.
- [x] **B5** — Hapus `scripts/worker.py` (monolit V1) + `src/intelligence/schedule_manager.py` (nol importer pasca-B1; `production_schedules` tak lagi dibaca BE). *(2026-06-16)*

### C. FE
- [x] **C1** — Halaman Jadwal di-rewrite: channel-centric, baca/tulis **`channels.publish_slots`** (JAM saja, zona tenant) via RPC `set_channel_publish_slots` (validasi N ≤ tier). `production_schedules` & niche **dilepas** dari UI. build PASS. *(2026-06-16)*
- [x] **C2** — Onboarding + `/channels/new`: INSERT channel kini set `publish_slots: ["13:00"]` (default ≤ semua tier) → channel baru punya jadwal. build PASS.
- [x] **C3** — Editor niche per-channel di **Channel Detail** (Settings): pilih `niche_mode` fixed/random + niche (opsi **dari entitlement** tenant) → RPC `set_channel_niche`. Menggantikan "niche write-once". build PASS.
- [x] **C4** — Form ajukan custom niche (Config→Niches) **FUNGSIONAL**: type public-90d/private + judul + clue → insert `niche_requests`. **+ Admin panel (E2.3, `/api/admin/niche-requests`):** antrian request + approve (buat niche `exclusive_to`=tenant, public_90d→`exclusive_until`=+90h / private→permanen) / reject. **Loop e2e LULUS**: tenant ajukan → admin approve → entitlement tenant bertambah → tenant set channel ke niche custom-nya. Admin route 401-gated. build PASS (51 route).
- [x] **C5** — Batas tier tampil: Jadwal "max N/hari/channel" + "N/cap slot"; opsi niche dibatasi entitlement. *(via C1+C3)*

### D. Validasi e2e — ✅ SEMUA LULUS (temp authed user, key+RLS identik FE; 2026-06-16)
- [x] Buat channel (default slot `['13:00']`) → baca/ubah jadwal via RPC `set_channel_publish_slots` → tersimpan di `channels.publish_slots` (publisher baca sini, bukan production_schedules).
- [x] `random` → `entitled_niches` = seluruh entitlement (business=4, trial=3 base) + DiversityEngine.pick; niche di luar entitlement **ditolak** RPC (fun_facts utk trial ditolak).
- [x] Ubah niche channel pasca-buat (fixed/random) via RPC → tersimpan.
- [x] Ajukan custom niche → `niche_requests` terisi (judul+clue) + **admin melihatnya** (audience/refs/angle).
- [x] Cap tier: 1 slot trial ok / 2 ditolak. Channel orang lain ditolak. py_compile BE OK · build FE PASS · grep `production_schedules` di kode = komentar saja.

**🎉 PERBAIKAN PRODUCE & PUBLISH SELESAI 100% (A+B+C+D + admin niche-requests, 2026-06-16).** Migr v2 = 0001-0047. **Loop custom-niche tertutup penuh** (tenant ajukan → admin proses → eksklusif → entitlement). GATE CUTOVER boleh dijalankan.

---

## 🧠 IMPROVEMENT — QC Self-Healing + Trend Radar (kualitas viral & skala)

> **Plan AKTIF (sumber-kebenaran-tunggal track ini).** Disisip sebelum §GATE CUTOVER. Centang `[x]` **HANYA** bila script/fungsi **sudah dibuat DAN tervalidasi berjalan 100%** (aturan owner 2026-06-16). Desain rinci = `QC_CONTENT_ARCHITECTURE.md` + `TREND_RADAR_ARCHITECTURE.md` (doc = desain/roadmap; PROGRESS = checklist status). Semua angka/sumber/provider **config-driven, no-hardcode**. V1 produksi JANGAN disentuh.

**Relasi ke cutover (anti-ambigu):** ini track **polish kualitas & skala**, BUKAN prasyarat keras single-tenant cutover (beda dari §PERBAIKAN PRODUCE & PUBLISH). Namun: **A+B disarankan mendarat sebelum produksi diandalkan** (dgn ElevenLabs ryan lapse, QC-fail saat ini menghapus video diam-diam — A/B mengubahnya jadi private+advisory). **C** = polish marketing (sebelum publik). **D1 (doc) + D2 (F1 cache)** = **prasyarat sebelum skala banyak tenant** (cegah 429 IP-based), bukan blocker cutover ryan.

**Urutan eksekusi (owner "mulai dari eksekusi 1 lalu 2"):** #1 sinkron doc QC = ✅ DONE (changelog QC 2026-06-16). #2 = **A + B**. Lalu **C**, lalu **D**.

### A. QC-fail → Self-Healing: publish PRIVATE + advisory (Opsi A) — `QC §3/§6.2`
- [x] **A1** — `pipeline.py` blok QC-fail: **hapus `unlink()` pra-upload** → set `tenant_config.publish_privacy="private"` → publish via `youtube_publisher.publish(...)` (jalan di **kedua** jalur producer `publish=False` & direct `publish=True`) → isi `result["published"]["youtube"]` → `write_qc_failed(url=...)` (videos status qc_failed) → advisory → bersihkan lokal. **Buffer tetap murni** (`produce_one` cek `steps.qc.passed` → QC-fail tak masuk buffer). Publisher tak diubah. **Validated e2e (lihat A4).** *(2026-06-16)*
- [x] **A2** — Advisory Telegram: `notify_qc_fail` → **"di-publish PRIVAT untuk ditinjau"** + alasan + **rekomendasi DINAMIS** (no-hardcode) + **URL privat** + "Anda putuskan publik/hapus". **Validated** (unit: pesan memuat PRIVAT+url+Saran+putusan; pesan lama "tidak dipublish" hilang). *(2026-06-16)*
- [x] **A3** — `write_qc_failed` terima `url` → simpan ke `videos` (status `qc_failed`, qc_passed False, +url privat); alasan QC tercatat (logger ctx run_id → pipeline_run_logs, infra existing). **Validated** (unit: record berisi status/qc_passed/url). *(2026-06-16)*
- [x] **A4** — **e2e nyata LULUS** (2026-06-16, direct-produce ryan, owner-authorized): QC-fail durasi terpicu (`48.3s` di luar ±15% target 60s — skrip 73w < budget 108w) → **publish PRIVAT** `youtube.com/shorts/ermbEg-Qess` (privacy=`private` **terverifikasi via YouTube API**) → **advisory Telegram TERKIRIM** (chat 8699847842, rekomendasi dinamis) → `production_runs.status=qc_failed`/`qc_passed=false`/url terisi (BUKAN mislabel success) → `direct_jobs=published` → video **tidak dihapus**. run_id `direct-0f73a253`.

### B. Transparansi fallback TTS (no-hardcode) — `QC §0.3` + `§4b` (parsial)
- [x] **B1** — `tts_engine.py`: concern fallback **dinamis** (`_fallback_concern(prev,next)` pakai nama provider dari config) — literal "ElevenLabs"/"Edge"/"OpenAI" **dibuang** dari pesan (sisa hanya docstring/komentar/nama-kelas-import). **Validated** (unit: concern memuat nama dinamis, nol literal vendor). *(2026-06-16)*
- [x] **B2** — Engine **expose provider aktual**: `last_primary`/`last_provider`/`last_fallback_used` (di-set tiap `generate`) → `pipeline.run` catat ke `result["steps"]["tts"]` (`configured_provider`/`provider_used`/`fallback_used`) → dipakai advisory A1. **Validated** (unit: atribut init + ter-set; py_compile). *(2026-06-16)*
- [x] **B3** — Validasi unit: TTSEngine attrs + concern dinamis · Telegram advisory · `write_qc_failed(url)` · `run_direct` status-mapping NYATA (success/qc_failed/failed via fake sb+Pipeline). **PASS** (`/tmp/val_qc_advisory.py`). *(2026-06-16)*
- *(F7 penuh — checkbox consent lanjut-vs-stop per-komponen + flag `content_inventory.metadata` + alert kredit BYOK — = epik terpisah, tetap di `QC §4b/F7`. Di sini hanya transparansi minimal yang menopang advisory.)*

### C. Landing — pipeline looping 11-simpul (animasi)
- [x] **C1** — Marketing page (`(marketing)/page.tsx`): **circuit 2-baris** — BARIS ATAS 8 node produksi (brand, glow statis TETAP), BARIS BAWAH 3 simpul umpan-balik accent (kiri→kanan: **Self-improvement**/`TrendingUp` di bawah Trend Radar · **Self-learning**/`Brain` · **Report→Telegram**/`Send` di bawah Publish) via grid 8-kolom (col1/4-6/8 selaras track). + baris `.pipe-loopback` "↺ kembali ke Trend Radar". Lead diperbarui. **build PASS.** *(layout/animasi = review visual owner :3000)* *(2026-06-16, revisi per owner)*
- [x] **C2** — Label **"8 langkah"→"11 langkah"**; **track SVG rounded-rect** (`landing.css`) dgn **cahaya mengalir** (`tk-flow` stroke-dasharray + `@keyframes pipe-race` stroke-dashoffset, `pathLength=100` responsif, `vector-effect non-scaling-stroke`) mengelilingi loop: atas 1→8 → turun kanan → bawah R→L → naik kiri → **balik ke Trend Radar (ikon 1)**. Glow ikon **tidak** dianimasi (fix bug shadow hilang). `prefers-reduced-motion` aman. **Responsif: tinggi & posisi baris DIKUNCI px** (`.pipe-circuit-in` height fixed, baris anchor-by-top, label nowrap) → track selalu sejajar ikon di semua lebar; layar sempit scroll-horizontal 1-unit (fix "berantakan di layar kecil"). build **✓ Compiled successfully**. *(2026-06-16, revisi per owner)*

### D. Trend Radar — revisi arsitektur + build bertahap — `TREND_RADAR_ARCHITECTURE.md`
- [x] **D1** *(doc — SELESAI + owner setuju, sinyal LIVE-VALIDATED)* — `TREND_RADAR_ARCHITECTURE.md` direvisi: **§2b rasio bobot** (`source_weights` config-driven: YouTube velocity PRIMER ~0.45 · Trends ~0.30 · News ~0.13 niche-flag · Wikipedia ~0.07 filter-only · HN ~0.05 tech-only, Wiki&HN kandidat-drop) · **§2c inventaris sinyal YouTube + status validasi** · **§3 out-of-the-box** (velocity mining + pola channel-sendiri + agregat lintas-tenant) · **§4a self-learning vs self-improvement + diagram loop** · §6/§7/changelog. **Validasi LIVE (ryan):** Analytics API scope+data NYATA (avg_view_pct **67.72%**, trafficSourceType SHORTS/SEARCH/…), autocomplete live, Trends-youtube 429(→cache), Data API quota-limited. *(2026-06-16)*
- [ ] **D2 — F1 Decouple + cache (kritikal scaling 429, NOL kredit AI):**
  - [x] **F1a** — migr **0048** `trend_cache` (cache_key unik niche+geo+source+timeframe, signals jsonb, fetched_at, ttl_sec) + RLS **service-role only** + config `app_config.trend_cache_ttl_sec`(43200)/`trend_refresh_pacing_ms`(3000). **Applied v2 + verified** (10 kolom, RLS on, 40 tabel). DB_SCHEMA_V2.md diupdate. *(2026-06-16)*
  - [x] **F1b** — `src/orchestrator/trend_refresher.py` (`run_once`/`run_forever`) + thread di `worker_decoupled`. Loop **niche-aktif × geo-aktif** (§5: O(niche×geo)) → `radar.refresh_niche_geo` (trends/yt/news per niche+geo) + `radar.refresh_global` (HN/Wiki sekali). **only_stale** (skip cache fresh) + **pacing** `app_config.trend_refresh_pacing_ms` (anti-429). yt key = platform env (graceful kosong). *(2026-06-16)*
  - [x] **F1c** — `trend_radar.scan()` **baca `trend_cache`** (`_read_cache` per sumber), **NOL panggil sumber eksternal**; graceful (cache kosong → sinyal minim + warning, produce lanjut). + helper `_cache_sb/_read_cache/_write_cache/_cache_age_sec`. *(2026-06-16)*
  - [x] **F1d** — **Validasi LIVE PASS:** refresher tulis 5 cache (news20/HN6/wiki10; trends0=429-graceful/yt0=no-key); **run#2 tulis 0 (staleness)**; **scan 0.72s baca 36 sinyal, NOL fetch eksternal** → 429 hanya di refresher (paced), hot-path kebal. py_compile 3 file PASS. *(2026-06-16)*

  **🎉 F1 SELESAI** — fix scaling 429 (M1) terbukti: produce decoupled dari sumber, request_sumber konstan vs tenant. Migr 0048. **Sisa radar (F2 sumber+bobot · F3 ukur-dimensi · F4 self-improvement) = propose-first.**
- [ ] **D2** — **F1 Decouple + cache** (KRITIKAL skala 429, **nol kredit AI**): tabel `trend_cache` + `TrendRefresher` (thread paced di `worker_decoupled`, TTL config `app_config`) + produce **baca cache** (tak panggil sumber langsung). Validasi: produce nol-fetch-eksternal + refresher tulis cache + resilient saat sumber 429.
- [x] **D3 — F2 Sumber + bobot (buildable parts SELESAI + validated):** migr **0049** `source_weights` (config app_config trend_weight_*, §2b) · `niche_selector._prepare_signals_summary` **terapkan bobot** (urutan + jumlah item ∝ bobot) · **filter-niche HackerNews** (M2 — buang HN off-niche) · **Wikipedia di-DROP** dari seleksi (§2b verdict; de-facto sudah unused) · **autocomplete** sumber demand baru (`_get_youtube_autocomplete`, gratis, di refresher+scan+summary). **Validated** (unit summary + autocomplete live 18 query + cache roundtrip). *(2026-06-16)*
  - [x] **YouTube velocity mining — SELESAI + LIVE-VALIDATED** (`_get_youtube_trending_search`: 1 search OR-join → `videos.list?part=statistics` batch → **velocity=views/jam**, terurut; ~101u/niche frugal §7; key=`YOUTUBE_PLATFORM_API_KEY`). niche_selector summary surface views+velocity (angka NYATA). **Live (universe_mysteries):** 25 video, top **349.504 views/jam**; rantai fetch→cache→scan→summary PASS. **Key GCP:** ✅ **restricted ke IP VPS `103.103.22.227`** (owner, 2026-06-16) — dev tak bisa panggil lagi (normal; uji selesai), worker VPS jalan saat deploy. *(velocity live-validated sebelum restrict.)*
    - 📌 **Refinemen presisi (→F3):** velocity bawa sedikit noise lintas-niche (mis. teaser film); **hard keyword-filter merugikan recall** (buang "Moon/NASA" relevan, simpan "Marvel universe" noise) → sekarang LLM kontekstualisasi; fix robust = `videos.list?part=topicDetails` (kategori topik, 1 unit sama) di F3.
- [x] **D4/F3a — Presisi relevansi `topicDetails` SELESAI + validated.** Fetcher tambah `part=topicDetails` (1 unit sama) → `topic_categories` per video. **Temuan data nyata (2026-06-16):** topicCategories YouTube **terlalu kasar** utk filter POSITIF (relevan sering ke-tag `entertainment`/kosong → salah-buang) → **rencana mapping-positif niche→topik DIBATALKAN**. **Pivot AMAN:** topicDetails dipakai sbg **denylist** (buang yang topiknya MURNI game/musik/olahraga) + **LLM penilai relevansi UTAMA**. Validated (Lego/gaming dibuang; Moon/NASA/kosong tetap). *(2026-06-16)*
- [x] **D4/F3b — Skor dari angka NYATA SELESAI + validated.** `_apply_signal_factor` (pola `_apply_historical_factor`): boost viral_score per-topik yang **SELARAS sinyal nyata meledak** — YouTube **velocity** (overlap ≥2 kata → ×s/d 1.25 ∝ velocity) + Trends **momentum** positif (×s/d 1.10). Hanya menaikkan; base dimensi LLM tetap; fail-soft; di-wire di `select()` + re-sort. **"Ukur, jangan menebak"** tanpa refactor berisiko. Validated (selaras→boost bounded; tak-selaras/kosong/momentum-negatif→tak berubah). *(2026-06-16)*
- [ ] **D5 — F4 Self-improvement** *(sebagian SUDAH ada; sisanya DATA-GATED):* learned `viral_score_weights` + `channel_insights` + `historical_factor` **sudah jalan**. Baru: kalibrasi `source_weights` dari outcome + panen sinyal Analytics kaya (trafficSource/retensi/CTR — `channel_analytics` sebagian sudah) → butuh **akumulasi analytics nyata** (post-cutover, nyambung §GATE CUTOVER E3). Mekanisme siap, aktivasi = data.

### E. Temuan e2e 2026-06-16 (PR to-be-solved — disurvei dgn bukti kode/DB, NOL asumsi)
> Muncul saat validasi A4 (run `direct-0f73a253`). Akar sudah ditelusuri; perbaikan menunggu giliran. Centang setelah fix + validasi 100%.
- [x] **E1 — Thumbnail upload timeout (robustness).** AKAR: `youtube_publisher.publish` video pakai resumable+**retry 3×** (`:244-256`), tapi `_upload_thumbnail` `thumbnails().set().execute()` (`:335`) **tanpa retry** → transient *read timeout* → thumbnail dilewati (non-kritis, video tetap publish). FIX: **`.execute(num_retries=3)`** (exponential backoff googleapiclient, retry socket.timeout). py_compile PASS; konfirmasi penuh di publish berikut (timeout tak bisa diinduksi murah). *(2026-06-16)*
- [x] **E2 — Music cross-niche fallback.** AKAR (premis "tiap niche punya library" BENAR — universe_mysteries=7 track dramatic/tense/mysterious): mood terdeteksi `ominous` (milik dark_history) tak ada di niche → cascade `_query_tracks` step-2 "mood-only lintas-niche" menang sebelum coba track niche-sendiri → ambil `shadow_empire` (dark_history). FIX (robust, semua jalur): **tambah step-1b di `_query_tracks`** — coba **niche + mood_priority (track niche-sendiri)** SEBELUM lintas-niche. **Validated** (query nyata: `(universe,ominous)`→3 track universe/dramatic, bukan dark_history; regresi niche+mood-ada tetap step-1). *(Supersede kebutuhan inject preferred_mood di run_direct — selector kini niche-safe by-design. Gap data track `epic`/`ambient` universe = tugas kurasi admin, bukan bug kode.)* *(2026-06-16)*
- [ ] **E3 — Akurasi durasi: length-gate LLM (akar-b QC §2).** Skrip 73w < budget 108w meski EL jalan → 48.3s. `script_engine` length-gate retry 3× lalu pakai best-available (78/100, tetap pendek). ANALISIS (#5): skor 78 = ScriptAnalyzer (LLM-judge tulisan, BEDA dari skor topik trend-radar 78.6). FIX: length-gate lebih tegas (retry s/d ≥ budget×toleransi atau prompt pemaksa-panjang) + WPS-follow-actual-provider — masuk QC F3/F5 (propose-first). *(Sudah didokumentasikan di `QC_CONTENT_ARCHITECTURE.md §2` akar-KEDUA.)*
- *(#1 YouTube API quota habis → diselesaikan di **plan D** trend radar. #3 smart-focus insight "0% retention" (avg_view_pct=0) → diselesaikan di **plan D** ATAU **§GATE CUTOVER E3** — diputuskan saat itu, jangan diasumsikan sekarang.)*

---

## 🔐 ADMIN SYSTEM SECRETS — editable di panel (RENCANA, PRA-GO-LIVE)

> **Owner 2026-06-16:** platform/system secrets (kini di `S3-CONNECTION.md`/`.env`) sebaiknya **editable di admin panel** (bukan hanya file/env), **termasuk** key lain di S3-CONNECTION. **Minimal direncanakan + dieksekusi SEBELUM go-live.** Centang `[x]` setelah dibuat+validasi 100%.

**Prinsip keamanan — kategori secret (KRUSIAL, jangan dilanggar):**
- **Kategori A — BOLEH admin-config** (DB Fernet, service-role-only, audit) — integrasi/operasional yang bisa di-rotate tanpa bootstrap: **YouTube platform API key** · **Midtrans** (merchant/client/server) · **SMTP** (host/port/user/pass/from) · **Biznet/Neo S3 buffer** (endpoint/access/secret/bucket) · (opsional) `OAUTH_STATE_SECRET`.
- **Kategori B — WAJIB tetap ENV/VPS-only** (bootstrap; TAK bisa di-DB): **`ENCRYPTION_KEY`** (master Fernet — chicken-egg, tak bisa simpan terenkripsi pakai dirinya sendiri) · **`SUPABASE_KEY` service_role + DB password** (dibutuhkan untuk MENCAPAI DB tempat secret disimpan) · **`MV_INTERNAL_SECRET`**.
- **BUKAN bagian ini:** tenant BYOK (AI keys + YouTube OAuth) = TETAP per-tenant (`tenant_credentials`/`tenant_configs`).

**Rencana eksekusi (pra-go-live):**
- [ ] **S1** — migr `system_secrets` (`key` PK, `value_enc` Fernet, `category`, `updated_by`, `updated_at`) — RLS **service-role only** (pola `tenant_credentials`). + update `DB_SCHEMA_V2.md`.
- [ ] **S2** — loader `src/config/system_secrets.py`: baca DB (Fernet decrypt) → **fallback env** (transisi mulus; env tetap valid). Worker/webhook pakai untuk Kategori A.
- [ ] **S3** — admin page `/admin/integrations` (service-role, `requireSuperAdmin`): status (set/kosong, **masked**) + set/rotate per-secret + **"Test koneksi"** (reuse pola Test Lab). Audit→`admin_audit`. Kategori B = read-only note "env-managed" (tak editable).
- [ ] **S4** — seed nilai env→DB + validasi (worker baca dari DB; rotate dari panel berlaku; restart-safe).

**Status sekarang:** semua secret operasional dari **env/`.env`** (incl. **`YOUTUBE_PLATFORM_API_KEY`** baru ditambah dari S3-CONNECTION, SET). Ini interim sah sampai S1-S4. **Pointer di §GATE CUTOVER.**

---

## 🎨 RENCANA KERJA — IMAGE-GEN PER-PRESET + LLM 2-TAHAP (Opsi A) + AKURASI DURASI (Cacat B)  [AKTIF 2026-06-17]

> **Status (2026-06-17):** **✅ CACAT A SELESAI + DEPLOYED (`e964a9e`)** — image-gen 2-tahap + VISUAL DNA (no-hardcode, 4 niche), validated 6 preset, ryan **UNPAUSED + produksi jalan** (preset 60s lolos QC). Spec di MULTI_FORMAT §3+§10. **⚠️ TERSISA = CACAT B** (durasi 15s/30s overshoot) — root-cause + plan di FASE 2 (B2) bawah. *(QC §2 + DESAIN §12b pointer ditulis saat Cacat B tuntas.)*
>
> **Arsitektur (disepakati owner):** Tahap-1 LLM = narasi saja (→ TTS → caption) ⟂ Tahap-2 LLM terdedikasi = prompt-image per-beat (→ image-gen). Clue prompt per-scene = **teks beat FINAL + niche_visual_style + peran arc**. Per-tenant: durasi→preset(beat/budget/jumlah-image) · niche→style/voice/speed/timing · topik→narasi+clue.

**FASE 1 — Cacat A (prompt image konsisten, tahan model murah):** ✅ **VALIDATED-LOKAL (6 preset, prompt bersih 6/6), pending deploy.**
- [x] A1 — STEP 3 = **Tahap-1 narasi saja** (skema JSON bersih, slot `core_facts_2`, array malformed dibuang). ✓ validated
- [x] A2 — **Guard beat aktif non-kosong** (tolak→retry). ✓ validated
- [x] A3 — **STEP 4.5 = Tahap-2** (1 LLM call pasca hook-optimize; thumbnail + N−1 prompt; through-line+variasi). ✓ validated
- [x] A4 — **Sanitize/guard** ("N/A"/kurung/echo/kosong) + **fallback ekstraktif**. ✓ validated
- [x] A5 — **scene-hook = thumbnail_concept** (no-waste: Hook-frame + N scene). ✓ validated
- [x] A6 — **Ken-Burns motion BEAT-ROLE-aware** (role→motion). ✓ validated
- [x] **VISUAL DNA (no-hardcode):** Tahap-2 inject SELURUH key `visual_style`(=visual_dna) generik + `style_exemplars` (eks-visual_fallbacks) + mandat "beauty-first". `visual_dna` universe_mysteries diperkaya 10-key (admin-editable via `/admin/niches` JSON; update-API whitelist). ✓ validated (60s sinematik). **3 niche lain belum diisi.**

**FASE 2 — Cacat B (akurasi durasi → lolos QC):** ⚠️ **SEBAGIAN.**
- [x] B1 — **budget speed-adjust** (`detik × delivery_wps × niche_speed`, EL ×0.9→1.62). → **45/60/75/90 LOLOS** ✓. 15s/30s masih overshoot.
- [ ] B2 (REFRAMED — root-cause data: bukan delivery/v1, tapi **LLM melebihi word-budget §3 di preset pendek**; TTS sudah benar): **PAKSA kepatuhan word-budget §3 di preset pendek** — hard word-cap per beat di BEAT PLAN (ultra-terse) + length-gate batas-atas lebih galak (pangkas saat > budget×1.12). Validasi 15s/30s masuk window. *(Bukti: bila LLM patuh, 15s→24kata÷1.43=16.8s LOLOS, 30s→49÷1.65=29.7s LOLOS.)*

**VALIDASI & RILIS (SOP):**
- [x] V1 — Validasi SOP lokal 6 preset: image=visual_beats ✓ · prompt BERSIH 6/6 ✓ · universe 60s sinematik ✓ · durasi: 45/60/75/90 lolos, 15/30 overshoot (Cacat B). *(2026-06-17)*
- [x] V2 — **Cacat A DEPLOYED** (`e964a9e` → VPS pull → mv-worker restart active → **ryan UNPAUSED**, preset 60). *(2026-06-17. Cacat B menyusul.)*
- [x] V3 — SPEC ditulis: **MULTI_FORMAT §3 + §10** (arsitektur 2-tahap + VISUAL DNA + status Cacat B). *(QC §2 + DESAIN §12b pointer = saat Cacat B tuntas.)*

**FUTURE (catat — JANGAN ubah tanpa keputusan owner; melanggar kontrak N=visual_beats):** >1 image per beat-panjang utk retensi · image-gen paralel TTS (latency) · quality-tier per kebutuhan viral.

---

## 🛑 INSIDEN RUNAWAY PRODUKSI (2026-06-17) — ✅ RESOLVED + DEPLOYED (Opsi C)

> **STATUS: SELESAI 2026-06-17.** Akar (producer loop tanpa rem + Opsi A producer-publish) diperbaiki via **Opsi C** (lihat §PERBAIKAN ARSITEKTUR PRODUKSI v2 di atas) — deployed (commit `53d4720`), **mv-worker RESTARTED + AMAN** (circuit-break terbukti: runaway tak terulang, 0 kredit). **UPDATE 2026-06-17 (lanjutan):** **E3 ElevenLabs+OpenAI = ✅ DI-TOPUP owner (kuota aktif, EL TTS premium nyata).** ryan kini **PAUSED-manual sementara** untuk **validasi image-gen per-preset** (bukan lagi auto-pause-0-kredit pending-E3) — lihat journal entri TERATAS. Riwayat insiden di bawah (arsip).


> **State kritis.** `mv-worker` **SENGAJA di-stop** (`sudo systemctl stop mv-worker`) untuk hentikan runaway. **Produksi+publish HALTED, nol pembakaran kredit.** ⛔ **JANGAN restart** sebelum #2 & #3 beres. `mv-web` normal.
- **Gejala:** channel ryan produksi nonstop tiap ~10 mnt. **Fakta (verified DB+kode):** `content_inventory` ryan = **29 row SEMUA `failed`, 0 ready**. Alasan NYATA (query metadata.error): **22× "produce/QC gagal"** (generik — akar TAK tercatat, BELUM diverifikasi) · 4× "Video rendering failed" · 3× "Visual assembly — no clips" (image-gen). ⚠️ image-gen cuma 3/29; mayoritas generik → **akar per-kategori WAJIB diverifikasi sesi baru, JANGAN asumsi**. ElevenLabs habis kredit tapi fallback edge_tts berhasil → bukan penyebab.
- **Mekanisme:** produksi = **buffer-deficit-driven, BUTA jadwal** (`producer.py:204 plan_and_submit`, `target=buffer_depth=3`, loop 10s). Gagal → `ready` selamanya 0 → defisit 3 tiap siklus → produksi nonstop. **Satu-satunya rem = buffer terisi; rusak saat gagal; tak ada rem cadangan.** Publish (publisher.py) = schedule-driven terpisah, TAK terlibat.
- **Lubang = §4b/F7 (QC_CONTENT_ARCHITECTURE) BELUM DIBANGUN** ("komponen gagal → item DIHENTIKAN + alert keras, BUKAN loop bakar-kredit"). Cutover deploy worker live tanpa pengaman ini + tanpa validasi loop-kontinu.
- **➡️ PRIORITAS (urut):** (1) ⛔ jangan restart mv-worker · (2) **root-cause kegagalan per-kategori** (22 generik "produce/QC gagal" + 4 render + 3 image-gen — verifikasi nyata dari pipeline_run_logs/log, JANGAN asumsi penyebab tunggal) · (3) **bangun §4b/F7** stop-on-fail di `plan_and_submit` (N gagal→stop channel+alert Telegram+auto-recover, config-driven) · (4) baru restart + lanjut GATE CUTOVER.
- ✅ Sesi ini juga: fix `channel_analytics impressionClickThroughRate` (`044102e`, deployed ke worker tapi worker stop). Detail lengkap = memory `progress_journal` entri "2026-06-17 (SESI MALAM)".

## 🏗️ PERBAIKAN ARSITEKTUR PRODUKSI v2 (OPSI C) — RENCANA KERJA + penutup INSIDEN RUNAWAY

> **Plan AKTIF (sumber-kebenaran-tunggal track ini).** Disetujui owner 2026-06-17. Centang `[x]` **HANYA** bila **dibuat DAN tervalidasi 100%**. Desain = `QC_CONTENT_ARCHITECTURE.md §3/§6.2` + `DESAIN §12d.F`. **Aturan: LOKAL → validasi 100% → (commit saat owner minta) → push → pull VPS + restart. JANGAN ngoding di VPS. v1 jangan disentuh.**
>
> **TUJUAN:** ganti Opsi A → **Opsi C** (producer hanya stok; publisher hanya publish `ready`; video bermasalah ditinjau di domain kita, approve→publish ber-kuota, BUKAN auto-upload YouTube; rem alami + circuit-breaker). **KRITERIA-TERIMA UTAMA: otomatis menyetop runaway ryan (insiden 2026-06-17) — loop berhenti ≤ buffer_depth, NOL upload off-schedule, kredit terkurung.**
>
> **Feasibility: ✅ 100% TERVALIDASI (2026-06-17)** terhadap kode/DB nyata: `content_inventory.status` tanpa CHECK (status baru gratis) · `limits`/`telegram_notifier`/`s3_buffer`/`youtube_publisher` fungsi tersedia · publisher sudah klaim `ready` saja. Dependensi publish=OAuth tenant (ryan sudah jalan; tenant umum=gate BYO-CC pre-existing).

### Urutan prioritas: P0 dokumen → A DB → B Producer → C Publisher → D Review/Approve → E Janitor → F Fosil → G Validasi+Deploy

**P0 — Dokumen (LANGKAH 2, prasyarat sebelum kode):**
- [x] Revisi `QC_CONTENT_ARCHITECTURE.md` §3 + §6.2 + changelog → Opsi C *(2026-06-17)*
- [x] Revisi `DESAIN_PRODUK_SAAS.md §12d.F` → Opsi C *(2026-06-17)*
- [x] Revisi `DB_SCHEMA_V2.md` (status `ready_with_issues` + kolom/flag baru bila ada) — saat migrasi A dibuat
- [x] Rencana kerja ini (PROGRESS) *(2026-06-17)*

**A — DB:**
- [x] A1 — Dukung status `content_inventory.status='ready_with_issues'` (tanpa migrasi constraint — sudah diverifikasi); `mark_*` set `expires_at` (TTL tinjau) untuk issue **dan** `failed` (tutup bug janitor: `failed` NULL expires_at tak pernah disapu).
- [x] A2 — Mekanisme pause channel (migr **0050** `channels.production_paused*` applied+verified v2) (flag config-driven `production_paused`+reason ATAU derivasi gagal-beruntun dari `content_inventory`) — pilih yang paling sederhana saat implementasi.

**B — BE Producer (inti rem + hentikan producer-publish):**
- [x] B1 — `pipeline.run`: untuk **producer (publish=False)** saat QC-fail → **JANGAN upload YouTube, JANGAN hapus video**; kembalikan `video_path`+`qc_reason`+`recommendation`. (Hapus jalur Opsi A producer-publish.)
- [x] B2 — `produce_one`: QC-fail-ada-video → upload S3 + `mark_ready_with_issues` (+metadata issue/koreksi); crash-tanpa-video → `failed` (tak stok).
- [x] B3 — `plan_and_submit`: `stok = ready + ready_with_issues + producing` (**rem alami**) + **circuit-breaker**: N gagal beruntun/channel (config) → pause + **alarm Telegram SEKETIKA**; auto-recover saat 1 produce sukses.

**C — BE Publisher:**
- [x] C1 — ✅ **DONE (terverifikasi kode 2026-06-18; checkbox sebelumnya basi).** Publisher **hanya klaim `ready`** (`claim_oldest_ready`), gate kuota di publish (`gate_for_channel`+`published_today_count`), **laporan sukses `notify_published` dikirim SAAT PUBLISH** (`publisher.py:103-109`); **producer TIDAK lapor sukses** (hanya `notify_circuit_break`) → sudah pindah dari produce. ✓
- [x] C2 — ✅ **DONE (terverifikasi kode 2026-06-18).** Idempoten: `_already_handled` (dedup per-slot `publishing`/`published`, `publisher.py:79`) + tandai `target_slot` sebelum publish (`:89`) + status `published` → tak dobel-kirim laporan. ✓

**D — Review/Approve (domain kita — tutup cheat di sumber):**
- [x] D1 — **RPC `approve_inventory_item`/`discard_inventory_item`** (migr **0052**, security-definer, scope `auth.uid()`, grant authenticated/revoke anon — verified). Approve = promote `ready_with_issues→ready` → Publisher publish saat slot **ber-kuota** (tutup cheat: jadi publik HANYA via jalur kita); Discard = tandai buang → janitor hapus S3. *(2026-06-17)*
- [x] D2 — ✅ **DONE + TERVERIFIKASI BERFUNGSI (owner konfirmasi 2026-06-18).** Preview video di `/review` — route `/api/review/preview` presign **Biznet S3** (forcePathStyle, `S3_*` di env `mv-web`) + `<video>` FE. **Owner sudah cek: video TER-PUTAR di browser. SELESAI, jangan masuk PR lagi.**
- [x] D3 — FE `app/(app)/review` (daftar `ready_with_issues` + advisory + tombol **Pakai/Buang** via RPC) + link nav app-shell. **build PASS** (route `/review` ter-prerender). *(2026-06-17)*
- [x] D4 — Circuit-breaker **alarm Telegram** DONE (B3 `notify_circuit_break`) + laporan sukses publish (C). **Review-request per-issue SENGAJA TIDAK dibuat** (cegah mini-flood): tenant tahu via nav "Perlu Ditinjau" + alarm saat sistemik. *(keputusan 2026-06-17)*

**E — Janitor/TTL:**
- [x] E1 — `buffer_janitor.sweep_stale` sertakan `ready_with_issues` (hapus S3+baris saat `expires_at` lewat) + fix `failed` ber-`expires_at`.

**F — Bersih fosil (HATI-HATI: pastikan fosil → refactor pembaca → drop → update DB_SCHEMA):**
- [x] F1 — DROP `tenant_configs.llm_script_fallback` (migr **0051**, re-verified 0 pembaca, applied v2). *(2026-06-17)*
- [ ] F2 — Refactor pembaca lalu drop: `tenant_configs.{publish_slots,production_cron,analytics_cron,niche_pool,default_niche_rotation,niche_rotation_index}`, `channels.{production_cron,niche_pool}`, kolom plaintext `*_api_key` (sudah NULL). Per-kolom: grep pembaca (src+FE) → lepaskan → drop.
- [ ] F3 — Evaluasi tabel `pipeline_queue` (fosil V1, FK `production_runs.queue_id` — sangat hati-hati; mungkin sisakan).
- [ ] F4 — **Buang fosil pexels (V2 = no pexels, keputusan owner).** Selektor EFEKTIF = `visual_mode` (assembler); `tenant_configs.visual_provider`='pexels' = kolom legacy + `get_visual_provider()` (0 caller, mati) + `_try_pexels`/`pexels.py` + dispatch `visual_mode=="video"`/unknown/ai_video→pexels. **Log menyesatkan sudah diperbaiki (→visual_mode, commit f4358cf).** **BUTUH keputusan owner:** `visual_mode="video"`/default → jadi apa? Opsi1 default `ai_image` / Opsi2 error eksplisit. **SUPER HATI-HATI (multi-perspektif, terdokumentasi): FE-write (channels/new+onboarding) + BE-read + display + urutan-deploy + irreversible-drop — refactor DB+BE+FE bertahap, no auto-deploy. Defer ke fase cleanup pra-launch bertahap+tes e2e** (risiko>nilai bila dipaksa sekarang; rotasi sudah benar via entitlement, pexels harmless saat ini).

**G — Validasi & Deploy (prioritas akhir):**
- [~] G1 — Validasi LOKAL: **logika inti A+B+E ✅ PASS (2026-06-17)** — compile 6 file + simulasi nol-kredit (streak/rem-alami/circuit-break/produce_one branching). **Sisa: e2e dgn render nyata** (butuh kredit) + uji jalur D (approve/discard) saat D dibangun.
- [x] G2 — **KRITERIA-TERIMA TERBUKTI DI PRODUKSI (2026-06-17):** restart `mv-worker` → producer **circuit-break seketika** (streak 12 dari stale) → `channels.production_paused=true` ryan + alarm → **0 produksi baru, 0 kredit, 0 upload off-schedule**. Runaway **TIDAK terulang**. 7 thread `up`.
- [x] G3 — 29 baris `failed` stale ryan dibersihkan (0 s3_key → 0 orphan; content_inventory ryan kosong). Wajib agar auto-recover tak di-defeat data stale. *(2026-06-17)*
- [x] G4 — Deploy: commit `53d4720` push → pull `~/viral-machine-v2` + `~/mesinviral-web` (FE build PASS) + **`PRODUCER_MAX_RENDER=1`** di .env VPS (anti-OOM 2-core, decisions §3). *(2026-06-17)*
- [x] G5 — `mv-worker` restarted + dipantau: 7 thread up, ryan auto-paused (aman), nol runaway. `mv-web` 200, `/review` 200. *(2026-06-17 — saat itu; per UPDATE di bawah ryan kini PAUSED-manual utk validasi image-gen, E3 sudah di-topup)*
- [x] **E3 ElevenLabs+OpenAI re-subscribe/topup — ✅ SELESAI (owner, 2026-06-17):** kuota aktif, EL TTS premium nyata, 429 hilang.
- [ ] **SISA (urut):** **IMAGE-GEN per-preset** (validated-lokal; **Opsi A 2-tahap LLM** + kalibrasi akurasi durasi akar-b — SEDANG dikerjakan, detail journal TERATAS) → unpause ryan → **D2** preview · **F2/F3** fosil sisa.

---

## 🚀 GATE CUTOVER — Go-Live Checklist (SUMBER KEBENARAN TUNGGAL)

> **Ini SATU-SATUNYA daftar item cutover/go-live.** Catatan lain di dokumen ini hanya MENUNJUK ke sini (tidak menduplikasi). Status kode/fitur = baris STATUS teratas. Belum ada item yang dieksekusi ke VPS (v1 produksi JANGAN disentuh sampai langkah F). **⛔ PRASYARAT: §PERBAIKAN PRODUCE & PUBLISH (di atas) WAJIB selesai 100% dulu.**

**A. Kode/repo (bisa dikerjakan di dev, tanpa akses VPS)**
- [x] A1 — `requirements.txt`: `fastapi`+`uvicorn`+`cryptography` (webhook_app butuh saat deploy). ✅ 2026-06-15
- [x] A2 — **`DEPLOY_RUNBOOK.md`** lengkap: systemd unit (mv-worker + mv-webhook), nginx (api.mesinviral.com→:8088), pemisahan env Vercel/VPS (ENCRYPTION_KEY hanya VPS), smoke test + urutan cutover. *(2026-06-16; tinggal eksekusi B–F = akses owner)*
- [x] A3 — rename `src/middleware.ts`→`src/proxy.ts` + fungsi `middleware`→`proxy` (config matcher tetap; Next 16 konvensi). **Auth gate REVALIDATED** (/ 200 · /dashboard→307 /auth · /admin/tenants→307 /admin/login · /auth 200) — nol regresi. Deprecation warning hilang. *(2026-06-16)*

**B. Deploy ke VPS / Vercel (butuh akses owner)**
- [x] **B1 — Worker v2 DEPLOYED + LIVE (2026-06-16 CUTOVER).** `~/viral-machine-v2` (clone v2-backend sparse-checkout, venv 109 deps, `.env`→v2). systemd **`mv-worker`** active+enabled (0 restart). **7 thread "up"** di worker_heartbeats. **Test ryan e2e LULUS dari VPS** (`shorts/asGyGt20zH0` privat + QC-fail self-healing + Telegram). **v1 PENSIUN**: worker.py stop, crontab v1 dihapus, `~/viral-machine`+backup-lama dihapus; **disimpan arsip v1 `.tar.gz` + DB v1 utuh**. Update lanjutan v2 = local→validasi→push→`git pull` di `~/viral-machine-v2`+restart.
  - ✅ **Bug platform `channel_analytics` DONE (2026-06-17, commit `044102e`):** `impressionClickThroughRate` (impression tak tersedia per-video → 400 men-poison query, retensi ikut hilang) **dibuang**; index kolom disesuaikan; retensi/watch/subs recover; CTR per-video jujur 0. Deployed ke `~/viral-machine-v2`. *(Catatan: mv-worker kini STOP karena insiden runaway — fix ada di kode, worker belum jalan.)*
  - *(B2 webhook_app + B3 Vercel/frontend + B4 env-prod-domain = untuk SaaS PUBLIK, belum — ini baru cutover MESIN ryan.)*
- [ ] B2 — `webhook_app` (uvicorn+nginx) → VPS → Midtrans webhook + YouTube OAuth + `/api/keys/set`.
- [x] **B3 — Frontend DEPLOYED (2026-06-17) — SELF-HOST di VPS, BUKAN Vercel (keputusan owner: hemat biaya + tanpa akun baru).** `~/mesinviral-web` (clone v2-backend sparse `/apps/web`, `npm ci`+`next build`, systemd **`mv-web`** `next start :3000`). nginx `mesinviral.com`+`www`→:3000. **HTTPS Let's Encrypt (certbot via snap; apt-certbot rusak)** auto-renew, HTTP→HTTPS 301. **`https://mesinviral.com` LIVE + cert valid.** *(Menyimpang dari rencana "Vercel" lama — VPS tak lagi "bersih"; trade-off demi hemat, owner-approved.)*
  - 🔶 **Follow-up (ATURAN: fix LOKAL→validasi→push→pull VPS+rebuild+restart; JANGAN di VPS):**
    - **✅ BUG-1 DONE (2026-06-17, deployed+verified live):** logout TENANT diperbaiki — `app-shell.tsx` `sb-bottom` dapat tombol Keluar/Sign out (`createClient().auth.signOut()`+redirect `/auth`, pola sama admin-shell). Commit `9cecae6`, push→`git pull` VPS `~/mesinviral-web`+`next build`+restart `mv-web`. Verified: VPS HEAD=9cecae6, mv-web active, `https://mesinviral.com` 200.
    - *(BUKAN bug) `/admin`→`/dashboard` utk ryan = BENAR (super-admin-only; admin via `/admin/login` akun `mesinviral@`).*
    - `webhook_app`→`api.mesinviral.com` (B2) belum → Connect-YouTube + Midtrans belum jalan. `NEXT_PUBLIC_YT_REDIRECT_URI`/`MV_API_BASE` di build masih dev → rebuild prod (`https://api.mesinviral.com/...`) setelah B2. DNS `api`→VPS sudah di-set.
- [ ] B4 — Env produksi di VPS: `ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET`, `YOUTUBE_OAUTH_REDIRECT_URI`(host prod), `APP_BASE_URL`(domain prod), `SUPABASE_*`(service_role), `SMTP_*`, `MIDTRANS_*`.

**C. Konfigurasi akun eksternal (butuh dashboard owner)**
- [ ] C1 — Midtrans: Server/Client key **produksi** + 6 URL dashboard (Finish/Error/Notification ×3 channel) + `MIDTRANS_ENV=production`.
- [ ] C2 — Supabase Auth: custom SMTP (`mail.lumite.biz.id`) untuk email auth + aktifkan Google OAuth provider.
- [ ] C3 — Domain/DNS: host API (untuk redirect URI YouTube + webhook Midtrans).

**D. Smoke test langsung (setelah deploy)**
- [ ] D1 — **YouTube OAuth 1× consent nyata** (Google OAuth app + browser) — satu-satunya leg yang belum diuji live.
- [ ] D2 — SMTP egress dari VPS (kirim email nyata; dev WSL diblok 8/8 port — bukan bug, `email.py` fail-soft by design).
- [ ] D3 — Midtrans 1× transaksi (sandbox→prod).
- [ ] D4 — 1 video end-to-end via worker v2 (bukti produksi nyata) + (opsional) ukur speedup render 35→~13mnt (5.5).

**E. Keamanan & data sebelum publik**
- [ ] E1 — **ROTASI semua secret dev**: password DB, service_role, anon, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET`, SMTP, Midtrans, ElevenLabs.
- [ ] E2 — Isi kredensial channel **admin-test** (Test Lab).
- [~] E3 — (kualitas) ElevenLabs ryan: **✅ DI-TOPUP owner 2026-06-17** (voice premium aktif, 429 hilang). **Sisa turunan (OPEN):** kalibrasi `tts_profiles.delivery_wps` **× speed-niche** = akar **Cacat B** akurasi durasi (sedang via track image-gen) + closed-loop + self-learning penuh (data-gated).
- [ ] E4 — **§ADMIN SYSTEM SECRETS** (build S1-S4, lihat section di atas): system secrets editable di admin panel (Kategori A) sebelum go-live. *(rencana owner 2026-06-16; rotasi E1 mencakup secret-secret ini.)*

**F. Cutover (flip)**
- [ ] F1 — Stop worker v1 → deploy v2 menunjuk DB v2 → arahkan frontend (Vercel) → **pensiunkan v1**.

---

## 🎯 Visi Akhir (dari [[project_vision]])

SaaS multi-tenancy, multi-channel — platform produksi konten video viral otomatis berbasis AI.
Setiap tenant: login → dashboard → config API keys → scheduler → lihat laporan & log produksi sendiri.

**Prinsip non-negotiable:**
- Kualitas konten = segalanya (no silent degradation)
- Config-driven, no hardcode biaya AI
- Self-learning & self-improvement
- Tenant isolation total (RLS di DB level)

---

## 📍 STATUS SAAT INI (2 track paralel)

**Track BACKEND:** 🛠️ **Phase 1 in-progress.** Phase 0 ✅ (audit, 2026-06-12). **Phase 1.1 ✅ done + tervalidasi struktural (2026-06-13)** — LLM softcode + **AI Provider Catalog DB-driven** (`ai_providers`/`ai_models` live di v2; factory resolve provider/model dari DB; nol literal vendor di business logic/error; backfill `ryan_andrian` OK). Real production-run = gate user. Lihat §"AI PROVIDER CATALOG" + roadmap 12-phase.

**Track FRONTEND:** 🛠️ in-progress (`apps/web` Next.js 16 + React 19 + Tailwind v4, Hybrid). **DONE + tervalidasi (build PASS + curl 200):**
- ✅ Fondasi: design system port (tokens+components+app-shell), tema dark, lang ID — `36fa616`
- ✅ App Shell (sidebar+topbar `MVShell`) + theme/lang toggle + `/dashboard` placeholder — `ed1b2b5`
- ✅ D5 Run Detail (`/runs/[id]`) — pipeline live + log streaming + cost rail — `97d6f1c`
- ✅ D4 Runs List (`/runs`) — tabel + filter status + drawer slide-in → D5 — `2192488`
- ✅ A1 Landing (`/`) — hero+mockup, stats, problem, pipeline, 6 fitur, comparison, how, testi, pricing, FAQ, CTA + MarketingShell (nav+footer). Xendit→Midtrans. — `a2c2505`
- ✅ A2 Pricing (`/pricing`) — tiers + billing toggle (annual −20%) + full comparison + BYOK calculator (slider) + add-ons + FAQ. Xendit→Midtrans. — `5701cd0`
- ✅ B1-B4 Auth (`/auth`) — multi-view (signup/login/forgot/forgot-sent/verify/verified) split-screen + deep-link `?view=`. Auth nyata = Supabase Phase 4. — `7f413b5`
- ✅ D7 Schedule (`/schedule`) — view toggle week/month/list, AI optimization banner, slot grid 3 channel + pause/switch, month pips, list view — `f2bf4dd`
- ✅ B5 Settings (`/settings`) — tab nav (profil/keamanan/integrasi/notif/bahasa/danger), profil form, 2FA+sesi, integrasi, lang picker + theme toggle, danger zone — `d1a54e9`
- ✅ C1-C5 Onboarding (`/onboarding`) — wizard 5 langkah: paket, connect YouTube (verify sim), API keys BYOK (accordion+test), niche+**Bahasa Konten** (config-driven catalog→voice filtered)+voice+warna, jadwal week. Standalone pre-login. — `9216849`
- ✅ D20 Compliance (`/compliance`) — gauge skor + radar + 4 dim-card (donut/bar/dup), AI disclosure, tren 90hari, action items, edu. **Semua chart = SVG hand-drawn (tanpa tremor)**, deterministik (SSR-safe). — `9aab4ff`
- ✅ D1 Main Dashboard (`/dashboard`) — greeting+Run Now, 4 KPI (2 sparkline SVG), grid2: jadwal hari ini + recent runs (kiri) · compliance gauge + cost tracker BYOK + self-learning insight (kanan), activity feed. **Chart = SVG hand-drawn (spark+gauge, tanpa tremor)**, mock deterministik SSR-safe. Ganti placeholder lama. — `db3dafb`
- ✅ Config (D8-D19) **Stage 1** (`/config/[tab]`) — **routing path-based** (`/config`→redirect `/config/ai-engines`; sidebar AppShell href `/config/<id>` nyambung + active-state pathname benar) + shell left-nav 10 tab (grup Engine/Content/System) + 5 panel grup **Engine**: AI Engines (3 svc accordion: provider radio, model per-task, API key+Test, usage), API Keys (tabel 5 service + audit log), Voice (lang note + voice cards waveform + default per niche), Visual (preset + prompt prefix Pro+ + palette), Music (mood pills + track list + switch). Interaktif (accordion/test/play/radio), deterministik no-`Math.random`, brand-icon→kotak inisial. — `d011662`
- ✅ Config **Stage 2** (`/config/{captions,quality,hashtags,niches,notifications}`) — grup Content+System: Captions (preview 9:16 live + 3 sub-tab + slider/swatch interaktif + preset), Quality Gate (Pro+ badge + lock-preview toggle + histogram SVG + retry stepper + action radio + per-dim + AI rec), Hashtags (segmented niche + default/custom/blacklist chips removable + preview), Niches v3 (active grid + New This Month + catalog + **dual custom-request `{{pricing.*}}` placeholder** + modal + sub-tag + override), Notifications (3 accordion + event matrix + quiet hours). Routing path-based `/config/[tab]`. — `8973008`
- ✅ D21 Self-Learning Insights (`/insights`) — moat #1: header+grade, hero "belajar dari 87 video"+stat-strip, **timeline insight filterable** (6 filter pill) dgn bar-chart CSS + adaptasi + confidence + **accept interaktif** (pending→accepted), rail (override manual slider + how-it-works FAQ per-channel isolation), tabel riwayat adaptasi. Mock deterministik. Sidebar "Wawasan" nyambung. — `17cf167`
- ✅ D13 Billing (`/billing`) — current plan (harga `{{pricing.plan_pro}}` placeholder) + usage bars, metode pembayaran **Midtrans** (ex-Xendit), riwayat invoice 6-baris + PDF, add-ons aktif, **drawer katalog add-on** (slide-in + scrim + ESC), BYOK cost tracker (bar provider + budget). Mock deterministik. Sidebar "Tagihan" nyambung. — `66bb907`
- ✅ D2 Channels List (`/channels`) — header+Add, quota bar, segmented filter (all/active/incomplete/suspended), grid card channel (logo+handle+niche badge+**spark SVG area+line hand-drawn**+4 stat+Kelola→`/channels/[id]`) + incomplete setup-card. Mock deterministik. Sidebar "Kanal" nyambung. — `668431b`
- ✅ D3 Channel Detail (`/channels/[id]`) — header+KPI strip, **5 tab** (Overview: **perf dual-area SVG** + **donut niche SVG** + rec + top-video tabel + hook bars · Runs mini-list · Analytics placeholder · Schedule slot · Settings form +warning bahasa non-retroaktif). id→header map. Class prefix `cd-` (anti bentrok CSS global). "Kelola" dari D2 nyambung. — `462761a`
- ✅ D6 Analytics (`/analytics`) — filter, 6 KPI strip, **views multi-line SVG** + **CTR histogram SVG** + niche/hook bar-CSS + **2 heatmap deterministik** (publish-time×eng + music-mood, ganti `Math.random`) + top-video tabel + insight self-learning (accept/reject state). Class prefix `an-`. Sidebar "Analitik" nyambung. **→ tenant D1-D21 komplit.** — `8b6cbd6`
- ✅ **Admin E1-E5** (`admin.mesinviral.com` → segment `/admin/*`) — **AdminShell** (nav Operasi/Katalog + badge ADMIN amber + Link nav + theme/lang, reuse app-shell.css) + 6 screen: **E1 Tenants** (tabel + drawer detail), **E4 Support** (inbox 3-kolom chat), **E3 System** (worker grid + 2 SVG line + DB stats), **E2 Catalog** (5 tab: AI Models/Music/Niche-link/Voice/Content Languages), **E2.3 Niches** (tabel + 6-tab drawer + monthly release + exclusivity pipeline), **E5 Pricing** (tabel inline-edit + quick-card + API panel + 4-tab drawer + toast). Prefix adm-/sup-/sys-/cat-/nl-/pr- (anti bentrok CSS antar-route SPA). Mock deterministik; nol wiring Supabase. — `ff6abaa`
- ✅ Marketing **A3 Demo** (`/demo` — tur produk via **iframe ke route nyata** /dashboard,/runs/97,/channels,/runs) · **A4 Docs** (`/docs` — tree+artikel BYOK+TOC) · **A5 Blog** (`/blog` — toggle blog/cases + filter kategori) · **A6 About** (`/about` — 4 tab About/Contact/Status/Legal) · **A8 404** (`not-found.tsx`). Prefix dm-/dc-/blg-/ab-. Mock; nol wiring Supabase. — (commit ini)

**Next:** Config (D8-D19) / Insights (D21) / Admin (E1-E5) / next-intl / shadcn init / **PWA**. *(Chart D2/D3/D6: lanjut SVG hand-drawn seperti D1/D20, atau install tremor jika chart kompleks spt heatmap D6.)* Data: mock → Supabase-first (RLS) saat backend mendarat. ⚠️ Next 16 breaking changes (`apps/web/AGENTS.md`) — baca `node_modules/next/dist/docs/` sebelum routing/middleware (next-intl). Detail [[plan_frontend_via_claude_design]].

> Frontend & backend jalan **paralel** — frontend pakai MOCK DATA dulu (tidak nunggu backend), wire ke Supabase saat phase backend mendarat. Frontend = Phase 9-10 di roadmap, tapi DIMULAI lebih awal secara paralel atas keputusan user.

**Last validated run:** Job #96 (2026-06-10 09:31 WIB) — SUCCESS, published https://www.youtube.com/shorts/Jf-soZuYIOs

**Active tenant:** `ryan_andrian` (single tenant)

---

## 🎨 FRONTEND — DESAIN SELESAI, IMPLEMENTASI HYBRID (Update 2026-06-11)

**Claude Design SELESAI 100%.** Handoff bundle (HTML/CSS/JS + screenshot, **32 file HTML ≈ 30 screen prototype + mobile/states**; spec brief = 39 screen logis) diterima & disimpan di `design-source/mesinviral-com/` (**gitignored** — tidak ke git/VPS). **Pengembangan UI lanjutan TIDAK lagi lewat Claude Design** — dikembangkan langsung di sini.

### Keputusan implementasi (user-confirmed 2026-06-11)

| Topik | Keputusan |
|---|---|
| **Strategi** | **HYBRID** — reuse CSS desain (tokens+components, 0 redesign) + shadcn/Radix HANYA utk komponen interaktif/a11y, di-tema pakai tokens desain. Charts: tremor. |
| **Repo** | **Monorepo** — frontend di `apps/web/` (Next.js 15) di repo ini. |
| **Sequencing** | Mulai **SEKARANG dgn MOCK DATA**, paralel/mendahului backend. Wire Supabase saat phase backend mendarat. |
| **Deploy** | ~~Vercel~~ → **SELF-HOST di VPS** (2026-06-17, owner: hemat biaya+tanpa akun): `mv-web` Next.js+nginx+Let's Encrypt di VPS. `https://mesinviral.com` LIVE. *(VPS tak lagi Python-only — relax demi hemat.)* |
| **Data boundary** | **Supabase-first** — frontend→Supabase langsung (client SDK + RLS) + Realtime; **NO API layer Python**; worker = penulis data; endpoint minimal utk webhook Midtrans. |
| **Responsive + PWA** | Responsive: harmonisasi breakpoint (29/33 screen sudah `@media`) saat port. **PWA installable** (manifest + service worker) ditambah saat implementasi — web-only, no native. |

### Sumber desain (single source)

- `CLAUDE_DESIGN_BRIEF.md` — spec brief (39 screen, sudah termasuk multi-bahasa v4). Tetap acuan konten/layout.
- `design-source/mesinviral-com/project/` — bundle final: `CLAUDE.md` (build notes), `*.html` (32 file ≈ 30 screen prototype; brief spec = 39 screen logis, sebagian dibangun saat implementasi), `styles/` (tokens.css, components.css, shell.js/MVShell, icons.js/MVIcons, marketing.*, app-shell.*), `config/` (cfg-content, cfg-engines), `content-languages.js`.
- `CLAUDE_DESIGN_ADDENDUM_v2/v3/v4.md` — referensi delta (niche, pricing config-driven, multi-bahasa). Sudah terserap ke brief + desain; bukan untuk Claude Design lagi.

### Urutan kerja implementasi (NEXT)

1. **Fondasi** ← NEXT — setup `apps/web` (Next.js 15 + Tailwind), port `tokens.css`+`components.css`→global, `MVShell`→layout React, icons (lucide + SVG custom), i18n (next-intl ID/EN), theme (next-themes `data-theme`).
2. **Proof-of-concept:** D5 Run Detail (paling kompleks) → D1 Dashboard.
3. **Marketing:** A1 Landing + A2 Pricing.
4. **Auth + Onboarding** (C4 dropdown Bahasa Konten sebelum voice).
5. Sisa Dashboard (D2-D21) → Admin (E1-E5) → States/Mobile.

**Deviasi desain yg ditangani saat port:** A2/C1 literal "Rp..K"→placeholder `{{pricing.*}}`; ikon custom MVIcons→lucide+SVG; chart mockup→tremor; pola i18n span-ganda→next-intl.

### Decisions UX User-Confirmed (Claude Design Q1-Q9)

| Topik | Pilihan |
|---|---|
| **Start order** | Design system + D5 Run Detail (proof of concept) — BUKAN landing dulu |
| **Presentation** | Hybrid — clickable prototype untuk dashboard, static high-fid untuk marketing |
| **Theme** | Dark default + working light toggle |
| **Language UI copy** | Bahasa Indonesia default + working EN toggle |
| **Viewports** | Desktop 1440px + Mobile 375px untuk key screens (Landing, Pricing, Sign-up, Onboarding 5 step, Dashboard, D5 Run Detail) |
| **Typography** | **Geist Sans** (BUKAN Inter — terlalu generik AI-slop), JetBrains Mono untuk log viewer |
| **Charts** | Fully rendered dengan Indonesian sample data |
| **Real content** | Sample tenant Riko Pratama, channel "Misteri Samudra", niche ID, pricing real Rp 149/349/699K, AI cost real $0.34/video |
| **Priority demo** | D5 Run Detail → D1 Dashboard → A1 Landing → A2 Pricing → Onboarding step 3 (API Keys) → Compliance Score widget |

> Tabel "Decisions UX Q1-Q9" di atas = konteks historis desain (sudah baked-in ke output Claude Design). Bukan pekerjaan terbuka.

### Sumber Referensi untuk Sesi Berikutnya

[[plan_frontend_via_claude_design]] memory file (sudah di-rewrite 2026-06-11) — single source status frontend: lokasi bundle, strategi Hybrid, urutan kerja, fakta design system. **Baca itu + `design-source/.../CLAUDE.md` sebelum implementasi.**

### 🆕 Niche Model + Pricing Decisions (2026-06-11)

User confirm via AskUserQuestion 3-question session:
- **Niche granularity:** Hybrid broad + sub-tag layer (4 broad default + monthly release + tag pool per niche di videos)
- **Custom niche workflow:** Monthly release + on-demand custom request (hybrid model)
- **Exclusivity:** Public-after-90d (Rp 299K default) ATAU Permanent Private (Rp 1.499K default)
- **🚨 CRITICAL: Pricing CONFIG-DRIVEN** — semua nominal disimpan di table `pricing_config`, adjustable by sysadmin via admin panel E5 (NEW screen di brief)

Detail permanent reference: [[decisions_niche_model]] memory file.

**Implication backend (untuk Phase implementasi nanti):**
- Schema: tambah `tag_pool`, `released_at`, `access_type`, `exclusive_*` ke `niches`; `topic_tags` ke `videos`; NEW table `pricing_config`
- Helper `src/utils/pricing.py` dengan `get_price(key)` + caching 5 menit
- API `/api/pricing` endpoint untuk UI render

**Implication design brief (sudah di-update dalam session ini):**
- D18 Config Niches: dual-option request (public/private dengan pricing dari DB)
- E2.3 Admin Niches: tag pool editor + monthly release scheduler + exclusivity manager (expanded detailed)
- E5 NEW: Admin Pricing Config screen (CRUD pricing entries + audit log)
- Screen inventory 38 → 39

### Integration Tech Stack Target

Next.js 15 (App Router) + shadcn/ui + Tailwind + tremor.so + Geist Sans + next-intl (i18n) + Supabase Auth + Supabase Realtime + Vercel deploy. Detail per layer di [[plan_frontend_via_claude_design]].

**Repo structure:** ✅ DIPUTUSKAN (2026-06-11) — **monorepo**, frontend di `apps/web/` di repo ini. ~~`apps/web` di-exclude dari sparse-checkout VPS; deploy ke Vercel.~~ **REVISI 2026-06-17: frontend SELF-HOST di VPS** (clone terpisah `~/mesinviral-web` sparse `/apps/web`; `mv-web` systemd). Bukan Vercel.

**Domain:** `mesinviral.com` (landing) + `app.mesinviral.com` (dashboard) + `admin.mesinviral.com` (internal).

---

## 🗺️ MASTER ROADMAP (12 Phase)

> **Roadmap konsep di `DESAIN_PRODUK_SAAS.md §12`; STATUS LIVE = tabel ini (MASTER status — jangan duplikat status di tempat lain).** Disinkronkan 12-phase: Self-Learning+Diversity **Phase 6 (CORE MOAT)**, Compliance 7, Payment 8 (Midtrans), UI 9-10, Beta 11, Public 12.
>
> **Konvensi status (PRINSIP: tahap jadi ✅ HANYA jika TERBUKTI valid / running well — wajib ada bukti):** ⏸️ pending approval · 🔒 blocked · 🛠️/⏳ in-progress · ✅ DONE+VALIDATED (sertakan bukti: production run #, `npm build` PASS, curl 200, migration applied — catat di Status/VALIDATION HISTORY) · 🔄 continuous. **Update tabel ini tiap sub-phase yang lulus validasi.**

| Phase | Nama | Tujuan | Estimasi | Status |
|-------|------|--------|----------|--------|
| **0** | Audit & Persiapan | Verifikasi semua klaim SOFTCODE_AI_CONFIG vs kode | – | ✅ DONE (read-only, 2026-06-12) — hasil di journal + rekonsiliasi di §1.1 |
| **1** | SOFTCODE AI Config | Hilangkan hardcode AI, hapus silent fallback (6 sub-phase) | 4-6 jam | ✅ **DONE (2026-06-13)** — 1.1-1.5 softcode + 1.6 bugfix (Bug 2 `_generate_image` fixed). Bug 1 dispatcher-timezone = **pg_cron DB v1 (bukan kode repo)** → re-klasifikasi **Phase 5** (publisher v2 timezone-aware). |
| **2** | Error Mgmt Terpusat | `src/exceptions.py` + structured error flow | 2 jam | ✅ **DONE (2026-06-13)** — hierarki PipelineError + typed raises + catch kategori/step. DB-persist (`pipeline_errors`) → Phase 3 (tabel belum ada). |
| **3** | Pipeline Run Logs (DB) | `pipeline_run_logs` table, RLS-ready, UI-facing | 2 jam | ✅ **DONE (2026-06-13)** — tabel + `db_log_sink` loguru→DB (per-record, enqueue) + worker context-wire. Menutup DB-persist error Phase 2. |
| **4** | BYO-CC Phase 1 | `tenant_credentials` + Fernet + auth foundation | 1 minggu | ✅ **DONE (2026-06-13)** — 4.1 crypto+creds · 4.2 Auth user+tenant_id→UUID · 4.3 RLS go-live+security fix · 4.4 OAuth dari DB (file-fallback; seed token pending) · 4.5 key validation. §PHASE 4. |
| **5** | Multi-Channel + Decouple | `channels`, channel_id, content_inventory, S3 buffer, producer/publisher | 1 minggu | ✅ **decouple TERBUKTI END-TO-END NYATA** — full loop `produce→buffer(S3)→claim→publish PRIVATE→published` jalan (2026-06-13), termasuk **upload YouTube asli** (`shorts/7ocW6BPdlVg` privacy=private terverifikasi API), slot Asia/Jakarta (Bug1), OAuth DB-first (4.4). Mekanik cutover PROVEN. **Sisa = deploy → §GATE CUTOVER (B1/F1).** 5.5 optimasi render pending. `PHASE5_DESIGN.md`. |
| **6** | 🥇 Self-Learning + Diversity Engine | **CORE MOAT** — pull YT Analytics 24-72h post-publish + adapt config; voice/hook/niche rotation | <2 minggu (sebagian SUDAH ADA) | 🛠️ in-progress — DESIGN ✅ (`PHASE6_DESIGN.md`). **6.1 ✅ DONE** (OAuth analytics DB-first + self_learning loop). **6.2 ✅** (0018 + DiversityEngine LRU hook/visual/music/niche + tutup gap write_video; voice deferred). **6.3 ✅** (0019 `ai_disclosure` → YouTube `containsSyntheticMedia` default ON). Sisa: **6.4** insights per-tag + filter channel · *(follow-up: voice rotation)*. |
| **7** | 🛡️ Compliance Score + AI Slop Defense | **SURVIVAL** — compliance calculator + polish diversity | 1 minggu | ✅ **calc DONE (2026-06-14)** — `compliance.py` 5-dim 0-100 + migr 0020 (`channel_insights.compliance`) + wired ke compute_and_store; e2e SEHAT 86.8 vs SLOP 18.0 (membedakan). Feed D20 (FE P9-10). Polish/threshold-tuning + per-tag = saat data produksi terkumpul. |
| **8** | Payment Integration | **Midtrans** Snap + Email (SMTP) + tier-gating | 2 minggu | ✅ **BACKEND DONE (2026-06-14)** — 8a tier-gating+subscription-gate · 8b Snap-redirect+webhook+payments(0022)+comp · renewal/grace/suspend · trial BYOK-tier+trial_expired-leads · 8c email SMTP+auth-admin-resolve+3 notif. e2e sandbox NYATA penuh. **Sisa = CUTOVER ops → §GATE CUTOVER (C1/B2).** |
| **9** | UI Foundation | Next.js + landing + dashboard + Supabase Realtime + RLS | 4-6 minggu | ✅ **SELESAI (2026-06-15)** — SEMUA layar tenant + marketing ter-wiring ke Supabase v2 (auth/RLS/Realtime/RPC), termasuk 9.4 (analytics/compliance/insights/schedule/config) + direct-produce + CMS. `PHASE9_FRONTEND_WIRING.md`. |
| **10** | UI Polish + Admin | Admin area penuh (E1-E5 + System + Support) + subsistem | 2-3 minggu | 🟢 **ADMIN SELESAI (2026-06-15)** — 9 sub-fase (fondasi service_role + Tenants/Leads + Pricing+audit/rollback + Niches+exclusivity + Catalog AI-models/providers/music/voice/languages + System Health+heartbeats + Support subsystem) runtime-validated + pushed. migr 0034-0040. Akun super-admin `mesinviral@`. Detail [`PHASE10_ADMIN_WIRING.md`](PHASE10_ADMIN_WIRING.md). Sisa polish (next-intl/PWA) + Phase 9.4 tenant (OAuth/schedule/analytics). |
| **11** | Beta Launch | 10 hand-picked tenant + feedback iteration | 1 bulan | 🔒 Blocked by Phase 10 |
| **12** | Public Launch | Marketing kick-off | – | 🔒 Blocked by Phase 11 |

**Cross-cutting (bukan phase bernomor):** Docs Sync — update `MESIN_VIRAL.md` + `roadmap_1.md` + memory tiap selesai sub-phase (lihat "Aturan Lintas Phase" di [[plan_master_softcode_to_saas]]).

**Catatan:** Detail sub-phase di bawah baru lengkap untuk Phase 0-5 (foundation backend). Detail Phase 6-8 ada di `DESAIN_PRODUK_SAAS.md`; detail UI Phase 9-10 mengacu `CLAUDE_DESIGN_BRIEF.md` + [[plan_frontend_via_claude_design]] (Claude Design workflow).

### 🧩 EPIC — Multi-Format Short Studio (proposal TERVALIDASI, 2026-06-11)

Perluasan produk: menampung **banyak kategori creator short faceless** (mystery/facts/edukasi-softsell/motivasi/brand). **Konsep/positioning** di `DESAIN_PRODUK_SAAS.md` (induk) · **spec teknis + validasi** di `MULTI_FORMAT_STUDIO.md` · ringkasan [[plan_multi_format_studio]].

> ✅ **Sudah divalidasi terhadap kode + API eksternal (2026-06-11)** — verdict per item ada di `MULTI_FORMAT_STUDIO.md §0`. **Jangan analisa ulang.**

**Plan-vs-realisasi (status per item):**
| Item | Feasibility | Status |
|---|---|---|
| QC window relatif · link deskripsi · logo overlay · soft-sell CTA | ✅ murah (~20-50 LOC each) | ✅ **BE DONE** (QC relatif=F2c ±15%; Branded FB1-4=link/logo/soft-sell). **FE Branded panel = BELUM** → [`BRANDED_CONTENT_ARCHITECTURE.md`](BRANDED_CONTENT_ARCHITECTURE.md) |
| Durasi 30–75s (section_timing preset + compression-map) | 🟡 medium | ✅ **F1+F2 DONE** — katalog (0012/0013) + scaling/word-budget (F2a) + wiring channel→tc (F2b) + QC relatif ±15% (F2c) + LLM-QC length-gate (F2d) + **effective-WPS per kelas TTS (F2e, 0014)**. Tervalidasi LIVE (ryan 60s konvergen). Closed-loop speed-adjust (poles edge + presisi) = pasca-ElevenLabs aktif. |
| Closed-loop akurasi durasi (speed-adjust Edge/ElevenLabs) | 🟡 medium | ⏳ setelah cheap wins |
| Variable visual beats · katalog `ai_models` (konsolidasi Phase 1.3) | 🟡 medium | ⏳ |
| **ai_video (BYOK)** + ultra-short 8–15s | 🟡 berat (`ai_video.py` DISABLED; redesign section) | ⏳ fase C |
| **Multi-platform** (base_publisher + Reels/TikTok) | 🟡 berat + **eksternal** | ⏳ fase C |

**⚠️ Kendala eksternal terdokumentasi (masuk perencanaan onboarding):** TikTok auto-post publik butuh **audit 2–4 mgg** (tanpa audit SELF_ONLY); IG Reels butuh akun Business+Page+**App Review 2–4 mgg**; **auto-pin YouTube comment MUSTAHIL** (pakai link deskripsi); ai_video latency 1–3 mnt → **wajib async** (queue kita sudah async).

**Keputusan final:** 8s & ai_video **tetap masuk** (provider support); Bahasa Latin saja; pinned-comment dihapus (mustahil); Payment = **Midtrans**; tier: Starter=YT, Pro=+Reels, Scale=ke-3 platform.
**Placement:** cheap wins → **Phase 1.x**; medium → setelah cheap wins; ai_video + multi-platform → fase C (nyambung **BYO-CC Phase 4** + tier **Phase 8 Midtrans**).

### ⚙️ ARSITEKTUR — Produksi & Scaling (TERVALIDASI 2026-06-12)

**Konsep/pondasi + pseudo-code di `DESAIN_PRODUK_SAAS.md §12c`** (rumah utama). Angka detail + bukti file:line di [[decisions_production_scaling]] (memory). Section ini = ringkasan status/roadmap. **Berbasis benchmark/log VPS nyata — jangan analisa/benchmark ulang.**

> 🔴 **Kritikal:** produksi 1 video = **35 mnt** terukur (render ~21 mnt dominan). Banyak tenant berbagi slot publish → spike → **VPS down** (terbukti live: 2-core/swap-0 OOM-mati di bawah render konkuren).

**Keputusan:**
- **Decouple produksi ↔ publish** — producer kontinu jaga **buffer per-channel**; publisher di slot ambil video ready (ringan). "Jadwal" = jadwal **publish**, bukan produksi.
- **Buffer = Biznet Gio S3** (co-located, ~50MB/file) + tabel **`content_inventory`** (source of truth status).
- **Concurrency cap = jumlah core + RAM ≥ ~2GB/core + tambah swap** (terbukti wajib).
- **Scale by core/node** (orkestrator bagi job), BUKAN lebih banyak proses di core sama.
- **Optimasi render = prioritas #1** — **2,87× terukur** (21→7 mnt) gabung 3 pass→1 + `veryfast`; + paralel image (10→2 mnt) → total **35→~13 mnt**.
- **Capacity model** (cores/RAM vs tenant) di memory: ~50 tenant→4 core, ~100→8 core, lalu multi-node 16-core.

**Placement:** optimasi render + paralel image + swap → **Phase 1.x** (murah, dampak terbesar, prasyarat scale). Decouple + buffer S3 + content_inventory + orkestrator multi-node → arsitektur dekat **Phase 5** / sebelum scale tenant.

**Status (update 2026-06-13):** ✅ **DECOUPLE TERBUKTI end-to-end nyata.** Dibangun+tervalidasi: `content_inventory` + buffer **Biznet Gio S3** + `producer`(semaphore=core) + `publisher`(timezone-aware) + `worker_decoupled.py` + **S3 janitor** (sweep+reconcile) — full loop → publish YouTube private. S3 secret/bucket resolved. **5.5 optimasi render (35→13mnt) — ✅ DONE (kode, 2026-06-14):** **5.5a** paralel image-gen (`asyncio.gather` I/O + convert CPU sekuensial anti-OOM; commit `7271b8c`). **5.5b** merge Step A xfade + Step B audio/subtitle/tpad → **1 `filter_complex`/1 encode** (`_single_pass_concat`) + **safety-net fallback** ke 2-pass proven (`_concat_two_pass`) = **nol regresi** + **preset config-driven** (`RENDER_PRESET`, default veryfast). **Validasi KOMPREHENSIF e2e** (render() nyata, aset sintetis, nol kredit): single-pass & fallback dua-duanya hasilkan 9:16 h264/aac VALID; **single-pass ≡ 2-pass 0.0s** utk klip realistis; A/B isolated identik. **Sisa:** cutover deploy + ukur speedup → **§GATE CUTOVER (B1/D4)**. "tobe_submitted" lama (video numpuk VPS `logs/`) digantikan buffer S3 saat cutover.

---

### 🧩 AI PROVIDER CATALOG (DB-driven) — directive user 2026-06-13

**Keputusan (user):** provider AI + **format parameter API**-nya bisa terus ditambah **super-admin lewat DATABASE** (tanpa redeploy), lengkap **quality + cost**, agar tenant punya banyak pilihan → makin banyak kategori kreator terlayani → makin banyak tenant. **Nol literal nama provider** di business logic & error message (kecuali file *adapter transport* yang memang implementasi SDK — batas yang diterima user). Lihat [[feedback_no_hardcode]].

**Arsitektur (live di v2):** `ai_providers` (provider_key, display_name, **adapter**=protokol, base_url, auth, `request_param_schema`) + `ai_models` (model_key, provider_key, **component** llm/tts/image/video, model_id, quality_tier, **cost_hint**, default_params). Kode hanya punya **adapter per-protokol** (`anthropic_messages`, `openai_chat` (+OpenAI-compatible via base_url)). Tambah vendor sejenis = 1 baris DB (nol deploy); protokol baru = 1 adapter.

**Status per komponen (verified 2026-06-13):**
| Komponen | Sisi-tenant `tenant_configs` | Catalog-wired? | Tindak lanjut |
|---|---|---|---|
| **LLM** | `llm_library`+`llm_models` | ✅ DONE (1.1) | — |
| **Image** | `visual_provider`=`ai_image:<model_key>` (rujuk katalog) | ✅ DONE (1.3) | — (harmonisasi penuh tenant_configs opsional) |
| **TTS** | `tts_provider`(=library)+`tts_fallback_provider` — chain config-driven ✅ (1.4) | 🟡 sebagian | provider/voice **catalog-wiring** = follow-up deeper |
| **Video (ai_video BYOK)** | belum ada kolom | ❌ | **Multi-Format fase C** |

**FOLLOW-UP DITUANGKAN ke rencana (tindak lanjut PADA FASENYA — jangan dikerjakan di luar jalur):**
- **(A) Backend** — harmonisasi `tenant_configs` agar refer `ai_models.model_key` per komponen + seed katalog: **image→Phase 1.3**, **TTS→Phase 1.4**, **video→Multi-Format fase C**. (Saat ini link loose by model_id string; pertimbangkan validasi app-layer ke katalog.)
- **(B) Frontend** (saat wiring / Phase 9-10) — (1) **Admin E2 Catalog**: tambah manajemen **PROVIDER** (`ai_providers` CRUD: adapter/base_url/auth/`request_param_schema`) — sekarang UI hanya kelola MODEL. (2) **Tenant "AI Engines"**: ganti radio provider hardcoded `[Anthropic,OpenAI]` + model statik → **dinamis dari katalog** + tampilkan **quality/cost**. (Clone v2 sudah ada → guardrail wiring terbuka.)
- **(C) S3 buffer / `content_inventory`** — sudah tercatat di §"Arsitektur Produksi & Scaling" (placement Phase 5), belum mulai.

### 🔗 KESELARASAN DB ↔ BACKEND ↔ FRONTEND (audit 2026-06-13)
Setelah Phase 1-4 + alignment (migr 0010). **DB = lengkap untuk semua domain; backend selaras untuk fase selesai; frontend = mock, wiring di Phase 9 (gap ter-track, bukan drift diam).**

| Domain | DB | Backend | Frontend (apps/web) | Status |
|---|---|---|---|---|
| LLM provider/model | `ai_providers`/`ai_models`+`llm_library`/`llm_models` ✅ | factory katalog ✅ | AI Engines (radio hardcoded) | DB/BE ✅ · FE perlu dinamis (B, P9) |
| Image | `ai_models`(image) ✅ | ai_image load DB ✅ | E2 Catalog (model) | ✅ · provider-mgmt UI gap (B) |
| TTS | `tenant_configs.tts_*` ✅ | chain config ✅ | Voice/AI Engines | BE ✅ · voice catalog-wiring (follow-up) |
| Niche | `niches`+`niche_fallback`/`niche_pool` ✅ | resolver fail-loud ✅ | D18 Niches | ✅ · gate enforcement (P5/9) |
| Pricing | **`pricing_config` ✅ (0010)** | helper `src/utils/pricing.py` ❌ | `{{pricing.*}}` + E5 | DB ✅ · BE helper+FE wiring (P8/9) |
| Content language | **`content_languages` ✅ (0010)** | inject ke script ❌ | landing/C4/E2.5 | DB ✅ · BE inject (P5/6) + FE wiring (P9) |
| OAuth/credentials | `tenant_credentials` ✅ | crypto+loader ✅ | onboarding C3 | DB/BE ✅ · FE wiring (P9); seed token ryan pending |
| Logs/live-tail | `pipeline_run_logs` ✅ | db_log_sink ✅ | D5 (simulasi) | DB/BE ✅ · FE live-tail wiring (P9) |
| Auth/isolasi | `auth.users`+`tenant_id=auth.uid()`+RLS ✅ | RLS+service_role ✅ | B1-B4 (mock) | DB/BE ✅ · FE Supabase Auth (P9) |
| Multi-Format | `format_profiles`+`duration_presets`+`tts_profiles`+branded(0015) ✅ (0012-0015) | **F1+F2 ✅** + **Branded FB1-4 ✅** (link deskripsi + soft-sell CTA + **logo overlay** `_overlay_logo`, tervalidasi pixel) | **screen baru BELUM ada** (Hybrid §11) | DB ✅ · BE ✅ · **FE gap Phase 9-10 (WAJIB): (a) format/preset picker; (b) Branded Content — link + soft-sell + `config/visual/logo-overlay` tab: upload logo + PEMILIH POSISI + PREVIEW (pola `config/visual/caption` position); UKURAN platform-fixed (bounds DB `branding_config`, tenant ikut). SEMUA OPSIONAL (backend nullable=non-breaking)** · closed-loop pasca-ElevenLabs · **status kanonik branded → [`BRANDED_CONTENT_ARCHITECTURE.md`](BRANDED_CONTENT_ARCHITECTURE.md)** |

| Diversity (Phase 6.2) | `videos`(voice_id/hook_pattern/music_mood/visual_seed)+`diversity_config` ✅ (0018) | `DiversityEngine` LRU + hook/visual/music rotation ✅ | — | DB/BE ✅ · FE (opsional, admin diversity_config) P9-10 |
| AI Disclosure (Phase 6.3) | `channels.ai_disclosure` ✅ (0019) | `youtube_publisher` set `containsSyntheticMedia` ✅ | D-channel settings (toggle) | DB/BE ✅ · **FE toggle gap (default ON) P9-10** |
| Compliance Score (Phase 7) | `channel_insights.compliance` jsonb ✅ (0020) | `ComplianceScorer` 5-dim + wired compute_and_store ✅ | **D20 Compliance** (gauge+radar, sudah ada mock) | DB/BE ✅ · **FE wiring D20→channel_insights.compliance P9-10** |

**Kesimpulan:** tak ada misalignment diam — semua gap = (a) frontend mock→wiring **Phase 9**, atau (b) backend helper/inject di fasenya (pricing P8, content-lang P5/6), atau (c) epik (format_profiles). Tertuang semua.

**⚠️ Catatan infra v2 (verified 2026-06-13):** `tenant_configs` RLS=ON (policy `auth.uid()`) → **worker v2 WAJIB pakai SUPABASE service_role key** (anon/publishable ke-block, tak bisa baca row tenant). Katalog `ai_providers`/`ai_models` = public-read (OK dgn anon). **LLM v2 = OpenAI** (pilihan owner saat ini). Key Anthropic clone-v1 mati, **tapi BUKAN masalah / di luar plan** — owner sengaja pakai OpenAI; ganti ke Claude = **test SETELAH v2 go-live** (bukti "ganti provider = 1 baris config DB" sudah ada). Saat wiring frontend→Supabase pakai anon+RLS (`auth.uid()`); worker/backend pakai service_role.

---

## 🔍 PHASE 0 — Audit & Persiapan

**Tujuan:** verifikasi setiap klaim SOFTCODE_AI_CONFIG masih akurat di kode hari ini (file/line bisa shifted setelah 2 bulan).

### Checklist
- [ ] Git status bersih + `main` up-to-date dengan origin
- [ ] Verifikasi 7 lokasi hardcode LLM (SOFTCODE §1):
  - `src/intelligence/script_engine.py:415` (`"claude-sonnet-4-6"`)
  - `src/intelligence/script_engine.py:442` (`"gpt-4o-mini"`)
  - `src/intelligence/script_analyzer.py:149` (`"gpt-4o-mini"`)
  - `src/intelligence/hook_optimizer.py:143` (`"gpt-4o-mini"`)
  - `src/intelligence/niche_selector.py:412` (`"gpt-4o-mini"`)
  - `src/providers/visual/ai_image.py:310` (`"claude-haiku-4-5-20251001"`)
  - `src/providers/visual/ai_image.py:319` (`"gpt-4o-mini"`)
- [ ] Verifikasi 3 lokasi hardcode TTS (SOFTCODE §2):
  - `src/production/tts_engine.py:154` (chain `["elevenlabs", "openai_tts", "edge_tts"]`)
  - `src/production/tts_engine.py:156` (chain `["openai_tts", "edge_tts"]`)
- [ ] Verifikasi catalog `AI_IMAGE_MODELS` di `src/providers/visual/ai_image.py:20-38`
- [ ] Verifikasi 7 lokasi hardcode niche_fallback `"universe_mysteries"` (SOFTCODE §6)
- [ ] Cek `tenant_configs` schema sekarang (list semua kolom)
- [ ] Snapshot daftar file yang akan diubah + rencana commit per file

**Validation gate:** Tabel "klaim docs vs realita kode" disetujui user.

---

## 🔧 PHASE 1 — SOFTCODE AI CONFIG (6 sub-phase)

### 1.1 — LLM Refactor (paling besar, paling penting)
**Scope:**
- Schema: tambah `llm_library` (text), `llm_models` (jsonb) ke `tenant_configs`
- Code: refactor `script_engine`, `script_analyzer`, `hook_optimizer`, `niche_selector`, `ai_image` (untuk rewrite)
- **Hapus silent fallback Claude→GPT** di `script_engine._call_llm()`
- Per [[plan_s93_config_driven_llm]] yang sudah dimatangkan

> **🔑 REKONSILIASI dari Phase 0 audit (2026-06-12, LOCKED — jangan analisa ulang):** Skema `tenant_configs` SEKARANG (dibaca `tenant_config.py` `.select("*")`) sudah punya **kolom terkait yang SOFTCODE tidak catat** — wajib direkonsiliasi, bukan sekadar ADD:
> - `llm_provider`+`llm_model` (flat, single model) **sudah ada** → Phase 1.1 ADD `llm_library`+`llm_models`(jsonb per-task). **Migrasi:** isi `llm_models` dari `llm_model` existing; pertahankan `llm_provider` sbg back-compat sampai semua kode baca `llm_library`.
> - `llm_script_fallback` (default `gpt-4o-mini`) **= cross-library fallback yang §1 mau HAPUS** → drop/abaikan, ganti retry in-library.
> - `tts_fallback_provider` (default `edge_tts`) **sudah ada** → Phase 1.2/1.4 `tts_fallback` REUSE kolom ini (jangan bikin duplikat); `tts_library` = `tts_provider` existing.
> - `production_on_api_error` (default `fallback`) kontrol silent-fallback → audit saat hapus fallback.
> - Realita kode (verified): semua hardcode LLM/TTS akurat persis (lihat journal 2026-06-12). worker niche `:83` (bukan :79); `AI_IMAGE_MODELS` `:22-44`; `music_selector.py` di `src/providers/music/`.
>
> **⚠️ VALIDATION GATE v2 ≠ v1:** gate di bawah (push→VPS→restart worker) adalah **pola v1 lama**. Untuk **v2**, validasi terhadap **DB CLONE v2 + worker lokal/branch v2**, **JANGAN sentuh v1 VPS/DB** sampai cutover (lihat [[decisions_v1_v2_migration]]). v1 tetap produksi normal selama dev v2.

**File yang berubah:**
- `src/intelligence/script_engine.py` — hapus fallback + fix ScriptAnalyzer key
- `src/intelligence/script_analyzer.py` — dual provider support
- `src/intelligence/niche_selector.py` — ganti `visual_api_key` → `llm_api_key` + dual provider
- `src/intelligence/hook_optimizer.py` — sama dengan niche_selector
- `src/providers/visual/ai_image.py` — prompt rewrite via `llm_models.rewrite`
- `src/config/tenant_config.py` — tambah field baru

**Validation gate:**
- Push ke main → SSH VPS → git pull → restart worker
- Update `tenant_configs` di Supabase: set `llm_library='anthropic'` + `llm_models` jsonb
- Enqueue 1 production run
- ✅ **Lulus jika:** pipeline COMPLETE + zero OpenAI call di log untuk komponen LLM (NicheSelector pakai Claude saat tenant Claude)

> ### ✅ 1.1 STATUS — DONE + TERVALIDASI STRUKTURAL (2026-06-13)
> Diperluas jadi **AI Provider Catalog DB-driven** (atas directive user 2026-06-13 — lihat §"AI PROVIDER CATALOG"). Yang selesai & tervalidasi terhadap **v2 nyata**:
> - **Skema:** `migrations/0001` (backfill `llm_library`+`llm_models` per-task — applied v2; row `ryan_andrian` OK) + `migrations/0002` (tabel `ai_providers`+`ai_models`, RLS+read-policy, seed 2 provider + 4 model LLM — applied v2).
> - **Kode:** lapisan `src/providers/llm/` (base + `catalog.py` loader REST + `adapters.py` per-protokol + factory DB-driven). 5 call-site (`script_engine`/`script_analyzer`/`niche_selector`/`hook_optimizer`/`ai_image`) lewat abstraksi. Dihapus: SDK langsung, silent fallback Claude→GPT, `visual_api_key` utk LLM, `SUPPORTED_MODELS`, 3 parser duplikat, `claude.py`/`openai.py`. Net −282 baris.
> - **Bukti:** `py_compile` ✅ · katalog dibaca REST+RLS ✅ · `build_llm_provider` resolve adapter dari DB ✅ · backfill row OK ✅. (**Belum**: real production-run = gate user; commit/push.)
> - **Reconciliation §1.1 (LOCKED) terpenuhi:** `llm_provider`/`llm_model` legacy dipertahankan (back-compat); `llm_script_fallback` di-deprecate (di-`0001`); silent fallback dihapus.

### 1.2 — Niche Fallback Config
**Scope:**
- Schema: tambah `niche_fallback` (text, default `'universe_mysteries'`) ke `tenant_configs`
- Code: hapus 7 hardcode `"universe_mysteries"` di:
  - `src/orchestrator/pipeline.py:575,595,599`
  - `src/intelligence/schedule_manager.py:110-111`
  - `src/intelligence/config.py:14`
  - `src/config/tenant_config.py:86,452,488,503`
  - `scripts/worker.py:79`
  - `src/production/visual_assembler.py:287`

**Validation gate:** `grep -r "universe_mysteries" src/ scripts/` = zero match (kecuali file provider/test/youtube_publisher data).

> ### ✅ 1.2 STATUS — DONE + TERVALIDASI STRUKTURAL (2026-06-13)
> **Revisi best-practice (keputusan user):** alih-alih default global, pakai **gate enforcement di hulu + fail-loud di hilir**. `niche_fallback` = **NULLABLE, tenant-specific** (bukan default global mystery). Migration `0003` applied v2.
> - **Site produksi diperbaiki:** `worker.py:83` (resolver + **fail-loud** raise bila niche kosong), `visual_assembler.py:287`, `schedule_manager.py:110-111` (fallback niche tenant, bukan global). Resolver `TenantRunConfig.niche_or_fallback()` = `niche_fallback → niche → niche_pool[0] → '' (fail-loud)`. Default dataclass `niche`/`niche_pool` → `''`/`[]` (buang mystery global).
> - **KEEP (verified, bukan produksi):** `pipeline.py:575/590/595/599` = blok `__main__` demo (line >566); test/`__main__`, `youtube_publisher`, data-map provider TTS/visual (`NICHE_VOICES[...]`), komentar. (Koreksi: line-number spec SOFTCODE §6 usang.)
> - **Bukti:** compile ✅ · grep site produksi = 0 ✅ · resolver runtime ✅ · `ryan_andrian` niche=`universe_mysteries` (non-empty) + pool 4 niche → nol breakage ✅.
> - **FOLLOW-UP ditindaklanjuti di fasenya:** **gate enforcement** (niche/niche_pool WAJIB sebelum schedule dibuat) → Phase 5 (schedule) + Phase 9-10 (onboarding C4) + pertimbangan constraint DB.

### 1.3 — Visual Image Catalog → DB
**Scope:**
- Schema: buat tabel `ai_image_models` (`model_key` PK, `platform`, `model_id`, `description`, `size`, `is_active`)
- Seed data: 3 model existing (flux-schnell, gpt-image-1-mini, stable-diffusion)
- Code: `ai_image.py` load catalog dari Supabase
- `visual_assembler.py` — hapus default `"gpt-image-1-mini"`

**Validation gate:** 1 production run sukses dengan model dipilih via DB row.

> ### ✅ 1.3 STATUS — DONE + TERVALIDASI STRUKTURAL (2026-06-13)
> Pakai **`ai_models` terunifikasi** (component='image') — BUKAN tabel `ai_image_models` terpisah (selaras AI Provider Catalog, satu katalog semua komponen). Migration `0004` (provider `replicate` + 3 model image) applied v2.
> - `ai_image.py`: hapus dict hardcode `AI_IMAGE_MODELS` → load `model_config` (platform=provider_key, model_id, size) dari katalog DB via loader. Model tak dikenal → fail-loud `VisualError`. `visual_assembler.py:217`: buang default `gpt-image-1-mini` → `''`.
> - **Bukti:** compile ✅ · grep `AI_IMAGE_MODELS`=0 ✅ · `AIImageProvider` resolve `gpt-image-1-mini`(openai) + `flux-schnell`(replicate) dari DB ✅ · unknown→fail-loud ✅. Katalog v2: 3 provider / 7 model (4 llm + 3 image).
> - **Belum:** real image-gen run (butuh key OpenAI/Replicate + biaya) — resolusi katalog terbukti; generate aktual = saat full-pipeline run.

### 1.4 — TTS Fallback Softcode
**Scope:**
- Schema: tambah `tts_library` (text), `tts_fallback` (text) ke `tenant_configs`
- Code: `tts_engine.py` — bangun fallback chain dari config, bukan hardcode

**Validation gate:** fallback hanya dalam ekosistem yang sama (e.g., elevenlabs → edge_tts, BUKAN elevenlabs → openai_tts).

> ### ✅ 1.4 STATUS — DONE + TERVALIDASI STRUKTURAL (2026-06-13)
> **Tanpa migrasi** (rekonsiliasi §1.1): `tts_library`=`tts_provider`, `tts_fallback`=**reuse `tts_fallback_provider`** (kolom sudah ada). `tts_engine.py`: chain hardcode `["elevenlabs","openai_tts","edge_tts"]`/`["openai_tts","edge_tts"]` **DIHAPUS** → chain config-driven `[tts_provider, tts_fallback_provider]` deduped; `_get_provider_config` sertakan `tts_fallback_provider`.
> - **No silent cross-vendor:** elevenlabs primary → fallback **edge_tts** (default), BUKAN openai_tts (yang tenant mungkin tak punya key). Bukti: compile ✅ · grep chain hardcode=0 (seluruh src) ✅ · simulasi chain ✅ (elevenlabs→edge_tts).
> - **Follow-up (deeper, ditindaklanjuti pada saatnya):** TTS provider/voice **catalog-wiring** (ai_providers/ai_models component='tts' + tts_engine baca provider/voice dari DB) — analog 1.3 tapi lebih dalam (voice per-niche). Voice data-map di file provider (`NICHE_VOICES` dst) = data, sah keep sampai catalog-wiring.

### 1.5 — Music + R2 Defaults Hapus
**Scope:**
- Schema: tambah `music_default_mood` ke `tenant_configs`
- Code: `music_selector.py:88` hapus default `"dramatic"`, baca dari config
- Code: `intelligence/config.py:35` hapus default `"viral-machine"` untuk R2 — wajib di `.env`, raise error jika kosong

**Validation gate:** start worker tanpa `R2_BUCKET` → error message jelas + tenant pakai mood dari config.

> ### ✅ 1.5 STATUS — DONE + TERVALIDASI STRUKTURAL (2026-06-13)
> Migrasi `0005` (`music_default_mood` nullable, applied v2). `music_selector.py`: mood hardcode `"dramatic"` → config `music_default_mood` (threaded video_renderer→_mix_music→select_and_download→_detect_mood); kosong → mood any-active (graceful, no global default). `R2_BUCKET`: default `"viral-machine"` DIHAPUS di `music_selector` (→ raise jelas jika kosong saat download) + `intelligence/config.py` (→ `""`).
> - **Bukti:** compile ✅ · grep `'dramatic'`=0 + bucket-default=0 ✅ · runtime: mood pakai config / fallback any-active ✅.

### 1.6 — Bug Fixes Bundle (pasangan refactor hari ini)
- **Dispatcher timezone bug**: `dispatch_pipeline_jobs()` saat ini compare publish_slots dengan UTC, tidak hormati `tenant_configs.timezone`. Fix: konversi target ke timezone tenant sebelum compare.
- **`AIImageProvider._generate_image()` signature mismatch**: warning saat hook_frame generation:
  ```
  WARNING [s6c7] Hook frame generation failed (AIImageProvider._generate_image() 
  missing 1 required positional argument: 'output_path')
  ```

**Validation gate:** dispatcher fire pada slot WIB yang benar + hook_frame generated tanpa warning.

> ### ✅ 1.6 STATUS — DONE (2026-06-13)
> - **Bug 2 (FIXED):** `visual_assembler:318` panggil `_generate_image(prompt, img_path)` kurang arg → `_build_image_prompt(prompt)` lalu `_generate_image(positive, negative, img_path)`. Validasi: compile + signature/arity match (inspect.bind) ✓. (Tanpa real image-gen — butuh key.)
> - **Bug 1 (RE-KLASIFIKASI, bukan skip):** `dispatch_pipeline_jobs()` timezone = **pg_cron SQL function di DB v1**, BUKAN kode Python repo (verified: grep repo-wide kosong; MESIN_VIRAL:184 "publish_slots = jam UTC"). **Tak di-clone ke v2; ada di v1-produksi (jangan disentuh).** → jadi **requirement Phase 5** (publisher v2 decouple, timezone-aware by-design per [[decisions_production_scaling]]). Tak bisa & tak boleh difix sebagai kode v2 sekarang.
> - **Phase 1 SOFTCODE = SELESAI.** Semua komponen AI (LLM/image/TTS/niche/music/R2) config-driven; nol silent cross-provider fallback; katalog DB-driven.

---

## 🔁 GitHub Workflow Per Sub-Phase

```
1. Code change di /home/rad/viral-machine (WSL dev)
2. Test lokal jika applicable
3. git add <files> → git commit (per sub-phase, commit message standar)
4. git push origin main
5. ssh vps → cd ~/viral-machine → git pull origin main
6. pip install -r requirements.txt (jika ada)
7. Apply SQL migration via Supabase MCP (jika ada)
8. Restart worker: ssh vps → kill PID + nohup restart
9. Enqueue test job (INSERT pipeline_queue)
10. Monitor pipeline_queue + worker.log
11. ✅ Validate pass → UPDATE PROGRESS.md + memory + roadmap_1.md → commit "docs: phase X.Y validated"
    ❌ Fail → rollback (git revert) → diagnose → retry
12. → next sub-phase
```

### Commit Message Standar
```
feat(s93): softcode LLM library/models — niche_selector, hook_optimizer, script_analyzer

Phase 1.1 of master_softcode_to_saas. Removes hardcode model strings.
Validation: production run #97 success with claude-sonnet-4-6 end-to-end.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 📝 PHASE 2 — Error Management Terpusat
**Scope:**
- Buat `src/exceptions.py` dengan hierarchy: `PipelineError` → `ConfigError` / `LLMError` / `TTSError` / `VisualError` / `PublishError`
- Refactor semua `raise Exception(...)` → typed exceptions
- Pipeline catch typed → log + Telegram + write ke `pipeline_errors` (existing table)

**Validation gate:** simulasi 4 jenis error → semua tercatat di Supabase + Telegram notif sesuai jenis.

> ### ✅ PHASE 2 STATUS — DONE (2026-06-13)
> - **`src/exceptions.py`**: `PipelineError` base + `ConfigError/LLMError/TTSError/VisualError/RenderError/PublishError` (bawa `category`+`step`).
> - **Unifikasi**: `LLMError`/`TTSError`/`VisualError` di `providers/{llm,tts,visual}/base.py` di-**re-export** dari `src.exceptions` → kini `PipelineError` subclass, **import lama tetap jalan** (verified `is` identik + `except LLMError` tetap nangkap).
> - **Pipeline**: 6 `raise Exception(...)` step → typed (`LLMError`/`TTSError`/`VisualError`/`RenderError` + `step`); `except BaseException` capture `error_category`+`error_step` ke `result` + log. Telegram `notify_failure` + `write_failed_run` (production_runs) sudah ada.
> - **Bukti**: compile ✅ · `raise Exception(` generik=0 ✅ · runtime hierarki/kategori/step + re-export identity ✅.
> - **DEFER ke Phase 3 (transparan):** persist error ke tabel `pipeline_errors` — **tabel belum ada di v2** (Phase 3 bangun `pipeline_run_logs` + konsolidasi). Untuk sekarang error tercatat di `production_runs` (write_failed_run) + Telegram. **Local ValueError** (provider/key/bucket-missing di niche/hook/music) **sengaja TIDAK diretype** — mereka di-catch lokal untuk retry/graceful; retype → ubah control-flow (risiko).

---

## 📊 PHASE 3 — Pipeline Run Logs (DB-based)
**Scope:**
- Schema: `pipeline_run_logs` table dengan `tenant_id`, `channel_id` (placeholder), `queue_id` FK, `level`, `step`, `message`, `metadata` jsonb
- RLS policy (placeholder, aktif setelah Phase 4)
- Custom loguru sink: `src/utils/db_log_sink.py` — batch insert ke DB
- Konsolidasi `pipeline_errors` + `qc_failed_videos` jadi views dari `pipeline_run_logs`
- Hapus rencana file-based `PIPELINE_LOG_SEPARATION` (superseded)

**Validation gate:** pipeline run → events appear in DB dalam < 5 detik dari emit.

> ### ✅ PHASE 3 STATUS — DONE (2026-06-13)
> - **Migrasi `0006`**: tabel `pipeline_run_logs` (tenant_id/channel_id-placeholder/queue_id/run_id/level/step/category/message/metadata jsonb), index, **RLS forward-compatible** (`SELECT tenant_id=auth.uid()`; dormant s/d Phase 4; INSERT hanya service_role). Applied v2.
> - **`src/utils/db_log_sink.py`**: loguru sink → `pipeline_run_logs`. **enqueue=True** (thread bg, tak memblok render 35 mnt) + **flush per-record** (live-tail <5s). Konteks (tenant_id/queue_id/run_id) dari `record["extra"]`; **filter**: hanya log ber-`tenant_id` (skip noise global). Best-effort (gagal flush → stderr, tak crash pipeline).
> - **Worker wiring**: `setup_db_logging()` di `main()`; call `_run_production` di-wrap `logger.contextualize(tenant_id, queue_id)` + `flush_logs()` (drain enqueue) di `finally`. queue_id = kunci grouping run (↔ `production_runs`).
> - **Konsolidasi `pipeline_errors`/`qc_failed_videos` → view:** N/A (tabel tsb tak ada di v2; `pipeline_run_logs` = sumber baru). **Menutup DB-persist error yang di-defer Phase 2** (error typed → log ber-kategori → DB).
> - **Bukti:** compile ✅ · sink build-row + filter konteks ✅ · shape valid roundtrip ke `pipeline_run_logs` ✅. **Catatan:** INSERT produksi butuh **service_role** (anon ke-block RLS — by design); e2e REST insert belum dites (tak ada service_role key di dev).

---

## 🔐 PHASE 4 — BYO-CC Phase 1 + Auth foundation
> **Auth model DIPUTUSKAN ([[decisions_auth_rbac]]):** `tenant_id = auth.uid()` (1 user=1 tenant, no team); RLS=`tenant_id=auth.uid()`; super-admin via `app_metadata`; migrasi "ryan_andrian"→UUID di sini.

**Scope (per [[project_byocc_roadmap]]):**
- Tabel `tenant_credentials` di Supabase
- `src/utils/crypto.py` Fernet utility, master key di `.env` VPS (`ENCRYPTION_KEY`)
- Modifikasi `youtube_publisher.py` & `channel_analytics.py` load OAuth dari DB
- Mandatory key validation di pipeline start (per provider yang dipilih tenant)
- Hapus semua `.env` fallback untuk API key tenant

**Validation gate:** tenant tanpa required key → pipeline berhenti + Telegram notif yang jelas; tenant dengan key valid → pipeline jalan normal.

> ### 🛠️ PHASE 4 STATUS (2026-06-13) — rencana desain di `PHASE4_DESIGN.md`
> **Konteks tenant (owner):** `ryan` = tenant developer/tester (tenant #1); ke depan dapat **kupon diskon 100%/bulan by-system** → fitur **Phase 8 (payment/coupon)**, bukan sekarang.
> - **✅ 4.1 DONE:** `src/utils/crypto.py` (Fernet; `ENCRYPTION_KEY` di `.env`, gitignored) + migr `0007` `tenant_credentials` (OAuth `*_enc`, RLS service_role-only). Validasi: encrypt≠plaintext + decrypt match + DB roundtrip ✅.
> - **✅ 4.2 DONE (service_role key disediakan owner):** Auth user ryan dibuat (`ryan@lumite.biz.id`) → **`auth.uid()` = `a410251c-cb09-492f-8342-0d829cd7de60`**. Remap `tenant_id` `"ryan_andrian"`→UUID di **8 tabel** (transaksi atomik; FK `channels_tenant_id_fkey` drop→remap→re-add; count utuh: tenant_configs1/channels1/channel_insights15/production_runs99/production_schedules5/video_analytics3182/videos211/pipeline_queue101; 0 sisa). `display_handle="ryan_andrian"`. Migr `0008`.
> - **✅ 4.3 DONE + security fix:** RLS go-live — policy SELECT `tenant_id=auth.uid()::text` di 9 tabel privat. **Temuan kritis: policy `service_all` (ALL,public,USING true) clone-v1 → BOCOR (anon baca/tulis semua)** → DIHAPUS (migr `0009`) di 6 tabel + `plan_limits` jadi read-only. **Verified isolasi: service_role lihat data, anon=0 di semua 8 tabel.** music_library/niches/moods/fonts = shared (tetap public-read). `service_role` bypass RLS otomatis (worker).
> - **⚠️ Konsekuensi:** **worker v2 WAJIB pakai `SUPABASE_KEY=service_role` + `SUPABASE_URL=v2`** (anon kini ke-block tabel tenant). Recorded.
> - **✅ 4.4 DONE (code):** `src/utils/tenant_credentials.py` (load/save OAuth decrypt Fernet) + `youtube_publisher._get_credentials` **DB-first + file-fallback** (non-breaking; refresh → save_google_access_token ke DB bila source=db). Validasi: loader decrypt roundtrip ✓. **Seed token ryan ke DB = pending** (file di VPS v1; sampai itu jalan via file-fallback).
> - **✅ 4.5 DONE:** `TenantRunConfig.missing_credentials()` (key wajib per provider terpilih; edge_tts/pexels gratis) → pipeline **STEP 0** raise `ConfigError` fail-loud SEBELUM produksi 35 mnt. Validasi: lengkap→[], kurang→list, gratis→[] ✓.
> - **Senior call:** AI keys (tenant_configs, BYOK) cukup RLS-protected (tenant_credentials fokus OAuth).

---

## 🎬 PHASE 5 — Multi-Channel per Tenant
**Scope:**
- Tabel `channels` (channel_id, tenant_id, youtube_channel_id, oauth_creds_enc, niche_default, is_active)
- `channel_id` propagation di pipeline (di-pass dari worker → orchestrator → publisher)
- `production_schedules` dapat `channel_id`
- Analytics isolation: `video_analytics` filter per channel
- Update `pipeline_run_logs.channel_id` aktif

**Validation gate:** 1 tenant 2 channel berbeda niche → both produce + publish independently.

---

## 🥇 PHASE 6 — Self-Learning + Diversity Engine (CORE MOAT)
**Scope (detail di `DESAIN_PRODUK_SAAS.md`):**
- Self-Learning Feedback Engine — pull YouTube Analytics 24-72h post-publish, adapt config per channel (niche/hook/visual weighting)
- Diversity Engine — voice/hook/niche rotation algorithm (AI Slop Defense)

**Validation gate:** TBD saat phase dimulai (post Phase 5).

---

## 🛡️ PHASE 7 — Compliance Score + AI Slop Defense Polish (SURVIVAL)
**Scope:**
- Compliance Score calculator (5 dimensi) — feed widget D20
- Polish diversity rotation + threshold tuning

**Validation gate:** TBD.

---

## 💳 PHASE 8 — Payment Integration
**Scope:**
- **Midtrans** (Indonesia-native, **akun owner sudah tersedia** per 2026-06-11) webhook handler — ganti rencana Xendit/Stripe
- Email service (Resend)
- Subscription state ↔ scheduler gate (suspend → stop produksi)
- Tier-gating: caps videos/day + platform (Pro=Reels, Scale=TikTok) + add-on (custom niche, ai_video BYOK)

**Validation gate:** TBD.

---

## 🎨 PHASE 9-10 — UI Foundation + Polish
**Scope (sesi terpisah — via Claude Design workflow, lihat [[plan_frontend_via_claude_design]]):**
- Next.js app baru atau subdir `apps/web/`
- Supabase Auth — login per tenant
- Page: dashboard, config, scheduler, reports, **logs per tenant**
- Supabase Realtime subscription untuk live tail `pipeline_run_logs`
- Deploy: Vercel atau VPS terpisah

**Validation gate:** tenant A login → hanya lihat data tenant A (RLS test).

---

## 📋 Docs Sync (Cross-Cutting, Continuous — bukan phase bernomor)
- Update `MESIN_VIRAL.md` per perubahan arsitektur (worker, dispatcher, tabel baru)
- Update `roadmap_1.md` per item completed (mark ✅ dengan tanggal)
- Delete `SOFTCODE_AI_CONFIG - BELUM DI EKSEKUSI.md` setelah Phase 1 selesai
- Delete `PIPELINE_LOG_SEPARATION - BELUM DI EKSEKUSI.md` setelah Phase 3 selesai
- Sync memory files dengan realitas baru

---

## 🐛 KNOWN ISSUES (Hari Ini, 2026-06-10)

| # | Issue | Severity | Phase | Notes |
|---|---|---|---|---|
| 1 | NicheSelector/HookOptimizer/ScriptAnalyzer hardcode OpenAI meskipun config Claude | 🔴 Critical | Phase 1.1 | Root cause kegagalan job 94 & 95 hari ini |
| 2 | Dispatcher `dispatch_pipeline_jobs()` tidak hormati `tenant_configs.timezone` — publish_slots di-treat UTC | 🟠 High | **→ Phase 5** | **pg_cron DB v1 (bukan kode repo), tak di-clone v2, v1 jangan disentuh** → requirement publisher v2 (timezone-aware by-design) |
| 3 | `AIImageProvider._generate_image()` signature mismatch saat hook_frame | 🟡 Medium | 1.6 | ✅ **FIXED (2026-06-13)** — `_build_image_prompt` + 3-arg call |
| 4 | `tenant_configs.publish_slots` setting WIB tapi treated UTC | 🟠 High | **→ Phase 5** | Bagian dari #2 (pg_cron DB) |

---

## 📂 FILE REGISTRY

### Project root (this repo) — semua `.md` di-exclude dari VPS (sparse-checkout aktif)
- `PROGRESS.md` — **this file** — live status A-to-Z (plan vs realisasi) + master roadmap 12-phase + EPIC tracker
- `DESAIN_PRODUK_SAAS.md` — **konsep induk produk** (business, pricing, roadmap, epic concept §12b, payment Midtrans)
- `MULTI_FORMAT_STUDIO.md` — **spec teknis epic Multi-Format Studio** + **§0 validasi tervalidasi (jangan analisa ulang)**
- `CLAUDE_DESIGN_BRIEF.md` — spec desain UI (39 screen); bundle final di `design-source/` (gitignored)
- `CLAUDE_DESIGN_ADDENDUM_v2/v3/v4.md` — delta prompt desain (historis; sudah terserap ke brief+bundle)
- `MESIN_VIRAL.md` — dokumentasi arsitektur teknis (perlu sync, terakhir update 8 Apr 2026)
- `roadmap_1.md` — checklist roadmap (perlu sync, terakhir update 8 Apr 2026)
- `SOFTCODE_AI_CONFIG - BELUM DI EKSEKUSI.md` — spec Phase 1, akan dihapus saat selesai
- `PIPELINE_LOG_SEPARATION - BELUM DI EKSEKUSI.md` — superseded oleh Phase 3 DB-based

### Memory (auto-loaded sesi baru)
- `MEMORY.md` — index
- `plan_master_softcode_to_saas.md` — ringkasan master plan (this doc → memory)
- `progress_journal.md` — per-phase completion log
- `project_vision.md` — visi & prinsip non-negotiable
- `project_byocc_roadmap.md` — BYO-CC roadmap (memory)
- `plan_s93_config_driven_llm.md` — **superseded** oleh Phase 1.1
- `feedback_workflow.md` — wajib propose dulu
- `feedback_no_hardcode.md` — no silent fallback
- `feedback_analysis_discipline.md` — no asumsi liar

---

## 🚀 QUICK-START UNTUK SESI BARU

**Urutan baca kanonik = `MEMORY.md` (auto-loaded) — ikuti itu.** Ringkas:
1. `MEMORY.md` (index + urutan baca) → 2. `progress_journal.md` (kronologis terbaru) → 3. **file ini** (status LIVE + next step) → 4. `DESAIN_PRODUK_SAAS.md` (pondasi: bisnis, arsitektur §12b/§12c).
   Lalu sesuai TRACK: **Backend** → [[decisions_production_scaling]] + `MULTI_FORMAT_STUDIO.md §0` + `SOFTCODE_AI_CONFIG…md`; **Frontend** → [[plan_frontend_via_claude_design]] + `design-source/mesinviral-com/project/CLAUDE.md` + `CLAUDE_DESIGN_BRIEF.md`.
5. Verify state: `git status` + `git log -5` + (track backend) `ssh vps && tail logs/worker.log`.
6. Tanya user: "Lanjut dari [next-step di STATUS SAAT INI] atau ada arahan baru?"

**⛔ Jangan jadikan acuan:** `MESIN_VIRAL.md`, `roadmap_1.md` (usang April), `PIPELINE_LOG_SEPARATION` (superseded Phase 3), `plan_s93` (superseded Phase 1.1) — semua sudah ada banner.

---

## 📊 VALIDATION HISTORY

| Tanggal | Phase | Job ID | Hasil | Notes |
|---------|-------|--------|-------|-------|
| 2026-06-13 | 1.2 (niche_fallback) | — (struktural) | ✅ PARTIAL | Applied v2: migr 0003 (`niche_fallback` nullable). Best-practice: gate-enforcement + fail-loud, no global default. compile OK · grep site produksi=0 · resolver OK · `ryan_andrian` niche non-empty → no breakage. Real production-run BELUM. |
| 2026-06-13 | 1.1 (LLM + AI Catalog) | — (round-trip) | ✅ **HIJAU** | **Production-run LLM-path GREEN.** v2 ryan dibelokkan ke OpenAI (key Anthropic clone-v1 mati → 401; OpenAI key valid di `visual_api_key`). catalog(DB)→`OpenAIChatAdapter`("OpenAI GPT" dari DB)→**REAL OpenAI API**→`{"ok":true,"engine":"openai"}` parsed ✓. **Membuktikan: ganti provider = 1 baris config DB (`llm_library`), nol perubahan kode.** Key Anthropic invalid = isu kredensial bukan bug. |
| 2026-06-13 | (config v2) | — | ✅ INTENDED | **v2 ryan_andrian LLM = OpenAI** (pilihan owner): `llm_library=openai`, `llm_api_key←visual_api_key`, `llm_models→gpt-4o/4o-mini`. **Bukan temporary** — ganti ke Claude = **test post-go-live, DI LUAR plan** (key Anthropic dilepas dari plan per arahan owner 2026-06-13). **v1 TIDAK disentuh.** |
| 2026-06-13 | **S3 janitor anti-sampah** | sweep stale + reconcile orphan (real) | ✅ **HIJAU** | `buffer_janitor.py` (TTL `expires_at` + orphan reconcile, grace anti in-flight) + thread di `worker_decoupled`; bug publisher thumbnail difix. Tervalidasi: sampah terhapus, bucket bersih. QC floor→3 interim. **`QC_CONTENT_ARCHITECTURE.md`** (living doc: QC v2 relatif-preset + self-improvement; fase nunggu owner). |
| 2026-06-13 | **FULL LOOP DECOUPLE (real)** | produce→buffer→publish YouTube | ✅ **HIJAU** | edge_tts 35.2s LOLOS QC (min baru 20s; aturan lama 45s buang sia-sia), publish PRIVATE nyata `shorts/7ocW6BPdlVg`, privacy diverifikasi YouTube API, OAuth DB-first terpakai, slot Asia/Jakarta (Bug1). QC→gate-integritas config-driven; privacy config-driven. |
| 2026-06-13 | **VALIDASI HOLISTIK local** | semua (real) | ✅ **36/36 PASS** | compileall ✅ · 50 modul import bersih ✅ · suite 29/29 (DB 11 migrasi, P1.1-P5.3, RLS isolasi anon=0, buffer Biznet e2e, inventory, semaphore-brake, Bug1-timezone) ✅ · suplemen 1.4/1.5/1.6 7/7 ✅. SEMUA item built valid di local. Yang tak bisa di-local = produce→render→publish nyata (= cutover Step 4, belum dibangun + butuh run berbiaya). |
| 2026-06-13 | **Phase 5 buffer e2e** | Biznet S3 (real) | ✅ **HIJAU** | s3_buffer upload→download→verify→delete ke Biznet Gio (bucket `tobe-submitted`) BERFUNGSI nyata (secret+bucket dari owner). Infra buffer proven. 5.3 decouple producer/publisher = next (design-review). |
| 2026-06-13 | align + **Phase 5.1** | DB v2 | ✅ | Align: pricing_config + content_languages (0010). P5.1: content_inventory + channel_id (production_runs/pipeline_queue) (0011) + `s3_buffer.py` util (Biznet, env). S3-CONNECTION gitignored. v2=20 tabel. 5.3 decouple=design-review (S3 secret pending). |
| 2026-06-13 | **Phase 4.4+4.5** → **Phase 4 SELESAI** | — (struktural) | ✅ | 4.4 `tenant_credentials.py` loader (decrypt) + youtube_publisher DB-first+file-fallback (loader roundtrip OK; seed token pending). 4.5 `missing_credentials()` + pipeline STEP 0 fail-loud (ConfigError). compile OK. |
| 2026-06-13 | **Phase 4.2+4.3** (auth+RLS) | DB v2 (real) | ✅ **+ security fix** | Auth user ryan (uid a410251c…) + remap tenant_id→UUID 8 tabel (count utuh, FK handled) + display_handle. RLS go-live. **KRITIS: drop `service_all` permissive (clone-v1) yg bikin anon baca/tulis semua** + plan_limits read-only. **Verified isolasi: anon=0, service_role bypass** semua tabel tenant. Worker v2 wajib service_role key. Migr 0008/0009. |
| 2026-06-13 | **Phase 4.1** (crypto+creds) | — (struktural) | ✅ | `src/utils/crypto.py` Fernet (ENCRYPTION_KEY .env) + migr 0007 `tenant_credentials` (RLS service_role-only). encrypt≠plaintext + decrypt match + DB roundtrip OK. 4.2/4.3 (auth user+tenant_id→UUID+RLS) gate service_role key; 4.4/4.5 menyusul. |
| 2026-06-13 | **Phase 3** (Run Logs DB) | — (struktural) | ✅ | Migr 0006 `pipeline_run_logs` (RLS-ready) + `db_log_sink` (loguru→DB, enqueue, per-record, filter konteks) + worker contextualize/flush. compile OK · sink row+filter OK · shape roundtrip OK. INSERT produksi=service_role (anon block RLS). |
| 2026-06-13 | **Phase 2** (Error Mgmt) | — (struktural) | ✅ | `src/exceptions.py` hierarki PipelineError + unifikasi LLM/TTS/VisualError (re-export, import lama jalan) + 6 raise pipeline → typed + catch kategori/step. compile OK · `raise Exception(`=0 · runtime isinstance/kategori OK. DB-persist `pipeline_errors`→Phase 3 (tabel belum ada). |
| 2026-06-13 | 1.6 (bugfix) → **Phase 1 SELESAI** | — (struktural) | ✅ | Bug 2 `_generate_image` signature FIXED (compile + arity match). Bug 1 dispatcher-tz = pg_cron DB v1 (bukan repo) → re-klasifikasi Phase 5. Phase 1 SOFTCODE komplit (1.1-1.6). |
| 2026-06-13 | 1.5 (music/R2) | — (struktural) | ✅ | Migr 0005 (`music_default_mood`). mood `'dramatic'` → config (threaded); R2_BUCKET default `'viral-machine'` dihapus → fail-loud. compile OK · grep dramatic/bucket=0 · runtime mood threading OK. Real music-gen BELUM (R2 keys absen di .env dev). |
| 2026-06-13 | 1.4 (TTS chain) | — (struktural) | ✅ | TTS chain hardcode dihapus → config-driven (`tts_provider`+`tts_fallback_provider`, no migrasi per §1.1). No silent cross-vendor (elevenlabs→edge_tts default). compile OK · grep chain hardcode=0 · simulasi chain OK. Real TTS-gen BELUM (butuh key+biaya). Catalog-wiring TTS = follow-up. |
| 2026-06-13 | RE-AUDIT 1.1/1.2/1.3 | commits `8e40fd8`,`3fb8cbb` | ✅ | Sweep adversarial global (user skeptis). Fix miss: default niche di 6 file provider; default `openai`/model di visual_assembler; **layer legacy tenant_config** (llm_model_for/effective/loader/dataclass → ''/None fail-loud; llm_script_fallback DEAD→None). grep default provider/model business-logic=0. PENDING (bukan miss): TTS chain `tts_engine:154/156` = Phase 1.4. |
| 2026-06-13 | 1.3 (image catalog) | — (struktural) | ✅ | Applied v2 migr 0004 (provider replicate + 3 model image). `ai_image` load `model_config` dari `ai_models` DB; `AI_IMAGE_MODELS` hardcode dihapus. compile OK · resolve openai+replicate dari DB OK · unknown→fail-loud OK. Real image-gen BELUM (butuh key+biaya). |
| 2026-06-13 | 1.1 commit | branch `v2-backend` `f7e9832` | ✅ | Commit ke **branch v2-backend** (BUKAN main — `src/` tak di-exclude sparse-checkout → lindungi v1). `main` tetap `31a558b`. |
| 2026-06-10 09:31 | Pre-Phase-0 | #96 | ✅ SUCCESS | OpenAI billing aktif, pipeline normal, dipakai sebagai baseline |
| 2026-06-10 05:30 | — | #95 | ❌ FAILED | OpenAI 429 billing_not_active — root cause yang memicu refactor |
| 2026-06-09 20:30 | — | #94 | ❌ FAILED | Same as #95 |
| 2026-06-09 05:30 | — | #93 | ✅ SUCCESS | Sebelum billing OpenAI berhenti |

---

**END OF FILE. Update setiap selesai sub-phase.**
