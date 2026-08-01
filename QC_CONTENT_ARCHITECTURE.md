# QC & Content-Quality Architecture — MesinViral v2

> ✅🔒 **CLOSED sbg backlog aktif (2026-07-01).** Daftar kerja = HANYA **[`SISA_KERJA_GO_LIVE.md`](SISA_KERJA_GO_LIVE.md)**. **Dokumen ini = SPEC/single-source-of-truth arsitektur QC konten** (sinkron penuh ke codebase 2026-07-16 atas mandat owner).
>
> **⚠️ DUA PENOMORAN "F" BERBEDA di dokumen ini — jangan tertukar:**
> 1. **"QC-F0…QC-F7"** (§5) = fase roadmap QC lama (2026-06-13). Status: QC-F0/F1/F2 ✅ LIVE · QC-F3 quarantine, QC-F4 self-critic, QC-F5 belajar-QC-fail (sebagian terwujud), QC-F6 dashboard, QC-F7 consent-fallback = ROADMAP.
> 2. **"PROGRAM DURASI F1…F5"** (banner 🎯 di bawah) = program perbaikan durasi 2026-07-16. Status: **kodenya TER-DEPLOY, tapi DONE-BILA-nya TIDAK PERNAH DIPENUHI** — lihat §2c (2026-07-29). Kata "LIVE" di sini dulu dibaca sesi-sesi berikutnya sebagai "durasi sudah beres", padahal yang terbukti hanya kodenya naik ke server, bukan akurasinya. **Jangan tandai apa pun ✅ sebelum diukur dari DURASI VIDEO JADI.**
> 3. Kode fase lain yang ikut disebut (mis. `F1-05`, `F5-01` = fase dokumen REMEDIASI; `[B6] F0–F4` = tracker AI-video) = penomoran dokumen/tracker LAIN — selalu dibaca bersama konteks kalimatnya.

> **Living document.** Tujuan: arsitektur khusus untuk *quality control* + *self-improvement* yang **terus dievaluasi & di-improve** sampai ideal. Cakupan: **dari ScriptAnalyzer → seluruh tahap produksi → file hasil (pra-submit)** + **loop self-analyzer/self-improvement** (janji landing page: "robot pintar, makin pintar tiap hari").
>
> Status LIVE per-fase = `PROGRESS.md`. Pondasi multi-format = `MULTI_FORMAT_STUDIO.md`. Prinsip: [[feedback_no_hardcode]] · [[feedback_analysis_discipline]].
>
> **🔄 REKONSILIASI AUDIT 2026-07-01:** durasi-via-speed (fase F4 milik dokumen REMEDIASI, commit `8670fc3`, migr 0078/0079) diterapkan. QC v2 Lapis 1-3 (QC-F0–QC-F2) = LIVE. **Masih ROADMAP:** QC-F3 quarantine · QC-F4 self-critic pra-submit · QC-F5 belajar-dari-QC-fail · QC-F6 dashboard · QC-F7 consent-fallback penuh.
>
> **⚠️ KOREKSI 2026-07-15 (data produksi membantah klaim lama "durasi TUNTAS"):** durasi MASIH sering meleset di produksi beragam-niche (±10 dari 206 run gagal "di luar ±15%"; contoh nyata: preset 60s → audio 46,8s). **ROOT-CAUSE (verified log+kode):** (1) *Lapis-1, akar utama* — LLM sering menulis naskah KEPENDEKAN (mis. 72–86 kata dari target ~134) menembus 3× retry, lalu sistem "pakai seadanya" (best-score) → durasi mustahil tercapai walau suara diperlambat mentok; (2) *Lapis-2, menipu* — estimator durasi (`solve_speed_for_duration`, seed `_PAUSE_INFLATION`=1.10 belum dikalibrasi per-suara) meleset ~9% → naskah kadang lolos gate padahal nyatanya pendek. Perbaikan lampau semua menyentuh Lapis-2 (kalibrasi/tuas speed/toleransi); **Lapis-1 belum tuntas** (tak ada pemaksaan panjang yang mengikat).
>
> **✅ DITANGANI 2026-07-15 (commit `d27273b`; ✅ DEPLOYED 2026-07-16 bersama batch F1):** (a) **Lapis-1 prompt** `script_engine._build_user_prompt` — CABUT pintu-kabur ("sistem set speed; rewrite panjang hanya bila terpaksa" = yang mengajari LLM abaikan jumlah kata) → target **STRUKTUR (jumlah kalimat)** yang bisa dipatuhi LLM (bukan hitung-kata yang mustahil) + panjang=syarat via kekayaan isi + **preset-aware** (8–15s cegah kepanjangan · 30–90s cegah kependekan). (b) **Gerbang durasi pra-visual** kini HANYA stop meleset PARAH (`QC_DURATION_GROSS_FACTOR`×tol, default ±30%); **near-miss LANJUT diproduksi → OPSI C review** (tak dibuang, tak panik). (c) **Pesan review** dimanusiakan (`_humanize_qc_reason`; nol jargon, nol "GAGAL"). *(Blok prompt versi ini SUDAH digantikan penuh oleh PROGRAM DURASI F3 di bawah — seragam EN, hardcode dibuang.)*
>
> **🎯 PROGRAM DURASI 5-FASE (mandat owner 2026-07-16 "tuntas 100% no turn-back"; tracker = `SISA_KERJA_GO_LIVE.md [C1]`):**
> **ROOT-CAUSE FINAL (data 110 render + backfill log + DNA niche — MENYEMPURNAKAN koreksi 2026-07-15 di atas):** 85% video keluar PENDEK; biang dominan = **taksiran pace salah per (voice × gaya-DNA-niche)** — voice SAMA beda niche pace nyata beda s/d 25% (Ardi: legenda_daerah 2.53 vs radiant_affirmations 2.00 wps); niche yang pace-nya kebetulan pas (dark_history) = **86% dalam ±15%**, yang melenceng cuma 20–58%. `tts_profiles.delivery_wps` global SUDAH akurat <1% (**JANGAN dikalibrasi ulang membuta**); `voice_catalog.delivery_wps` per-voice mayoritas NULL. Error taksiran per-niche terukur (backfill): ocean 3% · dark 6% · legenda ~10% · radiant ~12% · **fun_facts ~20%**. DNA mempengaruhi durasi via `narration_persona.style` (radiant "ONE sentence" = konflik struktural) + kepadatan jeda; visual TIDAK menentukan durasi (ai_video: klip diskrit ≥ audio lalu di-trim; hukum durasi final tetap `audio + trailing` utk SEMUA render_mode — `video_renderer.py` `total_duration`).
> - ✅ **F1 INSTRUMEN — DEPLOYED 2026-07-16** (`fe83d28`, migr 0162): +5 kolom nullable `tts_delivery_samples` (`predicted_secs` · `raw_audio_secs` [mentah PRA-atempo — pembanding sah; `audio_secs` = pasca-koreksi] · `target_secs` · `pause_secs` · `pause_counts`); tiap render TTS kini merekam taksiran-vs-aktual. Durasi mentah diukur 1× & dipakai-ulang `_fit_duration(precomputed_actual)` → **NOL ffprobe/waktu tambahan**. + **BACKFILL mining worker.log**: 78/112 baris lama terisi (0 ambigu; md5 kolom lama identik).
> - ✅ **DURASI-3 KOREKTOR — DEPLOYED 2026-07-16** (`a4ea83e`): STEP 5 (target atempo) dulu pakai env `RENDER_TRAILING_SILENCE` (1.5 umum) sementara naskah/gerbang/renderer pakai `effective_trailing` per-preset → korektor mengejar target BEDA (8s: naskah 7.0s dipaksa atempo ke 6.5s — suara dipercepat percuma, final ~7.6s). Kini **SATU rumus di 4 titik** (pipeline STEP 5 hitung trailing efektif → kirim `target+trailing_secs` ke `tts_engine.generate` → `_fit_duration`).
> - ✅ **F2 KALIBRASI — BUILT + tabel terisi 2026-07-16 (✅ DEPLOYED `4fee742` health=200):** (a) migr **0163** `tts_pace_calibration` (pace per voice×niche + agregat '*') + **0164** `tts_speed_response` (α respons-speed per provider) — dua tabel BARU additif; kosong = perilaku lama persis. (b) **Temuan α (regresi log-log, R²=0.80 n=45):** ElevenLabs MELEBIH-LEBIHKAN perintah speed (α=1.324; edge 1.02 patuh) — estimator lama berasumsi α=1. (c) `src/production/pace_calibration.py`: α dulu → inversi pace sadar-α → median per sel; pagar = min-sampel (env `PACE_CALIB_*`), `pace_locked` dihormati (skip+hapus), nilai di luar pagar DITOLAK bukan di-clamp. (d) Jalur-baca: `tenant_config._load_pace_calibration` (niche EFEKTIF, semantik sama blok DNA s85) → `script_engine` lapis pace: **terkalibrasi(voice×niche→'*') → voice_catalog → tts_profiles**; solver+estimator sadar-α (`speed_alpha`, default 1.0 = rumus lama byte-identik). (e) **BUKTI replay leave-one-out 73 render:** error taksiran median **9.3% → 4.7%**, dalam-±10% **54% → 74%**, SEMUA 8 niche membaik (fun_facts 20.5%→5.1%). Kalibrasi perdana tertulis: α×2 + 10 sel pace. Uji lokal 4/4 (α=1 identik-lama · solver mendarat tepat · guard α liar · jalur-baca live).
> - ✅ **F3 PROMPT FINAL + TOLERANSI-1-SUMBER — DEPLOYED 2026-07-16 (`916e72f` health=200):** (a) `_script_len_tol()` = SATU sumber (env `SCRIPT_LENGTH_TOLERANCE` hidup dari config-mati, dipagari terkode `min(·, QC_DURATION_TOLERANCE)`); 6 angka terpatri DIBUANG (prompt ±10% · legacy −8/+12% · beat MAX +15% · gerbang `length_ok` ±10%) + fosil `_Tlo/_Thi` prompt. (b) **BEAT PLAN = satu-satunya otoritas angka**: tiap beat target + **MIN** (lantai anti-kependekan — dulu tak ada) + MAX dari toleransi tunggal; protokol SWA-VERIFIKASI (draft → hitung per-beat → revisi → output `_beat_words` di JSON). (c) `length_block` SERAGAM INGGRIS (blok ID di kerangka EN = penurun kepatuhan) + hardcode "~14 kata/kalimat" DIBUANG; pintu-kabur speed tetap tercabut. (d) Feedback retry kini ground-truth **per-beat** (sistem hitung kata nyata tiap beat → "OFF-BUDGET BEATS: hook 5w vs target 9w"). Uji lokal: prompt 3 preset (8/30/60 — EN penuh, MIN/MAX konsisten rumus, `_beat_words`+SELF-CHECK ada, pintu-kabur nihil) + toleransi (default/override/pagar-QC) + py_compile; grep-final: nol toleransi terpatri tersisa. **Bukti runtime menyusul otomatis via timbangan F1** (kata vs target per render + frekuensi DURATION-FAIL-retry).
> - ✅ **F4 JALUR DNA + OVERHEAD PENUH — DEPLOYED 2026-07-16 (`7dd42cd` health=200):** (a) **Ranjau overhead-loop MATI**: video final = audio + trailing + LOOP bersih (loop−0.5, verified `_add_loop_ending`) — naskah sudah menghitungnya tapi korektor STEP 5 & gerbang pra-visual hanya trailing → korektor bisa MEREGANG audio benar (8s ±12%). Kini `format_catalog.effective_overhead` = SATU rumus 4 titik (naskah pakai helper [ekuivalen, uji 2] · STEP 5 `overhead_secs` · gerbang · window `_fit_duration`); tanpa-param = jalur lama persis. (b) **DNA radiant diharmonisasi** (config, guard hanya key `style`): 'ONE single quotable sentence' → 'ONE flowing sentence that FILLS the required word budget (or two short) + ellipses sparingly' — selaras MIN/MAX F3. (c) Klip-diskrit ai_video = fakta harga vendor (Kling 5/10s · Hailuo 6/10s · Veo patok 8s), bukan bug — relevan saat owner pilih model [B6]. Uji 4/4: rumus overhead (8s=2.0 · 60s=3.5 · off/None/rusak aman) · ekuivalensi budget naskah · korektor tak meregang audio-benar · kompatibel-mundur.
> - ✅ **F5 SWA-PEMELIHARAAN — DEPLOYED 2026-07-16 (`7dd42cd` health=200):** `pace_calibration.run_maintenance` dipanggil `self_learning.run_once` tiap cadence (fail-soft total): (1) **kalibrasi pace+α otomatis** dari sampel baru (ganti suara/niche/provider apa pun → terkalibrasi sendiri); (2) **bobot-beat dinamis-sederhana** `align_beat_weights` — ground-truth `tts_delivery_samples.beat_words` (migr 0165; hitungan SISTEM dari naskah final, bukan laporan LLM), rasio porsi-nyata÷porsi-cfg per set-beat-sampel, langkah dibatasi ±`BEAT_ALIGN_MAX_STEP_PCT` (20%), min `BEAT_ALIGN_MIN_N` (10), `content_beats.weight_locked` dihormati, bobot int ≥1; (3) **alarm drift** `check_drift_alarm` — median |error| taksiran `DRIFT_WINDOW_N` (30) sampel terbaru > `DRIFT_ALARM_PCT` (10%) → Telegram ADMIN (murni lapor, nol aksi otomatis — §0.6); anti-alarm-palsu (data tipis → diam). Uji: nyata (align nol-perubahan saat data kosong · drift 12.5% alarm NYATA terkirim [taksiran era pra-kalibrasi — ekspektasi turun <10% pasca-deploy] · pace dry 10 sel) + sintetis (langkah dibatasi 3→4 bukan →6 · lock utuh · min_n) + recorder beat_words. Form admin bobot-beat (Catalog>Durasi, tampil+lock+panduan) = item FE terpisah menyusul.
> - **DONE-BILA:** akurasi per-niche ≥ patokan dark_history (86% dalam ±15%) DIBUKTIKAN dari render nyata pasca-kalibrasi; alarm drift hidup.
> - 🔴 **DONE-BILA DI ATAS TIDAK TERPENUHI — diukur 2026-07-29 dari produksi nyata 30 hari:** preset 60s meleset rata **−5,5 dtk** (20% dalam ±1,5 dtk), preset 90s **−14,2 dtk** (7%), terburuk −40,6 dtk; 36 dari 110 render di luar ±15%. Preset 8/15s memang presisi (0,5 dtk · 91%) — dan **justru di situ dulu validasi dilakukan**, sehingga program ini dinyatakan selesai berdasar kasus yang kebetulan lolos. Rincian & sebab = §2c.
>
> **Aturan dokumen ini:** setiap perubahan QC/quality WAJIB lewat sini dulu (propose → approve → implement). Jangan ubah ambang QC di kode tanpa update dokumen ini.

