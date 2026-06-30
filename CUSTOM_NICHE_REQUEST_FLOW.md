# Alur Bisnis Custom Niche Request — Sumber Kebenaran Tunggal

> **Status:** PLAN final (disetujui owner 2026-06-30) + Realisasi BERTAHAP. Living doc — update kolom REALISASI saat dikerjakan.
> **Ground truth = kode + DB live.** Bila doc ini ≠ kode, kode menang → update doc.
> **🔌 PENTING:** Bagian **§7 (Pembayaran)** memuat integrasi Midtrans yang **SENGAJA DITUNDA** — **WAJIB dieksekusi saat finalisasi pembayaran sewa tenant** (lihat `PROGRESS.md` §GATE CUTOVER B2). Jangan sampai terlewat.
> Selaras: [[decisions_niche_model]] · [[decisions_niche_owns_content_config]] · `src/billing/midtrans.py` (Snap subscription) · tabel `payments` · `src/config/app_config.py`.

---

## §1. Ringkasan
Tenant memesan niche custom (DNA dibuat khusus oleh tim). Dua jenis (harga dari `pricing_config`, **no-hardcode**):
- **Public (90 hari eksklusif)** — `price_key = custom_niche_public_90d` (default Rp299rb). Eksklusif 90 hari → lalu masuk katalog umum.
- **Privat permanen** — `price_key = custom_niche_private` (default Rp1.499rb). Tak pernah publik.

Alur A-Z: **Diajukan → (batal/tolak) / Menunggu pembayaran → Diproses → Diserahkan (Evaluasi) → Selesai.**

## §2. Aktor & entitas
- **Tenant** (Pustaka Niche `/niches`): mengajukan, melihat riwayat+status, membatalkan (saat pending), evaluasi (terima/minta-revisi).
- **Admin** (`/admin/niches`): tolak / terima-untuk-diproses / tandai-lunas (interim) / serahkan.
- **Tabel:** `niche_requests` (pesanan+status), `niches` (niche hasil), `pricing_config` (harga), `payments` (pembayaran — dipakai saat Midtrans disambung), `app_config` (durasi evaluasi), `admin_audit` (jejak admin).

## §3. Status & transisi (lifecycle)
| Status | Arti | Aktor & aksi keluar |
|---|---|---|
| `pending` | Diajukan, belum diproses admin | Tenant **Batalkan** → `cancelled` · Admin **Tolak** → `rejected` · Admin **Terima** → `awaiting_payment` |
| `cancelled` | Dibatalkan tenant (terminal) | — |
| `rejected` | Ditolak admin (terminal, + `admin_note`) | — |
| `awaiting_payment` | Disetujui diproses; menunggu bayar (📧 tagihan) | Bayar (lihat §7) → `in_progress` |
| `in_progress` | Sudah dibayar; admin membangun niche DNA. **Baris `niches` DIBUAT di sini dgn `is_active=false`** (+`exclusive_to`=tenant) → tenant lihat "Belum aktif" di Pustaka. (📧 pembayaran diterima) | Admin **Serahkan** → `delivered` |
| `delivered` | Admin set **`niches.is_active=true`** + lampirkan tautan video contoh (`delivery_note`); **masa Evaluasi mulai** (`delivered_at`, 📧 serah-terima) | Tenant **Terima** → `closed` · Tenant **Minta perbaikan** (`revision_note`, niche tetap aktif, DNA diperbaiki di tempat) → `in_progress` · **N hari lewat tanpa respons** → `closed` (auto) |
| `closed` | Selesai (terminal, `closed_at`, 📧 penutup) | — |

> CHECK lama (`pending/approved/rejected/live`) DIGANTI set di atas (migrasi). `approved`/`live` lama dipensiunkan.

## §3.1 Di mana niche disimpan · cara review · apakah masuk pool (jawaban desain, owner 2026-06-30)
- **SATU tabel — `niches` yang SAMA** (TIDAK ada tabel staging terpisah). Niche custom yang sedang dibangun = baris `niches` dgn **`is_active=false`** + `exclusive_to=tenant`. Saat diserahkan → `is_active=true`. (Konsisten dgn kondisi nyata: `imunitas_tubuh` = is_active=false = sedang disiapkan.) Baris niche **dibuat saat `in_progress`** (sudah dibayar) — bukan sebelumnya. Tenant melihatnya berlabel **"Belum aktif"** di Pustaka (sudah ada).
  - ⚠️ Ubah route admin: sekarang `approve` membuat niche `is_active=true` LANGSUNG → di model baru, niche dibuat `is_active=false` (in_progress) lalu di-`true`-kan saat **Serahkan**.
