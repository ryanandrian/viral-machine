# 🔄 LIFECYCLE & NURTURE ARCHITECTURE — MesinViral

> **🔒 CLOSED — SPEC FINAL (2026-07-03).** Seluruh fitur (termasuk **item 14** tombol aksi-manual admin) **SELESAI + deployed + tervalidasi**; dokumen direkonsiliasi ke realita DB/BE/FE (audit verifikator 2026-07-03). **BEKU sebagai referensi** — status hidup & sisa aksi = **`SISA_KERJA_GO_LIVE.md`** (HUB, item [B9]). Sisa = verifikasi data-nyata otomatis (revoke token / purge S3 / email-hapus saat tenant nyata lewat siklus). Jangan pakai marker doc ini sbg daftar kerja.
>
> **Sumber kebenaran TUNGGAL** untuk *tindak-lanjut siklus-hidup tenant* **setelah** gate langganan: (1) selamatkan
> **trial yang lapsed** (nurture), (2) tagih/selamatkan **pelanggan berbayar yang berhenti** (dunning + win-back),
> (3) **blokir & hapus data** yang benar-benar tak kembali (bebaskan storage). **SATU mesin** (bukan dua) — segmen beda,
> jalur sama. Dibuat 2026-07-02.
>
> **Prinsip:** **NO-HARDCODE** (semua timing/insentif = saklar admin `app_config`) · **world-class** · **dwibahasa EN/ID** ·
> **patuh UU PDP** (hak hapus data + cabut token YouTube) · **idempotent + fail-soft** (kegagalan 1 tenant tak stop sweep).
>
> **🔗 Rantai kanonik:** backlog/status = **`SISA_KERJA_GO_LIVE.md`** (HUB — item ini = **[B9]**; terkait [B8] /feedback, [D1] funnel).
> **MELANJUTKAN** **`PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`** (CLOSED; gate berhenti di `suspended` → di sini `suspended→blocked→deleted` + nurture).
>
> **✅ STATUS: DEPLOYED + LIVE (v2-backend, 2026-07-02).** Mesin lifecycle penuh berjalan di VPS (thread `billing_renewal`,
> sweep terverifikasi jalan bersih; endpoint `/reactivate` live). Di-*ground* pada deep-dive DB+BE+FE(tenant & admin) nyata.
> Mode aman: default suspended 30h + retensi 30h → **nol risiko hapus mendadak**; timing semua di `app_config` (admin-editable).
> **Bukan pemblokir jualan** — pengoptimal konversi/biaya. **Item 14 (tombol aksi-manual admin) = ✅ SELESAI 2026-07-03.** Sisa = verifikasi data-nyata §11 (revoke token / purge S3 / email-hapus — matang saat ada tenant nyata lewat siklus).

---

## 0. KEPUTUSAN OWNER (TERKUNCI 2026-07-01/02) — semua default, adjustable di admin
| Keputusan | Nilai (default) |
|---|---|
| Insentif comeback = **saklar admin** (3 tuas) | perpanjang-trial **ON** · diskon **OFF** (angka siap) · pesan-nilai **selalu ON** |
| Kanal lead PANAS | **Email + notif admin ke Telegram** (concierge manual) |
| Panjang sekuens nurture trial-lapse | **Standar 4–5 email, ~2–3 minggu** |
| Masa **suspended** (data utuh, 1-klik aktif-lagi) | **30 hari** |
| Retensi setelah **blocked** sebelum hapus | **30 hari** (peringatan H-30/7/1) |
| Hapus DINI file video mentah S3 saat suspended | **YA** (video aman di YouTube; simpan config/insight) |
| Tombol "Unduh data saya" self-service | **NANTI/manual** (admin bantu bila diminta) — tak dibangun sekarang |
| **Kirim email manual** (tenant detail, subject+body) | **DIPERTAHANKAN** sebagai alat concierge personal — komplementer, BUKAN diganti nurture |

---

## 1. STATE MACHINE — lanjutan dari gate (grounded)