---

## 0. Prinsip dasar (kontrak arsitektur)

1. **QC ≠ penilaian konten.** Kualitas konten (hook, retensi, CTA) dinilai **di hulu** oleh `ScriptAnalyzer` (ambang ≥80). QC pra-submit hanya menjawab: *"apakah FILE hasil render utuh, sesuai NIAT produksi, dan sah untuk platform?"* — bukan "apakah kontennya bagus".
2. **Relatif, bukan absolut.** Tidak ada angka ajaib global (mis. "≥45s"). Ambang diturunkan dari **Duration Preset** + **Format Profile** tenant (8/15/30/45/60/75/90s). Floor absolut = anti-pattern yang membuang video valid + biaya render.
3. **Config-driven, no-hardcode.** Semua ambang dari config/DB/env, dapat ditambah super-admin. Tidak ada nama provider/angka tertanam di pesan error.
4. **GAGAL JUJUR, nol degradasi senyap.** Kegagalan komponen produksi (TTS/visual) = **STOP + tercatat + ternotifikasi** — TIDAK pindah diam-diam ke cadangan (NO-FALLBACK, F1-05; fallback ber-izin = fitur opt-in masa depan §4b). QC-fail → video TIDAK dibuang membabi-buta → OPSI C review (§2/§7). *Yang boleh "fail-soft" hanyalah komponen OBSERVASI (logging/kalibrasi/alarm) — gagal mengamati tak boleh mengganggu produksi.*
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
| 5 | TTS | **NO-FALLBACK (F1-05)**: HANYA provider terkonfigurasi channel; gagal = gagal jujur. + closed-loop atempo (`_fit_duration`, overhead PENUH per-preset F4) + instrumen F1 (`_log_delivery_sample` → taksiran-vs-aktual + `beat_words`) | `production/tts_engine.py` |
| 6 | Visual assembly | N clip = **`visual_beats` preset** (per-preset; legacy tanpa-preset default 6); ai_video = 1 klip ≥ audio lalu di-trim | `production/visual_assembler.py` |
| 7 | Render | xfade + caption (karaoke ASS) + music ducking + trailing efektif per-preset + loop-ending | `production/video_renderer.py` |
| 7.5 | **Pre-publish QC** | **QC v2 relatif** (durasi ±tol vs preset · clip=visual_beats · size SADAR-DURASI per-60s floor 0.3MB · stream audio+video · aspect) — lihat §2 | `pipeline.py::_pre_publish_qc` |

### 1a. ScriptAnalyzer — gate kualitas konten utama (HULU)
`VIRAL_DIMENSIONS` berbobot (`script_analyzer.py`):
- `hook_power` 25% · `curiosity_gap` 20% · `retention_arc` 20% · `emotional_peak` 20% · `information_density` 10% · `cta_strength` 5%
- Ambang lulus **80/100**; di bawah → retry s/d 3× dengan **feedback per-dimensi** (ScriptEngine `generate`). Kriteria `emotional_peak` diambil dari **niche profile (Supabase)** → sudah config-driven.
- **Inilah penilai "konten bagus".** QC pra-submit TIDAK boleh menduplikasi peran ini.

### 1b. Self-improvement loop yang SUDAH ADA (parsial)
Janji landing "self-improve tiap hari" **sudah berdiri sebagian**:
```
video nyata → video_analytics (views, watch_time, avg_view_pct, ctr, subscriber_gain)
   → PerformanceAnalyzer.compute_and_store()  [self_learning worker — loop 24j; cron compute_insights.sh DIHAPUS 2026-06-28]
   → channel_insights (grade, niche_weights, top_hooks[by CTR], avoid_patterns, content_types)
   → di-inject balik ke: NicheSelector (smart focus) · ScriptEngine (top hooks/content types) · HookOptimizer (historical hooks)
```
**Grade tiers** (`performance_analyzer.py`): `insufficient_data` (<5 video → estimasi AI murni) · `learning` (5–20 → inject top topics, belum adjust skor) · `peak` (50+ → ekstraksi pola hook + A/B ready). Sumber analytics: `analytics/channel_analytics.py` (YouTube Analytics) → `video_analytics`.

---

## 2. QC pra-submit — KONDISI NYATA (sinkron kode 2026-07-16)

`_pre_publish_qc(video_path, duration_secs, clip_count, target_seconds, expected_beats)` — dua mode:

