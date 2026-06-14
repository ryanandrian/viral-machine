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

## 2. Sub-phase (urutan = leverage tertinggi → beta tercepat)

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

### 9.2 — VERTICAL SLICE (buktikan pola e2e) 🔴
- 1 layar authed baca data v2 NYATA: **D1 Dashboard** atau **D2 Channels** (read) + 1 write (mis. toggle config) + 1 Realtime (D5 live-tail).
- Tujuan: de-risk stack (client+RLS+read+write+realtime) sebelum fan-out.

### 9.3 — BETA-CRITICAL PATH (cukup utk beta 10 tenant)
- **C1-C5 Onboarding** (signup→**BYOK keys**→YouTube OAuth→niche+bahasa+voice→jadwal). **Trial wajib BYOK upfront** (hapus "skip keys"). Tulis `tenant_configs`/`channels`/`tenant_credentials`.
- **D2/D3 Channels** (list+detail, RLS) · **D4/D5 Runs** (list + live-tail Realtime `pipeline_run_logs`).
- **D1 Dashboard** (KPI real) · **D13 Billing** (Snap checkout + `payments` history + plan/usage).
- **B5 Settings** (profil/keamanan/integrasi).

### 9.4 — CONFIG & ANALYTICS
- **Config D8-D19** (`/config/*` write ke `tenant_configs`: AI engines/voice/visual/music/captions/quality/hashtags/niches/notif + **format/preset picker + Branded panel + privacy toggle + AI-disclosure toggle** = FE gap dari Multi-Format/6.3).
- **🎯 Niche access model (backend siap, FE gating P9-10):** niche-picker filter by tier via `limits.available_niches(plan_type)` — **trial/starter → niche dasar (`is_base`) saja · pro/business → semua aktif**. **Pengajuan CUSTOM niche** (add-on: public-90d/private — [[decisions_niche_model]]) via `limits.can_request_custom_niche` → **starter/pro/business YA, trial TIDAK**. Admin set `niches.is_base` (migr 0026) + harga add-on `pricing_config`. **⚠️ Sistem custom-niche PENUH** (schema `niches.access_type`/`exclusive_*` BELUM ada di v2 + request-flow D18 + admin E2.3 + add-on payment) = fitur tersendiri per `decisions_niche_model` (build di fase niches).
- **D6 Analytics** + **D20 Compliance** (baca `channel_insights.compliance`) + **D21 Insights** (`channel_insights`).

### 10 — ADMIN & POLISH
- **Admin E1-E5** (`/admin/*`): Tenants + **Trial-Leads** (status `trial_expired` → kontak+usage) · Catalog (ai_providers/models CRUD = gap §AI-CATALOG) · Pricing E5 (`pricing_config`/`plan_limits`/`app_config`) · System health · Support.
- **A1-A8 Marketing** (sebagian besar statis; pricing dari `pricing_config`).
- next-intl rework · PWA · responsive harmonisasi.

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
