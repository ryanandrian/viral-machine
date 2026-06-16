# TREND RADAR ARCHITECTURE — MesinViral v2

> **Living document.** Tujuan: Trend Radar **terbaik** yang menghasilkan Shorts **benar-benar viral**, **skalabel ribuan tenant**, dengan **self-learning & self-improvement** nyata (bukan klaim). Semua angka/sumber/bobot **config-driven, no-hardcode** ([[feedback_no_hardcode]]). Status LIVE per-fase = `PROGRESS.md`. Saudara dokumen: `QC_CONTENT_ARCHITECTURE.md` (kualitas file), `MULTI_FORMAT_STUDIO.md` (preset/format).
>
> **Aturan dokumen ini:** tiap perubahan trend-radar/seleksi-topik lewat sini dulu (propose → approve → implement). **Hanya item yang sudah DIVALIDASI nyata yang masuk arsitektur** (lihat §2).

---

## 0. Prinsip
1. **Viral-first:** sinyal yang dipilih harus prediktif untuk Shorts (spike/momentum, format terbukti, relevansi niche) — bukan sekadar "ramai global".
2. **Relevan-niche:** setiap sumber harus berkontribusi sinyal **sesuai niche channel**; sumber yang jadi noise dibuang/difilter.
3. **Skalabel (tenant-independen):** beban ke sumber eksternal **tidak boleh** tumbuh seiring jumlah tenant. (lihat §3 Pilar-1)
4. **Ukur, jangan menebak:** dimensi viral dihitung dari **angka nyata** sebisa mungkin; LLM untuk meramu angle, bukan mengarang metrik.
5. **Self-improving terukur:** hasil nyata (analytics) mengalir balik menaikkan seleksi berikutnya.
6. **No-hardcode:** sumber, bobot, TTL, keyword/subreddit, threshold = DB/config; nol nama vendor/angka tertanam.

---

## 1. Kondisi sekarang (kode nyata)
`src/intelligence/trend_radar.py` → 5 sumber, fetch **per-produce**, regional (`peak_region`), keyword per-niche. Output sinyal mentah → `niche_selector`:
- **Seleksi (`niche_selector`):** LLM **buat kandidat topik + skor 5 dimensi (0–100)** dari ringkasan teks → `_calculate_viral_score` (`VIRAL_SCORE_WEIGHTS`, **di-blend bobot hasil-belajar channel** bila ≥20 video) → `historical_factor` (performa channel) → ranking.
- **Sudah ada (bagus):** pembobotan objektif + **self-learning weights per-channel** + faktor performa historis.

### Masalah (terverifikasi)
| # | Masalah | Bukti |
|---|---|---|
| M1 | **Scaling 429 (IP-based, fetch per-produce)** | `_get_google_trends` via pytrends; 429 di run nyata. Banyak tenant 1 IP VPS → blokir. |
| M2 | **2/5 sumber noise non-niche** | `_get_hackernews_trending` (tech-bias) & `_get_wikipedia_trending` (top global) **tak difilter niche**. |
| M3 | **Dimensi diskor LLM dari teks, bukan angka nyata** | `niche_selector._analyze_with_ai` ("score dimensions 0–100"); `competition_gap` ditebak. |
| M4 | **Sinyal YouTube dangkal + rapuh** | `_get_youtube_trending_search` hanya judul (tanpa viewCount/velocity) + bergantung `youtube_api_key` tenant (kuota habis → 0). |
| M5 | **LLM skoring tiap produce** | biaya + latensi + variasi. |

---

## 2. Validasi sumber (HANYA yang terbukti dipakai)
Diuji nyata 2026-06-16 dari environment ini:

| Sumber | Status validasi | Keputusan |
|---|---|---|
| **Google Trends — interest_over_time** | ✅ jalan (pytrends, gratis, tanpa key) — **kena 429 di IP-share** | **PAKAI + WAJIB cache** (Pilar-1) |
| **Google Trends — related/rising queries** | ✅ **tervalidasi** (25 rising query "space") | **PAKAI** (discovery sub-topik spiking) |
| **Google News RSS** | ✅ reachable (302) | PAKAI (filter niche) |
| **Wikipedia top pageviews** | ✅ reachable (301) | PAKAI **hanya bila difilter niche** |
| **HackerNews** | ✅ reachable (200) | PAKAI **niche-conditional** (tech/science saja) |
| **YouTube Data API** (search + `videos.list?part=statistics`) | ⚠️ valid secara API (viewCount/velocity terdokumentasi) — **butuh kuota** (key tenant tadi habis) | PAKAI dgn **key platform + cache**, bukan andalkan key tenant |
| **Reddit** (`/r/{sub}/.json`) | ❌ **GAGAL**: timeout 000 (semua varian, 20s) dari environment ini **+ API komersial BERBAYAR sejak 2023** (SaaS tak boleh gratis) | **DIKELUARKAN** (bukan sumber gratis valid now/future). Perannya digantikan Trends-rising + YouTube-velocity. *(opsi berbayar masa depan bila perlu — bukan sekarang)* |

**Item arsitektur lain (kelayakan):**
- `trend_cache` (tabel Supabase) — **valid** (pola tabel standar, sudah biasa di proyek).
- **TrendRefresher** (thread paced di `worker_decoupled`) — **valid** (pola thread `run_forever` sudah ada: producer/publisher/janitor/email_outbox/heartbeat).
- Filter-niche HN/Wiki (string/keyword match) — **valid** (trivial).
- Scoring berbasis angka — **valid** (`_calculate_viral_score` + bobot sudah ada; tinggal isi dimensi dari angka).
- Self-learning — **valid & sebagian sudah jalan** (`channel_insights`, learned weights, `historical_factor` — terbukti di run: grade=peak).

### 2b. Efektivitas & RASIO BOBOT sumber (config-driven `source_weights`)
Tidak semua sumber sama bernilai untuk **viralitas Shorts**. Kontribusi tiap sumber **dibobot**, **config-driven** (`app_config.trend_source_weights`, admin-tunable, **dikalibrasi self-improvement §4**). Bobot **default + verdict efektivitas** (jawaban langsung atas "apakah News/Wikipedia/HackerNews benar-benar efektif?"):

| Sumber | Peran | Bobot default | Verdict efektivitas (alasan) |
|---|---|---|---|
| **YouTube velocity** (search + `videos.list` statistics) | **PRIMER** | **~0.45** | **Tertinggi.** Sinyal paling langsung — apa yang **sedang ditonton** di Shorts niche ini = prediktor terkuat. **Diukur** (viewCount + velocity + competition_gap), bukan ditebak. Medan perang sebenarnya. |
| **Google Trends** (interest + rising) | sekunder | ~0.30 | **Tinggi.** Permintaan pencarian + rising query = demand nyata, gratis, niche-keyword. Tapi "dicari" ≠ "ditonton sebagai Shorts" → di bawah YouTube. |
| **Google News** (RSS) | pelengkap | ~0.13 | **MODERAT, niche-dependent.** Berguna utk niche butuh kesegaran/timely (tech, sains terkini, peristiwa) — beri hook aktual. Niche evergreen (ocean/fun_facts) nilai rendah → **flag per-niche**, bukan global. |
| **Wikipedia** (top pageviews) | minor | ~0.07 | **RENDAH / cenderung noise.** Top pageviews global didominasi selebriti/film/peristiwa — jarang relevan niche. **Hanya berguna setelah filter-niche ketat**; bila tak "membayar dirinya" (kontribusi ke avg_view_pct ≈ 0) → **kandidat DROP**. |
| **HackerNews** | kondisional | ~0.05 | **Tech/sains SAJA.** Bias tech/startup. Untuk niche faceless umum (mystery/space/ocean/history/fun) = noise. **Aktif HANYA bila niche di-flag tech/science**; selain itu **skip**. **Kandidat drop** bila katalog niche tak punya niche tech. |

> Bobot = **default awal, bukan final.** **Self-improvement (§4) mengkalibrasi bobot per (niche, geo) dari outcome NYATA** — sumber yang terbukti memprediksi `avg_view_pct` tinggi → bobot naik; yang jadi noise → turun/0 (bisa otomatis men-drop Wiki/HN per-niche). **No-hardcode:** angka di `app_config`, peta sumber↔niche + flag tech di DB (admin-kurasi).