- **Cara tenant REVIEW (masa Evaluasi):** niche sudah aktif & tampil penuh → tenant buka **detail niche** (deskripsi/contoh topik/hashtag/gaya/musik/visual/alur) untuk menilai sesuai brief. Admin **melampirkan tautan VIDEO CONTOH** saat serah-terima (`delivery_note`; dari fitur "Test niche" admin = video privat) agar tenant menilai **hasil NYATA**, bukan cuma teks. Lalu tenant **Terima & Selesaikan** ATAU **Minta perbaikan** (catatan → balik ke admin; niche tetap aktif, DNA diperbaiki di tempat).
- **Delivered TIDAK otomatis masuk `niche_pool`.** Pool = per-CHANNEL & pilihan sengaja tenant (1 tenant bisa banyak channel). Saat diserahkan, niche jadi **TERSEDIA** (masuk entitlement → muncul di Pustaka + bisa dipilih di Channel Detail), TAPI **tenant yang memasangnya** ke channel pilihannya (tombol "Pakai di channel →"). Tak ada auto-assign.

## §4. Aturan pembatalan
- Tenant **hanya bisa membatalkan saat status = `pending`** (belum di-followup admin). Setelah masuk `awaiting_payment`+ → tak bisa batal sendiri (hubungi admin).
- Implementasi aman: RPC `cancel_niche_request` (SECURITY DEFINER, set `cancelled` HANYA bila pemilik + status `pending`). **Bukan** lewat UPDATE/DELETE langsung (RLS tenant tetap read-only + insert).

## §5. Masa Evaluasi (config-driven, well-informed)
- Setelah `delivered`, tenant punya **N hari** untuk minta perbaikan. **N = `app_config.niche_eval_window_days`** (default **3**), **admin-editable via panel System Configuration** (pola identik `trial_duration_days` — `src/config/app_config.py::get_int`). **TIDAK hardcode.**
- **Well-informed (WAJIB):** di Pustaka Niche/riwayat tampil **hitung mundur** ("Sisa evaluasi: X hari") + 2 tombol jelas: **Terima & Selesaikan** (langsung `closed`) dan **Minta perbaikan**. Email serah-terima menjelaskan masa evaluasi + ajakan segera cek. Email **pengingat H-1** sebelum auto-close.
- **Auto-close:** worker menutup `delivered` yang lewat N hari → `closed` (numpang thread worker yang ada, mis. cadence harian seperti `renewal`).

## §6. Email (pakai `src/utils/email.py` + pola `notify_*`; fail-soft)
| Titik | Email |
|---|---|
| `awaiting_payment` | **Tagihan**: jenis niche, jumlah (dari pricing_config), cara bayar |
| `in_progress` (bayar diterima) | **Konfirmasi pembayaran** + estimasi pengerjaan |
| `delivered` | **Serah-terima**: niche siap + masa evaluasi N hari + ajakan cek & Terima |
| H-1 evaluasi | **Pengingat** sebelum auto-close |
| `closed` | **Penutup** transaksi |

## §7. 🔌 PEMBAYARAN — pondasi SEKARANG vs integrasi Midtrans DITUNDA
**Keputusan owner 2026-06-30:** pakai **sistem pembayaran aplikasi (Midtrans Snap)** yang sama dengan **sewa/langganan tenant**. Integrasi **live ditunda**, dikerjakan **berbarengan** dengan finalisasi pembayaran sewa. **Pondasi disiapkan sekarang** agar tinggal colok.

**Disiapkan SEKARANG (pondasi):**
- Status `awaiting_payment` + kolom `paid_at` + `order_id` (link ke `payments.order_id`, null dulu) di `niche_requests`.
- Harga sudah dari `pricing_config` (`price_key`). UI jujur: *"Pesanan diproses tim termasuk pembayaran"* — **bukan** "beli sekarang".
- **Interim (concierge):** admin **Tandai lunas** manual (set `paid_at`, `awaiting_payment`→`in_progress`) — sambil menunggu Midtrans.

