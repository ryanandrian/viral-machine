# PROGRAM AGEN & AFILIASI MESINVIRAL — ARSITEKTUR LENGKAP A–Z

> **Status:** 📋 SPEC DISETUJUI OWNER (2026-07-17) — konsep + seluruh aturan bisnis DIKETOK; **implementasi BELUM dimulai** (menunggu ketok per-fase). **DIMATANGKAN 2026-07-17 (mandat owner "evaluasi lagi, semua harus clear"):** + riset pajak (§6b) + draf kontrak (Lampiran A) + aturan operasional rinci (§5g) + inventaris permukaan (§3b).
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

**Peta dokumen ini:** §1–§2 keputusan owner FINAL → §3 prinsip + §3b inventaris permukaan → §4 data → §5 alur uang + §5g aturan operasional rinci → §6 keamanan/privasi → §6b pajak komisi → §7 **rencana kerja urut prioritas (progress monitor — lihat di sini untuk tahu posisi terkini)** → §8 keputusan yang masih terbuka → §9 risiko → **Lampiran A: draf kontrak kerjasama**.

---

## §0 CARA LANJUT (resume pasca-compaction/sesi baru — baca INI dulu, jangan riset ulang)

1. **POSISI TERKINI:** ✅ **SEMUA TEKNIS TUNTAS & LIVE PRODUKSI 2026-07-17 — F1+F2+F3+F4 + audit A–Z (§9b) + kartu konfigurasi terpusat (§9c, `11f2788` 19:51).** Verifikasi terakhir bersih (R1/C3/C4/C5/REG1/REG2; situs 200, /admin/app-config ter-guard). **SISA [B21] = murni NON-TEKNIS owner:** (a) F0 — angka komisi default + validasi konsultan pajak (§6b) & hukum (Lampiran A); (b) bukti klik-layar (rekrut agen uji e2e); (c) agen nyata pertama TERBAYAR = DONE-BILA tutup item. **JANGAN bangun/audit ulang fase teknis — tuntas & teraudit.**
   *(Riwayat)* ✅ **F1 + F2 + F3 LIVE DI PRODUKSI** (F3 deployed 2026-07-17: BE OK 14:47 + FE OK 14:52 commit `e652357` — percobaan-1 FE FAIL karena `exceljs` belum ada di lingkungan build VPS [skrip deploy tak pernah `npm install`; dependency FE baru pertama sejak skrip lahir] → dipasang sesuai lockfile → percobaan-2 OK. Verifikasi produksi: /reseller/login 200+badge ✓ · /reseller anon→login ✓ · join publik hidup & kode ngawur ditolak ✓ · export Excel anon 401 ✓ · op BE tanpa secret 401 ✓ · regresi /agent ✓). **USULAN menunggu ketok:** skrip deploy_fe.sh diberi langkah `npm ci` otomatis (anti-terjegal dependency baru). Berikutnya: bukti klik→layar owner (rekrut agen nyata) → **F4 pelengkap** (rencana rinci → ketok) + sisa F0 (angka default & validasi konsultan, owner).
   *(Riwayat)* ✅ **F1 LIVE DI PRODUKSI 2026-07-17 10:36** (izin owner "deploy BE + FE untuk batch F1 ini"; skrip resmi BE OK 10:34 + FE OK 10:36, commit `8705997`, situs 200). **Verifikasi produksi 4 titik:** `/api/partner/check` hidup ✓ · kolom kode ID+EN tampil di HTML live /auth ✓ · `/admin/partners` anon dilempar login (307) ✓ · endpoint uang internal tanpa secret = 401 ✓. Sisa F1 (kecil): bukti mata-kepala owner di layar admin + pembayaran Midtrans nyata pertama dari tenant beratribusi = bukti hidup pamungkas. **Berikutnya: F2 portal agen (susun rencana rinci → ketok owner).**
   **🎯 PERINTAH OWNER 2026-07-17: sesi berikutnya FOKUS menyelesaikan modul ini** — paham 100% apa yang dibangun (dokumen ini) + peta & progres (§7). Langkah pertama sesi berikut: susun **rencana teknis rinci F1 + daftar file** → sodorkan ke owner → tunggu "ya" → eksekusi → bukti runtime → izin deploy.
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
9. **🎨 SATU NUANSA UI (mandat owner 2026-07-17):** portal agen, portal reseller, dan modul admin WAJIB memakai **pustaka UI & pola halaman yang SUDAH ADA** di `apps/web` (komponen, tema, tipografi, pola form/tabel/badge yang sama dengan panel tenant & admin) — DILARANG membangun gaya/library baru. Ukuran lulus: orang yang membuka portal agen merasa di aplikasi yang sama.
10. **⚖️ ATURAN KERJA WAJIB (mandat owner 2026-07-17):** SETIAP sesi yang menyentuh modul ini wajib menerapkan `CLAUDE.md` penuh tanpa kecuali — deep-dive §2 pre-touch sebelum menyentuh, daftar-file → ketok sebelum edit, bukti runtime §3.4 sebelum "selesai", izin deploy eksplisit §5.0, world-class best practice di DB/BE/FE.

### §3b INVENTARIS PERMUKAAN (helicopter view — apa tersentuh & apa TIDAK, dengan alasan)

