# MESIN VIRAL — Dokumentasi Teknis
> Dokumentasi teknis sistem produksi konten otomatis mesinviral.com.  
> Update terakhir: 8 April 2026.  
> Selalu verifikasi dengan kode aktual sebelum mengambil keputusan teknis.

---

## 1. GAMBARAN SISTEM

Mesin Viral adalah pipeline otomatis yang memproduksi video YouTube Shorts setiap hari. Input: topik trending. Output: video 45–180 detik dipublish ke YouTube.

**Stack inti:**
- Python 3.11 (WSL2 dev, Ubuntu 22.04 VPS)
- Supabase (PostgreSQL) — config, logging, analytics
- Cloudflare R2 — musik dan font storage
- Claude Sonnet 4.6 / GPT-4o-mini — script generation
- ElevenLabs / OpenAI TTS — text-to-speech
- DALL-E 3 — visual AI image generation
- FFmpeg — video rendering
- YouTube Data API v3 — publish

---

## 2. PIPELINE — 8 LANGKAH

```
pipeline.py
  │
  ├─ Step 0: resolve_slot() — pilih niche dari production_schedules / rotation
  │
  ├─ Step 1: TrendRadar.scan() — 5 sumber trend
  │           Google Trends (geo=US/UK) | YouTube Search | Google News
  │           Hacker News | Wikipedia Recent Changes
  │           → list topik kandidat dengan skor viral
  │
  ├─ Step 2: NicheSelector.select() — pilih 1 topik terbaik
  │           AI prompt + channel_insights injection (self-learning)
  │           Dedup: skip topik yang dipublish dalam duplicate_lookback_days
  │
  ├─ Step 3: ScriptEngine.generate() — buat script 8 section
  │           LLM: Claude Sonnet 4.6 (atau GPT-4o-mini fallback)
  │           Scoring: ScriptAnalyzer 6 dimensi (gpt-4o-mini)
  │           Retry: max 3x, threshold min script_min_viral_score
  │           Output: hook, mystery_drop, build_up, pattern_interrupt,
  │                   core_facts, curiosity_bridge, climax, cta,
  │                   visual_suggestions (8 cinematic prompts)
  │
  ├─ Step 4: TTSEngine.synthesize() — text ke audio
  │           Provider: ElevenLabs (default) → OpenAI TTS → Edge TTS
  │           Output: audio.mp3 + word_timestamps (per kata)
  │
  ├─ Step 5: VisualAssembler.assemble() — buat 8 clips visual
  │           Mode video: Pexels stock (per keyword)
  │           Mode ai_image: DALL-E 3 (3 attempts, Claude rewrite on rejection)
  │           Output: 8 file MP4 clip
  │
  ├─ Step 6: VideoRenderer.render() — assembly final
  │           FFmpeg: clips → 1080×1920, 30fps, H.264
  │           Karaoke captions (word-sync, ASS format)
  │           Hook title overlay (config-driven font dari R2)
  │           Background music (optional, dari R2)
  │           Loop ending (optional, xfade 0.5s)
  │
  ├─ Step 7: QC Gate (4 checks)
  │           size ≥ 5 MB | durasi 45–180s | ≥ 6 clips berhasil
  │           Jika gagal: write_qc_failed → hapus video → skip publish
  │
  └─ Step 8: YouTubePublisher.publish()
              Upload + metadata (title, description, hashtags, thumbnail)
              Thumbnail: frame dari hook clip, di-resize sesuai content_type
                short → 1080×1920 portrait (9:16) | long → 1280×720 landscape (16:9)
              Telegram notif: success / QC fail / error
```

---

## 3. KOMPONEN UTAMA

### 3.1 Orchestrator

| File | Fungsi |
|------|--------|
| `src/orchestrator/pipeline.py` | Main pipeline — orkestrasi 8 step, QC gate, Telegram notif |

### 3.2 Intelligence

