# 💳🔐 PAYMENT & TENANT GATE ARCHITECTURE — MesinViral

> **🚧 DIBUKA KEMBALI 2026-08-02 — [G-UJI] GERBANG UJI PRODUKSI (§10).** Deep-dive 2-Agu menemukan **4 pintu
> yang menghasilkan video TANPA memeriksa status langganan** (Test Run · Test Niche · Jalankan-ulang · unduh stok)
> + **5 jalur reaktivasi yang tak satu pun melepas rem channel**. Rencana + tracker progress = **§10 (SSOT kerja ini)**.
> Bagian §1–§9 di bawah tetap berlaku untuk gerbang PRODUKSI; §10 menambah gerbang UJI. **Baca §10 sebelum menyentuh
> apa pun yang berkaitan dengan tombol uji / status langganan / rem channel.**

> **🔒 CLOSED — SPEC FINAL, LIVE PRODUKSI (update 2026-07-04).** Arsitektur payment + gate tenant (s/d `suspended`) **SELESAI + LIVE PRODUKSI TERBUKTI**: `MIDTRANS_ENV=production` + **pembayaran NYATA pertama sukses A-Z 2026-07-04** (GoPay Rp 149rb, effi trial→active, webhook settlement dari IP Midtrans, kuitansi terkirim — [A1] ✅ TUTUP di `SISA_KERJA_GO_LIVE.md`). Dokumen ini **BEKU sebagai referensi** — status hidup = `SISA_KERJA_GO_LIVE.md` (HUB). Lanjutan pasca-`suspended` (nurture/dunning/blokir/hapus-data) = `LIFECYCLE_NURTURE_ARCHITECTURE.md`. Jangan pakai isi doc ini sbg daftar kerja.

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
kembalikan `redirect_url` → FE redirect user ke halaman bayar Midtrans. `payments` = ledger (migr 0022 + 0108 + 0122/0123).

**Tambahan 2026-07-04 (terbukti bekerja di produksi nyata):**
- **Anti dobel-bayar** — `_cancel_pending_orders(sb, tenant_id, category)` dipanggil di awal KEDUA fungsi checkout:
  order `pending` lama tenant (kategori sama) DIBATALKAN via API Midtrans dulu (404 = belum di-charge → cukup tandai
  `canceled` di ledger). 1 tenant = maks 1 tagihan hidup per kategori. Terbukti 2× saat pembayaran nyata pertama.
- **Lanjutkan pembayaran** — `payments.redirect_url` (migr 0122) disimpan saat order dibuat → halaman Billing tampilkan
  banner "🧾 Ada tagihan menunggu" + tombol **"Lanjutkan pembayaran"** (order pending usia <24j). Email Midtrans sendiri
  TAK memuat link Snap — kanal kita (banner + email payment-link) yang menyediakannya.
- **Email payment-link** — `notify_payment_link` (email.py) terkirim tiap order dibuat ("Selesaikan pembayaran Anda",
  ber-brand, dwibahasa, berisi link Snap). Fail-soft.

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
  - **Audit (migr 0123, 2026-07-04):** selalu isi `payments.transaction_id` (referensi Midtrans dari payload) +
    `payments.paid_at` (settlement_time/transaction_time WIB) saat settlement — ledger query-able tanpa bongkar `raw_notification`.

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
| `notify_payment_link` | order dibuat (checkout) | link Snap "Selesaikan pembayaran" (email Midtrans tak memuat link) |

Link upgrade = `UPGRADE_URL` (default `/billing`); link feedback = `TRIAL_SURVEY_URL` (default `/feedback`).

---

## 5. FRONTEND
**Tenant:**
- **Banner in-app** (`components/app-shell.tsx`) — status + sisa hari + tombol Upgrade (muncul saat trial/trial_expired/
  grace/suspended; comp exempt). **Pintu upgrade selalu terlihat.**
- **Routing status-aware** (`auth/page.tsx doLogin` + `auth/callback/route.ts`) — non-produksi (trial_expired/suspended)
  → `/billing` (BUKAN terjebak `/onboarding`).
- **Billing** (`(app)/billing/page.tsx`) — paket/status (label jelas + sisa hari)/pemakaian + riwayat invoice (`payments`,
  RLS) + drawer 2-mode "Ubah paket" (Starter/Pro/Business) & katalog add-on (→ Pustaka Niche) + **banner tagihan pending
  "Lanjutkan pembayaran"** (redirect_url, <24j; checkout baru = auto-cancel tagihan lama).
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
       0122 (payments.redirect_url — lanjutkan-pembayaran) · 0123 (payments.transaction_id + paid_at + backfill)
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
- **Go-live**: ✅ **SUDAH — `MIDTRANS_ENV=production` LIVE sejak 2026-07-04** (flip + restart; dashboard Midtrans tak diubah).
- **Rekonsiliasi manual**: `reconcile_pending(sb)` — tarik status semua `payments` pending.
- **Refund**: via dashboard Midtrans (ledger admin read-only).

### Metode pembayaran merchant (temuan produksi 2026-07-04 — verified via API Snap)
- Aktif: **gopay (mode `deeplink` SAJA)** + 5 VA (bni/bri/cimb/permata/other) + echannel (Mandiri Bill). **QRIS TIDAK aktif.**
- Konsekuensi: **GoPay hanya muncul di HP** (deeplink ke app Gojek); di desktop Snap menyembunyikannya. Agar tampil di
  desktop → owner aktifkan **GoPay QRIS** di dashboard (persetujuan GoTo, tak instan; menambah kanal utk aiwa juga — tak merusak).
- Daftar metode dievaluasi Midtrans DINAMIS tiap halaman Snap dibuka (bukan terkunci saat order dibuat) & TIDAK dibatasi
  kode kita (tak kirim `enabled_payments`).
- Preferensi merchant (dibagi aiwa): display_name = "SD Islamia Islamic School" + logo Lumite — ganti = keputusan owner (Snap Preferences).

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

**STATUS: 🟢 LIVE PRODUKSI (`MIDTRANS_ENV=production`, 2026-07-04).** 3 service active (mv-worker/mv-webhook/mv-web).
**Pembayaran NYATA pertama TERBUKTI A-Z** (order `MV-starter-eb5e3f0d1eda-1783160261`, GoPay Rp 149rb): webhook settlement
masuk dari IP Midtrans → `payments` settlement + transaction_id/paid_at terisi → effi trial→active (period_end +30hr) →
kuitansi terkirim. Anti dobel-bayar terbukti 2× (2 order lama auto-cancel). [A1] ✅ di `SISA_KERJA_GO_LIVE.md`.