| Permukaan | Tersentuh? | Apa persisnya |
|---|---|---|
| **DB** | ✅ | HANYA tabel-tabel baru §4 + kunci config baru. Tabel produksi (`videos`, `production_runs`, `channels`, `niches`, dst.) TIDAK diubah — hanya DIBACA status pembayarannya |
| **BE — webhook billing** (`mv-webhook`) | ✅ 1 titik | Satu langkah tambahan pasca-settlement Midtrans (5b) + reversal refund (5e) |
| **BE — worker produksi video** (`mv-worker`, pipeline) | ❌ **TIDAK TERSENTUH SAMA SEKALI** | Program ini murni lapisan komersial; nol risiko ke produksi konten — pemisahan ini disengaja & wajib dipertahankan tiap fase |
| **FE-marketing** | ✅ 1 titik | Form daftar: kolom "Kode agen/reseller (opsional)" + dukungan `?ref=` (5a). Landing & halaman lain TIDAK berubah (keputusan §1b) |
| **FE-tenant** (panel tenant) | ❌ TIDAK | Tenant tidak melihat program ini sama sekali pasca-daftar |
| **FE-admin** | ✅ modul baru | Modul "Partner": CRUD agen · rate · resume + rinci per-agen · gerbang pencairan · config |
| **Portal agen & reseller** | ✅ BARU | Pintu masuk baru menumpang aplikasi web existing (§3.1); tanpa server baru |
| **Infra/nginx** | ⚠️ hanya bila K3 = subdomain | Path `/agent` = nol perubahan infra; subdomain = 1 blok nginx |
| **Notifikasi (Telegram/email)** | ✅ reuse | Alarm gagal-hitung ke admin (F1); notifikasi ke agen (F4) — infra sudah ada |

---

## §4 RANCANGAN DATA (DDL final = introspeksi DB live saat F1; ini kontrak logisnya)

> Semua tabel di schema yang sama dgn aplikasi (Supabase v2). RLS wajib per §6. Nama kolom final boleh bergeser saat implementasi — MAKNA di bawah tidak boleh.

| Tabel (baru) | Isi & kolom kunci | Catatan |
|---|---|---|
| `agents` | id · nama perusahaan · kontak (nama/email/telepon) · `status` (active/suspended) · **`commission_type`** (`flat_idr`\|`percent`) · **`commission_value`** · rekening tujuan (bank, no. rek, atas-nama — terenkripsi) · `join_code` (kode pendaftaran reseller khusus agen ini) · created_at | Nilai komisi per-agen = kesepakatan; HANYA admin yang menulis |
| ~~`agent_users`~~ **DIBATALKAN (ketok owner F2 2026-07-17):** login agen = **`agents.user_id`** (SATU login per agen) | user auth ber-`app_metadata.role='agent'` (pola super-admin; tak bisa dipalsukan) tertaut kolom `agents.user_id` | Multi-staf per agen = kebutuhan masa depan (buat tabel baru saat nyata dibutuhkan, ber-ketok). User agen BUKAN tenant; email agen ≠ email tenant (§5g.3) ditegakkan saat undangan |
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
- Kabar refund Midtrans → baris reversal (minus) di ledger → bila baris asal belum dibayar/dikunci: saling meniadakan; bila sudah **approved ATAU paid**: jadi pengurang payout bulan berikutnya (§2.3; audit T-1 2026-07-17 — status `approved` = sudah dikunci ke payout, wajib jalur pengurang). Semua otomatis + terlihat di admin & dasbor agen.
- **Kebijakan `partial_refund` (aturan eksplisit, hasil audit T-4):** refund parsial menarik balik **SELURUH** komisi order tsb (konservatif melindungi kas — tidak diproratakan). Mengubah jadi prorata = ketok owner.

### 5f. Pendaftaran reseller
1. Agen membagikan tautan pendaftaran khususnya (`join_code`).
2. Calon reseller mengisi: nama · kontak · login · bank+rekening (§2.5) → status `pending`.
3. Agen melihat antrean di dasbornya → setujui/tolak → disetujui = kode reseller aktif + (agen menyetel rate komisinya) → reseller bisa login melihat pencapaiannya.

### 5g. ATURAN OPERASIONAL RINCI (anti-ambigu — hasil evaluasi total 2026-07-17)
1. **Onboarding agen — TIDAK ada pendaftaran-mandiri agen.** Alur satu-satunya: kontrak ditandatangani (Lampiran A) → admin membuat agen di admin panel (nama, rate, rekening) → sistem mengundang email PIC agen membuat login. Agen hanya lahir dari tangan admin.
2. **Format kode:** huruf besar + angka, 4–12 karakter, input case-insensitive, **unik GLOBAL** (satu daftar kode lintas agen & reseller — mustahil dua entitas berkode sama). Default dibuat sistem; boleh diganti pemiliknya selama unik & belum pernah dipakai mendaftar (kode yang pernah dipakai = beku selamanya, jejak atribusi).
3. **Satu email = satu peran.** Email user agen/reseller tidak boleh sama dengan email tenant/admin (model auth existing: 1 user = 1 tenant). Ditolak jelas di titik input.
4. **Definisi periode & cut-off:** periode komisi = **bulan kalender menurut tanggal settlement**. Pencairan periode itu terjadi pada `partner_payout_day` bulan BERIKUTNYA (contoh config=5: settlement 1–31 Jan → cair 5 Feb). Tidak ada wilayah abu-abu tanggal.
5. **Pembulatan:** hasil hitung persen dibulatkan ke rupiah penuh terdekat per baris ledger. *(Keputusan teknis reversible — diputuskan di sini, CLAUDE.md §2.3c.)*
6. **Suspend agen = cascade:** seluruh kode di bawahnya (kode agen + semua kode reseller-nya) berhenti menerima pendaftaran BARU seketika; atribusi & ledger lama utuh. Nasib komisi berjalan selama suspend = §8-K4.
7. **Reseller nonaktif:** kodenya mati untuk pendaftaran baru; atribusi tenant lama TETAP padanya (§1b permanen); agen bebas mengubah rate reseller kapan pun — berlaku hanya untuk pembayaran berikutnya (§3.6).
8. **Putus kontrak agen:** akun & semua kode dinonaktifkan; seluruh ledger/payout **disimpan** (kewajiban audit & pajak); nasib komisi pasca-putus = §8-K7 (dicerminkan Pasal 10 draf kontrak).
9. **Agen sekaligus tenant:** boleh (akun terpisah), tapi TIDAK berkomisi atas langganan miliknya sendiri / akun se-identitas (blok self-referral §6).
10. **Komisi HANYA dari pembayaran langganan plan** (default rancangan): pembayaran jenis lain (mis. pesanan custom-niche bila kelak live) TIDAK berkomisi — mengubahnya = keputusan §8-K6.
11. **Mata uang tunggal:** IDR. **Format export:** .xlsx, dibuat on-demand per periode dari ledger (bukan file tersimpan — selalu angka terkini).

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

