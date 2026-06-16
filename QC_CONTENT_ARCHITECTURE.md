# QC & Content-Quality Architecture — MesinViral v2

> **Living document.** Tujuan: arsitektur khusus untuk *quality control* + *self-improvement* yang **terus dievaluasi & di-improve** sampai ideal. Cakupan: **dari ScriptAnalyzer → seluruh tahap produksi → file hasil (pra-submit)** + **loop self-analyzer/self-improvement** (janji landing page: "robot pintar, makin pintar tiap hari").
>
> Status LIVE per-fase = `PROGRESS.md`. Pondasi multi-format = `MULTI_FORMAT_STUDIO.md`. Prinsip: [[feedback_no_hardcode]] · [[feedback_analysis_discipline]].
>
> **Aturan dokumen ini:** setiap perubahan QC/quality WAJIB lewat sini dulu (propose → approve → implement). Jangan ubah ambang QC di kode tanpa update dokumen ini.

---

## 0. Prinsip dasar (kontrak arsitektur)

1. **QC ≠ penilaian konten.** Kualitas konten (hook, retensi, CTA) dinilai **di hulu** oleh `ScriptAnalyzer` (ambang ≥80). QC pra-submit hanya menjawab: *"apakah FILE hasil render utuh, sesuai NIAT produksi, dan sah untuk platform?"* — bukan "apakah kontennya bagus".
2. **Relatif, bukan absolut.** Tidak ada angka ajaib global (mis. "≥45s"). Ambang diturunkan dari **Duration Preset** + **Format Profile** tenant (8/15/30/45/60/75/90s). Floor absolut = anti-pattern yang membuang video valid + biaya render.
3. **Config-driven, no-hardcode.** Semua ambang dari config/DB/env, dapat ditambah super-admin. Tidak ada nama provider/angka tertanam di pesan error.
4. **Fail-soft yang jujur.** Kegagalan komponen (mis. TTS) → fallback yang dicatat, bukan diam-diam. QC-fail → video TIDAK dibuang membabi-buta; lihat §5 (kebijakan retry/quarantine).
5. **Self-improving.** Output nyata (analytics) harus mengalir balik menaikkan kualitas generasi berikutnya — terukur, bukan klaim.

---

## 1. Rantai kualitas SAAT INI (kondisi nyata, dengan rujukan kode)

Pipeline `src/orchestrator/pipeline.py` (7 step) dengan gate kualitas di beberapa titik:

| # | Tahap | Gate kualitas saat ini | File |
|---|---|---|---|
| 1 | Trend scan | — (kumpul sinyal) | `intelligence/trend_radar.py` |
| 2 | Niche/topic select | **insights-driven** (smart focus dari grade) + dedup topik 30d | `intelligence/niche_selector.py` |
| 3 | **Script gen + ANALISIS** | **`ScriptAnalyzer` skor 6-dimensi, ambang ≥80, retry s/d 3× dgn feedback** | `intelligence/script_engine.py`, `script_analyzer.py` |
| 4 | Hook optimize | generate N hook → skor → pilih winner; inject *historical top hooks* | `intelligence/hook_optimizer.py` |
| 5 | TTS | chain config-driven primary→fallback (fail-soft) | `production/tts_engine.py` |
| 6 | Visual assembly | N clip (saat ini **hardcode 6**), hook-frame | `production/visual_assembler.py` |
| 7 | Render | xfade + caption (karaoke ASS) + music ducking | `production/video_renderer.py` |
| 7.5 | **Pre-publish QC** | **integritas file (size/durasi/clip_count)** — lihat §2 | `pipeline.py::_pre_publish_qc` |

### 1a. ScriptAnalyzer — gate kualitas konten utama (HULU)
`VIRAL_DIMENSIONS` berbobot (`script_analyzer.py`):
- `hook_power` 25% · `curiosity_gap` 20% · `retention_arc` 20% · `emotional_peak` 20% · `information_density` 10% · `cta_strength` 5%
- Ambang lulus **80/100**; di bawah → retry s/d 3× dengan **feedback per-dimensi** (ScriptEngine `generate`). Kriteria `emotional_peak` diambil dari **niche profile (Supabase)** → sudah config-driven.
- **Inilah penilai "konten bagus".** QC pra-submit TIDAK boleh menduplikasi peran ini.

