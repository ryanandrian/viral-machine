# PHASE 10 — ADMIN AREA WIRING + SUBSYSTEMS (epic)

> **Status:** 📋 PLAN (menunggu GO owner) · 2026-06-15 · Branch `v2-backend`.
> **Pemicu:** owner pilih **"wiring SELURUH admin + bangun subsistem yang belum ada"** (bukan beta-prereq saja).
> **Prasyarat penguasaan (sudah dibaca penuh sesi ini):** `DB_SCHEMA_V2.md` (introspeksi 27 tabel) · `DESAIN_PRODUK_SAAS.md` · `MESIN_VIRAL.md` · `MULTI_FORMAT_STUDIO.md` · `PROGRESS.md`. Status LIVE = `PROGRESS.md`; alur FE = `PHASE9_FRONTEND_WIRING.md §1.5`.
> **Aturan tetap:** nol asumsi (verifikasi DB+kode) · config-driven (no-hardcode) · runtime-validate tiap layar sebelum klaim · v1 VPS jangan disentuh.

---

## 0. POLA DATA ADMIN (beda dari layar tenant — fondasi)

Layar tenant = anon key + RLS (`tenant_id=auth.uid()`). **Admin BACA/TULIS data LINTAS-tenant** → RLS (scope `auth.uid()`) justru memblokir admin. Tak ada policy bypass super-admin di DB (verified `DB_SCHEMA_V2`). Maka:

- **`lib/supabase/admin.ts`** — client **service_role** (server-only; `SUPABASE_SERVICE_ROLE_KEY` di `apps/web/.env.local`, TANPA `NEXT_PUBLIC_` → tak pernah ke browser). Bypass RLS.
- **Route-handler `/api/admin/*`** — tiap endpoint: (1) verifikasi caller super-admin (server client baca cookie → `getUser` → `app_metadata.role==='super_admin'`); (2) baru pakai service_role. Client admin (sudah ber-gate route-group `admin/(panel)/`) memanggil endpoint ini (fetch). **service_role tak pernah di komponen client.**
- **Audit:** aksi admin sensitif (impersonate, suspend, refund/credit, edit pricing, transition niche) tulis ke **`admin_audit`** (siapa, aksi, target, kapan, detail).

Gate sudah ada (sesi sebelumnya): middleware + `admin/(panel)/layout.tsx` cek `app_metadata.role`. Akun super-admin = `mesinviral@lumite.biz.id`.

---

## 1. FONDASI + ADMIN CHANGE-PASSWORD (10.0)

- `lib/supabase/admin.ts` (service_role factory, server-only) + helper `assertSuperAdmin()` (server) untuk semua route-handler.
- `apps/web/.env.local` += `SUPABASE_SERVICE_ROLE_KEY` (gitignored; nilai dari `SUPABASE-CONNECTION.md`).
- **Admin change-password:** halaman akun admin di shell (`/admin/account`) — `supabase.auth.updateUser({password})` (sesi admin sendiri, client-side, TANPA service_role — pola identik B5 tenant). Nav item + Logout sudah ada. **(menutup gap yang owner sebut.)**
- migr `admin_audit` (table baru, lihat §3).

---

## 2. PER-LAYAR — WIRE (data ada) vs BUILD (subsistem)

| # | Layar | WIRE | BUILD |
|---|---|---|---|
| 10.1 | **E1 Tenants + Trial-Leads** | list/detail `tenant_configs`+`payments`+`production_runs`/`channels` per-tenant; MRR=derive `pricing_config[plan_<tier>]`×aktif; **suspend** (`subscription_status`); leads (`subscription_status='trial_expired'`); KPI (total/MRR/trials/churn dari data nyata); ryan=comp gratis tetap | **kirim email** = antre `email_outbox` → worker kirim. ❌ **add-credit DIBUANG** (BYOK, tak ada kredit — owner) · ❌ **impersonate DIBUANG** (admin tak boleh masuk panel tenant; pakai akun tenant khusus — owner) |
| 10.2 | **E5 Pricing** | inline-edit `pricing_config` (value_idr/usd/active/desc/category) via RPC/route; schedule (`effective_from/until` ADA); `plan_limits`+`app_config` editor | **`pricing_audit`** (riwayat + rollback nyata; `updated_by/at` ada tapi tanpa history) |
| 10.3 | **E2.3 Niches** | identity/voice/visual/musik/keywords/hashtags/`is_active`/`is_base` (niches) | **kolom eksklusivitas** (`access_type`/`exclusive_to`/`exclusive_until`/`released_at`) + **`niche_releases`** (monthly-release scheduler). **Tag-pool = TIDAK (epik pipeline terpisah — §4).** |
| 10.4 | **E2.1 AI Models + Providers** | `ai_models` CRUD/toggle + **`ai_providers` CRUD** (gap §AI-CATALOG di PROGRESS: adapter/base_url/auth/`request_param_schema`) | — |
| 10.5 | **E2.2 Music** | `music_library` list/toggle/edit | **bulk-upload** (route → R2/S3 storage + insert row) |
| 10.6 | **E2.4 Voice** | `tts_profiles` (provider-class) + voice-per-niche (`niches.voice_profile`/`tenant_configs.tts_voice_per_niche`) | **`voice_catalog`** (voice ElevenLabs/edge per nama+lang+niche-default — mock "voice templates" tak punya tabel) |
| 10.7 | **E2.5 Languages** | `content_languages` list/toggle/add/edit | (+kolom kosmetik bila perlu: flag/script — derive dulu) |
| 10.8 | **E3 System Health** | queue-depth (timeseries `pipeline_queue.created_at`/status) + error-rate & failure-by-type (`production_runs.status`/`error_message`) | **`worker_heartbeats`** (+hook tulis di `worker_decoupled.py`) + RPC DB-stats (opsional) |
| 10.9 | **E4 Support** | — | **`support_tickets`+`support_messages`** + RLS tenant-own + **UI buat-tiket sisi tenant** (sumber tiket) + admin inbox/balas/resolve/tag |