### 2c. Sinyal YouTube yang DIPANEN (inventaris — divalidasi 2026-06-16)
Tiga permukaan data YouTube, dipakai sesuai biaya/akses. **Inilah yang membuat radar tajam (bukan sekadar tren generik).**

**A. Pasar/kompetitor — Data API v3 (key platform, WAJIB di-cache):**
- `videos.list?chart=mostPopular` (region+kategori) — **trending YouTube sendiri**. 1 unit.
- `search.list` (`order=viewCount`, `videoDuration=short`, `publishedAfter`) — riser cepat (velocity). **100 unit (mahal → cache agresif).**
- `videos.list?part=statistics,contentDetails,topicDetails` (batch 50) — viewCount/engagement + durasi + **topik semantik**. 1 unit.
- `commentThreads.list` — komentar penonton → **tambang hook/angle** (pertanyaan & emosi nyata). 1 unit.
- `channels.list?part=statistics` — kekuatan pesaing. 1 unit.
- Kuota **10k unit/hari/project** → ~100 search/hari → cache+refresher (§3) wajib. *(Tags video orang lain & caption-download = tak tersedia non-pemilik.)*

**B. Channel-SENDIRI — Analytics API v2 (OAuth tenant, scope `yt-analytics.readonly` SUDAH ADA — ✅ LIVE-VALIDATED):** *(sumber TERKAYA → bahan bakar self-learning §4)*
- ✅ **Retensi:** `averageViewPercentage` (uji ryan live: **67.72%**), `averageViewDuration`, `estimatedMinutesWatched`.
- ✅ **`insightTrafficSourceType`** (uji ryan live: SHORTS 34k / YT_SEARCH 1.1k / SUBSCRIBER / NOTIFICATION …) → **"apakah ALGORITMA mendorong topik ini"** + asal penonton.
- **CTR** `impressionClickThroughRate` (per-video — sudah di `channel_analytics.py`), **`searchTerms`** (kata kunci yang membawa penonton ke video KITA), **kurva retensi per-detik** (`audienceWatchRatio`) → enrichment (F4).
- ⚠️ `channel_insights.avg_view_pct=0` saat ini = **loop fetch belum dijalankan**, BUKAN tak bisa — kapabilitas **terbukti live**. (Unlock = jalankan loop / gate cutover E3.)

**C. Demand (gratis/murah):**
- **Google Trends `gprop='youtube'`** — tren pencarian KHUSUS di YouTube (beda web search). Fitur pytrends valid (library sama); uji kena **429** → konfirmasi alasan cache wajib.
- **YouTube autocomplete/suggest** — ✅ live-validated (query emergent paling dini); **tak resmi** → pelengkap, bukan tulang punggung.

**Ringkasan validasi (2026-06-16):** B core-metrics + trafficSourceType = **✅ live (data nyata ryan)** · autocomplete = **✅ live** · Trends-youtube = fitur valid, 429 (cache solves) · Data API = valid, quota-limited (terbukti e2e). **Tidak ada klaim yang belum teruji ketersediaannya.**

---

## 3. Arsitektur target

### Pilar 1 — Decoupled + cache + shared  (memecahkan M1 scaling)
**Insight:** data tren itu **per (keyword/niche, geo)** — **bukan per-tenant** — dan berubah lambat. Maka fetch **1× per kombinasi per TTL**, dipakai ulang **semua** tenant.

- **Tabel `trend_cache`**: `cache_key (niche+geo+source+timeframe)`, `signals jsonb`, `fetched_at`, `ttl_sec`. (papan data di Supabase, seperti buffer §12c).
- **TrendRefresher** = thread background di worker (di luar hot-path produce):
  - Tiap siklus: ambil daftar **(niche, geo) yang AKTIF dipakai channel** → untuk yang `cache` basi (umur > TTL) → fetch sumber → tulis `trend_cache`. **Pacing lembut** (mis. 1 request / beberapa detik, config-driven) → selalu di bawah rate-limit.
  - TTL config-driven (mis. 6–12 jam) di `app_config` (no-hardcode).
- **Produce membaca `trend_cache`** (fresh) — **tidak** memanggil sumber eksternal langsung. → produce **tak pernah** kena 429 + cepat.
- **Resilien:** sumber down/429 saat refresh → produce pakai cache terakhir (graceful, no block).