### 1b. Self-improvement loop yang SUDAH ADA (parsial)
Janji landing "self-improve tiap hari" **sudah berdiri sebagian**:
```
video nyata → video_analytics (views, watch_time, avg_view_pct, ctr, subscriber_gain)
   → PerformanceAnalyzer.compute_and_store()  [scripts/compute_insights.sh — cron harian]
   → channel_insights (grade, niche_weights, top_hooks[by CTR], avoid_patterns, content_types)
   → di-inject balik ke: NicheSelector (smart focus) · ScriptEngine (top hooks/content types) · HookOptimizer (historical hooks)
```
**Grade tiers** (`performance_analyzer.py`): `insufficient_data` (<5 video → estimasi AI murni) · `learning` (5–20 → inject top topics, belum adjust skor) · `peak` (50+ → ekstraksi pola hook + A/B ready). Sumber analytics: `analytics/channel_analytics.py` (YouTube Analytics) → `video_analytics`.

---

## 2. QC pra-submit SAAT INI + masalahnya

`_pre_publish_qc(video_path, duration_secs, clip_count)` — 4 cek:
1. size ≥ `QC_MIN_SIZE_MB` (default 5)
2. durasi ≥ `QC_MIN_DURATION` (**interim default 3** — sebelumnya 45 lalu sempat 20)
3. durasi ≤ `QC_MAX_DURATION` (default 180)
4. clip_count ≥ `QC_MIN_CLIPS` (default 6)

### Masalah arsitektur (yang sedang diperbaiki)
- 🔴 **Floor durasi absolut.** `<45s` (warisan v1) **memblokir preset 8s/15s** — `MULTI_FORMAT_STUDIO.md` baris 16 menandai ini "blocker", baris 53 minta **"QC relatif"**. Sempat saya turunkan ke 20s → **tetap memblokir 8/15s** (bug yang sama, angka beda). **Sekarang interim 3s** (hanya deteksi render kosong) sampai redesign §3.
- 🔴 **Mencampur integritas & konten.** "Durasi layak" itu penilaian konten, bukan integritas. Konten sudah di-gate ScriptAnalyzer.
- 🟡 **`clip_count` & `size` absolut.** 6-clip & 5MB benar untuk produksi 6-scene saat ini, tapi salah untuk preset ultra-short (2–3 beat, file lebih kecil — `MULTI_FORMAT_STUDIO.md` baris 53).
- 🟡 **QC-fail = buang total.** Video QC-fail dihapus + biaya render hangus, tanpa retry/quarantine cerdas.
- ✅ **(DIFIX) Cek integritas teknis** — kini `_pre_publish_qc` cek stream video+audio + aspect 9:16 (config `QC_REQUIRE_AUDIO`/`QC_ASPECT`/`QC_ASPECT_TOLERANCE`). Tervalidasi: render tanpa-audio & aspect salah ditolak; 9:16+audio lolos.

### Root cause DURASI (UPDATE 2026-06-16 — WPS 2.4 hardcode SUDAH ditangani; residual = mismatch provider)
**KOREKSI status:** WPS **bukan lagi** `2.4` hardcode. F1 (migr 0012) memasukkan **`format_wps` per-format/provider** dari `tts_profiles` (`script_engine.py:224` `WPS = format_wps if format_wps else 2.4`; 2.4 kini **fallback legacy** saja; sumber: `_eff_wps(format_profile, tts_provider)` `script_engine.py:511`). `tts_profiles.delivery_wps`: elevenlabs **1.8** · edge_tts/openai_tts **2.6**.
**Residual (tervalidasi test ryan 2026-06-16):** word-budget pakai `delivery_wps` provider **TERKONFIGURASI** (ryan=elevenlabs→1.8) tapi yang **me-RENDER = edge** (fallback krn ElevenLabs lapse, 2.6) → budget 60×1.8=108 kata, edge bicara 108/2.6 ≈ **43s** untuk target 60s → QC-fail. **Akar = WPS budget ≠ WPS provider AKTUAL (saat fallback).**
**Fix benar (2 jalur):** (a) WPS budget **ikut provider yang BENAR-BENAR me-render** (termasuk fallback) — bukan provider terkonfigurasi; ATAU (b) cegah fallback senyap (re-subscribe premium / §4b stop-on-fallback). **⛔ BUKAN dengan menurunkan preset** (preset 8/15/30/45/60/75/90 sudah rapat by-design; turunkan preset = output ikut lebih pendek, tetap meleset — keputusan owner 2026-06-16, no preset-hack).

---

## 3. ARSITEKTUR TARGET — QC v2 (spec-aware, relatif, berlapis)

QC menjadi **3 lapis**, semua ambang config-driven, ambang relatif diturunkan dari **Duration Preset × Format Profile** run tsb.

