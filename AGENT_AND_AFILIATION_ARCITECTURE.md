# PROGRAM AGEN & AFILIASI MESINVIRAL — ARSITEKTUR LENGKAP A–Z

> **Status:** 📋 SPEC DISETUJUI OWNER (2026-07-17) — konsep + seluruh aturan bisnis DIKETOK; **implementasi BELUM dimulai** (menunggu ketok per-fase).
> **Fungsi dokumen:** SINGLE SOURCE OF TRUTH + PROGRESS MONITOR program agen/afiliasi (mandat owner 2026-07-17).
> **Kaitan:** daftar kerja resmi = `SISA_KERJA_GO_LIVE.md` item **[B21]** (dokumen ini = SPEC+tracker-nya, pola `PROGRAM_BUKTI_KECERDASAN.md`). Marker ⬜ di sini BUKAN daftar kerja.
> **Aturan tracker:** tiap fase punya kolom REALISASI — diisi LANGSUNG saat selesai (✅ + tanggal + commit + bukti) + sinkron header [B21] + baris POSISI §0. Fase ber-gerbang KETOK = STOP menunggu owner.

---

## 📖 RINGKASAN AWAM — baca 3 menit, paham seluruh program (untuk owner & siapa pun)

**Apa ini?** MesinViral tidak punya tim marketing. Maka pemasaran diserahkan ke **perusahaan mitra (AGEN)**: merekalah yang keluar uang untuk iklan, bikin konten promosi, dan merekrut pasukan penjual (**RESELLER**). Imbalannya: setiap pelanggan yang mereka bawa membayar langganan, agen dapat **bagi hasil — terus-menerus, selamanya, selama pelanggan itu terus membayar**. Tugas kita satu: **menyediakan sistemnya** (aplikasi khusus agen + hitungan uang yang tidak bisa disengketakan).

**Tiga aturan emas yang membuat program ini aman:**
1. **Uang pelanggan selalu masuk ke KITA** (Midtrans MesinViral, harga resmi sama di mana-mana). Agen tidak pernah pegang uang pelanggan.
2. **Kita hanya mentransfer ke AGEN, sebulan sekali.** Reseller dibayar oleh agennya sendiri — tapi hitungannya KITA yang buat (rinci + file Excel siap-transfer), jadi tiga pihak melihat angka yang sama, nol sengketa.
3. **Milik siapa pelanggan ini? Ditentukan SATU hal saja:** kode unik yang dibawa calon pelanggan saat mendaftar. Bawa kode = bawaan pemilik kode, terkunci selamanya. Tidak bawa kode = bukan bawaan siapa pun. Titik — tidak ada rebutan.

**Contoh nyata satu putaran uang** *(angka hanya ilustrasi — angka asli diatur owner di admin panel):*
> PT Maju jadi agen; owner menyetel komisinya di admin panel: **20%**. PT Maju punya tautan pendaftaran reseller sendiri; **Budi** mendaftar lewat situ (isi nama + rekening), PT Maju menyetujui → Budi aktif & punya kode **BUDI88**, dan PT Maju menyetel jatah Budi: **Rp 50.000 per pembayaran**.
> Budi beriklan di TikTok (biaya Budi/PT Maju, bukan kita). **Ibu Sari** tertarik, mendaftar di mesinviral.com sambil memasukkan kode BUDI88 → sistem mengunci: *Ibu Sari = bawaan Budi, di bawah PT Maju — permanen*.
> Ibu Sari membayar paket **Rp 500.000/bulan** via Midtrans. Detik pembayaran sukses, sistem otomatis menulis di buku besar: *komisi PT Maju = 20% × 500rb = **Rp 100.000**; info jatah Budi = **Rp 50.000***.
> Tanggal pencairan (misal tiap tanggal 5): sistem menyodorkan tagihan "PT Maju: Rp 100.000" → **owner setujui → transfer → catat bukti**. PT Maju membuka dasbornya, unduh **Excel**: "Budi — BCA 1234567 — Rp 50.000" → transfer massal ke reseller-nya. Budi login dan melihat: "Bulan ini: 1 pelanggan, komisi Rp 50.000". Bulan depan Ibu Sari bayar lagi → semua terulang otomatis, selamanya.
> Kalau Ibu Sari refund? Komisi ditarik balik otomatis — kalau terlanjur dibayarkan, jadi pengurang tagihan PT Maju bulan berikutnya.