### 🧪 LAST-MILE INTERAKTIF — status per 2026-07-04
1. ~~1 pembayaran sandbox~~ → **✅ SUPERSEDED oleh pembayaran PRODUKSI nyata 2026-07-04** (status→active ✓, email struk ✓; visual customer_details di dashboard Midtrans = opsional owner).
2. Buka link invoice → halaman **LUNAS** ber-kop Lumite, PPN muncul hanya bila `ppn_percent>0`, tombol **Cetak/PDF**. *(⬜ visual owner — kini ADA payment nyata utk dicek)*
3. Admin `/admin/tenants` → tenant → **Comp/Diskon** → set is_developer → simpan → badge "Comp" muncul, tenant EXEMPT sweep. *(⬜ visual owner)*
4. **Signup** email baru → email konfirmasi **ber-brand** (From: `mesinviral@lumite.biz.id`) → klik → `verifyOtp` → `/auth?view=verified`. (Syarat: Supabase "Confirm email" = ON.) *(⬜ — tercakup [A5] smoke-test tenant baru)*

### Changelog
- **2026-08-02** — **🚧 [G-UJI] DOKUMEN DIBUKA KEMBALI — §10 ditambahkan (SSOT kerja gerbang uji).** Deep-dive
  atas perintah owner ("video uji privat bisa diubah publik sendiri → konten gratis tanpa bayar") menemukan:
  **4 pintu menghasilkan video tanpa cek status langganan** (Test Run · Test Niche · Jalankan-ulang lewat
  **browser→DB langsung** · unduh stok) + **5 jalur reaktivasi yang tak satu pun melepas rem channel** (billing
  nol sentuhan ke tabel `channels`). Bukti kebocoran nyata: m.yusroon (trial, jatah 1 video/hari) menekan uji 11×,
  7 ter-publish. Keputusan owner K1–K6 terekam §10b (grace: produksi jalan, uji dikunci · rem selalu lepas otomatis ·
  batasi jatah trial saja · cara-hitung dijadikan KENOP karena owner menahan keputusan). **Ralat yang dicatat
  supaya tak terulang:** Claude sempat mengklaim "membakar biaya AI kita" — SALAH, kunci AI 100% milik tenant
  (BYOK, no-fallback `tenant_config.py:539-577`); kebocorannya **NILAI**, bukan biaya. Nol kode disentuh.
- **2026-07-13** — **FINALISASI TIER PLAN Tahap 1-5 (`finalisasi_tier_plan.md`, akar tunggal 4-pilar).**
  Pembayaran/harga kini: (a) **periode NILAI-ADIL** `compute_new_period` (`midtrans.py`) — perpanjang
  paket-sama menyambung sisa hari, upgrade/downgrade prorate via rasio harga, bulanan↔TAHUNAN satu rumus
  (durasi ×period_months); idempotent via klaim optimistik (anti dobel-terapkan webhook×reconciler).
  (b) **harga checkout** `compute_checkout_amount` — diskon admin `discount_pct` 1–99 kini NYATA memotong
  (dulu dekorasi), terbesar-menang vs winback, comp DITOLAK checkout. (c) **TAHUNAN** knob
  `annual_discount_pct` + `payments.period_months` (migr 0156). (d) **kuota channel** ditegakkan server:
  RLS INSERT `channels` vs max_channels (migr 0155) + gate JALAN N-tertua (`limits.gate_for_channel`).
  (e) **auto-renew = BAYAR MANUAL by design** (bukan recurring API — lihat DESAIN §4 update). (f) revenue/MRR
  admin dari agregat nyata (RPC `admin_payments_stats` migr 0157; MRR = pembayaran ÷ period_months).
  (g) narasi paket + matriks + ilustrasi biaya = admin-editable (migr 0157/0158). (h) **insiden S3 NEO
  2026-07-13**: notif publish-gagal jalur terjadwal (dulu fosil log-only) di-wire ke Telegram tenant +
  alarm admin storage gagal-beruntun di janitor. Commit rangkaian: `fb04952`/`883836c`/`1b6b529`/`f9cd6aa`
  + fix notif `dc2394b`. Deploy Tahap 1-3+fix = VPS `75675cb` (2026-07-13); Tahap 4-5 menunggu ratifikasi
  redaksi + izin deploy owner.
- **2026-07-04** — **🟢 GO-LIVE PRODUKSI + rekonsiliasi doc ke realita** (instruksi owner): (1) [A1] TUTUP — flip
  `MIDTRANS_ENV=production` + **pembayaran nyata pertama sukses A-Z** (GoPay effi; webhook+aktivasi+kuitansi terbukti; §9).
  (2) Fitur baru tercatat: **anti dobel-bayar** `_cancel_pending_orders` + **redirect_url/lanjutkan-pembayaran** (migr 0122,
  banner Billing) + **email payment-link** `notify_payment_link` (§3.3) + **transaction_id/paid_at** (migr 0123, §3.4).
  (3) §7: metode merchant nyata (gopay deeplink-only → HP saja; QRIS tidak aktif; jangan sarankan QRIS s/d owner aktifkan).
  (4) Last-mile sandbox superseded oleh pembayaran produksi. Commit terkait: `227f2f8` (mobile-nav utk jalur bayar HP),
  `3a753d4` (0123+0124), `025f6dd` (anti-dobel + resume-payment).
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

---

# 10. [G-UJI] GERBANG UJI PRODUKSI — SSOT kerja aktif (dibuka 2026-08-02)