**Ber-preset (produksi normal) → QC v2 RELATIF penuh:**
1. **Durasi**: `|aktual − preset| / preset ≤ QC_DURATION_TOLERANCE` (default 0.15) — tanpa floor absolut.
2. **Clip**: `clip_count ≥ expected_beats` (= `visual_beats` preset — BUKAN hardcode 6).
3. **Ukuran SADAR-DURASI** ([B6] F4 2026-07-14): ambang env = basis per-60s, diskalakan `× target/60`, floor 0.3MB (8s sehat 3.3MB tak lagi dicap "render gagal").
4. **Integritas**: stream video+audio (`QC_REQUIRE_AUDIO`) + aspect 9:16 (`QC_ASPECT`/`QC_ASPECT_TOLERANCE`).

**Tanpa preset (legacy) → interim integritas:** size ≥ `QC_MIN_SIZE_MB`(5) · durasi ≥ `QC_MIN_DURATION`(**3**) & ≤ `QC_MAX_DURATION`(180) · clip ≥ `QC_MIN_CLIPS`(6).

**Gerbang KEDUA di hulu (pra-visual, `pipeline.py` STEP 6):** proyeksi `audio + overhead PENUH` (trailing efektif + loop bersih — `effective_overhead`, F4) vs window QC yang SAMA; meleset **PARAH** (>`QC_DURATION_GROSS_FACTOR`×tol) → stop sebelum biaya gambar/render; **near-miss → LANJUT → OPSI C review** (owner 2026-07-15).

### Masalah arsitektur (status 2026-07-16 — SEMUA butir lama TERTUTUP)
- ✅ Floor durasi absolut → QC relatif preset (F2 QC v2) + interim 3s utk legacy.
- ✅ Integritas vs konten dipisah (konten = ScriptAnalyzer; QC = file/niat/platform).
- ✅ `clip_count` & `size` absolut → clip = visual_beats preset; size sadar-durasi.
- ✅ QC-fail = buang total → **OPSI C**: `ready_with_issues` → tenant tinjau/putuskan (§3, §7).
- ✅ Cek integritas teknis (stream audio+video + aspect) — tervalidasi.

### 🗄️ ARSIP — Root cause DURASI (kronik 2026-06-16/17; SUPERSEDED oleh banner "PROGRAM DURASI 5-FASE" di atas — root-cause FINAL = pace per voice×niche + α respons-speed + overhead, semua SUDAH ditangani F1–F5)
**KOREKSI status:** WPS **bukan lagi** `2.4` hardcode. F1 (migr 0012) memasukkan **`format_wps` per-format/provider** dari `tts_profiles` (`script_engine.py:224` `WPS = format_wps if format_wps else 2.4`; 2.4 kini **fallback legacy** saja; sumber: `_eff_wps(format_profile, tts_provider)` `script_engine.py:511`). `tts_profiles.delivery_wps`: elevenlabs **1.8** · edge_tts/openai_tts **2.6**.
**Residual (tervalidasi test ryan 2026-06-16):** word-budget pakai `delivery_wps` provider **TERKONFIGURASI** (ryan=elevenlabs→1.8) tapi yang **me-RENDER = edge** (fallback krn ElevenLabs lapse, 2.6) → budget 60×1.8=108 kata, edge bicara 108/2.6 ≈ **43s** untuk target 60s → QC-fail. **Akar = WPS budget ≠ WPS provider AKTUAL (saat fallback).**
**Akar KEDUA — LLM under-produce word budget (tervalidasi e2e ryan 2026-06-16, run `direct-0f73a253`):** kali ini ElevenLabs **berhasil** (98% timestamps, no fallback) TAPI durasi tetap pendek (**48.3s** vs 60s) karena `ScriptEngine` hanya menghasilkan **73 kata** vs budget 108 — `length-gate` (script_engine.py:629 "73w vs target 108w → retry") retry 3× lalu **pakai best-available** (78/100) yang tetap pendek. Jadi miss-durasi bisa datang dari **(a) WPS provider-mismatch saat fallback** ATAU **(b) LLM tak memenuhi word_budget** meski provider utama jalan. **Implikasi fix:** selain WPS-follow-actual (a), perlu **length-gate lebih tegas** (b) — mis. retry sampai ≥ budget×toleransi, atau prompt yang memaksa panjang, sebelum publish (masuk F3/F5 self-tune). *Advisory dinamis (§3) sudah benar menangani kedua kasus: `fallback_used=True`→saran provider; `False`→saran preset/panjang skrip.*
**Fix benar (2 jalur):** (a) WPS budget **ikut provider yang BENAR-BENAR me-render** (termasuk fallback) — bukan provider terkonfigurasi; ATAU (b) cegah fallback senyap (re-subscribe premium / §4b stop-on-fallback). **⛔ BUKAN dengan menurunkan preset**

> 🔴 **KLAIM DI BAWAH INI GUGUR (dibantah eksperimen 2026-07-29, §2c).** "Akar = prompting" ternyata SALAH: memperketat prompt tidak pernah bisa menyelesaikan durasi, dan justru klaim ✅ inilah yang membuat setiap sesi berikutnya berhenti mencari. Perhatikan juga akar yang BENAR sudah tertulis satu paragraf di atas ("LLM under-produce word budget", 2026-06-16) lalu ditimpa klaim ini keesokan harinya — tanpa pernah diperbaiki.
> ~~✅~~ **AKAR SEBENARNYA = PROMPTING LLM (DIPERBAIKI 2026-06-17, keputusan owner).** Bukan WPS/TTS. Arsitektur (owner): **(1) LLM hasilkan total-kata sesuai preset** → **(2) TTS provider TERDAFTAR** (apa-adanya: premium dulu, kredit kurang → fallback edge) → **(3) durasi pas → lolos QC → publish**; bila edge (kredit kurang) → produk jadi tapi tak lolos QC → **flagged (Opsi C) + lapor tenant saat tinjau: "kredit TTS tak cukup, pakai edge default — terima/topup+re-run"**.
> - **Fix:** word-budget pakai `delivery_wps` provider **TERDAFTAR** tenant (mis. elevenlabs 1.8 → 60s=109 kata). Prompt `_build_user_prompt` diberi **direktif TEGAS total-kata + durasi** ("MUST total N words, range lo–hi, REJECTED jika kurang") + per-seksi menjumlah ke total. **length-gate diperketat** `SCRIPT_LENGTH_TOLERANCE` 0.25→**0.12** + feedback retry tegas+spesifik (berapa kata kurang). 
> - **Tervalidasi (LLM-only, 2026-06-17):** ryan 60s → word_count **82 → 109** (rentang 100–122, lolos quality-gate). Dengan ElevenLabs 1.8 → 60.5s lolos QC; edge → ~44s flagged (by-design, ryan kredit tipis).
> - **TTS DIKEMBALIKAN apa-adanya** (revert "effective-provider/is_available" — itu belok yang salah). File: `script_engine.py` (prompt+gate); `tts_engine.py`/`providers/tts/{base,elevenlabs}.py` (revert bersih).
> - ✅ **DISEMPURNAKAN per-preset 2026-06-17 (compression-mapping, MULTI_FORMAT §3):** prompt LLM kini **per-preset** — `visual_beats` → N beat narasi (=N scene), BEAT PLAN dinamis + intent naratif per-durasi + budget-kata per-beat. **Validasi LLM-only: 15/30/45/60/75/90 SEMUA word_count tepat + scene=beats + durasi-EL pas.** Bukan 1-prompt-untuk-semua lagi. Detail = `MULTI_FORMAT_STUDIO §3`. (preset 8/15/30/45/60/75/90 sudah rapat by-design; turunkan preset = output ikut lebih pendek, tetap meleset — keputusan owner 2026-06-16, no preset-hack).

---

## 2c. DURASI VIDEO & MUTU NARASI — SATU-SATUNYA ACUAN (status per 2026-08-01)

> **Bagian ini menggantikan seluruh catatan durasi sebelumnya.** Yang tertulis di bawah adalah
> **keadaan sekarang**, bukan riwayat. Riwayat percobaan hanya disebut di satu tempat: daftar
> "JANGAN DIULANG". Angka apa pun di dokumen lain tentang durasi = **basi**.

### ISSUE UTAMA (kata owner, 3 butir)

1. **Setiap video wajib masuk rentang toleransi preset durasinya.**
2. **Narasi adalah ISI produk** — dibaca, didengar, dilihat penonton. Tidak boleh ada potongan yang
   merusaknya.
3. **Seluruh DNA niche + konfigurasi channel wajib jadi asupan LLM** saat membangun narasi.

Diukur dari produksi nyata: hanya **22% dari 243 video** mendarat di batas sah; **41%** render mentok
di kecepatan suara paling lambat (**nol** render normal); **107 dari 294** produksi gagal QC.

### SOLUSI — RANTAI YANG BERJALAN SEKARANG

**A. ALAT UKUR — dua tahap, keduanya PENGUKURAN, bukan turunan**

1. **Biaya tiap tanda jeda DIUKUR LANGSUNG** (`src/production/pause_probe.py`), dua cara:
   - **Pasangan terkontrol** — lima versi teks ber-HURUF IDENTIK yang hanya berbeda tandanya
     (`duration_probe_texts` di DB, bukan di kode). Selisih durasinya hanya bisa milik tanda itu.
     Dipakai untuk penyedia yang deterministik (Edge: sebaran antar-teks ±0,05 dtk).
   - **Jarak antar-kata dari penanda waktu penyedia** — pembandingnya ada DI DALAM render yang sama,
     jadi kebal derau antar-render. Wajib untuk ElevenLabs (`stability` 0,3 = prosodi diambil sampel
     tiap render; cara pasangan menghasilkan nilai koma −0,244…+0,505 dtk, separuhnya negatif).
   - Pagar: arah harus konsisten di ≥75% teks · sebaran (MAD) ≤100 ms · median ≥50 ms. Gagal → tanda
     itu TIDAK dianggap terukur (pakai angka bawaan), bukan disimpan sebagai angka.
