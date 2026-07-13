# 🎯 FINALISASI TIER PLAN — CETAK BIRU TERPADU (pricing · paket · pembayaran · upgrade · diskon · trial · tenant khusus)

> **Status:** RENCANA MATANG FINAL (audit 3-pass 2026-07-12 → desain terpadu 2026-07-13).
> **Mandat owner:** (1) seluruh issue skop ini = proses SALING TERINTEGRASI → penyelesaian WAJIB
> terpadu, HARAM parsial/kacamata-kuda; (2) HARAM bug baru — tiap tahap dibuktikan nol regresi
> di 5 permukaan; (3) daftar fitur per-paket = NARASI yang admin edit dari panel (keputusan 2026-07-13);
> (4) jangan sentuh kode sebelum rencana 100% matang — dokumen ini adalah kematangan itu.
> **Cara pakai:** eksekusi per-TAHAP urut (tiap tahap = utuh per-sistem, bukan potongan); tiap item
> selesai → `[x]` + REALISASI (commit+bukti). Izin owner: "kerjakan Tahap N" = izin file-file yang
> tercantum di tahap itu. Deploy = gerbang izin TERPISAH per-batch (CLAUDE.md §5).
> Setelah semua tahap tuntas → TIDAK ADA lagi issue tier/pricing/payment/upgrade/bulanan-tahunan/
> diskon/perpanjangan-trial/tenant-khusus.

---

## §0 PETA SISTEM (verifikasi 2026-07-12 — sesi baru JANGAN audit ulang)

**Dua domain "pricing":** (1) HARGA JUAL: `pricing_config` (plan_starter 149rb · plan_pro 349rb ·
plan_business 699rb · custom_niche_public_90d 299rb · custom_niche_private 1.499rb) + caps
`plan_limits` (admin-editable); (2) BIAYA AI BYOK: `ai_models.pricing` auto-sync — SEHAT, di luar skop ini.

**Yang SUDAH SEHAT (jangan disentuh/diaudit ulang):** rantai Midtrans (Snap, signature, anti-dobel,
webhook+reconciler satu logika `_apply_settlement`) · lifecycle trial→grace→suspended→blocked→deleted
(config-driven, comp exempt) · gerbang server yang SUDAH ada: unpaid-stop (producer:507, publisher:71),
video/hari (RPC `set_channel_publish_slots`), katalog niche (RPC `set_channel_niche`), niche custom
(RLS 0130), Niche Studio (API mine) · signup→trial (trigger `handle_new_tenant`) · RLS harga/payments/
audit · admin pricing (edit+audit+rollback) + pricing_pending UI Catalog · invoice+PPN · **tenant
khusus/comp** (`is_developer` atau `discount_pct≥100` = gratis selamanya, exempt sweep, caps ikut
plan_type-nya; ryan=business comp; tambah developer = modal Comp/Diskon admin) · **perpanjangan trial**
3 jalur (1-klik email token · admin extend · admin reactivate_clean; hari dari `nurture_trial_extend_days`).

**Salah-paham yang DICABUT (jangan diangkat lagi):** "Max video/hari 50" landing = BENAR (5×10ch
business) · caps live 1/3/5 lebih kecil dari DESAIN 5/10/24 = SENGAJA (admin-editable, setelan launch)
· fungsi entitlement `limits.py` = kode mati, gerbang asli di DB (dibersihkan Tahap 5).

**Akar masalah (hasil audit):** tidak pernah ada DESAIN TERPADU untuk 4 hal: (P1) penegakan hak paket,
(P2) matematika periode langganan, (P3) perhitungan harga checkout, (P4) sumber tampilan. Semua issue
di bawah = gejala dari 4 lubang itu → maka perbaikan = 4 PILAR, bukan tambalan per-gejala.

---

## §1 DESAIN TERPADU — 4 PILAR

### PILAR 1 — PENEGAKAN HAK PAKET: "satu tuas berbayar = satu gerbang server"
Prinsip: tuas yang dijual TIDAK BOLEH hanya dijaga tampilan. Dua gerbang baru melengkapi yang sudah ada:
- **1a. Gerbang LAHIR** — RLS INSERT `channels`: jumlah channel < `plan_limits.max_channels`
  (pola 0130; gagal-aman bila config tak ada; service_role/admin bebas). Menutup bocor pembuatan.