### §6b PAJAK KOMISI AGEN (hasil riset Claude 2026-07-17 — mandat owner; WAJIB validasi konsultan pajak/DJP sebelum pencairan pertama)

> Memotong PPh atas komisi = **kewajiban hukum PIHAK PEMBAYAR (kita)**, bukan pilihan. Yang tersisa untuk diputuskan owner hanyalah SIAPA yang mengurus administrasinya (§8-K5).

| Status agen | Jenis pajak | Tarif | Praktiknya bagi kita |
|---|---|---|---|
| **Badan usaha** (PT/CV) ber-NPWP | PPh 23 — jasa keagenan/perantara (non-final) | **2% × bruto komisi** | Kita potong saat transfer → setor → terbitkan **bukti potong** (via Coretax DJP) |
| Badan **tanpa NPWP** | PPh 23 | **4%** (2× lipat) | idem — dorong semua agen ber-NPWP sejak kontrak |
| **Perorangan** | PPh 21 bukan-pegawai (PMK 168/2023, non-final) | tarif progresif Ps.17 × (50% × bruto) → lapisan awal efektif **2,5%** | idem |
| Agen berstatus **PKP** | PPN jasa keagenan | efektif **11%** (12% × DPP 11/12, PMK 131/2024; faktur pajak kode 04) | Agen MENAGIH kita komisi **+ PPN** (bukan potongan) — anggarkan |

**Dukungan sistem (masuk lingkup F1):** rekap bruto komisi per-agen per-bulan = dasar bukti potong; kolom potongan-pajak di draft payout admin (nilai transfer = bruto − PPh); status pajak agen (badan/perorangan/NPWP/PKP) tercatat di profil agen.
**Catatan:** (a) agen UMKM ber-Surat Keterangan PP 55/2022 bisa berhak potongan final 0,5% — ditangani per-kasus saat onboarding, minta suratnya; (b) angka-angka di atas = riset internet per 2026-07-17 (sumber DJP/Ortax/Klikpajak/DDTC) — peraturan pajak bisa berubah; validasi konsultan sebelum pencairan pertama adalah gerbang F0.

---

## §7 RENCANA KERJA — URUT PRIORITAS (progress monitor; isi REALISASI SAAT ITU JUGA)

> Setiap fase: rencana teknis rinci + daftar file → **ketok owner** → bangun → bukti runtime §3.4 (uji data nyata, bukan build-lulus) → laporan → **izin deploy eksplisit** (§5.0) → REALISASI diisi + sinkron [B21] + §0.

### F0 — PERSIAPAN BISNIS (tanpa kode; boleh paralel dgn F1)
- ✅ **Draf kontrak kemitraan** — disiapkan Claude (mandat owner 17-Jul) = **Lampiran A**. Sisa: review owner + konsultan hukum → template resmi.
- ✅ **Riset pajak komisi** — selesai Claude 17-Jul = **§6b**. Sisa: validasi konsultan pajak + keputusan §8-K5 (siapa mengurus administrasi).
- ⬜ Owner tetapkan angka awal: default komisi agen · tanggal pencairan · ambang minimum (§8-K1).
- **DONE-BILA:** kontrak tervalidasi siap-tanda-tangan + angka awal diketok (tidak memblok F1 DIMULAI; memblok agen pertama DIREKRUT).
- **REALISASI:** 🟡 draf kontrak + riset pajak ✅ 2026-07-17 (sesi yang sama dgn lahirnya SPEC); sisa = validasi eksternal & angka (owner).