```
trial ─lewat─▶ trial_expired ──(nurture 4–5 email, ~2–3 mgg; suhu lead)──┐
                 └── LEADS (di /admin/tenants) ──────────────────────────┼─ bayar/upgrade ─▶ active
active ─lewat─▶ grace(7h, msh jalan) ─lewat─▶ suspended ─30h─▶ blocked ─30h─▶ DELETED
                                              │stop produksi  │akun terkunci  │purge DB+S3
                                              │login+1klik    │jadwal-hapus   │+cabut token YT
                                              │data UTUH       │warn H-30/7/1  │+sisakan record
                                              │dunning+winback │               │ legal minimal
                                              └── bayar → active ◀── (sampai sedetik sblm deleted) ──┘
comp/developer (is_developer OR discount_pct≥100) = EXEMPT dari SELURUH alur.
```

**Grounding (verified 2026-07-02):**
- ✅ Kolom `tenant_configs.subscription_status` = **text tanpa CHECK constraint** → tambah nilai `blocked`/`deleted` **TAK perlu ALTER**.
- ✅ `src/billing/limits.py::can_produce` = `PRODUCING_STATUSES {active,trial,grace}` → `suspended`/`blocked`/`deleted` **otomatis TAK produksi** (producer+publisher skip). **Tak perlu ubah gating.**
- ✅ `is_comp_account` (is_developer / discount≥100) sudah di-**exempt** di `renewal.py` (2 titik) — dipertahankan.
- 🆕 Transisi `suspended→blocked→deleted` + reaktivasi dari `blocked` = **BANGUN** di `renewal.py`.

**Prinsip:** login SELALU boleh sampai `deleted` (agar bisa bayar/aktif-lagi). `blocked` = akun terkunci (produksi mati, UI diarahkan ke bayar/kontak) tapi **belum** hapus data.

---

## 2. SEGMENTASI LEAD — dari perilaku NYATA (grounded)
Suhu dihitung sekali saat masuk `trial_expired` (atau saat `suspended`), disimpan `tenant_configs.lead_temp` (🆕).
| Suhu | Kriteria (sumber DB — ✅ ada) | Perlakuan |
|---|---|---|
| 🔥 Panas | Ada baris `production_runs`/`videos` utk tenant (sudah produksi saat trial) | Email + **notif Telegram admin** → outreach personal |
| 🌤️ Hangat | Ada `channels` ATAU `tenant_youtube_accounts`/`tenant_ai_accounts` tapi belum produksi | Email fokus bantuan onboarding + perpanjang trial |
| ❄️ Dingin | Nyaris tak setup | Sekuens ringan; jangan boros |

---

## 3. KONFIGURASI (NO-HARDCODE) — `app_config`, admin-editable (🆕 seed)
Muncul di **`/admin/app-config`** (System Config; catch-all "Lainnya" sudah jamin key baru tampil — ✅). Grup label baru "Pertumbuhan & Siklus-Hidup" via CFG_META (🆕).
| key | default | arti |
|---|---|---|
| `nurture_enabled` | 1 | master on/off mesin nurture |
| `nurture_trial_extend_days` | 3 | tuas "perpanjang trial 1-klik" (0 = matikan) |
| `winback_discount_pct` | 0 | diskon comeback bulan pertama (0 = matikan) |
| `winback_discount_valid_days` | 3 | masa berlaku diskon comeback (urgensi) |
| `nurture_step1..5_days` | 2,5,9,16,30 | offset hari tiap email nurture (int-only per key → no-hardcode) |
| `suspend_window_days` | 30 | lama `suspended` sebelum `blocked` |
| `suspend_dunning1..N_days` | 0,7,14,21,28 | offset email dunning selama suspended |
| `block_retention_days` | 30 | lama `blocked` sebelum `deleted` |
| `deletion_warn1..3_days` | 30,7,1 | H-x peringatan sebelum hapus |
| `s3_raw_purge_after_suspend_days` | 0 | hapus file video mentah S3 setelah masuk suspended (0 = segera) |

*(`app_config.value` = integer → daftar offset disimpan per-key int, bukan CSV. Harga/diskon nominal tetap `pricing_config`.)*
✅ Knob billing lama tetap: `trial_duration_days`(3)/`billing_grace_days`(7)/`trial_reminder_days_before`(1)/`renewal_reminder_days_before`(3)/`checkout_expiry_hours`(24).

---

## 4. DATA MODEL — DEEP DIVE (✅ada / 🆕bangun)