### Lapis 1 — Integritas render ("file-nya rusak/kosong tidak?")
- size > `QC_MIN_SIZE_KB` (kecil, anti file-kosong)
- ffprobe: **ada stream video DAN audio**
- durasi > floor integritas kecil (≈3s) — deteksi render terpotong-total
- **(baru)** codec/container valid, tak ada error decode

### Lapis 2 — Konformitas ke PRESET ("sesuai NIAT produksi?")
- `|durasi_aktual − target_preset| / target_preset ≤ QC_DURATION_TOLERANCE` (mis. 0.20)
  → preset 15s lolos ~12–18s; preset 60s lolos ~48–72s. **Tanpa floor absolut.**
- **aspect ratio == target** (9:16 untuk Shorts/Reels/TikTok)
- `clip_count == expected_beats(preset)` — semua visual beat preset berhasil (bukan hardcode 6)

### Lapis 3 — Batas platform ("sah untuk platform tujuan?")
- durasi ≤ `platform_max` per-platform (YouTube Shorts ≤180s, dst — config-driven)
- resolusi/fps sesuai spek platform

### Di LUAR QC (tetap di hulu)
- Kualitas naratif (hook/retensi/emosi/CTA) = **ScriptAnalyzer ≥80** (STEP 3). QC tak menilai ini.

### Sumber `target_preset` & `expected_beats`
Dari **Duration Preset tenant** — mekanisme di `MULTI_FORMAT_STUDIO.md §3` (8/15/30/45/60/75/90s; word_budget = detik×WPS; visual beat per preset). **Belum ada field-nya di `tenant_configs`** → QC v2 **mendarat bersama** field preset. Interim sekarang (§2) aman karena produksi aktif ~40s/6-clip.

### Kebijakan QC-fail (DIPUTUSKAN owner 2026-06-16)
- **Publish PRIVATE + advisory, BUKAN buang.** QC-fail → video tetap di-publish **private** (walau channel public) + status `qc_failed` + diagnosa tersimpan → tenant **lihat hasil** + **advisory** (alasan + rekomendasi config, lewat Telegram/FE) → **tenant putuskan** public/take-down. (Mengganti hapus-video `pipeline.py:317`.)
- Bila penyebab transient terukur (mis. fallback TTS bikin durasi meleset) → boleh **re-generate terarah** (kalibrasi WPS §2), bukan loop bakar-kredit.
- Catat **alasan terstruktur** (lapis+metrik) ke `pipeline_run_logs` untuk feedback ke §4.

---

## 4. Self-analyzer & self-improvement — roadmap (janji landing "makin pintar tiap hari")

Tujuan: tutup loop tidak hanya di **input** (script/hook dari analytics) tapi juga di **output** (kualitas file & performa nyata), terukur harian.

| Kapabilitas | Sekarang | Target |
|---|---|---|
| Insight dari performa nyata | ✅ `PerformanceAnalyzer` harian → grade/top_hooks/avoid | tambah sinyal: hook retention-curve, drop-off per-detik, thumbnail CTR |
| Inject insight ke generasi | ✅ NicheSelector/ScriptEngine/HookOptimizer | tambah: voice/pacing/visual-style per performa; per-preset learning |
| **QC sebagai sumber belajar** | 🔴 belum | feed alasan QC-fail → tuning otomatis word_budget/section_timing preset |
| **Self-critic pra-submit** | 🔴 belum | agen "tonton" hasil render (frame+caption sync, keterbacaan, brand-safety) sebelum publish |
| A/B & bandit | 🟡 "peak" A/B-ready | uji hook/thumbnail varian → pilih pemenang otomatis |
| Closed-loop akurasi durasi | 🟡 deviasi ±5–15%, one-shot | retry render terarah sampai durasi ≈ target preset (`MULTI_FORMAT_STUDIO.md` baris 18) |
| Transparansi ke tenant | 🔴 belum | dashboard "apa yang dipelajari robot minggu ini" (mendukung klaim landing) |

---

## 4b. Consent & Transparency untuk Fallback (TTS + Visual)

> **Prinsip (kuatkan §0.4): TIDAK ada degradasi kualitas yang SENYAP.** Setiap fallback ke provider cadangan = penurunan kualitas yang tenant **bayar** untuk dihindari (mis. suara premium ElevenLabs → edge_tts). Diam-diam menurunkannya = pelanggaran kepercayaan + kualitas.

