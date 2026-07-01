# 🔄 LIFECYCLE & NURTURE PLAN — MesinViral

> **Sumber kebenaran TUNGGAL** untuk *tindak-lanjut siklus-hidup tenant*: menyelamatkan **trial yang lapsed** +
> menagih/menyelamatkan **pelanggan berbayar yang berhenti (suspended)** + **blokir & hapus data** yang benar-benar
> tak kembali (agar tak membebani storage/sistem). **SATU mesin** (bukan dua) — segmen berbeda, jalur sama.
> Dibuat 2026-07-02. Prinsip: **NO-HARDCODE** (semua timing/insentif = saklar admin di `app_config`) + **world-class** +
> **dwibahasa EN/ID** + **patuh UU PDP** (hak data + cabut token YouTube saat hapus).
>
> **🔗 Rantai kanonik:** backlog/status = **`SISA_KERJA_GO_LIVE.md`** (HUB — item ini = **[B9]**; terkait [B8] /feedback, [D1] funnel). Dokumen ini **melanjutkan** **`PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`** (gate berhenti di `suspended`; di sini `suspended→blocked→deleted` + nurture). SATU mesin (`renewal.py`), non-redundan. Selaras `ONBOARDING_FUNNEL_PLAN.md` ([D1]).
> **Bukan pemblokir jualan** — pengoptimal konversi/biaya (bangun setelah [A1] go-live).

---

## 0. Keputusan owner (TERKUNCI 2026-07-01/02) — semua default, adjustable di admin

| Keputusan | Nilai (default) | Sumber |
|---|---|---|
| Insentif comeback = **saklar admin** (3 tuas) | trial-extend **ON**, diskon **OFF** (angka siap), pesan-nilai **selalu ON** | owner |
| Kanal lead PANAS | **Email + notif admin ke Telegram** (concierge manual) | owner |
| Panjang sekuens nurture trial-lapse | **Standar 4–5 email, ~2–3 minggu** | owner |
| Masa **suspended** (data utuh, 1-klik aktif-lagi) | **30 hari** | owner |
| Retensi setelah **blocked** sebelum hapus | **30 hari** (peringatan H-30/7/1) | owner |
| Hapus DINI file video mentah S3 saat suspended | **YA** (video aman di YouTube; simpan config/insight) | owner |
| Tombol "Unduh data saya" self-service | **NANTI/manual** (admin bantu bila diminta) — tak dibangun sekarang | owner |

---

## 1. STATE MACHINE — diperluas dari gate langganan

```
trial ──lewat──▶ trial_expired ─────(nurture 4–5 email, ~2–3 mgg)─────┐
                   │  (LEAD panas/hangat/dingin)                        │ bayar/upgrade
                   └───────────────────────────────────────────────────┼──▶ active
active ─lewat─▶ grace(7h,jalan) ─lewat─▶ suspended ──30h──▶ blocked ──30h──▶ DELETED
                                          │ stop produksi    │ akun terkunci   purge S3+DB
                                          │ login+1klik aktif │ jadwal-hapus    + cabut token YT
                                          │ data UTUH         │ peringatan       + sisakan
                                          │ dunning+winback   │ H-30/7/1         record legal min.
                                          └─bayar→active◀─────┴─bayar→active◀────(sblm deleted)
comp/developer = EXEMPT dari SELURUH alur ini.
```

**Status baru yang dibutuhkan** (perluas `tenant_configs.subscription_status`):
- `blocked` — akun terkunci, produksi mati, login hanya ke halaman bayar/kontak; deletion terjadwal.
- `deleted` — data konten dihapus; baris tenant disisakan minimal (legal/anti-abuse), status final.
- ⚠️ **Cek CHECK-constraint** `subscription_status` sebelum migrasi (mungkin perlu `ALTER` daftar nilai).

**Reaktivasi** (bayar) berlaku di SEMUA state non-final (`trial_expired`/`grace`/`suspended`/`blocked`) sampai `deleted`.

---

## 2. SEGMENTASI LEAD (kunci efektivitas) — dihitung dari perilaku nyata
| Suhu | Kriteria (dari DB) | Perlakuan |
|---|---|---|
| 🔥 Panas | Sudah **produksi ≥1 video** saat trial (`production_runs`/`videos`) | Email + **notif Telegram admin** → outreach personal |
| 🌤️ Hangat | Connect channel/kunci tapi **belum produksi** | Email fokus **bantuan onboarding** + tawaran perpanjang trial |
| ❄️ Dingin | Nyaris tak setup | Sekuens ringan; jangan boros |