2. **Huruf & angka di-fit dari naskah nyata dengan biaya jeda DIPATOK** (`_fit_jeda_dipatok`).
   Dua parameter dari puluhan titik jauh lebih stabil daripada enam.

    detik_audio = a·huruf + b·ANGKA + c·kalimat + d·elipsis + e·koma + f·em_dash

**Ketepatan luar-sampel (leave-one-out) di rentang preset produksi:**

| suara | sebelum | sekarang | terburuk |
|---|---|---|---|
| id-ID-ArdiNeural | 1,47 dtk | **1,13** | 3,63 |
| id-ID-GadisNeural | 1,82 dtk | **1,52** | 4,46 |
| en-US-JennyNeural | — | **0,89** | 2,04 |
| ElevenLabs Adam | 3,33 dtk | **2,34** | pertama kali terkalibrasi |

**B. SATU KOEFISIEN HANYA LAHIR BILA ADA CUKUP BUKTI**
Tanda yang muncul di < `pace_calib_min_fitur_n` naskah TIDAK dapat angkanya sendiri → dikosongkan →
angka bawaan terukur yang dipakai. Kolom "ada tapi jarang" LEBIH berbahaya daripada kolom kosong:
hasilnya angka yang tampak masuk akal (em-dash pernah 1,137 dtk padahal terukur 0,424).

**C. LAJU BICARA = RATIO 1, DI SEMUA PENYEDIA** (aturan owner 2026-08-01)
Satu fungsi bersama (`src/production/voice_delivery.py`) menerjemahkan setelan penyedia apa pun
(`rate: "+15%"` gaya Edge · `speed: 0.87` gaya ElevenLabs/fal/OpenAI) menjadi SATU rasio tanpa satuan.
Dipakai adaptor (melaporkan apa yang benar-benar dikirim) DAN kalibrasi (memeriksa sampel diukur pada
laju yang sama) — satu implementasi, tak bisa berbeda diam-diam.

**D. BATAS SAH = TITIK-TENGAH ANTAR-PRESET** — `duration_model.band_video()`, satu sumber untuk resep
naskah, gerbang pra-visual, dan QC pasca-render. Preset 480 dtk: lantai keras 480,0 (ambang iklan).

**E. PERINTAH KE PENULIS = KATA + KALIMAT**, dibagi per adegan lewat `content_beats.weight`.

**F. NASKAH DI LUAR JATAH → TULIS PER BAGIAN, DIPICU DUA ARAH.** Satu adegan ±30 kata ada di dalam
kemampuan model mana pun. Tiap bagian dikoreksi SEKETIKA: **lantai** (kependekan → dilengkapi) dan
**plafon** (kepanjangan → dirapatkan). Hasilnya dinilai "lebih DEKAT ke jatah", bukan "lebih panjang".

**G. MASIH MELESET → MODEL MERAPATKAN NASKAHNYA SENDIRI** (maks 3 putaran), sementara KODE
memverifikasi. **KODE TIDAK PERNAH MEMOTONG KALIMAT.** Pagar putaran:
- putaran yang **menjauh dari band DITOLAK** (dulu diterima: '52s → 49s' padahal butuh ≥52);
- penjaga fakta **sadar arah** — memanjangkan = nol toleransi; memendekkan = sebanding porsi potongan,
  pagar keras 25% (melarang semua fakta hilang saat tugasnya memendekkan = perintah yang bertentangan);
- penolakan **tidak menghentikan loop**: putaran berikutnya diberi tahu PERSIS apa yang wajib kembali;
- **throttle penyedia ≠ balasan rusak** → ditunggu (2/4/8 dtk), bukan dihitung sebagai kegagalan.

**H. CACAT MEKANIS YANG DITEMUKAN → DIPERBAIKI PENULIS**, bukan cuma dilaporkan. Kode memverifikasi
cacat berkurang, fakta utuh, panjang tak bergeser >10%.

**I. AUDIO TIDAK LENGKAP = GAGAL JUJUR** (dua lapis) + **BATAS WAKTU PENYEDIA SUARA**. Panggilan TTS
dulu tanpa batas waktu sama sekali: penyedia yang menggantung mematikan satu utas pekerja selamanya,
tanpa error dan tanpa notifikasi.

**J. SELURUH AMBANG BISA DILIHAT & DIATUR OWNER** — 31 kenop pindah dari variabel lingkungan ke
`app_config` lewat satu pintu (`src/config/ambang.py`), dua kartu admin sendiri, label & penjelasan
dwibahasa, satuan yang wajar bagi manusia. Sebelumnya `.env` server tak memuat SATU PUN dari ambang
ini — semuanya berjalan dengan angka bawaan kode yang tak terlihat di layar mana pun.

**K. DNA NICHE & ARAHAN ADEGAN SAMPAI KE PENULIS** — dibuktikan dengan MENANGKAP PROMPT SUNGGUHAN,
bukan membaca kode.

### ANGKA TERUKUR YANG MENGGANTIKAN ANGKA LAMA

| | angka LAMA (turunan regresi) | TERUKUR LANGSUNG 2026-08-01 |
|---|---|---|
| elipsis (bawaan) | 1,376 dtk | **0,288** (rentang 5 suara 0,156–0,376) |
| koma (bawaan) | 0,221 dtk | **0,296** (0,172–0,396) |
| em-dash (bawaan) | 0,442 dtk | **0,292** (0,088–0,424) |
| akhir kalimat (bawaan) | 1,308 dtk | **1,184** (0,848–1,372) |
| em-dash Ardi | 1,137 dtk (dari 6 naskah) | **0,424** |
| em-dash Gadis | 1,262 dtk (dari 6 naskah) | **0,400** |
| ElevenLabs Adam | belum pernah terkalibrasi | koma **0,116** · em-dash **0,169** · kalimat **0,545** |

### YANG DICABUT — jangan dipasang kembali

| Dicabut | Bukti kenapa |
|---|---|
| `solve_speed_for_duration` (solver kecepatan) | 41% mentok 0,70 · nol normal · durasi tetap meleset |
| `tts_engine._fit_duration` (peregangan atempo) | 17/140 render diubah, faktor median 0,832 |
| `_apply_speed_to_rate` + jalur `tts_voice_settings[niche].speed` | **tuas kecepatan MASIH HIDUP di sisi pembaca sampai 2026-08-01**: BJ Yusroon (aktif) dibacakan −17%, Abyss ID −10% |
| bawaan `speed = 0.87` di adaptor ElevenLabs/fal/OpenAI | kembaran cacat `+10%` Edge, ke arah "seperti orang malas" |
| `estimate_spoken_seconds` + benih `_PAUSE_SECONDS` | salah 7,01 dtk |
| Toleransi persen ±12%/±15% + pagar 2× | arah salah; diganti titik-tengah |
| Batas platform 180 dtk rata | menolak semua video Regular sebelum dinilai |
| Kode memangkas kalimat | membuang fakta terkuat naskah |
| Biaya jeda dari REGRESI | derau yang menyamar jadi pengukuran (tabel di atas) |

### BUKTI RUNTIME

| Uji | Hasil |
|---|---|
| Rantai penuh sampai AUDIO, 6 channel nyata (gpt-4o-mini, izin owner) | 4/6 mendarat · ramalan meleset **0,1–2,0 dtk** di 5 channel |
| — Bang Us-Dat 60s | 66,2s ∈ 52–68 · meleset 0,7 dtk |
| — RETRO REWIND 60s | 63,2s ∈ 52–68 · meleset 2,0 dtk |
| — BJ Yusroon 90s | 89,5s ∈ 82–98 · meleset 0,3 dtk |
| — BISIK NUSANTARA 90s | 83,5s ∈ 82–98 · meleset 0,1 dtk |
| — RAD The Explorer (ElevenLabs) | 77,2s vs band 52–68 → **DI LUAR karena `speed 0,87` belum dimigrasi**: ramalan 65,5 ÷ nyata 74,7 = 0,877 persis. Alat ukur benar; produksi yang 13% lambat |
| — Abyss ID 30s | 148 kata untuk jatah 75 → diperbaiki pemicu per-bagian dua-arah (132→65 kata, jatah 64) |
| Uji otomatis | **447 lulus** |
| Audit wiring DB→BE→FE | 11 tabel · 65 kolom diperiksa satu per satu |

### MASIH TERBUKA (jujur — jangan diklaim tuntas)

1. **Verifikasi pada model llama tertunda** — kuota harian Groq tingkat gratis habis (TPD 100rb).
   Model lemah = kasus terburuk dan justru paling menguji mekanisme per-bagian.
2. **Belum di-deploy.** Migrasi **0187 (ratio 1)** dan **0188 (31 kenop)** SENGAJA belum diterapkan:
   0187 mengubah perilaku produksi, 0188 akan memunculkan 31 baris mentah di panel admin yang LIVE.
   Keduanya menyala bersama deploy. 0185/0186 sudah diterapkan (tak terlihat kode server).