**Kamus singkat:** **Tenant** = pelanggan pembayar MesinViral · **Atribusi** = pencatatan "pelanggan ini bawaan siapa" (via kode, permanen) · **Buku besar / ledger** = daftar baris komisi yang hanya bisa ditambah, tak bisa diedit (koreksi = baris baru minus; setiap rupiah tertelusur) · **Pencairan / payout** = transfer bulanan kita ke agen, selalu lewat persetujuan owner · **Settlement** = uang benar-benar cair di Midtrans (satu-satunya pemicu komisi).

**Peta dokumen ini:** §1–§2 keputusan owner FINAL → §3 prinsip → §4 data → §5 alur uang → §6 keamanan/privasi → §7 **rencana kerja urut prioritas (progress monitor — lihat di sini untuk tahu posisi terkini)** → §8 keputusan yang masih terbuka → §9 risiko.

---

## §0 CARA LANJUT (resume pasca-compaction/sesi baru — baca INI dulu, jangan riset ulang)

1. **POSISI TERKINI:** 📋 Spec final 2026-07-17. Belum ada kode/DB/FE yang disentuh. Langkah berikut = owner ketok "mulai F1" → susun rencana teknis rinci F1 + daftar file → tunggu "ya" → eksekusi.
2. Seluruh keputusan owner = §1 + §2 — **FINAL, jangan tanya ulang**. Yang masih terbuka = §8 (tanya HANYA saat fasenya tiba).
3. Skema DB di §4 = **rancangan**; DDL final wajib introspeksi DB live dulu (aturan kerja: kode+DB live = fakta; dokumen = peta). Anchor kode di §5 wajib di-grep ulang sebelum dipakai.
4. Aturan kerja penuh = `CLAUDE.md` (§2 pre-touch · §3 pre-done · §5 deploy per-batch ber-izin eksplisit · dwibahasa · config-driven · gagal-jujur).

---

## §1 KONSEP BISNIS & KEPUTUSAN OWNER (FINAL 2026-07-17 — jangan tanya ulang)

### 1a. Bentuk program
```
MesinViral ──kontrak + bagi hasil──▶ AGEN (perusahaan mitra)
                                        │ merekrut, menyetujui & membayar
                                        ▼
                                     RESELLER (tim penjual agen)
                                        │ menyebar kode unik
                                        ▼
                                     TENANT (pelanggan — bayar ke Midtrans KITA)
```
- **Kami developer, tanpa tim marketing.** Seluruh investasi pemasaran (iklan, konten promosi, rekrut reseller) = **tanggungan agen**. Kami menyediakan SISTEM.
- **Jenjang 2 tingkat penuh:** sistem mengenal AGEN dan RESELLER-nya (kode per reseller, kinerja per reseller terlihat). 
- **Uang masuk 1 pintu:** semua tenant membayar harga resmi ke Midtrans milik MesinViral. Tidak ada agen/reseller yang memegang uang pelanggan. TIDAK white-label.
- **Uang keluar 1 pintu:** MesinViral hanya mentransfer komisi ke AGEN (1×/bulan). **Reseller dibayar oleh agennya masing-masing** — kami menyediakan perhitungan rinci + export Excel untuk transfer massal oleh agen (1 bulan 1 kali).
- **Masa komisi: SELAMANYA** — selama tenant bawaan agen terus membayar, agen terus dapat bagian.

### 1b. Atribusi (aturan tegas — kata owner)
- Calon tenant **datang membawa kode unik** (diisi di form daftar, atau otomatis via tautan `?ref=KODE`) = bawaan agen/reseller pemilik kode itu, **terkunci permanen sejak daftar**.
- **Tanpa kode = bukan bawaan siapa pun. Titik.** Tidak ada cookie-tracking, tidak ada klaim belakangan, tidak ada rebutan.
- Kode reseller otomatis ter-atribusi juga ke agen induknya.
- Marketing kit = **HANYA tautan & kode unik** — landing page tetap marketing site yang sudah ada; kami TIDAK membuat materi iklan (itu investasi agen).