| File | Fungsi |
|------|--------|
| `src/intelligence/trend_radar.py` | Scan 5 sumber trend, scoring sinyal, geo filter Tier-1 |
| `src/intelligence/niche_selector.py` | Pilih topik terbaik via AI + channel_insights injection |
| `src/intelligence/schedule_manager.py` | Resolve niche per slot: explicit schedule → rotation → random. Diversity guard: cegah niche dominan dalam 6 run terakhir. |
| `src/intelligence/script_engine.py` | Generate + score script 8 section. Support Claude & OpenAI. Retry dengan feedback skor per dimensi |
| `src/intelligence/script_analyzer.py` | Score script 6 dimensi viral (via gpt-4o-mini). Niche-aware emotional_peak scoring |
| `src/intelligence/config.py` | `TenantConfig` (legacy, minimal). `get_niches()` load niches dari Supabase |

### 3.3 Providers

| File | Fungsi |
|------|--------|
| `src/providers/llm/claude.py` | Claude Sonnet 4.6 — script generation, rejection rewrite |
| `src/providers/llm/openai.py` | GPT-4o-mini — script generation fallback |
| `src/providers/tts/elevenlabs.py` | ElevenLabs TTS (default) — voice + word timestamps |
| `src/providers/tts/openai.py` | OpenAI TTS (fallback ke ElevenLabs) |
| `src/providers/tts/edge_tts.py` | Edge TTS Microsoft (fallback gratis) |
| `src/providers/visual/pexels.py` | Pexels stock video (visual_mode="video") |
| `src/providers/visual/ai_image.py` | DALL-E 3 AI image (visual_mode="ai_image:dall-e-3"). 3 attempts, rewrite via Claude/OpenAI |
| `src/providers/visual/ai_video.py` | AI Video — **DISABLED**, raise VisualError |
| `src/providers/music/music_selector.py` | Pilih track dari library R2: mood detection → niche+mood query → download |

### 3.4 Production

| File | Fungsi |
|------|--------|
| `src/production/tts_engine.py` | Orkestrasi TTS, fallback cascade, cache audio |
| `src/production/visual_assembler.py` | Orkestrasi visual, pass niche_visual_style ke provider |
| `src/production/video_renderer.py` | FFmpeg assembly: clips + caption + title + music + loop |

### 3.5 Analytics

| File | Fungsi |
|------|--------|
| `src/analytics/channel_analytics.py` | Pull YouTube Data API + Analytics API → upsert video_analytics |
| `src/analytics/performance_analyzer.py` | Compute channel_insights dari video_analytics (mingguan) |

### 3.6 Distribution

| File | Fungsi |
|------|--------|
| `src/distribution/youtube_publisher.py` | Upload YouTube, set metadata, thumbnail. OAuth per channel. Thumbnail: short→1080×1920 portrait, long→1280×720 landscape (s92) |

### 3.7 Config & Utils

| File | Fungsi |
|------|--------|
| `src/config/tenant_config.py` | `TenantRunConfig` — 70+ field dari Supabase. `TenantConfigManager` load config |
| `src/utils/telegram_notifier.py` | Kirim notif Telegram: success, QC fail, publish fail, pipeline error |
| `src/utils/supabase_writer.py` | Write videos, QC failed, pipeline errors ke Supabase. Fire-and-forget |

### 3.8 Scripts

| File | Fungsi |
|------|--------|
| `scripts/fetch_analytics.sh` | Cron harian 06:00 UTC — jalankan channel_analytics.py |
| `scripts/compute_insights.sh` | Cron mingguan Senin 07:00 UTC — jalankan compute_insights.py |
| `scripts/compute_viral_weights.sh` | Cron bulanan — update viral weights dari analytics |
| `scripts/test_telegram.py` | Test manual Telegram notif |
| `scripts/reauth_youtube.py` | Re-auth OAuth YouTube per channel |
| `scripts/seed_music_library.py` | Seed music_library dari R2 ke Supabase |
| `scripts/migrate_s*.sql` | Migration DDL — dijalankan manual di Supabase SQL Editor |

---

## 4. DATABASE SCHEMA (SUPABASE)