> **Status: 🟢 F1–F7 + AUDIT 3 PUTARAN SELESAI (2026-08-02/03) — BELUM DEPLOY (menunggu izin owner, §5.0).**
> 5 migrasi **SUDAH APPLIED ke DB live** (0190–0194) — gerbang lapis DATABASE sudah AKTIF di produksi;
> lapis API & layar baru aktif setelah deploy. **778 pemeriksaan lulus, 0 gagal** (§10e-3).
> Audit menemukan & menutup **5 lubang tambahan** di luar 4 pintu awal: tautan unduh hasil uji (§10e-2) ·
> JEBAKAN kunci-tanpa-jalur-buka (§10e-2) · pekerjaan disamarkan sbg admin · **produksi di channel tenant
> LAIN** · perpanjangan masa coba mandiri tanpa batas (§10e-3). **Total 9 pintu/celah ditutup.**
> Dokumen ini = satu-satunya tempat rencana & progress kerja ini. Pasca-compaction: baca §10 UTUH, jangan riset ulang §10a.
>
> **⚠️ DUA HAL MENUNGGU KEPUTUSAN OWNER (jangan diputuskan sendiri):**
> 1. **Efek berlaku-surut** — `m.yusroon` (trial) langsung terhitung 8/3 → terkunci, karena jatah dihitung
>    sejak `trial_started_at` sehingga riwayat lamanya ikut terhitung. Pilihan di akhir "Realisasi F1".
> 2. **Link perpanjangan trial 1-klik gratis** (§10a jalur 5) — memungkinkan tenant memperpanjang diri
>    berulang tanpa bayar. Belum pernah dipakai (0 kejadian di log), jadi tak mendesak.

## 10a. FAKTA TERVERIFIKASI 2026-08-02 (introspeksi kode + DB live — JANGAN AUDIT ULANG)

**Sebab kerja ini (owner 2-Agu):** video uji ter-unggah PRIVAT ke YouTube Studio tenant → **tenant bisa mengubahnya
jadi Publik sendiri** → mendapat konten tanpa bayar. Kebocoran **NILAI**, bukan biaya (biaya AI = kunci tenant sendiri
/BYOK, `tenant_config.py:539-577` no-fallback ke `.env` — dikoreksi owner setelah Claude salah klaim "biaya AI kita").

### 7 pintu keluar nilai — 4 TIDAK dijaga status langganan
| # | Pintu | Pintu masuk | Dijaga status? | Anchor |
|---|---|---|---|---|
| 1 | Produksi terjadwal | mesin | ✅ ya | `producer.py:533` `gate_for_channel` |
| 2 | Publish terjadwal | mesin | ✅ ya | `publisher.py:73` |
| 3 | **Test Run** (`job_type='test'`) → unggah PRIVAT ke YouTube tenant | API (service_role) | ❌ **TIDAK** | `api/channels/[id]/test/route.ts:31` |
| 4 | **Test Niche** (`test_nopub`) → presigned URL 10 mnt (bisa diunduh) | API (service_role) | ❌ **TIDAK** | `api/niches/mine/test/route.ts:45` + `lib/test-run.ts:16` |
| 5 | **Jalankan ulang** (`retry`) → unggah PRIVAT (default `publish_privacy='private'`) | 🔴 **browser → DB LANGSUNG** | ❌ **TIDAK** | `runs/[id]/page.tsx:93` |
| 6 | Unduh stok gudang | API | ❌ **TIDAK** (stok tenant non-aktif kini **0**) | `api/review/preview/route.ts` |
| 7 | Test niche admin (`admin_test`) | API | — comp internal | `api/admin/niches/[id]/test/route.ts:23` |

**Pintu 5 = jebakan utama.** Insert langsung dari browser; satu-satunya penjaga = RLS
`direct_jobs_tenant_insert` WITH CHECK `(tenant_id = auth.uid()::text)` — **nol pemeriksaan status**.
API (pintu 3/4/7) memakai `createAdminClient()` (service_role) yang **melewati RLS** → butuh pagar sendiri.
⇒ **3 lapis pagar WAJIB, masing-masing menjaga jalur berbeda; tidak saling menggantikan.**

Sapu lengkap (nol jalur lain): pembuat `direct_jobs` = 4 titik di atas. Pemanggil `Pipeline()` = 3 titik,
semua di `producer.py` (196 terjadwal · 327 run_direct publish=True · 409 test_nopub publish=False).
Tabel yang bisa ditulis browser (RLS non-SELECT) = 6: `channels`(insert/update) · `direct_jobs`(insert) ·
`niche_requests` · `support_messages` · `support_tickets`. Hanya `direct_jobs` yang memicu produksi.

### 5 jalur reaktivasi — TAK SATU PUN melepas rem channel
| # | Jalur | Hasil | Lepas rem? | Anchor |
|---|---|---|---|---|
| 1 | Bayar Midtrans | → `active` + periode baru + reset penanda | ❌ | `midtrans.py:395` |
| 2 | Admin "Aktifkan/Suspend" | → `active`/`suspended` | ❌ | `api/admin/tenants/[id]/suspend/route.ts:21` |
| 3 | Admin "Perpanjang trial" | → `trial` +N hari | ❌ | `api/admin/tenants/[id]/lifecycle/route.ts:53` |
| 4 | Admin "Aktifkan bersih" | → `trial` +N hari | ❌ | `.../lifecycle/route.ts:72` |
| 5 | **Tenant sendiri: link 1-klik email** | → `trial` +3 hari **GRATIS** | ❌ | `webhook_app.py:259` |

**Billing TIDAK PERNAH menyentuh tabel `channels`** (diverifikasi: nol `table("channels")` di `src/billing/*` selain
`limits.py:115` read & `youtube_oauth.py`). Konsekuensi: rem circuit-breaker (`production_paused`) hanya dilepas oleh
`run_direct` sukses (`producer.py:376-382`) — yaitu jalur yang justru akan DIKUNCI. **Tenant bisa terjebak.**

### Fakta jatah trial
- `trial_started_at` **TIDAK PERNAH diubah** oleh jalur perpanjangan mana pun (diverifikasi ke 3 kode + data:
  semua tenant `trial_started_at == created_at`) ⇒ **jangkar andal, tak bisa di-reset diam-diam**.
- Trial **bisa** diperpanjang berulang; link 1-klik gratis **belum pernah dipakai** (0 kejadian `[lifecycle]` di
  worker.log). Perpanjangan nyata 100% = aksi admin (`admin_audit`: m.yusroon 27-Jul 7 hari; ryan.andrian 2-Jul).
- Bukti kebocoran NYATA: **m.yusroon** (status `trial`, jatah paket Trial **1 video/hari**) menekan uji **11×**,
  **7 ter-publish**. Tombol uji tidak dihitung kuota (CLAUDE.md §6.6) ⇒ kuota tertembus.