**Hasil:** request ke sumber = **O(jumlah_niche × geo ÷ TTL)** = **konstan**, **independen jumlah tenant** (10 atau 10.000 tenant → sama).

### Pilar 2 — Sumber tepat & relevan-niche (memecahkan M2, M4)
- **Google Trends (cached):** `interest_over_time` (momentum/avg) **+ `related_queries` rising** (sub-topik spiking) → discovery.
- **YouTube (key platform + cache):** untuk keyword niche, ambil Shorts terbaru (`order=viewCount`, `videoDuration=short`, 7–30d) **+ `videos.list?part=statistics`** → **viewCount + velocity** → `competition_gap` & format terbukti **DIUKUR**, tak rapuh ke key tenant.
- **Google News (filter niche):** RSS per keyword niche (sudah relevan).
- **Wikipedia (filter niche):** ambil top pageviews **lalu saring** ke entitas yang match keyword/niche; selain itu buang.
- **HackerNews (niche-conditional):** hanya untuk niche tech/science (flag per-niche di DB); selain itu lewati.
- Peta sumber↔niche + keyword/entitas **di DB** (admin-kurasi, no-hardcode).
- **Bobot sumber** (rasio kontribusi sinyal) = `source_weights` §2b — **YouTube velocity primer**, Trends sekunder, sisanya pelengkap/kondisional.

> **OUT-OF-THE-BOX (lompatan dari V1 — bukan sekadar "V1 + cache"):**
> 1. **YouTube velocity mining = radar PRIMER.** Alih-alih menebak tren dari sumber luar, **UKUR langsung** Shorts mana yang **paling cepat naik view** (velocity = views ÷ umur jam) di (niche, geo) + **competition_gap** (demand tinggi + sedikit pesaing baru = peluang emas). Sinyal dari **medan perang sebenarnya**, bukan proxy.
> 2. **Pola channel-SENDIRI = input PRIMER (moat per-channel).** Topik/angle/hook/format yang **audiens channel INI** sudah buktikan menang (`channel_insights`) = bias terkuat seleksi, mengalahkan tren generik. (§4)
> 3. **Agregat lintas-tenant ANONIM = network-effect moat.** Pola (niche, klaster-topik, geo) terbaik dari **SELURUH tenant** (agregat anonim, RLS-safe — dihitung server-side, nol kebocoran data tenant) → tenant baru dapat **cold-start boost**. Mustahil ditiru tool solo. (§4)
> 4. **Rising-query → KANDIDAT topik** (bukan keyword statis) → tangkap spike emergent lebih dini.

### Pilar 3 — Ukur, jangan menebak (memecahkan M3, M5)
- Isi dimensi `_calculate_viral_score` dari **angka nyata**:
  - `search_volume` + `trend_momentum` ← angka Google Trends.
  - `competition_gap` ← saturasi/velocity YouTube (banyak view, sedikit pesaing baru = gap).
  - `emotional_trigger` ← klasifikasi ringan (heuristik kata-emosi) + sinyal engagement.
  - `evergreen_potential` ← profil niche.
- **LLM dipakai untuk meramu ANGLE + script** dari kandidat ber-skor, **bukan** mengarang metrik → akurat, lebih murah, konsisten.

### Pilar 4 — Self-learning & self-improvement (the moat) → §4

---

## 4. Self-learning & self-improvement (detail)
Loop tertutup: **radar → produce → analytics nyata → balik ke radar**.

**Sudah ada (terverifikasi):**
```
video nyata → video_analytics (views, watch_time, avg_view_pct, ctr)
  → PerformanceAnalyzer (harian) → channel_insights (grade, niche_weights, top_hooks, avoid_patterns)
  → di-inject ke: NicheSelector (smart focus) · ScriptEngine (top hooks) · HookOptimizer
  → bobot viral di-blend per-channel (viral_score_weights bila ≥20 video) + historical_factor
```
Grade: `insufficient_data` (<5) · `learning` (5–20) · `peak` (50+).

