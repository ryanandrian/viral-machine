# 💳🔐 PAYMENT & TENANT GATE ARCHITECTURE — MesinViral

> **🔒 CLOSED — SPEC FINAL (2026-07-02).** Arsitektur payment + gate tenant (s/d `suspended`) **SELESAI + deployed `04cf0a2` + tervalidasi server-side** (build/DB/endpoint/customer_details sandbox). Dokumen ini **BEKU sebagai referensi** — **status hidup & sisa aksi = `SISA_KERJA_GO_LIVE.md`** (HUB): [A1] flip produksi + last-mile 1 bayar sandbox = **aksi owner, BUKAN celah doc**. Lanjutan pasca-`suspended` (nurture/dunning/blokir/hapus-data) = `LIFECYCLE_NURTURE_ARCHITECTURE.md`. Jangan pakai isi doc ini sbg daftar kerja.

> **Sumber kebenaran TUNGGAL** untuk arsitektur *gate tenant* (siklus akun trial→berbayar) + *pembayaran Midtrans*.
> Dibuat 2026-07-01 setelah implementasi + validasi e2e (sandbox & live). Baca ini sebelum menyentuh apa pun
> yang berkaitan dengan billing/pembayaran/status langganan. **Prinsip: NO-HARDCODE** (semua angka di `app_config`,
> admin-editable via **System Configuration** `/admin/app-config`) + **world-class** + **dwibahasa EN/ID**.
>
> **🔗 Rantai kanonik:** backlog/status = **`SISA_KERJA_GO_LIVE.md`** (HUB — item [A1] Midtrans prod · [E1] add-on · [B8] /feedback · [B9] siklus-hidup). Dokumen ini meng-cover gate **s/d `suspended`**; **LANJUTAN** (`suspended→blocked→deleted` + nurture + hapus-data) = **`LIFECYCLE_NURTURE_ARCHITECTURE.md`**.

---

## 0. Ringkasan 1 paragraf
Setiap tenant punya **status langganan** (`tenant_configs.subscription_status`) yang menentukan apakah mesin boleh
berproduksi. Alur: **trial → trial_expired → active → grace → suspended** (+ `comp` gratis-selamanya). Tenant membayar
via **Midtrans Snap (redirect)** untuk **langganan bulanan** dan **add-on custom-niche**. Akun Midtrans **DIBAGI** dengan
aplikasi lain (aiwa), jadi notifikasi dititipkan **per-transaksi** (`X-Override-Notification`). Pembayaran dipastikan
oleh **DUA mekanisme**: **webhook (push)** + **reconciler (pull, tarik status API Midtrans)** — keduanya memanggil
**satu fungsi settlement** (`_apply_settlement`). Semua timing (durasi trial, grace, kapan reminder, masa berlaku
link bayar) = **config di `app_config`**, bisa diubah admin tanpa sentuh kode.

---

## 1. TENANT GATE — state machine langganan

```
  (daftar)                                (bayar)
     │                                       │
     ▼                                       ▼
  ┌────────┐  periode lewat   ┌───────────────┐   bayar    ┌────────┐
  │ trial  │ ───────────────▶ │ trial_expired │ ─────────▶ │ active │◀──────┐
  └────────┘   (H-x reminder) │  ("Leads")    │            └────────┘       │ bayar
     │  bayar (upgrade dini)   └───────────────┘               │ periode    │ (perpanjang)
     └────────────────────────────────────────────────────────┤ lewat      │
                                                                ▼            │
                                                            ┌────────┐  grace lewat  ┌───────────┐
                                                            │ grace  │ ────────────▶ │ suspended │─┘
                                                            └────────┘  (dunning)    └───────────┘
  comp / developer (is_developer=true ATAU discount_pct>=100) = EXEMPT → gratis selamanya, tak pernah disentuh sweep.
```