3. **Video Regular (2–12 menit)**: butuh pemotongan+penyambungan suara untuk naskah 1.000+ kata.
4. **Mutu naskah belum punya alat ukur** yang tumbuh bersama ratusan niche. Kandidat satu-satunya =
   retensi penonton (222 kurva + 11.261 baris), belum tersambung ke pembuatan naskah. **Ini MOAT
   produk** (DESAIN §8 killer feature #1), bukan pekerjaan sisa.
5. **5 dari 6 kunci OpenAI habis kredit tapi berstatus 'valid'** di layar — validasi hanya terjadi
   saat kunci dipasang.
6. 20 suara ElevenLabs/fal lain belum diukur (biaya vendor); memakai angka bawaan sampai dipakai.

### JANGAN DIULANG (tertutup dengan bukti)

- Memperbaiki susunan prompt untuk mengejar durasi — 83 naskah berpasangan.
- Kecepatan suara sebagai tuas durasi — dilarang owner, dan terbukti tak menghasilkan durasi.
- Kode memangkas kalimat — membuang fakta.
- Kalibrasi koefisien PER-NICHE — diuji, TIDAK menang (sel terlalu tipis).
- Biaya jeda dari regresi — lihat tabel angka di atas.
- Mencabut separuh rantai (yang MENULIS saja, bukan yang MEMBACA) — itu yang membuat tuas kecepatan
  hidup sepuluh hari setelah "dicabut".

### PETA KODE (grep ulang sebelum dipakai)

`duration_model.py` alat ukur+batas+resep+vonis · `pause_probe.py` ukur biaya jeda (2 cara) ·
`voice_delivery.py` rasio laju lintas-penyedia · `pace_calibration.py` kalibrasi dua-tahap ·
`ambang.py` semua kenop dari DB · `script_checker.py` cacat mekanis · `script_engine.py`
resep→prompt→per-bagian→perbaikan→cacat→satu-perhitungan-akhir · `tts_engine.py` batas waktu +
penjaga terpotong · `pipeline.py` gerbang + QC · migrasi `0182`–`0188`.

---
## 3. ARSITEKTUR QC v2 (spec-aware, relatif, berlapis) — ✅ TERPASANG (desain 2026-06-13 → live sejak 2026-06-16; kondisi kode = §2)

QC menjadi **3 lapis**, semua ambang config-driven, ambang relatif diturunkan dari **Duration Preset × Format Profile** run tsb.

### Lapis 1 — Integritas render ("file-nya rusak/kosong tidak?")
- size > `QC_MIN_SIZE_KB` (kecil, anti file-kosong)
- ffprobe: **ada stream video DAN audio**
- durasi > floor integritas kecil (≈3s) — deteksi render terpotong-total
- **(baru)** codec/container valid, tak ada error decode

### Lapis 2 — Konformitas ke PRESET ("sesuai NIAT produksi?")
- 🔴 **DIGANTI keputusan owner 2026-07-29 — batas PERSEN dicabut, pakai TITIK-TENGAH antar-preset:** hasil sah selama masih lebih dekat ke preset yang dipilih daripada ke preset tetangganya. Preset 45 sah 37,5–52,5 dtk (contoh owner: 45→32 = mulai masalah karena sudah milik 30; 45→29 = masalah besar). Preset pertama tak berbatas bawah; preset terakhir dicerminkan dari jarak tetangga bawahnya. **Keunggulan: batasnya lahir dari tangga preset itu sendiri, bukan angka karangan** — dan otomatis melebar bila tangga dirampingkan (membuang preset 75 → batas 60 jadi 52,5–75 dan 90 jadi 75–105). Status: **KEPUTUSAN, belum diterapkan di kode.**
- ~~`|durasi_aktual − target_preset| / target_preset ≤ QC_DURATION_TOLERANCE` (mis. 0.20)~~ *(nilai berjalan 0.15; inilah yang meloloskan video 90 dtk keluar 74 dtk sambil melapor "berhasil")*
  → preset 15s lolos ~12–18s; preset 60s lolos ~48–72s. **Tanpa floor absolut.**
- **aspect ratio == target** (9:16 untuk Shorts/Reels/TikTok)
- `clip_count == expected_beats(preset)` — semua visual beat preset berhasil (bukan hardcode 6)

### Lapis 3 — Batas platform ("sah untuk platform tujuan?")
- durasi ≤ `platform_max` per-platform (YouTube Shorts ≤180s, dst — config-driven)
- resolusi/fps sesuai spek platform

### Di LUAR QC (tetap di hulu)
- Kualitas naratif (hook/retensi/emosi/CTA) = **ScriptAnalyzer ≥80** (STEP 3). QC tak menilai ini.

### Sumber `target_preset` & `expected_beats` (kondisi nyata)
Dari **`channels.duration_preset`** (per-CHANNEL, migr 0012 — bukan di `tenant_configs`) → detail preset dari tabel `duration_presets` (`seconds`/`visual_beats`/`beats`/`render_mode`/`trailing_silence_override`, admin-editable di Catalog). Mekanisme multi-format = `MULTI_FORMAT_STUDIO.md §3`. Channel tanpa preset (NULL) → jalur legacy interim §2.

### Kebijakan QC-fail (DIPUTUSKAN owner 2026-06-16 → **DIREVISI ke OPSI C 2026-06-17**)
- **Tinjau di DOMAIN KITA + approve, BUKAN buang & BUKAN auto-upload ke YouTube (OPSI C, owner 2026-06-17).** QC-fail (video jadi) → video **tetap di buffer S3** dengan status **`ready_with_issues`** + diagnosa tersimpan → tenant **tinjau dari dashboard (preview dari S3)** + **advisory** (alasan + rekomendasi, via Telegram/FE) → **tenant putuskan**: **Pakai** (kita publish, **kuota−1**) / **Buang** (hapus S3) / diabaikan (TTL → auto-buang). **YouTube TIDAK PERNAH menerima video bermasalah tanpa persetujuan ber-kuota** → flip-di-Studio mustahil, kuota tak bisa diakali. *(Mengganti hapus-video `pipeline.py:317` DAN superseding "upload-private-ke-YouTube" Opsi A.)*
- Bila penyebab transient terukur → boleh **re-generate terarah** (mis. via tombol produksi-langsung pasca-perbaikan), bukan loop bakar-kredit. *(Contoh lama "fallback TTS bikin durasi meleset" sudah tidak mungkin — TTS kini NO-FALLBACK.)*
- Catat **alasan terstruktur** (lapis+metrik) ke `pipeline_run_logs` untuk feedback ke §4.
- **Integrasi alur §12c — OPSI C (owner-confirmed 2026-06-17, MENGGANTIKAN Opsi A).** Producer **HANYA stok** ke buffer: QC-pass→`ready`; QC-fail-ada-video→**`ready_with_issues`** (+metadata issue/koreksi); crash-tanpa-video→`failed`. **Producer TIDAK memanggil `publish()`/Telegram** → mengembalikan invariant §12c yang dilanggar Opsi A. **`ready` + `ready_with_issues` SAMA-SAMA dihitung stok → REM ALAMI** (buffer penuh ⇒ producer berhenti; menutup runaway). Publisher saat slot **hanya auto-publish `ready`** (kuota−1, lapor sukses saat publish); `ready_with_issues` **tak pernah auto-tayang** → ditinjau tenant (approve=publish+kuota / buang / TTL). Hard-fail beruntun (N, config) → **circuit-breaker**: pause channel + **alarm Telegram SEKETIKA**; auto-recover saat 1 produce sukses (mis. via direct pasca-perbaikan). **Alasan ganti dari Opsi A:** Opsi A meng-upload video bermasalah privat ke YouTube DARI producer → (1) melanggar decouple, (2) banjir upload off-schedule saat loop, (3) lubang cheat flip-di-Studio (di luar kendali kita). **Opsi C menutup ketiganya di sumber + otomatis menyetop runaway** (insiden 2026-06-17). *(Alternatif "upload-private ke YouTube" = Opsi A, ditolak; "lewat buffer + publisher force-private di slot" juga ditolak.)*

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

### Kondisi nyata (SINKRON KODE 2026-07-16 — kondisi 2026-06-13 di bawah ini SUDAH BERUBAH TOTAL)
- ✅ **TTS kini NO-FALLBACK (F1-05, verified `tts_engine.py`):** HANYA provider terkonfigurasi channel; gagal = **gagal jujur** (log + run gagal), TIDAK pindah diam-diam ke edge. Field `tts_fallback_provider` **SUDAH TIDAK ADA di kode**. Klaim lama "TTS fallback SILENT" = sejarah (memicu insiden runaway 2026-06-17), bukan kondisi sekarang.
- ✅ **Visual = GENERATOR AI saja, NO-FALLBACK** (sejak 2026-06-24, Pexels dibuang): gagal → `[]` → pipeline raise → notify → retry. Konsisten dgn TTS: **kedua komponen kini gagal-jujur** — prinsip "nol degradasi senyap" terpenuhi via TIDAK ADA degradasi sama sekali.
- **Konsekuensi utk roadmap F7:** checkbox "izinkan fallback" (model B di bawah) = fitur OPT-IN masa depan (bila owner mau menawarkan mode hemat), BUKAN perbaikan kondisi sekarang. Model A (transparansi) tetap prinsip wajib bila fallback pernah diaktifkan.
- Rekonsiliasi akurasi caption edge (~80% vs klaim 95%) masih terbuka (§6).

### Model: dua sumbu, JANGAN disatukan jadi satu toggle
**A) Transparansi — WAJIB di KEDUA mode (tak bisa di-opt-out):**
- Fallback aktif → **notifikasi tenant** (Telegram — `telegram_notifier` sudah ada) + **flag output** di `content_inventory.metadata` (`fallback_used=true`, `provider_used`, `quality_note`).
- Flag ini = **sinyal QC** → tampil di dashboard + (idealnya) tercatat di QC akhir. Tidak pernah senyap.

**B) Lanjut-vs-stop — INI yang jadi checkbox per-komponen (frontend):**
- ☑ **Izinkan fallback** → produksi lanjut pakai cadangan (tenant terima konsekuensi yang dijelaskan eksplisit).
- ☐ **Tidak diizinkan** → komponen utama gagal → **item DIHENTIKAN** (status blocked) + **alert keras** ("kredit ElevenLabs habis — inject sekarang"). Tak ada konten turun-kualitas tayang. Terhubung ke **monitor kredit BYOK**.

### Tier fallback (STATUS NYATA 2026-07-16: keduanya NO-FALLBACK — tabel = desain F7 bila opt-in dibuka)
| Komponen | Kondisi SEKARANG | Bila F7 opt-in dibuka kelak |
|---|---|---|
| TTS | **NO-FALLBACK** (F1-05) — gagal jujur | rantai izin-tenant ke edge = degradasi wajar (caption ~80%) |
| Visual | **NO-FALLBACK** (Pexels dibuang 2026-06-24) — gagal jujur | ❌ tetap tanpa cadangan (kualitas visual = nilai jual) |