- **riandipantria** (`trial_expired`) menekan uji **8×** — semua gagal karena kredensialnya sendiri rusak,
  **bukan karena kita menahan**. Dari 9 tenant `trial_expired`: 7 tanpa kunci AI valid (mustahil uji), 1 channel lolos
  gerbang kesiapan (Abyss ID, sudah ter-pause sejak 21-Jul).

### Fakta teknis pendukung
- `app_config`: `value` **integer** + `value_text` **text** (13 kenop pakai value_text). Layar admin sudah mendukung
  **angka · teks/JSON · dropdown (`options`) · readonly (`ops_*`)** — `admin/(panel)/app-config/page.tsx:51,276-286`.
- Volume: `direct_jobs` 98 · `tenant_configs` 17 · `app_config` 110 · `channels` 10 ⇒ fungsi gerbang di RLS = sepele.
- Migrasi terakhir = **0189**. Berikutnya 0190/0191.
- Fungsi DB pola yang bisa dicontoh: `channel_missing(ch)` / `tenant_ai_key_ok(...)` — `STABLE SECURITY DEFINER`.
- Panel uji menampilkan `j.error` **apa adanya** (`test-niche-panel.tsx:69`) = teks Indonesia mentah ⇒ pesan
  penolakan baru **wajib** pakai KODE + terjemahan FE (§3.5 CLAUDE.md), bukan teks mentah.
- **Fosil**: `"trialing"` dipakai 3 tempat FE (`channel-status.tsx:15`, `channels/[id]/page.tsx:806,889`) —
  **tidak ada di BE (`PRODUCING_STATUSES`) maupun DB**. Daftar status tercecer 2 tempat = sumber bug berikutnya.

## 10b. KEPUTUSAN OWNER (diketok 2026-08-02 — JANGAN tanya ulang)
| # | Keputusan | Ketokan |
|---|---|---|
| K1 | **grace**: produksi + publish rutin **TETAP JALAN**; **Test Run & Test Niche DIKUNCI** | ✅ owner |
| K2 | Pasca-aktif kembali: rem channel **SELALU dilepas otomatis**, tenant tak perlu menekan apa pun | ✅ owner |
| K3 | Tenant hidup: **batasi jatah uji TRIAL saja**; berbayar bebas | ✅ owner |
| K4 | Cara menghitung jatah (berhasil-saja vs semua) — owner menahan keputusan → **dijadikan KENOP**, bukan dibekukan | ✅ jalan tengah |
| K5 | `trial_expired`/`suspended`/`cancelled`/`blocked`: semua pintu uji dikunci | ✅ owner (perintah awal) |
| K6 | Terkunci = tombol **berubah jadi ajakan berlangganan**, bukan hilang, bukan gagal senyap | ✅ pola §7l CONTENT_CATEGORY |

**TERBUKA (belum diketok, JANGAN dikerjakan):** nasib link perpanjangan trial 1-klik gratis (§10a jalur 5) —
memungkinkan tenant memperpanjang diri berulang tanpa bayar; belum pernah dipakai ⇒ tak mendesak; keputusan produk.

## 10c. ARSITEKTUR — satu otak, tiga lapis
```
              tenant_test_gate(p_tenant_id) → jsonb {allowed, reason, used, max}
              (fungsi DB, STABLE SECURITY DEFINER — SATU-SATUNYA sumber kebenaran)
                 │                    │                      │
      Lapis DB (RLS)          Lapis API              Lapis MESIN (worker)
      menjaga pintu 5         menjaga pintu 3,4      menjaga job yang SUDAH antre
      (browser→DB)            (service_role          lalu status berubah
                               melewati RLS)         (race condition)

              tenant_resume_channels(p_tenant_id) → int (jumlah rem dilepas)
              dipanggil KELIMA jalur reaktivasi §10a — bukan hanya jalur bayar
```
**Alasan 3 lapis = teknis, bukan gaya:** tidak ada satu lapis yang bisa menggantikan yang lain (bukti §10a).

## 10d. KENOP (NO-HARDCODE — grup baru "Gerbang Uji Produksi")
| key | tipe | default | arti |
|---|---|---|---|
| `test_gate_enabled` | 0/1 | **1** | Saklar induk. 0 → perilaku **identik hari ini**, seketika tanpa deploy (jaring pengaman owner) |
| `test_allowed_statuses` | value_text JSON | `["active","trial"]` | Status yang boleh menguji. Tambah `"grace"` bila owner berubah pikiran |
| `trial_test_quota` | integer | **3** | Jatah uji tenant trial. **0 = tanpa batas** (pola sama `nurture_trial_extend_days`) |
| `trial_test_quota_counts` | dropdown | `success` | `success` = hanya uji BERHASIL memotong jatah · `all` = semua percobaan. **K4** |
| `trial_quota_reset_on_extend` | 0/1 | **1** | Jatah segar saat admin memperpanjang trial (perpanjangan admin = sengaja) |
| `auto_resume_on_reactivate` | 0/1 | **1** | Rem channel dilepas otomatis saat tenant aktif kembali (**K2**) |

Semua wajib lahir LENGKAP (CLAUDE.md §3.3): baris DB + label/deskripsi dwibahasa + grup sendiri + tipe input tepat.