### 4.1 `tenant_configs` — kolom yang dipakai
✅ **ADA:** `subscription_status`, `plan_type`, `current_period_end`, `is_developer`, `discount_pct`, `display_handle`, `telegram_chat_id`, `trial_reminder_sent_at`, `renewal_reminder_sent_at`, `suspend_notified_at`.
🆕 **BANGUN (migrasi baru):** `lead_temp` (hot/warm/cold) · `nurture_step` (int, anti-dobel) · `nurture_last_sent_at` · `suspended_at` · `blocked_at` · `deletion_scheduled_at` · `raw_assets_purged_at` · `winback_offer_pct` · `winback_offer_expires_at` · `deletion_warn_sent` (int langkah peringatan terkirim).

### 4.2 CAKUPAN HAPUS DATA (tabel ber-`tenant_id`) — saat `deleted`
> **⚠️ DAFTAR INI WAJIB IKUT BERTAMBAH SETIAP TABEL BER-`tenant_id` BARU LAHIR.** Versi 3-Jul menulis
> "verified" lalu **membusuk diam-diam**: 4 tabel ber-`tenant_id` lahir SESUDAHNYA
> (`channel_decisions` migr 0172 · `video_retention_curves` migr 0171 · `commission_ledger` +
> `tenant_attribution` migr 0168) dan tak seorang pun memperbarui daftarnya ⇒ data tenant BERTAHAN
> setelah ia memakai hak hapusnya (temuan audit 2026-08-04). Kode PATUH pada daftar ini; jadi daftar
> yang basi = celah UU PDP yang tumbuh sendiri.
> **Penjaganya sekarang mesin, bukan ingatan:** `tests/test_purge_pdp_lengkap.py` MERAH bila ada tabel
> ber-`tenant_id` yang tak masuk salah satu kategori di bawah. Kategori = `_PURGE_TABLES` /
> `_KEEP_TABLES` / `_PENDING_OWNER_TABLES` di `src/billing/renewal.py`.

🗑️ **PURGE (WHERE tenant_id = X):** `channels`, `content_inventory`, `production_runs`, `pipeline_run_logs`, `pipeline_queue`, `video_analytics`, `videos`, `channel_insights`, `tts_delivery_samples`, `direct_jobs`, `tenant_ai_accounts` (kunci AI), `tenant_youtube_accounts` (SETELAH revoke), `support_tickets`, `email_outbox`, `music_library` (baris milik tenant), `voice_catalog` (HANYA baris ber-tenant_id; baris global tenant_id NULL JANGAN disentuh), `niche_requests` (pesanan tenant; niche publik 90hr milik katalog → jangan hapus), **`video_retention_curves`** (data per-video, sekeluarga `video_analytics` — ditambah 04-Agu), **`channel_decisions`** (jejak analis AI per-channel, sekeluarga `channel_insights` — ditambah 04-Agu).
📦 **SISAKAN (legal/anti-abuse, anonimkan bila perlu):** `payments` (bukti bayar/legal), `tenant_configs` (set `subscription_status='deleted'` + strip PII), `feedback_submissions` (insight lead — anonimkan email), **`commission_ledger`** (AGENT §5g.8 "seluruh ledger/payout DISIMPAN — kewajiban audit & pajak"; catatan uang ke PIHAK KETIGA/agen, bukan data tenant), **`tenant_attribution`** (AGENT §1.3/§2 atribusi "terkunci PERMANEN"/"selamanya" + "Masa komisi: SELAMANYA"; **dihapus = agen kehilangan komisi selamanya bila tenant kembali**, sebab akun login tenant TIDAK ikut dihapus dan atribusi hanya ditulis saat pendaftaran).
⚠️ Tabel global (tanpa tenant_id / tenant_id NULL) — `niches` base, `voice_catalog` global, `pricing_config`, `app_config`, `plan_limits` — **JANGAN disentuh**.
❓ **TERBUKA (belum diketok, JANGAN diputuskan sendiri):** hard-delete **TIDAK menghapus akun login** tenant (nol `deleteUser` di seluruh jalur) ⇒ **email tenant tetap tersimpan di `auth.users`** padahal ia meminta datanya dihapus. Mungkin DISENGAJA sebagai anti-abuse (penanda masa-coba ikut bertahan sebagai jangkar → cegah panen trial ulang), tapi **tak ada satu baris pun di dokumen mana pun yang menyatakannya** — jadi tak diketahui apakah rencana atau terlewat. Status: `SISA_KERJA_GO_LIVE.md` [B9].

