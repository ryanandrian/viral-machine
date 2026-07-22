# MANAJEMEN ERROR AI — ARSITEKTUR (SINGLE SOURCE OF TRUTH)

> **Status:** ✅ **LIVE PRODUKSI 2026-07-18 01:04** (izin owner "deploy BE", commit `99b1c32`, mv-worker/webhook active, health 200; verifikasi: nol error import/ErrorClass, 3 thread produksi start bersih). Taksonomi + adapter EL-direct terverifikasi + circuit-breaker semantik + persistensi migr 0170.
> **Fungsi dokumen:** peta + tata-kelola. **Kode = otoritatif; dokumen = peta + bukti.** Kontradiksi → kode menang; perbarui dokumen SAAT ITU.
> **Aturan emas:** sebuah kode error masuk registry **HANYA bila ada bukti sampel nyata** (log kita / respons asli). Belum terbukti → `UNKNOWN` = aman (retryable, perilaku lama). **Update kode + dokumen dalam commit yang SAMA** (anti-drift, disiplin CLAUDE.md §3.7).

---

## §1 Prinsip & taksonomi
Sistem berpikir dalam **MAKNA** error, bukan teks/HTTP-status mentah. Dua dimensi ORTOGONAL pada `PipelineError` (`src/exceptions.py`):
- **`category`** = DI MANA gagal (tts/llm/visual/render/publish) — sudah ada.
- **`error_class`** (`ErrorClass`) = KENAPA gagal (makna) — BARU.

| ErrorClass | Arti | Sikap |
|---|---|---|
| `ACCOUNT_BILLING` | pembayaran/langganan gagal | **non-retryable → REM SEGERA** |
| `QUOTA_EXHAUSTED` | kredit/kuota habis | **non-retryable → REM SEGERA** |
| `AUTH_INVALID` | kunci/koneksi ditolak PERMANEN (mis. OAuth `invalid_grant`) | **non-retryable → REM SEGERA** |
| `RATE_LIMIT` | throttle sesaat (429) | retryable → toleransi normal |
| `TRANSIENT` | jaringan/5xx/timeout | retryable → toleransi normal |
| `UNKNOWN` | belum dikenali | retryable (DEFAULT AMAN) |

**`FAST_FAIL = {ACCOUNT_BILLING, QUOTA_EXHAUSTED, AUTH_INVALID}`** (`src/exceptions.py`). Awal (2026-07-17): "kredit habis / masalah pembayaran". **Diperluas 2026-07-18** (ketok owner "rem segera, jangan bakar duit tenant", [B11] 3.2): `AUTH_INVALID` — koneksi YouTube putus permanen mustahil sembuh dgn diulang. Menambah/menghapus kelas = ubah SATU set ini.

## §2 Transport-keyed (bukan merek model)
Klasifikasi menempel pada **transport yang menerima error**, bukan merek model. "Suara ElevenLabs" = model; "API EL" & "API fal" = dua transport → dua kontrak error.
- **EL-direct** → adapter `elevenlabs` → kode native EL → akun ElevenLabs.
- **EL-via-fal** (kelak) → adapter **fal** → amplop error fal → akun fal. **BUKAN** di adapter EL-direct.
- Agregator (fal) = **satu titik billing**: bila fal habis, SEMUA model via fal (TTS+image+video) gagal bersama.

## §3 Aliran error ujung-ke-ujung (dengan anchor `file:baris` — grep ulang bila bergeser)
1. Adapter tangkap error provider → `_classify_el_error()` (`src/providers/tts/elevenlabs.py`) → `raise TTSError(..., error_class=, human_message=)`.
2. `tts_engine.generate()` **menelan** error TTS (return `"",[]`) TAPI menyimpan `last_error/last_error_class/last_human_error` (`src/production/tts_engine.py` except).
3. `pipeline` STEP 5 lihat audio kosong → `raise TTSError(last_human_error or last_error, error_class=last_error_class, human_message=...)` (`src/orchestrator/pipeline.py:~275`).
4. `pipeline` except → `result["error_class"]` + `result["human_error"]` (`pipeline.py:~636`).
5. `producer` catat ke `production_runs.error_class` + `error_message`=pesan manusiawi (`src/orchestrator/producer.py` `_record_production_run` + 2 insert direct). **Reorder:** catat-run SEBELUM `mark_failed` (fast-fail deterministik).
6. Circuit-breaker: `inventory.latest_failure(cid)` → bila `error_class ∈ FAST_FAIL` **rem di streak≥1**; else streak≥`PRODUCER_FAIL_STREAK_STOP`(3) (`producer.py` plan_and_submit).
7. **PESAN SERAGAM SEMUA PERMUKAAN (SSOT tampilan — ditegakkan 2026-07-22):** teks yang tampil ke manusia = **`human_error or error`** yang IDENTIK di setiap permukaan, tak boleh ada jalur bercerita sendiri: (a) `production_runs.error_message` — KETIGA jalur producer: scheduled `:206`, direct-publish `:340`, direct-test `:435`; (b) tabel `videos` (`pipeline` crash-path `write_failed_run`, var `human_err`); (c) Telegram `notify_failure` (var `human_err` sama); (d) FE drawer Runs + halaman detail (baca `production_runs.error_message`). ⚠️ Circuit-break `notify_circuit_break` juga pakai `error_message`. **Sebelum 22-Jul MENYIMPANG:** direct-test `:432` & `notify_failure` mengirim `str(e)` mentah → Telegram/DB bisa beda dari layar (celah tampak hanya utk error TERKLASIFIKASI; unknown kebetulan sama). Kini kanonik. `notify_publish_fail` (jalur upload YouTube gagal, `_yt_err`) = konteks berbeda, belum diseragamkan (dicatat jujur — bukan crash produksi).