---

## 3. SUBSISTEM BARU — desain schema (ikut konvensi DB_SCHEMA_V2)

> Konvensi dipatuhi: `tenant_id` TEXT = `auth.uid()::text`; PK uuid `gen_random_uuid()` utk tabel transaksional; RLS tenant = SELECT `tenant_id=(auth.uid())::text` (+INSERT WITH CHECK utk yg tenant tulis); admin tulis via service_role. Tak ada FK ke `auth.users` (Supabase-managed; pola existing pakai tenant_id text).

- **`admin_audit`** (uuid id, admin_uid text, action text, target_tenant text, detail jsonb, created_at) — RLS: tak ada policy (service_role only). ✅ migr 0034.
- ~~`tenant_credits`~~ **DIBUANG** (owner: BYOK, tak ada konsep kredit; tenant bayar per tier + upgrade).
- **`email_outbox`** (uuid id, tenant_id text, subject text, body text, status text default 'pending' [pending/sent/failed], created_by text, created_at, sent_at, error text) — service_role only. Admin enqueue via route; **worker Python proses** (resolve email via Auth admin API `email.py:tenant_email` → `send_email` → mark sent/failed, fail-soft).
- **`pricing_audit`** (uuid id, key text, old jsonb, new jsonb, changed_by text, changed_at) — service_role only. Rollback = tulis balik old.
- **niches +kolom:** `access_type` text default `'public'` (CHECK public/pending/private), `exclusive_to` text null, `exclusive_until` timestamptz null, `released_at` timestamptz null, `release_scheduled_at` timestamptz null. **`niche_releases`** (uuid id, niche_id varchar FK niches, scheduled_at, announced bool, status text). (RLS niches saat ini OFF — admin via service_role; public-read onboarding tetap.)
- **`voice_catalog`** (text voice_key PK, provider_key text, display_name, locale text, gender text, niche_default text null, preview_url text, is_active bool, sort_order int).
- **`worker_heartbeats`** (text worker_name PK, status text, current_job text null, node text null, last_heartbeat_at timestamptz) — service_role only; `worker_decoupled.py` upsert tiap loop.
- **`support_tickets`** (uuid id, tenant_id text, subject text, status text default 'open' CHECK open/pending/resolved, priority text, assigned_to text null, created_at, updated_at) + **`support_messages`** (uuid id, ticket_id uuid FK, sender text CHECK 'tenant'/'admin', body text, created_at). RLS: tenant SELECT/INSERT own ticket+message; admin service_role. Realtime: tambah `support_messages` ke publication (live chat).

---

## 4. KEPUTUSAN FORK (expert, berbasis dokumen — bukan asumsi)

- **Tag-pool niche → DITUNDA sbg epik terpisah.** `MULTI_FORMAT_STUDIO §0` + `PROGRESS` (Phase 6.4) mengunci: tag-pool = Layer-2 (`videos.topic_tags` + assignment **di pipeline produksi**) = "fase berat C", mengubah mesin konten yang sudah jalan → risiko. Layar niche tetap fungsional penuh tanpa tab tag (eksklusivitas+release dibangun).
- **Impersonate → DIBUANG** (owner 2026-06-15): admin = jalur+akun terpisah; admin TAK boleh masuk panel tenant. Mau rasakan sisi tenant → pakai **akun tenant khusus** (bukan akun admin). **+Perkuat pemisahan:** middleware blokir super-admin dari route tenant (`/dashboard` dll) → redirect `/admin`. (ryan = comp gratis selamanya, tetap.)
- **Add-credit → DIBUANG** (owner): BYOK, tenant bayar per tier; tak ada kredit. Diskusi terpisah bila perlu.
- **Kirim email → antre `email_outbox` → worker** (owner pilih platform-queue, bukan mailto).
- **Worker heartbeat → DIBANGUN** (`worker_heartbeats` + hook worker v2). Additif, aman (worker belum di VPS).
- **Support → PENUH** (tenant create + admin manage).

---

## 5. URUTAN EKSEKUSI (tiap sub-phase: build → runtime-validate → docs → commit)

10.0 Fondasi (admin client + route pattern + change-password + admin_audit) → 10.1 E1 Tenants+Leads (suspend/email/credit/impersonate) → 10.2 E5 Pricing (+audit) → 10.3 E2.3 Niches (+eksklusivitas/release) → 10.4 E2.1 AI Models+Providers → 10.7 E2.5 Languages → 10.6 E2.4 Voice → 10.5 E2.2 Music (+upload) → 10.8 E3 System Health (+heartbeat) → 10.9 E4 Support (full).

Urutan: leverage (E1/E5/niche dulu = beta-prereq), lalu katalog ringan, lalu yang sentuh storage/worker/subsistem besar (music-upload, heartbeat, support).

## 6. VALIDASI (disiplin terbukti)

Tiap layar: route-handler super-admin gate (curl: non-admin→403, admin→200) · service_role read/write lintas-tenant benar · cross-check RLS tenant tak bocor · build PASS · update PROGRESS+PHASE10+journal. Migrasi via psycopg2 pooler (lanjut 0034+).
