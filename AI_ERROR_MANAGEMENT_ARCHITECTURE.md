# MANAJEMEN ERROR AI — ARSITEKTUR (SINGLE SOURCE OF TRUTH)

> **🔍 AUDIT DOKUMEN-vs-KODE 2026-08-03 — 4 drift ditemukan & diperbaiki (§11).** Dua di antaranya membuat
> dokumen ini menyatakan **perilaku yang salah** (kelas hilang dari tabel · daftar FAST_FAIL kurang satu),
> satu menyandarkan bukti pada berkas uji yang **tidak ada**. **Kini dijaga MESIN:**
> `tests/test_ssot_error_mgmt.py` membandingkan dokumen ini dengan kode setiap kali suite dijalankan —
> bergeser tanpa pasangannya = MERAH (§10). Registry §4 diperiksa baris demi baris: semua klaim ✅ terbukti.
> **Baca §8 (celah terbuka) & §9 (kontrak tampilan per-kelas) sebelum menyentuh UI kegagalan produksi.**

> **Status:** ✅ **LIVE PRODUKSI 2026-07-18 01:04** (izin owner "deploy BE", commit `99b1c32`, mv-worker/webhook active, health 200; verifikasi: nol error import/ErrorClass, 3 thread produksi start bersih). Taksonomi + adapter EL-direct terverifikasi + circuit-breaker semantik + persistensi migr 0170.
> **Fungsi dokumen:** peta + tata-kelola. **Kode = otoritatif; dokumen = peta + bukti.** Kontradiksi → kode menang; perbarui dokumen SAAT ITU.
> **⚖️ ATURAN EMAS — DIPERBARUI 2026-08-11 (ketok owner): SUMBERNYA DOKUMEN RESMI PENYEDIA, BUKAN MENUNGGU KERUSAKAN.**
> Pemetaan kode error **WAJIB diambil dari dokumentasi resmi penyedia, dan WAJIB dibaca SEBELUM penyedia itu
> dipakai produksi.** Setiap penyedia AI besar menerbitkan tabel kode galatnya. **Menunggu tenant rusak dulu baru
> memetakan = PELANGGARAN.** Tiap baris pemetaan wajib mencantumkan **tautan sumber + tanggal dibaca** (§4 kolom Bukti).
> **Sampel nyata tetap dipakai — tapi bukan sebagai IZIN memetakan**, melainkan untuk memastikan **BENTUK jawaban di
> kabel** (mis. Cloudflare mengirim galat sebagai DAFTAR `{"errors":[{"code":…}]}`, bentuk yang classifier lama tak mengerti).
> **Yang HARAM adalah MENEBAK:** dari ingatan, dari pola penyedia lain, atau dari kode HTTP semata.
> **Bukti kenapa menebak berbahaya:** Cloudflare memakai **HTTP 429 untuk DUA hal berlawanan** — `3036` jatah gratis
> harian habis (**berhenti**, pulih besok UTC) vs `3040` kapasitas penuh sesaat (**ulangi**). Menebak "429 = jatah habis"
> akan menghentikan produksi channel tenant atas dasar yang **salah**. Pola sama di Gemini: `quota_exceeded` (harian,
> berhenti) vs `rate_limit_exceeded` (per-menit, ulangi). Sampel tunggal pun tak menyelamatkan — ia hanya menampakkan
> satu dari dua, dan yang kedua tak akan pernah kita duga.
> Kode yang **tidak ada di dokumen resmi dan tanpa sampel** → `UNKNOWN` = aman (retryable, perilaku lama).
> **Update kode + dokumen dalam commit yang SAMA** (anti-drift, disiplin CLAUDE.md §3.7).
> **📍 LETAKNYA SATU: `src/providers/galat_registry.py`** (sejak 12-Agu, ketok owner: *"pastikan tidak
> ada jalur lain yang menghandle AI error management"*). Sebelumnya EMPAT penilai tersebar → gejala
> IDENTIK ditangani berbeda-beda per vendor/komponen. **Menambah vendor/model = menambah BARIS DATA di
> berkas itu, NOL koding.** Tiap baris membawa `sumber` + `dibaca`. Penilai kedua di berkas lain =
> **uji MERAH** (`tests/test_galat_generik.py`).
> **🔀 AGREGATOR** (fal.ai; blackbox.ai dsb. ke depan) meneruskan galat vendor DI BALIKNYA → ditandai
> `agregator: True`; tipe `downstream_service_*` memicu penyisiran ulang lintas-vendor.

---

## §1 Prinsip & taksonomi
Sistem berpikir dalam **MAKNA** error, bukan teks/HTTP-status mentah. Dua dimensi ORTOGONAL pada `PipelineError` (`src/exceptions.py`):
- **`category`** = DI MANA gagal (tts/llm/visual/render/publish) — sudah ada.
- **`error_class`** (`ErrorClass`) = KENAPA gagal (makna) — BARU.

**TUJUH kelas** (`src/exceptions.py` — dijaga uji anti-drift `tests/test_ssot_error_mgmt.py`):

| ErrorClass | Arti | Sikap | Pulih sendiri? |
|---|---|---|---|
| `ACCOUNT_BILLING` | pembayaran/langganan penyedia gagal | **non-retryable → REM SEGERA** | ❌ butuh tindakan tenant |
| `QUOTA_EXHAUSTED` | kredit/kuota penyedia habis | **non-retryable → REM SEGERA** | ❌ butuh isi ulang |
| `AUTH_INVALID` | kunci/koneksi ditolak PERMANEN (mis. OAuth `invalid_grant`) | **non-retryable → REM SEGERA** | ❌ butuh kunci baru |
| `MODEL_UNAVAILABLE` | model dipensiunkan/ditutup vendor (404) | **non-retryable → REM SEGERA** | ❌ butuh ganti model |
| `RATE_LIMIT` | throttle (429) — sesaat ATAU batas harian | retryable → toleransi normal | ✅ ya (menit s/d ganti hari) |
| `TRANSIENT` | jaringan/5xx/timeout/sintesis terpotong | retryable → toleransi normal | ✅ ya (biasanya menit) |
| `UNKNOWN` | belum dikenali | retryable (DEFAULT AMAN) | ❓ tak diketahui |

**`FAST_FAIL = {ACCOUNT_BILLING, QUOTA_EXHAUSTED, AUTH_INVALID, MODEL_UNAVAILABLE}`** (`src/exceptions.py`).
Awal (2026-07-17): "kredit habis / masalah pembayaran". **+`AUTH_INVALID` 2026-07-18** (ketok owner "rem
segera, jangan bakar duit tenant", [B11] 3.2). **+`MODEL_UNAVAILABLE` 2026-07-20** (model dipensiunkan
vendor — mustahil sembuh dengan diulang). Menambah/menghapus kelas = ubah SATU set ini.

> **Kolom "Pulih sendiri?" bukan hiasan.** Ia pembeda yang menentukan APA yang boleh dikatakan sistem
> kepada tenant: kelas yang pulih sendiri berarti "tunggu, jangan ubah apa pun"; yang tidak berarti
> "ada yang harus Anda kerjakan". Dipakai UI pemulihan channel — **per KELAS, tidak pernah per nama
> penyedia** (penyedia akan terus bertambah; kelas berjumlah tujuh dan stabil). Lihat §9.

## §2 Transport-keyed (bukan merek model)
Klasifikasi menempel pada **transport yang menerima error**, bukan merek model. "Suara ElevenLabs" = model; "API EL" & "API fal" = dua transport → dua kontrak error.
- **EL-direct** → adapter `elevenlabs` → kode native EL → akun ElevenLabs.
- **EL-via-fal** (kelak) → adapter **fal** → amplop error fal → akun fal. **BUKAN** di adapter EL-direct.
- Agregator (fal) = **satu titik billing**: bila fal habis, SEMUA model via fal (TTS+image+video) gagal bersama.

## §3 Aliran error ujung-ke-ujung
> ⚠️ **Anchor baris SENGAJA DIHAPUS 2026-08-03.** Semua nomor baris di versi lama sudah basi
> (pipeline `~275`→ nyata 359/428 · `~636`→747 · producer `:206/:340/:435`→137/397/491) dan justru
> menyesatkan pembaca yang mempercayainya. **Aturan baru: rujuk NAMA fungsi/simbol, bukan nomor baris**
> — nama bertahan melewati penyuntingan, nomor tidak. (CLAUDE.md §1.2 mewajibkan grep ulang; kalau
> tetap wajib di-grep, nomornya tak menambah nilai apa pun.)

1. Adapter tangkap error provider → **penilai TUNGGAL** `galat_registry.golongkan()` (dipanggil lewat pembungkus tipis tiap adapter, mis. `_classify_el_error` di `src/providers/tts/elevenlabs.py`) → `raise TTSError(..., error_class=, human_message=, milik_kita=)`. **Sejak 12-Agu tak ada lagi penilai per-vendor** — satu jalur untuk naskah · suara · gambar · video (dijaga `tests/test_galat_generik.py`).
2. `tts_engine.generate()` **menelan** error TTS (return `"",[]`) TAPI menyimpan `last_error/last_error_class/last_human_error` (`src/production/tts_engine.py` except).
3. `pipeline` STEP 5 lihat audio kosong → `raise TTSError(last_human_error or last_error, error_class=last_error_class, human_message=...)` (`src/orchestrator/pipeline.py`, cari `raise TTSError`).
4. `pipeline` except → `result["error_class"]` + `result["human_error"]` (`pipeline.py`, cari `result["error_class"]`).
5. `producer` catat ke `production_runs.error_class` + `error_message`=pesan manusiawi (`src/orchestrator/producer.py` `_record_production_run` + 2 insert direct — cari `"error_message"`). **Reorder:** catat-run SEBELUM `mark_failed` (fast-fail deterministik).
6. Circuit-breaker: `inventory.latest_failure(cid)` → bila `error_class ∈ FAST_FAIL` **rem di streak≥1**; else streak≥`PRODUCER_FAIL_STREAK_STOP`(3) (`producer.py` plan_and_submit).
7. **PESAN SERAGAM SEMUA PERMUKAAN (SSOT tampilan — ditegakkan 2026-07-22):** teks yang tampil ke manusia = **`human_error or error`** yang IDENTIK di setiap permukaan, tak boleh ada jalur bercerita sendiri: (a) `production_runs.error_message` — KETIGA jalur producer (`_record_production_run` scheduled · insert direct-publish · insert direct-test); (b) tabel `videos` (`pipeline` crash-path `write_failed_run`, var `human_err`); (c) Telegram `notify_failure` (var `human_err` sama); (d) FE drawer Runs + halaman detail (baca `production_runs.error_message`). ⚠️ Circuit-break `notify_circuit_break` juga pakai `error_message`. **Sebelum 22-Jul MENYIMPANG:** jalur direct-test & `notify_failure` mengirim `str(e)` mentah → Telegram/DB bisa beda dari layar (celah tampak hanya utk error TERKLASIFIKASI; unknown kebetulan sama). Kini kanonik. `notify_publish_fail` (jalur upload YouTube gagal, `_yt_err`) = konteks berbeda, belum diseragamkan (dicatat jujur — bukan crash produksi).

## §4 REGISTRY penyedia — **DIJAGA MESIN, bukan disalin tangan**

> **📍 RINCIAN KODE ADA DI `src/providers/galat_registry.py`, BUKAN DI SINI.** Sampai 12-Agu tabel ini
> MENYALIN pemetaan kode dari kode program — dan salinan itulah yang melenceng: dua baris sempat
> menyatakan jatah gratis harian sebagai "kredit habis", bertentangan dengan mesin yang berjalan.
> Owner: *"bukankah hal ini sudah dijaga mesin???"* — penjaganya ADA, tapi **tabel ini tak pernah
> masuk daftar periksanya**, jadi hijau padahal isinya salah. Sejak sekarang tabel di bawah
> **dibandingkan otomatis** dengan data registry oleh `tests/test_ssot_error_mgmt.py`:
> penyedia hilang · sumber/tanggal tak cocok · penyedia hantu = **uji MERAH, commit DITOLAK.**

| Penyedia (`provider_key`) | Penanda dipetakan | Sumber | Dibaca |
|---|---|---|---|
| `anthropic` | 11 | [dokumen resmi](https://platform.claude.com/docs/en/api/errors) | 2026-08-12 |
| `cloudflare` | 17 | [dokumen resmi](https://developers.cloudflare.com/workers-ai/platform/errors/) | 2026-08-11 |
| `edge_tts` | 4 | **TIDAK ADA dokumen resmi** | 2026-08-12 |
| `elevenlabs` | 17 | [dokumen resmi](https://elevenlabs.io/docs/eleven-api/resources/errors) | 2026-08-12 |
| `fal` · **AGREGATOR** | 23 | [dokumen resmi](https://fal.ai/docs/documentation/model-apis/errors) | 2026-08-12 |
| `gemini` | 19 | [dokumen resmi](https://ai.google.dev/gemini-api/docs/api-errors) | 2026-08-11 |
| `groq` | 1 | [dokumen resmi](https://console.groq.com/docs/errors) | 2026-08-12 |
| `openai` (alias: `openai_tts`) | 9 | [dokumen resmi](https://developers.openai.com/api/docs/guides/error-codes) | 2026-08-12 |

> **Cara membaca:** "Penanda dipetakan" = jumlah kode/kalimat/penanda-milik-kita yang dikenali untuk
> penyedia itu. Rincian per-kode + alasan tiap pilihan ada di registry, satu tempat, berikut catatan
> keterbatasannya. Menambah vendor/model = **menambah baris data di registry** (§5), lalu baris di
> tabel ini wajib menyusul — dituntut mesin, bukan ingatan.

> **Keterbatasan yang diakui terang (bukan kelalaian kita):** `groq` tidak menerbitkan kode galat
> rinci — hanya status HTTP + kalimat; batas HARIAN vs PER-MENIT hanya terbaca dari kalimatnya.
> `edge_tts` tidak punya dokumen galat resmi sama sekali (layanan tanpa kunci lewat pustaka
> komunitas) — dipetakan hanya sejauh yang jujur: gangguan jaringan = sesaat, setelan kurang = milik kita.

> **Jaring HTTP generik** (401·402·403·404·429, plus 413 = permintaan KITA cacat) berlaku untuk
> penyedia **yang belum ada hari ini** sekalipun, supaya vendor baru langsung berperilaku waras.
> 5xx/408/422/409 SENGAJA DIKELUARKAN — keputusan owner "yang RAGU tetap UNKNOWN" tetap berlaku.

> **Bukti sampel produksi** (sejarah, tidak ikut berubah): fal 403 `Exhausted balance`/`User is locked`
> ×6 (worker.log 14-Jul) · OpenAI `billing_hard_limit_reached` (29-Jul) · OpenAI `insufficient_quota`
> (09-Jul) · `exceeded your current quota` (21-Jul) · Gemini `is no longer available` (21/22-Jul) ·
> `invalid_api_key`/`model_not_found` (20-Jul) · Groq `tokens per day (TPD)` ×8 (01-Agu) ·
> ElevenLabs `payment_issue` (17-Jul) / `quota_exceeded` (16-Jun) · Google OAuth `invalid_grant`.

## §5 Checklist onboarding provider baru (6 langkah) — *urutan diubah 2026-08-11: dokumen resmi DULU*
> **Langkah 1 WAJIB SELESAI SEBELUM penyedia/model dinyalakan untuk tenant.** Menyalakan penyedia yang
> tabel galatnya belum dipetakan = menanam bug yang menunggu tenant menemukannya.
1. **BACA DOKUMEN GALAT RESMI penyedia** — wajib, sebelum dipakai produksi. Catat **tautan + tanggal dibaca**.
2. **Petakan SELURUH kode terdokumentasi** → ErrorClass. **Wajib memisahkan "berhenti" vs "ulangi" walau
   kode HTTP-nya SAMA** (Cloudflare `3036` vs `3040`, keduanya 429 — lihat Aturan Emas §1).
3. **Tangkap sampel nyata bila ada** — untuk memastikan **BENTUK** jawaban di kabel (daftar? objek? di mana kodenya?).
   Tidak ada sampel **BUKAN** alasan menunda pemetaan; ia hanya menuntut pembacaan bentuk yang tahan banting.
4. **Catat di §4** — kolom Bukti = tautan dokumen + tanggal (+ sampel bila ada).
5. **Tambahkan BARIS DATA** di `src/providers/galat_registry.PENYEDIA` (bukan menulis penilai baru —
   penilainya sudah generik & satu). Adapter transportnya cukup raise dgn `error_class` +
   `human_message` + **penanda ASAL** (milik KITA vs milik PENYEDIA — bila dokumen resmi
   menyatakan permintaannya cacat, itu kesalahan KITA dan **haram ditimpakan ke tenant**).
   Bila error ditelan lapisan atas, pastikan propagasi (pola `last_*` tts_engine).
6. **Uji** (unit classifier + persistensi + keputusan berhenti/ulangi) → set status ✅ + commit kode & dokumen BERSAMAAN.

## §6 Tata-kelola (anti-drift, anti-asumsi)
- Pemetaan bersumber **dokumen resmi penyedia (WAJIB)** + sampel nyata (untuk bentuk kabel). **HARAM MENEBAK**; di luar keduanya → `UNKNOWN`.
- **Penyedia/model baru TIDAK boleh dinyalakan sebelum tabel galatnya dipetakan** (§5 langkah 1–2).
- **NOL JALUR KEDUA:** pemetaan penanda→kelas HANYA di `galat_registry.py`. Tabel anjuran per-KELAS
  (mis. `_VISUAL_HUMAN`, `_OPENAI_COMPAT_HUMAN`) tetap sah di adapter karena kalimatnya khas-komponen.
  Dijaga `tests/test_galat_generik.py` (dibuktikan merah untuk 3 bentuk pelanggaran).
- **Jaring HTTP generik SENGAJA SEMPIT** (401·402·403·404·429 + 413=milik-kita). 5xx/408/422/409
  DIKELUARKAN: keputusan owner "yang RAGU tetap UNKNOWN" tetap berlaku; vendor yang dokumennya
  menyebut arti status itu tertangani lewat tabelnya sendiri. Melebarkannya = ubah perilaku-saat-gagal
  = **butuh ketok owner**.
- Kode = otoritatif; dokumen = peta + bukti; sinkron dalam commit yang sama.
- Circuit-breaker TIDAK boleh string-sniffing — hanya baca `error_class` terstruktur.
- Menambah/menghapus kelas fast-fail = ubah `FAST_FAIL` (`src/exceptions.py`) saja.

## §7 Verifikasi — berkas uji NYATA (diperbaiki 2026-08-03)
> ⚠️ **KOREKSI.** Versi lama mengklaim bukti dari `tests/test_errmgmt.py` **13/13** — berkas itu
> **Penjaga yang HIDUP untuk topik ini (wajib lengkap — arah sebaliknya ikut dijaga sejak 12-Agu:**
> **yang ada di repo WAJIB disebut di sini, bukan hanya sebaliknya):**
> `tests/test_ssot_error_mgmt.py` (dokumen vs kode + tabel §4 vs registry) ·
> `tests/test_galat_generik.py` (satu jalur · katalog DB lengkap · jatah berkala · agregator) ·
> `tests/test_setelan_ai_tak_pernah_hilang.py` (setelan AI tak hilang · salah kita jangan ditimpakan) ·
> `tests/test_kelas_error_visual.py` · `tests/test_error_429_generik.py` ·
> `tests/test_openai_compat_error_classes.py`

> **TIDAK ADA di repo**. Entah berganti nama entah tak pernah di-commit; yang jelas, selama berbulan-bulan
> dokumen SSOT ini menyandarkan buktinya pada berkas yang tak bisa dijalankan siapa pun. Diganti dengan
> daftar berkas yang benar-benar ada beserta angka yang benar-benar dijalankan.

| Berkas uji | Jumlah | Yang dijaga |
|---|---|---|
| `tests/test_openai_compat_error_classes.py` | — | classifier OpenAI-compatible: sampel verbatim + regresi UNKNOWN + wiring adapter + rem-1-percobaan |
| `tests/test_error_429_generik.py` | — | 429 level-transport (bukan kalimat vendor) → RATE_LIMIT |
| `tests/test_youtube_auth_invalid.py` | — | `invalid_grant`→AUTH_INVALID; RefreshError lain tetap transien |
| `tests/test_suara_terpotong.py` · `test_suara_naskah_panjang.py` | — | kegagalan suara → TRANSIENT |
| **`tests/test_ssot_error_mgmt.py`** | 9 | **penjaga anti-drift: dokumen ini vs kode** (§10) |
| **`tests/test_pemulihan_channel.py`** | **12** | **[B25] rem menyimpan sebabnya · Telegram bedakan pulih-sendiri · anti-drift `SELF_HEALING` lintas 3 tempat** |
| **Total kelima berkas lama** | **39 lulus** | dijalankan 2026-08-03 |

**Bukti dari PRODUKSI NYATA** (bukan hanya uji) — `production_runs.error_class` sejak migr 0170:
`unknown` 32× · `quota_exhausted` 4× · `rate_limit` 3× · `model_unavailable` 2×. Registry bekerja:
empat kelas berbeda benar-benar terklasifikasi pada trafik sungguhan, bukan semuanya jatuh ke UNKNOWN.

## §8 CELAH TERBUKA yang diketahui (jujur — belum diperbaiki)

### 8a. ~~Rem darurat MEMBUANG kelas errornya~~ — ✅ **DITUTUP 2026-08-03** *(migr 0196 + [B25] A–D)*
> Kelas error kini **disimpan** saat rem menyala (`channels.production_paused_class`), dan alasan yang
> tercatat memuat pesan manusiawi dari kegagalan terakhir untuk **kedua** cabang (rem-cepat & 3-gagal;
> dulu hanya cabang rem-cepat). Layar channel menampilkan **panel pemulihan per-KELAS** yang menjawab
> tiga pertanyaan tenant — apa yang terjadi · apakah pulih sendiri · apa langkah Anda — plus tombol
> **Pulihkan produksi**. Telegram memberi anjuran yang berbeda untuk kelas yang pulih-sendiri vs yang
> menuntut tindakan, dan mengantar ke layar. Layar admin (`/admin/system`) memuat satu daftar seluruh
> channel yang berhenti beserta sebabnya. Sumber "pulih sendiri" = **`SELF_HEALING`** (`src/exceptions.py`),
> dijaga uji anti-drift lintas tiga tempat (kode ↔ dokumen ↔ layar).
> **Bukti:** 22 pemeriksaan klik→layar (7 kelas × judul & status, kelas tak-dikenal, daftar admin), nol
> galat halaman. **Pemulihan tetap keputusan tenant** — sistem tidak pernah melepas rem sendiri karena
> sebab teknis dianggap lewat (arahan owner).
>
> Teks aslinya dipertahankan di bawah sebagai catatan sebab-akibat.

### 8a-lama. Rem darurat MEMBUANG kelas errornya *(ditemukan 2026-08-03)*
`_pause_channel` (`producer.py`) menyimpan `production_paused_reason` sebagai kalimat generik
**"3x produksi beruntun gagal/bermasalah"** — kelas errornya sudah diketahui sistem saat itu
(`inventory.latest_failure()` membacanya untuk memutuskan rem) **tetapi tidak ikut disimpan**.

Akibat nyata, terukur pada tenant berbayar:
- Layar & Telegram hanya bisa menganjurkan tebakan: *"perbaiki penyebabnya (mis. saldo/kredensial AI)"*.
- Tenant tak pernah tahu apakah sebabnya **pulih sendiri** atau **butuh tindakan** — padahal kolom
  itu sudah didefinisikan di §1.
- **Bang Us-Dat** (tenant berbayar) mati **±44 jam** karena jatah harian penyedia habis — sebab yang
  pulih sendiri keesokan harinya. Ia bahkan sudah 2× produksi sukses sesudahnya, remnya tetap menyala.
- **BISIK NUSANTARA** (tenant berbayar) mati dengan pola yang sama sehari kemudian.

Rencana perbaikan (menunggu ketok owner): simpan kelas + rincian saat rem menyala → panel pemulihan
per-KELAS di layar channel → notifikasi selaras → daftar admin. **Pemulihan tetap keputusan tenant**
(arahan owner 2026-08-03: *"jangan otomatis aktif, tapi UI/UX harus user-friendly & well-informed"*).

### 8c. ~~Memulihkan produksi tidak memutus hitungan kegagalan~~ — ✅ **DITUTUP 2026-08-03** *(migr 0197)*
**Dilaporkan owner, terbukti di log produksi.** BISIK NUSANTARA "dihentikan mesin" berulang meski sudah
dipulihkan dan sudah dijalankan uji. Log membuktikan rem menyala **dua kali** hari itu (11:01 & 11:08 WIB)
**tanpa satu pun percobaan produksi baru** — nol `production_runs` dan nol stok bertanggal hari itu.

Sebabnya: hitungan kegagalan beruntun membaca 12 run terakhir channel. Tiga kegagalan dari **hari
sebelumnya** masih terhitung; melepas rem tak menyentuh hitungan itu, jadi siklus penjadwal berikutnya
membaca streak=3 dan langsung mengerem lagi. Bagi tenant: **pemulihan yang hanya ilusi beberapa menit.**

**KEJUJURAN — ini lahir dari jalur buka yang baru ditambahkan** ([B24] tombol "Pulihkan produksi").
Sebelumnya rem HANYA dilepas oleh produksi direct yang SUKSES, dan sukses itu sendiri memutus hitungan,
sehingga masalahnya tak pernah muncul. **Menambah cara melepas rem tanpa ikut memutus hitungannya =
menambah pintu tanpa memasang lantainya.** Komentar `recent_nonready_streak` bahkan sudah merekam
insiden BERPOLA SAMA pada 2026-07-08 — sebab berbeda, akibat identik.

**Perbaikan:** `channels.production_resumed_at` dicatat oleh SETIAP jalur pelepas rem, dalam pernyataan
yang SAMA dengan pelepasannya (dua pernyataan terpisah membuka celah bagi siklus yang lewat di antaranya).
Hitungan kegagalan — dan rem-cepat — hanya membaca kejadian SESUDAH titik itu. Riwayat lama tidak
dipalsukan atau dihapus; ia hanya berhenti dipakai menghukum periode yang sudah ditutup.
**Bukti pada kasus nyata:** streak BISIK 3 → **0** setelah pemulihan, sementara kegagalan dalam 7 hari
tetap terhitung 3 (rem tidak dilumpuhkan). 6 uji unit permanen + verifikasi terhadap data produksi.

**BUKTI RUNTIME DI PRODUKSI (3-Agu):** BISIK dipulihkan 11:48 → penjadwal berjalan **12 siklus** →
**12:09 channel MEMPRODUKSI VIDEO SUKSES** (stok masuk) → rem **tetap mati** setelah 41 menit.
Sebelum perbaikan: rem menyala lagi dalam **1–11 detik** dan channel tak pernah sempat memproduksi.

### 8d. Tiga cacat turunan yang ikut ditemukan & ditutup (3-Agu)
Ditemukan saat menyisir SELURUH permukaan yang menampilkan keadaan rem — bukan hanya halaman channel
(kacamata kuda yang ditegur owner):
1. **Alasan terpotong di tengah kata.** `reason[:300]` memotong buta; setelah alasan menyertakan
   penyebab nyata (pesan penyedia ±275 huruf + awalan ±100) hasilnya melewati batas — terekam di
   produksi berbunyi *"…jatah HARIAN penyedia AI sudah terpa"*. Kalimat terputus membuat pesan yang
   seharusnya menenangkan justru terlihat seperti sistem rusak. → pemotong yang menghormati batas
   kata, ruang cukup agar pesan wajar tersimpan UTUH (terverifikasi 369 huruf, utuh).
2. **Anjuran tebakan jadi fosil.** *"Perbaiki penyebabnya (kredit/konfigurasi)"* dibuat sebelum kelas
   error disimpan; setelah keadaan halted punya panelnya sendiri, teks itu tak pernah tampil di mana
   pun tapi tetap duduk di sumber status bersama — siap dipakai permukaan berikutnya. → dibuang.
3. **Kartu daftar channel bisa memanjang** — menampilkan alasan tanpa batas; satu channel bermasalah
   mendorong kartu lain keluar layar. → dibatasi 3 baris + tooltip.

Diperiksa dan TIDAK bermasalah: **dashboard** (menampilkan alasan lalu mengantar ke halaman channel) ·
**publisher** (sengaja tidak memeriksa rem — stok yang sudah lolos QC tetap boleh terbit; rem
melindungi biaya PRODUKSI, bukan melarang menerbitkan yang sudah jadi).

### 8e. 🔴 JALUR TERMAHAL adalah satu-satunya yang MEMBUANG sebab errornya *(ditemukan 2026-08-04)*
**Terukur, bukan taksiran:**

| Jalur | Titik `raise` | Yang membawa `error_class` | Biaya per kegagalan |
|---|---|---|---|
| Naskah (LLM) | — | `_classify_openai_compat_error` **aktif** (5 pola + lapis HTTP 429) | termurah |
| Suara (TTS) | — | sebagian (`TRANSIENT` di 4 titik) | menengah |
| **Gambar & video** | **38** (`ai_image.py` 21 · `ai_video.py` 17) | **0** | **termahal** |

Setiap `raise VisualError(...)` di jalur visual memakai `error_class` DEFAULT = `UNKNOWN`, padahal pesannya
sudah memuat status HTTP + body vendor utuh. Lebih jauh: **TIGA penangkap di `visual_assembler.py`
(`_try_ai_image` · `_try_ai_video` · penangkap pembangun provider) menelan sebab aslinya** dengan pola identik
`except Exception → logger.error → return []`. Exception-nya tidak diteruskan; pemanggil hanya menerima daftar
kosong, lalu run tercatat dengan kalimat generik *"Visual assembly failed — no clips downloaded"* — jejak
vendornya HANYA ada di worker.log, tidak pernah masuk `production_runs`.
Sampel nyata: `production_runs` 2026-07-29 04:32 (kelas `unknown`).

**Rantai akibat (tiap mata bisa ditelusuri):** batas tagihan/kuota penyedia gambar tercapai → sebab dibuang
→ `error_class=unknown` → `UNKNOWN` = retryable (default aman §1) → mesin mengulang → streak 3 → rem menyala
berbunyi "3× gagal beruntun" → panel pemulihan hanya bisa menampilkan varian kelas-tak-dikenal → tenant tak
tahu ini soal tagihannya. **Biaya sudah terbakar 3× di langkah paling mahal**, dan `FAST_FAIL` — yang ada
justru untuk mencegah itu — tidak pernah terpicu karena kelasnya hilang sebelum sampai ke pengambil keputusan.

**Ini insiden yang MELAHIRKAN arsitektur ini** (RAD 2026-07-17, langganan ElevenLabs gagal bayar → 3× gagal
membakar biaya sebelum rem; §11 entri 18-Jul). Ditutup di jalur naskah, **dibiarkan terbuka di jalur termahal.**

**DIPECAH DUA — SENGAJA, karena aplikasi ini sudah punya tenant berbayar:**

**§8e-A — ✅ DITUTUP 2026-08-04 (nol risiko perilaku).** Sebab penyedia kini DIBAWA sampai ke
`production_runs.error_message`, yaitu teks yang layar detail run & tabel run tampilkan APA ADANYA ke tenant.
`VisualAssembler.last_error` (atribut KELAS — cara objek dibuat tak berubah) direkam di **ketiga** penangkap,
termasuk kedua penangkap BERSARANG yang menangkap lebih dulu daripada penangkap luar (tanpa itu kasus nyata
14-Jul tetap lolos), lalu dirakit `Pipeline._pesan_gagal_visual()`. Dikosongkan di awal tiap `assemble()`
supaya sebab run LAMA tak menempel di run BARU. Cabang mode-tak-dikenal kini menyebut modenya.
**Yang berubah HANYA teks** — mesin tidak mengambil satu keputusan pun dari nilai ini, jadi tak ada channel
yang bisa berhenti karenanya. Pola meniru `tts_engine.last_error_class` / `niche_selector.last_error*`.
**Bukti:** `tests/test_sebab_visual_sampai_ke_tenant.py` — 11 uji, semua sampel VERBATIM dari produksi;
**merah dibuktikan lebih dulu** (11/11 gagal tanpa perbaikan) sebelum hijau dipercaya. Suite 623 → **634**.

**§8e-B — ✅ DITUTUP 2026-08-05, MENGIKUTI PROSEDUR §5 (bukan rancangan baru).**
`classify_visual_error()` di `providers/visual/base.py` — **pola persis `_classify_el_error`** seperti yang
§5.4 perintahkan, satu sumber untuk kedua transport (tabel TIDAK disalin ke `ai_video`/`ai_image`; dijaga uji).
Disambung di 3 titik: `ai_video._generate_fal` submit · `ai_image._generate_fal` submit · `_generate_dalle`
(SDK OpenAI dibungkus — tanpa itu maknanya hilang di lapisan atas).

**KOREKSI PENILAIAN 04-Agu:** catatan sebelumnya di sini menyatakan bagian B "butuh ketok owner karena
memicu `FAST_FAIL`". **Itu salah, dan itu contoh Claude mengarang gerbang yang arsitekturnya tak punya.**
`QUOTA_EXHAUSTED` & `ACCOUNT_BILLING` SUDAH anggota `FAST_FAIL` sejak ketok owner 17-Jul & 18-Jul, dan §6
menyatakan *"menambah/menghapus kelas fast-fail = ubah `FAST_FAIL` saja"* ⇒ memetakan kode penyedia BARU ke
kelas yang SUDAH ADA adalah **langkah 3 prosedur normal**, bukan keputusan produk. Arahan owner sendiri:
petakan per KELAS, jangan per nama penyedia.

**Yang TETAP tidak dipetakan (§5.3 "ragu → biarkan UNKNOWN"):** 500/502 · timeout · respons tanpa
`b64_json`/`url` · unduhan gagal. Salah-petakan lebih berbahaya daripada tak memetakan — kelas fast-fail
menghentikan channel setelah 1 kegagalan. Dijaga uji khusus.

**Dampak:** saat saldo/tagihan penyedia gambar habis, rem menyala setelah **1** kegagalan alih-alih 3 ⇒
biaya tenant tak terbakar 3× pada sebab yang mustahil sembuh dengan diulang — insiden RAD 17-Jul yang
melahirkan seluruh arsitektur ini. **Bukti:** `tests/test_kelas_error_visual.py` (9 uji, sampel VERBATIM
produksi); merah dibuktikan 3 arah (classifier dilumpuhkan · kelas dicabut dari `FAST_FAIL` · error jaringan
salah-dipetakan).

### 8g. UKURAN KEBUTAAN DIAGNOSA — angka, bukan kesan *(diukur 2026-08-04)*
Owner bertanya, wajar: seburuk apa sebenarnya? Dijawab dengan hitungan, bukan adjektiva.

**326 run produksi · 229 sukses (70,2%) · 79 gagal (24,2%).** 79 kegagalan itu, menurut PEMILIK sebabnya:
| Jumlah | Sebab | Milik |
|---|---|---|
| 33 (42%) | kuota/kunci/tagihan/model-pensiun di akun penyedia **tenant** | tenant |
| 15 (19%) | **gerbang mutu kita MENOLAK naskah buruk**, lalu produksi ulang | by design — mesin menolak membakar biaya |
| 26 (33%) | **sebab TERHAPUS** — tak seorang pun bisa tahu | kode kita |
| 3 (4%) | setelan tak cocok yang seharusnya mustahil dipilih (§3.1) | UX kita |
| 2 (3%) | tak tergolong | — |

**26 "bisu" itu nyaris seluruhnya SEJARAH, bukan keadaan sekarang** — dan ini diperiksa dengan aturan
tanggal (§11 04-Agu), bukan ditebak:
- 15 catatan bisu naskah/suara **semuanya bertanggal ≤ 17-Jul**; jalur suara mulai membawa sebab **18-Jul**
  (`99b1c32`), jalur naskah **20-Jul** (`84d9ebb`). Satu hari & dua belas hari SEBELUM perbaikannya.
- 11 sisanya = jalur visual → akarnya dipotong **§8e-A** malam ini.

**UKURAN SEKARANG: dari 42 kegagalan sejak 20-Jul, hanya 1 yang sebabnya terhapus** (2,4%) — yaitu
kegagalan visual 29-Jul, jenis yang §8e-A tutup. **Cara owner memeriksa sendiri:** hitung `production_runs`
berstatus `failed` yang `error_message`-nya PERSIS kalimat pembungkus tanpa rincian
("No topics selected" · "TTS generation failed" · "Visual assembly failed — no clips downloaded").
Angka itu harus tetap 0 untuk run baru; kalau naik, diagnosa melorot lagi.

### 8f. 🔴 DEGRADASI SENYAP pada FRAME PERTAMA (tuas viral) *(ditemukan 2026-08-04, BELUM diperbaiki)*
`visual_assembler._generate_hook_frame` gagal → `logger.warning(... keeping original clips[0])` → video
**tetap dikirim** dengan frame pertama yang lebih buruk, **tanpa notifikasi ke siapa pun**. Frame pertama =
penentu penonton berhenti menggulir; menurunkannya diam-diam melemahkan janji inti produk.

**Terukur di produksi (worker.log, 04-Agu):** **4 gagal dari 181 percobaan = 2,2%.** Empat sebab BERBEDA:
| Sebab | Milik siapa |
|---|---|
| `[Errno 2] No such file: hook_frame_img.jpg` | **kode kita** |
| `FFmpeg image-to-video failed` | **kode kita** |
| `Billing hard limit has been reached` (OpenAI) | akun penyedia tenant |
| `cannot schedule new futures after interpreter shutdown` | worker sedang berhenti (jinak) |

**Kenapa ini pelanggaran, bukan selera:** CLAUDE.md §0.6 — kegagalan komponen = STOP + notifikasi, HARAM
fallback senyap; dan **`PROGRESS.md` kita sendiri menetapkan gerbang validasi "hook_frame generated tanpa
warning"**, jadi kegagalan ini pernah diperlakukan sebagai CACAT. Toleransi ini masuk lewat commit fitur
(`6a6da40`), **bukan lewat ketok owner.**

**KEJUJURAN:** celah ini TERLIHAT saat menyisir §8e malam yang sama dan **dilewati** — Claude membacanya lalu
melanjutkan. Persis pola yang ditegur owner: melihat catatan yang relevan, lalu melangkahinya.

**BELUM DIPERBAIKI — menunggu ketok owner**, karena pilihannya adalah perilaku-saat-gagal (§0.6):
(a) tetap kirim tapi **beri tahu** · (b) STOP produksi run itu · (c) coba ulang N× dulu. Dua dari empat sebab
adalah bug kita sendiri dan pantas ditangani terpisah dari kebijakan degradasi.

### 8h. ~~EKOR pesan penyedia DIBUANG sebelum disimpan~~ — ✅ **DITUTUP 2026-08-06**

> **REALISASI.** 13 pemotongan di jalur simpan **dicabut** — pesan penyedia kini disimpan **apa adanya,
> tanpa batas**. `_potong_rapi(batas=500)` diganti `_rapikan_alasan()` yang hanya membuang spasi ujung.
> **Peringkasan hanya tersisa SATU di seluruh sistem: Telegram**, karena Telegram sendiri menolak pesan
> >4.096 huruf (`BATAS_TELEGRAM` — batas milik Telegram, bukan angka kita), dan ruang untuk pesan galat
> dihitung dari sisa jatah SETELAH bagian tetap, bukan diketik sendiri.
>
> **⚖️ ATURAN YANG DIPATRI — peringkasan tampilan WAJIB DIUMUMKAN.** `ringkas_diumumkan()` menyebut
> **berapa huruf disembunyikan** + ke mana melihat teks penuhnya. Alasannya bukan gaya: potongan senyap
> **terbaca persis seperti pesan utuh** — itulah yang menipu owner, tenant, dan Claude sendiri selama
> berbulan-bulan. Tiga syarat yang mengikat setiap peringkasan tampilan: (1) ada satu tempat yang SELALU
> menampilkan penuh (halaman detail run — haram memotong) · (2) potongannya diumumkan, bukan sekadar
> "…" · (3) yang dipotong selalu SALINAN, tak pernah yang tersimpan.
>
> **Kenapa tak ada batas simpan sama sekali** (usulan awal "katup pengaman 4.000" DICABUT owner):
> memasang batas untuk sesuatu yang tak pernah terjadi = persis cara angka 220 lahir. Aturan proyek
> sendiri berlaku di sini — *"masuk registry HANYA dengan sampel NYATA"*. Bila suatu hari penyimpanan
> benar-benar gagal karena ukuran, kegagalannya sudah tercatat dan **saat itu** diperbaiki dengan sampel.
>
> **BUKTI RUNTIME — 338 pesan NYATA dari `worker.log` VPS dijalankan lewat kode baru:**
> • disimpan **338/338 UTUH** · • Telegram: **337/338 lolos apa adanya**, 1 diringkas (halaman galat
> Cloudflare 7.705 huruf) **dan diumumkan** · • nol hasil melebihi batas Telegram ·
> • **56 pesan memuat waktu "try again in" — sebelumnya 0 yang selamat (terpotong di huruf ke-220),
> kini 56/56 tersimpan.** Suite 802 lulus (dari 791), nol regresi.
> Dijaga `tests/test_pesan_penyedia_utuh.py` (11 uji; merah dibuktikan lebih dulu: 7 gagal).
> **Layar: NOL perubahan** — sudah tak memotong; pembatasan kartu memakai tinggi visual (CSS), teks utuh.

<details><summary>Catatan asli saat ditemukan (disimpan sebagai riwayat)</summary>

**Bukan cacat Groq — cacat jalur BERSAMA.** Potongan `[:220]` ada pada penetapan `last_error` di
`niche_selector.py` (2 tempat) dan `script_engine.py` (2 tempat) — jalur yang dilewati **SEMUA
penyedia penulis naskah**. OpenAI, Gemini, Anthropic, dan penyedia mana pun yang ditambahkan nanti
kena potongan yang sama. *(Jangkar sengaja tanpa nomor baris — §10 melarangnya, nomor baris cepat basi.)*

**Aritmetika (terverifikasi pada 3 baris `production_runs` nyata):** 21 huruf kalimat kita +
23 huruf `"Provider 'Groq' gagal: "` + **197 huruf sisa pesan penyedia** = 241 · dan 23 + 197 = **220**,
tepat di batasnya. Potongnya jatuh di **"Li"** dari **"Limit"**.

**Yang hilang** (dibuktikan dari `worker.log` VPS, kejadian 2026-08-01 19:00 — nomor organisasi Groq-nya
identik dengan yang tersimpan di DB):
> `… on tokens per day (TPD): **Limit 100000, Used 97045, Requested 5359. Please try again in 34m37.056s.**
> Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing`, `'code': 'rate_limit_exceeded'`

⇒ **kapan boleh dicoba lagi · berapa jatah terpakai · tautan menaikkan paket · kode resmi penyedia** —
keempatnya sampai ke server kita, tercatat di log kita, lalu **dibuang sebelum disimpan**. Yang
tersimpan justru bagian tak berguna bagi tenant: nama model + nomor organisasi (± **110 dari 220** huruf).

**Ini BUG, bukan disain.** Di jalur pesan galat ada **13 angka potong berbeda** — 40, 40, 70, 80, 120,
200, 220, 220, 300, 300, 300, 500, 500 — tak satu pun sama, tak satu pun beralasan tertulis, tak satu
pun bisa diatur (melanggar §3.3 CLAUDE.md: nilai bisnis dari config, nol literal di kode). Disain punya
SATU angka di SATU tempat dengan SATU alasan. Angka 220 masuk 9-Jul bersamaan dengan fitur "teruskan
alasan penyedia"; tak ada catatan kenapa 220. **Makin banyak penyedia makin parah**: penyedia dengan
basa-basi pembuka lebih panjang kehilangan lebih banyak ekor.

**Rencana (Tahap 2, menunggu ketok owner):** satu pemotong bersama · batas dari config, angkanya
DIUKUR dari 62 pesan galat nyata di `worker.log` (bukan tebakan) · bila harus dipotong yang dibuang
**bagian TENGAH** (kepala = penyedia & jenis galat, ekor = angka/waktu/tautan — keduanya disimpan) ·
**pemotongan hanya saat DITAMPILKAN, bukan saat disimpan.**

**Akibat berantai yang sudah terlihat:** §9a tidak bisa memberi tenant jam perkiraan pulih, dan
pertanyaan "bolehkah rem melepas dirinya sendiri pada waktu yang penyedia sebutkan" **tidak bisa
dijawab** sebelum celah ini ditutup — waktunya belum benar-benar kita punya.

</details>

> **Kini terbuka (akibat 8h ditutup):** waktu "coba lagi" dari penyedia **sudah tersimpan** (56 kejadian
> nyata). Pertanyaan "bolehkah rem melepas dirinya sendiri pada waktu itu" **baru sekarang bisa
> dibicarakan** — dan tetap **KEPUTUSAN OWNER** (§0.6 perilaku-saat-gagal), belum diketok. Ingat batasan
> yang sudah tertulis di §9: *"pemulihan = keputusan TENANT, bukan sistem"* — mengubahnya butuh ketok
> baru, bukan disimpulkan dari tersedianya data.

### 8i. ~~ADEGAN GAMBAR GAGAL DISAMARKAN JADI MASALAH DURASI~~ — ✅ **DITUTUP 2026-08-08**

**Rantai kerusakannya** (dipetakan ujung-ke-ujung 07/08-Agu, atas perintah owner "pahami petanya dulu"):
penyedia menolak/kehabisan kredit → penangkap adegan **membuang sebabnya** & mencoba tulis-ulang 3×
(sia-sia bila kredit habis) → adegan dilewati, perakit tetap melapor **"✅ berhasil"** → pipeline hanya
memeriksa "NOL klip", kekurangan sebagian **lolos** → perender menyusun durasi dari **JUMLAH klip** →
video lebih pendek dari narasi → QC menamainya **"Durasi kependekan"** → masuk gudang sebagai stok →
**menyumbat slot 72 jam** → channel diam 3 hari.

**Terukur di produksi:** 23 adegan dilewati · **12 dari 180 render kehilangan gambar** (terparah 34,4 dtk;
7 di antaranya dari jalur kode lama yang mati sejak 17-Jun) · run RETRO REWIND 03-Agu: **berkas 36,7 dtk
sementara narasinya 58,3 dtk** ⇒ ±21 detik cerita tenant tidak ikut. Sebaran penyedia: **17 dari 23
kegagalan di OpenAI (berbayar)**, 6 di Cloudflare (gratis) — dugaan awal "hanya tingkat gratisan" SALAH.

**KENAPA INI BUKAN MASALAH DURASI — dan kenapa belasan perbaikan durasi tak pernah menuntaskannya:**
pada run itu SELURUH rantai durasi benar (naskah 167 kata dari resep 133-163 · gerbang hulu lolos ·
audio nyata 55,8 dtk · gerbang pra-visual lolos · perender menghitung 58,3 dtk). Yang hilang **gambarnya**.
Label "durasi" mengarahkan setiap sesi memperbaiki rantai yang **tidak bersalah**.

**Perbaikannya (semua MEMBUANG sesuatu, tak ada yang menambah beban baru):**
1. Sebab kegagalan adegan **disimpan** (`AIImageProvider.scene_errors`) — dulu dibuang satu baris setelah dibuat.
2. Kelas yang **mustahil sembuh** (FAST_FAIL) **tidak diulang 3×** — aturan yang sudah berlaku di jalur
   penulis naskah, di sini hanya diikuti. Mengulang hanya membakar sisa jatah tenant.
3. Perakit berhenti melapor "berhasil" saat adegan kurang; sebab penyedia diteruskan.
4. `Pipeline._periksa_kelengkapan_klip` — klip < bagian naskah (`beat_durations`) ⇒ **GAGAL JUJUR**
   dengan sebab penyedia. Tanpa `beat_durations` → **DIAM, tidak menebak**.
5. **10 pemotongan balasan penyedia dicabut** di adaptor (250/300 huruf) — memotong justru angka, jam
   pulih, dan tautan perbaikannya.

**Yang SENGAJA tidak dilakukan:** menerjemahkan/merapikan pesan penyedia (ketok owner 08-Agu: "AI provider
tidak menulis pesan tidak rapi; akan ada ratusan model — jangan terjemahkan"). Pesan penyedia diteruskan
**apa adanya**; kita hanya menambahkan penunjuk **TEMPAT** — *"Kegagalan terjadi di layanan AI Anda"* —
bukan menebak **APA** yang terjadi ("menolak" keliru untuk penyedia yang menggantung / server rusak /
model dipensiunkan).

**Bukti:** merah dibuktikan lebih dulu (9 gagal) · suite **813 lulus** (dari 802), nol regresi ·
uji `tests/test_adegan_hilang_tak_disamarkan.py` (11 uji, termasuk **anti-regresi klip lengkap**).
**Angka "/6" di log perakit = literal mati** (log yang sama mencetak "7/6" & "8/6") — pemeriksaan
SENGAJA tidak memakai hitungan itu.

### 8j. ~~PEMULIHAN GAMBAR MATI 2 BULAN · SEBAB PENYEDIA DIBUANG · SALAH KITA DITIMPAKAN KE TENANT~~ — ✅ **DITUTUP 2026-08-11**

**Satu baris setelan yang tidak pernah diserahkan**, bertemu satu penjaga yang benar, menghasilkan
tiga kerusakan sekaligus — dan menyembunyikan diri selama dua bulan.

**Rantainya (terverifikasi ujung-ke-ujung):**
1. `visual_assembler._load_run_config` menyerahkan `llm_models` tapi **TIDAK** `llm_model`.
2. `ai_image._ai_rewrite_on_rejection` memilih model dengan `llm_models["rewrite"] or llm_model`
   → cabang kedua **selalu `""`**.
3. Penjaga koherensi [B11]-G3 (`_apply_channel_overlay`) **sengaja membuang** `llm_models` bila
   penyedia channel ≠ penyedia tenant — **benar, dan justru itu yang mengosongkan cabang pertama.**
   Dua aturan yang masing-masing benar, bertemu → **kosong melompong.**
4. Hasilnya: `"Model untuk 'Groq' tidak ditentukan"` — **49 kejadian** di worker.log, 8 pada 11-Agu.

**Akibat terukur:**
- **17 dari 18 tenant** pemulihan gambarnya MATI. Satu-satunya yang hidup = channel owner sendiri
  (`RAD The Explorer`, satu-satunya dengan `llm_models['rewrite']` terisi) — **itu sebabnya kerusakan
  ini tak pernah terlihat dari tempat owner menguji.**
- **28 adegan mati** setelah 3 percobaan; pemulihan **berhasil hanya 1×** (di channel owner itu).
- Percobaan 2 & 3 **tak pernah sampai ke penyedia gambar** — mati di penulis-ulang prompt. Jadi
  dugaan "mesin membakar jatah tenant dengan 3× percobaan" **TIDAK benar**; yang terbakar adalah
  **video yang sebenarnya bisa diselamatkan** (kedua galat Cloudflare nyata = prompt ditolak, yaitu
  persis keadaan yang penulis-ulang diciptakan untuk mengatasinya).
- Sebab **TERAKHIR** dipakai sebagai sebab yang ditampilkan (cacat yang dikirim `0d64f79`) → karena
  percobaan 2-3 memanggil penulis-ulang lebih dulu, sebab terakhir hampir selalu **galat KITA**,
  lalu ditempeli *"Kegagalan terjadi di layanan AI Anda"*. **Kejadian nyata 11-Agu 12:21.**
  Terukur **75 kegagalan MILIK KITA** di worker.log (49 setelan rewrite · 16 berkas tak ada · 10 FFmpeg).
- **35 kegagalan penyedia gambar** (13 Jun · 13 Jul · 9 Agu) sebabnya **tak pernah tersimpan di mana
  pun** — baris log percobaan-1 hanya menyebut BAHWA gagal. **Inilah sebabnya "jatah Cloudflare habis"
  tak bisa dibuktikan ADA maupun TIDAK ADA** selama ini; bukan karena tidak terjadi.

**Yang diperbaiki:**
| # | Perbaikan | Berkas |
|---|---|---|
| 1 | `llm_model` diserahkan (2 lapis: `_load_run_config` + dict `_try_ai_image`; kedua cabang dict dibuat identik) | `visual_assembler.py` |
| 2 | Setelan kosong = **gagal jujur** menyebut apa yang kurang + `milik_kita=True`, bukan `""` diteruskan diam-diam | `ai_image.py` |
| 3 | Pemetaan galat **Cloudflare & Gemini** dari dokumen resmi (§4) — termasuk **3036 berhenti vs 3040 ulangi, dua-duanya 429** | `base.py`, `ai_image.py` |
| 4 | `PipelineError.milik_kita` — asal ditandai **di titik raise**, tak lagi ditebak dari teks | `exceptions.py` |
| 5 | Sebab **PERTAMA** yang dipakai (jawaban penyedia), sebab terakhir tetap di log utk diagnosa | `ai_image.py` |
| 6 | Sebab percobaan-1 **ikut dicatat** di log (menutup lubang 35 sebab terbuang) | `ai_image.py` |
| 7 | Beberapa adegan gagal → dipilih sebab yang **paling bisa dikerjakan tenant** (FAST_FAIL penyedia dulu, galat kita paling belakang — belakang, bukan disembunyikan) | `visual_assembler.py` |
| 8 | Pesan tenant: galat milik kita → *"Penyebabnya ada di MesinViral, BUKAN di layanan AI Anda"* | `pipeline.py` |
| 9 | Nama penyedia di log dibetulkan: dulu mencetak `llm_provider` (legacy, "openai") padahal yang dipakai `llm_library` ("groq") | `ai_image.py` |

**Bukti runtime (bukan hanya uji hijau):** ke-7 channel aktif diuji dengan config produksi nyata →
**7/7 memilih model perbaikan yang cocok dengan penyedianya sendiri** (gemini→`gemini-2.5-flash`,
groq→`llama-3.3-70b`/`llama-3.1-8b`, openai→`gpt-4o-mini`). Sebelum perbaikan: **6 dari 7 kosong.**
Suite **852 lulus**, nol regresi. Penjaga permanen: `tests/test_setelan_ai_tak_pernah_hilang.py` (26 uji).

**🔁 KOREKSI & PENYATUAN 12-Agu (lanjutan langsung §8j).** Beberapa jam setelah §8j dikirim, ditemukan
bahwa `3036` (jatah GRATIS harian) dipetakan QUOTA_EXHAUSTED — dan itu membuat **layar tenant DAN
Telegram** sama-sama berkata *"Kredit habis · TIDAK akan pulih sendiri · Isi ulang saldo"* untuk jatah
yang pulih tengah malam UTC, sekaligus **memaksa tenant menekan tombol pemulihan** untuk sesuatu yang
sudah benar sendiri (bentuk persis insiden channel berbayar mati ±44 jam). Owner: *"satu gejala, tiga
perlakuan berbeda — ini perbuatan goblok."* Yang dikerjakan:
- `3036`/Gemini `quota_exceeded` → **RATE_LIMIT**, rak yang SUDAH dipakai gejala identik di jalur naskah
  (Groq `tokens per day`, 8 sampel nyata). Nol rak baru, nol tampilan disentuh.
- **EMPAT penilai tersebar → SATU** (`galat_registry.py`, data + penilai generik). Adapter lama menjadi
  pembungkus tipis; tanda tangan dijaga → nol titik panggil berubah, uji-uji lama tetap hijau.
- **Seluruh 9 penyedia katalog dipetakan dari dokumen RESMI** (tautan + tanggal di tiap baris), termasuk
  yang sebelumnya NOL golongan: **Anthropic** (punya `billing_error` 402 tersendiri), **OpenAI TTS**,
  **Edge TTS** (6 channel aktif; diakui terang tak punya dokumen resmi), **fal.ai** (AGREGATOR).
- **OpenAI:** dua kode terdokumentasi yang belum pernah kita kenali — `credit_balance_exhausted`
  (saldo → tindak) vs `organization_usage_limit_exceeded` (batas pakai → pulih). 4 channel aktif.
- **`milik_kita` diseragamkan** ke jalur naskah & suara (dulu hanya gambar): setelan kurang / pustaka
  belum terpasang = pihak KITA, haram ditimpakan ke tenant.
- **Pagar:** `tests/test_galat_generik.py` (16 uji) — penyedia aktif di katalog DB wajib punya baris ·
  nol penilai kedua · jatah berkala wajib pulih-sendiri · saldo berbayar wajib menuntut tindakan ·
  jaring generik tak boleh merem cepat · terusan agregator terbaca. **Dibuktikan MERAH** untuk 3 bentuk
  pelanggaran, lalu hijau lagi. Suite **853 → 869 lulus, nol regresi.**

**⚠️ MASIH TERBUKA — butuh ketok owner, sengaja TIDAK diputuskan sendiri:** Cloudflare `3036` (jatah
gratis harian) dipetakan QUOTA_EXHAUSTED = **FAST_FAIL (berhenti)**, sesuai rencana yang disetujui.
Tapi jatah itu **pulih sendiri keesokan hari UTC** — apakah ia juga layak masuk `SELF_HEALING`
(produksi lanjut sendiri besok, tanpa tenant menekan apa pun) adalah **keputusan produk** (§0.6),
bukan keputusan Claude. Hari ini: berhenti + beri tahu tenant.

### 8b. ~~`notify_publish_fail` belum diseragamkan~~ — ✅ **DITUTUP 2026-08-04**
Jalur upload YouTube gagal adalah satu-satunya notifikasi yang tak bisa menjawab pertanyaan penentu
tenant — **perlu bertindak, atau cukup ditunggu?** — padahal `youtube_publisher.publish()` SUDAH
mengembalikan `error_class` **dan** `human_error` ([B11] 3.2); keduanya DIBUANG di pemanggil
(`pipeline` STEP publish membaca hanya `error`). Akibatnya kegagalan yang pulih sendiri terlihat sama
gentingnya dengan koneksi YouTube yang putus permanen.

**Perbaikan:** pemanggil meneruskan `error_class` + memakai `human_error` bila ada; `notify_publish_fail`
memberi anjuran per-KELAS dari `SELF_HEALING` (persis pola `notify_circuit_break`) — pulih-sendiri →
"tidak ada yang perlu Anda ubah, akan diunggah ulang otomatis"; butuh-tindakan → "periksa Koneksi
YouTube"; kelas kosong/asing → netral, TIDAK mengarang. **Argumen aditif** (satu-satunya pemanggil
memakai keyword) → nol regresi.

**SENGAJA TIDAK diubah:** dua jalur `return` pagar salah-channel di `youtube_publisher` tetap TANPA
kelas. Memberinya `AUTH_INVALID` akan **menandai koneksi YouTube tenant tidak sah** (→ `channel_missing`
menutup gerbang) padahal tokennya SAH — hanya menunjuk channel lain. Demikian juga
`unauthorized_client` (sampel nyata worker.log, 2 kejadian) belum dipetakan: memetakannya = perilaku
mesin = keputusan produk (§0.6). Keduanya dijaga uji agar tidak "diperbaiki" jadi salah.

**Bukti:** 6 uji baru di `tests/test_pemulihan_channel.py`, sampel VERBATIM worker.log
(`invalid_grant: Token has been expired or revoked.` ×4 · `unauthorized_client: Unauthorized` ×2);
merah dibuktikan lebih dulu (10 gagal tanpa perbaikan). Suite 634 → **639**.

## §9 KONTRAK TAMPILAN PER-KELAS (mengikat semua permukaan)

**Aturan tunggal: layar dan notifikasi memetakan per `ErrorClass`, TIDAK PERNAH per nama penyedia.**
Katalog penyedia & model akan terus bertambah (arahan owner 2026-08-03); kelas berjumlah tujuh dan
stabil. Penyedia baru cukup dipetakan ke kelas di registry §4 → **otomatis mendapat pesan, anjuran,
dan perilaku yang benar tanpa satu baris kode UI baru.** Menyebut nama penyedia di kode UI = pelanggaran.

Setiap kelas wajib menjawab tiga pertanyaan tenant, dalam bahasa awam & dwibahasa:
1. **Apa yang terjadi?** — bukan kode mentah vendor
2. **Apakah pulih sendiri?** — kolom di tabel §1, bukan tebakan
3. **Apa yang harus saya lakukan?** — satu langkah konkret + tautan ke tempatnya

| Kelas | Pulih sendiri | Anjuran kanonik |
|---|---|---|
| `RATE_LIMIT` | ✅ | tunggu (sesaat / sampai ganti hari bila pesan menyebut batas harian) — atau pakai penyedia lain |
| `TRANSIENT` | ✅ | biasanya pulih sendiri dalam hitungan menit |
| `QUOTA_EXHAUSTED` | ❌ | isi ulang kredit di penyedia Anda → tautan Integrasi |
| `ACCOUNT_BILLING` | ❌ | perbaiki pembayaran di penyedia Anda → tautan Integrasi |
| `AUTH_INVALID` | ❌ | perbarui kunci/koneksi → tautan Integrasi |
| `MODEL_UNAVAILABLE` | ❌ | pilih model lain → tautan Pengaturan Channel |
| `UNKNOWN` | ❓ | tampilkan pesan apa adanya + ajak hubungi dukungan |

**Pemulihan produksi = keputusan TENANT, bukan sistem.** Sistem tidak pernah melepas rem sendiri karena
sebab teknis dianggap sudah lewat. Pengecualian tunggal yang sudah diketok owner: rem dilepas otomatis
saat **langganan aktif kembali** (pembayaran/aktivasi admin) — konteks langganan, bukan kegagalan
teknis. Lihat `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` §10b K2.

### §9a JALUR PEMULIHAN per kelas — ditentukan oleh SEBAB, bukan oleh gerbang uji *(dipatri 2026-08-06)*
| Kelas | Yang ditawarkan panel | Kenapa |
> **🔧 DITUTUP 2026-08-12 — SEBAB YANG PULIH SENDIRI TIDAK LAGI MENGEREM CHANNEL.**
> Cacat: layar tenant berkata *"batas seperti ini pulih sendiri, Anda tidak perlu mengubah apa pun"*
> sementara channelnya **tetap mati sampai tenant menekan tombol** — dua pernyataan yang saling
> membatalkan, dan tenant yang MEMPERCAYAI kalimat kita justru paling dirugikan.
> **Terukur:** Bang Us-Dat direm 01-Agu 12:00 (jatah token HARIAN Groq habis), jatahnya pulih
> keesokan pagi — 02-Agu produksinya BERHASIL 2× — tapi status berhenti menempel **11 hari**.
> Pola sama pernah membuatnya mati **44 jam** (§8a).
> **Perbaikan:** `inventory.recent_nonready_streak` tidak lagi menghitung kegagalan ber-kelas
> `SELF_HEALING`. **NETRAL, bukan pemutus** — dua arah sengaja: memutus = kegagalan NYATA sebelumnya
> ikut dimaafkan (rem lumpuh); menghitung = channel direm untuk sebab yang sudah sembuh. Kelas
> KOSONG (run lama) tetap dihitung → perilaku lama dipertahankan.
> **Keputusan owner [B25] TIDAK dibalik:** ia lahir untuk sebab yang MENUNTUT tindakan tenant
> (saldo · kunci · model). Untuk sebab yang tak menuntut apa pun, remnya memang tak seharusnya
> menyala — jadi tak ada rem yang perlu dilepas sendiri. Lingkupnya dikembalikan, bukan dicabut.
> **Bukti data NYATA:** Abyss ID (sebab `model_unavailable`) hitungan tetap 10 → rem TETAP menyala,
> benar. **Batas jujur:** kegagalan Bang Us-Dat 01-Agu tersimpan ber-kelas `unknown` (penggolongan
> jatah harian Groq aktif setelahnya) → perbaikan ini **mencegah kejadian berikutnya, tidak
> menyembuhkan yang sudah tercatat**; channel itu tetap butuh satu tekanan tombol tenant.
> **Dijaga** `tests/test_pemulihan_channel.py` (kelas `TestSebabPulihSendiriTakMengeremChannel`),
> dibuktikan merah dua arah.

|---|---|---|
| `QUOTA_EXHAUSTED` · `ACCOUNT_BILLING` · `AUTH_INVALID` · `MODEL_UNAVAILABLE` | **"Jalankan uji & pulihkan"** (selama gerbang uji mengizinkan) | tenant harus memperbaiki sesuatu dulu; **uji MEMBUKTIKAN perbaikannya berhasil**, dan keberhasilan itu sendiri yang memutus hitungan kegagalan |
| `RATE_LIMIT` · `TRANSIENT` | **"Pulihkan produksi"** + peringatan jujur | uji **tidak membuktikan apa pun** di sini dan **memanggil penyedia yang sedang menolak** ⇒ dijamin gagal sambil MEMBAKAR sisa jatah tenant |
| `UNKNOWN` / kelas kosong (rem yang menyala sebelum kelas dicatat) | **"Pulihkan produksi"** + peringatan jujur | kita tak tahu apa yang akan dibuktikan uji; memaksanya = menebak dengan jatah tenant |

**Peringatan jujur = bagian dari kontrak, bukan hiasan:** tombol pemulih WAJIB disertai kalimat
*"Tekan setelah penyebabnya lewat. Bila belum, produksi akan gagal lagi dan mesin berhenti lagi."*
Tanpa itu insiden 3-Agu (tenant menekan tanpa memperbaiki apa pun) lahir kembali dalam bentuk lain.

**Kenapa aturan lama dipersempit — dan kenapa aman.** Aturan sebelumnya: *"selama uji masih boleh
dijalankan, ITU jalur yang ditawarkan"* — tombol pemulih disembunyikan. Untuk sebab yang pulih sendiri
itu **jebakan**: rem menyala karena jatah HARIAN penyedia habis, uji = satu produksi NYATA ke penyedia
yang jatahnya sedang habis ⇒ pasti gagal + membakar sisa jatah. **Terukur:** channel tenant BERBAYAR
(langganan aktif, karena itu "masih boleh menguji") berhenti **1-Agu s/d 6-Agu** tanpa jalan keluar
yang berfungsi. Melepas rem sendiri **tidak memanggil AI sama sekali** (`api/channels/[id]/resume`).
Mempersempitnya aman karena **akar insiden 3-Agu sudah ditutup di MESIN oleh migrasi 0197** (§8c):
pelepasan rem menyetel `production_resumed_at` dalam SATU pernyataan dan hitungan kegagalan hanya
menghitung yang SESUDAHnya ⇒ rem-menyala-lagi-dalam-detik **mustahil secara struktur**. Aturan UI itu
ternyata tambalan penyeimbang untuk bug yang sudah diperbaiki.
**Dijaga uji:** `tests/test_pemulihan_tak_menjebak.py` (12 uji, dua arah) + `tests/test_pemulihan_channel.py`
(aturan lama dipersempit, bukan dihapus — pelajaran 3-Agu tetap terkunci di sana).

⚠️ **Jangan tertukar:** `direct_jobs.error` kini bisa berisi **kode gerbang** `GATE:*` (penolakan
langganan/jatah uji — [B24]), yang **bukan** `ErrorClass` dan bukan kegagalan AI. Penerjemahnya
terpisah (`components/gate-message.tsx`). Dokumen ini hanya mengatur kegagalan AI.

## §10 PENJAGA ANTI-DRIFT (supaya dokumen ini TETAP SSOT)

> **Tiga penjaga, dan batas masing-masing — ditulis supaya hijau tak pernah lagi dibaca sebagai
> "dokumen sudah sejalan":**
> 1. `tests/test_ssot_error_mgmt.py` — taksonomi §1 vs `ErrorClass`, daftar FAST_FAIL, anjuran
>    per-golongan, larangan menyebut vendor di UI, **dan sejak 12-Agu tabel §4 vs `galat_registry`
>    (dua arah)** + kelengkapan daftar penjaga di §7/§10 (dua arah).
> 2. `tests/test_galat_generik.py` — nol penilai kedua · penyedia aktif di katalog DB wajib
>    terpetakan · jatah berkala wajib pulih-sendiri · jaring generik tak boleh merem cepat.
> 3. `tests/test_setelan_ai_tak_pernah_hilang.py` — setelan AI wajib diserahkan · sebab PERTAMA
>    yang dipakai · galat milik kita tak boleh dilabeli "layanan AI Anda".
>
> ⚠️ **YANG TIDAK DIJAGA SIAPA PUN:** apakah pemetaan sebuah kode memang BENAR menurut dokumen
> vendornya. Mesin bisa memastikan tabel & kode sinkron; ia tidak bisa membaca dokumen vendor
> untuk Anda. Itu tetap pekerjaan manusia — dan di situlah §1 Aturan Emas berlaku.

Audit 2026-08-03 menemukan dokumen ini menyimpang dari kode di **empat** tempat sekaligus — dua di
antaranya membuatnya **menyatakan perilaku yang salah** (kelas hilang, daftar FAST_FAIL kurang satu),
dan satu menyandarkan bukti pada berkas uji yang tak ada. Janji "akan dijaga" jelas tidak cukup.

Karena itu: **`tests/test_ssot_error_mgmt.py` membaca dokumen ini dan membandingkannya dengan kode.**
Bila salah satu bergeser tanpa yang lain, uji MERAH sebelum sempat menyesatkan siapa pun:
- setiap anggota `ErrorClass` wajib punya barisnya di tabel §1 — dan sebaliknya, tak ada baris hantu
- daftar `FAST_FAIL` di §1 wajib sama persis dengan `src/exceptions.py`
- setiap berkas uji yang dirujuk §7 wajib benar-benar ada
- §9 wajib memuat baris untuk setiap kelas (kelas baru tanpa kontrak tampilan = tenant melihat pesan kosong)
- dokumen tidak boleh memuat anchor `file:baris` (aturan §3 — nomor baris selalu basi)

## §11 CHANGELOG
- **2026-08-04 (2)** — **§8e-A DITUTUP: jalur visual berhenti membuang sebabnya.** Sampel yang menuntunnya
  (worker.log 14-Jul, 6 kejadian): penyedia video menjawab *"User is locked. Reason: Exhausted balance.
  Top up your balance at fal.ai/dashboard/billing"* — sebab yang tenant bisa bereskan dalam 2 menit —
  sementara yang tersimpan & ditampilkan hanya *"no clips downloaded"*; 3 run terbakar 55-85 dtk.
  Kini sebab itu ikut ke `error_message` → layar tenant. **Hanya TEKS**: `error_class` sengaja TIDAK diisi
  (§8e-B) karena itu memicu rem-setelah-1-gagal = keputusan produk. 11 uji sampel-produksi, merah dibuktikan
  dulu; suite 623 → 634. Aman-untuk-tenant dipilih di atas lengkap-tapi-berisiko.
- **2026-08-04** — **CELAH §8e DIDOKUMENTASIKAN (belum diperbaiki — menunggu ketok owner).** Audit atas
  perintah owner *"jangan berhenti selama masih ada bug"*. Metodenya: **menjalankan penggolong yang ADA DI
  PRODUKSI atas 5 sampel error ASLI** dari `production_runs`/worker.log — bukan membaca kode. Hasil: 4 dari 5
  sudah benar (429 throttle→RATE_LIMIT · 429 kuota→QUOTA_EXHAUSTED · 404 Gemini→MODEL_UNAVAILABLE ·
  401→AUTH_INVALID). Satu tersisa (`billing_hard_limit_reached`→UNKNOWN) menyingkap celah STRUKTURAL §8e:
  **jalur visual = 38 titik `raise`, 0 berkelas** — jalur termahal justru satu-satunya yang membuang sebab.
  Dua baris ⏳ §4 dikoreksi (satu di antaranya menyatakan "belum ada sampel" padahal sampelnya ada sejak 29-Jul).
  **KOREKSI KEJUJURAN:** putaran ini sempat "menemukan" bug kedua (404 Gemini tak dikenali) yang **TIDAK ADA** —
  sampel ujinya DIKARANG (`"is not found"`), sedangkan teks produksi berbunyi `"is no longer available"` yang
  sudah terpetakan. Nyaris menyunting penggolong produksi tanpa sebab. Pelajaran yang mengikat:
  **sampel uji WAJIB diambil dari produksi, bukan disusun dari ingatan** — temuan yang lahir dari sampel
  karangan adalah mesin utama rantai bug-fix tanpa ujung.
- **2026-08-03 (2)** — **[B25] CELAH §8a DITUTUP: rem darurat berhenti membuang sebabnya.**
  (A) migr **0196** `channels.production_paused_class` + `_pause_channel` menyimpannya; alasan kini
  memuat pesan manusiawi untuk KEDUA cabang (dulu hanya rem-cepat — tenant yang paling sering terkena
  justru paling sedikit diberi tahu). (B) **panel pemulihan per-KELAS** di layar channel: apa yang
  terjadi · **apakah pulih sendiri** · langkah konkret + tautan + tombol *Pulihkan produksi*; kelas tak
  dikenal tidak mengarang, hanya mengantar ke dukungan. (C) Telegram memberi anjuran berbeda untuk
  pulih-sendiri vs butuh-tindakan, plus tautan ke channelnya. (D) `/admin/system` memuat satu daftar
  seluruh channel yang berhenti + sebab + kolom pulih-sendiri.
  **Himpunan baru `SELF_HEALING`** (`src/exceptions.py`) jadi sumber tunggal jawaban "pulih sendiri?" —
  hidup di tiga tempat (Python · dokumen §1 · peta layar TS) dan **keselarasannya diuji**, bukan
  dipercaya. Layar dilarang menyebut nama penyedia (arahan owner: katalog akan terus bertambah →
  petakan per KELAS); larangan itu **ditegakkan uji**. **Pemulihan tetap keputusan tenant.**
  Bukti: 12 uji unit + **22 pemeriksaan klik→layar** (7 kelas × judul & status · kelas tak-dikenal ·
  daftar admin), nol galat halaman; suite proyek 600 → 612.
- **2026-08-03** — **AUDIT DOKUMEN-vs-KODE (perintah owner: "pastikan masih sesuai codebase & terus
  jadi SSOT"). EMPAT DRIFT ditemukan, dua di antaranya membuat dokumen ini MENYATAKAN PERILAKU YANG
  SALAH:**
  1. **Kelas `MODEL_UNAVAILABLE` hilang dari tabel §1** — ada di kode & dipakai produksi (2× tercatat),
     tapi pembaca §1 hanya melihat enam kelas.
  2. **`FAST_FAIL` di §1 kurang satu anggota** (3 vs 4 di kode). Ini klaim tentang KAPAN mesin mengerem —
     salah di dokumen SSOT berarti setiap keputusan yang bersandar padanya ikut salah.
  3. **§7 menyandarkan bukti pada `tests/test_errmgmt.py` yang TIDAK ADA di repo** ("13/13 LULUS" tak
     bisa diverifikasi siapa pun). Diganti daftar berkas yang benar-benar ada: **39 uji lulus**, plus
     bukti dari produksi nyata (`production_runs.error_class`: unknown 32 · quota_exhausted 4 ·
     rate_limit 3 · model_unavailable 2).
  4. **Semua anchor `file:baris` basi** (pipeline ~275→359/428 · ~636→747 · producer :206/:340/:435→
     137/397/491 · ai_video.py:219). Anchor dihapus seluruhnya; aturan baru: **rujuk nama simbol**.
     Registry §4 diperiksa baris demi baris — **semua klaim ✅ TERBUKTI ada di kode** (satu-satunya
     bagian yang tidak drift).

  **Ditambahkan:** §1 kolom **"Pulih sendiri?"** (pembeda yang menentukan apa yang boleh dikatakan
  sistem ke tenant) · **§8 CELAH TERBUKA** — rem darurat MEMBUANG kelas errornya, sehingga layar hanya
  bisa menebak; berdampak nyata pada dua tenant berbayar (Bang Us-Dat mati ±44 jam karena sebab yang
  pulih sendiri) · **§9 KONTRAK TAMPILAN PER-KELAS** (arahan owner: penyedia akan terus bertambah →
  petakan per KELAS, **tidak pernah** per nama penyedia; pemulihan tetap keputusan tenant, bukan
  otomatis) · **§10 PENJAGA ANTI-DRIFT**.

  **`tests/test_ssot_error_mgmt.py` — dokumen ini kini dijaga MESIN, bukan janji.** Ia membaca dokumen
  dan membandingkannya dengan kode. Penjaganya sendiri diuji dengan **lima simulasi drift** (kelas
  dihapus · FAST_FAIL dikurangi · anchor disisipkan · kontrak §9 dilubangi · berkas uji fiktif) —
  **kelimanya merah**, lalu hijau lagi setelah dokumen dipulihkan. Versi pertama penjaga ini sempat
  **bocor** (kelas dihapus dari tabel tapi tetap hijau, karena namanya masih muncul di baris FAST_FAIL
  pada bagian yang sama) → diperketat ke baris TABEL saja. *Hijau tidak membuktikan apa pun sampai
  merahnya juga dibuktikan.*
- **2026-08-01** — (a) **HTTP 429 → RATE_LIMIT untuk SEMUA transport OpenAI-compatible**, menggantikan pengenalan berbasis kalimat vendor. Alasan: klasifikasi wajib menempel pada TRANSPORT (§2) karena katalog model akan terus bertambah; §1 sendiri sudah mendefinisikan RATE_LIMIT sebagai 429. Tidak mengubah perilaku rem (RATE_LIMIT dan UNKNOWN sama-sama di luar FAST_FAIL dan sama-sama retryable — diverifikasi) — yang berubah: pesan ke tenant jadi benar, bukan "kesalahan tak dikenal". (b) Tiga baris registry BARU untuk kegagalan SUARA (audio terpotong · penyedia menggantung · cakupan sintesis kurang), semuanya TRANSIENT. (c) Lama TUNGGU kini dibaca dari pesan penyedia sendiri ("try again in Xs", dibatasi 90 dtk) — sebelumnya 2/4/8 detik lalu menyerah, dan itu membuang 135 kata naskah yang sudah jadi hanya karena penyedia minta ditunggu 8 detik.
- **2026-07-22** — **PENEGAKAN SSOT TAMPILAN (koreksi doc-drift + fix kode).** Owner menohok benar: "buat apa dokumen SSOT kalau tak ditegakkan?". Ditemukan (bukti kode): satu kegagalan tercatat di 3 tempat dgn cara BEDA — tabel `videos` & Telegram `notify_failure` pakai `str(e)` mentah, `production_runs` (via producer) pakai pesan-manusiawi; DAN di dalam producer sendiri jalur direct-test (`:432`) MELEWATI `human_error` (blok scheduled `:206` & direct-publish `:340` sudah benar). Klaim changelog 20-Jul "pesan manusiawi di layar/Telegram" karena itu = **over-claim** (belum benar utk notify_failure). **Fix (terkurung, low-risk):** (1) `pipeline` crash-path — satu var kanonik `human_err = human_error or str(e)` dipakai bersama `write_failed_run` (videos) + `notify_failure` (Telegram); (2) producer direct-test `:435` +`human_error` di depan chain (samakan 2 jalur lain). Semua UNKNOWN → `str(e)` = perilaku lama (nol regresi terbukti); TERKLASIFIKASI → pesan ramah seragam di SEMUA permukaan (§3 langkah 7). Uji: py_compile 2 file · verifikasi statis 4 jalur konsisten · uji logika unknown-identik/terklasifikasi-seragam. Bukti runtime pamungkas (run gagal terklasifikasi → Telegram=DB=layar identik) menyusul pasca-deploy. **Classifier DITUNTASKAN se-sesi ini (owner: "jangan sisakan utk sesi besok"):** Gemini `is no longer available`→MODEL_UNAVAILABLE + OpenAI quota (`insufficient_quota` · `exceeded your current quota`)→QUOTA_EXHAUSTED, ditambah ke `_OPENAI_COMPAT_ERROR_MAP` (Gemini pakai adapter `openai_chat` → lewat classifier yg sama; format 404-nya beda dari Groq shg dulu lolos jadi unknown). Bukti sampel byte-penuh dari production_runs riandipantria. Uji 6/6: 2 sampel nyata + 2 regresi (invalid_api_key/model_not_found) + **kasus kritis 429 rate-limit→UNKNOWN (jangan salah-rem)** + error asing→UNKNOWN. §4 registry di-update ✅. Sisa jujur: `notify_publish_fail` (jalur upload YouTube, bukan crash produksi) belum diseragamkan — dicatat, bukan disembunyikan.
- **2026-07-20** — Transport **OpenAI-compatible** naik ✅ (ketok owner "kerjakan tawaran 1"; sampel nyata insiden MVT): `invalid_api_key`→AUTH_INVALID · `model_not_found`→**MODEL_UNAVAILABLE (kelas baru, masuk FAST_FAIL)**. Classifier `_classify_openai_compat_error` di adapters.py (pola _classify_el_error; kode lain→UNKNOWN) + **rem cepat di loop retry niche_selector** (FAST_FAIL = stop percobaan-1; dulu 401 di-retry 3×) + propagasi `last_error_class/last_human_error` (pola last_* TTS) → pipeline raise ber-kelas → `production_runs.error_class` terisi benar (dulu 'unknown') + pesan manusiawi di layar/Telegram. Uji permanen `tests/test_openai_compat_error_classes.py` **6/6** (2 sampel verbatim + regresi UNKNOWN + taksonomi + wiring adapter + rem-1-percobaan) · suite 57/57.
- **2026-07-18 (2)** — **[B11] 3.2** menambah transport **Google OAuth** ke registry: `invalid_grant` → `AUTH_INVALID` (masuk FAST_FAIL). Koneksi YouTube putus permanen kini GAGAL JUJUR (bukan senyap): ditandai `status='invalid'` (helper `mark_youtube_account_invalid`) → gerbang `channel_missing` menutup → produksi channel berhenti seketika + notif tenant sekali + badge FE + publish menahan video (bukan "akan diulang" menyesatkan). RefreshError non-invalid_grant tetap transien (regresi dijaga uji `tests/test_youtube_auth_invalid.py` 10/10). ✅ **DEPLOYED PRODUKSI 2026-07-18 12:07 (`dd8fcdc`, izin owner, health=200).**
- **2026-07-18** — Lahir + kerangka dibangun + **DEPLOYED PRODUKSI 01:04 (`99b1c32`, izin owner)**. Pemicu: insiden RAD 2026-07-17 (langganan EL gagal-bayar → 3× gagal bakar biaya LLM sebelum rem). Owner minta manajemen error world-class extensible (bukan tambalan). Isi awal registry: EL-direct (✅), OpenAI (⏳). Verifikasi produksi: nol error import, 3 thread produksi start bersih.