### 4.3 Aset S3 (✅ mekanisme ada — `src/utils/s3_buffer.py`)
- Video mentah/perantara = MP4 di S3, key di **`content_inventory.s3_key`** (✅). Publisher hapus pasca-publish (`s3_buffer.delete`).
- Logo brand = `brand-logo/{tenant}/{channel}.png` (✅, dari upload-logo route).
- **Purge dini (suspended)** & **purge total (deleted)** = `s3_buffer.delete_prefix(prefix)` dipanggil **LANGSUNG** di `renewal.py` (prefix `{tenant}/` video mentah + `brand-logo/{tenant}/` logo). Helper `delete_prefix`/`delete`/`list_keys` ✅ ADA. *(Tak ada wrapper `purge_tenant_assets` — dibatalkan; `delete_prefix` dipakai langsung.)*

### 4.4 Token YouTube (✅ tabel ada — `tenant_youtube_accounts`)
- ✅ `google_refresh_token_enc`/`google_access_token_enc` (Fernet). `youtube_oauth.disconnect()` ✅ hapus baris DB + lepas channel — **TAPI TIDAK revoke ke Google**.
- 🆕 **BANGUN `revoke_token()`** (POST `https://oauth2.googleapis.com/revoke`) → dipanggil saat `deleted` SEBELUM hapus baris (UU PDP: jangan tinggalkan token hidup).

---

## 5. MESIN (BE) — SATU jalur, non-redundan
🆕 Perluas thread **`billing_renewal`** (`src/billing/renewal.py::sweep_subscriptions`) — **BUKAN thread baru**. Tambahan per sweep (idempotent, fail-soft per-tenant):
1. **trial_expired** → tangga `nurture_stepN_days`: kirim email langkah-berikut (varian by `lead_temp`), set `nurture_step`/`nurture_last_sent_at`. Hot → `notify_admin_hot_lead` (Telegram admin). Bila `winback_discount_pct>0` pada langkah diskon → set `winback_offer_pct`/`_expires_at`.
2. **grace→suspended** (✅ transisi ada di `next_status`) → set `suspended_at`; jalankan dunning `suspend_dunningN_days`.
3. **suspended** → bila `now-suspended_at ≥ s3_raw_purge_after_suspend_days` & `raw_assets_purged_at` kosong → `purge_tenant_assets(raw_only=True)` + set `raw_assets_purged_at`. Terus dunning+winback.
4. **suspended→blocked** bila `now-suspended_at ≥ suspend_window_days` → set `blocked_at` + `deletion_scheduled_at = now + block_retention_days`; email "akun dikunci + dihapus {tgl}".
5. **blocked** → kirim peringatan `deletion_warnN_days` (H-30/7/1) via `deletion_warn_sent` (anti-dobel).
6. **blocked→deleted** bila `now ≥ deletion_scheduled_at` → **hard delete** (§4.2 + §4.3 + revoke §4.4) → set `deleted`.
- ✅ Reaktivasi (bayar) `suspended`/`blocked` = jalur pembayaran SUDAH ada (`midtrans._apply_settlement` set `active` + reset penanda). 🆕 tambah reset penanda lifecycle (`suspended_at`/`blocked_at`/`deletion_scheduled_at`/`nurture_step` → null) saat aktivasi.

---

## 6. EMAIL + TELEGRAM (grounded)
✅ **ADA** (`src/utils/email.py`, dwibahasa, config-driven, fail-soft): `notify_trial_ending`, `notify_trial_lapse`, `notify_renewal_reminder`, `notify_suspend_warning`, `notify_suspended`, `notify_payment_receipt`.
🆕 **BANGUN (dwibahasa):** `notify_nurture_step(step, lead_temp, offer?)`, `notify_reactivation_offer`, `notify_account_blocked(deletion_date)`, `notify_deletion_warning(days_left, date)`, `notify_data_deleted`.
✅ **Telegram admin — TERPASANG (2026-07-03):** `notify_admin(text)` (`telegram_notifier.py:146`) kirim hot-lead ke admin. chat_id dari **`company_profile.admin_telegram_chat_id`** (migr 0114, editable owner via `/admin/company-profile`) + fallback env `ADMIN_TELEGRAM_CHAT_ID`. Notif per-tenant tetap dari `tenant_configs.telegram_chat_id` (terpisah, sengaja tanpa fallback sistem).
- Link email: perpanjang/aktif = `/reactivate?token=`; feedback 1-klik = `/feedback?ref=<tenant>&source=…&reason=<key>` (✅ `?ref`/`?source` sudah didukung; 🆕 prefill `?reason`).