| Status | Bisa produksi? | Bisa login? | Arti | Notifikasi saat masuk status |
|---|---|---|---|---|
| `trial` | ✅ (`PRODUCING_STATUSES`) | ✅ | Masa coba (durasi `trial_duration_days`) | H-`trial_reminder_days_before`: **reminder upgrade + minta masukan** |
| `trial_expired` | ❌ | ✅ (agar bisa upgrade) | Trial habis, jadi **"Leads"** (calon pelanggan) | email **lapse** (upgrade + feedback) |
| `active` | ✅ | ✅ | Berlangganan (periode 30 hari) | struk bayar; H-`renewal_reminder_days_before`: **reminder perpanjang** |
| `grace` | ✅ (masih jalan) | ✅ | Periode lewat, masa tenggang `billing_grace_days` (dunning) | email **peringatan** (akan stop) |
| `suspended` | ❌ | ✅ | Tenggang lewat → produksi **DIHENTIKAN** | email **suspend** (aktifkan lagi) |
| `comp` (bukan status, tapi flag) | ✅ | ✅ | is_developer / discount≥100 → gratis | — (exempt) |

**Prinsip kunci:** login SELALU boleh (agar tenant lapsed bisa upgrade); yang di-gate = **PRODUKSI**
(`src/billing/limits.py::can_produce`, `PRODUCING_STATUSES = {active, trial, grace}`).

> **⛳ Batas dokumen ini:** state machine di sini berhenti di **`suspended`**. Lanjutan `suspended → blocked → deleted`
> (dunning 30h → kunci akun 30h + peringatan H-30/7/1 → hapus data + cabut token YouTube) + mesin **nurture** trial-lapse
> = **`LIFECYCLE_NURTURE_ARCHITECTURE.md`** (backlog [B9]). Keduanya **satu mesin** (`renewal.py`), non-redundan.

**Mesin state:** `src/billing/renewal.py` — thread `billing_renewal` di worker, cadence `BILLING_CHECK_INTERVAL_SEC`
(default 86400s/harian). Tiap sweep: (1) kirim reminder pra-habis (anti-dobel via penanda), (2) transisi status + notif.
Reaktivasi (grace/suspended/trial_expired → active) = HANYA lewat pembayaran (webhook/reconciler), bukan sweep.

---

## 2. KONFIGURASI (NO-HARDCODE) — semua di `app_config`, admin-editable

Diedit di **`/admin/app-config`** (System Configuration; editor generik — key baru dgn `description` otomatis muncul).

| key | default | arti |
|---|---|---|
| `trial_duration_days` | 3 | lama trial (hari) |
| `billing_grace_days` | 7 | masa tenggang setelah periode habis sebelum produksi dihentikan |
| `trial_reminder_days_before` | 1 | H-x kirim reminder sebelum trial habis (0 = matikan) |
| `renewal_reminder_days_before` | 3 | H-x kirim reminder sebelum langganan habis (0 = matikan) |
| `checkout_expiry_hours` | 24 | masa berlaku link bayar Midtrans |

Migrasi: `0109_billing_lifecycle_config.sql` (knob + kolom penanda), `0024/0028` (trial). **Harga** = `pricing_config`
(`plan_starter/pro/business`, `custom_niche_public_90d`, `custom_niche_private`) — juga admin-editable (`/admin/pricing`).

Penanda anti-dobel di `tenant_configs`: `trial_reminder_sent_at`, `renewal_reminder_sent_at`, `suspend_notified_at`
(di-RESET saat pembayaran mengaktifkan siklus baru → reminder segar bulan berikutnya).

---

## 3. PAYMENT — arsitektur Midtrans

### 3.1 Akun BERBAGI + override notifikasi (KRITIS)
Satu merchant Midtrans (`G523181402`) dipakai **MesinViral + aiwa** (domain berbeda). Karena itu:
- **JANGAN ubah Notification URL global di dashboard Midtrans** (itu milik aiwa).
- MesinViral menitipkan URL webhook **per-transaksi** via header **`X-Override-Notification`** =
  `{APP_BASE_URL}/api/webhooks/midtrans` (kode: `src/billing/midtrans.py::_snap_post`).
- Order ID ber-awalan **`MV-`** (langganan `MV-{plan}-…`, add-on `MV-niche-…`); aiwa pakai `AIWA` → **tak tabrakan**.
- ⚠️ Header override HANYA bekerja bila `APP_BASE_URL` benar (`https://mesinviral.com`). Di `.env` lokal
  `APP_BASE_URL=http://localhost:3000` → transaksi dibuat dari lokal TAK dapat notifikasi (wajar; produksi = VPS).