- **1b. Gerbang JALAN** — `gate_for_channel` (satu titik yang SUDAH dipakai producer+publisher)
  ditambah aturan: hanya **N channel TERTUA** (N=max_channels paket) yang boleh produksi/publish;
  channel di luar N = skip + log. Menutup bocor downgrade/keadaan-lama: turun paket → kapasitas
  otomatis mengikuti paket TANPA menghapus channel (data tenant aman; upgrade lagi → hidup lagi).
- **1c. FE-tenant (kejujuran tampilan):** halaman Channels memberi badge "di luar kuota paket" pada
  channel yang tidak dilayani + ajakan upgrade. (Elemen UI baru — bagian sah dari desain ini,
  disetujui bersama dokumen ini.)

### PILAR 2 — MATEMATIKA PERIODE: "satu rumus nilai-adil untuk SEMUA transisi"
Satu fungsi resmi `compute_new_period()` dipakai satu-satunya penulis periode (`_apply_settlement`):
```
sisa_nilai_hari = max(0, hari_tersisa_periode_lama) × (harga/hari paket-lama ÷ harga/hari paket-baru)
period_end_baru = SEKARANG + durasi_paket_baru + sisa_nilai_hari
```
- **Perpanjang paket sama** → rasio=1 → sisa hari tersambung UTUH (fix "bayar dini kehilangan hari";
  selaras DESAIN §4 "tanggal jangkar").
- **Upgrade** → sisa nilai paket murah terbawa proporsional → FAQ "di-prorate otomatis" jadi JUJUR
  tanpa mesin refund.
- **Downgrade** → sisa nilai paket mahal jadi hari lebih panjang di paket murah → tidak ada celah
  curang (kapasitas langsung dijepit Pilar 1b), tidak ada penjadwalan rumit, tenant tidak dirugikan.
- **Bulanan ↔ TAHUNAN** → rumus sama (harga/hari). Tahunan = durasi `subscription_period_days`×12,
  harga = bulanan×12×(1−`annual_discount_pct`/100); knob baru di `app_config` (seed 20, 0=matikan).
  → toggle "Tahunan hemat 20%" di /pricing jadi NYATA (DESAIN §4 Q5), drawer Billing dapat pilihan
  Bulanan/Tahunan.
- Status trial/expired/suspended/blocked (tanpa periode hidup) → murni SEKARANG + durasi (tanpa kredit).
- Harga acuan konversi = `pricing_config` saat itu (config-driven, sederhana, terdokumentasi).

### PILAR 3 — HARGA CHECKOUT: "satu fungsi resmi harga"
Satu fungsi `compute_checkout_amount()` di `snap_create_transaction`:
```
dasar   = pricing_config[plan] (× faktor tahunan bila periode=annual)
diskon  = MAX(discount_pct tenant bila 1–99, winback aktif) — pakai TERBESAR, tak digabung
jumlah  = max(1000, dasar × (100−diskon)/100)
```
- **Fix diskon-dekorasi:** `discount_pct` admin kini benar-benar memotong tagihan.
- **Tenant khusus:** comp (`is_developer`/≥100) yang memaksa checkout → DITOLAK dgn kode error jelas
  (tidak pernah ada order Rp 0 nyasar ke Midtrans).
- **Pelaporan uang jujur:** revenue admin & MRR dihitung agregat SQL penuh dari `payments` yang
  benar-benar dibayar (bukan penjumlahan daftar terpotong-500, bukan harga penuh pura-pura).
- **Jadwal harga (effective_from/until): DIBUANG dari UI admin** (kolom DB dibiarkan). Keputusan
  expert: dua tuas tumpang-tindih (Active + jadwal yang tak dibaca siapa pun) = jebakan; satu tuas
  Active = jujur & cukup. (Bila kelak butuh harga terjadwal → bangun benar dengan pembaca tanggalnya.)

