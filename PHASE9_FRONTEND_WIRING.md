# PHASE 9-10 — Frontend Wiring (mock → Supabase v2) — Rencana Breakdown

> **Status:** 📋 DESIGN (propose-first — review owner sebelum koding). Status LIVE per sub-phase = `PROGRESS.md` (jangan duplikat status di sini). Konvensi sama `PHASE4/5/6_DESIGN.md`.
>
> **Tujuan:** wire **28 layar mock `apps/web`** ke **Supabase v2** (`atliatnjhysdibmfypul`) — Auth + RLS + Realtime — sehingga produk benar-benar dipakai tenant. Backend Phase 0-8 sudah LENGKAP & headless; ini satu-satunya jalur ke beta/revenue.
>
> Sumber desain UI (tak diubah): [[plan_frontend_via_claude_design]] + `CLAUDE_DESIGN_BRIEF.md` + `design-source/`. Doc ini = **lapisan wiring data** di atas UI yang sudah jadi.

---

## 0. Guardrail & prasyarat (WAJIB sebelum wiring)
- ⛔ **RLS-first:** FE pakai **anon/publishable key + Supabase Auth** → semua query tenant-scoped via **`tenant_id = auth.uid()`** (RLS). **JANGAN** pakai service_role di FE (itu hanya worker/webhook backend). [[decisions_auth_rbac]].
- ✅ **Prasyarat terpenuhi:** clone DB v2 ✅, RLS go-live ✅ (Phase 4.3, anon=0 tanpa auth), env v2 siap. Guardrail "jangan wiring sebelum clone" → **terbuka**.
- **Env FE:** `apps/web/.env.local` → `NEXT_PUBLIC_SUPABASE_URL=https://atliatnjhysdibmfypul.supabase.co` + anon/publishable key (dari `SUPABASE-CONNECTION.md`, gitignored). **JANGAN commit.**
- ⚠️ **Next 16 breaking changes** (`apps/web/AGENTS.md`) — baca sebelum middleware/routing (next-intl). i18n rework saat wiring (next-intl span-ganda → proper).
- **Deploy:** Vercel (FE) + VPS (worker/webhook). FE tak pernah ke VPS.

## 1. Pendekatan teknis
- `@supabase/supabase-js` — 1 client util (browser, anon) + helper server-component (RSC) bila perlu.
- **Auth:** Supabase Auth (email+password, verify, reset) → session → `auth.uid()` = tenant scope.
- **Read:** query langsung (RLS) di Server Component / Client. **Write:** mutation + optimistic.
- **Realtime:** subscribe `pipeline_run_logs` (live-tail D5) + status run.
- **Pola:** ganti mock per-komponen (mock tetap fallback saat data kosong → SSR-safe deterministik).
- **Payment:** Snap.js (client key) → redirect; status via webhook backend (sudah ada). Billing baca `payments`/`tenant_configs`.

## 1.5 — ALUR BUSINESS-PROCESS per AREA (peta KELENGKAPAN)
> **View komplementer** dgn §2 (urutan eksekusi). §1.5 = jaminan **tiap area lengkap & koheren** sbg workflow (FE = realisasi alur bisnis; sumber: `DESAIN §3 Customer Journey` + `§7 IA` + BRIEF). §2 = **urutan build** (leverage→beta) yang MENARIK dari peta ini. Status LIVE = `PROGRESS.md`.
>
> Legenda: **🔑 beta-prereq** = wajib ada untuk jalankan beta 10 tenant · ⏳ mock ported belum wired · ✅ wired+validated.

### AREA 1 — MARKETING / LANDING (`mesinviral.com`, PUBLIK, no-auth) — funnel akuisisi
Actor: calon tenant (visitor). Proses: **Discover → Evaluate → Learn → Convert(→signup)**. Hampir 100% read publik; tabel public-read (anon OK), **nol write**.