### F1 — MESIN UANG (prioritas #1 — program bisa jalan dgn agen pertama TANPA portal)
- **Lingkup:** semua tabel §4 + RLS · kolom kode di form daftar + `?ref=` (5a) · sambungan webhook settlement → ledger (5b) · reversal refund (5e) · **admin panel:** CRUD agen + rate + resume lintas-agen + rinci per-agen + draft-approve-catat pencairan (5c) · **dukungan pajak §6b** (status pajak di profil agen + kolom potongan PPh di draft payout + rekap bruto per-agen) · config ber-label · notifikasi-gagal Telegram.
- **Nilai bisnis:** owner sudah bisa merekrut & membayar agen pertama; laporan sementara via admin.
- **DONE-BILA (ukur, bukan rasa):** ≥1 pendaftaran uji ber-kode terkunci benar · ≥1 pembayaran uji (sandbox/riil kecil) melahirkan baris ledger dgn rupiah PERSIS sesuai §2.1–2.2 (kasus: bulanan-persen · bulanan-flat · tahunan-flat ×12 · dgn-diskon basis-net) · refund uji menghasilkan reversal benar · draft payout bulanan terbentuk & bisa disetujui-dicatat · RLS terbukti (agen tak bisa baca data agen lain — diuji nyata).
- **REALISASI:** ✅ **DIBANGUN + TERVALIDASI LOKAL + DEPLOYED PRODUKSI 2026-07-17 10:36** (izin eksplisit owner; BE OK 10:34 + FE OK 10:36 commit `8705997` situs 200; verifikasi produksi: check-API ✓, kolom kode di HTML live ✓, /admin/partners ter-guard 307 ✓, /api/partner/op tanpa secret 401 ✓).
  Migrasi **0168 APPLIED ke DB live** (6 tabel + RLS terkunci-total + 9 kenop ber-label; guard identitas v2). `src/billing/partner.py` = SATU otoritas uang (accrual/reversal/payout/pajak-prefill/bank-Fernet) · pengait di `_apply_settlement` (settlement→komisi; refund→reversal; fail-soft BER-ALARM Telegram) · endpoint `mv-webhook /api/partner/op` · form daftar +kolom kode+`?ref=`+cek-hidup `/api/partner/check` · route signup: validasi→tolak-di-titik-input→kunci atribusi (idempotent; used_count naik hanya saat baris baru; gagal-tulis tercatat `admin_audit`) · admin **/admin/partners** (KPI+tabel agen+drawer rinci+form+rekening terenkripsi+gerbang pencairan draft→approve→paid) via design system existing (1-nuansa §3.9).
  **BUKTI runtime (data nyata DB live): uji Python 18/18 LULUS** — 4 kasus rupiah-PERSIS ✓ (100rb/50rb/600rb/80rb) · reseller-info ✓ · addon & tanpa-kode TIDAK berkomisi ✓ · idempoten ✓ · refund pra-bayar saling-meniadakan ✓ & pasca-bayar jadi pengurang ✓ · net-negatif digulung ✓ · draft→approve(lock 2 baris)→paid ✓ · pajak prefill 2%/2,5% presisi ✓ · bank terenkripsi+reveal ✓ · RLS anon buta 6/6 tabel ✓ · data uji bersih (0 sisa). **Rantai FE nyata (next start lokal + curl): check valid/invalid ✓ · signup kode-salah DITOLAK 400 dwibahasa ✓ · signup nyata ber-kode → atribusi TERKUNCI benar ✓ · kirim-ulang idempoten (used_count tetap 1) ✓ · user uji auth DIHAPUS bersih.** tsc 0 error · next build lulus (route /admin/partners + /api/partner/check di manifest) · webhook app terkonstruksi dgn route /api/partner/op ✓. **Sisa jujur F1: bukti klik→layar admin UI di produksi (setelah deploy ber-izin) + 1 pembayaran Midtrans nyata pertama sebagai bukti hidup end-to-end.**

### F2 — PORTAL AGEN (prioritas #2)
- **Lingkup:** pintu masuk agen (path/subdomain = ketok §8-K3) · login · **dasbor:** pelanggan bawaannya + status bayar + komisi berjalan + riwayat pencairan · kode & tautan uniknya · dwibahasa penuh.
- **DONE-BILA:** agen uji melihat SEMUA angka yang identik dgn admin rinci-per-agen (satu sumber, §1f) · uji-silang isolasi antar-agen · rantai penuh klik→layar dibuktikan (§3.4).
- **REALISASI:** ✅ **DIBANGUN + TERVALIDASI LOKAL 2026-07-17 (ketok owner "ya" + K2/K3/K8); ⛔ BELUM DEPLOY (gerbang §5.0).** Nol migrasi (fondasi F1 cukup; `agent_users` dibatalkan → `agents.user_id`). Terbangun: gate middleware `/agent` (cermin gate admin; agen⇄tenant⇄admin saling terlempar ke wilayahnya) · `/agent/login` (email+password, tolak-dini non-agen) · `/agent/setup` (set password pasca-undangan) · portal `(portal)/layout+AgentShell` (topbar Partner, dwibahasa, tema) · dasbor (KPI · kode+tautan ber-tombol-salin · tenant bawaan ber-label-seperlunya · pencairan · riwayat komisi · rekening tersamar) · `/api/agent/overview` (SATU pintu, filter paksa dari sesi — tabel sumber PERSIS sama dgn admin §1f) · `requireAgent` guard · admin: tombol **Undang login portal** + route invite (buat user role `agent` via service_role → tautkan `agents.user_id` → email undangan ber-brand dwibahasa link set-password; email tenant/admin DITOLAK jelas §5g.3). **BUKTI runtime (server nyata `next start` + login session ASLI via @supabase/ssr):** N1 overview anon 401 ✓ · N2 /agent anon→/agent/login ✓ · N3 login publik 200 ✓ · P1-P2 login agen A → overview HANYA data A ✓ · **P3 ISOLASI: agen B HANYA data B ✓** · P4 halaman /agent render nama A ✓ · N4 user non-agen 403 ✓ · N5 non-agen /agent→/dashboard ✓ · N6 agen ke /dashboard→dilempar /agent ✓ · P5-P6 invite: 200 + user role `agent` + `user_id` tertaut ✓ · N7 invite tanpa admin 401 ✓ · R1 regresi F1 check ✓. tsc 0 error · build lulus (route /agent, /agent/login, /agent/setup, /api/agent/overview di manifest) · aktor uji dibersihkan total (0 sisa). **Sisa jujur: bukti klik→layar di produksi pasca-deploy (owner).**

