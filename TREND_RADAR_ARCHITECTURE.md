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

**Target peningkatan (self-improvement radar):**
| Kapabilitas | Sekarang | Target |
|---|---|---|
| Bobot dimensi belajar per-channel | ✅ (≥20 video) | + belajar **per (niche, geo)** lintas-tenant (anonim, agregat) — "topik X niche space perform global" |
| Umpan balik OUTCOME ke radar | 🟡 lewat insights | **eksplisit**: topik yang terbukti tinggi `avg_view_pct` → boost tren serupa run berikutnya |
| Rising-query → kandidat | 🔴 | jadikan Trends-rising sumber kandidat topik (bukan cuma keyword statis) |
| QC-fail sebagai sinyal | 🔴 (lihat QC doc §4) | durasi/skor gagal → tuning budget/preset |
| Transparansi tenant | 🔴 | "robot belajar apa minggu ini" (dukung klaim landing) |

> Catatan: `avg_view_pct` baru terisi saat **analytics nyata di-fetch** (loop `self_learning` harian + YouTube Analytics). Saat lapse/insufficient → fallback estimasi (jujur).

---

## 5. Matematika skala (kenapa ini aman ribuan tenant)
- **Sekarang:** request_sumber ≈ tenant × produce/hari × 5 sumber → **tumbuh linear** → 429/blokir IP.
- **Target (Pilar-1):** request_sumber ≈ (jumlah_niche × geo) ÷ TTL → **konstan** (mis. 30 niche × 4 geo ÷ 12 jam ≈ ~240 fetch/hari **total**, untuk berapa pun tenant). Produce hanya **baca DB** (murah, tak kena rate-limit).

---

## 6. Rencana bertahap (propose-first; angka config-driven)
- **F1 — Decouple + cache (kritikal scaling):** `trend_cache` + `TrendRefresher` (paced, TTL config) + produce baca cache. *Memecahkan M1; nol kredit AI.*
- **F2 — Sumber relevan:** Trends `related_queries` rising · filter-niche Wikipedia/HN · YouTube `videos.list` statistics (key platform). *Memecahkan M2/M4.*
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

**Perlu data/biaya (jangan dikoding buta):**
- Kuota YouTube Data API platform (untuk velocity di banyak niche) — hitung biaya kuota.
- Kalibrasi nyata `competition_gap`/`emotional_trigger` dari angka (butuh beberapa run).

---

### Changelog
- 2026-06-16 — dibuat. Analisis trend_radar + niche_selector nyata; **validasi sumber** (Reddit gagal→dikeluarkan, Trends-rising tervalidasi); arsitektur cache+refresher (scaling) + ukur-dimensi + self-learning. Menunggu keputusan owner per-fase (§6, propose-first).