### 1c. Nilai komisi (dua tingkat, dua pengatur)
| Tingkat | Bentuk nilai | Siapa yang mengatur | Di mana |
|---|---|---|---|
| Komisi AGEN (dari MesinViral) | **Rupiah tetap ATAU persen** per pembayaran-valid tenant — sesuai kesepakatan per-agen | **Owner/admin** | **Admin panel** (BUKAN dari aplikasi agen) |
| Komisi RESELLER (dari agen) | **Rupiah tetap ATAU persen** | **Agen masing-masing** | **Dasbor agen** |

### 1d. Pencairan
- Komisi agen dibayar **1×/bulan**; **tanggal pencairan bisa dikonfigurasi** (config admin).
- Pencairan SELALU lewat gerbang persetujuan owner di admin panel (sistem menyodorkan tagihan → owner setujui → transfer → catat bukti). Tidak pernah ada uang keluar otomatis.

### 1e. Reseller
- Calon reseller **mendaftar sendiri** melalui aplikasi yang kami sediakan untuk agen masing-masing (tautan pendaftaran khusus per agen).
- Setiap reseller punya akses **melihat pencapaiannya sendiri** per periode/bulan (hanya miliknya, bukan milik reseller lain).

### 1f. Visibilitas untuk owner
- Kami **tidak perlu masuk** ke aplikasi agen. Admin panel punya **dua lapis**: (1) resume lintas-agen (peringkat, pelanggan baru, komisi berjalan, tren) + (2) **rinci per-agen** — klik satu agen → terlihat persis apa yang agen itu lihat di dasbornya (untuk penyelesaian sengketa dengan data yang sama).

### 1g. Ditolak owner (JANGAN diusulkan ulang)
- ❌ Peringatan "Anda nombok" bila agen menyetel komisi reseller > jatahnya ("agen tidak sebodoh itu").
- ❌ Materi iklan/banner buatan kami di marketing kit (cukup tautan + kode).
- ❌ Program referral antar-tenant "ajak teman" (konsep awal) — DIGANTI seluruhnya oleh program agen ini.

---

## §2 ATURAN BISNIS TERKUNCI (5 titik rawan sengketa — DIKETOK owner 2026-07-17)

1. **Pembayaran tahunan × komisi Rupiah-tetap:** komisi dihitung **per bulan-langganan yang dibayar**. Tenant bayar 12 bulan sekaligus = 12× komisi bulanan, dicairkan sekaligus pada periode pembayaran itu. (Berlaku pola sama utk semua nominal-per-bulan; komisi persen otomatis adil karena mengikuti rupiah masuk.)
2. **Basis persen = rupiah yang BENAR-BENAR masuk** (nilai settlement setelah diskon apa pun; bukan harga pajangan). Sistem tidak pernah membagi uang yang tidak diterima.
3. **Refund setelah komisi terlanjur dibayarkan** → otomatis menjadi **pengurang tagihan pencairan bulan berikutnya** agen tsb (tidak menagih transfer balik). Refund sebelum pencairan → baris komisi ditarik-balik langsung.
4. **Pendaftaran reseller ber-gerbang persetujuan agen:** calon daftar → status `pending` → **agen menyetujui** → kode aktif. Tanpa persetujuan, kode tidak pernah hidup.
5. **Data rekening reseller** (nama bank + nomor rekening) diisi reseller saat mendaftar → masuk otomatis ke kolom export Excel transfer-massal. Disimpan **terenkripsi**; hanya terlihat oleh agen ybs (dan owner/admin). 

---

## §3 PRINSIP ARSITEKTUR (mengikat semua fase)