## §4 REGISTRY per-adapter (titik "inject" — tabel HIDUP)
| Provider/Transport | Kode mentah | → ErrorClass | Status | Bukti |
|---|---|---|---|---|
| **ElevenLabs (direct)** | `payment_issue`, `payment_required` | ACCOUNT_BILLING | ✅ AKTIF | worker.log 2026-07-17 (RAD) |
| **ElevenLabs (direct)** | `quota_exceeded` | QUOTA_EXHAUSTED | ✅ AKTIF | worker.log 2026-06-16 |
| **Google OAuth (YouTube)** | `invalid_grant` | AUTH_INVALID | ✅ AKTIF | OAuth2 RFC 6749 (refresh token dicabut/kedaluwarsa); klasifikasi di `youtube_publisher._get_credentials` + `channel_analytics._load_credentials` → `mark_youtube_account_invalid` (status='invalid' → gerbang `channel_missing` menutup → produksi berhenti). RefreshError LAIN = transien (tak ditandai). [B11] 3.2 2026-07-18 |
| **OpenAI-compatible (LLM: OpenAI/Groq/dst via `openai_chat`)** | `invalid_api_key` (401) | AUTH_INVALID | ✅ AKTIF | worker.log 2026-07-20 (insiden MVT; classifier `_classify_openai_compat_error` adapters.py + rem-cepat no-retry di niche_selector + propagasi last_* → production_runs.error_class; uji 6/6) |
| **OpenAI-compatible (LLM)** | `model_not_found` (404) | **MODEL_UNAVAILABLE (kelas BARU 20-Jul, masuk FAST_FAIL)** | ✅ AKTIF | worker.log 2026-07-20 (MVT llama-4-scout — model dipensiunkan vendor, terbukti via fasilitas Uji admin dgn model_id resmi; pesan manusiawi "pilih model lain di setting channel") |
| **OpenAI (LLM/image)** | `insufficient_quota` · `exceeded your current quota` | QUOTA_EXHAUSTED | ✅ AKTIF (22-Jul) | worker.log 09-Jul + production_runs 21-Jul (riandipantria) — uji 6/6 |
| **Google Gemini (AI Studio, adapter `openai_chat`)** | `is no longer available` (404 model dipensiunkan) | MODEL_UNAVAILABLE | ✅ AKTIF (22-Jul) | production_runs 21/22-Jul (riandipantria `gemini-2.5-flash` ditutup Google utk user baru). ⚠️ 429 rate-limit (bukan quota) TETAP UNKNOWN/retryable — token quota spesifik, jangan salah-rem |
| **OpenAI** | `billing_hard_limit_reached` | ACCOUNT_BILLING | ⏳ dokumentasi, belum ada sampel | — |
| **fal (agregator)** | ? | ? | ⏳ menunggu sampel error nyata | adapter tangkap `status_code`+body (`ai_video.py:219`) |
| **edge_tts** | — gratis, tak ada billing | — | n/a | — |
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

## §7 Verifikasi (bukti pembangunan 2026-07-18)
Uji `test_errmgmt.py` **13/13 LULUS** vs DB live: classifier EL 2 string NYATA (payment_issue→BILLING, quota_exceeded→QUOTA) + structured-body + error-asing→UNKNOWN · taksonomi/FAST_FAIL benar · persistensi `error_class` end-to-end (`_record_production_run`→`latest_failure`) · keputusan hard=rem-di-1 · **regresi: UNKNOWN tetap streak-3, success memutus streak** · migr 0170 applied (guard identitas) · py_compile + import worker bersih · data uji 0 sisa. **FE tak tersentuh.**

