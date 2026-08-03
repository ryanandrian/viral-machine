# MANAJEMEN ERROR AI — ARSITEKTUR (SINGLE SOURCE OF TRUTH)

> **🔍 AUDIT DOKUMEN-vs-KODE 2026-08-03 — 4 drift ditemukan & diperbaiki (§11).** Dua di antaranya membuat
> dokumen ini menyatakan **perilaku yang salah** (kelas hilang dari tabel · daftar FAST_FAIL kurang satu),
> satu menyandarkan bukti pada berkas uji yang **tidak ada**. **Kini dijaga MESIN:**
> `tests/test_ssot_error_mgmt.py` membandingkan dokumen ini dengan kode setiap kali suite dijalankan —
> bergeser tanpa pasangannya = MERAH (§10). Registry §4 diperiksa baris demi baris: semua klaim ✅ terbukti.
> **Baca §8 (celah terbuka) & §9 (kontrak tampilan per-kelas) sebelum menyentuh UI kegagalan produksi.**

> **Status:** ✅ **LIVE PRODUKSI 2026-07-18 01:04** (izin owner "deploy BE", commit `99b1c32`, mv-worker/webhook active, health 200; verifikasi: nol error import/ErrorClass, 3 thread produksi start bersih). Taksonomi + adapter EL-direct terverifikasi + circuit-breaker semantik + persistensi migr 0170.
> **Fungsi dokumen:** peta + tata-kelola. **Kode = otoritatif; dokumen = peta + bukti.** Kontradiksi → kode menang; perbarui dokumen SAAT ITU.
> **Aturan emas:** sebuah kode error masuk registry **HANYA bila ada bukti sampel nyata** (log kita / respons asli). Belum terbukti → `UNKNOWN` = aman (retryable, perilaku lama). **Update kode + dokumen dalam commit yang SAMA** (anti-drift, disiplin CLAUDE.md §3.7).

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

1. Adapter tangkap error provider → `_classify_el_error()` (`src/providers/tts/elevenlabs.py`) → `raise TTSError(..., error_class=, human_message=)`.
2. `tts_engine.generate()` **menelan** error TTS (return `"",[]`) TAPI menyimpan `last_error/last_error_class/last_human_error` (`src/production/tts_engine.py` except).
3. `pipeline` STEP 5 lihat audio kosong → `raise TTSError(last_human_error or last_error, error_class=last_error_class, human_message=...)` (`src/orchestrator/pipeline.py`, cari `raise TTSError`).
4. `pipeline` except → `result["error_class"]` + `result["human_error"]` (`pipeline.py`, cari `result["error_class"]`).
5. `producer` catat ke `production_runs.error_class` + `error_message`=pesan manusiawi (`src/orchestrator/producer.py` `_record_production_run` + 2 insert direct — cari `"error_message"`). **Reorder:** catat-run SEBELUM `mark_failed` (fast-fail deterministik).
6. Circuit-breaker: `inventory.latest_failure(cid)` → bila `error_class ∈ FAST_FAIL` **rem di streak≥1**; else streak≥`PRODUCER_FAIL_STREAK_STOP`(3) (`producer.py` plan_and_submit).
7. **PESAN SERAGAM SEMUA PERMUKAAN (SSOT tampilan — ditegakkan 2026-07-22):** teks yang tampil ke manusia = **`human_error or error`** yang IDENTIK di setiap permukaan, tak boleh ada jalur bercerita sendiri: (a) `production_runs.error_message` — KETIGA jalur producer (`_record_production_run` scheduled · insert direct-publish · insert direct-test); (b) tabel `videos` (`pipeline` crash-path `write_failed_run`, var `human_err`); (c) Telegram `notify_failure` (var `human_err` sama); (d) FE drawer Runs + halaman detail (baca `production_runs.error_message`). ⚠️ Circuit-break `notify_circuit_break` juga pakai `error_message`. **Sebelum 22-Jul MENYIMPANG:** jalur direct-test & `notify_failure` mengirim `str(e)` mentah → Telegram/DB bisa beda dari layar (celah tampak hanya utk error TERKLASIFIKASI; unknown kebetulan sama). Kini kanonik. `notify_publish_fail` (jalur upload YouTube gagal, `_yt_err`) = konteks berbeda, belum diseragamkan (dicatat jujur — bukan crash produksi).