1. **Menumpang infrastruktur yang ada** — aplikasi web & server yang sama (Next.js self-host + nginx), pintu masuk berbeda untuk agen/reseller. Nol server baru, nol biaya infra baru. (Bentuk pintu: path `/agent` vs subdomain = keputusan §8-K3 saat F2.)
2. **Config-driven total** (CLAUDE.md §3.3): semua angka program (tanggal pencairan, ambang minimum, nilai default) = DB/config ber-label admin; **nol literal di kode**.
3. **Gagal jujur, HARAM fallback senyap** (§0.6): kegagalan hitung/atribusi = STOP + notifikasi, bukan tebakan.
4. **Buku besar tak-bisa-diedit (append-only):** baris komisi tidak pernah di-UPDATE nilainya; koreksi = baris baru (reversal). Setiap rupiah tertelusur: pembayaran → baris komisi → pencairan → bukti transfer.
5. **Dwibahasa ID/EN** via mekanisme `Bi` untuk SEMUA UI baru (portal agen, reseller, admin, form daftar) — §3.5.
6. **Rate di-snapshot per baris komisi:** perubahan % / Rp oleh admin/agen berlaku untuk pembayaran BERIKUTNYA; baris yang sudah tercatat tidak berubah.
7. **Privasi tenant utuh:** agen/reseller hanya melihat data tenant seperlunya (label nama + status bayar + nilai komisinya) — TIDAK PERNAH isi akun, kredensial, channel, email penuh.
8. **UI layak orang awam** (§3.6): status + tombol dalam satu panel, auto-save, narasi singkat fungsi tiap kenop.

---

## §4 RANCANGAN DATA (DDL final = introspeksi DB live saat F1; ini kontrak logisnya)

> Semua tabel di schema yang sama dgn aplikasi (Supabase v2). RLS wajib per §6. Nama kolom final boleh bergeser saat implementasi — MAKNA di bawah tidak boleh.

| Tabel (baru) | Isi & kolom kunci | Catatan |
|---|---|---|
| `agents` | id · nama perusahaan · kontak (nama/email/telepon) · `status` (active/suspended) · **`commission_type`** (`flat_idr`\|`percent`) · **`commission_value`** · rekening tujuan (bank, no. rek, atas-nama — terenkripsi) · `join_code` (kode pendaftaran reseller khusus agen ini) · created_at | Nilai komisi per-agen = kesepakatan; HANYA admin yang menulis |
| `agent_users` | user_id (Supabase auth) · agent_id · role (`agent_owner`\|`agent_staff`) | Login agen. PENTING: model auth existing = `tenant_id = auth.uid()` (1 user = 1 tenant) — user agen BUKAN tenant; dibedakan via `app_metadata` role (pola super-admin yang sudah ada). Verifikasi pola pasti saat F1 |
| `resellers` | id · agent_id · user_id (login reseller) · nama · kode unik · `status` (`pending`/`active`/`suspended`) · **`commission_type`/`commission_value`** (diatur agen) · bank+rekening (terenkripsi) · created_at | Lahir dari pendaftaran-mandiri via `join_code` agen; aktif hanya setelah agen setujui (§2.4) |
| `tenant_attribution` | tenant_id (UNIQUE — kunci anti-rebutan) · agent_id · reseller_id (nullable — bawaan langsung agen) · kode yang dipakai · locked_at | **Ditulis SEKALI saat signup, tidak pernah di-update** (§1b) |
| `commission_ledger` | id · payment_ref (order Midtrans) · tenant_id · agent_id · reseller_id? · `gross_idr` (rupiah settlement) · `months_paid` (utk aturan §2.1) · snapshot rate agen (type+value) · `agent_amount_idr` · snapshot rate reseller (type+value) · `reseller_amount_idr` (informasi utk agen — bukan kewajiban kami) · `status` (`accrued`→`approved`→`paid` \| `reversed`) · `payout_id?` · created_at | **Append-only** (§3.4). Reversal = baris minus baru yang menunjuk baris asal |
| `agent_payouts` | id · agent_id · periode (bulan) · total tagihan · pengurang-refund (§2.3) · total dibayar · `status` (`draft`→`approved`→`paid`) · bukti transfer (catatan/ref) · approved_by · paid_at | 1 baris per agen per bulan; gerbang owner (§1d) |
| Config (`app_config`/`pricing_config`, ber-label admin) | `partner_payout_day` (tanggal pencairan bulanan) · `partner_min_payout_idr` (ambang minimum) · `partner_default_commission_*` (nilai awal saat membuat agen baru) · saklar program on/off | Semua bisa diubah owner tanpa sentuh kode (§3.2) |