### 4a. Self-learning ↔ radar — bagaimana bekerja (DIPERJELAS)
**Dua hal berbeda yang sering dikira sama:**
- **Self-LEARNING = MENGEKSTRAK pelajaran** dari hasil nyata: `video_analytics` → `PerformanceAnalyzer` → `channel_insights` (grade, `niche_weights`, `top_hooks`, `avoid_patterns`, **learned `viral_score_weights`**). Menjawab: *"apa yang TERBUKTI menang di channel ini?"*
- **Self-IMPROVEMENT = MENERAPKAN pelajaran** itu agar seleksi BERIKUTNYA lebih tajam: weights + insights **di-inject balik ke radar & seleksi** → (1) bobot dimensi/sumber dikalibrasi, (2) topik mirip-pemenang di-boost, (3) pola-gagal dihindari. Menjawab: *"kenapa loop makin pintar tiap siklus?"*

**Diagram loop tertutup (radar → produce → analytics → balik ke radar):**
```
   ┌──────────────────────── TREND RADAR (seleksi topik) ───────────────────────┐
   │  sumber × source_weights (YouTube velocity PRIMER · Trends · News · …)       │
   │  → kandidat topik (incl. rising-query)                                       │
   │  skor = dimensi TERUKUR × viral_score_weights(channel) × historical_factor   │
   │  → RANKING                                                                   │
   └───────────┬─────────────────────────────────────────────────▲──────────────┘
               │ topik terpilih                                    │  umpan balik:
               ▼                                                    │  (1) bobot belajar / channel+niche
        PRODUCE ──► PUBLISH                                         │  (2) boost topik mirip-pemenang
               │                                                    │  (3) avoid pola gagal
               ▼                                                    │
        video_analytics NYATA (views, avg_view_pct, ctr) ──► PerformanceAnalyzer
               │                                                    │
               └──► channel_insights ──────────────────────────────┘
                         + AGREGAT LINTAS-TENANT (anonim) ──► cold-start tenant baru
```
> **Inti:** radar **tidak** meranking sinyal generik — ia meranking **sinyal × apa-yang-terbukti-menang** (per-channel + agregat lintas-tenant). Tiap video nyata **mempersempit tebakan** berikutnya. Inilah "robot makin pintar tiap siklus" (klaim landing) yang **terukur**, bukan slogan.

**Target peningkatan (self-improvement radar):**
| Kapabilitas | Sekarang | Target |
|---|---|---|
| Bobot dimensi belajar per-channel | ✅ (≥20 video) | + belajar **per (niche, geo)** lintas-tenant (anonim, agregat) — "topik X niche space perform global" |
| Umpan balik OUTCOME ke radar | 🟡 lewat insights | **eksplisit**: topik yang terbukti tinggi `avg_view_pct` → boost tren serupa run berikutnya |
| Rising-query → kandidat | 🔴 | jadikan Trends-rising sumber kandidat topik (bukan cuma keyword statis) |
| QC-fail sebagai sinyal | 🔴 (lihat QC doc §4) | durasi/skor gagal → tuning budget/preset |
| Transparansi tenant | 🔴 | "robot belajar apa minggu ini" (dukung klaim landing) |

> Catatan: `avg_view_pct` baru terisi saat **analytics nyata di-fetch** (loop `self_learning` harian + YouTube Analytics). Saat lapse/insufficient → fallback estimasi (jujur). **Sinyal yang dipanen utk loop ini = §2c-B** (retensi, trafficSourceType, CTR, searchTerms — sebagian sudah di `channel_analytics.py`, sisanya enrichment F4). Kapabilitas **terbukti live 2026-06-16** (ryan: avg_view_pct 67.72%, trafficSource SHORTS/SEARCH).

---

## 5. Matematika skala (kenapa ini aman ribuan tenant)
- **Sekarang:** request_sumber ≈ tenant × produce/hari × 5 sumber → **tumbuh linear** → 429/blokir IP.
- **Target (Pilar-1):** request_sumber ≈ (jumlah_niche × geo) ÷ TTL → **konstan** (mis. 30 niche × 4 geo ÷ 12 jam ≈ ~240 fetch/hari **total**, untuk berapa pun tenant). Produce hanya **baca DB** (murah, tak kena rate-limit).

---