### Default & teknis
- **Default TERPASANG = keputusan owner §6.5: stop/gagal-jujur** untuk SEMUA komponen (sudah kondisi nyata, bukan rencana).
- **Pendaratan F7 (bila dibuka):** config boolean allow per-komponen + **frontend checkbox + penjelasan konsekuensi**; wiring `telegram_notifier`; flag `content_inventory.metadata`. *(Field `tts_fallback_provider` lama sudah dibuang — rancang ulang saat F7 dikerjakan.)*

---

## 5. Roadmap QC (penomoran "QC-F"; lihat catatan kepala dokumen — BEDA dari Program Durasi F1–F5)

- **QC-F0 ✅ DONE:** QC interim aman (floor 3s) — tak memblokir preset; produksi aktif tetap terlindungi.
- **QC-F1 ✅ DONE (2026-06-14):** katalog **`format_profiles`** (WPS per-format §4: energik/listicle 2.4, edukasi 2.2, motivasi 1.6 + section_template/cta/render) + **`duration_presets`** (8/15/30/45/60/75/90s + visual_beats §3) + field `channels.duration_preset`/`format_profile` (NULLABLE = non-breaking). Migr `0012`, public-read, tervalidasi v2. Prasyarat QC v2 & multi-format. *(field di channels, bukan tenant_configs — per-channel, selaras niche/content_language.)*
- **QC-F2 ✅ DONE (2026-06-16 dikonfirmasi):** **QC v2 Lapis 1–3 SUDAH diterapkan** di `_pre_publish_qc`. Lapis-1/3 integritas (stream video+audio + aspect 9:16). **Lapis-2 konformitas-durasi-relatif AKTIF**: `|durasi−target_preset|/target_preset ≤ QC_DURATION_TOLERANCE` (env `QC_DURATION_TOLERANCE` default **0.15**; anchor baris historis — grep ulang bila perlu) + clip_count = visual_beats preset. `target_preset` dari `channels.duration_preset` (F1). Terbukti di test ryan (43s vs 60s ditolak, "di luar ±15%"). *(Catatan lama "sisa = akurasi durasi" → SUDAH TUNTAS via PROGRAM DURASI F1–F5, lihat banner.)*
- **QC-F3 (roadmap):** Kebijakan **quarantine + re-generate terarah** (ganti buang-buta) + diagnosa terstruktur ke `pipeline_run_logs`.
- **QC-F4 (roadmap):** **Self-critic pra-submit** (review render: caption-sync, keterbacaan, brand-safety).
- **QC-F5 (roadmap, SEBAGIAN terwujud):** Loop belajar dari QC-fail → auto-tune word_budget/section_timing per preset; A/B hook/thumbnail. *(Sebagian TERWUJUD via PROGRAM DURASI F5 2026-07-16: word_budget kini swa-kalibrasi [pace voice×niche + α + bobot-beat dinamis-terbatas] — sisa scope: belajar dari alasan QC-fail non-durasi + A/B.)*
- **QC-F6 (roadmap):** Dashboard "robot belajar apa" untuk tenant (transparansi klaim landing).
- **QC-F7 (roadmap, §4b):** **Consent & Transparency Fallback** (TTS+Visual) — notifikasi+flag WAJIB; checkbox lanjut-vs-stop per-komponen; tier (black-screen selalu stop); alert "inject kredit". Rekonsiliasi dulu angka akurasi edge_tts (95% vs 80%).

> Urutan & detail tiap fase **diputuskan bersama owner** sebelum koding (propose-first).

---

## 5b. PARAMETER DURASI & QC — LOKASI KONTROL (verified codebase 2026-07-16; NOL hardcode nilai bisnis)
Semua parameter dikontrol via ADMIN PANEL atau ENV — tidak ada nilai bisnis yang terkunci di kode.

| Parameter | Dikontrol di | Sumber teknis |
|---|---|---|
| Preset durasi (8–90s), aktif/nonaktif, segmentasi beat, jumlah gambar, use-case | **ADMIN** (Catalog) | tabel `duration_presets` |
| `render_mode` per-preset (image_seq / ai_video) | **ADMIN** (Catalog) | `duration_presets.render_mode` |
| Jeda-akhir KHUSUS per-preset (mis. 8s=1.0s) | **ADMIN** (Catalog) | `duration_presets.trailing_silence_override` |
| Kecepatan bicara per-suara (`delivery_wps`) + rentang speed | **ADMIN** (Catalog) | `voice_catalog` / `tts_profiles.param_schema` |
| Model/suara/niche/kualitas per-channel | **tenant/admin** | tabel `channels` |
| Toleransi durasi lolos/gagal (0.15) | **ENV** `QC_DURATION_TOLERANCE` | `pipeline.py` (gate pra-visual & pre-publish) |
| Pagar-pengaman gerbang pra-visual (2.0× tol = ±30%; near-miss lanjut, hanya PARAH di-stop) | **ENV** `QC_DURATION_GROSS_FACTOR` | `pipeline.py` gate pra-visual (owner 2026-07-15) |
| Toleransi panjang naskah (0.12) — SATU-SUMBER utk prompt (rentang total, MIN/MAX per-beat) + gerbang internal `length_ok`; dipagari terkode `min(·, QC_DURATION_TOLERANCE)` | **ENV** `SCRIPT_LENGTH_TOLERANCE` — ✅ HIDUP sejak F3 2026-07-16 (dulu config-mati; 6 angka terpatri ±10%/−8+12%/+15% DIBUANG) | `script_engine._script_len_tol()` |
| Batas regang suara/atempo (0.80–1.35) | **ENV** `TTS_ATEMPO_MIN/MAX` | `tts_engine._fit_duration` |
| Jeda-akhir per-run (rantai KOHEREN 4 titik: naskah·korektor·gerbang·renderer) | **tenant/admin** (`tenant_configs.trailing_silence` → override per-preset admin) | `format_catalog.effective_trailing` — sejak DURASI-3 2026-07-16 pipeline STEP 5 kirim `trailing_secs` ke `_fit_duration`; env di bawah tinggal fallback non-preset |
| Jeda-akhir fallback global (1.5s — HANYA run tanpa preset) | **ENV** `RENDER_TRAILING_SILENCE` | `tts_engine._fit_duration` (bila `trailing_secs` tak dikirim) |
| Integritas render (ukuran/durasi/klip/audio/aspek min) | **ENV** `QC_MIN_SIZE_MB`·`QC_MIN_DURATION`·`QC_MAX_DURATION`·`QC_MIN_CLIPS`·`QC_REQUIRE_AUDIO`·`QC_ASPECT`·`QC_ASPECT_TOLERANCE` | `pipeline._pre_publish_qc` |
| **Instrumen durasi (F1, baca-saja)** — taksiran vs aktual + kata per-beat per render | **otomatis** (tiap render TTS sukses) | `tts_delivery_samples.{predicted_secs, raw_audio_secs, target_secs, pause_secs, pause_counts, beat_words}` (migr 0162+0165; `tts_engine._log_delivery_sample`, fail-soft, nol waktu tambahan) |
| **Pace terkalibrasi (voice×niche) + α respons-speed provider** | **otomatis** (F5 swa-kalibrasi harian; `voice_catalog.pace_locked` = veto admin per-voice) | `tts_pace_calibration` + `tts_speed_response` (migr 0163/0164; penulis TUNGGAL `pace_calibration.py`; kosong → lapisan admin/provider) |
| **Bobot antar-adegan** (porsi kata narasi, GLOBAL) | **ADMIN** (Catalog > Durasi: bobot + kunci 🔒 + pratinjau porsi) + **otomatis** (F5 selaras berkala ±20%/siklus; `weight_locked` = veto admin per-beat) | `content_beats.weight`/`weight_locked` (migr 0165); API `/api/admin/beats` (pagar bulat 1–30) |
| Ambang swa-pemeliharaan F5 (min-sampel kalibrasi/align, langkah maks, jendela+ambang alarm drift) | **ENV** `PACE_CALIB_*` · `BEAT_ALIGN_*` · `DRIFT_*` | `pace_calibration.py` (nilai = default kode, berkomentar di `.env`) |

> ✅ **Utang F3 LUNAS (2026-07-16):** toleransi internal `script_engine` kini SATU-SUMBER `SCRIPT_LENGTH_TOLERANCE` via `_script_len_tol()` (dipagari `min(·, QC_DURATION_TOLERANCE)`); 6 angka terpatri lama (prompt ±10%/−8+12%/beat +15%/gerbang ±10%) sudah DIBUANG.

> **Catatan:** semua variabel ENV di atas kini **tertulis eksplisit + berkomentar di `.env`** (nilai = default kode; 2026-07-15). Ambang QC sengaja di ENV (platform-wide, bukan per-tenant). *(Belum ada di admin panel — bila ingin diatur dari layar admin, itu item terpisah menunggu ketok owner.)*

