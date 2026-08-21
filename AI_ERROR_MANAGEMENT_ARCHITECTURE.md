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
- Agregator (fal) = **satu titik billing**: bila fal habis, SEMUA model via fal (naskah+suara+gambar+video) gagal bersama.

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

### §4b PENYIMPANAN MILIK KITA (S3/NEO) — bukan penyedia AI tenant *(ditambah 2026-08-13)*

Penyimpanan video **milik MesinViral**, bukan milik tenant. Karena itu ia **TIDAK** masuk tabel §4
di atas (tabel itu = penyedia AI tenant; mencampurnya membuat dokumen ini berbohong), tapi
penggolongannya **tetap hidup di satu rumah yang sama**: `src/providers/galat_registry.py` →
`golongkan_penyimpanan()` + `_PENYIMPANAN_KODE`. Pemetaan di berkas lain = pelanggaran (§6, dijaga
`tests/test_galat_generik.py`).

| Hal | Ketetapan |
|---|---|
| Sumber pemetaan | [Dokumen galat resmi S3](https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html) — dibaca **2026-08-13**. NEO BiznetGio ber-antarmuka S3, kosakata galatnya sama. |
| Asal-usul | **`milik_kita=True` SELALU** — bucket, kunci, dan tagihannya milik kita. Haram ditimpakan ke tenant dalam bentuk apa pun. |
| Kalimat ke tenant | Dua bentuk saja: **(a)** gangguan → *"tertunda … video Anda aman … terbit otomatis di jam tayang berikutnya"*; **(b)** `NoSuchKey`/404 (berkas benar-benar hilang) → kalimat BERBEDA yang **tidak** menjanjikan terbit otomatis, karena mengulang dijamin gagal. |
| Kode asli | Tetap utuh di catatan server + alarm ADMIN. Kontraknya §9: **tenant dapat MAKNA, kami dapat KODE.** |
| Rem channel | **TIDAK terpengaruh.** Rem menghitung dari `production_runs`; kegagalan terbit tidak membuat baris run. Jadi tagihan penyimpanan KITA tak pernah bisa mematikan channel tenant. |

**Sampel produksi yang melahirkannya (13-Agu 2026):** akun kami diblokir penyedia 04:24–10:21 karena
tagihan belum dibayar (`AccountProblem` ×13, tiap 30 menit). Pukul 06:00 jam tayang tiba dan tenant
menerima galat mentah `403 HeadObject Forbidden` lengkap dengan nama berkas internal — untuk
kegagalan yang 100% milik kita. Owner: *"pesan errornya tidak jelas hanya kode saja. ANEH"*.

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
- **[14-Agu] DUA ATURAN GENERIK tentang PARAMETER yang kita kirim** — ketetapan owner: *"pastikan
  setiap perbaikan sedapat mungkin bersifat GENERIK, karena AI model dan AI vendor akan terus
  bertambah"*. Keduanya berlaku untuk vendor yang **belum ada**:
  (a) **Jangan kirim parameter yang skema resmi model tidak menyatakan menerimanya.** Penandanya
  DATA (`ai_models.default_params.supports_seed`), **default = tidak mengirim**. Arahnya disengaja:
  mengirim parameter tak-didukung membuat produksi GAGAL (±$0,068 uang tenant hangus dalam 2 hari,
  §8k butir 4); tidak mengirimnya hanya membuat vendor memakai nilai acaknya sendiri.
  (b) **Penolakan atas parameter = `milik_kita=True`, di vendor mana pun** (`_RX_PARAM_CACAT`,
  jalur generik). Alasannya semantik: parameter permintaan hanya bisa datang dari kami. **Sempit
  dengan sengaja** — pola lebar akan menangkap galat MILIK TENANT (*"API key invalid"*), dan
  salah-alamat ke arah itu sama merusaknya.
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
| **`tests/test_ssot_error_mgmt.py`** | 20 | **penjaga anti-drift: dokumen ini vs kode** (§10) — sejak 14-Agu termasuk **kolom "Sikap" §1 vs perilaku mesin**, **struktur tabel utuh**, dan **angka bukti §7 tak basi** |
| **`tests/test_pemulihan_channel.py`** | 35 | **[B25] rem menyimpan sebabnya · Telegram bedakan pulih-sendiri · anti-drift `SELF_HEALING` lintas 3 tempat · setiap kegagalan dihitung (§8k)** |
| **`tests/test_rem_tak_boleh_lumpuh.py`** | 5 | **§8k — PERILAKU, bukan angka perantara:** berapa kali produksi di-submit · berapa kabar ke tenant · apakah mesin berhenti sendiri |
| **`tests/test_parameter_kita_tak_ditimpakan_tenant.py`** | 10 | **§8k butir 4 — dua arah:** parameter tak-didukung tak pernah dikirim (vendor baru otomatis aman) · galat parameter mengaku MILIK KITA lintas-vendor · **dan tidak salah-alamat ke arah sebaliknya** |
| `tests/test_migrasi_selaras_db.py` | 6 | kolom & **trigger** yang migrasi janjikan benar-benar hidup di DB (§8k butir 2/3, migr 0198) |
| **`tests/test_naskah_fal_jalur_hidup.py`** | 8 | **jalur naskah fal (16-Agu):** alamat tak boleh datang dari transport VISUAL & tak boleh menunjuk endpoint yang DIPENSIUNKAN vendor · pemakaian tercatat (tabel harga butuh angka untuk dikalikan) · balasan **HTTP 200 yang berisi `error`** digolongkan lewat penilai yang SATU itu (saldo habis ⇒ rem 1-kegagalan, bukan 3 produksi terbuang) · **generik: SETIAP adapter naskah wajib mencatat biaya**, jadi vendor berikutnya tertangkap merah bila lupa |
| **`tests/test_galat_menyebut_model_yang_harus_diganti.py`** | 11 | **identitas ikut ke kalimat tenant (17-Agu, keluhan BISIK NUSANTARA):** golongan `MODEL_UNAVAILABLE` menyebut **slot + nama model + penyedia** — anjuran "pilih model lain" mustahil dikerjakan tenant ber-3-slot AI tanpa itu, padahal vendor SUDAH menyebutkannya · generik untuk vendor/model yang belum ada · penampung tak terisi tak bocor ke mata tenant · tanda tangan 1-argumen tetap sah · 3 golongan lain & UNKNOWN tak bergeser · **setiap adapter naskah wajib meneruskan identitas** |
| **`tests/test_jawaban_terpotong_tak_diulang_sia_sia.py`** | 9 | **jawaban terpotong (18-Agu):** jatah token = SATU kantong untuk berpikir + menjawab; model generasi baru memakainya untuk berpikir ⇒ jawaban terpotong ⇒ JSON gugur ⇒ pemanggil mengulang IDENTIK 3× (tenant ditagih 3× tanpa peluang berhasil). Dijaga: jatah DINAIKKAN bukan diulang sama · naik SEKALI lalu pulih · batas atas dihormati (Groq menolak 8000) · model yang memang tak sanggup **gagal jujur + tenant diberi tahu ganti model** · **pelajaran tak menular ke tugas lain** (kunci memo memuat jatah-diminta) · memo tak pernah MENURUNKAN jatah · teks biasa & panggilan sehat tak tersentuh |
| **`tests/test_peta_tak_menyebut_bug_tanpa_bukti.py`** | 3 | **klaim "rusak" wajib berbukti uji (19-Agu):** setiap butir di daftar "Yang rusak" pada `PETA_MESINVIRAL.md` WAJIB menunjuk berkas `tests/…` yang ADA — kerusakan = ada yang bisa dibuat MERAH; tanpa uji itu PENDAPAT, tempatnya di daftar improvement. Juga menjaga judul bagiannya (jalan termudah mengakali) + keberadaan §4b/§4c. **Lahir dari pelanggaran Claude sendiri, dalam sesi yang sama, di dokumen yang dibuat untuk mencegahnya** — dibuktikan MERAH dengan menyabotase peta (menyelipkan butir pendapat ke daftar rusak) |
| **`tests/test_katalog_suara_tak_menipu.py`** | 4 | **katalog suara tak boleh menjanjikan yang mati (18-Agu):** suara AKTIF hanya pada mesin yang MENYALA — layar channel menyaring suara menurut mesin, jadi mesin mati ⇒ suara tak pernah terlihat siapa pun (kelas ini terjadi DUA HARI BERTURUT: 12 suara fal 16-Agu · 4 suara Gemini 18-Agu) · mesin menyala wajib punya model TTS yang bisa dipanggil **dan** karakter suara (Groq: 2 suara HANTU, nol model) · setiap suara yang ditawarkan wajib punya contoh audio yang bisa DIDENGAR tenant sebelum memilih |
| **`tests/test_harga_otomatis_model_fal.py`** | 4 | **tabel harga (16-Agu):** model berpenanda `vendor/model` ikut terisi sumber otomatis (dulu SELALU meleset ⇒ harga mandek selamanya) · model berpenanda polos tak berubah · model tanpa sumber dilaporkan jujur, harganya TIDAK dikosongkan · kunci admin tetap menang |
| **`tests/test_penurunan_mutu_tak_senyap.py`** | 6 | **§8f — penurunan mutu tak boleh senyap:** sebab frame pembuka IKUT tersimpan ke `run_metadata` di KEDUA jalur produksi · pesan penyedia tak dipotong · run sehat tak dikotori |
| **`tests/test_mesin_tak_mati_mendadak.py`** | 12 | **§8L — mesin tak boleh MATI MENDADAK:** skema SDK dipanaskan di alur utama (SELURUH model, bukan yang teratas) · mengurai balasan tak lagi membangun skema · urutan dibaca dari **pohon sintaks** · **reproduksi crash dua arah** |
| **Total kelima berkas lama** | **39 lulus** | dijalankan 2026-08-03 |