### F3 — RESELLER (prioritas #3)
- **Lingkup:** tautan pendaftaran-mandiri per agen + antrean persetujuan (5f) · kode per reseller · agen menyetel rate reseller (Rp/%) dari dasbornya · kinerja per-reseller di dasbor agen · **hitungan komisi reseller per periode + Export Excel transfer-massal** (5d) · **portal reseller:** login + pencapaian miliknya per bulan · rekening terenkripsi.
- **DONE-BILA:** alur daftar→pending→disetujui→kode aktif diuji penuh · tenant uji via kode reseller ter-atribusi ke reseller DAN agen induk · Excel terbuka benar di Excel/Sheets dgn kolom siap-transfer & angka cocok ledger · reseller uji hanya melihat miliknya (uji isolasi).
- **REALISASI:** ✅ **DIBANGUN + TERVALIDASI LOKAL 2026-07-17 (ketok owner; 20 uji runtime); ⛔ BELUM DEPLOY (BE+FE — gerbang §5.0).** Nol migrasi. **BE:** `partner.py` +`set_reseller_bank`+`reseller_monthly_breakdown` (satu otoritas; bank via Fernet) + 2 op `/api/partner/op`. **FE:** tautan rekrut per-agen (`join_code`, bisa diganti) + form publik `/agent/join/[kode]` (rekening dienkripsi; gagal-enkripsi = pendaftaran dibatalkan UTUH) + route register publik (anti-dobel) · portal agen halaman **Reseller** (antrean setujui/tolak · rate Rp/% auto-save · kinerja per-periode · kirim-ulang undangan · suspend-cascade kode) + nav shell · **Export Excel** `.xlsx` exceljs (no-rek format TEKS — nol-depan aman; total = ledger) · approve = lahirnya login reseller (role `reseller`, kode unik anti-salah-ketik, email undangan ber-brand; email peran-lain DITOLAK) · portal reseller `/reseller` (login/setup/shell/dasbor: pencapaian per-bulan §1e, kode+tautan, catatan jujur "pembayaran oleh agen") + `/api/reseller/overview` + `requireReseller` + gate middleware (join publik dikecualikan eksplisit). **BUKTI (20 uji, server FE+BE webhook lokal nyata, sesi login asli):** daftar publik ✓ (dobel 400 ✓, rekening TERENKRIPSI di DB ✓, gagal-enkripsi rollback ✓ [terjadi alami saat webhook belum hidup]) · setujui → status+role+kode+rate ✓ · **tenant signup NYATA bawa kode reseller → atribusi DUA ARAH (reseller+agen induk) ✓ → komisi dua-tingkat dari mesin F1: agen 100rb + reseller 25rb PERSIS ✓** · kinerja periode API ✓ · **Excel di-parse balik: no-rek `0123456789` UTUH + total cocok ledger ✓** · overview reseller-1 hanya miliknya ✓ · **ISOLASI reseller-2 kosong ✓** · gerbang lintas-peran 6 arah ✓ (incl. hop-2 anti-loop) · regresi F1+F2 ✓ · cleanup 0 sisa. tsc+build lulus (9 route baru di manifest). Dependency baru: `exceljs` (ketok owner). **Sisa jujur: bukti klik→layar produksi pasca-deploy.**

### F4 — PELENGKAP (prioritas #4 — setelah program hidup)
- **Lingkup:** agen mendaftarkan pelanggan langsung dari dasbornya (jualan tatap muka) · notifikasi Telegram ke agen saat komisi lahir/cair · rekap tahunan utk pajak · otomasi pengingat tanggal pencairan ke owner.
- **DONE-BILA (ditetapkan saat eksekusi):** token agen valid & verifier lama tetap menolaknya · linker mencatat chat agen · notif menempel TANPA mengganggu jalur uang (uji chat-palsu) · pengingat maks 1×/periode · connect/disconnect dari dasbor teruji · rekap pajak xlsx terbuka benar · daftar-pelanggan memakai jalur signup resmi ber-kode.
- **REALISASI:** ✅ **DIBANGUN + TERVALIDASI LOKAL 2026-07-17 (ketok owner "d dan c, telegram pakai cara panel tenant"); ⛔ BELUM DEPLOY (BE+FE — gerbang §5.0).** Migr **0169 APPLIED** (`agents.telegram_chat_id`). **(1) Telegram agen = mekanisme 1-klik tenant PERSIS** (arahan owner): token varian `ag`+uuid (≤64 char; verifier lama menolaknya — kompatibel-mundur TERUJI) · linker cabang agen · endpoint link menerima `agent_id` · tombol Hubungkan/Putuskan di dasbor agen (poll 3s×40 pola tenant) · notif ke agen saat **komisi lahir** (di mesin uang, fail-soft — T4: uang tetap tercatat walau Telegram error) & saat **cair** (mark_paid). **(2) Rekap pajak tahunan** admin: `tax-recap?year=` → xlsx per-agen per-periode PAID (bruto·PPh·bersih·NPWP) + tombol di halaman Partner. **(3) Agen daftarkan pelanggan** dari dasbor: form email+password-sementara → jalur `/api/auth/signup` resmi dgn kode agen (atribusi otomatis; email konfirmasi ke pelanggan). **(4) Pengingat pencairan owner**: `maybe_send_payout_reminder` menumpang loop payment_reconciler (marker persisten `ops_partner_reminder_last` — maks 1×/periode; nol-komisi = tanpa kirim). **BUKTI: BE 6/6** (T1 fail-soft tanpa-chat · T2 linker agen catat chat · T3 chat-palsu fail-soft · T4 komisi 50rb utuh walau notif gagal · T5 draft→approve→paid+notif [insiden uji: 50rb<ambang DIGULUNG = sistem benar] · T6 pengingat 1×) **+ FE 6/6 server nyata** (U1/U2 anon 401 · U3 URL t.me ber-token `ag` · U4/U5 connect→disconnect · U6 xlsx rekap terbuka benar) · cleanup 0 sisa · py_compile+tsc+build lulus. **PLUS (d) ketok owner: `deploy_fe.sh` + langkah `npm install` lockfile pra-build** (anti insiden exceljs terulang; aktif setelah BE deploy menarik repo worker).

**Urutan tidak boleh dibalik:** F1 tanpa portal tetap menghasilkan uang & kepercayaan; portal tanpa mesin-uang = etalase kosong.

---

## §8 KEPUTUSAN MASIH TERBUKA (tanya owner TEPAT saat fasenya — jangan diasumsikan)