### Kondisi nyata (tervalidasi 2026-06-13, vs kode)
- **TTS fallback SILENT** — `tts_engine.generate` hanya `logger.warning` saat fallback; **tak ada notifikasi tenant**. Field `tts_fallback_provider` ADA (default `edge_tts`).
- **Visual juga fallback** (bukan TTS saja): `visual_assembler` ai_image → **Pexels** → **black-screen**. Jadi kebijakan ini **umum**, bukan TTS-only.
- **Konsekuensi kualitas edge_tts nyata**: timestamp **aproksimasi** (interpolasi batas-kalimat) → sinkron caption ~80% vs ElevenLabs char-level ~98%. ⚠️ *Inkonsistensi kode: docstring edge_tts klaim ~95%, engine label ~80% — REKONSILIASI dulu (verifikasi angka nyata) sebelum dipakai sebagai janji.*

### Model: dua sumbu, JANGAN disatukan jadi satu toggle
**A) Transparansi — WAJIB di KEDUA mode (tak bisa di-opt-out):**
- Fallback aktif → **notifikasi tenant** (Telegram — `telegram_notifier` sudah ada) + **flag output** di `content_inventory.metadata` (`fallback_used=true`, `provider_used`, `quality_note`).
- Flag ini = **sinyal QC** → tampil di dashboard + (idealnya) tercatat di QC akhir. Tidak pernah senyap.

**B) Lanjut-vs-stop — INI yang jadi checkbox per-komponen (frontend):**
- ☑ **Izinkan fallback** → produksi lanjut pakai cadangan (tenant terima konsekuensi yang dijelaskan eksplisit).
- ☐ **Tidak diizinkan** → komponen utama gagal → **item DIHENTIKAN** (status blocked) + **alert keras** ("kredit ElevenLabs habis — inject sekarang"). Tak ada konten turun-kualitas tayang. Terhubung ke **monitor kredit BYOK**.

### Tier fallback (acceptability BERBEDA)
| Komponen | Rantai | Boleh tayang (bila diizinkan)? |
|---|---|---|
| TTS | ElevenLabs → edge_tts | ✅ degradasi wajar (caption ~80%, suara generik) |
| Visual | ai_image → Pexels | ✅ wajar (stock, bukan bespoke) |
| Visual | … → **black-screen** | ❌ **TIDAK PERNAH** — itu video rusak; **selalu stop**, lepas dari checkbox |

### Default & teknis
- **Default** (keputusan owner — lihat §6): rekomendasi **stop** untuk provider **premium berbayar** (nilai jual = kualitas premium).
- **Pendaratan:** config per-komponen (TTS: `tts_fallback_provider` + boolean allow; Visual: kebijakan `visual_fallback`); **frontend checkbox + penjelasan konsekuensi spesifik**; wiring `telegram_notifier`; flag `content_inventory.metadata`.

---

## 5. Rencana eksekusi (fase — diisi/di-update saat dikerjakan)

- **F0 (DONE):** QC interim aman (floor 3s) — tak memblokir preset; produksi aktif tetap terlindungi.
- **F1 ✅ DONE (2026-06-14):** katalog **`format_profiles`** (WPS per-format §4: energik/listicle 2.4, edukasi 2.2, motivasi 1.6 + section_template/cta/render) + **`duration_presets`** (8/15/30/45/60/75/90s + visual_beats §3) + field `channels.duration_preset`/`format_profile` (NULLABLE = non-breaking). Migr `0012`, public-read, tervalidasi v2. Prasyarat QC v2 & multi-format. *(field di channels, bukan tenant_configs — per-channel, selaras niche/content_language.)*
- **F2 ✅ DONE (2026-06-16 dikonfirmasi):** **QC v2 Lapis 1–3 SUDAH diterapkan** di `_pre_publish_qc`. Lapis-1/3 integritas (stream video+audio + aspect 9:16). **Lapis-2 konformitas-durasi-relatif AKTIF**: `|durasi−target_preset|/target_preset ≤ QC_DURATION_TOLERANCE` (`pipeline.py:562`, default **0.15**) + clip_count = visual_beats preset. `target_preset` dari `channels.duration_preset` (F1). Terbukti di test ryan (43s vs 60s ditolak, "di luar ±15%"). **Sisa nyata = akurasi durasi (WPS provider-aktual, §2), bukan QC-nya.**
- **F3:** Kebijakan **quarantine + re-generate terarah** (ganti buang-buta) + diagnosa terstruktur ke `pipeline_run_logs`.
- **F4:** **Self-critic pra-submit** (review render: caption-sync, keterbacaan, brand-safety).
- **F5:** Loop belajar dari QC-fail → auto-tune word_budget/section_timing per preset; A/B hook/thumbnail.
- **F6:** Dashboard "robot belajar apa" untuk tenant (transparansi klaim landing).
- **F7 (§4b):** **Consent & Transparency Fallback** (TTS+Visual) — notifikasi+flag WAJIB; checkbox lanjut-vs-stop per-komponen; tier (black-screen selalu stop); alert "inject kredit". Rekonsiliasi dulu angka akurasi edge_tts (95% vs 80%).