## 10e. FASE & DAFTAR FILE — tracker progress (update kolom Status saat kerja)
| Fase | Berkas | Perubahan | Status |
|---|---|---|---|
| F1 | `migrations/0190_kenop_gerbang_uji.sql` | 6 kenop + deskripsi (kenop DULU — fungsi membacanya) | ✅ **APPLIED** 2-Agu |
| F1 | `migrations/0191_gerbang_uji_tenant.sql` | kolom `trial_extended_at` + 2 fungsi + hak akses + ganti RLS `direct_jobs_tenant_insert` | ✅ **APPLIED** 2-Agu |
| F3 | `migrations/0192_gerbang_produksi_untuk_unduh.sql` | **SUSULAN** — `tenant_produce_allowed()` utk pintu unduh stok (aturan PRODUKSI, bukan uji) | ✅ **APPLIED** 2-Agu |
| F2 | `src/billing/limits.py` | `test_gate()` + `resume_channels()` bersebelahan `can_produce()` — **memanggil otak DB, tidak menghitung sendiri** | ✅ |
| F2 | `src/orchestrator/producer.py` | `run_direct` cek gerbang sebelum eksekusi; tolak → `failed` + **kode** `GATE:…`; `admin_test` dikecualikan | ✅ |
| F2 | `src/billing/midtrans.py` | panggil `resume_channels` saat settlement (fail-soft, tak mengganggu jalur uang) | ✅ |
| F2 | `src/billing/webhook_app.py` | link 1-klik: `trial_extended_at` (satu update atomik) + lepas rem | ✅ |
| F3 | `apps/web/src/lib/test-gate.ts` | **BARU** — pemanggil gerbang sisi Next.js + `gateCode()` | ✅ |
| F3 | `api/channels/[id]/test/route.ts` | gerbang di POST + `gate` di GET (tombol tampil terkunci sebelum ditekan) | ✅ |
| F3 | `api/niches/mine/test/route.ts` | idem | ✅ |
| F3 | `api/admin/tenants/[id]/suspend/route.ts` | lepas rem saat → active + dicatat di `admin_audit` | ✅ |
| F3 | `api/admin/tenants/[id]/lifecycle/route.ts` | `trial_extended_at` + lepas rem (extend & reactivate_clean) | ✅ |
| F3 | `api/review/preview/route.ts` | gerbang unduh stok pakai `tenant_produce_allowed` (grace tetap boleh) | ✅ |
| F4 | `admin/(panel)/app-config/page.tsx` | grup baru + 6 kenop lengkap + **dropdown numerik berlabel** (`optionLabels`) | ✅ |
| F5 | `apps/web/src/components/gate-message.tsx` | **BARU** — penerjemah kode `GATE:*` → kalimat dwibahasa + ajakan | ✅ |
| F5 | `lib/channel-status.tsx` | `SUB_PRODUCING`/`subIsProducing()` satu tempat + **fosil `trialing` dibuang** | ✅ |
| F5 | `channels/[id]/page.tsx` | pakai `subIsProducing` (2 tempat) — fosil `trialing` habis | ✅ |
| F5 | `runs/[id]/page.tsx` | "Jalankan ulang" tanya gerbang dulu; 3 pesan diubah jadi **dwibahasa** (dulu ID saja) | ✅ |
| F5 | `components/test-niche-panel.tsx` | tombol **Terkunci** + alasan + ajakan; pesan galat lewat penerjemah | ✅ |
| F5 | `niche-studio/page.tsx` | **tak perlu disentuh** — memakai `TestNichePanel` yang sama | ✅ n/a |
| F6 | `tests/test_gerbang_uji.py` | **BARU** — 21 uji hermetik: kontrak · gagal-jujur · penolakan `run_direct` · anti-drift SQL↔Python | ✅ |
| F7 | dokumen ini §10 + `SISA_KERJA_GO_LIVE.md` + `MEMORY.md` | realisasi + penunjuk (CLAUDE.md §3.7) | ✅ |

### Realisasi F2–F7 (2026-08-02) — bukti
**Validasi 5 jalur, 707 pemeriksaan, 0 gagal** (dijalankan ULANG seluruhnya setelah setiap perbaikan):

| Jalur | Hasil | Cara |
|---|---|---|
| Lapis DB | **64/64** | menyamar tenant sungguhan (`set local role authenticated` + jwt claims) lalu INSERT nyata; transaksi di-ROLLBACK |
| Mesin (RPC) | **30/30** | `test_gate`/`resume_channels` memanggil DB live untuk 17 tenant nyata |
| Suite proyek | **581 passed** | naik dari 560 (+21 uji baru); nol regresi pada 560 lama |
| Lapis API | **13/13** | sesi tenant SUNGGUHAN via magiclink → HTTP nyata ke server build baru |
| Layar | **19/19** | Playwright: tenant mati · mode EN · tenant aktif · layar admin. **Nol galat halaman** |

Bukti layar tersimpan: `scratchpad/layar_tenant_terkunci.png` (tombol 🔒 Terkunci + alasan + "Lihat paket →"),
`layar_tenant_terkunci_en.png`, `layar_tenant_aktif.png`, `admin_kartu_gerbang2.png` (6 kenop + dropdown berlabel).
`tsc --noEmit` bersih · `next build` sukses · `py_compile` 4 berkas OK.

**Produksi tak tergores:** `direct_jobs` tetap 98 · channel terjeda tetap 3 (Abyss ID, Bang Us-Dat, BISIK
NUSANTARA — ketiganya sudah terjeda SEBELUM kerja ini) · nol status tenant berubah.

**BUG DITEMUKAN & DITUNTASKAN selama siklus validasi (4):**
1. **Kode produksi** — `limits.test_gate` meneruskan dict sembarang dari RPC tanpa memastikan ada kunci
   `allowed` bertipe bool. Pemanggil yang menulis `g["allowed"]` akan `KeyError`. Sisi TypeScript sudah
   memvalidasi, sisi Python belum. → validasi kontrak ditambahkan; ditemukan oleh uji `[{"tidak":"relevan"}]`.
2. **Uji** — `now()` di dalam satu transaksi mengembalikan waktu MULAI transaksi, sehingga job uji dan
   penanda perpanjangan bercap waktu identik. Fungsi tidak salah; ujinya tak realistis. *Pelajaran: uji
   berbasis `now()` dalam transaksi adalah jebakan — beri jarak waktu eksplisit.*
3. **Uji** — pytest mengumpulkan fungsi terimpor bernama `test_gate` sebagai kasus uji → alias `periksa_gerbang`.
4. **Uji** — perkakas memilih akun ber-`is_developer` sebagai admin, padahal super-admin ditentukan
   `app_metadata.role` (`guard.ts:13`). Sembilan pemeriksaan merah tanpa ada yang salah di aplikasi.
   *Pelajaran: `is_developer` (comp billing) ≠ `super_admin` (hak layar admin) — dua konsep berbeda.*

Catatan tambahan yang ditemukan sambil jalan: cookie sesi tenant bisa melewati batas 4096 byte
(terukur 4439 utk tessartea vs 2659 utk rw23mutiara) → perkakas uji wajib memecahnya seperti
`@supabase/ssr` (`.0`, `.1`), kalau tidak browser menolak dengan pesan menyesatkan "Invalid cookie fields".

**Keputusan teknis reversible yang diambil sendiri (§2.3c), dicatat di sini:**
- Jatah trial menghitung **ketiga** jenis pekerjaan manual (`test`, `test_nopub`, `retry`) — ketiganya
  menghasilkan video di luar kuota terjadwal. `admin_test` dikecualikan (channel internal admin).