| # | Keputusan | Dibutuhkan saat |
|---|---|---|
| K1 | Angka default: komisi agen (Rp/% berapa) · ambang minimum pencairan · tanggal pencairan | F0/F1 (semuanya kenop config — bisa diisi belakangan tanpa ubah kode) |
| K2 | ✅ **DIKETOK 2026-07-17: "MesinViral Partner"** | selesai |
| K3 | ✅ **DIKETOK 2026-07-17: path `mesinviral.com/agent`** (nol perubahan nginx) | selesai |
| K4 | Kebijakan agen `suspended`: komisi berjalan dibekukan atau tetap cair utk tenant lama? | F1 (default rancangan: tetap cair — atribusi & ledger sah; pembekuan = keputusan owner per-kasus) |
| K5 | Administrasi pajak: siapa yang MENGURUS (owner sendiri via Coretax vs konsultan) + validasi angka §6b. *(Memotong PPh = wajib hukum, bukan pilihan — yang diputuskan hanya pengurusnya.)* | F0, sebelum pencairan pertama |
| K6 | Pembayaran NON-langganan (mis. custom-niche kelak) ikut berkomisi? | Default rancangan: **TIDAK** (§5g.10) — ubah = ketok owner |
| K7 | Nasib komisi saat kontrak agen BERAKHIR (berhenti seketika · masa transisi N bulan · tetap utk tenant existing?) | F0/F1 — Pasal 10 draf kontrak memakai placeholder pilihan ini |
| K8 | ✅ **DIKETOK 2026-07-17: DITUNDA/TIDAK PERLU** — login agen TANPA Google (email+password via `agents.user_id`); atribusi tenant tetap via form email + `?ref=` saja. Bila kelak mau dukung jalur Google utk tenant beratribusi = ketok baru | selesai |

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

## §9d PANDUAN = TOMBOL HELP (arahan owner: bukan file lepas) — DUA panduan
- **Panduan OWNER** (siapkan→rekrut→pencairan bulanan+situasi lain) = `apps/web/public/panduan/program-agen.html` → tombol **"Panduan"** di header **Admin → Program Agen**. ✅ LIVE 2026-07-17 20:17 (`be79406`).
- **Panduan AGEN** (masuk portal→sebar kode→rekrut reseller→komisi&pencairan+FAQ) = `apps/web/public/panduan/agen.html` → tombol **"Panduan"** di nav **portal agen** (`/agent`). URL publik bisa dikirim ke CALON agen saat rekrut. Dibangun 2026-07-17; tsc/build lulus; statis tersaji 200 + owner-guide nol regresi. ⛔ menunggu deploy FE.
- Keduanya HTML mandiri satu-set (desain sama, dwibahasa-tema, nol dependensi), publik tanpa auth (owner: "tidak ada yang rahasia"). File HTML lepas repo-root DIBUANG (anti-fosil §3.2).

## §9c KONFIGURASI ADMIN TERPUSAT 2026-07-17 (teguran owner: kenop berserakan)
- **Masalah:** 9 kenop partner + 3 penanda `ops_*` jatuh ke kelompok "Lainnya" di Konfigurasi Sistem sbg nama mentah tanpa label — "asal jadi, tidak world-class". Akar: F1–F4 hanya menyisipkan baris DB, tak menyelesaikan sisi layar admin.
- **Fix (1 file `admin/(panel)/app-config/page.tsx` + guard 1 file route):** kartu **"Program Agen (Partner)"** = 9 kenop ber-label+deskripsi dwibahasa, satuan benar (tgl/Rp/%), tipe komisi = **dropdown** percent/flat_idr (anti salah-ketik). Kartu **"Internal — ditulis mesin"** = 3 penanda (`ops_partner_reminder_last`, `ops_tg_update_offset`, `ops_drift_alarm_last_at`) READ-ONLY (🔒, tampil demi transparansi) + **guard PATCH server menolak `ops_*`** (pertahanan berlapis; mesin menulisnya via klien Python, bukan route ini).
- **Bukti runtime (sesi admin nyata):** GET 9 partner+3 ops hadir ✓ · PATCH `ops_*` → 400 `readonly_key` ✓ · PATCH partner_payout_day & tipe-komisi(value_text) sah ✓ · mapping deterministik 9→G_PARTNER 3→G_INTERNAL ✓ (render CSR — kartu dirakit browser; owner lihat langsung) · nilai uji dipulihkan (tgl 5, percent) · admin uji dihapus · tsc+build lulus. Aturan dipatri di CLAUDE.md §3.3.
- **Verifikasi pra-deploy (teguran owner "pastikan tak ada bug"):** R1 hanya 3 key `ops_` = penanda mesin (guard tak sentuh setelan sah) · C3 nol salah-eja meta · C4 nol kenop yatim di "Lainnya" · C5 nol meta-key tanpa padanan DB (regresi lintas-grup) · REG1 kenop biasa tetap editable (bukan readonly_key) · REG2 auth utuh 401. **✅ DEPLOYED PRODUKSI 2026-07-17 19:51 (izin owner "deploy FE", commit `11f2788`, situs 200, /admin/app-config ter-guard 307).**

## §9b AUDIT TERPADU A–Z 2026-07-17 (mandat owner "pastikan tidak ada error/bug")
- **Lingkup:** DB live (higienitas+konstrain) · seluruh jalur uang (accrual/reversal/payout) · gerbang & isolasi · integrasi (signup, Midtrans, Telegram, Excel) · kesehatan produksi (log worker, endpoint ter-guard).
- **Bersih:** 6 tabel partner = 0 sisa uji · 0 user-uji auth · 9+1 kenop benar · unique/FK/PK terpasang · log worker nol error partner · marker pengingat sudah ditulis PRODUKSI sendiri (bukti F4 hidup).
- **Temuan & status:** **T-1 KRITIKAL FIXED+TERUJI A1–A4**: refund di jendela approve→paid dulu HANGUS (mark_paid menimpa status by payout_id) → kini `approved` diperlakukan spt `paid` (reversal tinggal accrued = pengurang bulan berikut). **T-2 FIXED**: ganti-kode (agen&reseller) — delete kode lama tak dicek → bisa dua-kode senyap; kini rollback+pesan jujur. **T-3 FIXED**: breakdown reseller gagal-ambil dulu tampil "Rp 0" palsu → kini "—"+catatan (anti §0.6 tampilan). **T-5 FIXED**: satu email jadi reseller di 2 agen → portal cuma tampilkan satu; kini DITOLAK jelas saat approve. **T-4 = KEBIJAKAN dipatri** (§5e partial_refund tarik penuh). **Informasional (bukan bug):** approve menghitung-ulang baris terkini (komisi baru masuk antara draft & approve ikut terbayar — angka final yang tampil pasca-reload); used_count berpotensi undercount pada signup serentak (freeze tetap dijaga FK atribusi).