### 3.2 Switch Sandbox ↔ Production (NO-HARDCODE, nol perubahan kode)
`.env` menyimpan **KEDUA set kunci** permanen; switch = **ubah `MIDTRANS_ENV` SAJA** (`sandbox`|`production`):
```
MIDTRANS_ENV=production            # ← 1 saklar
MIDTRANS_MERCHANT_ID=G523181402
MIDTRANS_SANDBOX_SERVER_KEY=SB-Mid-server-…      MIDTRANS_SANDBOX_CLIENT_KEY=SB-Mid-client-…
MIDTRANS_PRODUCTION_SERVER_KEY=Mid-server-…      MIDTRANS_PRODUCTION_CLIENT_KEY=Mid-client-…
```
Kode (`_is_production` → `_server_key`/`_snap_base`/`_status_base`) otomatis pilih kunci + URL (`app.midtrans.com` vs
`app.sandbox.midtrans.com`, `api.midtrans.com` vs `api.sandbox.midtrans.com`) sesuai `MIDTRANS_ENV`. Client key TAK
dipakai (mode redirect, bukan Snap.js). **Tak ada perubahan di dashboard Midtrans saat switch** (pakai override).

### 3.3 Alur checkout (buat transaksi)
| Jenis | Pintu FE | Route FE (session) | Route internal (mv-webhook) | Fungsi BE |
|---|---|---|---|---|
| **Langganan** | Billing → "Ubah paket" (drawer) | `POST /api/billing/checkout` | `POST /api/billing/checkout` | `snap_create_transaction` |
| **Add-on custom-niche** | Pustaka Niche → "Bayar" (status `awaiting_payment`) | `POST /api/niche-requests/[id]/pay` | `POST /api/billing/niche-checkout` | `snap_create_niche_addon` |

Alur: FE (mv-web, verifikasi sesi Supabase) → panggil mv-webhook (`vault()`, header `X-Internal-Secret`) → BE buat
order `payments` (status `pending`, `category` subscription|addon, `ref_id` = request_id utk add-on) + Snap token →
kembalikan `redirect_url` → FE redirect user ke halaman bayar Midtrans. `payments` = ledger (migr 0022 + 0108).

### 3.4 Settlement — DUA jalur, SATU logika (anti-redundan)
- **Webhook (PUSH, cepat):** Midtrans POST → nginx `location /api/webhooks/midtrans` → mv-webhook `:8088`
  (`src/billing/webhook_app.py`) → `handle_notification` → verifikasi **signature SHA512** → `_apply_settlement`.
- **Reconciler (PULL, PENJAMIN):** thread `payment_reconciler` (worker, cadence `PAYMENT_RECONCILE_INTERVAL_SEC`=120s)
  → tiap `payments` `pending` (usia < 48j) → `get_transaction_status` (API Midtrans, terautentikasi = tepercaya) →
  `_apply_settlement`. **Tak tergantung delivery notifikasi** → aman untuk akun berbagi.
- **`_apply_settlement` (satu sumber):** settlement/capture + fraud accept →
  - **addon** → RPC `settle_niche_request_paid` (buat niche `is_active=false` + status `in_progress` + email). Idempotent.
  - **subscription** → `subscription_status=active` + `plan_type` + `current_period_end=+30hr` + reset penanda reminder + email struk.
  - `expire`/`cancel`/`deny` → tandai status (reconciler).

> ⚠️ **nginx WAJIB** punya `location /api/webhooks/midtrans { proxy_pass 127.0.0.1:8088; }` (di
> `/etc/nginx/sites-enabled/mesinviral`) — kalau tidak, notifikasi Midtrans → 404 (mv-web) → pembayaran tak ter-catat.

### 3.5 Custom-niche settlement RPC (SATU sumber)
`settle_niche_request_paid(p_request_id, p_order_id)` (migr 0108, SECURITY DEFINER, service_role) — dipakai oleh
webhook/reconciler (bayar Midtrans, otomatis) **DAN** admin "Tandai lunas" (concierge offline, `/api/admin/niche-requests`).
Atomik: buat baris `niches` (auto-slug, `is_active=false`, `exclusive_to`=tenant, 90hr utk public) + set
`niche_requests` (`in_progress`, `niche_id`, `paid_at`, `order_id`) + antre email. Idempotent (retry aman).

---