## §4 REGISTRY per-adapter (titik "inject" — tabel HIDUP)
| Provider/Transport | Kode mentah | → ErrorClass | Status | Bukti |
|---|---|---|---|---|
| **ElevenLabs (direct)** | `payment_issue`, `payment_required` | ACCOUNT_BILLING | ✅ AKTIF | worker.log 2026-07-17 (RAD) |
| **ElevenLabs (direct)** | `quota_exceeded` | QUOTA_EXHAUSTED | ✅ AKTIF | worker.log 2026-06-16 |
| **Google OAuth (YouTube)** | `invalid_grant` | AUTH_INVALID | ✅ AKTIF | OAuth2 RFC 6749 (refresh token dicabut/kedaluwarsa); klasifikasi di `youtube_publisher._get_credentials` + `channel_analytics._load_credentials` → `mark_youtube_account_invalid` (status='invalid' → gerbang `channel_missing` menutup → produksi berhenti). RefreshError LAIN = transien (tak ditandai). [B11] 3.2 2026-07-18 |
| **OpenAI-compatible (LLM: OpenAI/Groq/dst via `openai_chat`)** | `invalid_api_key` (401) | AUTH_INVALID | ✅ AKTIF | worker.log 2026-07-20 (insiden MVT; classifier `_classify_openai_compat_error` adapters.py + rem-cepat no-retry di niche_selector + propagasi last_* → production_runs.error_class; uji 6/6) |
| **OpenAI-compatible (LLM)** | `model_not_found` (404) | **MODEL_UNAVAILABLE (kelas BARU 20-Jul, masuk FAST_FAIL)** | ✅ AKTIF | worker.log 2026-07-20 (MVT llama-4-scout — model dipensiunkan vendor, terbukti via fasilitas Uji admin dgn model_id resmi; pesan manusiawi "pilih model lain di setting channel") |
| **OpenAI (LLM/image)** | `insufficient_quota` · `exceeded your current quota` | QUOTA_EXHAUSTED | ✅ AKTIF (22-Jul) | worker.log 09-Jul + production_runs 21-Jul (riandipantria) — uji 6/6 |
| **Google Gemini (AI Studio, adapter `openai_chat`)** | `is no longer available` (404 model dipensiunkan) | MODEL_UNAVAILABLE | ✅ AKTIF (22-Jul) | production_runs 21/22-Jul (riandipantria `gemini-2.5-flash` ditutup Google utk user baru) |
| **SEMUA transport OpenAI-compatible** | **HTTP 429 apa pun** (status SDK, else `Error code: 429`) | RATE_LIMIT | ✅ AKTIF (2026-08-01) | Groq llama-3.3 TPD: "Rate limit reached ... tokens per day (TPD): Limit 100000, Used 97156 ... try again in 35m51s" (uji rantai penuh 01-Agu). **Aturan LEVEL-TRANSPORT, bukan kalimat vendor** (§2): katalog model akan terus bertambah dan aturan ber-kalimat diam-diam gagal pada vendor berikutnya. §1 sendiri mendefinisikan RATE_LIMIT = "throttle sesaat (429)". Pesan manusiawi punya DUA varian: batas HARIAN (bila pesan menyebut per-day/daily/harian) vs sesaat — tindakan tenantnya berbeda. TIDAK masuk FAST_FAIL → channel tidak direm (kekhawatiran lama "salah-rem" berlaku utk QUOTA_EXHAUSTED, bukan RATE_LIMIT) |
| **OpenAI** | `billing_hard_limit_reached` | ACCOUNT_BILLING | ⏳ dokumentasi, belum ada sampel | — |
| **fal (agregator)** | ? | ? | ⏳ menunggu sampel error nyata | adapter tangkap `status_code`+body (`src/providers/visual/ai_video.py`) |
| **edge_tts** | — gratis, tak ada billing | — | n/a | — |
| **SEMUA penyedia suara** | audio jauh lebih pendek dari ramalan (`tts_potong_ambang_pct`) | TRANSIENT | ✅ AKTIF (2026-08-01) | narasi TERPUTUS; laju terukur 1 dari 73 render. Berlaku per potongan pada naskah panjang |
| **SEMUA penyedia suara** | tak menyelesaikan permintaan dalam batas waktu | TRANSIENT | ✅ AKTIF (2026-08-01) | direproduksi 01-Agu: render Edge menggantung belasan menit; tanpa batas waktu satu utas pekerja mati selamanya tanpa error |
| **edge_tts** | penanda kalimat vendor mencakup < `tts_cakupan_min_pct` naskah | TRANSIENT | ✅ AKTIF (2026-08-01) | sintesis berhenti di tengah tanpa error; teks 581 huruf → audio 27,0 dtk vs 40,8 dtk saat diulang |
| **Anthropic (LLM)** | ? | ? | ⏳ menunggu sampel | — |