## §10 CHANGELOG
- **2026-07-17 (3)** — +§3.9 SATU-NUANSA UI (wajib pustaka UI existing `apps/web`) & +§3.10 aturan-kerja-wajib per-sesi (mandat owner "LANJUTKAN + 1 nuansa + WAJIB aturan kerja").
- **2026-07-17 (2)** — DIMATANGKAN (mandat owner "evaluasi lagi, jangan ada yang terlewat/confuse/ambigu, seluruh area terinventarisir" + "sesi berikutnya fokus selesaikan modul ini"): +§3b inventaris permukaan (worker produksi TIDAK tersentuh — eksplisit) · +§5g 11 aturan operasional rinci (onboarding agen admin-only, kode unik-global & beku-setelah-dipakai, 1-email-1-peran, cut-off periode, pembulatan, cascade suspend, retensi data, agen-sekaligus-tenant, komisi hanya-langganan) · +§6b pajak (riset: PPh 23 2%/4%, PPh 21 bukan-pegawai ~2,5%, PPN PKP 11%, dukungan sistem masuk F1) · +Lampiran A draf kontrak 13 pasal · F0 → 🟡 (kontrak+pajak selesai, sisa angka & validasi owner) · §8 +K6/K7, K5 direframe.
- **2026-07-17** — Dokumen lahir (mandat owner "arsitektur lengkap A–Z + rencana kerja urut prioritas, single source of truth & progress monitor"). Seluruh §1–§2 = keputusan owner FINAL dari diskusi 2026-07-16→17 (jenjang 2-tingkat · bayar-ke-kami · selamanya · Rp/% dua-tingkat · pencairan bulanan ber-tanggal-config · reseller dibayar agen + Excel · pendaftaran reseller mandiri ber-persetujuan · admin resume+rinci · 5 aturan sengketa · penolakan §1g). Implementasi belum dimulai.

---

## LAMPIRAN A — DRAF PERJANJIAN KERJASAMA KEAGENAN PEMASARAN

> ⚠️ **Status draf:** disusun sistematis selaras seluruh keputusan §1–§2 dokumen ini, namun **BUKAN nasihat hukum** — wajib direview konsultan hukum owner sebelum dipakai. Bagian `[...]` = diisi per-agen. Bagian bertanda **[K7]** menunggu keputusan owner §8-K7.

### PERJANJIAN KERJASAMA KEAGENAN PEMASARAN — MESINVIRAL

Perjanjian ini dibuat pada tanggal `[tanggal]` oleh dan antara:
1. **`[PT/badan usaha owner]`**, penyelenggara platform **mesinviral.com** ("**MesinViral**"); dan
2. **`[nama perusahaan/perorangan agen]`**, `[alamat]`, NPWP `[nomor / "tidak memiliki"]` ("**Agen**").

**Pasal 1 — Definisi.** (a) **Platform** = layanan SaaS mesinviral.com beserta sistem keagenannya; (b) **Tenant** = pelanggan yang berlangganan Platform; (c) **Reseller** = penjual yang direkrut & disetujui Agen melalui sistem; (d) **Kode** = kode unik atribusi milik Agen/Reseller; (e) **Komisi** = imbalan bagi-hasil sebagaimana Pasal 5; (f) **Periode** = satu bulan kalender berdasarkan tanggal pembayaran diterima (settlement); (g) **Sistem** = pencatatan elektronik MesinViral (dasbor, buku besar komisi, laporan) yang menjadi sumber data tunggal Perjanjian ini.

**Pasal 2 — Ruang Lingkup & Sifat Hubungan.** (1) MesinViral menunjuk Agen secara **non-eksklusif** untuk memasarkan Platform. (2) Agen adalah **mitra usaha independen** — bukan pegawai, perwakilan hukum, atau kuasa MesinViral; Agen tidak berwenang membuat perikatan apa pun atas nama MesinViral. (3) Seluruh Tenant adalah pelanggan MesinViral: membayar langsung ke MesinViral dengan harga resmi dan dilayani oleh MesinViral.

**Pasal 3 — Kewajiban Agen.** (1) Menanggung **seluruh biaya pemasarannya sendiri** (iklan, konten promosi, perekrutan Reseller) tanpa hak penggantian. (2) Materi promosi wajib **akurat & jujur**: dilarang menjanjikan penghasilan/hasil tertentu, klaim fitur yang tidak ada, atau mengatasnamakan MesinViral di luar pedoman. (3) Mematuhi peraturan periklanan, anti-spam, dan perlindungan konsumen yang berlaku. (4) Tidak mengubah/menyimpangkan harga resmi Platform. (5) **Bertanggung jawab penuh atas Reseller-nya**, termasuk pembayaran komisi Reseller (Pasal 8). (6) Menjaga nama baik MesinViral.

**Pasal 4 — Kewajiban MesinViral.** (1) Menyediakan Sistem: dasbor Agen, Kode & tautan, pencatatan atribusi & komisi yang transparan, perhitungan komisi Reseller beserta berkas ekspor. (2) Membayar Komisi sesuai Pasal 5. (3) Melayani & mendukung Tenant sepenuhnya. (4) Memberitahukan perubahan harga/paket yang memengaruhi perhitungan Komisi.