**Yang TIDAK dibuat:** tabel materi-iklan (ditolak §1g) · tabel payout-reseller (reseller dibayar agen, di luar kas kami — kami hanya menghitung & meng-export).

---

## §5 ALUR UANG & PROSES (end-to-end)

### 5a. Pendaftaran tenant ber-kode
1. Calon tenant membuka form daftar (marketing site yang ada) — kolom baru **"Kode agen/reseller (opsional)"**; tautan `mesinviral.com/?ref=KODE` mengisi kolom itu otomatis.
2. Saat submit: kode divalidasi (ada & `active`?) → tulis `tenant_attribution` (terkunci). Kode tak dikenal = **ditolak jelas di titik input** (§3.1 anti-human-error), bukan diterima-diam-diam.
3. Tanpa kode → tidak ada baris atribusi → selamanya bukan bawaan siapa pun (§1b).

### 5b. Lahirnya komisi (otomatis, per pembayaran valid)
1. Tenant membayar → **webhook settlement Midtrans yang SUDAH ADA** (`src/billing/webhook_app.py` — anchor wajib grep ulang saat F1) diberi satu langkah tambahan: *tenant ini punya baris atribusi?* → hitung & tulis baris `commission_ledger` (`accrued`).
2. Perhitungan: `months_paid` dari isi order (bulanan=1, tahunan=12) → agen: flat×months ATAU %×gross (§2.1–2.2) → reseller (informasi): rumus sama dari snapshot rate reseller.
3. Gagal hitung/tulis = STOP + notifikasi admin (Telegram — infra sudah ada); pembayaran tenant TIDAK terganggu (komisi menyusul setelah dibereskan; gagal-jujur, §3.3).

### 5c. Pencairan bulanan ke agen
1. Tiap `partner_payout_day`: sistem menyusun `agent_payouts` draft per agen = Σ `accrued` periode itu − reversal/refund menggantung (§2.3); di bawah `partner_min_payout_idr` → digulung ke bulan berikut.
2. Admin panel menyodorkan daftar tagihan → **owner menyetujui** → transfer manual bank → owner catat bukti → baris-baris ledger jadi `paid`.
3. Rekap per-agen tersedia utk kebutuhan pajak (§8-K5).

### 5d. Hitungan reseller + Excel transfer-massal (kewajiban kami = hitung & sajikan)
1. Tiap periode, sistem menghitung rincian per-reseller per-agen dari ledger (baris `reseller_amount_idr`).
2. Dasbor agen: tabel per-reseller + tombol **Export Excel** — kolom siap-transfer: nama reseller · bank · no. rekening · atas-nama · total komisi periode · rincian. 1 bulan 1 file (§1a).
3. Pembayaran ke reseller = urusan agen (di luar kas kami); reseller melihat pencapaian & nilai komisinya sendiri di portalnya (§1e) — transparan tiga arah tanpa kami pegang uangnya.

### 5e. Refund / pembatalan
- Kabar refund Midtrans → baris reversal (minus) di ledger → bila baris asal belum dibayar: saling meniadakan di draft payout; bila sudah dibayar: jadi pengurang payout bulan berikutnya (§2.3). Semua otomatis + terlihat di admin & dasbor agen.

### 5f. Pendaftaran reseller
1. Agen membagikan tautan pendaftaran khususnya (`join_code`).
2. Calon reseller mengisi: nama · kontak · login · bank+rekening (§2.5) → status `pending`.
3. Agen melihat antrean di dasbornya → setujui/tolak → disetujui = kode reseller aktif + (agen menyetel rate komisinya) → reseller bisa login melihat pencapaiannya.

---

## §6 KEAMANAN, PERAN & PRIVASI

| Peran | Melihat | TIDAK PERNAH melihat |
|---|---|---|
| **Owner/admin** | Segalanya: resume lintas-agen + rinci per-agen (tampilan sama dgn yang agen lihat, §1f) + seluruh ledger & payout | — |
| **Agen** | Pelanggan bawaannya (label nama + status bayar + nilai komisi) · reseller-nya + kinerjanya + rekeningnya · ledger & payout miliknya · Excel export | Data agen lain · isi akun tenant (kredensial/channel/email penuh) · pengaturan rate agen (read-only — rate agen milik admin, §1c) |
| **Reseller** | Pencapaian & komisi MILIKNYA per periode | Data reseller lain · rate/omzet agen · data tenant selain label bawaannya |
| **Tenant** | (tidak berubah — tenant tidak melihat program ini kecuali kolom kode saat daftar) | — |