### 4.1 tenant_configs
Config per tenant — dibaca sekali per pipeline run.

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| tenant_id | VARCHAR PK | ID tenant unik |
| niche | VARCHAR | Niche default (overrideable via schedule) |
| llm_provider | VARCHAR | `"claude"` atau `"openai"` |
| llm_model | VARCHAR | Model ID, e.g. `"claude-sonnet-4-6"` |
| llm_api_key | TEXT | Anthropic API key (jika llm_provider=claude) |
| visual_api_key | TEXT | OpenAI API key (untuk DALL-E + ScriptAnalyzer) |
| visual_mode | VARCHAR | `"video"` (Pexels) atau `"ai_image:dall-e-3"` |
| elevenlabs_api_key | TEXT | ElevenLabs API key |
| elevenlabs_voice_id | VARCHAR | Voice ID ElevenLabs |
| script_min_viral_score | INT | Threshold score minimum (default: 75) |
| max_script_retry | INT | Maks retry script jika di bawah threshold |
| music_enabled | BOOLEAN | Aktifkan background musik |
| music_volume | FLOAT | Volume musik (0.0–1.0) |
| caption_style | JSONB | `{font_name, size, color, bold, italic, border_color, alignment}` |
| hook_title_style | JSONB | `{font_name, size, color, bold, italic, border_color, alignment}` |
| telegram_enabled | BOOLEAN | Aktifkan notif Telegram |
| telegram_chat_id | VARCHAR | Chat ID Telegram penerima notif |
| channel_name | VARCHAR | Nama channel untuk display di notif |
| peak_region | VARCHAR | Geo target analitik (`"us"`, `"uk"`, dll) |
| duplicate_lookback_days | INT | Hari lookback untuk dedup topik |
| loop_ending_enabled | BOOLEAN | Aktifkan loop ending di video |
| loop_ending_duration | FLOAT | Durasi loop ending dalam detik |
| publish_slots | JSONB | Jam publish UTC (array) |

### 4.2 niches
Registry niche — config-driven, tidak ada hardcode di kode.

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| niche_id | VARCHAR PK | ID niche unik |
| name | VARCHAR | Nama display |
| keywords | JSONB | Keyword untuk trend scanning |
| voice_profile | JSONB | `{style, tone, emotion_arc, language_register}` |
| target_emotion | TEXT | Emosi target untuk penonton |
| visual_style | JSONB | `{base_style, color_palette, atmosphere}` |
| mood_priority | JSONB | Array mood yang cocok untuk niche ini |
| default_hashtags | JSONB | Hashtag default YouTube |
| emotion_scoring_criteria | TEXT | Kriteria scoring emotional_peak untuk ScriptAnalyzer (s89) |
| is_active | BOOLEAN | Status aktif |

**4 niche aktif:** `universe_mysteries`, `dark_history`, `ocean_mysteries`, `fun_facts`

### 4.3 production_schedules
Jadwal produksi per slot. Niche eksplisit per slot atau NULL untuk rotation.

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| schedule_id | UUID PK | |
| tenant_id | TEXT | |
| slot_time | VARCHAR | Jam UTC, e.g. `"08:30"` |
| niche_id | VARCHAR | NULL = rotation otomatis |
| niche_focus | TEXT | Keyword fokus opsional |
| content_type | VARCHAR | `'short'` (default) atau `'long'` — menentukan dimensi thumbnail (s92) |
| is_active | BOOLEAN | |

### 4.4 fonts
Font library — didownload dari R2 saat pipeline berjalan. (s88)

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| id | UUID PK | |
| font_name | VARCHAR | Nama font, e.g. `"Anton"` |
| r2_key | TEXT | Path di R2, e.g. `"fonts/Anton-Regular.ttf"` |
| is_active | BOOLEAN | |

### 4.5 moods
Mood library untuk music selector. (s85b)

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| mood_id | VARCHAR PK | e.g. `"dramatic"`, `"mysterious"` |
| name | VARCHAR | Display name |
| keywords | JSONB | Keyword untuk deteksi mood dari script |
| is_active | BOOLEAN | |

**15 mood aktif** (contoh): dramatic, mysterious, epic, tense, dark, cosmic, eerie, wonder, unsettling, hopeful, suspenseful, melancholic, energetic, ambient, cinematic

### 4.6 music_library
Track musik background.

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| id | UUID PK | |
| name | VARCHAR | Nama track |
| niche | VARCHAR | Niche target (atau NULL untuk semua niche) |
| mood | VARCHAR | FK ke moods.mood_id |
| r2_key | TEXT | Path di R2 |
| duration_s | FLOAT | Durasi dalam detik |
| bpm | INT | BPM |
| play_count | INT | Berapa kali dipakai |
| is_active | BOOLEAN | |