### PILAR 4 — SATU SUMBER TAMPILAN: "yang dilihat pelanggan = data, bukan hardcode"
- **Narasi fitur per-paket (keputusan owner 2026-07-13):** `plan_limits` + `tagline_id/en`,
  `is_popular`, `marketing_features` (baris dwibahasa, urutan bebas) — di-seed PERSIS dari teks
  sekarang (tampilan perdana identik = nol regresi). Editor di /admin/pricing (auto-save).
  Kartu paket /pricing + landing membacanya; ANGKA fakta (channel, video/hari, Niche Studio) tetap
  otomatis dari kolom kuota — fakta tak pernah jadi teks bebas.
- **Nama paket:** `display_name` dipakai SEMUA permukaan (billing tenant, drawer, invoice, email —
  kini masih hardcode/key mentah).
- **Drawer "Ubah paket"** render dari `fetchPlans()` (bukan array hardcode) + pilihan periode
  Bulanan/Tahunan (Pilar 2).
- **Landing: biaya per-video = ILUSTRASI STATIS admin-editable (keputusan final owner 2026-07-13):**
  "Rp 75/video" lama = harga LANGGANAN per video (tenant→kita), BUKAN biaya AI — angka basi dibuang.
  Pengganti: BLOK ILUSTRASI ber-label periode pengukuran nyata ("penggunaan real 8–12 Juli 2026"),
  BUKAN data hidup (job harian/config publik DIBATALKAN — owner tak ingin data hidup di marketing);
  disimpan sebagai konten narasi ADMIN-EDITABLE (mekanisme B4) → owner perbarui kapan pun tanpa deploy.
  Isi seed (semua angka = hasil verifikasi per-run DB 2026-07-13, hanya run ber-harga, per channel,
  ber-racikan aktif — run pra-meteran & racikan lama DIKECUALIKAN):
  ① PREMIUM "RAD The Explorer": LLM GPT-4o + GPT-4o-mini (OpenAI) · TTS ElevenLabs Turbo v2.5 ·
    Visual gpt-image-1-mini (OpenAI) → ±Rp 1.270/video (avg 18 video).
  ② GRATIS "Mesin Viral (Test)": LLM Llama-3.3-70B (Groq) · TTS Edge-TTS · Visual FLUX-1 Schnell
    (Cloudflare) → senilai ±Rp 190/video (avg 9 video ber-racikan-gratis); rumusan BERSYARAT-JUJUR:
    "dengan kunci tier gratis & dalam kuota gratis harian → tagihan provider Rp 0" (benar umum, tak
    bergantung tier akun ryan; lewat kuota → provider menolak, bukan menagih senyap).
  + langganan/video per tier (dari harga & kuota saat seed, diberi label ilustrasi).
  Redaksi final di-review owner 1× sebelum tayang.
- **FAQ dibuat JUJUR oleh sistem, bukan diedit bohongnya:** "prorate" → BENAR (Pilar 2) ·
  "refund 7 hari" → redaksi jujur "hubungi kami ≤7 hari pembayaran pertama, diproses via Midtrans"
  (proses manual by design) · tahunan → BENAR (Pilar 2).
- **Auto-renew:** kenyataan = bayar-manual tiap periode via link/reminder (GoPay/VA memang tak bisa
  recurring) — DICATAT resmi di DESAIN §4 + PAYMENT doc sebagai keputusan, bukan bug.
- **Tabel perbandingan lengkap** ("Compare all features"): baris FAKTA sudah config-driven; baris
  narasi mengikuti mekanisme `marketing_features` TAHAP 4 (matriks per-tier disimpan sebagai config
  admin-editable) — bukan hardcode lagi.

---

## §2 TAHAP EKSEKUSI (urut; tiap tahap utuh per-sistem + uji nol-regresi 5 permukaan)