> ⚠️ **Angka di kolom tengah kini DIJAGA MESIN** (`TestAngkaBuktiUjiTidakBasi`): bila jumlah uji
> berubah tanpa tabel ini menyusul, suite MERAH. Sebelum 14-Agu angkanya basi — tertulis 9 & 12,
> nyatanya 20 & 35 — dan pembaca memakainya untuk menilai seberapa terjaga sebuah topik.

**Bukti dari PRODUKSI NYATA** (bukan hanya uji) — `production_runs.error_class`, dihitung ulang
**14-Agu 2026** atas SELURUH run (paginasi penuh, bukan sampel): `rate_limit` **53×** ·
`unknown` 39× · kelas kosong 46× · `quota_exhausted` 4× · `model_unavailable` 2×.
Registry bekerja: empat kelas berbeda benar-benar terklasifikasi pada trafik sungguhan.
**Rincian "kelas kosong" — diperiksa, bukan diasumsikan:** 38 = run gagal sebelum kelas disimpan
(migr 0170) · 8 = `qc_failed`, yaitu **gerbang mutu KITA yang menolak** (durasi meleset) — itu bukan
galat penyedia, jadi memang tak punya golongan. Yang terakhir bertanggal **2-Agu**, dan 37 dari 46
terjadi di Juli ⇒ ini SEJARAH, bukan kebocoran yang masih berjalan.
⚠️ **Angka `rate_limit` naik 3 → 53 justru karena kerusakan §8k** — 50 dari 53 terjadi pada 13 &
14-Agu, saat rem dilumpuhkan dan mesin mencoba tanpa henti. Angka yang melonjak di satu kelas
adalah **gejala yang layak diperiksa**, bukan tanda registry makin pintar.

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

**UKURAN SEKARANG *(dihitung ulang 14-Agu atas SELURUH `production_runs`, paginasi penuh)*: dari
105 kegagalan sejak 20-Jul, masih hanya 1 yang sebabnya terhapus** (0,95%; angka lama "42 kegagalan"
= keadaan 04-Agu, sudah basi — **yang penting bukan penyebutnya melainkan pembilangnya, dan ia tetap
1**) — yaitu
kegagalan visual 29-Jul, jenis yang §8e-A tutup. **Cara owner memeriksa sendiri:** hitung `production_runs`
berstatus `failed` yang `error_message`-nya PERSIS kalimat pembungkus tanpa rincian
("No topics selected" · "TTS generation failed" · "Visual assembly failed — no clips downloaded").
Angka itu harus tetap 0 untuk run baru; kalau naik, diagnosa melorot lagi.

### 8f. ~~DEGRADASI SENYAP pada FRAME PERTAMA~~ — ✅ **SENYAPNYA DITUTUP 2026-08-15**

> **Yang ditutup: SENYAPNYA. Yang TIDAK diubah: video tetap terbit.** Menghentikan produksi karena
> frame pembuka = keputusan produk (§0.6) dan bukan hak Claude; yang §0.6 larang adalah **fallback
> senyap**, dan itulah yang dicabut.
>
> **Cacat sebenarnya bukan "nilainya tak ada" — nilainya SUDAH ADA dan dibuang.** Sebab kegagalan
> ditangkap sejak 05-Agu (`visual_assembler.hook_frame_error`) lalu dimasukkan ke
> `result["steps"]["visuals"]` — tapi `steps` **tidak pernah ditulis ke tabel mana pun**. Komentar di
> `visual_assembler.py` bahkan **mengakuinya terang-terangan sejak 08-Agu**, dan tetap begitu sepuluh
> hari. Terukur 15-Agu: **85 run sejak 8-Agu, NOL yang menyimpannya.**
> **Perbaikan:** `producer._mutu_fields()` menyambungkannya ke `run_metadata` lewat jalur simpan yang
> SUDAH ADA & terbukti (`_cost_fields`), pada **kedua** jalur produksi (terjadwal + tombol tenant).
> Nol jalur baru · nol migrasi · nol tabel · nol perubahan perilaku mesin.
> Pesan penyedia disimpan **tanpa dipotong** (§8h). Fail-soft: gagal mencatat tak menghentikan apa pun.
>
> **Frekuensinya sudah turun sendiri tanpa disadari:** dari 13 kegagalan (653 percobaan, 2%),
> **3 di antaranya bug `seed` KITA** yang ditutup 14-Agu (§8k butir 4), 2 lagi bug kita di Juni
> (berkas tak ada · FFmpeg, nihil sejak). Sisanya milik akun/penyaring penyedia.
> **Dijaga** `tests/test_penurunan_mutu_tak_senyap.py` (6 uji; merah dibuktikan: sambungan dicabut
> dari satu jalur ⇒ merah).
>
> ⛔⛔ **AKAR YANG SAMA, TIGA KALI — pelajaran paling mahal malam itu.** Ketiga cacat ini satu
> kebiasaan, bukan tiga kejadian terpisah: **keterangan DITANGKAP lalu DIBUANG sebelum sampai ke
> siapa pun.**
> | # | Datanya ada di | Yang membacanya | Akibat |
> |---|---|---|---|
> | 1 | `production_runs.error_class` | layar tak membacanya | panel salah, tenant diarahkan ke jalur keliru (§8m) |
> | 2 | `hook_frame_error` di memori | tak ada yang menyimpan | penurunan mutu senyap 10 hari |
> | 3 | pesan MENTAH penyedia di dalam galat | ditimpa pesan kita saat simpan | waktu "coba lagi" hilang — 0 dari 53 baris (§8k) |
> **MENANGKAP ≠ MENYAMPAIKAN.** Setiap kali menambah perekaman, telusuri sampai permukaan yang
> membacanya — kalau tak ada pembacanya, perekaman itu belum selesai.

<details><summary>Catatan asli saat ditemukan (riwayat sebab-akibat)</summary>

**8f-lama. DEGRADASI SENYAP pada FRAME PERTAMA (tuas viral)** *(ditemukan 2026-08-04)*
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

*(15-Agu: pilihan (a) dijalankan — itu YANG SUDAH diketok §0.6, bukan keputusan baru. (b) & (c) tetap
menunggu owner. Dua "bug kita sendiri" itu nihil sejak Juni; yang tersisa milik akun/penyaring penyedia.)*

</details>

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

**✅ SUDAH TERTUTUP — koreksi drift 14-Agu.** Blok ini sebelumnya berbunyi *"MASIH TERBUKA … `3036`
dipetakan QUOTA_EXHAUSTED = FAST_FAIL (berhenti) … hari ini: berhenti + beri tahu tenant"* — dan itu
**bertentangan dengan kalimat di atasnya sendiri** (yang sudah menyatakan `3036` → `RATE_LIMIT`),
berjarak 16 baris. Yang benar = kode: dijalankan 14-Agu lewat `classify_cloudflare_error` dengan
balasan CF berbentuk daftar, hasilnya **`rate_limit` · pulih sendiri · tidak merem cepat**. Dokumen
resmi CF mendukungnya (*"Account limited — daily free allocation exhausted"*, HTTP 429, dibaca
14-Agu), dan `3040` tetap terpisah sebagai `transient` — dua arti di balik satu kode HTTP, benar.
`MEMORY.md` ikut memuat versi basi itu dan dikoreksi pada tanggal yang sama.
**Pelajaran bentuknya:** satu bagian dokumen menyimpan DUA jawaban untuk satu pertanyaan, dan yang
dibaca sesi berikutnya adalah yang kebetulan ditemukan lebih dulu. Bila sebuah pertanyaan sudah
dijawab, catatan "masih terbuka"-nya wajib dicabut **di commit yang sama** — bukan ditinggalkan
sebagai jejak sejarah di tempat pembaca mencari keputusan yang berlaku.

### 8k. 🔴 REM YANG DILUMPUHKAN → BANJIR KABAR KE TENANT *(ditanam 12-Agu, DICABUT 14-Agu)*

**Ini bug yang KAMI tanam sendiri saat memperbaiki bug lain.** Dilaporkan owner dari keluhan tenant.

**Rantainya:** perbaikan 12-Agu membuat kelas `SELF_HEALING` (jatah harian · throttle) **netral** di
`inventory.recent_nonready_streak`, supaya channel tenant tak mati berhari-hari untuk sebab yang
sembuh sendiri. Niatnya benar. Yang tak terhitung: **rem itu mengerjakan DUA hal — menghentikan
CHANNEL *dan* menghentikan PERCOBAAN.** Hanya yang pertama yang diincar; yang kedua ikut hilang, dan
**tak ada apa pun di aplikasi ini yang menggantikannya** — nol penahan laju, nol jeda, nol batas
percobaan per jam.

**Terukur (production_runs + worker.log VPS), dua channel tenant yang SAMA, dua hari berurutan:**

| Tanggal | Channel | Kegagalan | Rentang | Rem menyala? |
|---|---|---|---|---|
| 13-Agu | Thetangga Property | **30** (29 jatah-harian) | 8 menit | ❌ tidak |
| 14-Agu | BISIK NUSANTARA | **23** (21 jatah-harian) | 11 menit | ❌ tidak |

- Laju terukur: satu produksi baru tiap **±14 detik** ⇒ **±257 kabar gagal per JAM** ke Telegram tenant
- Setiap percobaan menembak penyedia **3×** (`AI analysis attempt 1/3 … 3/3`) ⇒ ±13 permintaan/menit
  ke penyedia yang sedang menolak
- Dari 53 kegagalan `rate_limit` sepanjang umur aplikasi, **50 (94%) terjadi pada dua hari itu**
- Rem TERAKHIR menyala **3-Agu**; sejak perbaikan naik (12-Agu 19:54) **tak sekali pun**
- Hitungannya bahkan tak sampai ambang: 21 dilewati + 2 dihitung = **2** dari ambang 3
- **Yang menghentikannya: tenant mematikan channelnya sendiri** — bukan mesin