**Pasal 5 — Komisi & Pembayaran.** (1) Besaran komisi Agen tercantum pada **Lampiran-1** (bentuk: Rupiah tetap per bulan-langganan ATAU persentase). (2) Komisi timbul **hanya** atas pembayaran Tenant beratribusi Agen yang **berhasil diterima** (settlement); dasar persentase = nilai yang benar-benar diterima setelah diskon. (3) Pembayaran di muka multi-bulan: komisi Rupiah-tetap dihitung per bulan-langganan yang dibayar. (4) Pencairan **satu kali per bulan** pada tanggal yang ditetapkan MesinViral dalam Sistem, atas seluruh komisi Periode sebelumnya, setelah dikurangi pajak (Pasal 7) dan koreksi ayat (5); nilai di bawah ambang minimum digulung ke bulan berikutnya. (5) Pengembalian dana (refund)/pembatalan membatalkan komisi terkait; bila telah dibayarkan, menjadi **pengurang pencairan berikutnya**. (6) Komisi berlaku berkelanjutan selama Tenant bersangkutan terus membayar **dan Perjanjian ini berlaku** [K7: ketentuan pasca-berakhir — lihat Pasal 10 ayat 4].

**Pasal 6 — Atribusi Pelanggan.** (1) Tenant terhitung bawaan Agen **hanya apabila** mencantumkan Kode Agen/Reseller-nya saat pendaftaran; atribusi bersifat **permanen** sejak pendaftaran. (2) Pendaftaran tanpa Kode bukan bawaan pihak mana pun dan tidak dapat diklaim kemudian. (3) Data Sistem (buku besar) = **satu-satunya acuan** penghitungan; kedua pihak dapat melihat angka yang sama di dasbor masing-masing.

**Pasal 7 — Pajak.** (1) MesinViral memotong PPh atas Komisi sesuai peraturan yang berlaku menurut status Agen (badan/perorangan/NPWP) dan menerbitkan bukti potong. (2) Agen berstatus PKP menerbitkan faktur pajak atas Komisi + PPN sesuai ketentuan. (3) Masing-masing pihak menanggung kewajiban pajaknya sendiri di luar mekanisme pemotongan tersebut.

**Pasal 8 — Reseller.** (1) Reseller mendaftar melalui tautan Sistem milik Agen dan hanya aktif setelah **disetujui Agen**. (2) Besaran & **pembayaran komisi Reseller sepenuhnya kewajiban Agen**; MesinViral hanya menyediakan perhitungan & berkas ekspor sebagai alat bantu. (3) Perbuatan Reseller dalam memasarkan Platform = tanggung jawab Agen sebagaimana perbuatannya sendiri.

**Pasal 9 — Kerahasiaan & Data Pribadi.** (1) Agen/Reseller hanya menerima data Tenant seperlunya (label nama, status pembayaran, nilai komisi) dan dilarang menggunakannya di luar Perjanjian ini. (2) Kedua pihak tunduk pada UU Perlindungan Data Pribadi; data rekening Agen/Reseller disimpan terenkripsi oleh MesinViral. (3) Kewajiban ini bertahan setelah Perjanjian berakhir.

**Pasal 10 — Jangka Waktu & Pengakhiran.** (1) Berlaku `[12 bulan]` sejak ditandatangani, diperpanjang otomatis kecuali salah satu pihak memberitahukan sebaliknya `[30 hari]` sebelumnya. (2) Masing-masing pihak dapat mengakhiri dengan pemberitahuan tertulis `[30 hari]`. (3) MesinViral dapat mengakhiri/menangguhkan **seketika** bila Agen/Reseller-nya melanggar Pasal 3, 6, 8, atau 9. (4) **[K7 — pilih salah satu]** Akibat pengakhiran terhadap komisi berjalan: (a) komisi berhenti pada tanggal berakhir; ATAU (b) komisi Tenant existing tetap dibayar selama `[N bulan]` masa transisi; ATAU (c) komisi Tenant existing tetap berjalan sepanjang Tenant membayar, kecuali pengakhiran karena pelanggaran (huruf mana pun: pelanggaran = komisi berhenti seketika). (5) Kewajiban yang telah timbul sebelum pengakhiran tetap diselesaikan.

**Pasal 11 — Merek & Materi.** Agen boleh memakai nama/logo MesinViral hanya untuk memasarkan Platform sesuai pedoman selama Perjanjian berlaku; hak itu berhenti otomatis saat berakhir.

**Pasal 12 — Keadaan Kahar.** Kegagalan akibat keadaan di luar kendali wajar (bencana, gangguan infrastruktur luas, perubahan regulasi) tidak dianggap wanprestasi; pihak terdampak memberitahu pihak lain segera.

**Pasal 13 — Hukum & Penyelesaian Sengketa.** Perjanjian tunduk pada hukum Republik Indonesia. Sengketa diselesaikan musyawarah `[30 hari]`; bila gagal, melalui `[Pengadilan Negeri (domisili owner) / arbitrase]`. Bila terdapat perbedaan antara pemahaman para pihak dan catatan Sistem mengenai angka, catatan Sistem yang berlaku (Pasal 6 ayat 3).

**LAMPIRAN-1 (per-Agen):** bentuk & besaran komisi: `[Rp ____ per bulan-langganan / ____% ]` · ambang minimum pencairan: `[Rp ____]` · tanggal pencairan bulanan: `[tgl __]` · PIC & rekening Agen: `[...]` · status pajak: `[badan ber-NPWP / perorangan / PKP]`.

*Ditandatangani oleh para pihak dalam keadaan sadar tanpa paksaan.*
`[MesinViral]` ——— `[Agen]`