## §8 CHANGELOG
- **2026-07-22** — **PENEGAKAN SSOT TAMPILAN (koreksi doc-drift + fix kode).** Owner menohok benar: "buat apa dokumen SSOT kalau tak ditegakkan?". Ditemukan (bukti kode): satu kegagalan tercatat di 3 tempat dgn cara BEDA — tabel `videos` & Telegram `notify_failure` pakai `str(e)` mentah, `production_runs` (via producer) pakai pesan-manusiawi; DAN di dalam producer sendiri jalur direct-test (`:432`) MELEWATI `human_error` (blok scheduled `:206` & direct-publish `:340` sudah benar). Klaim changelog 20-Jul "pesan manusiawi di layar/Telegram" karena itu = **over-claim** (belum benar utk notify_failure). **Fix (terkurung, low-risk):** (1) `pipeline` crash-path — satu var kanonik `human_err = human_error or str(e)` dipakai bersama `write_failed_run` (videos) + `notify_failure` (Telegram); (2) producer direct-test `:435` +`human_error` di depan chain (samakan 2 jalur lain). Semua UNKNOWN → `str(e)` = perilaku lama (nol regresi terbukti); TERKLASIFIKASI → pesan ramah seragam di SEMUA permukaan (§3 langkah 7). Uji: py_compile 2 file · verifikasi statis 4 jalur konsisten · uji logika unknown-identik/terklasifikasi-seragam. Bukti runtime pamungkas (run gagal terklasifikasi → Telegram=DB=layar identik) menyusul pasca-deploy. **Classifier DITUNTASKAN se-sesi ini (owner: "jangan sisakan utk sesi besok"):** Gemini `is no longer available`→MODEL_UNAVAILABLE + OpenAI quota (`insufficient_quota` · `exceeded your current quota`)→QUOTA_EXHAUSTED, ditambah ke `_OPENAI_COMPAT_ERROR_MAP` (Gemini pakai adapter `openai_chat` → lewat classifier yg sama; format 404-nya beda dari Groq shg dulu lolos jadi unknown). Bukti sampel byte-penuh dari production_runs riandipantria. Uji 6/6: 2 sampel nyata + 2 regresi (invalid_api_key/model_not_found) + **kasus kritis 429 rate-limit→UNKNOWN (jangan salah-rem)** + error asing→UNKNOWN. §4 registry di-update ✅. Sisa jujur: `notify_publish_fail` (jalur upload YouTube, bukan crash produksi) belum diseragamkan — dicatat, bukan disembunyikan.
- **2026-07-20** — Transport **OpenAI-compatible** naik ✅ (ketok owner "kerjakan tawaran 1"; sampel nyata insiden MVT): `invalid_api_key`→AUTH_INVALID · `model_not_found`→**MODEL_UNAVAILABLE (kelas baru, masuk FAST_FAIL)**. Classifier `_classify_openai_compat_error` di adapters.py (pola _classify_el_error; kode lain→UNKNOWN) + **rem cepat di loop retry niche_selector** (FAST_FAIL = stop percobaan-1; dulu 401 di-retry 3×) + propagasi `last_error_class/last_human_error` (pola last_* TTS) → pipeline raise ber-kelas → `production_runs.error_class` terisi benar (dulu 'unknown') + pesan manusiawi di layar/Telegram. Uji permanen `tests/test_openai_compat_error_classes.py` **6/6** (2 sampel verbatim + regresi UNKNOWN + taksonomi + wiring adapter + rem-1-percobaan) · suite 57/57.
- **2026-07-18 (2)** — **[B11] 3.2** menambah transport **Google OAuth** ke registry: `invalid_grant` → `AUTH_INVALID` (masuk FAST_FAIL). Koneksi YouTube putus permanen kini GAGAL JUJUR (bukan senyap): ditandai `status='invalid'` (helper `mark_youtube_account_invalid`) → gerbang `channel_missing` menutup → produksi channel berhenti seketika + notif tenant sekali + badge FE + publish menahan video (bukan "akan diulang" menyesatkan). RefreshError non-invalid_grant tetap transien (regresi dijaga uji `tests/test_youtube_auth_invalid.py` 10/10). ✅ **DEPLOYED PRODUKSI 2026-07-18 12:07 (`dd8fcdc`, izin owner, health=200).**
- **2026-07-18** — Lahir + kerangka dibangun + **DEPLOYED PRODUKSI 01:04 (`99b1c32`, izin owner)**. Pemicu: insiden RAD 2026-07-17 (langganan EL gagal-bayar → 3× gagal bakar biaya LLM sebelum rem). Owner minta manajemen error world-class extensible (bukan tambalan). Isi awal registry: EL-direct (✅), OpenAI (⏳). Verifikasi produksi: nol error import, 3 thread produksi start bersih.