**🔌 DITUNDA — WAJIB DIKERJAKAN SAAT INTEGRASI MIDTRANS (PROGRESS.md §GATE CUTOVER B2 / Phase 8b):**
1. Buat order Midtrans Snap untuk add-on: reuse `src/billing/midtrans.py::snap_create_transaction` (generalisasi dari plan_type → add-on `price_key`; insert `payments` kategori add-on dgn `order_id`).
2. `niche_requests.order_id` ← order_id Midtrans; status `awaiting_payment`.
3. `handle_notification` (webhook): saat settlement add-on → set `niche_requests.paid_at` + `awaiting_payment`→`in_progress` **otomatis** (ganti "Tandai lunas" manual).
4. Tombol bayar di Pustaka Niche → Snap redirect (saat checkout sewa sudah live).
5. Hapus/teruskan jalur concierge sesuai kebutuhan.
> **Tanpa langkah ini, custom niche TAK tertagih otomatis.** Cross-check di GATE CUTOVER B2 sebelum go-live pembayaran.

## §8. Perubahan DB (rencana — migrasi saat build)
- `niche_requests`: ganti CHECK status → set §3; tambah `paid_at timestamptz`, `order_id text`, `delivered_at timestamptz`, `closed_at timestamptz`, `revision_note text`, `delivery_note text` (catatan serah-terima + tautan video contoh). (`price_key`, `admin_note`, `niche_id` sudah ada.)
- `niches`: tak ada kolom baru. **Ubah perilaku route admin**: niche dibuat `is_active=false` saat `in_progress`, di-`true`-kan saat `delivered` (lihat §3.1). Niche custom = baris biasa di `niches` (TIDAK ada tabel terpisah).
- RPC `cancel_niche_request(p_request_id)` (SECURITY DEFINER; pemilik + status pending → cancelled).
- `app_config`: seed `niche_eval_window_days` = 3 (admin-editable).
- (Saat Midtrans) generalisasi `payments` utk kategori add-on / link order.

## §9. Frontend (rencana)
- **Tenant — Pustaka Niche `/niches`:** seksi **Riwayat pengajuan** (tabel: jenis, tanggal, status badge, aksi). Aksi per status: pending→**Batalkan**; delivered→**Terima & Selesaikan** + **Minta perbaikan** (+countdown). Modal pesan custom sudah ada.
- **Admin — `/admin/niches` (panel Custom Niche Requests):** tombol per status: Tolak · Terima (→awaiting_payment) · Tandai lunas (interim) · Serahkan (buat/aktifkan niche + isi DNA via drawer).

## §10. Plan vs Realisasi
| Item | Status |
|---|---|
| Desain alur A-Z (doc ini) | ✅ PLAN final (2026-06-30) |
| DB: status set + kolom + RPC cancel/aksi-tenant + app_config | ✅ migr 0104+0105+0106 (APPLIED ke DB v2; LOKAL, belum di-deploy bareng kode) |
| BE: worker auto-close + pengingat (email via email_outbox) | ✅ `src/orchestrator/niche_request_sweeper.py` + wired worker_decoupled (py_compile OK; jalan saat deploy) |
| FE tenant: riwayat+status+batal+evaluasi (countdown) | ✅ `(app)/niches/page.tsx` (build OK) |
| FE admin: tombol proses (accept/mark_paid/deliver) | ✅ `admin/(panel)/niches/page.tsx` + route `api/admin/niche-requests` (build OK) |
| Email tagihan/bayar/serah-terima/pengingat/penutup | ✅ antre ke email_outbox (admin route + worker); KIRIM saat worker jalan (deploy) |
| 🔌 Integrasi Midtrans live (§7) | ⏸️ DITUNDA — bareng pembayaran sewa (GATE CUTOVER B2) |

**Status deploy:** ✅ **DEPLOYED LIVE 2026-06-30** (commit `e263e1a`). FE (mv-web rebuild) + BE (mv-worker restart, thread NicheSweep up) + migr 0103/0104/0105/0106 applied ke DB v2. Email (via email_outbox→SMTP) & auto-close worker kini AKTIF di produksi. **Pembayaran = concierge/manual** (admin "Tandai lunas"); integrasi Midtrans live tetap DITUNDA → GATE CUTOVER B2 (§7).

## §11. Catatan rekonsiliasi
- `PROGRESS.md` ~baris 120 ("loop custom-niche tertutup penuh") = **over-claim** (hanya ajukan→approve→eksklusif; tanpa bayar/batal/riwayat/evaluasi). Doc ini = spesifikasi A-Z sebenarnya.
- Voice niche = per-channel (lihat [[decisions_niche_owns_content_config]] ralat 2026-06-30).