### TAHAP 1 — Fondasi uang & penegakan (Pilar 1a/1b + 2-inti + 3-inti)  ✅ SELESAI 2026-07-13 (lokal; menunggu izin deploy)
File: `migrations/0155_tier_enforcement.sql` · `src/billing/limits.py` · `src/billing/midtrans.py` ·
`apps/web/src/app/api/admin/tenants/[id]/lifecycle/route.ts`.
(Catatan eksekusi: knob `annual_discount_pct` DIPINDAH ke migrasi Tahap 2 — halaman admin app-config
menampilkan SEMUA key via catch-all "Others"; menanam knob tanpa label dwibahasanya = permukaan admin
cacat. Knob + label CFG_META masuk satu batch Tahap 2.)
- [x] 1.1 RLS kuota channel (gerbang LAHIR) — **terpasang & AKTIF di DB live**. Bukti (tenant uji
      nyata, anon+sesi): trial insert ch-1 ✓, ch-2 DITOLAK RLS ✓, plan→pro ch-2 BERHASIL (config-driven) ✓.
- [x] 1.2 Gate N-tertua `gate_for_channel` — bukti: tenant uji 2-channel paket-1 → tertua dilayani,
      termuda TIDAK; plan→business → hidup lagi; REGRESI ryan: 2 channel tetap dilayani ✓.
- [x] 1.3 `compute_new_period` + klaim optimistik anti dobel-terapkan — bukti presisi ≤1 detik:
      same-plan sisa 10h → end=now+40h ✓ · upgrade → now+32,13h ✓ · downgrade → now+76,91h ✓ ·
      expired → now+30h ✓ · re-delivery webhook → periode TAK berubah (klaim) ✓.
- [x] 1.4 `compute_checkout_amount` — diskon admin 50% → Rp 74.500 ✓ · winback 60 vs admin 50 →
      terbesar menang Rp 59.600 ✓ · tak digabung ✓ · comp DITOLAK ✓ · wiring Snap sandbox end-to-end:
      order nyata 74.500 + token, lalu dibatalkan ✓.
- [x] 1.5 Pagar status lifecycle admin — uji runtime HTTP (login super-admin uji, cookie ssr asli):
      tanpa-auth 401 ✓ · extend pada ACTIVE → 400 + status utuh ✓ · extend pada trial_expired → 200 ✓ ·
      reactivate_clean active→400/suspended→200 ✓ · postpone di luar blocked → 400 ✓.
- **REALISASI:** 22/22 uji lulus (17 python + 5 route), NOL residu data uji (diverifikasi count=0;
      3 user auth uji dihapus; server uji dimatikan). py_compile ✓ · import worker ✓ · npm build ✓.
      C7-sebagian ikut tuntas (5 fungsi mati limits.py dibuang) + C8-sebagian (docstring midtrans).
      Catatan utk Tahap 3: toast FE admin saat 400 masih generik ("Gagal memproses") — poles pesan
      spesifik menyusul. Commit: `fb04952`. **Deploy: ✅ 2026-07-13 (izin owner) — BE OK 01:24
      (mv-worker+mv-webhook active, health 200) · FE OK 01:27 (mv-web active, situs 200) · commit
      VPS `0f7f435` · sanity live: rute lifecycle 401 tanpa-auth ✓, / & /pricing 200 ✓.**

### TAHAP 2 — Tahunan + permukaan tenant (Pilar 2-lengkap + 4-tenant)  ⏳
File: `apps/web/src/app/api/billing/checkout/route.ts` + `src/billing/webhook_app.py` +
`src/billing/midtrans.py` (terima `period` monthly|annual) · `apps/web/src/app/(app)/billing/page.tsx`
(drawer dari fetchPlans + pilihan periode + `display_name`) · `apps/web/src/lib/plans.ts` ·
`apps/web/src/app/billing/invoice/[id]/page.tsx` + `src/utils/email.py` (display_name).
- [x] 2.1 Checkout tahunan end-to-end — bukti: `compute_checkout_amount` 12bln = Rp 1.430.400 (149rb×12×80%) ✓
      + tumpuk diskon admin 50% = 715.200 ✓ + bulanan tak berubah ✓ + periode selain 1|12 ditolak ✓ ·
      settlement tahunan → end=now+370h (360+kredit sisa 10h, presisi ≤1s) + ledger ikut ✓ · regresi
      bulanan expired → now+30h ✓ · endpoint BE (jalur Next→webhook_app) period=annual → order sandbox
      1.430.400 + period_months=12 + token; tanpa period → bulanan (kompat lama) ✓ — order uji dibatalkan.