**R2 struktur:** `music/{niche}/{mood}/{filename}.mp3`

### 4.7 videos
Log setiap video yang diproduksi.

| Kolom | Keterangan |
|-------|-----------|
| video_id | UUID PK |
| tenant_id | |
| topic | Judul topik |
| niche | |
| script_viral_score | Skor script (0–100) |
| hook_frame_img | Path thumbnail |
| youtube_url | URL video yang dipublish |
| duration_s | Durasi video |
| file_size_mb | Ukuran file |
| word_count | Jumlah kata script |
| published_at | Timestamp publish |
| run_id | ID unik pipeline run |

### 4.8 video_analytics
Metrics YouTube per video (diupdate harian).

| Kolom | Keterangan |
|-------|-----------|
| video_id | FK ke videos |
| tenant_id | |
| views | Total views |
| likes | Total likes |
| comments | Total comments |
| watch_time_minutes | Total watch time |
| avg_view_percentage | Rata-rata % ditonton |
| subscriber_gain | Subscriber dari video ini |
| analytics_date | Tanggal update terakhir |

### 4.9 channel_insights
Aggregated analytics per tenant — dicompute mingguan oleh PerformanceAnalyzer.

| Kolom | Keterangan |
|-------|-----------|
| insight_id | UUID PK |
| tenant_id | |
| computed_at | Waktu komputasi |
| videos_analyzed | Jumlah video dalam analisis |
| performance_grade | `insufficient_data` / `learning` / `optimizing` / `peak` |
| niche_weights | JSONB `{niche_id: weight}` — distribusi produksi optimal |
| top_hooks | JSONB — hook patterns dengan CTR tertinggi |
| avoid_patterns | JSONB — topik/pattern yang perform buruk |
| top_topics | JSONB — topik terbaik untuk referensi |

### 4.10 qc_failed_videos & pipeline_errors
Fire-and-forget logging. QC gagal dan pipeline errors disimpan untuk debug.

---

## 5. ENVIRONMENT VARIABLES

### 5.1 Wajib

| Variabel | Dipakai Oleh | Keterangan |
|----------|-------------|-----------|
| `SUPABASE_URL` | Semua modul | URL project Supabase |
| `SUPABASE_KEY` | Semua modul | Anon key Supabase |
| `OPENAI_API_KEY` | ScriptAnalyzer, DALL-E 3, OpenAI TTS | Wajib untuk visual + script scoring |
| `ELEVENLABS_API_KEY` | TTSEngine | Wajib jika pakai ElevenLabs TTS |
| `YOUTUBE_CLIENT_ID` | YouTubePublisher | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | YouTubePublisher | Google OAuth client secret |

### 5.2 Opsional / Conditional

| Variabel | Dipakai Oleh | Keterangan |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | claude.py | Wajib jika `llm_provider='claude'` dan `llm_api_key` tidak ada di DB |
| `TELEGRAM_BOT_TOKEN` | TelegramNotifier | Wajib jika notif Telegram diaktifkan |
| `TELEGRAM_CHAT_ID` | TelegramNotifier | Fallback jika `telegram_chat_id` tidak ada di DB |
| `R2_ENDPOINT` | MusicSelector, VideoRenderer | URL endpoint Cloudflare R2 |
| `R2_ACCESS_KEY` | MusicSelector, VideoRenderer | R2 access key |
| `R2_SECRET_KEY` | MusicSelector, VideoRenderer | R2 secret key |
| `R2_BUCKET` | MusicSelector, VideoRenderer | Nama bucket (default: `"viral-machine"`) |
| `PEXELS_API_KEY` | PexelsProvider | Wajib jika `visual_mode="video"` |

> **Catatan**: `ANTHROPIC_API_KEY` tidak ada di `.env.example` — harus ditambah manual jika tenant pakai Claude. Alternatif: isi `llm_api_key` di tabel `tenant_configs`.

---

## 6. KONFIGURASI TENANT

### 6.1 Dua Kelas Config