| Tahap | Layar | Sumber data | Beta-prereq | Status |
|---|---|---|---|---|
| Discover | A1 Landing | statis + `pricing_config` (harga preview) | — (beta = invite langsung) | ⏳ (harga literal→`{{pricing}}` belum di-wire) |
| Evaluate | A2 Pricing | `pricing_config` + `plan_limits` (harga+caps dinamis) | — | ⏳ |
| Learn | A3 Demo · A4 Docs · A5 Blog · A6 About/Contact/Status/Legal | statis | — | ⏳ |
| Convert | CTA → `/auth` | — (handoff ke Area 2) | — | ✅ (auth 9.1) |
| Error | A8 404/500 | — | — | ✅ |
**Wiring inti area ini = harga dinamis dari `pricing_config`** (sumber tunggal, dipakai juga billing+onboarding). Minim risiko. **Prioritas rendah utk beta**, naik utk **public launch (Phase 12)**.

### AREA 2 — TENANT PANEL (`app.mesinviral.com`, AUTH, RLS=`auth.uid()`) — lifecycle tenant
Actor: tenant (creator). Proses: **Aktivasi → Operasi harian → Konfigurasi → Akun/komersial**.

| Sub-alur | Layar | Tabel (RLS) | Write-policy diperlukan | Beta-prereq | Status |
|---|---|---|---|---|---|
| **2.1 Aktivasi/Onboarding** | B1-B4 Auth · C1 paket/trial · C2 connect YouTube · C3 BYOK keys · C4 niche+bahasa+voice · C5 jadwal | `auth.users` · `tenant_configs` · `channels` · **`tenant_credentials`** · katalog niche/lang/voice · `production_schedules` | tenant_configs UPDATE · channels INSERT/UPDATE · **`tenant_credentials` = service_role-only (Phase 4.1) → C2/C3 WAJIB lewat server-route, BUKAN anon** (⚠️ lihat nuansa lintas-area #1) | 🔑 **YA (inti)** | auth ✅ · onboarding ⏳ |
| **2.2 Operasi harian** | D1 Dashboard · D2/D3 Channels · D4/D5 Runs (live-tail) · D6 Analytics · D21 Insights · D20 Compliance | `videos` · `production_runs` · **`pipeline_run_logs`** (Realtime) · `channel_insights`(+`.compliance`) · `video_analytics` · `content_inventory` | (read-only; D3 settings = channels UPDATE ✅) | 🔑 dashboard+runs YA · analytics/insights/compliance = data terisi pasca-produksi | D2 ✅ · sisa ⏳ |
| **2.3 Konfigurasi** | D8-D19 Config · D7 Schedule | `tenant_configs` (+branded/preset/privacy/disclosure) · katalog `ai_providers`/`ai_models` · `production_schedules` | tenant_configs UPDATE · schedules INSERT/UPDATE | 🔑 sebagian (AI engines/API keys/voice/niche utk produksi) · sisanya tuning | ⏳ |
| **2.4 Akun/komersial** | D13 Billing · D14/B5 Settings | `payments` · `tenant_configs`(plan/status) · `pricing_config` · `auth.users` | (billing tulis via Snap+webhook; settings = auth API + tenant_configs UPDATE) | 🔑 billing YA (konversi trial→paid) | ⏳ |

### AREA 3 — ADMIN PANEL (`admin.mesinviral.com`, SUPER-ADMIN via `app_metadata`, bypass RLS) — operasi internal
Actor: staf MesinViral. Proses: **Kelola tenant → Kurasi katalog (supply) → Set komersial → Support → Monitor sistem**. **⚠️ Sebagian = PRASYARAT beta, BUKAN polish** (lihat insight bawah).

| Sub-alur | Layar | Tabel | Beta-prereq | Status |
|---|---|---|---|---|
| **3.1 Tenant-mgmt** | E1 Tenants (suspend/refund/detail) + **Trial-Leads** (`trial_expired`) | `tenant_configs` · `payments` | 🔑 **YA** (kelola 10 tenant + follow-up lead) | ⏳ |
| **3.2 Kurasi katalog** | E2 Catalog (E2.1 AI models · E2.2 Music · E2.3 Niche+is_base+release · E2.4 Voice · E2.5 Languages) | `ai_providers`/`ai_models` · `music_library` · `niches` · `content_languages` | 🔑 niche+is_base YA · AI provider-mgmt = gap §AI-CATALOG | ⏳ |
| **3.3 Komersial** | E5 Pricing (inline-edit) | `pricing_config` · `plan_limits` · `app_config` | 🔑 **YA** (sumber harga SELURUH sistem — landing+billing+onboarding) | ⏳ |
| **3.4 Support** | E4 Support (tiket/chat) | (tiket — tabel TBD) | — (beta = manual/email) | ⏳ |
| **3.5 System health** | E3 System (worker/queue/DB/error) | `pipeline_run_logs` · `production_runs` · `content_inventory` | berguna (monitor worker) | ⏳ |

### ⚠️ Nuansa LINTAS-AREA (wajib diputuskan saat wiring area terkait)
1. **`tenant_credentials` (OAuth+API keys) = RLS service_role-only** (Phase 4.1, sensitif). Onboarding C2/C3 **tak boleh tulis via anon client** → butuh **server-route/route-handler** (Next) yang enkripsi Fernet + tulis pakai service_role (atau RPC SECURITY DEFINER). **Keputusan arsitektur sebelum 9.3 onboarding.**
2. **Admin auth-gating BELUM ADA** — route `/admin/*` saat ini mock/terbuka. Butuh **gate super-admin** (cek `app_metadata.role` di middleware + akses data bypass-RLS lewat server/service_role). Beda jalur dari auth tenant. **Keputusan sebelum Area-3 wiring.**
3. **Write-policy per-tabel** (temuan 9.2): Phase 4.3 cuma SELECT → tiap tabel yang ditulis FE butuh policy INSERT/UPDATE `tenant_id=(auth.uid())::text` (onboarding, config, dst).
4. **Harga = `pricing_config`** (single source) menyentuh **3 area** (landing A2 + tenant billing D13 + admin E5) → wire helper baca pricing sekali, pakai bertiga.

### 🎯 INSIGHT (lensa proses bisnis mengubah prioritas)
Urutan "leverage" (§2) menaruh **semua Admin di Phase 10 (polish)** — itu **keliru** dilihat dari proses bisnis: **E1 tenant-mgmt + E5 pricing + E2.3 niche/is_base = PRASYARAT menjalankan beta** (set harga, kelola tenant, kurasi niche yang dikonsumsi onboarding). → **§2 9.3 di-perluas**: tarik admin-beta-prereq (E1/E5/E2.3 + Trial-Leads) ke jalur beta, sisanya (E2.1 provider-mgmt/E3/E4 + marketing + polish) tetap di Phase 10.

## 2. Sub-phase (urutan = leverage tertinggi → beta tercepat) — MENARIK dari peta §1.5

### 9.1 — FONDASI (unblock semua) 🔴 FIRST
- ✅ **DONE (2026-06-14):** deps `@supabase/supabase-js`+`@supabase/ssr` · `src/lib/supabase/{client,server,middleware}.ts` (anon+RLS, pola @supabase/ssr Next-16 async cookies) · `src/middleware.ts` (refresh session, **NON-BREAKING** belum hard-redirect) · `.env.local` v2 (anon/publishable, gitignored) + `.env.local.example`. **Validasi:** `npm run build` PASS · anon-key v2 konek (plan_limits public=4) · **RLS isolasi** (tenant_configs/videos=0 tanpa auth). Commit `f1a9b8f`/`252a704`.
- ✅ **Provisioning signup DONE (2026-06-15, fork A=DB trigger):** migr `0028` trigger `on_auth_user_created` (auth.users insert → `tenant_configs` row + trial mulai; durasi dari app_config). e2e penuh (create test-user → row trial/trial + gate can_produce/cap-1 + niche 3-base + no-custom → cleanup). Provisioning = idiomatic, RLS langsung valid.
- ✅ **Auth page wired DONE (2026-06-15):** `auth/page.tsx` 6 view → `supabase.auth.signUp`(emailRedirect→verified)/`signInWithPassword`(→/dashboard)/`resetPasswordForEmail`/`resend`/`signInWithOAuth`(google). Input controlled + busy/error state; demo-bypass dibuang. build PASS. (Pakai `window.location` redirect — hindari API Next-16-spesifik.)
  - ✅ **RUNTIME-VALIDATED (2026-06-15, anon key FE):** alur nyata via supabase-py anon: `sign_up`→**trigger provision `trial/trial`** ✓ · login pre-confirm→ditolak "Email not confirmed" ✓ (error-path) · login post-confirm→**session token** ✓ · cleanup (ryan-only) ✓. **Verdict: signup→provision→login 100% jalan.** `reset` call benar tapi kena **429 email-rate-limit Supabase** (env, BUKAN bug kode).
  - 🚩 **Go-live (gate owner):** konfig **Supabase Auth → custom SMTP `mail.lumite.biz.id`** → hilangkan rate-limit email default Supabase + email auth (confirm/reset) ber-brand. (SMTP sudah tersedia di `S3-CONNECTION.md`.)
- ✅ **SISA 9.1 DONE (2026-06-15) — RUNTIME-VALIDATED:**
  - (1) **`/auth/callback/route.ts`** (Next-16 route handler, baca docs dulu): `exchangeCodeForSession(code)` (PKCE email-verify + OAuth) + `verifyOtp(token_hash,type)` fallback + guard open-redirect (`next` wajib `/`-prefix) → set session cookie server-side. Email/reset/OAuth redirect di-retarget LEWAT callback (bukan langsung ke page).
  - (2) **Hard-redirect proteksi** di `lib/supabase/middleware.ts`: prefix `dashboard/channels/runs/analytics/insights/compliance/config/schedule/settings/billing/onboarding/admin` → no-session redirect `/auth?view=login&next=<path>`. Marketing + `/auth` + `/auth/callback` publik.
  - (3) **Reset-password lengkap** (gap desain ditutup, approved owner): view `reset` baru di `auth/page.tsx` (`updateUser({password})`) — reset link → callback(recovery) → form pw baru → /dashboard.
  - (4) **Login → onboarded-check**: honor `?next` (dari middleware) lalu fallback query `channels` count (RLS) → 0 ⇒ `/onboarding`, >0 ⇒ `/dashboard`.
  - **Validasi runtime (server `next start`):** publik 200 · protected 307→/auth?next · callback no-code/bad-code → error redirect (**bad-code balas error PKCE asli Supabase = exchange beneran jalan**) · onboarded-check: ryan(1 ch)→/dashboard, tenant baru(0 ch, trigger trial)→/onboarding · cleanup bersih. `npm run build` PASS.
  - ⏳ **Sisa kecil (gate owner):** Google OAuth baru aktif setelah provider dikonfig di Supabase dashboard. Happy-path cookie-session→200 di protected route butuh sesi browser (tercakup di 9.2 vertical-slice / test manual owner).
- **Gate:** RLS test — tenant A login hanya lihat data A; anon → 0 (fondasi + middleware-redirect terbukti). ✅

### 9.2 — VERTICAL SLICE (buktikan pola e2e) ✅ DONE (2026-06-15) — RUNTIME-VALIDATED
- **Layar = D2 Channels** (`apps/web/src/app/(app)/channels/page.tsx`) — mock diganti data v2 NYATA:
  - **READ** (RLS, anon): `from('channels').select()` + `tenant_configs.plan_type` + `plan_limits.max_channels` → kartu real (channel_name, niche/niche_pool→badge, is_active→status) + quota real (X dari max, plan). Stats views/CTR/subs/spark = placeholder `—` (belum ada sumber timeseries; video historis ryan `channel_id=null`) — JUJUR, bukan mock. Empty (0 channel) → IncompleteCard→/onboarding.
  - **WRITE** (RLS): toggle `is_active` (Jeda/Aktifkan) optimistic + persist + revert-on-error.
  - **REALTIME**: subscribe `channels` postgres_changes (tenant-scoped via RLS) → live re-sync.
- **migr `0029`** (applied v2): (a) `channels` → publication `supabase_realtime`; (b) **policy `channels_tenant_update`** (UPDATE, `tenant_id=(auth.uid())::text`) — Phase 4.3 cuma bikin SELECT → write FE ke-block tanpa ini.
- **Validasi runtime (anon key FE, temp authed user):** build PASS · **RLS read isolasi PASS** (lihat hanya channel sendiri, bukan ryan) · quota read PASS · **WRITE toggle PASS** · **cross-tenant write guard PASS** (tak bisa ubah channel ryan) · **REALTIME websocket receipt PASS** (event UPDATE diterima, RLS-scoped) · cleanup bersih.
- **🔑 POLA untuk fan-out (penting):** tabel tenant HANYA punya SELECT policy (Phase 4.3) → **tiap layar yang WRITE wajib tambah policy UPDATE/INSERT** `tenant_id=(auth.uid())::text` per-tabel (spt `channels_tenant_update`). Realtime per-tabel = tambah ke publication `supabase_realtime` + RLS men-scope event. Client component: `createClient()` browser + `useEffect` load + `.channel().on('postgres_changes').subscribe()` + cleanup `removeChannel`.
- ⏳ Browser-render visual (setelah login) = owner check (mekanik data-layer sudah tervalidasi penuh via supabase-py anon + RLS yang identik dgn FE).

### 9.3 — BETA-CRITICAL PATH (cukup utk beta 10 tenant) — Area 2 (tenant) + Area 3 admin-prereq
> Menarik dari §1.5: **Area 2.1 aktivasi + 2.2 operasi + 2.4 billing** + **Area 3 prasyarat-beta** (insight §1.5). Sisanya → 9.4/10.
- **[Area 2.1] C1-C5 Onboarding** (signup→**BYOK keys**→YouTube OAuth→niche+bahasa+voice→jadwal). **Trial wajib BYOK upfront** (hapus "skip keys"). Tulis `tenant_configs`/`channels`/`tenant_credentials`. ⚠️ **`tenant_credentials` lewat server-route** (nuansa lintas-area #1) + tambah write-policy per-tabel (#3).
- **[Area 2.2] D2/D3 Channels** (D2 ✅; D3 detail, RLS) · **D4/D5 Runs** (list + live-tail Realtime `pipeline_run_logs`) · **D1 Dashboard** (KPI real).
- **[Area 2.4] D13 Billing** (Snap checkout + `payments` history + plan/usage) · **B5 Settings** (profil/keamanan/integrasi).
- **[Area 3 — admin PRASYARAT beta] 🔑** (insight §1.5 — bukan polish): admin auth-gate (nuansa #2) + **E1 Tenants + Trial-Leads** (kelola 10 tenant) + **E5 Pricing** (sumber harga sistem) + **E2.3 Niche/is_base** (katalog yang dikonsumsi onboarding C4).

### 9.4 — CONFIG & ANALYTICS — Area 2.3 (konfigurasi) + sisa Area 2.2 (analytics)
- **Config D8-D19** (`/config/*` write ke `tenant_configs`: AI engines/voice/visual/music/captions/quality/hashtags/niches/notif + **format/preset picker + Branded panel + privacy toggle + AI-disclosure toggle** = FE gap dari Multi-Format/6.3).
- **🎯 Niche access model (backend siap, FE gating P9-10):** niche-picker filter by tier via `limits.available_niches(plan_type)` — **trial/starter → niche dasar (`is_base`) saja · pro/business → semua aktif**. **Pengajuan CUSTOM niche** (add-on: public-90d/private — [[decisions_niche_model]]) via `limits.can_request_custom_niche` → **starter/pro/business YA, trial TIDAK**. Admin set `niches.is_base` (migr 0026) + harga add-on `pricing_config`. **⚠️ Sistem custom-niche PENUH** (schema `niches.access_type`/`exclusive_*` BELUM ada di v2 + request-flow D18 + admin E2.3 + add-on payment) = fitur tersendiri per `decisions_niche_model` (build di fase niches).
- **D6 Analytics** + **D20 Compliance** (baca `channel_insights.compliance`) + **D21 Insights** (`channel_insights`).

### 10 — SISA ADMIN + MARKETING + POLISH — sisa Area 3 + Area 1 + infra
> Admin **prasyarat-beta** (E1/E5/E2.3/Trial-Leads) sudah ditarik ke 9.3. Di sini = SISANYA.
- **[sisa Area 3] Admin**: E2.1 Catalog AI provider-mgmt (ai_providers/models CRUD = gap §AI-CATALOG) · E2.2 Music · E2.4 Voice · E2.5 Languages · **E3 System health** · **E4 Support**.
- **[Area 1] A1-A8 Marketing** (sebagian besar statis; **harga dari `pricing_config`** = nuansa lintas-area #4) — naik prioritas saat **public launch (Phase 12)**.
- **Polish**: next-intl rework · PWA · responsive harmonisasi.

## 3. Peta layar → sumber data (RLS) — turunan matriks keselarasan PROGRESS
| Layar | Tabel (RLS `auth.uid()`) | R/W |
|---|---|---|
| Auth B1-4 | `auth.users` (Supabase Auth) | — |
| Onboarding C1-5 | `tenant_configs`, `channels`, `tenant_credentials`, katalog (niche/lang/voice) | W |
| Dashboard D1 | `videos`, `production_runs`, `channel_insights`, `content_inventory` | R |
| Channels D2/3 | `channels`, `videos`, `video_analytics` | R/W (settings) |
| Runs D4/5 | `production_runs`, **`pipeline_run_logs`** (Realtime live-tail) | R |
| Analytics D6 | `video_analytics`, `channel_insights` | R |
| Compliance D20 | `channel_insights.compliance` (Phase 7) | R |
| Insights D21 | `channel_insights` | R |
| Config D8-19 | `tenant_configs` (+ branded/preset/privacy/disclosure), katalog `ai_providers/ai_models` | R/W |
| Billing D13 | `payments`, `tenant_configs` (plan/status), `pricing_config` | R + Snap |
| Admin E1-5 | semua (super-admin via app_metadata, bypass RLS) | R/W |

## 4. Risiko & mitigasi
- **Next 16 breaking** → baca AGENTS.md + node_modules docs sebelum middleware. 
- **RLS pitfall** (lupa policy / salah scope) → test isolasi per-screen (tenant A vs B vs anon).
- **next-intl rework** (pola span-ganda mock → proper) → saat wiring, sekali.
- **YouTube OAuth FE↔backend** (onboarding C2) → flow OAuth + simpan ke `tenant_credentials` (Fernet, backend).
- **Snap client** (popup/redirect) + finish/error redirect → halaman billing.

## 5. Validasi (tiap sub-phase)
`npm run build` PASS · curl/route 200 · **RLS isolasi** (tenant A≠B, anon=0) · write→DB terverifikasi · Realtime live-tail muncul <5s. (FE belum bisa di-test owner manual sampai sebagian ter-wire — beban validasi di dev.)

## 6. Gate owner (operasional)
- Env FE (anon key) di Vercel · domain `app.mesinviral.com`/`admin.` · **cutover** (deploy worker+webhook ke VPS) saat beta-path siap · Midtrans prod key (go-live).

---
### Changelog
- 2026-06-14 — dibuat (rencana breakdown Phase 9-10 wiring). Menunggu review/approval owner sebelum eksekusi 9.1.
- 2026-06-15 — auth page **runtime-validated** (signup→provision→login OK; reset kena rate-limit env). Catat go-live: Supabase Auth custom SMTP → lumite.
- 2026-06-15 — **SISA 9.1 selesai + runtime-validated**: `/auth/callback` route, middleware hard-redirect, view `reset` (updateUser), login onboarded-check. 9.1 = TUNTAS (kecuali gate owner: OAuth provider config).
- 2026-06-15 — **9.2 VERTICAL SLICE DONE + runtime-validated**: D2 Channels wired (read+write+realtime, RLS) + migr 0029 (realtime publication + channels UPDATE policy). Pola stack de-risked untuk fan-out. Next = 9.3 beta-path.
- 2026-06-15 — **+§1.5 Peta Alur Business-Process per Area** (Marketing/Tenant/Admin) — actor→tahap→layar→tabel/RLS→write-policy→beta-prereq→status; +nuansa lintas-area (tenant_credentials server-route, admin auth-gate, write-policy per-tabel, pricing single-source); insight: admin E1/E5/E2.3+Trial-Leads = PRASYARAT beta → ditarik ke §2 9.3. §2 di-tag per area. (owner: plan harus refleksikan alur bisnis tiap area.)