- **RLS** di setiap tabel baru mengikuti matriks di atas; user agen/reseller dibedakan dari tenant via `app_metadata` (pola super-admin existing — verifikasi pasti di F1).
- **Rekening bank** (agen & reseller) terenkripsi at-rest (pakai pola vault kredensial yang sudah ada — anchor: `src/utils/api_key_vault.py`, grep ulang saat implementasi); tak pernah tampil di log/chat (CLAUDE.md §6.3).
- **Anti-kecurangan bawaan:** komisi HANYA dari settlement nyata · atribusi permanen-unik (UNIQUE tenant_id) · kode self-signup diblok utk email/identitas yang sama dgn pemilik kode · ambang minimum pencairan · ledger append-only (audit penuh) · agen `suspended` = kode mati seketika tapi ledger utuh.

---

## §7 RENCANA KERJA — URUT PRIORITAS (progress monitor; isi REALISASI SAAT ITU JUGA)

> Setiap fase: rencana teknis rinci + daftar file → **ketok owner** → bangun → bukti runtime §3.4 (uji data nyata, bukan build-lulus) → laporan → **izin deploy eksplisit** (§5.0) → REALISASI diisi + sinkron [B21] + §0.

### F0 — PERSIAPAN BISNIS (tugas OWNER — tanpa kode; boleh paralel dgn F1)
- Template **kontrak kemitraan** per agen (kewajiban investasi iklan, larangan janji-palsu, hak putus) — sistem menegakkan angka, kontrak menegakkan perilaku.
- Konfirmasi **pajak** komisi (PPh) ke konsultan pajak — sistem menyediakan rekap per-agen (5c.3), kewajiban potong/lapor = keputusan owner.
- Tetapkan angka awal: default komisi agen · tanggal pencairan · ambang minimum (§8-K1/K2).
- **DONE-BILA:** owner menyatakan kontrak & angka siap (tidak memblok F1 dimulai; memblok agen pertama DIREKRUT).
- **REALISASI:** ⬜

### F1 — MESIN UANG (prioritas #1 — program bisa jalan dgn agen pertama TANPA portal)
- **Lingkup:** semua tabel §4 + RLS · kolom kode di form daftar + `?ref=` (5a) · sambungan webhook settlement → ledger (5b) · reversal refund (5e) · **admin panel:** CRUD agen + rate + resume lintas-agen + rinci per-agen + draft-approve-catat pencairan (5c) · config ber-label · notifikasi-gagal Telegram.
- **Nilai bisnis:** owner sudah bisa merekrut & membayar agen pertama; laporan sementara via admin.
- **DONE-BILA (ukur, bukan rasa):** ≥1 pendaftaran uji ber-kode terkunci benar · ≥1 pembayaran uji (sandbox/riil kecil) melahirkan baris ledger dgn rupiah PERSIS sesuai §2.1–2.2 (kasus: bulanan-persen · bulanan-flat · tahunan-flat ×12 · dgn-diskon basis-net) · refund uji menghasilkan reversal benar · draft payout bulanan terbentuk & bisa disetujui-dicatat · RLS terbukti (agen tak bisa baca data agen lain — diuji nyata).
- **REALISASI:** ⬜

### F2 — PORTAL AGEN (prioritas #2)
- **Lingkup:** pintu masuk agen (path/subdomain = ketok §8-K3) · login · **dasbor:** pelanggan bawaannya + status bayar + komisi berjalan + riwayat pencairan · kode & tautan uniknya · dwibahasa penuh.
- **DONE-BILA:** agen uji melihat SEMUA angka yang identik dgn admin rinci-per-agen (satu sumber, §1f) · uji-silang isolasi antar-agen · rantai penuh klik→layar dibuktikan (§3.4).
- **REALISASI:** ⬜