Suhu disimpan `lead_temp` (dihitung sekali saat masuk trial_expired) → dipakai memilih varian email + trigger Telegram.

---

## 3. KONFIGURASI (NO-HARDCODE) — `app_config`, admin-editable
| key | default | arti |
|---|---|---|
| `nurture_enabled` | 1 | master on/off seluruh mesin nurture |
| `nurture_trial_extend_days` | 3 | tuas "perpanjang trial 1-klik" (0 = matikan) |
| `winback_discount_pct` | 0 | diskon comeback bulan pertama (0 = matikan) |
| `winback_discount_valid_days` | 3 | masa berlaku diskon comeback (urgensi) |
| `nurture_steps_days` | 2,5,9,16,30 | offset hari email nurture trial-lapse (dari lapse) *(disimpan multi-key bila perlu int-only)* |
| `suspend_window_days` | 30 | lama `suspended` sebelum `blocked` |
| `suspend_dunning_days` | 0,7,14,21,28 | offset email dunning selama suspended |
| `block_retention_days` | 30 | lama `blocked` sebelum `deleted` |
| `deletion_warn_days` | 30,7,1 | H-x peringatan sebelum hapus |
| `s3_raw_purge_after_suspend_days` | 0 | hapus file video mentah S3 setelah masuk suspended (0 = segera) |

*(Angka default = keputusan §0. Semua muncul di System Configuration; catch-all "Lainnya" sudah menjamin key baru tampil.)*
**Harga/diskon** tetap lewat `pricing_config`; diskon comeback diterapkan di `midtrans.snap_create_transaction`.

Penanda anti-dobel di `tenant_configs`: `lead_temp`, `nurture_step`, `nurture_last_sent_at`, `suspended_at`,
`blocked_at`, `deletion_scheduled_at`, `winback_offer_pct`, `winback_offer_expires_at`, `raw_assets_purged_at`.

---

## 4. MESIN (BE, worker) — SATU jalur, non-redundan
Perluas thread **`billing_renewal`** (`src/billing/renewal.py`) — BUKAN thread baru (hindari duplikasi). Tiap sweep:
1. **trial_expired** → jalankan tangga `nurture_steps_days`: pilih email per-langkah (varian by `lead_temp`), set `nurture_step`/`nurture_last_sent_at`. Hot → `notify_admin_hot_lead` (Telegram). Anti-dobel via `nurture_step`.
2. **grace→suspended** (sudah ada) → set `suspended_at`; kirim dunning sesuai `suspend_dunning_days`.
3. **suspended** → bila `now - suspended_at ≥ s3_raw_purge_after_suspend_days` & belum `raw_assets_purged_at` → **purge file video mentah S3** (helper `purge_raw_assets(tenant)`), set `raw_assets_purged_at`. Terus dunning+winback.
4. **suspended → blocked** bila `now - suspended_at ≥ suspend_window_days` → set `blocked_at` + `deletion_scheduled_at = now + block_retention_days`; email "akun dikunci + dihapus pada {tgl}".
5. **blocked** → kirim peringatan `deletion_warn_days` (H-30/7/1).
6. **blocked → deleted** bila `now ≥ deletion_scheduled_at` → **hard delete**: hapus konten DB (videos/runs/inventory/insights) + sisa S3 + **cabut token YouTube** (revoke OAuth) + kosongkan kredensial; set `deleted`; sisakan baris minimal (billing/legal, di-anonim bila perlu). Idempotent, fail-soft per tenant.

**Email dwibahasa baru** (`src/utils/email.py`): `notify_nurture_step(step, lead_temp, offer?)`, `notify_reactivation_offer`,
`notify_account_blocked(deletion_date)`, `notify_deletion_warning(days_left, deletion_date)`, `notify_data_deleted`.
**Telegram admin**: `notify_admin_hot_lead(tenant, signals)`.