## 4. NOTIFIKASI (email lifecycle) — `src/utils/email.py`
Dikirim worker via SMTP lumite. **DWIBAHASA (EN + ID dalam satu email)**, durasi/angka dari `app_config` (no-hardcode).
Reset password & konfirmasi = dikirim mv-web sendiri (branded, token_hash lintas-alat; `apps/web/src/lib/email/`).

| Fungsi | Kapan | Isi |
|---|---|---|
| `notify_trial_ending` | H-x sebelum trial habis | ajak upgrade + link feedback |
| `notify_trial_lapse` | trial → trial_expired | upgrade + feedback |
| `notify_renewal_reminder` | H-x sebelum langganan habis | ajak perpanjang |
| `notify_suspend_warning` | → grace | dunning (akan stop dlm ~grace hari) |
| `notify_suspended` | → suspended | produksi stop, aktifkan lagi |
| `notify_payment_receipt` | settlement langganan | struk |

Link upgrade = `UPGRADE_URL` (default `/billing`); link feedback = `TRIAL_SURVEY_URL` (default `/feedback`).

---

## 5. FRONTEND
**Tenant:**
- **Banner in-app** (`components/app-shell.tsx`) — status + sisa hari + tombol Upgrade (muncul saat trial/trial_expired/
  grace/suspended; comp exempt). **Pintu upgrade selalu terlihat.**
- **Routing status-aware** (`auth/page.tsx doLogin` + `auth/callback/route.ts`) — non-produksi (trial_expired/suspended)
  → `/billing` (BUKAN terjebak `/onboarding`).
- **Billing** (`(app)/billing/page.tsx`) — paket/status (label jelas + sisa hari)/pemakaian + riwayat invoice (`payments`,
  RLS) + drawer 2-mode "Ubah paket" (Starter/Pro/Business) & katalog add-on (→ Pustaka Niche).
- **/feedback** (`app/feedback/page.tsx`, PUBLIK, bilingual) — alasan churn terstruktur + saran → `POST /api/feedback`.

**Admin:**
- **Pembayaran** (`/admin/billing`) — ledger transaksi `payments` (read-only; refund via dashboard Midtrans).
- **Masukan** (`/admin/feedback`) — daftar `feedback_submissions`.
- **Tenant** (`/admin/tenants`) — status langganan per tenant (trial_expired = "Leads").
- **System Configuration** (`/admin/app-config`) — semua knob billing (§2).
- Pembayaran langganan tenant = di menu Tenant (status); ledger = menu Pembayaran (anti-redundan).

---

## 6. PETA FILE (rujukan cepat)
```
DB     migrations/0022 (payments) · 0108 (payments.category/ref_id + RPC settle) · 0109 (knob+penanda) · 0110 (feedback)
BE     src/billing/midtrans.py     — snap_create_transaction / snap_create_niche_addon / _snap_post (override+expiry)
                                     handle_notification / _apply_settlement / get_transaction_status / reconcile_pending
       src/billing/renewal.py      — sweep_subscriptions (reminder+transisi, config-driven) [thread billing_renewal]
       src/billing/webhook_app.py  — route webhook + checkout internal (mv-webhook :8088)
       src/orchestrator/payment_reconciler.py — thread reconciler (pull) [thread payment_reconciler]
       src/billing/limits.py       — can_produce / is_comp_account / PRODUCING_STATUSES
       src/utils/email.py          — notifikasi lifecycle (dwibahasa, config-driven)
FE     apps/web/src/components/app-shell.tsx (banner) · admin-shell.tsx (nav)
       apps/web/src/app/(app)/billing/page.tsx · auth/page.tsx · auth/callback/route.ts
       apps/web/src/app/feedback/page.tsx · api/feedback/route.ts · api/billing/checkout · api/niche-requests/[id]/pay
       apps/web/src/app/admin/(panel)/{billing,feedback}/page.tsx · api/admin/{payments,feedback}/route.ts
INFRA  nginx /etc/nginx/sites-enabled/mesinviral (location /api/webhooks/ → :8088) · .env (MIDTRANS_*, APP_BASE_URL, SMTP_*)
```

---