> Baris ⏳ = belum di-fast-fail → jatuh ke `UNKNOWN`/streak-3 (aman). Naikkan ke ✅ hanya setelah `classify_error()` adapter diisi + diuji + bukti sampel dicatat.

## §5 Checklist onboarding provider baru (5 langkah)
1. **Tangkap sampel error NYATA** (dari worker.log atau reproduksi) — simpan byte respons (status + body).
2. **Catat** kode + message di §4 (kolom Bukti = tanggal/lokasi log).
3. **Petakan** kode → ErrorClass (hanya yang jelas billing/quota/auth; ragu → biarkan UNKNOWN).
4. **Implement** `classify_error()` di adapter transport-nya (pola `_classify_el_error`), raise dgn `error_class`+`human_message`. Bila error ditelan lapisan atas, pastikan propagasi (pola `last_*` tts_engine).
5. **Uji** (unit classifier dgn string sampel + persistensi + keputusan) → set status ✅ + commit kode & dokumen BERSAMAAN.

## §6 Tata-kelola (anti-drift, anti-asumsi)
- HANYA kode ber-bukti-sampel yang dipetakan; sisanya `UNKNOWN`.
- Kode = otoritatif; dokumen = peta + bukti; sinkron dalam commit yang sama.
- Circuit-breaker TIDAK boleh string-sniffing — hanya baca `error_class` terstruktur.
- Menambah/menghapus kelas fast-fail = ubah `FAST_FAIL` (`src/exceptions.py`) saja.

## §7 Verifikasi — berkas uji NYATA (diperbaiki 2026-08-03)
> ⚠️ **KOREKSI.** Versi lama mengklaim bukti dari `tests/test_errmgmt.py` **13/13** — berkas itu
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

### 8b. `notify_publish_fail` belum diseragamkan
Jalur upload YouTube gagal (`_yt_err`) — konteks berbeda dari crash produksi. Tercatat sejak 22-Jul,
belum ditangani. Bukan kegagalan produksi, jadi tak masuk aliran §3.

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

⚠️ **Jangan tertukar:** `direct_jobs.error` kini bisa berisi **kode gerbang** `GATE:*` (penolakan
langganan/jatah uji — [B24]), yang **bukan** `ErrorClass` dan bukan kegagalan AI. Penerjemahnya
terpisah (`components/gate-message.tsx`). Dokumen ini hanya mengatur kegagalan AI.

## §10 PENJAGA ANTI-DRIFT (supaya dokumen ini TETAP SSOT)

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