- Gerbang uji **fail-CLOSED** saat RPC tak terjawab (`gate_unavailable`), berbeda dari `channel_readiness`
  yang fail-OPEN. Alasan: uji = aksi manual yang bisa diulang; menolak sesaat tak menghentikan produksi.
- `optionLabels` ditambahkan ke meta kenop admin → kenop 1/0 kini dropdown berlabel. Efek samping searah
  aturan: `qc_require_audio` (satu-satunya kenop lama ber-`options` numerik) ikut jadi dropdown.

### Realisasi F1 (2026-08-02)
- **Migrasi 0190 + 0191 APPLIED ke DB live.** `app_config` 110 → **116**; kolom `tenant_configs.trial_extended_at`
  ada (terisi 0 tenant — belum ada jalur yang mengisinya, itu F2/F3). Cadangan pra-migrasi:
  `scratchpad/cadangan_pra_gerbang.json` (policy lama + 110 kenop + 17 tenant + 10 channel).
- **Uji lapis DB: 64 LULUS / 0 GAGAL** (`scratchpad/uji_gerbang_db.py`) — menyamar sebagai tenant sungguhan
  (`set local role authenticated` + `request.jwt.claims`) lalu benar-benar INSERT, seluruhnya dalam transaksi
  yang di-ROLLBACK. Cakupan: 7 status × 3 job_type · comp kebal · saklar induk OFF · jatah (success/all/jangkar/
  reset/tanpa-batas/berbayar-bebas) · pagar privasi · service_role tembus (by design) · hak pelepas rem ·
  kenop rusak & terhapus · masukan tak wajar. Produksi tak tergores: `direct_jobs` tetap 98, channel terjeda tetap 3.
- **1 bug ditemukan & dituntaskan — pada UJI, bukan pada fungsi:** dalam satu transaksi `now()` mengembalikan waktu
  MULAI transaksi, jadi job uji dan penanda perpanjangan bercap waktu identik → filter `created_at >= anchor` ikut
  mencocokkan. Diperbaiki dengan cap waktu realistis (job dibuat 1–2 jam sebelum perpanjangan) → hijau. Fungsi
  tidak diubah. **Pelajaran: uji berbasis `now()` di dalam transaksi adalah jebakan — selalu beri jarak waktu.**
- **⚠️ EFEK BERLAKU-SURUT (perlu keputusan owner, BELUM ditindak):** `m.yusroon` (status `trial`) langsung terhitung
  **8/3 → terkunci**, karena jatah dihitung sejak `trial_started_at` sehingga riwayat lama ikut terhitung. Pilihan:
  (a) biarkan (ia memang sudah memanen 7 video lewat tombol uji), (b) set `trial_extended_at = now()` untuk tenant
  trial yang ada saat gerbang dinyalakan = jatah segar sejak kebijakan berlaku, (c) owner perpanjang trialnya lewat
  layar admin (efeknya sama dengan (b), tanpa kode). Tenant lain tak terdampak.

## 10e-2. AUDIT FINAL PRA-DEPLOY (2026-08-02, perintah owner) — 2 lubang DITEMUKAN & DITUTUP

Audit ini sengaja TIDAK mengulang yang sudah hijau; ia memburu apa yang saya **tanam atau tinggalkan**.

### Lubang 1 — pintu keluar KEENAM yang terlewat: tautan unduh hasil uji
`lib/test-run.ts::latestTestResult` menerbitkan **presigned URL video uji terakhir** tanpa gerbang apa
pun, dan menerbitkannya **ulang setiap kali halaman dibuka**. Tenant yang langganannya mati tetap bisa
memanen video uji terakhirnya berkali-kali — tanpa menekan tombol apa pun. Ini pintu paling senyap dari
semuanya, dan saya melewatkannya di sapuan pertama karena hanya menelusuri pembuat `direct_jobs`.
**Ditutup** dengan gerbang PRODUKSI (grace tetap boleh melihat hasilnya — konsisten dengan pintu stok).

> **⚠️ HIJAU PALSU yang nyaris lolos.** Uji pertama untuk lubang ini LULUS — padahal lubangnya masih
> terbuka. Sebabnya: tenant terkunci yang dipakai menguji tak punya video sama sekali (semua ujinya
> gagal), jadi tautannya kosong karena **tak ada isinya**, bukan karena gerbang menahan. Uji diperbaiki:
> tenant terkunci **diberi video uji sungguhan**, lalu ditambah **uji pembanding** (hidupkan sesaat →
> tautan wajib TERBIT). Tanpa pembanding itu, "tidak ada tautan" tak membuktikan apa pun.
> **Pelajaran: setiap uji "X tidak terjadi" WAJIB berpasangan dengan uji "X terjadi" pada kondisi lawan.**

### Lubang 2 — JEBAKAN yang lahir dari gerbang ini sendiri (kunci tanpa jalur buka)
Rem darurat channel (3 produksi gagal beruntun) selama ini **hanya** bisa dilepas oleh "Jalankan ulang"
yang sukses. Setelah gerbang uji dipasang, tombol itu terkunci untuk:
- tenant **masa tenggang** — padahal produksi rutinnya SENGAJA tetap jalan (keputusan K1)
- tenant **masa coba yang jatah ujinya habis** — produksi rutinnya juga masih jalan

Keduanya **terjebak**: mesin berhenti, satu-satunya pemulih dikunci. Bukan teori — `m.yusroon` (trial,
jatah uji habis, produksi boleh) tinggal menunggu 3 kegagalan beruntun, dan kegagalan seperti itu
terjadi pada 3 channel lain di hari yang sama.

**Ditutup** dengan jalur buka yang tidak memproduksi apa pun: migrasi **0193** (parameter channel pada
`tenant_resume_channels`) + endpoint `POST /api/channels/[id]/resume` (gerbang PRODUKSI + kepemilikan) +
tombol **"Pulihkan produksi"** yang muncul PERSIS pada kondisi terjebak. Melepas rem tak memanggil AI,
tak merender, tak mengunggah; bila sebabnya belum diperbaiki, rem menyala lagi setelah 3 kegagalan.