---

## 7. ENDPOINT (🆕 bangun)
- `POST /api/lifecycle/reactivate?token=` → verifikasi token HMAC (pola `OAUTH_STATE_SECRET` ✅ ada di `youtube_oauth.sign_state`/`verify_state`) → perpanjang trial (`nurture_trial_extend_days`) ATAU buka checkout Snap (✅ `/api/billing/checkout`).
- `/api/feedback` (✅ ADA) → 1-klik reason dari email (page prefill `?reason=`).
- Diskon comeback: 🆕 di `midtrans.snap_create_transaction` — bila `winback_offer_pct` aktif & belum kedaluwarsa, terapkan potongan (harga dari `pricing_config`, potongan dari kolom offer) → order `payments` mencerminkan harga diskon.

---

## 8. FRONTEND (grounded — reuse, no elemen liar)
**Tenant:**
- ✅ **Banner** `components/app-shell.tsx` (baris 68–187) sudah tangani trial/trial_expired/grace/suspended (warna+pesan+CTA dwibahasa). 🆕 tambah varian **`blocked`** (pesan "akun dikunci, dihapus {tgl}" + hitung-mundur `deletion_scheduled_at` + CTA "Aktifkan").
- 🆕 **`/reactivate`** (publik, token) — 1-klik aktif-lagi / perpanjang trial (reuse kelas `card/btn`).
- ✅ **Billing** `(app)/billing/page.tsx` — 🆕 tampilkan diskon comeback aktif + hitung-mundur bila `winback_offer` ada.
- ✅ **`/feedback`** `app/feedback/page.tsx` — 🆕 prefill `?reason=` (REASONS sudah ada) untuk feedback 1-klik.

**Admin:**
- ✅ **`/admin/tenants`** = tempat **"Leads"** (trial_expired) + modal Comp/Diskon + status per-tenant. 🆕 tambah kolom **suhu lead** + tahap sekuens + timestamp lifecycle (`suspended_at`/`blocked_at`/`deletion_scheduled_at`) + filter + **✅ aksi manual (SELESAI 2026-07-03): Perpanjang trial / Undur hapus / Aktifkan-bersih / Hapus-permanen** (tombol di drawer + ConfirmDialog + reset kanonik + admin_audit); ekspor-manual ditunda. **Reuse halaman ini — JANGAN board baru.**
- ✅ **Kirim email manual** (tenant detail — `sendEmail` → antrean `email_outbox` → worker): **DIPERTAHANKAN** sebagai alat **concierge personal** (khusus/ad-hoc). **Komplementer, BUKAN diganti** nurture otomatis. Justru dipakai untuk follow-up **lead PANAS** setelah alert Telegram (owner: "email + Telegram admin → outreach personal"). Nurture = otomatis massal per-tahap; manual = personal 1-on-1. Dua tujuan beda → tak redundan.
- ✅ **System Config** `/admin/app-config` — 🆕 knob §3 (label grup baru via CFG_META).
- ✅ **`/admin/feedback`** — insight churn (sudah ada).

---

## 9. KEPATUHAN & KEAMANAN (world-class)
- **UU PDP:** hapus terjadwal + hak hapus atas permintaan; **cabut refresh-token YouTube** saat delete (§4.4).
- **Peringatan berulang + tanggal pasti** (H-30/7/1) — nol penghapusan diam-diam.
- **Ekspor manual** (keputusan owner: self-service ditunda) — admin sediakan arsip bila diminta.
- **Sisakan minimal** pasca-delete (payments + email-hash anti-abuse) — cegah abuse trial berulang.
- **Idempotent + fail-soft**: email/purge gagal 1 tenant tak stop sweep; aksi admin auditable (`admin_audit`).

---