- [x] 2.2 Drawer dinamis (fetchPlans, tier nonaktif otomatis hilang) + segmented Bulanan/Tahunan
      (tampil hanya bila knob>0) + `display_name` di: billing, drawer, halaman Channels, invoice
      (API `plan_display_name`="Starter" runtime ✓ + label "(Tahunan)" saat 12 bln ✓ + tanpa-auth 401 ✓),
      email kuitansi (body memuat "paket Starter", bukan key mentah — ditangkap runtime ✓), item Snap
      Midtrans ("MesinViral Starter (tahunan)").
- [x] 2.3 Badge "Di luar kuota paket — tidak diproduksi/tayang + Upgrade" per-kartu channel (dwibahasa;
      indeks ≥ kuota pada urutan created_at = cermin gerbang BE). Tenant dalam-kuota: nol perubahan
      visual (kondisi tak terpenuhi). Verifikasi visual penuh = last-mile owner pasca-deploy.
- **REALISASI:** 14/14 uji lulus (10 python + 4 invoice runtime via next start), nol residu (count=0,
      2 user uji dihapus, server uji dimatikan). py_compile ✓ npm build ✓ marketing /,/pricing,/showcase
      200 dgn fetchPlans baru ✓. Migrasi **0156_annual_billing** (knob `annual_discount_pct`=20 +
      `payments.period_months` default 1) TERPASANG di DB live + label CFG_META dwibahasa di admin
      app-config. Helper `plan_display_name` di limits.py (satu sumber nama). Commit: `883836c`.
      **Deploy: ✅ 2026-07-13 (izin owner) — BE OK 09:46 · FE OK 09:47 · commit VPS `6b6e58b` ·
      3 service active · sanity live: /,/pricing 200, checkout tanpa-auth 401.**

### TAHAP 3 — Panel admin lengkap & pelaporan uang jujur (Pilar 3-lengkap + 4-admin)  ✅ SELESAI 2026-07-13 (lokal; menunggu izin deploy)
File: `migrations/0157_plan_marketing_narrative.sql` (kolom narasi + seed teks sekarang; nomor 0156
terpakai annual billing Tahap 2) ·
`apps/web/src/app/admin/(panel)/pricing/page.tsx` (editor narasi per-paket · tombol Tambah entri harga ·
buang tab Schedule · sembunyikan kolom USD¢ mati · badge kategori sesuai DB) ·
`apps/web/src/app/api/admin/plan-limits/[plan]/route.ts` (whitelist + narasi + `full_niche_catalog` +
`can_request_custom_niche`) · `apps/web/src/app/api/admin/pricing/route.ts` (+POST tambah entri) ·
`apps/web/src/app/api/admin/payments/route.ts` + `admin/(panel)/billing/page.tsx` (agregat SQL penuh
+ "menampilkan X dari Y") · `api/admin/tenants/route.ts` (MRR dari pembayaran nyata).
- [x] 3.1 Editor narasi per-paket: drawer tagline ID/EN + baris fitur [{id,en}] (tambah/hapus/urut,
      auto-save on-blur, maks 12, baris kosong disaring, EN kosong → ikut ID) + toggle badge Populer.
      Migrasi **0157**: kolom narasi + SEED teks persis kartu /pricing hari ini (dikonsumsi marketing
      di Tahap 4). Bukti runtime: PATCH tersimpan+audit ✓ · >12 baris 400 ✓ · tagline>80 400 ✓ ·
      uji pakai plan 'trial' lalu DIRESTORASI persis (nol residu) ✓.
- [x] 3.2 Toggle `full_niche_catalog` + `can_request_custom_niche` (+`is_popular`) di tabel paket admin
      — whitelist route + validasi; audit admin_audit tiap patch.
- [x] 3.3 Tombol "+ Tambah entri" pricing (form key/IDR/kategori/deskripsi; validasi server snake_case
      unik + IDR≥0) — bukti: entri dibuat + pricing_audit(old=null) ✓ · duplikat 409 ✓ · key cacat 400 ✓.