**Endpoint publik token-based (tanpa login berbelit):**
- `POST /api/lifecycle/reactivate?token=` → perpanjang trial (`nurture_trial_extend_days`) ATAU buka checkout.
- `POST /api/feedback` (sudah ada) → terima alasan 1-klik (`?reason=`).
Token = HMAC ref tenant (pola `OAUTH_STATE_SECRET`/`MV_INTERNAL_SECRET`), kedaluwarsa.

---

## 5. FRONTEND
**Tenant:**
- Banner in-app sudah ada (status+sisa hari+Upgrade) → tambah varian **blocked** ("akun dikunci, dihapus pada {tgl}, aktifkan lagi").
- Halaman **`/reactivate`** (publik, token) — 1-klik aktif-lagi / perpanjang trial.
- **Billing** — tampilkan **diskon comeback** aktif + hitung mundur bila `winback_offer` ada.
- **`/feedback`** (sudah ada) — dukung `?reason=` prefilled (feedback 1-klik dari email).

**Admin:**
- **Leads board** (`/admin`, Phase 10.1) ditingkatkan — kolom **suhu lead** + tahap sekuens + status follow-up + filter; aksi manual "kirim penawaran"/"tandai dihubungi". Reuse pola yang ada (jangan subsistem baru).
- **System Configuration** — knob §3 (label ramah grup "Pertumbuhan & Siklus-Hidup").
- **Tenant detail** — tampil lifecycle (suspended_at/blocked_at/deletion_scheduled_at) + tombol admin (perpanjang/undur hapus/hapus-sekarang/ekspor-manual).

---

## 6. KEPATUHAN & KEAMANAN (world-class, wajib)
- **UU PDP:** hapus data atas jadwal + hak hapus atas permintaan; **cabut refresh-token YouTube** saat delete (jangan tinggalkan token hidup).
- **Peringatan berulang + tanggal pasti** sebelum hapus (H-30/7/1) — nol penghapusan diam-diam.
- **Ekspor manual** (owner pilih): bila tenant minta sebelum hapus, admin sediakan arsip (bukan self-service dulu).
- **Sisakan minimal** pasca-delete: billing/legal + sinyal anti-abuse (email hash) — cegah abuse trial berulang.
- **Idempotent & fail-soft**: kegagalan email/purge satu tenant tak menghentikan sweep; log auditable.

---

## 7. PLAN vs REALISASI (living tracker) — ⬜ belum · 🟡 sebagian · ✅ selesai+validasi
| # | Item | Lapisan | Realisasi |
|---|---|---|---|
| 1 | Migrasi: status `blocked`/`deleted` (cek CHECK) + kolom penanda (§3) | DB | ⬜ |
| 2 | Knob `app_config` (§3) + seed + CFG_META grup "Pertumbuhan & Siklus-Hidup" | DB+FE admin | ⬜ |
| 3 | Segmentasi `lead_temp` (hitung dari production_runs/channels) | BE | ⬜ |
| 4 | Sekuens nurture trial-lapse (tangga email + varian suhu, anti-dobel) | BE | ⬜ |
| 5 | Email dwibahasa baru + Telegram hot-lead | BE | ⬜ |
| 6 | Dunning suspended + transisi suspended→blocked→deleted | BE | ⬜ |
| 7 | Purge dini file video mentah S3 (`purge_raw_assets`) | BE | ⬜ |
| 8 | Hard-delete + **cabut token YouTube** + sisakan record minimal | BE | ⬜ |
| 9 | Diskon comeback diterapkan di checkout (`snap_create_transaction`) | BE | ⬜ |
| 10 | Endpoint token `/api/lifecycle/reactivate` + feedback 1-klik `?reason=` | BE+FE | ⬜ |
| 11 | FE tenant: `/reactivate`, banner blocked, diskon+countdown di Billing | FE tenant | ⬜ |
| 12 | FE admin: Leads board (suhu/tahap/filter/aksi) + lifecycle di tenant detail | FE admin | ⬜ |
| 13 | Validasi (build+py_compile+e2e sandbox: sekuens dipercepat via config) + deploy 1× | — | ⬜ |

### Changelog
- **2026-07-02** — dibuat. Keputusan owner §0 terkunci (nurture trial-lapse + siklus suspended→blocked→deleted 30+30 hari,
  purge S3 dini YA, ekspor self-service NANTI). Belum mulai build (nunggu restu + urutan vs [A1] go-live).