## 7. OPERASIONAL & TESTING
- **Ganti timing** (trial/grace/reminder/expiry): `/admin/app-config` — berlaku tanpa deploy.
- **Sandbox e2e** (gratis): `MIDTRANS_ENV=sandbox` + restart → checkout → bayar kartu tes `4811 1111 1111 1114` (CVV
  `123`, OTP `112233`) → webhook/reconciler settle. Kartu tes hanya jalan di sandbox.
- **Go-live**: `MIDTRANS_ENV=production` + restart mv-webhook & mv-worker. (Dashboard Midtrans tak perlu diubah.)
- **Rekonsiliasi manual**: `reconcile_pending(sb)` — tarik status semua `payments` pending.
- **Refund**: via dashboard Midtrans (ledger admin read-only).

---

## 8. FITUR PERUSAHAAN / INVOICE / PAJAK (batch kelengkapan world-class)
- **Profil penerbit** = tabel `company_profile` (single-row, admin-editable **via `/admin/company-profile` — menu LIVE 2026-07-03**, migr 0112) — PT. LUMITE AUTOMASI
  INDONESIA (brand Lumite), NPWP/NIB/SK-Menkum/alamat/telp/email. Dipakai di invoice + kebutuhan sistem ke depan.
  NO-HARDCODE (di DB, bukan di kode).
- **customer_details Midtrans** = `{first_name: <nama tenant>, email}` (+ item_details) → rekonsiliasi jelas di dashboard.
- **Invoice / bukti bayar** = halaman siap-cetak `/billing/invoice/[order_id]` (pemilik + admin, via `/api/invoice/[id]`):
  kop perusahaan (company_profile), No. invoice (order_id), pembeli (tenant), item+periode, subtotal, PPN (bila `ppn_percent`>0),
  total, status LUNAS, metode. Print-to-PDF (browser), dwibahasa. Link di Riwayat invoice + admin + email struk.
- **PPN** = `app_config.ppn_percent` (default 0 = harga final; set 11 bila PKP) — invoice tampilkan DPP+PPN bila >0.
- **Refund/chargeback** = webhook `refund/partial_refund/chargeback` (langganan) → tenant `suspended` (akses dicabut).
- **Admin Comp/Diskon** = set `is_developer`/`discount_pct` per-tenant dari panel admin.
- **Konfirmasi pendaftaran** = email ber-brand kita (token_hash lintas-alat), bukan Supabase default.

## 9. PLAN vs REALISASI — kelengkapan fitur world-class (living tracker)
> Update tiap item ke ✅ saat tervalidasi 100%, lalu kerjakan berikutnya. (⬜ belum · 🟡 sebagian · ✅ selesai+validasi)

| # | Item | Realisasi |
|---|---|---|
| 0 | `company_profile` table + seed Lumite + `ppn_percent` (migr 0112) | ✅ applied + verified DB live |
| 1 | customer_details (nama+email) + item_details ke Midtrans (`midtrans.py::_snap_post`,`_tenant_name`) | ✅ deployed `04cf0a2` — **e2e sandbox: Midtrans terima payload → token** (visual di dashboard = last-mile owner) |
| 2 | Refund/chargeback → suspend (`midtrans.py::_apply_settlement` cabang refund) | ✅ deployed `04cf0a2` — logika verified (baca kolom benar, set suspended); e2e butuh event refund nyata |
| 3 | Invoice API `/api/invoice/[id]/route.ts` (pemilik+admin, company+ppn) | ✅ deployed — LIVE: no-auth **401** (gate benar); pola super-admin cocok `guard.ts` |
| 4 | Invoice page `apps/web/src/app/billing/invoice/[id]/page.tsx` (dwibahasa, PPN, print) | ✅ deployed — LIVE: `/billing/invoice/x` → **307 login+next** (privat+fungsional); render visual = saat ada payment |
| 5 | Invoice link: Billing history + `/admin/billing` + email struk (`email.py::notify_payment_receipt` +order_id/`_site_url`) | ✅ deployed — verified di FE (tenant order_id+"Cetak", admin order_id) + email receipt +order_id |
| 6 | `ppn_percent` di CFG_META grup Billing (`admin/app-config/page.tsx`) | ✅ deployed — build punya rute; PATCH app-config **nol allowlist** → PPN editable admin (no-hardcode) |
| 7 | Admin Comp/Diskon: API `/api/admin/tenants/[id]/comp` + FE modal (`admin/tenants/page.tsx`) | ✅ deployed — LIVE: no-auth **401**; renewal.py **EXEMPT** comp (`is_comp_account` :70 + sweep loop :178); modal+reload wired |
| 8 | Signup branded: route `/api/auth/signup` + `auth/page.tsx` doSignup/doResend di-rewire | ✅ deployed — LIVE: GET **405** (POST-only); callback `verifyOtp(type=signup)`; FE buang `supabase.auth.signUp/resend` |
| 9 | Validasi (build+py_compile+e2e) + deploy 1× (worker+FE) | ✅ **DONE** `04cf0a2` — py_compile OK · npm build exit 0 · DB live verified · 3 service active · endpoint LIVE tervalidasi |