- [x] 3.4 Tab Schedule DIBUANG (indeks tab & tombol simpan disesuaikan) · kolom+input USD¢ disembunyikan
      · badge kategori = data nyata (subscription/one_time).
- [x] 3.5 Uang jujur: RPC **admin_payments_stats** (SECURITY DEFINER, khusus service_role) → kartu
      revenue/lunas/pending dari agregat SELURUH tabel + FE "menampilkan X dari Y" + email pakai
      paginasi penuh (bukan cap 1000). MRR tenants = pembayaran NYATA terakhir ÷ period_months
      (fallback harga list bila tanpa jejak). Bukti DISKRIMINATIF: revenue == SUM independen
      (797.000==797.000) ✓ · MRR tenant ber-diskon = 74.500 BUKAN 149.000 list ✓.
- [x] 3.6 (titipan Tahap 1) toast lifecycle admin ber-pesan spesifik saat pagar status menolak.
- **REALISASI:** 9/9 uji runtime HTTP lulus (sesi super-admin uji, cookie ssr asli), nol residu
      (entri+audit+2 user uji dihapus; narasi trial direstorasi byte-identik). npm build ✓ · marketing
      /,/pricing 200 ✓. Visual editor = last-mile owner pasca-deploy. Commit: `1b6b529`.
      **Deploy: ✅ 2026-07-13 10:40 (izin owner, SATU batch dgn fix notifikasi insiden S3 `dc2394b`)
      — BE OK 10:38 + FE OK 10:40, commit VPS `75675cb`, 3 service active, situs 200, admin API 401
      tanpa-auth, log worker bersih.**

### TAHAP 4 — Marketing selaras mesin (Pilar 4-marketing)  ✅ SELESAI 2026-07-13 (lokal; ⏳ RATIFIKASI REDAKSI + izin deploy owner)
File: `migrations/0158_marketing_matrix_blocks.sql` (tabel `marketing_blocks` + `plan_matrix_rows`,
RLS publik-baca, seed = teks persis lama) · `apps/web/src/lib/plans.ts` (narasi + annualDiscountPct) ·
`(marketing)/pricing/page.tsx` + `(marketing)/page.tsx` (baca DB) · 4 route admin baru
(`api/admin/marketing-blocks[/[key]]`, `api/admin/plan-matrix[/[id]]`) · editor di `admin/(panel)/pricing`.
- [x] 4.1 Kartu paket /pricing + landing membaca narasi DB (`plan_limits.marketing_*`) — PARITAS
      terbukti: tagline/fitur/populer 3 paket byte-identik dgn TIER_COPY/PREVIEW_COPY lama (nol regresi).
- [x] 4.2 Toggle tahunan tersambung knob `annual_discount_pct` (0 → disembunyikan) + harga ×(100−pct)% ·
      FAQ prorate/tahunan/refund ditulis JUJUR sesuai mesin (prorate & tahunan kini nyata; refund manual).
- [x] 4.3 Landing: angka "Rp 75/video·7,5×" DIGANTI 2-komponen jujur (langganan/video config + BYOK
      nyata ±Rp1.270 premium / ±Rp0 gratis) + baris tabel kompetitor "Biaya/video all-in ±Rp1.736" + footnote.
- [x] 4.4 Matriks "Compare all features" = `plan_matrix_rows` (admin-editable; token `auto:*` render FAKTA
      live plan_limits) — PARITAS 21 baris identik hardcode lama.
- [x] 4.5 (bonus) Ilustrasi biaya per-video = `marketing_blocks` STATIS ber-label periode (keputusan owner:
      bukan data hidup) + editor admin (drawer blok + tabel matriks tambah/edit/hapus, auto-save, dwibahasa).