## 6. Rencana bertahap (propose-first; angka config-driven)
- **F1 — Decouple + cache (kritikal scaling):** `trend_cache` + `TrendRefresher` (paced, TTL config) + produce baca cache. *Memecahkan M1; nol kredit AI.*
- **F2 — Sumber relevan + bobot:** Trends `related_queries` rising · **YouTube velocity mining** (`videos.list` statistics, key platform) sebagai sinyal primer · filter-niche Wikipedia/HN (HN flag tech-niche) · terapkan **`source_weights` §2b**. *Memecahkan M2/M4.*
- **F3 — Ukur dimensi:** isi `_calculate_viral_score` dari angka nyata; LLM hanya meramu angle. *Memecahkan M3/M5.*
- **F4 — Self-improvement radar:** umpan balik outcome eksplisit + rising-query→kandidat + (lintas-tenant agregat anonim).
- **F5 — Transparansi tenant** (sinkron QC doc §4/F6).

Setiap fase: **validasi nyata sebelum klaim** (sesuai disiplin proyek) + update dokumen ini.

---

## 7. Keputusan & yang perlu data
**Diputuskan (berbasis validasi 2026-06-16):**
1. **Reddit DIKELUARKAN** (timeout + komersial berbayar) — bukan sumber gratis valid.
2. **Cache+Refresher = wajib** sebelum skala (bukan opsional).
3. **YouTube pakai key platform + cache** (bukan andalkan key tenant yg rapuh kuota).
4. **YouTube velocity = sinyal PRIMER** (bobot terbesar `source_weights` §2b); Trends sekunder; **News moderat/niche-flag · Wikipedia rendah/filter-only · HackerNews tech-niche-only** — Wiki & HN **kandidat di-drop** bila tak membayar dirinya (kontribusi outcome ≈ 0).
5. **Bobot sumber & dimensi DIKALIBRASI self-improvement** dari outcome nyata per (niche, geo) — bukan angka mati. Default §2b hanya titik awal.
6. **Pola channel-sendiri + agregat lintas-tenant anonim = moat** (input primer seleksi, bukan tambahan).

**Perlu data/biaya (jangan dikoding buta):**
- Kuota YouTube Data API platform (untuk velocity di banyak niche) — hitung biaya kuota.
- Kalibrasi nyata `competition_gap`/`emotional_trigger` dari angka (butuh beberapa run).
- Kalibrasi `source_weights` nyata (butuh ≥ beberapa minggu outcome lintas-niche) — sebelum itu pakai default §2b.

---

### Changelog
- 2026-06-16 — dibuat. Analisis trend_radar + niche_selector nyata; **validasi sumber** (Reddit gagal→dikeluarkan, Trends-rising tervalidasi); arsitektur cache+refresher (scaling) + ukur-dimensi + self-learning. Menunggu keputusan owner per-fase (§6, propose-first).
- 2026-06-16 (revisi D1b — inventaris sinyal + validasi live) — **§2c Sinyal YouTube yang dipanen** (A Data API · B Analytics API · C demand) + **status validasi**. **Live-validated**: Analytics API scope+data NYATA (ryan: averageViewPercentage 67.72%, insightTrafficSourceType SHORTS/SEARCH/…) → sumber terkaya B TERBUKTI accessible+kaya; autocomplete live; Trends-youtube 429 (cache); Data API quota-limited. `avg_view_pct=0` = loop belum dijalankan (bukan tak bisa). Memperkuat keyakinan arsitektur berbasis BUKTI.
- 2026-06-16 (revisi D1, per owner) — **§2b RASIO BOBOT sumber** (`source_weights` config-driven) + **verdict efektivitas** (YouTube velocity PRIMER ~0.45 · Trends ~0.30 · News moderat/niche-flag ~0.13 · **Wikipedia rendah/filter-only ~0.07** · **HackerNews tech-niche-only ~0.05**; Wiki & HN kandidat-drop). **§3 OUT-OF-THE-BOX** (velocity mining primer · pola channel-sendiri primer · agregat lintas-tenant anonim moat · rising-query→kandidat). **§4a DIPERJELAS**: beda self-learning (ekstrak) vs self-improvement (terapkan) + **diagram loop tertutup** radar↔analytics. §6 F2 + §7 keputusan 4-6 diperbarui. Menunggu review owner sebelum D2 (F1 cache).