**STATUS: DEPLOYED `04cf0a2` (2026-07-01), mode `MIDTRANS_ENV=sandbox`.** 3 service active (mv-worker/mv-webhook/mv-web). Go-live pembayaran nyata = set `MIDTRANS_ENV=production` + restart (gate [A1] owner di `SISA_KERJA_GO_LIVE.md`).

### 🧪 LAST-MILE INTERAKTIF (perlu browser/sesi owner — server-side sudah tervalidasi)
Validasi visual yang hanya bisa lewat aksi nyata (server-side & gating semua sudah lolos):
1. **1 pembayaran sandbox** (Billing → Ubah paket → bayar kartu tes `4811 1111 1111 1114`, CVV `123`, OTP `112233`) → cek: (a) di dashboard Midtrans **customer_details** (nama+email) tampil, (b) status → active, (c) **email struk** masuk berisi link invoice.
2. Buka link invoice → halaman **LUNAS** ber-kop Lumite, PPN muncul hanya bila `ppn_percent>0`, tombol **Cetak/PDF**.
3. Admin `/admin/tenants` → tenant → **Comp/Diskon** → set is_developer → simpan → badge "Comp" muncul, tenant EXEMPT sweep.
4. **Signup** email baru → email konfirmasi **ber-brand** (From: `mesinviral@lumite.biz.id`) → klik → `verifyOtp` → `/auth?view=verified`. (Syarat: Supabase "Confirm email" = ON.)

### Changelog
- **2026-07-03** — **direkonsiliasi ke realita** (audit verifikator): ralat rujukan baris comp-exempt (§9 #7 → `renewal.py` :70/:178) + ralat klaim changelog `reconcile_pending` (BUKAN kode-mati — ia PENJAMIN aktif dipanggil `payment_reconciler.py`). Menu **Company Profile** (`/admin/company-profile`) kini LIVE → klaim §8 `company_profile` "admin-editable" kini terpenuhi. Tetap **CLOSED** — status hidup di `SISA_KERJA_GO_LIVE.md`.
- **2026-07-01** — dibuat setelah implementasi penuh + validasi e2e sandbox (langganan+add-on) & live (reconciler,
  webhook Midtrans terbukti, feedback insert). Commit terkait: `53e272c` (checkout A1+E1), `9d0c8e5` (switch env + admin
  Payments), `d9f0171` (reconciler), `4d861ed` (siklus lengkap: reminder/dunning/banner/routing/feedback, config-driven, dwibahasa).
- **2026-07-01** — batch kelengkapan world-class (§8/§9) **DEPLOYED `04cf0a2`**: invoice siap-cetak (halaman+API, dwibahasa,
  PPN, kop company_profile), customer_details+item_details ke Midtrans (e2e sandbox: token diterima), refund/chargeback→suspend,
  `ppn_percent` no-hardcode di System Config, admin Comp/Diskon (renewal EXEMPT), signup ber-brand (token_hash lintas-alat,
  `auth/page.tsx` di-rewire, buang `supabase.auth.signUp/resend`), `company_profile` migr 0112 + seed Lumite. Validasi: py_compile+
  npm build(exit 0)+kolom/keys DB live+customer_details sandbox+endpoint LIVE (invoice 401, comp 401, signup 405, situs 200).
  Last-mile interaktif (1 bayar sandbox + comp toggle + signup email) = aksi owner. Bersih kode-mati minor. **(Ralat 2026-07-03: `reconcile_pending` BUKAN kode-mati — ia fungsi PENJAMIN aktif, dipanggil `payment_reconciler.py`; klaim "dihapus" keliru.)**