## 10. PETA FILE (rujukan — ✅sentuh / 🆕baru)
```
DB     migrasi baru: kolom lifecycle §4.1 + seed knob §3 (+ CFG_META label FE)
BE     src/billing/renewal.py         ✅→🆕 perluas sweep (nurture + suspended→blocked→deleted)
       src/utils/email.py             ✅→🆕 5 template baru (dwibahasa)
       src/utils/telegram_notifier.py ✅ notify_admin → company_profile.admin_telegram_chat_id (migr 0114, fallback env)
       src/utils/s3_buffer.py         ✅ delete_prefix/delete/list_keys (dipanggil langsung di renewal.py — tanpa wrapper)
       src/billing/youtube_oauth.py   ✅ (disconnect) → 🆕 revoke_token (Google revoke)
       src/billing/midtrans.py        ✅ _apply_settlement/snap_create → 🆕 diskon comeback + reset penanda lifecycle
       src/billing/limits.py          ✅ can_produce (blocked/deleted otomatis non-producing — TAK diubah)
FE     apps/web/src/components/app-shell.tsx               ✅→🆕 banner blocked
       apps/web/src/app/reactivate/page.tsx                🆕 (token 1-klik)
       apps/web/src/app/feedback/page.tsx                  ✅→🆕 prefill ?reason
       apps/web/src/app/(app)/billing/page.tsx             ✅→🆕 diskon+countdown
       apps/web/src/app/admin/(panel)/tenants/page.tsx     ✅→🆕 suhu/tahap/timestamp/filter/aksi (Leads)
       apps/web/src/app/admin/(panel)/app-config/page.tsx  ✅→🆕 CFG_META grup lifecycle
       apps/web/src/app/api/lifecycle/reactivate/route.ts  🆕
       apps/web/src/app/api/admin/tenants/[id]/lifecycle/route.ts    🆕 extend/postpone/reactivate-clean (+admin_audit)
       apps/web/src/app/api/admin/tenants/[id]/hard-delete/route.ts  🆕 → vault → webhook internal
       src/billing/webhook_app.py    🆕 /api/admin/lifecycle/hard-delete (internal) → _hard_delete_tenant
INFRA  .env / app_config: ADMIN_TELEGRAM_CHAT_ID (🆕)
```

---

## 11. PLAN vs REALISASI (living tracker) — ⬜ belum · 🟡 sebagian · ✅ selesai+validasi
| # | Item | Lapisan | Realisasi |
|---|---|---|---|
| 1 | Migrasi kolom lifecycle §4.1 (tenant_configs) — no ALTER constraint | DB | ✅ migr `0113` applied+verified DB live |
| 2 | Seed knob `app_config` §3 + CFG_META grup "Pertumbuhan & Siklus-Hidup" | DB+FE admin | ✅ DEPLOYED — 20 knob seeded (0113) + grup+label ramah di System Config (build+live) |
| 3 | Hitung `lead_temp` dari production_runs/videos/channels/accounts | BE | ✅ DEPLOYED `renewal._compute_lead_temp` (unit-tested + sweep live bersih) |
| 4 | Sekuens nurture trial-lapse (tangga email + varian suhu, anti-dobel) | BE | ✅ DEPLOYED — sweep live `nurtured=3` (tangga+anti-dobel unit-tested) |
| 5 | 5 template email dwibahasa baru (§6) | BE | ✅ DEPLOYED (`email.py` 5 fungsi; import OK) |
| 6 | `notify_admin` Telegram + `ADMIN_TELEGRAM_CHAT_ID` (hot-lead) | BE+infra | ✅ DEPLOYED (kode live). ⚠️ set `ADMIN_TELEGRAM_CHAT_ID` di `.env` VPS utk aktifkan alert (kini skip aman) |
| 7 | Transisi suspended→blocked→deleted + reset penanda reaktivasi | BE | ✅ DEPLOYED (`renewal.sweep` §4/§5 + `midtrans` reset; `next_status` unit-tested; sweep live `changed=0 deleted=0`) |
| 8 | Purge S3 (raw dini + total) | BE | ✅ DEPLOYED (`s3_buffer.delete_prefix` + guard anti-hapus-semua) |
| 9 | `revoke_token` YouTube (Google revoke) saat delete | BE | ✅ DEPLOYED (`youtube_oauth.revoke_tenant_tokens`) |
| 10 | Hard-delete scope §4.2 (purge/sisakan/anonim) — idempotent | BE | ✅ DEPLOYED (`renewal._hard_delete_tenant`, 17 tabel anak→induk, KEEP payments) |
| 11 | Diskon comeback di `snap_create_transaction` (`winback_offer`) | BE | ✅ DEPLOYED (`midtrans._winback_discount` + tampil di Billing) |
| 12 | Endpoint token `/api/lifecycle/reactivate` (+ feedback prefill ?reason) | BE+FE | ✅ DEPLOYED — LIVE: GET 405, POST token-palsu→400 rapi (Next→vault→webhook→verify_state); /feedback ?reason |
| 13 | FE tenant: banner `blocked` + `/reactivate` + diskon/countdown Billing | FE tenant | ✅ DEPLOYED — LIVE: `/reactivate` 200; banner blocked+countdown; badge status blocked; diskon di Billing |
| 14 | FE admin: `/admin/tenants` suhu/tahap/timestamp + tombol aksi-manual | FE admin | ✅ **DONE 2026-07-03** (`6a5f798`) — visibilitas (badge suhu lead + timestamp + kpi.blocked) + **tombol aksi-manual**: Perpanjang trial / Undur hapus / Aktifkan-bersih / Hapus-permanen (route `/api/admin/tenants/[id]/lifecycle`+`/hard-delete`, ConfirmDialog, reset kanonik, admin_audit). Extend **terbukti live** (klik owner→DB berubah); reaktivasi/undur/hapus terpasang+ter-gate (uji-klik nyata nunggu akun terkunci). Footgun Suspend@blocked diperbaiki |
| 15 | Validasi (build+py_compile+unit-test) + deploy 1× | — | ✅ DONE — py_compile 6 file · npm build exit 0 · unit-test logika LOLOS · 3 service active · endpoint live |