### Matriks "setiap kunci punya jalur buka" (mandat owner)
| Kunci | Jalur buka yang sah |
|---|---|
| Gerbang uji — status mati | bayar (Midtrans) · admin **Aktifkan** · admin **Perpanjang trial** · admin **Aktifkan bersih** |
| Gerbang uji — masa tenggang | bayar · admin Aktifkan |
| Jatah uji masa coba habis | bayar · **admin Perpanjang trial** (jatah ikut segar — kenop `trial_quota_reset_on_extend`) |
| Tautan unduh hasil uji / stok | sama dengan gerbang produksi (masa tenggang tetap boleh) |
| **Rem channel** | "Jalankan ulang" (bila uji boleh) · **otomatis** saat reaktivasi · **"Pulihkan produksi"** (baru — untuk yang produksinya boleh tapi ujinya terkunci) |
| Saklar induk gerbang | `/admin/app-config` → **Gerbang Uji Aktif = Tidak** (seketika, tanpa deploy) |

### Berkas tambahan dari audit (di luar tracker §10e)
| Berkas | Perubahan |
|---|---|
| `migrations/0193_pulihkan_channel_per_channel.sql` | ✅ APPLIED — `tenant_resume_channels` + parameter channel opsional |
| `apps/web/src/app/api/channels/[id]/resume/route.ts` | **BARU** — jalur buka manual (gerbang PRODUKSI + kepemilikan) |
| `apps/web/src/lib/test-run.ts` | gerbang pada penerbitan tautan unduh hasil uji (lubang 1) |
| `apps/web/src/app/(app)/channels/[id]/page.tsx` | tombol **"Pulihkan produksi"** pada kondisi terjebak + `pulihkanProduksi()` |
| `apps/web/src/components/test-niche-panel.tsx` | prop `onGate` (lapor keadaan gerbang ke halaman induk, via ref — anti loop polling) |
| `tests/test_gerbang_uji.py` | +5 uji: setiap jalur reaktivasi WAJIB tetap memanggil pelepas rem |

### VALIDASI TOTAL PASCA-AUDIT — 755 pemeriksaan, 0 gagal
Seluruhnya dijalankan ULANG setelah perbaikan terakhir, bukan hanya bagian yang berubah:

| Jalur | Hasil |
|---|---|
| Lapis DB (samar sebagai tenant) | 64/64 |
| Mesin (RPC ke DB live) | 30/30 |
| Suite proyek | **586 passed** (560 → 581 → 586) |
| Lapis API (sesi tenant nyata) | 13/13 |
| Layar (klik→mata) | 19/19, nol galat halaman |
| Audit final (jalur belum teruji) | 14/14 |
| Pintu 6 + pembanding | 6/6 |
| **Jalur buka** (kondisi terjebak dibuat sungguhan) | 10/10 |
| **Proses terkait** (admin suspend · admin perpanjang · 3 layar lain) | 13/13 |

Bukti jalur buka resmi owner berjalan: admin menekan **Perpanjang trial** pada `m.yusroon`
(terkunci `trial_quota`) → `trial_extended_at` tercatat → gerbang berubah jadi `allowed=true`,
terpakai kembali `0`. Dikembalikan apa adanya setelah diuji.

Keadaan produksi setelah SELURUH pekerjaan: `direct_jobs` **98** · channel terjeda **3** ·
nol status tenant berubah · nol `trial_extended_at` terisi.

### Kesalahan prosedur saya yang TERULANG (dicatat supaya berhenti terulang)
Uji lubang 1 sempat merah palsu karena **server lokal yang diuji masih build LAMA** — `pkill` gagal
(exit 144) dan proses lama (20:38) tetap hidup saat build baru sudah jadi (23:45). Ini **kejadian kedua**
pada sesi yang sama. **Aturan untuk seterusnya: setelah build, WAJIB bandingkan waktu-mulai proses
server dengan waktu `.next/BUILD_ID`; jangan percaya `pkill`, bunuh lewat PID lalu verifikasi.**

## 10e-3. AUDIT PUTARAN KETIGA — 3 CELAH LAGI, dua di antaranya LINTAS-TENANT

> Owner: *"kalau anda masih menemukan bug, artinya audit terakhir juga bisa jadi anda masih miss."*
> Benar. Putaran ini menemukan **tiga celah lagi — dua di antaranya lebih serius dari semua yang
> sebelumnya**, karena menembus batas antar-tenant.

### CELAH A — pekerjaan bisa DISAMARKAN sebagai pekerjaan admin *(dibuktikan: HTTP 201)*
Aturan tabel antrean hanya memeriksa "atas nama diri sendiri" — **tidak** memeriksa JENIS pekerjaan.
Sementara itu worker sengaja MELEWATI gerbang untuk `admin_test`, dan penghitung jatah hanya
menghitung `test`/`test_nopub`/`retry`. Tenant cukup menulis `admin_test` dari browser untuk
memproduksi **tanpa batas**: melewati jatah DAN melewati pemeriksaan worker sekaligus.
**Ditutup:** aturan tabel membatasi jenis + pengecualian `admin_test` di worker **dicabut** (tak
diperlukan — tenant internal admin adalah akun comp yang gerbangnya selalu mengizinkan).

### CELAH B — produksi bisa dipicu di CHANNEL MILIK TENANT LAIN *(dibuktikan: HTTP 201)*
Aturan tabel memeriksa `tenant_id` tapi **tidak** memeriksa bahwa channel yang ditunjuk memang milik
tenant itu. Worker memakai channel dari job apa adanya, termasuk **kunci AI + koneksi YouTube
korban** → membakar dompet mereka dan mengunggah ke kanal mereka.
**Ditutup:** aturan tabel memeriksa kepemilikan + worker memeriksa ulang sebelum apa pun dikerjakan.
Data historis diperiksa: **NOL** pekerjaan pernah memakai channel orang lain — ditutup sebelum terjadi.

> **KEJUJURAN:** celah A & B **lebih tua** dari gerbang uji — aturan `direct_jobs_tenant_insert`
> sudah begitu sejak dibuat. Tetapi **saya baru saja mengganti aturan itu di 0191 dan tidak
> memperbaikinya saat itu.** Saya menyentuh persis baris yang bocor dan melewatkannya.

### CELAH C — perpanjangan masa coba mandiri BERULANG tanpa batas
Link 1-klik di email memperpanjang masa coba gratis. Komentar kode lama mengklaim "tak bisa berulang
tanpa lapse lagi" — dan **di situlah bugnya**: masa coba memang lapse lagi beberapa hari kemudian,
sementara token email berlaku 90 hari. Siklus lapse → klik → lapse → klik = **masa coba gratis
selamanya**. Owner: *"jelas-jelas bug yang harus ditutup."*