| Kelas | File | Fungsi |
|-------|------|--------|
| `TenantConfig` | `src/intelligence/config.py` | Legacy, minimal. Hanya `tenant_id`, `niche`, dan beberapa field dasar. Dipakai sebagai parameter awal pipeline dan `__main__` |
| `TenantRunConfig` | `src/config/tenant_config.py` | Modern, 70+ field. Dibaca dari Supabase `tenant_configs`. Dipakai untuk semua keputusan runtime |

Pipeline dimulai dengan `TenantConfig` (dari `__main__`), lalu memanggil `_load_tenant_run_config()` untuk mendapat `TenantRunConfig` dari Supabase.

### 6.2 LLM Provider

Script generation didukung dua provider (via `script_engine.py`):

| Provider | Kondisi | Model |
|----------|---------|-------|
| Claude Sonnet 4.6 | `llm_provider='claude'` + `llm_api_key` tersedia | claude-sonnet-4-6 |
| GPT-4o-mini | `llm_provider='openai'` atau Claude gagal | gpt-4o-mini |

**Catatan**: `TenantRunConfig.get_llm_provider()` mendukung `"openai"` dan `"claude"` (s91). ScriptEngine tetap handle Claude langsung via `anthropic.Anthropic()` untuk script generation.

**Script analysis** (`ScriptAnalyzer`) selalu menggunakan `visual_api_key` (OpenAI), bukan `llm_api_key`. Ini disengaja karena gpt-4o-mini lebih murah untuk scoring.

### 6.3 Visual Mode

| visual_mode | Provider | Keterangan |
|-------------|----------|-----------|
| `"video"` | Pexels | Stock video, default |
| `"ai_image:dall-e-3"` | DALL-E 3 | AI image per section, 3 attempts |
| `"ai_image:flux-schnell"` | Flux (Replicate) | Alternatif AI image |

**DALL-E 3 retry flow:**
1. Attempt 1: prompt dari `visual_suggestions` (cinematic prompt dari LLM)
2. Attempt 2–3: Claude/LLM rewrite prompt dengan `rejection_history` terakumulasi
3. Tidak ada `visual_fallbacks` — visual harus relevan dengan narasi
4. Jika 3 attempt gagal → scene di-skip, Telegram notif

### 6.4 Script Quality Gate

`script_min_viral_score` (field di `tenant_configs`, default 75) menentukan threshold minimum viral score.

Script Engine melakukan max 3 retry. Setiap retry feedback berisi:
- Skor aktual per dimensi
- Teknik konkrit yang harus diterapkan untuk dimensi lemah
- Kutipan section yang perlu diperbaiki

Jika setelah 3x masih di bawah threshold → gunakan script terbaik yang ada (tidak crash).

### 6.5 Font Config (s88)

Font untuk caption dan hook title dibaca dari Supabase `fonts` table:
1. `tenant_configs.caption_style.font_name` (e.g. `"Anton"`)
2. Pipeline query `fonts` table → dapat `r2_key`
3. Download dari R2 ke `logs/fonts/` (cache)
4. FFmpeg menggunakan path local font

---

## 7. SCRIPT — 8 SECTION

```
[HOOK]              — Stop scroll dalam 1 detik. Information gap spesifik.
[MYSTERY DROP]      — Teaser yang memperburuk pertanyaan, bukan menjawab.
[BUILD UP]          — Bangun konteks + stakes dengan angka/fakta spesifik.
[PATTERN INTERRUPT] — Reversal atau twist yang mengubah arah cerita.
[CORE FACTS]        — Fakta inti: verifiable, surprising, specific.
[CURIOSITY BRIDGE]  — Transisi ke climax: pertanyaan yang tidak bisa diabaikan.
[CLIMAX]            — CAUSE the emotion — jangan describe. Quality bar: baca sendiri, rasakan sesuatu, atau rewrite.
[CTA]               — Bukan instruksi. Chemistry via resonance. Tidak ada kata: Follow/Subscribe/Like/Hit the bell.
```

### 6 Dimensi Viral (ScriptAnalyzer)