### F3 — RESELLER (prioritas #3)
- **Lingkup:** tautan pendaftaran-mandiri per agen + antrean persetujuan (5f) · kode per reseller · agen menyetel rate reseller (Rp/%) dari dasbornya · kinerja per-reseller di dasbor agen · **hitungan komisi reseller per periode + Export Excel transfer-massal** (5d) · **portal reseller:** login + pencapaian miliknya per bulan · rekening terenkripsi.
- **DONE-BILA:** alur daftar→pending→disetujui→kode aktif diuji penuh · tenant uji via kode reseller ter-atribusi ke reseller DAN agen induk · Excel terbuka benar di Excel/Sheets dgn kolom siap-transfer & angka cocok ledger · reseller uji hanya melihat miliknya (uji isolasi).
- **REALISASI:** ⬜

### F4 — PELENGKAP (prioritas #4 — setelah program hidup)
- **Lingkup:** agen mendaftarkan pelanggan langsung dari dasbornya (jualan tatap muka) · notifikasi Telegram ke agen saat komisi lahir/cair · rekap tahunan utk pajak · otomasi pengingat tanggal pencairan ke owner.
- **DONE-BILA:** per-butir, ditetapkan saat rencana rinci F4.
- **REALISASI:** ⬜

**Urutan tidak boleh dibalik:** F1 tanpa portal tetap menghasilkan uang & kepercayaan; portal tanpa mesin-uang = etalase kosong.

---

## §8 KEPUTUSAN MASIH TERBUKA (tanya owner TEPAT saat fasenya — jangan diasumsikan)

| # | Keputusan | Dibutuhkan saat |
|---|---|---|
| K1 | Angka default: komisi agen (Rp/% berapa) · ambang minimum pencairan · tanggal pencairan | F0/F1 (semuanya kenop config — bisa diisi belakangan tanpa ubah kode) |
| K2 | Nama resmi program (utk kontrak & UI; "MesinViral Partner" = placeholder) | F2 (UI portal) |
| K3 | Pintu portal agen: `mesinviral.com/agent` vs subdomain `agen.mesinviral.com` | F2 (dampak: config nginx) |
| K4 | Kebijakan agen `suspended`: komisi berjalan dibekukan atau tetap cair utk tenant lama? | F1 (default rancangan: tetap cair — atribusi & ledger sah; pembekuan = keputusan owner per-kasus) |
| K5 | Pajak: dipotong kami saat transfer atau gross (agen lapor sendiri)? | F0 (konsultan pajak owner) |

---

## §9 RISIKO & MITIGASI (jujur di muka)

| Risiko | Mitigasi |
|---|---|
| Agen menjanjikan yang bukan-bukan ke pelanggan | Kontrak (F0) + hak suspend + semua tenant tetap milik & dilayani MesinViral langsung |
| Sengketa "pelanggan ini bawaanku" | Mustahil by-design: atribusi = kode saat daftar, UNIQUE, permanen (§1b) |
| Sengketa angka agen↔reseller | Ledger transparan 3 arah: owner, agen, reseller melihat angka dari SATU sumber yang sama |
| Salah hitung komisi | DONE-BILA F1 mewajibkan bukti rupiah-persis 4 kasus + append-only (koreksi selalu tertelusur) |
| Kebocoran data antar-agen | RLS diuji nyata sbg bagian DONE-BILA (bukan "harusnya aman") |
| Program sepi (tak ada agen) | Biaya tetap nol — sistem dorman tidak membebani; saklar program bisa off |
| Beban webhook bertambah | Langkah tambahan = 1 insert ringan; gagal-jujur TANPA mengganggu pembayaran tenant (5b.3) |

---

## §10 CHANGELOG
- **2026-07-17** — Dokumen lahir (mandat owner "arsitektur lengkap A–Z + rencana kerja urut prioritas, single source of truth & progress monitor"). Seluruh §1–§2 = keputusan owner FINAL dari diskusi 2026-07-16→17 (jenjang 2-tingkat · bayar-ke-kami · selamanya · Rp/% dua-tingkat · pencairan bulanan ber-tanggal-config · reseller dibayar agen + Excel · pendaftaran reseller mandiri ber-persetujuan · admin resume+rinci · 5 aturan sengketa · penolakan §1g). Implementasi belum dimulai.