> Urutan & detail tiap fase **diputuskan bersama owner** sebelum koding (propose-first).

---

## 6. Keputusan (2026-06-13, expert) + yang masih perlu data
**DIPUTUSKAN** (owner delegasi keputusan teknis — [[feedback_owner_delegates_expert_decisions]]):
1. `QC_DURATION_TOLERANCE` = **0.15 (15%)** — **diselaraskan ke KODE** (`pipeline.py:562`). *(Revisi 2026-06-16: sebelumnya tertulis 20%; owner — toleransi BUKAN lever; akar durasi diperbaiki di WPS §2, bukan dilonggarkan.)*
2. **QC-fail durasi → PUBLISH PRIVATE + ADVISORY** (keputusan owner 2026-06-16), **bukan dibuang**. Video tetap di-publish **private** (walau channel public) → tenant **lihat hasilnya** + terima **advisory (alasan + rekomendasi config)** → **tenant putuskan** public-kan / take-down. Mengganti perilaku lama (`pipeline.py:317` hapus video). Retry/regenerate = §3/F3 (kalibrasi, bukan loop bakar-kredit).
3. Self-critic = **heuristik dulu**; LLM-vision ditunda (biaya × ribuan tenant).
4. Prioritas = **G-final integritas dulu (✅ DONE)** → QC-relatif nyusul bersama field Preset (F1).
5. Default fallback = **stop** untuk provider premium berbayar (nilai jual = kualitas); per-komponen bisa beda (Visual ai_image→Pexels boleh).

**Masih perlu DATA/biaya (jangan dikoding buta):**
- Kalibrasi WPS per-provider + G-audio loop → butuh ukur WPS (run; ElevenLabs lapse) + validasi render (biaya owner).
- Rekonsiliasi akurasi edge_tts (95% vs 80%).

---

### Changelog
- 2026-06-13 — dibuat. Kondisi awal terdokumentasi; QC interim floor 3s; QC v2 + self-improvement roadmap diusulkan (menunggu keputusan owner per §6).
- 2026-06-13 — **§4b Consent & Transparency Fallback** ditambah (disetujui owner): umum TTS+Visual, model A (transparansi wajib) + B (checkbox lanjut-vs-stop), tier black-screen selalu stop, flag→QC. + F7. **Validasi staged-QC** (deviasi durasi nyata 5–31% vs target 51s; risiko regenerate-loop; G-audio feasible krn `target_duration` `script_engine.py:206` + `audio_duration` `pipeline.py:219` sebelum step mahal).
- 2026-06-13 — **Keputusan §6 direkam** (owner delegasi). **Root cause durasi tervalidasi** = WPS 2,4 hardcode ≠ delivery nyata per-provider (1,67–2,41) → folded ke §2. **G-final integritas (Lapis-1/3) DIIMPLEMENTASI + tervalidasi** (`_pre_publish_qc` cek stream audio/video + aspect 9:16, config-driven; klip uji lokal). Fix durasi penuh = blocked data/biaya.
- **2026-06-16 — SINKRON ke realita + keputusan owner (test e2e ryan):** (1) §2 root-cause di-update: **WPS bukan lagi 2.4 hardcode** (F1 per-provider `format_wps`); residual = budget pakai WPS provider terkonfigurasi vs provider AKTUAL fallback (EL 1.8 vs edge 2.6 → 43s/60s). (2) **F2/Lapis-2 durasi-relatif KONFIRMASI SUDAH AKTIF** (`QC_DURATION_TOLERANCE` default 0.15). (3) §6.1 toleransi diselaraskan **20%→15%** (sesuai kode; owner: toleransi bukan lever, WPS yang diperbaiki, **no preset-hack**). (4) §6.2/§3 kebijakan QC-fail → **publish PRIVATE + advisory** (bukan buang). (5) **Isu no-hardcode ditemukan**: `tts_engine` concern-messages **hardcode "ElevenLabs"/"Edge"** + hanya ke log (langgar §0.3) → diperbaiki bareng F7/advisory (eksekusi #2).