| Dimensi | Bobot | Threshold 80+ |
|---------|-------|--------------|
| hook_power | 25% | Information gap yang spesifik, tidak bisa berlaku untuk video lain |
| curiosity_gap | 20% | Setiap section berakhir dengan pertanyaan terbuka, bukan summary |
| retention_arc | 20% | Tidak ada kalimat yang bisa dihapus tanpa kehilangan sesuatu |
| emotional_peak | 20% | Niche-aware (dari `emotion_scoring_criteria`): emosi harus disebabkan, bukan dideskripsikan |
| information_density | 10% | Semua fakta verifiable dan specific (bukan "very large", "long ago") |
| cta_strength | 5% | Tidak ada instruksi eksplisit — following terasa seperti keputusan penonton sendiri |

---

## 8. SELF-LEARNING ANALYTICS

### 8.1 Arsitektur 3 Layer

```
Layer 1: ChannelAnalytics (harian)          → channel_analytics.py
  → Pull YouTube Data API v3 + Analytics API v2
  → Metric CTR: impressionClickThroughRate (bukan cardClickRate!)
  → Upsert ke video_analytics (skip video < 48 jam)

Layer 2: PerformanceAnalyzer (mingguan, Senin 07:00 UTC)  → performance_analyzer.py
  → Compute dari video_analytics per tenant
  → Simpan ke channel_insights: niche_weights, top_hooks, avoid_patterns
  → top_hooks di-sort by CTR — jika semua 0, fallback sort by views

Layer 3: NicheSelector (setiap pipeline run)  → niche_selector.py
  → Load channel_insights terbaru (_load_insights)
  → Fetch recent_topics via get_recent_topics() SEBELUM AI call (s91)
  → Inject ke AI prompt:
      - top topics, CTR hooks, avoid patterns (dari channel_insights)
      - "AVOID THESE ANGLES" — daftar topik yang sudah diproduksi (recent_topics[:10])
  → Grade optimizing/peak: apply historical_factor (0.7×–1.5×) ke viral_score
  → _filter_duplicates() menerima recent yang sama (tidak re-query Supabase)
```

### 8.2 Performance Grade

| Grade | Kondisi | Behavior Pipeline |
|-------|---------|-------------------|
| `insufficient_data` | < 5 videos | AI estimation murni |
| `learning` | 5–20 videos | Inject top topics + patterns ke prompt, skor tidak diubah |
| `optimizing` | 21–50 videos | Full injection + historical_factor adjustment |
| `peak` | 50+ videos | Hook pattern extraction + full self-optimization |

**Status ryan_andrian (7 Apr 2026):** grade=optimizing, 36+ videos, niche_weights: ocean_mysteries=0.6, fun_facts=0.4

---

## 9. INFRASTRUKTUR PRODUKSI

### 9.1 Environment

| | Dev | VPS Produksi |
|-|-----|-------------|
| OS | Windows 11 + WSL2 | Ubuntu 22.04 |
| Python | 3.11.9 | 3.11.0rc1 |
| Path | `/home/rad/viral-machine` | `/home/rad4vm/viral-machine` |
| User | rad | rad4vm |

SSH alias: `ssh vps` (konfigurasi di `~/.ssh/config` dev machine)

### 9.2 Crontab VPS

```bash
# Pipeline produksi 5× sehari
30 8  * * * /home/rad4vm/viral-machine/scripts/run_pipeline.sh >> logs/cron_$(date +\%Y\%m\%d)_r1.log 2>&1
30 11 * * * /home/rad4vm/viral-machine/scripts/run_pipeline.sh >> logs/cron_$(date +\%Y\%m\%d)_r2.log 2>&1
30 14 * * * /home/rad4vm/viral-machine/scripts/run_pipeline.sh >> logs/cron_$(date +\%Y\%m\%d)_r3.log 2>&1
30 17 * * * /home/rad4vm/viral-machine/scripts/run_pipeline.sh >> logs/cron_$(date +\%Y\%m\%d)_r4.log 2>&1
30 20 * * * /home/rad4vm/viral-machine/scripts/run_pipeline.sh >> logs/cron_$(date +\%Y\%m\%d)_r5.log 2>&1

# Analytics pull harian 06:00 UTC
0 6 * * * /home/rad4vm/viral-machine/scripts/fetch_analytics.sh >> logs/analytics_$(date +\%Y\%m\%d).log 2>&1

# Channel insights mingguan Senin 07:00 UTC
0 7 * * 1 /home/rad4vm/viral-machine/scripts/compute_insights.sh >> logs/insights_$(date +\%Y\%m\%d).log 2>&1
```