### Changelog
- **2026-07-03** — **Item 14 SELESAI + deployed** (`6a5f798`): tombol aksi-manual admin `/admin/tenants` (Perpanjang trial / Undur hapus / Aktifkan-bersih / Hapus-permanen) + route lifecycle/hard-delete + webhook internal `_hard_delete_tenant` + footgun Suspend@blocked. **Telegram admin di-wire** ke `company_profile.admin_telegram_chat_id` (migr 0114, `603640e`). Dokumen **direkonsiliasi ke realita** via 2 verifikator (§4.3/§6/§8/§10/§11 diperbaiki). **CLOSED → status di `SISA_KERJA_GO_LIVE.md`.**
- **2026-07-02** — dibuat sebagai **ARCHITECTURE** (rename dari …_PLAN), di-*ground* pada deep-dive DB+BE+FE nyata.
- **2026-07-02** — **BUILD + DEPLOYED + LIVE** (commit `871986b`→`db589b1`, v2-backend). Migr 0113 applied; BE (`renewal`/`email`/
  `telegram`/`s3_buffer`/`youtube_oauth`/`midtrans`/`webhook_app`) + FE (banner blocked/`/reactivate`/billing diskon/app-config
  label/admin lead_temp) deployed; worker restart → sweep lifecycle live bersih (`8 tenant · nurtured=3 · deleted=0 · comp 2`);
  endpoint reactivate live (405/400 rapi). Validasi: py_compile 6 file + npm build exit 0 + unit-test state-machine/tangga/bitmask LOLOS.
  **Follow-up tercatat:** item 14 tombol aksi-manual admin; set `ADMIN_TELEGRAM_CHAT_ID` env; e2e siklus penuh lintas-waktu (data-gated, pakai config dipercepat).
- **2026-07-02 — E2E TERVALIDASI (tenant dummy, izin owner; sweep asli VPS + SMTP produksi; data direstore+dibersihkan):**
  ✅ **Email nurture** step-1 terkirim ke effi (dwibahasa). ✅ **Reaktivasi 1-klik + extend-trial**: effi trial_expired→trial, period_end +3 hari (link ber-token dari email diklik). ✅ **Dunning + suspended→blocked**: kumala terima 2 email ("Reactivate"/"Account locked") + transisi blocked (deletion +30hr). ✅ **Hard-delete** (tenant throwaway ber-seed): PURGE content_inventory/production_runs/email_outbox=0 · KEEP payments · feedback ANONIM (email null) · tenant_configs=deleted+PII stripped · revoke token + purge S3 jalan tanpa error. ✅ **Diskon comeback**: pro 349rb→244.3rb (−30%) diterima Midtrans sandbox.
  ⚠️ **Belum diuji dgn DATA nyata** (jalur jalan tanpa error tapi set kosong): revoke YouTube token pada akun ber-token nyata; purge S3 pada aset nyata; email deletion_warning H-30/7/1 (throwaway di-set warn=terkirim). Non-blocker.