**Ditutup TANPA membuang jalur konversinya** (jawaban atas pertanyaan owner "penggantinya seperti apa"):

| Yang mengklik | Sebelum | Sesudah |
|---|---|---|
| Masa coba lapse, **pertama kali** | +N hari gratis | **tetap** +N hari gratis (umpan konversi) |
| Masa coba lapse, **sudah pernah** | +N hari gratis **lagi, tanpa batas** 🔴 | layar **"Lihat paket"** → diarahkan **UPGRADE** |
| **Pernah membayar** (tenggang/ditangguhkan) | dilempar diam-diam ke `/billing` | layar **"Perpanjang sekarang"** → diarahkan **RENEW** |

Dulu cabang non-gratis melompat ke halaman tagihan **tanpa satu kalimat pun penjelasan** — cara
tercepat kehilangan orang yang sebenarnya sudah hampir membayar. Kini halaman reaktivasi menjelaskan
keadaannya, menegaskan pengaturan channel mereka masih utuh, lalu mengarahkan ke jalur uang yang tepat.

Kolom `tenant_configs.trial_self_extends` menghitung perpanjangan **mandiri** saja — perpanjangan oleh
admin tidak menambahnya, karena admin memang berwenang memperpanjang berkali-kali (perintah owner:
*"jika ingin diperpanjang dilakukan lewat FE admin panel"*). Batasnya kenop
**`nurture_self_extend_max`** (default 1; **0 = tenant tak boleh sama sekali**).

### Berkas putaran ketiga
| Berkas | Perubahan |
|---|---|
| `migrations/0194_antrean_produksi_tak_bisa_disamarkan.sql` | ✅ APPLIED — aturan tabel 4 syarat + kolom `trial_self_extends` + kenop `nurture_self_extend_max` |
| `src/orchestrator/producer.py` | cabut pengecualian `admin_test` + tolak channel milik tenant lain |
| `src/billing/webhook_app.py` | batas perpanjangan mandiri + `arah` (upgrade/renew) |
| `apps/web/src/app/reactivate/page.tsx` | layar checkout dwibahasa: **Perpanjang** vs **Lihat paket** |
| `admin/(panel)/app-config/page.tsx` | kenop **Batas Perpanjang Mandiri** lahir lengkap (total 7 kenop baru) |
| `tests/test_gerbang_uji.py` | +3 uji (jenis pekerjaan · channel silang · batas perpanjangan) |

### VALIDASI TOTAL PUTARAN KETIGA — **778 pemeriksaan, 0 gagal**
| Jalur | Hasil |
|---|---|
| Lapis DB · Mesin RPC | 64 · 30 |
| Suite proyek | **589 passed** (560 → 581 → 586 → 589) |
| **Celah C** — layanan webhook dijalankan NYATA (TestClient), token HMAC sah | **18/18** |
| API · Layar · Audit final · Pintu 6 · Jalur buka · Proses terkait | 13 · 19 · 14 · 6 · 10 · 13 |
| **Celah A · Celah B** — penyisipan nyata ke tabel antrean | ✅ 403 (dulu 201) |

Produksi tak tergores: `direct_jobs` **98** · channel terjeda **3** · perpanjangan mandiri **0** ·
`trial_extended_at` **0** · kenop 110 → **117**.

**Kesalahan prosedur yang TERULANG (ketiga kalinya):** uji celah C sempat 401 di semua langkah —
endpoint webhook dijaga rahasia internal dan uji saya tidak mengirim headernya. Bukan bug aplikasi;
**pagar yang benar**. Pola yang sama dengan dua sebelumnya: **saya menyalahkan aplikasi sebelum
memeriksa perkakas ujinya sendiri.**

## 10f. MATRIKS REGRESI — "haram bug baru" (tiap baris = uji otomatis)
| Wajib tetap utuh | Risiko yang dijaga |
|---|---|
| `active` bisa Test Run + Test Niche + Jalankan-ulang | gerbang terlalu ketat |
| `trial` bisa menguji sampai jatah habis, lalu ditolak sopan | hitungan jatah salah |
| Comp (is_developer / diskon≥100) **tak tersentuh** | fungsi lupa mengecualikan comp |
| Produksi otomatis `grace` **tetap jalan** (`can_produce` tak berubah) | aturan produksi & uji tercampur |
| Publish `grace` tetap jalan | idem |
| `admin_test` tetap jalan | tenant internal ikut terpagari |
| Lepas rem **tidak** menghidupkan channel yang `channel_missing` ≠ kosong | gerbang kesiapan bocor |
| `effectiveStatus` untuk 6 status tak berubah tampilannya | menyentuh satu-sumber status |
| `test_gate_enabled=0` → perilaku **identik** hari ini | jaring pengaman tak berfungsi |
| Semua pesan penolakan **dua bahasa** | melanggar §3.5 |
| RLS baru tidak memblokir `admin_test` (service_role) | policy salah sasaran |

**Metode uji lapis DB:** menyamar sebagai tenant (`set local role authenticated` + `request.jwt.claims`) di dalam
transaksi, coba INSERT untuk **setiap status × setiap job_type** — bukan menyimpulkan dari membaca kode.

## 10g. SIKLUS VALIDASI (perintah owner: ulang sampai NOL bug)
```
uji seluruh matriks §10f → ada merah? → perbaiki → uji ULANG SELURUHNYA (bukan hanya yang merah)
  ↓ semua hijau
rantai nyata: tekan tombol sungguhan di layar untuk tiap status (bukti klik→layar, §3.4)
  ↓ benar
5 permukaan §2.1: DB · BE · FE-tenant · FE-admin · Telegram
  ↓ bersih
baru lapor selesai → tunggu izin deploy per-batch (§5.0)
```

## 10h. ROLLBACK
(a) `test_gate_enabled=0` dari layar admin — seketika, tanpa deploy · (b) git tag sebelum kerja ·
(c) cadangan JSON baris `app_config` + definisi RLS lama.

## 10i. TIDAK DISENTUH
Mesin produksi (naskah/suara/gambar/render/durasi) · `channel_missing` · rem 3-kegagalan · harga & paket ·
jalur pembayaran Midtrans itu sendiri · kuota channel (`in_quota`) · v1.