Log pipeline: `logs/cron_YYYYMMDD_r{1-5}.log`

### 9.3 Deploy Workflow

```
Dev lokal (WSL2)
  │  git push origin main
  ▼
GitHub (ryanandrian/viral-machine)
  │  git pull origin main  ← manual di VPS via: ssh vps
  ▼
VPS produksi
  │  pip install -r requirements.txt  (jika ada package baru)
  │  Jalankan SQL migration di Supabase dashboard (jika ada DDL baru)
  │  Update .env VPS (jika ada env var baru)
  ▼
Cron otomatis 5× sehari
```

### 9.4 Auto Cleanup

| Target | Kapan |
|--------|-------|
| Clips (PNG/MP4 per section) | Segera setelah video di-render |
| Video file (MP4 final) | Segera setelah upload ke YouTube |
| Log files | Setelah 30 hari |

---

## 10. CATATAN TEKNIS

### 10.1 Async/Sync Pipeline

Pipeline berjalan **sepenuhnya synchronous** (`pipeline.py` adalah sync Python).

Provider yang menggunakan async (`ai_image.py` menggunakan `AsyncOpenAI`):
- Dipanggil dari context sync via `asyncio.run()`
- `ai_image.py` menggunakan `async with AsyncOpenAI(...)` sebagai context manager (fix: RuntimeError event loop closed)

Tidak ada concurrency — TTS dan Visual tidak bisa jalan paralel. Refactor ke async-await bisa memangkas ~20–30% waktu eksekusi (belum dikerjakan).

### 10.2 Dua Kelas Config (Legacy vs Modern)

Lihat Section 6.1. Dampak praktis: jika field baru perlu dipakai di kode lama yang masih pakai `TenantConfig`, perlu extend kelas legacy — atau gunakan `get_niches()` / load langsung dari Supabase.

### 10.3 Fire-and-Forget Pattern

`SupabaseWriter` dan `TelegramNotifier` menggunakan prinsip fire-and-forget: semua operasi dibungkus `try-except`, error hanya di-log sebagai WARNING. Pipeline tidak pernah crash karena Supabase atau Telegram gagal.

### 10.4 QC Gate — 4 Checks

`pipeline.py._pre_publish_qc()`:
1. **File size ≥ 5 MB** — render tidak korup/kosong
2. **Durasi ≥ 45 detik** — minimum Shorts yang layak tayang
3. **Durasi ≤ 180 detik** — batas YouTube Shorts
4. **≥ 6 clips berhasil** — semua scene visual ada

Jika gagal: `write_qc_failed()` → hapus video → skip publish → lanjut run berikutnya.

### 10.5 Thumbnail

Diambil dari `hook_frame_img.jpg` — frame yang diekstrak dari hook clip selama visual assembly. Disimpan sebelum `cleanup_clips()`.

### 10.6 Karaoke Caption System

Subtitle dibangun dari `word_timestamps` hasil TTS ElevenLabs:
- Kata aktif: warna `#FFD700` (kuning)
- Kata lain di kalimat sama: `#FFFFFF` (putih)
- Format ASS (Advanced SubStation Alpha) — kontrol penuh timing + warna
- Maksimum 2 baris, 4 kata per baris, posisi 150px dari bawah

Font caption: dari `tenant_configs.caption_style.font_name` → download dari R2 (s88).

### 10.7 Diversity & Duplikat — 2 Layer Berbeda

Sistem memiliki **2 mekanisme** yang bekerja di level berbeda. Wajib dipahami agar tidak membuat fungsi redundant.

#### Layer 1 — Niche Diversity Guard (`schedule_manager.py:393`)
Mencegah **niche yang sama** mendominasi produksi terakhir.

```
Konstanta:
  DIVERSITY_LOOKBACK    = 6     → cek 6 produksi terakhir
  DIVERSITY_MAX_FRACTION = 0.4  → max 2 dari 6 (40%) boleh niche sama

Alur:
  _apply_diversity_guard(tenant_id, proposed_niche)
    → _get_recent_niches(limit=6)  → query videos table
    → hitung frekuensi proposed_niche
    → jika count >= max_allowed: ganti ke niche LRU (paling lama tidak dipakai)

  Tambahan: _get_last_niche() → cegah 2 produksi BERTURUTAN dengan niche sama
```

