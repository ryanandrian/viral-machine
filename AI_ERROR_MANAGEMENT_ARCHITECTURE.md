# MANAJEMEN ERROR AI — ARSITEKTUR (SINGLE SOURCE OF TRUTH)

> **Status:** 🟢 KERANGKA LIVE-READY (dibangun 2026-07-18) — taksonomi + adapter EL-direct terverifikasi + circuit-breaker semantik + persistensi. ⛔ **BELUM DEPLOY** (menunggu izin owner).
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
| `AUTH_INVALID` | kunci salah/diblokir | non-retryable (BELUM di fast-fail) |
| `RATE_LIMIT` | throttle sesaat (429) | retryable → toleransi normal |
| `TRANSIENT` | jaringan/5xx/timeout | retryable → toleransi normal |
| `UNKNOWN` | belum dikenali | retryable (DEFAULT AMAN) |

**`FAST_FAIL = {ACCOUNT_BILLING, QUOTA_EXHAUSTED}`** (`src/exceptions.py`) — persis lingkup owner 2026-07-17 ("kredit habis / masalah pembayaran"). Menambah kelas ke fast-fail = ubah SATU set ini.

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

## §4 REGISTRY per-adapter (titik "inject" — tabel HIDUP)
| Provider/Transport | Kode mentah | → ErrorClass | Status | Bukti |
|---|---|---|---|---|
| **ElevenLabs (direct)** | `payment_issue`, `payment_required` | ACCOUNT_BILLING | ✅ AKTIF | worker.log 2026-07-17 (RAD) |
| **ElevenLabs (direct)** | `quota_exceeded` | QUOTA_EXHAUSTED | ✅ AKTIF | worker.log 2026-06-16 |
| **OpenAI (LLM/image)** | `insufficient_quota` | QUOTA_EXHAUSTED | ⏳ TERVERIFIKASI, belum diimplement | worker.log 2026-07-09 (niche_selector) |
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
- **2026-07-18** — Lahir + kerangka dibangun. Pemicu: insiden RAD 2026-07-17 (langganan EL gagal-bayar → 3× gagal bakar biaya LLM sebelum rem). Owner minta manajemen error world-class extensible (bukan tambalan). Isi awal registry: EL-direct (✅), OpenAI (⏳). ⛔ belum deploy.