- **REALISASI:** BE-admin 8/8 + jalur-data anon 6/6 + paritas (matriks 21 & narasi 3 paket) LULUS;
      npm build ✓; /,/pricing 200; nol residu (blok di-PATCH lalu direstorasi persis, baris matriks uji
      dihapus, user uji dihapus). Migrasi 0158 terpasang DB live (RLS anon baca-saja diverifikasi).
      ⚠️ **REDAKSI COPY MARKETING (klaim "±10×", "±Rp1.736/video all-in", isi 2 profil biaya, FAQ) WAJIB
      diratifikasi owner sebelum TAYANG (deploy)** — gerbang copy di cetak biru. Commit: (diisi saat commit).

### TAHAP 5 — Higiene & rekonsiliasi dokumen  ⏳
- [ ] 5.1 Buang kode mati `limits.py` (5 fungsi; bila belum terangkut Tahap 1) + komentar basi
      (`midtrans.py:9-10` alias agency/scale; header /pricing "mock") + fallback caps
      `tenant_config.py:30-33` → log keras (bukan konstanta basi).
- [ ] 5.2 Catat resmi: auto-renew=bayar-manual by design (DESAIN §4 + PAYMENT doc) · sinkron
      `SISA_KERJA_GO_LIVE.md` (REALISASI) · update §9 PAYMENT doc.
- REALISASI: —

---

## §3 JAMINAN NOL REGRESI (dijalankan TIAP tahap sebelum lapor)
1. **DB** — semua policy/RPC lama tetap lulus uji smoke (insert/select per-role); migrasi idempotent.
2. **BE** — py_compile + worker start bersih + alur produksi channel ryan TIDAK berubah (log 1 siklus
   producer/publisher sebelum vs sesudah = identik utk tenant dalam-kuota).
3. **FE-tenant** — build lulus + billing/channels/niches jalur nyata di localhost:3000; tenant
   dalam-kuota melihat NOL perubahan visual (kecuali yang didesain di dokumen ini).
4. **FE-admin** — pricing/tenants/billing admin jalur nyata; audit tercatat.
5. **FE-marketing** — /pricing + landing render identik pra-Tahap-4; pasca-Tahap-4 sesuai redaksi
   yang di-review owner.
6. Checkout produksi nyata TIDAK disentuh perilaku default-nya di tahap mana pun kecuali yang
   didesain (bukti per-tahap di atas). Semua data uji sintetis dihapus bersih (nol residu).

## §3b RATIFIKASI KEPUTUSAN BISNIS (owner, 2026-07-13) — FINAL
1. ✅ Tahunan dibangun (knob diskon 20%, admin-editable). 2. ✅ Rumus nilai-adil semua transisi
(tanpa refund otomatis — nilai jadi waktu). 3. ✅ Kapasitas ikut paket (channel berlebih berhenti
dilayani, data aman). 4. ✅ Diskon: terbesar-menang tak digabung; **diskon admin BERTAHAN tiap tagihan
sampai di-nol-kan** (comeback hangus otomatis) — sudah dijelaskan & diterima. 5. ✅ Refund manual +
FAQ jujur. 6. ✅ Bayar manual per periode; kanal = SEMUA yang aktif di merchant Midtrans (kode tak
membatasi; kartu 'capture' ditangani; QRIS belum aktif di merchant per 04-07 = aksi dashboard owner;
JANGAN sentuh Notification URL). 7. ✅ (REVISI) angka per-video landing = 2 komponen HIDUP (lihat
Pilar 4). 8. ✅ Jadwal harga dibuang; SOP perubahan harga = edit panel pada tanggal-nya (seketika,
tanpa deploy; tenant berjalan kena mulai tagihan berikutnya; audit+rollback ada).

## §4 LOG REALISASI
- 2026-07-12 — audit 3-pass selesai; dokumen v1 (daftar temuan).
- 2026-07-13 — owner: narasi fitur admin-editable + mandat rencana TERPADU anti-parsial →
  dokumen ditulis ulang jadi cetak biru 4-pilar + 5 tahap. Belum ada kode disentuh.
- 2026-07-13 — 8 keputusan bisnis DIRATIFIKASI owner (§3b); butir 7 direvisi (dua komponen hidup);
  verifikasi data biaya BYOK nyata di DB (32 run, avg $0,054). Belum ada kode disentuh.