## 6. Keputusan (2026-06-13, expert) + yang masih perlu data
**DIPUTUSKAN** (owner delegasi keputusan teknis — [[feedback_owner_delegates_expert_decisions]]):
1. `QC_DURATION_TOLERANCE` = **0.15 (15%)** — kini di ENV berkomentar (lihat §5b; anchor lama `pipeline.py:562` BASI — nilai dibaca di gate pra-visual & `_pre_publish_qc`, grep ulang). *(toleransi BUKAN lever; akar durasi diperbaiki di §2/root-cause, bukan dilonggarkan.)*
2. **QC-fail durasi → REVIEW-IN-DOMAIN + APPROVE (OPSI C, owner 2026-06-17; supersede "publish-private" 2026-06-16)**, **bukan dibuang**. Video bermasalah **tetap di buffer S3** (`ready_with_issues`) → tenant **tinjau dari dashboard** + **advisory (alasan + rekomendasi)** → **tenant putuskan** Pakai (publish, kuota−1) / Buang / TTL. **TIDAK auto-upload ke YouTube** (tutup cheat flip-Studio + off-schedule). Retry/regenerate = §3/F3 + **direct** pasca-perbaikan (bukan loop bakar-kredit). **Integrasi alur §12c = OPSI C** (producer hanya stok; publisher hanya publish `ready`; issue ditinjau di domain kita — lihat §3).
3. Self-critic = **heuristik dulu**; LLM-vision ditunda (biaya × ribuan tenant).
4. Prioritas = **G-final integritas dulu (✅ DONE)** → QC-relatif nyusul bersama field Preset (F1).
5. Default fallback = **stop/gagal-jujur** — dan sejak F1-05 ini **kondisi terpasang** utk TTS & Visual (NO-FALLBACK, §4b). "TTS premium→edge bila tenant izinkan" = fitur opt-in masa depan (roadmap QC-F7), BUKAN perilaku sekarang.

**Status "perlu data" (update 2026-07-16):**
- ✅ **Kalibrasi pace per-provider/voice/niche + loop audio — SELESAI** (Program Durasi F1–F5: instrumen `tts_delivery_samples` + `tts_pace_calibration`/`tts_speed_response` + swa-kalibrasi harian + atempo closed-loop overhead-penuh). Datanya kini mengalir sendiri dari tiap render.
- ⬜ Rekonsiliasi akurasi caption edge_tts (klaim 95% vs label 80%) — masih terbuka, kecil, non-blocking.

---

## 7. Alur Produksi & Antrian Publish (lifecycle — ACUAN OPERASIONAL)
*(2026-06-28 — agar tim paham persis "apa yang terjadi" di produksi & antrian. Mesin = `mv-worker`, loop konkuren BUKAN cron: Producer + Publisher + Janitor + self_learning.)*

1. **PRODUKSI (Producer, OPSI C):** jaga stok buffer per-channel (`buffer_depth=2`). Hasil → `content_inventory`:
   - QC-pass → **`ready`** (siap tayang) · QC-fail-tapi-video-jadi → **`ready_with_issues`** (perlu ditinjau) · crash-tanpa-video → **`failed`**.
   - Producer **TIDAK pernah publish** (decouple §12c). `ready`+`ready_with_issues` dihitung stok = **rem alami** (buffer penuh → producer berhenti = anti-runaway).
2. **PUBLISH (Publisher, cek tiap 30s):** saat `publish_slot` channel jatuh tempo (zona tenant, jendela 90s) → **`claim_oldest_ready` = FIFO by `created_at`** (TERTUA dulu) → upload YouTube → `mark_published` + hapus S3 + update `production_runs` (status=`success`, youtube_url). **Kuota −1 saat publish.** Hanya `ready` yang auto-tayang.
   - ⚠️ **FIX 2026-06-28:** dulu order by `produced_at`/`target_slot` (keduanya NULL → urutan ACAK → konten lama terlewat/basi). `mark_ready` kini isi `produced_at` + FIFO by `created_at`.
3. **REVIEW (`ready_with_issues`):** tenant tinjau di `/review` (preview S3) → **Pakai** (promote→ready→publish, kuota−1) / **Buang** (`discard_inventory_item` → juga set `production_runs`=`discarded` agar sinyal "perlu ditinjau" padam) / diabaikan→TTL auto-buang.
   - ⚠️ **FIX 2026-06-28:** reject dulu tak update `production_runs` → sinyal "perlu ditinjau" menggantung di banyak layar. Kini tutup loop (simetris dgn approve yg di-tutup publisher).
4. **TTL / KESEGARAN (Janitor `sweep_stale`):** `ready`=**72 jam** (`BUFFER_TTL_HOURS`; diperpendek 168→72 2026-06-28 = penjaga kesegaran tren) · `ready_with_issues`=72j (`ISSUE_REVIEW_TTL_HOURS`) · `failed`=24j. Lewat `expires_at` → janitor hapus S3+baris. Operasi normal (FIFO + buffer dangkal) → tayang ~1 hari, jarang kena TTL; TTL = jaring pengaman "**takkan publish konten basi >3 hari**".
5. **STATUS di FE (penting — beda sumber):**
   - **Runs/Produksi** = ledger `production_runs` (TERMINAL): `success`→Completed · `qc_failed`→Perlu Ditinjau · `discarded`→Dibuang · `failed`→Failed. (Bukan live/FIFO. Tak ada state "running"/"queued" di production_runs.)
   - Tab **"Menunggu publish"** = `content_inventory.ready` (urut FIFO + tombol Pratinjau).
   - **"Perlu ditinjau" (aksi) = `content_inventory.ready_with_issues`** (antrean LIVE), BUKAN `production_runs.qc_failed` (ledger historis — itu sebab "/review kosong tapi sinyal nyala" sebelum fix).
6. **Viral score:** skala **0-100** (ScriptAnalyzer). Boost `historical_factor`/`signal_factor` **di-clamp ≤100** (fix 2026-06-28; dulu bisa tembus 102,7).

**Kebijakan kesegaran (rekomendasi 2026-06-28):** TTL per-niche (tren pendek vs evergreen panjang) = refinement Pro/Business, **DITUNDA** (channel baru prioritas konsistensi, bukan kejar-tren detik). Tombol **"Buang" di antrean publish** (tenant kontrol konten basi) = next-step.

---