**Scope**: Level niche saja. Tidak tahu isi topik.

#### Layer 2 — Topic Duplicate Filter (`niche_selector.py:577`)
Mencegah **topik yang sama** diproduksi ulang.

```
Alur (berjalan POST-generation, setelah AI sudah generate):
  _filter_duplicates(topics, tenant_config)
    → get_recent_topics(lookback_days=duplicate_lookback_days)  ← default 30 hari
    → normalisasi topic_slug (lowercase, strip spesial)
    → filter topics yang slug-nya ada di recent_slugs
    → jika semua 5 topik AI adalah duplikat:
        Safety net LRU → ambil topik TERLAMA dari histori → re-produksi ulang ⚠️

Config-driven: duplicate_lookback_days di tenant_configs (default 30)
```

**Scope**: Level slug (exact string). Tidak bisa deteksi topik bermakna sama, formulasi berbeda.

#### Keterbatasan

- `_filter_duplicates()` hanya cek exact slug match — topik bermakna sama tapi formulasi berbeda tetap lolos
- LRU safety net: jika semua 5 topik AI adalah duplikat slug → sistem re-produksi topik terlama dari histori (`niche_selector.py`)

### 10.8 Estimasi Biaya per Pipeline Run

| Komponen | Estimasi |
|----------|---------|
| Claude Sonnet 4.6 (script) | ~$0.03–0.08 |
| GPT-4o-mini (ScriptAnalyzer, ~2 calls) | ~$0.01 |
| DALL-E 3 (8 images) | ~$0.32 |
| ElevenLabs TTS (~1500 karakter) | ~$0.02–0.05 |
| Cloudflare R2 (musik) | < $0.01 |
| YouTube API, Supabase | $0 |
| **Total per run (ai_image mode)** | **~$0.40–0.50** |
| **Total per hari (5 run)** | **~$2.00–2.50** |
| **Total per bulan** | **~$60–75** |

> Estimasi dengan `visual_mode="ai_image:dall-e-3"`. Mode `video` (Pexels) lebih murah: ~$0.10/run.

### 10.9 Keterbatasan yang Diketahui
| Masalah | File | Detail |
|---------|------|--------|
| ScriptAnalyzer selalu pakai OpenAI | `script_analyzer.py` | Scoring gpt-4o-mini via `visual_api_key` — disengaja, lebih murah untuk scoring |
| Long form belum diimplementasi | — | `content_type='long'` di schedule tidak akan mengubah video resolution/duration — hanya thumbnail yang sudah siap |
| `_filter_duplicates()` hanya exact slug match | `niche_selector.py` | Topik bermakna sama tapi formulasi berbeda tetap lolos filter |
| AI Video DISABLED | `ai_video.py` | raise `VisualError` — belum ada provider video |
| Single tenant di `__main__` | `pipeline.py` | Hardcode `tenant_id="ryan_andrian"` |
| Tidak ada unit tests | — | Tidak ada test suite, tidak ada mock API |
| TikTok / Instagram | — | Field config ada, distribution code belum ada |

---

## 11. MIGRATION HISTORY

| Migration | Isi | Status |
|-----------|-----|--------|
| migrate_s81_telegram.sql | Kolom telegram_enabled, telegram_chat_id, channel_name ke tenant_configs | ✅ |
| migrate_s82_regional.sql | Regional targeting fields | ✅ |
| migrate_s84_schedules.sql | Tabel niches + production_schedules | ✅ |
| migrate_s84b_analytics.sql | Tabel video_analytics | ✅ |
| migrate_s84c_insights.sql | Tabel channel_insights + ALTER video_analytics | ✅ |
| migrate_s85_niche_visual.sql | Kolom visual_style, mood_priority ke niches | ✅ |
| migrate_s85b_moods_table.sql | Tabel moods (15 mood, keywords) | ✅ |
| migrate_s88_fonts.sql | Tabel fonts + RLS policy + seed Anton | ✅ |
| migrate_s89_emotion_scoring_criteria.sql | Kolom emotion_scoring_criteria ke niches + isi 4 niche | ✅ |