**Kenapa 880 uji hijau tak menangkapnya:** seluruh uji rem memeriksa **angka di dalam mesin**
(`streak == 3`), dan angka itu MEMANG benar. Yang salah adalah akibatnya di dunia nyata. Commit-nya
bahkan menulis *"jangkauan terbukti sempit — dipakai di SATU tempat untuk SATU keputusan"*: benar
secara harfiah, menyesatkan secara akibat, karena **titik panggil** dihitung dan **akibat** tidak.

**PENCABUTAN 14-Agu:** setiap kegagalan dihitung kembali, apa pun kelasnya (perilaku sebelum 12-Agu).
Aman, dan bukan sekadar mundur: mudarat yang dikejar 12-Agu akarnya sudah ditutup 3-Agu oleh [B25] —
kelas error TERSIMPAN saat rem menyala, layar memberi panel per-KELAS (*"pulih sendiri — tak ada yang
perlu Anda ubah"*) + tombol *Pulihkan produksi*, Telegram membedakan pulih-sendiri dari
butuh-tindakan. Bang Us-Dat menganggur 11 hari karena kelasnya tersimpan `unknown` sehingga panelnya
bisu — **bukan** karena rem menyala. Rem + panel yang bicara = tenant kehilangan satu tekanan tombol,
bukan kehilangan channelnya.
**Dampak pencabutan diukur pada data nyata sebelum dikirim:** **nol** channel aktif yang langsung
direm saat perbaikan naik (12 channel diperiksa satu per satu).

**Dijaga PERILAKU, bukan angka perantara** — `tests/test_rem_tak_boleh_lumpuh.py`: berapa kali
produksi di-submit · berapa kabar terkirim · apakah mesin berhenti sendiri; ditulis atas SELURUH
anggota `ErrorClass` supaya kelas baru ikut terjaga tanpa uji disunting. Merah dibuktikan lebih
dulu: pengecualian 12-Agu dihidupkan kembali → **14 uji gagal**.

**⏳ MASIH TERBUKA — keputusan produk, sengaja TIDAK diputuskan sendiri (§0.6 CLAUDE.md):**
1. **Jeda sementara** untuk sebab yang pulih sendiri — mesin berhenti mencoba lalu jalan lagi
   otomatis, **satu** kabar saja. Ini jalan keluar yang benar untuk KEDUA mudarat (banjir *dan*
   channel menganggur), tapi ia memilih angka & kebijakan baru. Yang perlu diketok: **lama jeda**
   (ikut waktu yang penyedia sebutkan — sudah tersimpan, 56 sampel §8h — / jeda tetap / sampai ganti
   hari) · **jumlah kabar** (satu saat jeda mulai; perlu satu lagi saat jalan kembali?) · **tombol
   Uji/Jalankan Ulang** boleh menembus jeda atau ikut ditahan. Bandingkan batasan §9: *"pemulihan =
   keputusan TENANT"* — mengubahnya butuh ketok baru.
2. ~~Saklar aktif/nonaktif channel tidak menutup periode kegagalan~~ — ✅ **DITUTUP 14-Agu (migr 0198).**
   Migrasi 0197 (§8c) mewajibkan *setiap* jalur pelepas rem mencatat `production_resumed_at`; jalur
   saklar terlewat. Akibat terukur: BISIK NUSANTARA & Thetangga menyimpan hitungan **12** ⇒ begitu
   tenant menyalakannya kembali, mesin mengerem **seketika, tanpa satu percobaan pun**.
   **Diperbaiki di DATABASE, bukan di layar** — ketetapan owner 14-Agu (*"pastikan setiap perbaikan
   bersifat GENERIK"*) berlaku untuk JALUR, bukan hanya untuk vendor: menulisnya di layar hanya
   menutup layar yang ada hari ini, dan jalur admin/API/skrip/layar-yang-belum-dibuat akan
   melewatinya — persis cara cacat ini lahir (0197 menutup 3 jalur, melewatkan 1). Trigger
   `channels_catat_pengaktifan` menutup **setiap** jalur tanpa satu baris kode aplikasi.
   **TIDAK menyentuh `production_paused`** ⇒ channel yang direm tetap direm; [B25] utuh.
   **Bukti runtime pada data NYATA** (di dalam transaksi yang dibatalkan ⇒ nol baris tenant berubah):
   matikan → titik pemulihan **tidak** bergeser · nyalakan → **bergeser** · update biasa → **tidak** ·
   kolom rem **tak tersentuh** · urutan trigger terverifikasi (gerbang aktivasi → 0198 → penjaga rem).
   **Akibat sampingan yang menyenangkan:** dua channel dengan hitungan 12 kini sembuh **sendiri**
   saat tenantnya menyalakannya — pemulihan data manual (butir 8 rencana) jadi TIDAK PERLU, dan nol
   data tenant kami sentuh. Dijaga `tests/test_migrasi_selaras_db.py` (trigger hidup + urutannya).
3. ~~Waktu tenant menyalakan/mematikan channel tidak terekam~~ — ✅ **DITUTUP 14-Agu (migr 0198).**
   Saklar hanya menulis `is_active`; tak ada pencatat otomatis, sehingga `updated_at` basi (catatan
   BISIK masih 13-Agu padahal banjirnya 14-Agu) dan satu-satunya sebab kami tahu tenant mematikan
   channelnya adalah karena owner memberitahukannya. Trigger yang sama kini mencatat `updated_at`
   pada **setiap** perubahan channel, dari jalur mana pun.
4. ~~Kode Cloudflare `5006` + parameter `seed`~~ — ✅ **DITUTUP 14-Agu.** Dua sisi, keduanya generik:
   **(a) PENCEGAHAN — akar masalahnya.** `seed` **tidak ada dalam skema resmi** FLUX schnell (hanya
   `prompt` + `steps`, dibaca 14-Agu); kita mengirimnya dan Cloudflare menerimanya diam-diam
   berbulan-bulan, lalu mulai memvalidasi skema: **1× 8-Agu · 1× 11-Agu · 10× 13-Agu · 22× 14-Agu**
   (37 kejadian, tren NAIK). Satu adegan gagal menggagalkan seluruh produksi (§8i) ⇒ yang hangus
   adalah pekerjaan yang hampir jadi: 248/442/341 detik · 15/34/26 panggilan LLM · 4/6/5 gambar ⇒
   **±$0,068 uang TENANT dalam 2 hari, untuk kesalahan KITA.** Rem "jangan bakar duit tenant"
   (ketok owner 17/18-Jul) secara struktur tak bisa menangkapnya — sebabnya bukan "kredit habis".
   Kini `seed` dikirim **hanya bila skema model menyatakan menerimanya** (`ai_models.default_params.
   supports_seed`, nol migrasi); **default = TIDAK mengirim** ⇒ model/vendor BARU otomatis aman
   tanpa seorang pun perlu mengingatnya. `fal flux/dev` ditandai mendukung (skema resminya memuat
   `seed`, dibaca 14-Agu) ⇒ Diversity §9.1 utuh di sana.
   **(b) KEJUJURAN — lintas-vendor.** Jaring `_RX_PARAM_CACAT` di jalur **generik** (bukan di tabel
   Cloudflare): kalimat vendor yang menolak PROPERTI/PARAMETER ⇒ `milik_kita=True`, berlaku untuk
   vendor yang belum ada sekalipun — alasannya semantik, bukan tebakan: parameter permintaan hanya
   bisa datang dari kami. Sengaja **sempit**: pola lebar (*"not allowed"* · *"bad input"* ·
   *"invalid"*) diuji pada seluruh pesan vendor nyata dan **ditolak** karena akan menangkap
   *"API key invalid"* — salah-alamat ke arah sebaliknya sama merusaknya (tenant menunggu kami
   membereskan hal yang hanya bisa ia bereskan sendiri).
   **Kelas tetap `unknown`** ⇒ nol perubahan perilaku rem. Dijaga
   `tests/test_parameter_kita_tak_ditimpakan_tenant.py` (merah dibuktikan dua arah: 8 & 10 gagal).
   ⚠️ **Batas yang diakui:** `videos.visual_seed` tetap mencatat seed yang DIPILIH walau tak dikirim
   ke model yang tak mendukung — angka itu tak berpengaruh di sana. Dan model fal lain
   (`flux-schnell`) belum diperiksa dokumennya ⇒ sengaja tidak ditandai (ragu → aman).
   ⚠️ **Kode `3030`** (prompt ditolak penyaring konten CF, 2 kejadian nyata) **sengaja TIDAK
   dipetakan**: tidak ada di dokumen resmi, dan pemiliknya ambigu — §5.3 "yang RAGU tetap UNKNOWN".

### 8L. ~~MESIN MATI MENDADAK~~ — ✅ **AKAR DITEMUKAN & DITUTUP 2026-08-15**

> ## 🎯 AKAR PENYEBAB — **CACAT PENGUMPUL SAMPAH (GC) PADA `Python 3.11.0rc1`**
>
> *(dibongkar dari INSTRUKSI MESIN di titik crash + catatan kernel + rekaman memori 387 MB —
> bukan disimpulkan. Owner menolak versi sebelumnya dari catatan ini karena ia masih dugaan; itu
> benar, dan bagian ini menggantikannya dengan rantai bukti.)*
>
> **Instruksi persis di ketiga titik crash — dibongkar dari biner rc1 ASLI** (diunduh ulang; cap
> waktunya **identik sampai detik** dengan yang tercatat di laporan crash: `1660298534` =
> 12-Agu-2022 17:02:14):
>
> ```
>   and  $0xfffffffffffffffc, %rdx     ; buang 2 bit penanda → dapatkan penunjuk
>   mov  %rcx, (%rdx)                  ; ← MATI DI SINI (menulis ke penunjuk itu)
>   and  $0x3, %eax  /  or ...         ; pasang kembali 2 bit penanda
> ```
>
> Pola **masker `~3` + dua bit penanda** itu tanda tangan khas `_PyGCHead_SET_NEXT/SET_PREV` —
> pembaruan **rantai ganda (doubly-linked list) milik pengumpul sampah CPython**, di mana 2 bit
> terendah `_gc_prev` dipakai sebagai penanda (`FINALIZED`/`COLLECTING`). Alamat yang ditulisi
> bernilai **NOL** ⇒ **rantai objek GC-nya rusak.** Ketiga crash memakai pola yang SAMA di titik
> panggil yang berbeda — konsisten dengan rantai yang korup, bukan satu bug kode.
>
> **Dan cacat itu memang ada di versi tersebut, terdokumentasi resmi:** CPython 3.11 punya
> beberapa cacat korupsi memori di GC yang **baru diperbaiki pada rilis 3.11.2 & 3.11.3** — antara
> lain **gh-101975** (*"fix stacktop value … to avoid **corruption on garbage collection**"*) dan
> **gh-102397** (*"fix segfault from **race condition in signal handling during garbage
> collection**"*), plus perbaikan crash GC subinterpreter di 3.11.2.
> **Mesin kita berjalan di `3.11.0rc1` — keluar SEBELUM 3.11.0 final, jadi tak memuat SATU PUN
> perbaikan itu.**
>
> | Mata rantai | Status |
> |---|---|
> | Crash berada di dalam pembaruan rantai GC | ✅ dibongkar dari instruksi mesin |
> | Rantai GC rusak (menulis ke alamat NOL) | ✅ terbukti |
> | Bukan kode kita / pustaka lain | ✅ seluruh `ip` di dalam biner `python3.11` |
> | Bukan perangkat keras · bukan OOM | ✅ nol proses lain crash · nol galat memori · nol OOM |
> | Versi itu memang bercacat korupsi GC | ✅ terdokumentasi (3.11.2 / 3.11.3) |
> | Versi kita lebih tua dari semua perbaikan | ✅ cap waktu biner cocok persis dengan rc1 |
> | Versi baru memuat seluruh perbaikan | ✅ 3.11.15, sudah aktif di produksi |
>
> ⚠️ **Yang TETAP tak bisa dibuktikan (dan tak diklaim):** bahwa crash-nya berhenti. Ia datang
> ±1× per 4 hari tanpa pola; membuktikannya butuh HARI tanpa kejadian, bukan menit. Garis dasar
> untuk pemantauan: **11 crash, 3-Jul → 13-Agu**.
>
> 🔬 **Cara temuan ini didapat — dan kenapa 4 dugaan sebelumnya gugur:** rekaman memori 387 MB
> dibongkar (`apport-unpack`), keadaan prosesor ke-14 thread dibaca langsung dari catatan ELF,
> lalu `rip` dipetakan ke pustaka lewat `ProcMaps`. **Temuan penting yang membalik pembacaan awal:**
> `rip` crash 14-Agu jatuh di **`pthread_kill` (libc)** — itu BUKAN titik crash, melainkan tempat
> perekam kematian MELEMPAR ULANG sinyalnya. Karena perekam baru naik 13-Agu, maka **hanya crash
> SEBELUM 13-Agu yang alamatnya asli** — dan alamat-alamat itulah yang dibongkar di atas.
>
> Bukti dari `dmesg` (catatan kernel — lapis terdalam yang bisa kita baca): **11 kali crash antara
> 3-Jul dan 13-Agu**, dan polanya tak bisa ditafsirkan lain:
>
> | Yang tercatat | Jumlah | Artinya |
> |---|---|---|
> | `segfault at 0` | 5× | menyentuh alamat **NOL** — penunjuk kosong |
> | `segfault at 1` · `at ffffffffffffffff` · alamat acak | 3× | penunjuk **liar/rusak** |
> | `general protection fault` | 1× | akses memori tak sah |
> | alamat instruksi (`ip`) yang BERBEDA | **10 titik berbeda** | crash di **tempat yang berlainan** |
>
> **Ketiga hal ini bersama-sama hanya berarti satu hal: kerusakan memori di dalam penerjemah.**
> Semua `ip` berada di dalam berkas biner `python3.11` **itu sendiri** (`41f000+2c2000`) — bukan di
> pustaka mana pun. Dan penyebab lain sudah disingkirkan satu per satu, dengan pemeriksaan:
> **bukan tumpukan jebol** (alamat kesalahannya jauh dari penunjuk tumpukan; lagipula pembangunan
> skema hanya butuh **64–96 KB** sedangkan thread produksi punya **8 MB** = 128× lebih) ·
> **bukan perangkat keras** (nol galat memori kernel, dan **nol proses selain python** yang crash
> di server yang sama) · **bukan kehabisan memori** (nol catatan OOM).
>
> **PERBAIKAN: penerjemah dimutakhirkan DI TEMPAT** — `python3.11` sistem dari **3.11.0rc1 →
> 3.11.15 stabil**, lewat paket yang memang sudah ditunjuk `venv` (`venv/bin/python3.11 →
> /usr/bin/python3.11`). **Nol lingkungan baru · nol jalur baru · nol perubahan kode.** Diverifikasi
> sesudahnya: **24 pustaka + 18 modul mesin termuat sempurna**, paket terkompilasi utuh (wheel
> `cp311` sekompatibel di seluruh 3.11.x).
>
> ⚠️ **EMPAT DUGAAN SAYA GUGUR SEBELUM YANG BENAR KETEMU — semuanya diuji, bukan ditinggalkan
> begitu saja:** *(1)* tumpukan Python jebol → rekaman hanya **57 frame** (butuh ribuan) ·
> *(2)* tumpukan C jebol → butuh 64–96 KB, tersedia 8 MB · *(3)* penerjemah 3.11.0 saja → diuji
> dengan memasang 3.11.0 **asli**, jalur crash yang sama: **selamat** · *(4)* versi pydantic
> (server 2.13.4 ≠ lokal 2.12.5) → diuji dengan versi **persis server**: **selamat**.
> Yang menuntun ke jawaban akhirnya bukan reproduksi, melainkan **catatan kernel** — lapis yang
> sejak awal menyimpan jawabannya dan baru saya baca paling belakangan.
>
> ℹ️ **Pemanasan skema (di bawah) TETAP DIPASANG, tapi ia BUKAN perbaikan akar** — ia lapis
> pertahanan yang berdiri sendiri (memindahkan pekerjaan berat keluar dari thread produksi),
> tak mengubah perilaku apa pun, dan gagal-terbuka. Jangan salah baca sebagai penyembuhnya.
>
> ⚠️ **DUA DIAGNOSIS SAYA SENDIRI GUGUR SEBELUM YANG BENAR KETEMU — dicatat supaya tak diulang:**
> **(1)** *"tumpukan jebol karena rekursi terlalu dalam"* → **GUGUR**: rekamannya hanya **57 frame
> Python**; jebolnya tumpukan Python butuh RIBUAN. Yang jebol adalah tumpukan **C**, dan itu
> pembedaan yang menentukan seluruh arah perbaikan.
> **(2)** *"cukup panaskan model teratas"* → **GUGUR, DAN NYARIS DIKIRIM**: diukur, `ChatCompletion.
> model_rebuild()` menyiapkan induknya saja — `Choice`, `ChatCompletionMessage`, `CompletionUsage`
> **tetap tertunda**, padahal SDK mengurai balasan secara bersarang dan menyentuh SETIAP tingkat.
> Perbaikan setengah itu tidak akan menyembuhkan apa pun, dan hijaunya uji tak akan menunjukkannya.
> Pelajaran yang mengikat: **periksa PERILAKU akhir (apakah masih ada `model_rebuild` saat balasan
> diurai), bukan atribut satu objek.**

<details><summary>Catatan saat pertama ditemukan (disimpan sebagai riwayat sebab-akibat)</summary>


**Perekam kematian ([B26] bagian D, naik 13-Agu) berbicara untuk PERTAMA KALINYA** — dan langsung
menunjuk tempat yang selama ini gelap. Sampai hari ini catatan resminya berbunyi *"sebab mesin mati
mendadak masih belum diketahui (Pillow/font DICABUT · OOM disingkirkan)"*.

**Kejadian:** 14-Agu 23:00:52, ±20 detik setelah produksi RETRO REWIND dimulai.
`systemd`: `Main process exited, code=killed, status=11/SEGV`. Mesin dihidupkan kembali otomatis
23:01:02, dan pesan *"MESIN SEBELUMNYA MATI MENDADAK"* terkirim ke owner ✅ (mekanisme 13-Agu bekerja).

**Rekaman detik kematian (`Fatal Python error: Segmentation fault`), tumpukan panggilannya:**
```
openai/_models.py            _get_extra_fields_type
pydantic/_internal/_mock_val_ser.py   __getitem__ → _get_built → handler
pydantic/main.py             model_rebuild
pydantic/_internal/_model_construction.py  complete_model_class
pydantic/_internal/_generate_schema.py     generate_schema → _generate_schema_inner
                                           → _model_schema → <dictcomp>   ← BERULANG
```
Artinya: saat SDK OpenAI-compatible mengurai balasan penyedia, **pydantic membangun skema modelnya
secara rekursif sampai tumpukan panggilan habis**. Ini bukan `RecursionError` Python (yang bisa
ditangkap) melainkan **stack overflow di lapis C ⇒ SIGSEGV**, yang mematikan SELURUH proses — ketujuh
thread ikut mati bersamanya.

**Frekuensi terukur:** `journalctl` mencatat **6 SEGV sejak 1-Agu**. Hanya yang terakhir punya
rekaman, karena perekamnya baru naik 13-Agu.

**Kenapa ini mahal, bukan sekadar restart:**
- Produksi yang sedang berjalan **hilang tanpa jejak** — run 23:00:31 tak pernah menghasilkan baris
  `production_runs`. Bagi sistem kita ia tak pernah ada; tenant tak dikabari apa pun.
- Ini bentuk kerugian yang sama dengan video `xa3Rbi-SbXM` (12-Agu, §11): pekerjaan hilang, catatan
  kosong, tak seorang pun tahu.
- **Tak satu pun mekanisme galat AI bisa menangkapnya** — proses mati sebelum sempat menggolongkan
  apa pun. Karena itu ia dicatat di sini: ia MEMOTONG seluruh rantai §3.

⚠️ **Diperiksa dan DIBANTAH: bukan dari perbaikan 14-Agu.** Kematian terjadi di STEP 1-2 (pemilihan
topik, jalur naskah) — jauh sebelum jalur gambar yang disentuh perbaikan `seed`; perubahan hari itu
seluruhnya Python murni (pola teks + pembacaan dict + trigger SQL) yang **tidak bisa** menghasilkan
SIGSEGV; dan 5 dari 6 kejadian terjadi **sebelum** perbaikan itu ada.

</details>

#### Rantai lengkap — dari frame PALING BAWAH (yang memulai), rekaman 14-Agu 23:00:52

```
producer._task → produce_one → pipeline.run → niche_selector.select → _analyze_with_ai
  → adapters.complete → openai chat.completions.create → _base_client.post → request
  → [balasan diurai] → openai/_models.py  _get_extra_fields_type
  → pydantic _mock_val_ser → model_rebuild → complete_model_class
  → generate_schema → _model_schema → _union_schema → _list_schema → … (rekursif) → SIGSEGV
```

`_get_extra_fields_type` menyentuh `cls.__pydantic_core_schema__`, dan **sentuhan itulah** yang
memicu pembangunan skema. Ia dipanggil untuk **setiap tingkat** balasan yang diurai.

#### Perbaikan — `src/utils/pemanasan_skema.py` + satu panggilan di `worker_decoupled.main()`

Skema dibangun **satu kali di alur UTAMA saat mesin start**, sebelum satu thread pun dibuat, saat
tumpukan masih kosong dan ruangnya lapang. Yang dipanaskan = **setiap turunan `BaseModel` milik SDK**
(terukur **1.049 model dalam 2,4 detik**) — bukan hanya model teratas, sebab diagnosis-gugur (2) di
atas membuktikan itu tidak cukup.

⚠️ **CELAH KETIGA yang nyaris lolos (diukur 15-Agu):** memuat `openai.types` saja menyiapkan 747
model — lalu begitu `openai.resources.*` ikut dimuat, muncul **308 model BARU** yang belum panas.
Sebabnya: SDK memuat modul sumber dayanya secara MALAS, dan kode mesin mengimpor SDK **di dalam
fungsi** (`from openai import OpenAI` di adaptor · `AsyncOpenAI` di jalur gambar) — yaitu **di dalam
thread produksi**, persis keadaan yang hendak dihindari. Karena itu `resources` ikut diimpor lebih
dulu di alur utama.

**UKURAN "TUNTAS" yang dipakai — dan kenapa bukan "semua model":** SDK memuat ratusan model untuk
endpoint yang mesin ini **tidak pernah panggil** (realtime · webhooks · evals · conversations);
menjamin semuanya panas mustahil dan tak ada gunanya. Yang dijaga adalah **ketiga jalur yang mesin
benar-benar lewati** — naskah (chat) · gambar (images) · naskah-Anthropic — diuji dengan mengurai
balasan berbentuk NYATA lalu memastikan **NOL `model_rebuild` terpanggil**.

**GENERIK atas ketetapan owner** (*"AI model & vendor akan terus bertambah"*): yang didaftar adalah
**awalan modul** (`openai` · `anthropic`), bukan nama kelas — nama kelas berubah tiap versi SDK dan
mustahil dijaga lengkap. Menambah vendor = tambah **satu kata**. SDK tak terpasang dilewati diam-diam.
**Gagal-terbuka**: pemanasan yang gagal tak pernah menghentikan mesin (pencegahan, bukan syarat).

#### Bukti penjaga — direproduksi dua arah, bukan disimpulkan

`tests/test_mesin_tak_mati_mendadak.py` (12 uji): membangun skema di thread bertumpuk sempit **tanpa**
pemanasan ⇒ proses **dibunuh sinyal**; **dengan** pemanasan ⇒ selesai wajar. Uji intinya memeriksa
**PERILAKU akhir**: sesudah pemanasan, mengurai balasan berbentuk NYATA (lengkap field tambahan
`x_groq` yang memicu `_get_extra_fields_type`) **tidak memanggil `model_rebuild` sama sekali**.
Urutan panggilan diperiksa dari **pohon sintaks**, bukan pencarian teks (komentar sudah 4× menipu uji
berbasis teks di proyek ini). **Merah dibuktikan lebih dulu:** kembali ke "model teratas saja" ⇒
6 gagal · pemanasan dipindah sesudah thread ⇒ 2 gagal.

### 8m. ~~GOLONGAN KOSONG MELUMPUHKAN PANEL PEMULIHAN~~ — ✅ **DITUTUP 2026-08-15**

**Dilaporkan lewat pertanyaan owner** *"apakah mesin sudah cukup jelas memberi tahu 2 tenant itu?"* —
dan jawabannya tidak, dengan sebab yang lebih dalam dari sekadar pesan tumpul.

**Cacatnya:** migrasi **0196** (3-Agu) hanya **MENAMBAH** kolom `channels.production_paused_class`;
**nol perintah mengisi baris lama** (diverifikasi: `UPDATE` = 0 di berkas migrasinya). Komentar kolom
itu bahkan **menuliskan sendiri** *"NULL = rem menyala sebelum kolom ini ada"* — keadaan itu disadari,
ditulis, lalu **tak pernah ditangani**.

**Kenapa bukan sekadar pesan tumpul.** `PemulihanChannel` memilih **judul · penjelasan · tombol
tindakan · DAN jalur pemulihan** dari golongan itu:
```ts
const ujiJalurYangBenar = bisaUji && r.pulihSendiri === false;
```
Golongan kosong ⇒ `pulihSendiri = null` ⇒ tenant diarahkan ke **"Pulihkan produksi"**. Untuk sebab
yang menuntut tindakan, itu **jebakan**: tekan tanpa memperbaiki ⇒ gagal lagi ⇒ direm lagi — persis
insiden 3-Agu yang komentar di berkas itu sendiri peringatkan.

**Akibat TERUKUR (15-Agu):** dua channel tenant **BERBAYAR** diam **13 & 24 hari** sambil membaca
*"Kami belum bisa memastikan penyebab pastinya — hubungi dukungan"*, padahal:

| Channel | Yang mesin SUDAH tahu (`production_runs`) | Yang tenant lihat |
|---|---|---|
| **Abyss ID** (24 hari) | `model_unavailable` — **panelnya sudah ada**: *"Ganti model"* + tautan ke pengaturan | *"belum bisa memastikan penyebabnya"* |
| **Bang Us-Dat** (13 hari) | `unknown` (penggolongan Groq belum ada saat itu) | idem |

Dan kalimat teknis yang tersimpan justru **menyesatkan**: *"Periksa kredensial/konfigurasi"* —
kredensial Bang Us-Dat baik-baik saja; yang terjadi hanya jatah harian habis, **sudah pulih keesokan
harinya (terbukti: 2× produksi sukses 2-Agu)**.

**Perbaikan:** layar mengambil golongan **CADANGAN dari kegagalan TERAKHIR** bila kolomnya kosong —
sumbernya `production_runs`, **tabel yang SAMA dengan yang dibaca rem darurat di mesin**, sehingga
layar & mesin tetap membaca dunia yang sama (§3: nol jalur yang bercerita sendiri).
**Nol jalur baru** (halaman itu sudah membaca `production_runs`) · nol migrasi · nol perubahan mesin.

**Bukti pada data NYATA — dan batas jujurnya:** Abyss ID berubah dari *"hubungi dukungan"* menjadi
**"Ganti model"** ✅. **Bang Us-Dat TIDAK berubah** — golongan kegagalan terakhirnya memang tersimpan
`unknown`, jadi mesin sungguh tak tahu dan layar **tidak boleh mengarang**. Perbaikan ini menolong
**1 dari 2**, dan itu disebut apa adanya.

**Dijaga** `tests/test_pemulihan_tak_menjebak.py` (`test_golongan_kosong_punya_CADANGAN`, merah
dibuktikan). Uji lama yang mengikat **teks harfiah** titik panggil diperketat ke **kontraknya** —
niat aslinya utuh, hanya berhenti mengunci susunan huruf.

⚠️ **Diakui, tidak diperluas:** layar admin (`/admin/system`) memakai kolom yang sama dan menampilkan
`—` untuk rem lama. Itu **informatif saja — tak mengarahkan siapa pun ke jalur yang salah**, jadi
sengaja tidak ikut disentuh (jangan melebarkan lingkup tanpa kerugian nyata).

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

**⚠️ KECUALIAN YANG MENGIKAT — kegagalan MILIK KITA tidak memakai anjuran di atas** *(13-Agu 2026)*.
Tabel ini menganggap penyebabnya ada di **akun penyedia AI tenant**. Bila penandanya `milik_kita=True`
(setelan kurang, permintaan kita cacat, FFmpeg, **atau penyimpanan kita** — §4b), seluruh anjuran itu
menjadi **salah alamat**: menyuruh tenant "isi ulang kredit" atas tagihan penyimpanan KAMI adalah
kesalahan yang menagih orang yang tak berutang. Kalimatnya wajib **mengaku di sisi MesinViral** dan
tidak meminta tenant mengerjakan apa pun.
**Sampel yang melahirkannya:** 13-Agu 06:00, tenant menerima `403 HeadObject Forbidden` + nama berkas
internal, padahal sebabnya akun penyimpanan kami diblokir karena tagihan.
**Dijaga:** `tests/test_notifikasi_owner_dan_tenant.py` (kelas `TestPesanGagalTerbit`).

**Pemulihan produksi = keputusan TENANT, bukan sistem.** Sistem tidak pernah melepas rem sendiri karena
sebab teknis dianggap sudah lewat. Pengecualian tunggal yang sudah diketok owner: rem dilepas otomatis
saat **langganan aktif kembali** (pembayaran/aktivasi admin) — konteks langganan, bukan kegagalan
teknis. Lihat `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` §10b K2.

### §9a JALUR PEMULIHAN per kelas — ditentukan oleh SEBAB, bukan oleh gerbang uji *(dipatri 2026-08-06)*
| Kelas | Yang ditawarkan panel | Kenapa |
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

## §9b PINTU KEDUA — channel yang DIAM *(dibuka 2026-08-21; Batch A terpasang, Batch B siap-deploy)*

§9 di atas mengikat jalur **produksi berjalan**. Ada jalur KEDUA yang selama ini **tidak tersambung
ke arsitektur ini sama sekali**, dan di situlah kerusakan 17-Agu terjadi:

| Pintu | Jalur | Terklasifikasi | Tenant diberi tahu |
|---|---|---|---|
| Model mati saat produksi **JALAN** | pipeline → adapter → registry §4 → `MODEL_UNAVAILABLE` | ✅ | ✅ sebut model + penyedia |
| Model mati saat channel **DIAM** | gerbang kesiapan → label `'model naskah'` → **skip senyap** | ❌ | ❌ |

**Akibat terukur:** 4 channel berhenti **4 hari** (2 tenant BERBAYAR langganan aktif) tanpa seorang
pun diberi tahu; log dibanjiri **20.979 baris** dalam 5 hari. BISIK NUSANTARA yang lewat pintu-1
dapat pesan jelas dan beres sendiri — yang lewat pintu-2 **tidak punya suara sama sekali**.

### Kenapa labelnya TIDAK boleh diperbaiki (kontrak yang mengikat selamanya)

`channel_missing()` mengembalikan **16 label pendek**, dan label itu adalah **KUNCI MESIN**: checklist
7 baris di layar tenant mencocokkan **katanya** (`channels/[id]/page.tsx` → `has("naskah")` dst).
Mengubah teksnya membuat checklist itu **salah** — hijau padahal rusak. Itu kelas kerusakan 17-Agu.
⇒ Perbaikan **wajib aditif**. Ke-16 label dikunci uji (`tests/test_alasan_terhalang_bukan_label_telanjang.py`).

### Bentuk perbaikannya (migr `0204`)

```
SEKARANG : { ready:false, missing:["model naskah"] }
SESUDAH  : { ready:false, missing:["model naskah"],            ← IDENTIK
             reasons:[{slot,code,model,provider,provider_name}] }   ← BARU
```

- `channel_blockers(ch)` + `channel_blockers_by_id(uuid)` = fungsi **BARU**; `channel_missing()` **tak disentuh**.
- `code` memakai kosakata `ErrorClass` yang sudah ada — **nol kosakata baru**: `model_unavailable` ·
  `voice_unavailable` · `model_not_in_catalog`.
- **Lingkup sengaja sempit:** hanya keadaan yang bisa diukur pasti (baris katalog yang ditunjuk channel
  sudah tidak aktif / tidak ada). Sisanya tetap label-saja — tak diklaim lebih dari yang terbukti.
- `readiness.py` meneruskannya **fail-soft** dan **hanya saat channel tidak siap** (producer memutari
  seluruh channel tiap ±16 detik; mengambilnya untuk channel sehat = panggilan DB sia-sia).

### Dua kalimat yang berubah, dan kenapa

| Sebelum | Sesudah | Sebab |
|---|---|---|
| titik merah "Penulis Naskah (LLM)" tanpa keterangan | *"Pilihan Anda `llama-3.3-70b-versatile` sudah tidak tersedia di Groq — pilih penggantinya."* | tenant punya **3 slot AI**; tanpa nama model & penyedia, "pilih model lain" tak bisa dikerjakan |
| pilihan tenant **hilang** dari daftar model | pil **TERKUNCI** bertanda *"tidak lagi tersedia"* | pemilih menyaring `is_active=true`; **melihat ≠ memilih** — jalur simpan tak memvalidasi katalog, jadi pil yang bisa diklik akan MENAMBAH channel menggantung |

### Batas jujur

Belum tercakup: model **aktif** tapi `provider_key`-nya ≠ `channels.llm_library` (paket campuran) —
gerbang tetap menahannya, tapi lewat label telanjang. Tercatat, bukan diklaim selesai.

### Batch B — KATALOG BELAJAR, dan kegagalan KAMI berhenti menuduh tenant

Dua cacat yang tersisa dari pintu-2, keduanya **aditif**, nol data tenant disentuh.

#### B-1 · Gagal-baca sesaat HARAM berbunyi seperti kelalaian tenant

RAD The Explorer gagal 20-Agu 21:00 dengan *"Kredensial wajib belum lengkap: visual_api_key"* lalu
**berhasil 21:07** tanpa seorang pun menyentuh apa pun. Kredensialnya tak pernah berubah. Yang
terjadi: jaringan ke DB terputus sekejap → kode menyetel kunci **kosong** → gerbang membacanya
*"tenant belum mengisi"*. **Kegagalan kami, dituduhkan ke tenant.**

Tiga titik yang menelan galat kini **bersuara** dan menandai `TenantRunConfig.baca_gagal`
(`_set_key_from_pool` · `_visual_provider` · `niche_visual_style`). Gerbang kredensial di
`pipeline.py` **bercabang atas penanda itu**, bukan menebak dari teks di hilir:

| Sebab | Golongan | Kalimat ke tenant |
|---|---|---|
| tenant memang belum mengisi | *(seperti dulu)* | "Kredensial wajib belum lengkap: …" |
| **KAMI gagal membacanya sesaat** | **`TRANSIENT`** + `milik_kita=True` | *"Setelan channel gagal dibaca sesaat — sistem akan otomatis mencoba kembali. Tidak ada yang perlu Anda ubah."* (redaksi diketok owner 21-Agu) |

`TRANSIENT` ada **di luar** `FAST_FAIL` ⇒ **ambang rem tidak bergeser** (dikunci uji dua arah).
Kejujuran kalimatnya terukur: producer adalah loop hidup ±16 detik, dan RAD memang pulih dalam 7 menit.

#### B-2 · Karantina model — bukti yang SUDAH di tangan, nol rupiah

Mesin sudah membuktikan kematian model (**7 run** `model_unavailable`), tapi **nol baris kode pernah
menyentuh `ai_models`**. Model yang terbukti mati tetap ditawarkan ke tenant berikutnya (Abyss ID
diam **24 hari**). Rancangan semula — membuktikan dengan memanggil vendor memakai kunci admin/Test
Lab — **ditolak owner 21-Agu**: itu membakar kredit owner diam-diam. **Dibuang.**

Penggantinya memakai bukti yang sudah kami pegang. **Nol panggilan berbayar** (dikunci uji):

| | Bukti | Kenapa ia menutup ambiguitas |
|---|---|---|
| **A** *(wajib)* | `Putusan.dasar` = `kode/teks-vendor` / `terusan-agregator` | vendor menyebut modelnya sendiri |
| **B1** | kata **GLOBAL** di pesan vendor: `decommission` · `no longer available` · `deprecated` · `retired` · `sunset` · `has been removed` | kata itu tak mungkin berarti "akun *Anda* tak punya akses" ⇒ **1 tenant cukup** |
| **B2** | **≥2 tenant BERBEDA** gagal pada model yang sama (`production_runs.failed_model`) | dua kunci API independen tak bisa sama-sama kehilangan akses karena kebetulan |
| **B3** | model hilang dari umpan harga publik (`price_sync` sudah menghitungnya tiap 24 jam) | lemah sendirian, **kuat** sebagai penguat A |

**A tanpa B ⇒ NOL karantina**, hanya alarm admin ber-bukti. **404 telanjang** (`dasar` =
`status-http-umum`) **HARAM** mengarantina — 404 bisa berarti alamat salah di sisi KITA.
Migr `0205` menambah `ai_models.unavailable_since` + `unavailable_reason` + `production_runs.failed_model`
(tanpa FK: riwayat harus utuh walau katalog berubah). Karantina **terasa ≤5 menit**, bukan seketika —
katalog Python ber-cache TTL 300 dtk. **Jalur buka:** admin menghidupkan kembali di panel; karantina
**tidak pernah** menyala sendiri.

> **⚠️ RANTAI YANG RAPUH, dan kerapuhannya tak terlihat dari membaca kodenya.** B1 mencari kata
> **Inggris milik vendor**. Pesan-manusiawi kami berbahasa **Indonesia** — terukur:
> `bukti_global("Model AI ini sudah tidak tersedia di penyedianya")` = `None`. Jadi mengalirkan
> `human_message`/`error_message` ke karantina (dan itu terasa **lebih rapi**) membuat B1 **mustahil**
> menyala dan seluruh jalur ini jadi **kode mati** — tanpa satu uji merah. Yang dialirkan **wajib**
> galat teknis (`result["error"]`, memuat pesan vendor apa adanya). Dikunci lewat **AST**, bukan
> pencocokan teks: sabotase membuktikan `pass  # karantina(sb, …)` lolos dari pencocokan teks.

#### B-3 · Mematikan baris katalog menyebut DAMPAKNYA

17-Agu saklar berpindah **tanpa suara**. Kini rute admin menghitung channel **aktif** yang masih
menunjuk baris itu dan mengembalikan `{perlu_konfirmasi, dipakai:[…]}` **status 200** — layar
menamai channelnya lewat `ConfirmDialog` **yang sudah ada di pustaka**. Ini **BUKAN penolakan**:
kalau vendor mematikan model, admin **wajib** tetap bisa mematikannya — blokir keras = *"kunci tanpa
jalur buka"* (sudah ditegur owner, `PAYMENT §10e-2`). Header `x-konfirmasi-dampak` = jalan LANJUT.
Dihitung **hanya saat `is_active` → false** (nol biaya untuk perubahan lain).

#### Batas jujur Batch B — dua hal yang TIDAK boleh dibaca sebagai selesai

1. **B2 tidak retroaktif.** `production_runs.failed_model` baru lahir di migr `0205`; **ketujuh** run
   riwayat berisi `NULL`. ⇒ bukti-silang antar-tenant mulai berlaku **ke depan**, bukan ke belakang.
   Praktiknya: B1 bekerja seketika (terbukti mengarantina `llama-3.3-70b-versatile` pada pesan Groq
   nyata), B2 mengumpulkan bukti dari kegagalan berikutnya.
2. **KOREKSI angka rencana.** Rencana 21-Agu menulis *"`gemini-2.5-flash` gagal di 2 tenant berbeda ⇒
   B2 menyala"*. Diperiksa ke DB: **tidak bisa dipertanggungjawabkan.** Dua tenant memang pernah
   gagal `model_unavailable`, tapi **4 dari 7 run tidak menyimpan nama model apa pun** — angka "2"
   itu saya rakit dari mengurai teks bebas, dan `failed_model` yang sesungguhnya kosong.
   **Klaim itu ditarik.**

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
> 4. `tests/test_terbit_dan_alarm_tak_senyap.py` *(13-Agu)* — jalur TERBIT & alarm penyimpanan:
>    galat mentah tak boleh masuk pesan tenant (§4b) · status alarm penyimpanan wajib **selamat dari
>    restart** · stok yang nyangkut di "sedang diterbitkan" wajib punya penyapu, dan keadaan yang
>    **tak bisa dipastikan wajib dilaporkan, bukan diterbitkan ulang**.
> 5. `tests/test_notifikasi_owner_dan_tenant.py` — bentuk pesan ke owner & tenant (nol kode mesin,
>    nol istilah teknis, nol potongan senyap) + sejak 13-Agu: kegagalan terbit **mengaku milik kita**.
> 6. `tests/test_rem_tak_boleh_lumpuh.py` *(14-Agu, §8k)* — **PERILAKU rem, bukan angka perantara:**
>    berapa kali produksi di-submit · berapa kabar gagal terkirim · apakah mesin berhenti sendiri.
>    Ditulis atas SELURUH anggota `ErrorClass` → kelas baru ikut terjaga tanpa uji disunting.
>
> ⚠️ **YANG TIDAK DIJAGA SIAPA PUN:** apakah pemetaan sebuah kode memang BENAR menurut dokumen
> vendornya. Mesin bisa memastikan tabel & kode sinkron; ia tidak bisa membaca dokumen vendor
> untuk Anda. Itu tetap pekerjaan manusia — dan di situlah §1 Aturan Emas berlaku.
>
> ⚠️⚠️ **BATAS YANG DIBAYAR MAHAL 13/14-Agu — hijau ≠ dokumen & mesin sejalan.** Ketiga penjaga di
> atas HIJAU sepanjang insiden §8k (880 uji lulus) sementara §1 & §3 dokumen ini menjanjikan rem
> yang **sudah tidak ada di mesin**, dan dua tenant dibanjiri 53 kabar gagal. Sebabnya: yang dijaga
> adalah **nama** kelas, **daftar** fast-fail, **keberadaan** berkas uji, dan tabel §4 — sementara
> yang bergeser adalah **kalimat SIKAP** ("toleransi normal"), **angka bukti**, dan **bentuk tabel**.
> Ketiganya kini dijaga (`TestSikapDokumenAdalahPerilakuNyata` · `TestAngkaBuktiUjiTidakBasi` ·
> `TestStrukturTabelDokumenUtuh`). Pelajaran yang tetap berlaku sesudahnya: **daftar penjaga ini
> bukan bukti kelengkapan** — ia hanya daftar hal yang sudah pernah gagal.

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
- **2026-08-21** — **§9b Batch B: KATALOG BELAJAR + kegagalan KAMI berhenti menuduh tenant.**
  Migr `0205` (aditif): `ai_models.unavailable_since`/`unavailable_reason` + `production_runs.failed_model`.
  Modul **baru** `src/orchestrator/karantina_model.py` — karantina hanya dari **A + (B1|B2|B3)**,
  **nol panggilan berbayar** (rancangan uji-berbayar dengan kunci admin **dibuang** atas keberatan
  owner 21-Agu) · gerbang kredensial `pipeline.py` bercabang atas `baca_gagal` yang ditandai di
  **titik kejadian** (`tenant_config.py`, 3 titik) dan digolongkan `TRANSIENT`+`milik_kita` dengan
  redaksi owner · rute+layar katalog admin menyebut channel aktif yang terdampak sebelum model
  dimatikan (`ConfirmDialog` pustaka, **status 200 — konfirmasi, bukan larangan**).
  **Bukti:** 20 uji baru · **26 sabotase semuanya MERAH** — dan sabotase menangkap **3 uji palsu
  saya sendiri**: (a) `from("channels")` lolos karena rute ini sudah mengueri `channels` **5× di
  kode lama**, (b) mengganti `ErrorClass.TRANSIENT`→`UNKNOWN` tetap hijau karena **komentar** di
  sebelahnya menyebut kata itu, (c) `pass  # karantina(…)` mematikan panggilannya tanpa satu uji
  merah ⇒ penjaganya dipindah ke **AST**. Ketiganya diganti. · **1231 uji hijau** · build FE lulus ·
  rujukan menggantung **tetap 5 (4 di channel aktif)** ⇒ **nol data tenant disentuh** · putusan
  karantina dijalankan pada **riwayat nyata**: pesan Groq `model_decommissioned` → **KARANTINA**;
  *"is not found **or you do not have access to it"*** → **alarm admin saja**; **404 telanjang** →
  **tidak** (persis ambang yang diminta). **Batas jujur** (§9b): B2 **tidak retroaktif**, dan klaim
  rencana *"2 tenant berbeda"* **ditarik** — 4 dari 7 run riwayat tak menyimpan nama model.
  Sisa: **Batch C** (6c panel katalog: buang-senyap `tts_profiles`, bisa membuat mesin TTS, gerbang
  kelayakan aktivasi, lahir nonaktif, paritas form↔whitelist) & **Batch D** (penjaga §7 + dokumen).
- **2026-08-21** — **§9b PINTU KEDUA TERSAMBUNG (Batch A: langkah 1·2·3·5 dari rencana owner).**
  Pemicu: owner melaporkan 2 kegagalan; penelusuran menemukan yang **tidak** dilaporkan — 4 channel
  (2 tenant BERBAYAR) mati 4 hari sejak 17-Agu 20:42 karena model naskahnya dimatikan di katalog
  tanpa seorang pun diberi tahu. **Migr `0204`** (aditif): `channel_blockers` + `channel_blockers_by_id`
  + kunci `reasons` pada `channel_readiness`; `channel_missing` & ke-16 labelnya **tak disentuh**.
  `readiness.py` meneruskan alasan (fail-soft, hanya saat tidak siap) · `producer.py` mencatat skip
  **sekali per KEADAAN** dengan penanda TERPISAH (`_READY_SUDAH_DICATAT`) — penanda cabang langganan
  di-`discard` tepat sebelum cek kesiapan, jadi memakainya di sini tak akan bekerja — dan alasannya
  ikut tercatat · layar channel + onboarding menyebut nama model & penyedianya · model terpilih yang
  mati tetap TERLIHAT tapi **terkunci** (`.radio-pill[aria-disabled]` ditambahkan ke **pustaka**
  `components.css` mengikuti konvensi `.btn:disabled` — nol gaya tempelan, nol komponen FE baru).
  **Bukti:** 20 uji baru, **12 dibuktikan MERAH dulu**, **11 sabotase** semuanya merah (dua di
  antaranya menangkap **uji palsu saya sendiri** — pemeriksaan yang tetap hijau walau perendernya
  dicabut; keduanya diganti) · 1211 uji hijau · build FE lulus · rujukan menggantung **tetap 5
  (4 di channel aktif)** ⇒ **nol data tenant disentuh** (prinsip owner 21-Agu) · 16 label utuh ·
  8 channel sehat **nol tuduhan palsu**. Kegagalan `TRANSIENT` yang menuduh tenant (langkah 4) &
  karantina katalog (6a) = **Batch B**, belum dikerjakan.
- **2026-08-15** — **§8L: AKAR "MESIN MATI MENDADAK" DITEMUKAN — PENERJEMAHNYA VERSI PRA-RILIS.**
  Mesin produksi berjalan di atas **Python 3.11.0rc1** (*release candidate*, Agu-2022) dan penerjemah
  itu **merusak memorinya sendiri**. Bukti dari catatan **KERNEL**: **11 crash antara 3-Jul dan
  13-Agu** · alamat kesalahan `0` (5×) · `1` · `ffffffffffffffff` · acak · satu *general protection
  fault* · dan **10 alamat instruksi BERBEDA, semuanya di dalam biner `python3.11` sendiri**.
  Penunjuk kosong/liar + titik crash yang berlainan = **kerusakan memori di penerjemah**, bukan bug
  satu jalur kode. Penyebab lain disingkirkan dengan pemeriksaan: **bukan tumpukan jebol** (alamatnya
  jauh dari penunjuk tumpukan; pembangunan skema butuh 64–96 KB, tersedia 8 MB) · **bukan perangkat
  keras** (nol galat memori kernel, **nol proses selain python** yang crash) · **bukan OOM** (nol).
  **PERBAIKAN: `python3.11` sistem dimutakhirkan DI TEMPAT ke 3.11.15 stabil** — paket yang memang
  sudah ditunjuk `venv`; **nol lingkungan baru, nol jalur baru, nol perubahan kode**. Diverifikasi:
  24 pustaka + 18 modul mesin termuat sempurna.
  **EMPAT dugaan saya GUGUR lebih dulu, semuanya diuji** (dicatat di §8L): tumpukan Python jebol
  (rekaman cuma 57 frame) · tumpukan C jebol (butuh 64–96 KB, ada 8 MB) · Python 3.11.0 saja (diuji
  dengan memasang 3.11.0 asli ⇒ selamat) · versi pydantic (diuji dengan versi persis server ⇒
  selamat). Yang menuntun ke jawaban bukan reproduksi, melainkan **catatan kernel — lapis yang sejak
  awal menyimpan jawabannya dan paling belakangan saya baca.**
  **Ikut dipasang sebagai lapis pertahanan (BUKAN perbaikan akar):** pemanasan skema SDK di alur utama
  saat start (1.049 model, 2,4 dtk) ⇒ pembangunan skema tak lagi terjadi di dalam thread produksi.
  Dijaga 12 uji, reproduksi dua arah, merah dibuktikan lebih dulu (6 & 2 gagal).
  **KEJUJURAN — satu bug saya tanam di putaran ini dan tertangkap DI PRODUKSI:** baris catatan
  startup menyebut kunci dict (`_p['dilewati']`) yang sudah berubah nama ⇒ `KeyError`. Gagal-terbuka
  bekerja (pemanasannya sendiri berhasil, mesin tetap jalan), tapi **keterangannya hilang** — dan
  itulah yang menyamarkan apakah perbaikan ini aktif. Ditutup secara STRUKTURAL: penyusunan kalimat
  dipindah ke dalam modul (`ringkasan()`) sehingga kunci dict tak pernah bocor keluar, plus 2 penjaga
  (menjalankan baris itu · melarang mesin menyentuh kunci dict, dibaca dari pohon sintaks).
  Suite 1014 → **1026**, nol regresi. Nol migrasi DB, nol perubahan layar.
- **2026-08-14** — **BUG YANG KAMI TANAM SENDIRI DICABUT + DOKUMEN INI BERHENTI BERBOHONG DI 6 TITIK.**
  Dilaporkan owner dari keluhan tenant: *"sebelumnya sudah berjalan baik, 3 kali gagal langsung kena
  rem; tapi setelah anda bug fixing, malah timbul bug baru."* Benar seluruhnya.
  **(A) §8k — rem yang dilumpuhkan.** Perbaikan 12-Agu mengecualikan kelas `SELF_HEALING` dari
  hitungan kegagalan. Rem itu mengerjakan DUA hal (menghentikan channel *dan* menghentikan
  percobaan); hanya yang pertama yang diincar, yang kedua ikut hilang tanpa pengganti. Akibat
  terukur: Thetangga 30 kegagalan/8 menit · BISIK 23/11 menit · ±257 kabar gagal per jam · 50 dari
  53 kegagalan `rate_limit` sepanjang umur aplikasi terjadi di dua hari itu · yang menghentikannya
  **tenant mematikan channelnya sendiri**. **Dicabut** — setiap kegagalan dihitung kembali. Diukur
  sebelum dikirim: **nol** channel aktif yang langsung direm.
  **(B) Enam ketidaksesuaian dokumen-vs-kenyataan diperbaiki.** §1 & §3 menjanjikan *"toleransi
  normal → rem di kegagalan ke-3"* untuk perilaku yang sudah tidak ada (sembuh sendiri begitu (A)
  dicabut) · §8j memuat DUA jawaban berlawanan tentang Cloudflare `3036` berjarak 16 baris
  (dijalankan: `rate_limit`, jadi catatan "masih terbuka"-nya dicabut) · tabel §9a **terbelah**
  karena catatan 12-Agu disisipkan antara baris judul & pemisahnya · angka bukti §7 basi (9 & 12 →
  nyata 20 & 35) · bukti produksi masih menyebut `rate_limit` 3× (nyata 53×) · celah baru §8k
  belum tercatat.
  **(C) Tiga penjaga baru — menyerang sebab kebocorannya, bukan gejalanya.**
  `TestSikapDokumenAdalahPerilakuNyata` (kolom "Sikap" §1 dibandingkan dengan PERILAKU mesin, bukan
  dengan teks) · `TestStrukturTabelDokumenUtuh` (tabel terbelah = merah) ·
  `TestAngkaBuktiUjiTidakBasi` (angka §7 dihitung dari suite, bukan diketik) ·
  `tests/test_rem_tak_boleh_lumpuh.py` (berapa percobaan · berapa kabar · apakah mesin berhenti
  sendiri).
  **Kenapa penjaganya berbentuk PERILAKU:** seluruh uji rem yang ada memeriksa `streak == 3`, dan
  angka itu MEMANG benar sepanjang insiden — 880 uji hijau sementara tenant dibanjiri. Uji pada
  angka perantara tidak bisa menangkap kerusakan yang terjadi pada akibatnya.
  **Bukti merah lebih dulu:** pengecualian 12-Agu dihidupkan kembali → **14 uji gagal**; dua penjaga
  dokumen baru merah pada dokumen apa adanya (tabel terbelah + angka basi), hijau setelah dibetulkan.
  **(D) TIGA CELAH §8k SISANYA IKUT DITUTUP di hari yang sama** (butir 2·3·4), keduanya dibuat
  GENERIK atas ketetapan owner *"AI model & vendor akan terus bertambah"* — dan prinsip itu
  diterapkan pada **JALUR** juga, bukan hanya vendor:
  • **migr 0198** — menyalakan channel menutup periode kegagalan + `updated_at` selalu tercatat.
  Dipasang sebagai **trigger DB**, bukan 2 baris di layar: layar hanya menutup jalur yang ada hari
  ini, dan justru begitulah cacat ini lahir (0197 menutup 3 jalur, melewatkan saklar aktif). Tidak
  menyentuh `production_paused` ⇒ [B25] utuh. Bukti runtime pada baris NYATA di dalam transaksi
  yang **dibatalkan** ⇒ nol data tenant berubah. Efek sampingnya: dua channel dengan hitungan 12
  sembuh SENDIRI saat tenantnya menyalakannya ⇒ pemulihan data manual jadi tidak perlu.
  • **`seed` hanya ke model yang skemanya menyatakan menerimanya** (default = TIDAK kirim ⇒ vendor
  baru otomatis aman) + **jaring lintas-vendor** yang mengakui penolakan parameter sebagai salah
  KITA. Menghentikan ±$0,068/2 hari uang tenant terbakar, dan menghentikan tenant disalahkan
  untuk permintaan kita yang cacat.
  **Yang SENGAJA masih terbuka** (§8k butir 1, menunggu ketok owner): **jeda sementara** untuk sebab
  yang pulih sendiri — satu-satunya yang memilih angka & kebijakan baru, jadi bukan keputusan Claude.
- **2026-08-13** — **JALUR TERBIT & ALARM PENYIMPANAN: tiga kegagalan senyap ditutup** (ketok owner
  "kerjakan A, B, C sampai tuntas"). Ketiganya berakar pada hal yang sama: **keadaan penting disimpan
  di ingatan proses, sementara proses itu bisa mati kapan saja.**
  **(A) Kabar "penyimpanan PULIH" yang tak pernah datang.** Akun penyimpanan diblokir penyedia
  04:24–10:21 (tagihan). Alarm bahaya terkirim 04:54 ✅; penyimpanan pulih, kabar pulih **tak pernah
  terkirim** — terukur: hari itu hanya 2 notifikasi keluar dari mesin. Sebabnya hitungan gagal hidup
  di ingatan proses, dan ingatan itu terhapus DUA kali (mesin mati mendadak 07:54, restart 10:21) →
  saat pulih, hitungannya < ambang → mesin menyimpulkan "tak pernah ada masalah". Alarm bahaya
  selamat dari restart, kabar pulih tidak. Kini status alarm hidup di `system_state` (pola yang sudah
  terbukti di alarm drift durasi, ketok owner 16-Jul). Penanda "sedang alarm" dinyalakan **hanya bila
  alarm benar-benar terkirim** → tak pernah mengabarkan akhir dari sesuatu yang tak punya awal.
  **(B) Pesan gagal-terbit berhenti melempar kode** → §4b + kecualian §9. Tenant dapat MAKNA, kami
  dapat KODE.
  **(C) Stok yang nyangkut di "sedang diterbitkan" akhirnya punya penyapu.** Korban nyata: 12-Agu
  19:00 mesin mati 7 detik setelah unggahan selesai; video `xa3Rbi-SbXM` **hidup, PUBLIK, 1.024
  penonton** di channel tenant BERBAYAR, sementara bagi sistem kita ia tidak pernah ada — `videos`
  tanpa barisnya, tautan YouTube kosong, tenant tak dikabari, aset kekal karena status itu justru
  DILINDUNGI penyapu-yatim, dan mesin pembelajaran tak pernah melihatnya. Penyapu baru memutuskan
  dari **jejak unggahan**, bukan tebakan: nomor YouTube ada → pembukuan dituntaskan · unggahan belum
  pernah dimulai → kembali ke stok · **unggahan sudah dimulai tapi nomor tak tercatat → TIDAK
  diterbitkan ulang, dilaporkan ke owner** (rencana pertama hendak menerbitkan ulang di keadaan ini —
  itu berisiko VIDEO KEMBAR, karena unggahan bertahap punya celah sempit di mana YouTube sudah
  menerima tapi kita belum tahu nomornya).
  **Kecelakaan yang ikut diperbaiki:** uji pertama versi ini **menulis ke baris PRODUKSI** karena
  penyapu memakai `inventory.mark_published()` yang membuat klien Supabase-nya sendiri dari env
  (baris inv=231 berubah status dari sebuah uji lokal). Penyapu kini memakai `sb` yang diberikan —
  seragam dengan seluruh berkas itu — dan berkas uji memasang pagar yang **menolak sambungan
  sungguhan**, sehingga kecelakaan senyap itu berubah menjadi kegagalan uji yang lantang.
  **Bukti:** 41 uji baru (23 + 18), keduanya dibuktikan **merah lebih dulu** dengan sabotase sengaja
  (galat mentah dikembalikan ke pesan tenant → merah; penyapu dikembalikan memakai sambungan sendiri
  → merah). Suite 907 → **935**. Nol migrasi DB.
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