### Changelog
- **2026-07-16 (2) — SINKRONISASI PENUH dokumen ↔ codebase (mandat owner: single source of truth, nol ambigu).** §0.4 prinsip diluruskan (GAGAL-JUJUR/no-fallback = kondisi terpasang; "fail-soft" hanya utk komponen observasi) · §1 tabel rantai disinkron (TTS NO-FALLBACK + instrumen; clip = visual_beats; QC v2 relatif) · §2 ditulis ulang sesuai kode (dua mode QC; size sadar-durasi; gerbang pra-visual overhead-penuh; SEMUA masalah lama ✅ tertutup; root-cause 2026-06 → ARSIP) · §3 dicap TERPASANG + sumber preset dikoreksi (channels.duration_preset, bukan 'belum ada field') · §4b kondisi nyata NO-FALLBACK kedua komponen (field tts_fallback_provider sudah tiada; checkbox = opt-in masa depan QC-F7) · §5 penomoran QC-F dipertegas (catatan kepala dokumen: 3 penomoran fase berbeda) · §5b +baris kalibrasi/bobot-beat/ambang-F5; utang-F3 dicap LUNAS · §6 'perlu data' kalibrasi pace → SELESAI. Form bobot-beat admin (Catalog>Durasi) DEPLOYED FE `4bf98cf` situs 200.
- **2026-07-29 — RISET DURASI: jalur PROMPT DITUTUP DENGAN BUKTI; klaim ✅ lama DICABUT (§2c).** 83 naskah lewat jalur prompt produksi (7 preset × 3 model × 3 niche, Latin, berpasangan), audio diukur nyata (Edge, gratis), skor mutu dinilai; biaya ±Rp 2.900. **Terukur:** (1) sisi suara bukan masalah — `audio = 0,61 × kata^0,95` R²=0,98 ±8%; (2) LLM tidak menuruti jumlah kata dan berpola `kata = a × pesanan^b`, b=0,24–0,70 → pesanan kecil dilampaui, pesanan besar tidak tercapai (SATU sebab untuk dua gejala yang selama ini dikejar terpisah); (3) **memperbaiki prompt tidak bisa menyelesaikan** — membuang pengikat angka F3 menaikkan mutu hanya +0,7 dari 84 tapi menurunkan yang lolos 24%→17%; (4) goyangan model ±12–17% > toleransi preset panjang ±8% → sekali-tulis mustahil andal; (5) mutu isi TIDAK dikorbankan kendali durasi (83,9 vs 84,6); (6) pilihan MODEL lebih menentukan daripada prompt (gemini-2.5-flash unggul mutu DAN kendali); (7) preset 8 dtk gagal di ketiga model karena KELEBIHAN; (8) preset 75 dtk paling rapuh. **Dicabut:** klaim 17-Jun 'akar = prompting' (akar benar sudah tertulis 16-Jun lalu ditimpa, tak pernah diperbaiki); status 'PROGRAM DURASI SEMUANYA ✅ LIVE' (kodenya ter-deploy, DONE-BILA-nya tidak pernah dipenuhi — produksi 30 hari: 60s −5,5 dtk · 90s −14,2 dtk · 36 dari 110 di luar ±15%); toleransi persen (diganti aturan TITIK-TENGAH antar-preset, keputusan owner). **BELUM TERBUKTI (jangan bangun di atasnya):** pace 2,585 vs 2,05 hasil ukur, dan apakah tuas kecepatan benar-benar sampai ke pembuat suara. **Nol kode produksi disentuh.**
- **2026-07-16 — PROGRAM DURASI 5-FASE dimulai; F1+korektor DEPLOYED (`fe83d28`+`a4ea83e`, deploy_be OK health=200; izin eksplisit owner).** (1) **F1 instrumen**: migr 0162 +5 kolom nullable `tts_delivery_samples` (taksiran vs aktual + jeda + mentah-pra-atempo); nol ffprobe/waktu tambahan (durasi mentah diukur 1×, dipakai-ulang `_fit_duration`). (2) **Backfill mining `worker.log`** (16-Jun→16-Jul): 78/112 baris lama terisi (0 ambigu; md5 kolom lama identik) → error taksiran per-niche kini TERUKUR (ocean 3% · dark 6% · legenda ~10% · radiant ~12% · fun_facts ~20%). (3) **DURASI-3 korektor**: trailing atempo SATU rumus per-preset dgn naskah/gerbang/renderer (dulu env global → 8s diperas 7.0→6.5s). (4) **Root-cause DISEMPURNAKAN** dari data: biang dominan = pace per (voice×gaya-DNA-niche), bukan estimator global (delivery_wps provider akurat <1%); dark_history (pace pas) = 86% dalam ±15% = patokan DONE. (5) Batch `d27273b` 2026-07-15 ikut terangkat (near-miss→review · pesan manusiawi · prompt Lapis-1). Sisa: F2 kalibrasi → F3 prompt+toleransi-1-sumber → F4 jalur DNA → F5 swa-kalibrasi+alarm (tracker `SISA_KERJA [C1]`). **Insiden dihindari**: `SUPABASE-CONNECTION.md` berisi URI v1+v2 → nyaris ALTER di DB v1; kini guard identitas DB wajib sebelum tulis.
- **2026-07-15 — perbaikan durasi 3-serangkai (commit `d27273b`; keputusan owner; lokal-teruji; ✅ DEPLOYED 2026-07-16).** (1) Gerbang durasi pra-visual: near-miss TIDAK lagi dibunuh → lanjut produksi → OPSI C review; hanya meleset PARAH (`QC_DURATION_GROSS_FACTOR` ±30%) di-stop (hemat render naskah rusak). (2) `notify_qc_fail` dimanusiakan (`_humanize_qc_reason`; nada "menunggu keputusan Anda", nol jargon/"GAGAL"). (3) Prompt `_build_user_prompt`: cabut pintu-kabur speed + target STRUKTUR (kalimat) + preset-aware (Lapis-1 root-cause). Param baru `QC_DURATION_GROSS_FACTOR` di `.env` berkomentar. Uji lokal lulus; bukti runtime durasi = pending.
- 2026-07-10 (3) — **Notif Telegram jalur terjadwal + header circuit-break** (mandat owner; commit `c6f3161`, 2 pesan uji nyata terkirim ✓): (a) `notify_review_pending` — video masuk antrean Review kini MEMBERI TAHU tenant (judul + catatan QC + saran + arahan Pakai/Buang + peringatan TTL hangus + link /review; chat/toggle per-tenant, TTL & URL config-driven) — menutup celah "video menunggu senyap → TTL → biaya hangus tanpa tenant tahu"; (b) header `notify_circuit_break` seragam `[nama channel]` (dulu UUID mentah).
- 2026-07-10 (2) — **Pintu ke-3 sinyal tinjau DITUTUP** (mandat eksplisit owner; commit `38fe43a`, validasi sintetis nyata di VPS): janitor `sweep_stale` kini memadamkan `production_runs.status qc_failed → discarded` saat menyapu item `ready_with_issues` kedaluwarsa TTL — simetri dgn approve (`→success`, RPC) & discard (`→discarded`, RPC). Sebelumnya run item kedaluwarsa = qc_failed ABADI → dashboard/Runs menghitung "perlu ditinjau" utk video yang sudah tak ada, selamanya (bug laten; nol kasus historis saat ditutup).
- 2026-07-10 — **GERBANG DURASI PRA-VISUAL LIVE** (mandat owner; commit `f941579`): proyeksi durasi final = `audio_duration` + `trailing_silence` (sumber SAMA renderer s72b) dicek vs window QC relatif (env `QC_DURATION_TOLERANCE` — identik `_pre_publish_qc`) **sebelum STEP 6** — di luar window → run `failed` jujur SEBELUM biaya gambar AI + render terbakar (dasar owner: salah sistem ≠ rugi tenant; 2 kegagalan nyata 2026-07-09 masing2 membakar 4 gambar + render sia-sia). Tanpa preset → lewat (paritas QC interim). Ini realisasi ide "staged-QC / G-audio" changelog 2026-06-13. Validasi: 7 kasus batas PASS + run produksi nyata `direct-dc87be14` lolos gerbang (proyeksi 60.1s) → QC PASSED → publish privat. **Bersamaan (koherensi tampilan):** `run_metadata.video_title` (judul AKHIR = nama di YouTube) dicatat kedua jalur; FE Runs tampil judul (fallback topik baris lama) + badge "Perlu Ditinjau" menyebut TEMPAT tinjau (direct→YouTube Studio · item live→/review · kedaluwarsa TTL) — menutup insiden bingung 1-video-2-nama 2026-07-10.
- 2026-06-13 — dibuat. Kondisi awal terdokumentasi; QC interim floor 3s; QC v2 + self-improvement roadmap diusulkan (menunggu keputusan owner per §6).
- 2026-06-13 — **§4b Consent & Transparency Fallback** ditambah (disetujui owner): umum TTS+Visual, model A (transparansi wajib) + B (checkbox lanjut-vs-stop), tier black-screen selalu stop, flag→QC. + F7. **Validasi staged-QC** (deviasi durasi nyata 5–31% vs target 51s; risiko regenerate-loop; G-audio feasible krn `target_duration` `script_engine.py:206` + `audio_duration` `pipeline.py:219` sebelum step mahal).
- 2026-06-13 — **Keputusan §6 direkam** (owner delegasi). **Root cause durasi tervalidasi** = WPS 2,4 hardcode ≠ delivery nyata per-provider (1,67–2,41) → folded ke §2. **G-final integritas (Lapis-1/3) DIIMPLEMENTASI + tervalidasi** (`_pre_publish_qc` cek stream audio/video + aspect 9:16, config-driven; klip uji lokal). Fix durasi penuh = blocked data/biaya.
- **2026-06-16 — SINKRON ke realita + keputusan owner (test e2e ryan):** (1) §2 root-cause di-update: **WPS bukan lagi 2.4 hardcode** (F1 per-provider `format_wps`); residual = budget pakai WPS provider terkonfigurasi vs provider AKTUAL fallback (EL 1.8 vs edge 2.6 → 43s/60s). (2) **F2/Lapis-2 durasi-relatif KONFIRMASI SUDAH AKTIF** (`QC_DURATION_TOLERANCE` default 0.15). (3) §6.1 toleransi diselaraskan **20%→15%** (sesuai kode; owner: toleransi bukan lever, WPS yang diperbaiki, **no preset-hack**). (4) §6.2/§3 kebijakan QC-fail → **publish PRIVATE + advisory** (bukan buang). (5) **Isu no-hardcode ditemukan**: `tts_engine` concern-messages **hardcode "ElevenLabs"/"Edge"** + hanya ke log (langgar §0.3) → diperbaiki bareng F7/advisory (eksekusi #2).
- **2026-06-16 (lanjutan) — OPSI A dikunci + plan masuk PROGRESS.** Owner pilih **Opsi A** (AskUserQuestion) utk integrasi QC-fail→publish-private+advisory ke alur decoupled §12c: **uniform di `pipeline.run`** (producer & direct), **buffer tetap murni**, publisher tak berubah, upload-private = artefak advisory out-of-band (invariant §12c terjaga). Ditulis ke §3 & §6.2. **Plan eksekusi (checklist) dipindah ke `PROGRESS.md §IMPROVEMENT — QC Self-Healing + Trend Radar`** (disisip sebelum §GATE CUTOVER); doc ini tetap = desain/roadmap (F-series), PROGRESS = checklist status. Centang PROGRESS hanya setelah tervalidasi 100%.
- **2026-06-17 — OPSI A → OPSI C (REVISI BESAR, owner; sekaligus penutup INSIDEN RUNAWAY).** Analisa nyata (DB+kode VPS) insiden 2026-06-17: producer loop tanpa rem + Opsi A meng-upload video QC-fail privat ke YouTube DARI producer → 29 produce/23 upload-privat-off-schedule dalam ~45 mnt (root: ElevenLabs lapse→edge fallback→durasi 32–39s<51s; diperparah **tak ada §4b/F7 stop-on-fail** + Opsi A langgar decouple). **Keputusan owner: ganti ke OPSI C** — producer **hanya stok** (`ready`/`ready_with_issues`/`failed`, dua pertama dihitung stok = **rem alami**); publisher **hanya auto-publish `ready`** (kuota saat publish); video bermasalah **ditinjau di dashboard (preview S3), approve→publish+kuota / buang / TTL**, **TIDAK auto ke YouTube** (tutup cheat flip-Studio + off-schedule di sumber); hard-fail beruntun → **circuit-breaker pause+alarm seketika**. **Kuota = video yang KITA UPLOAD/jadi-publik per hari** (titik yang kita kuasai). **Otomatis menyetop runaway ryan.** Plan eksekusi = `PROGRESS.md §PERBAIKAN ARSITEKTUR PRODUKSI v2 (OPSI C)`.
- **2026-06-28 — §7 Alur Produksi & Antrian (acuan operasional) DITAMBAH + 4 fix produksi/antrian** (batch lokal saat dicatat; ✅ deployed & verified 2026-07-01): (1) **FIFO sungguhan** — `mark_ready` isi `produced_at` (dulu di-pop tanpa pengganti = selalu NULL) + `claim_oldest_ready` urut `created_at` (dulu order by NULL → acak → konten lama basi terlewat). (2) **Reject tutup loop** — `discard_inventory_item` set `production_runs`=`discarded` (dulu hanya content_inventory → sinyal "perlu ditinjau" menggantung; akar: production_runs.qc_failed ledger ≠ content_inventory.ready_with_issues antrean-live). (3) **TTL 'ready' 168→72 jam** (penjaga kesegaran tren). (4) **Viral score clamp ≤100** (boost historical/signal dulu tembus 102,7; formula dasar 0-100 BENAR). FE: tab Runs "Running" dibuang + "Queued"→"Menunggu publish" (content_inventory.ready, kolom Durasi/Skor/Grade + Pratinjau). Lihat [[project_self_learning_remediation_2026_06_28]] / progress_journal.
