# ROADMAP MESIN VIRAL — Phase 8a & 8b
> Tujuan: Meningkatkan kualitas viral → monetisasi → 100% siap SaaS  
> Dimulai: 4 April 2026 | Diupdate setiap item selesai + tervalidasi

---

## PROGRESS TRACKER

| # | Item | Tier | Status | Selesai |
|---|------|------|--------|---------|
| 1 | Telegram Notifikasi | 1 | ✅ DONE | 4 Apr 2026 |
| 2 | Regional Targeting Tier-1 di TrendRadar | 1 | ✅ DONE | 4 Apr 2026 |
| 3 | Loop Ending Video | 1 | ✅ DONE (disabled) | 4 Apr 2026 |
| 4a | Niche DB + Schedule Manager + Focus per Slot | 1 | ✅ DONE | 4 Apr 2026 |
| 4b | ChannelAnalytics — YouTube Analytics pull | 1 | ✅ DONE | 5 Apr 2026 |
| 4c | PerformanceAnalyzer + channel_insights | 1 | ✅ DONE | 5 Apr 2026 |
| 4d | Feedback Loop NicheSelector (self-learning) | 1 | ✅ DONE | 5 Apr 2026 |
| 5 | Error Management Profesional (exceptions.py) | 2 | ⬜ TODO | — |
| 6 | Multi-channel per Tenant | 2 | ⬜ TODO | — |
| 7 | Multi-channel per Tenant | 2 | ⬜ TODO | — |
| 8 | Tenant Baru Onboarding (SaaS testing) | 2 | ⬜ TODO | — |

---

## DETAIL SETIAP ITEM

---

### ✅ Item 1 — Telegram Notifikasi

**Status**: SELESAI — 4 April 2026  
**Kode**: `src/utils/telegram_notifier.py`  
**Integrasi**: `src/orchestrator/pipeline.py` (3 titik inject)  
**Config**: `src/config/tenant_config.py` + `.env`

#### Yang Dikerjakan
- Buat `TelegramNotifier` class dengan 4 method notifikasi:
  - `notify_success()` — video berhasil dipublish ke YouTube
  - `notify_qc_fail()` — video gagal QC, tidak dipublish
  - `notify_publish_fail()` — QC lulus tapi YouTube upload gagal
  - `notify_failure()` — pipeline crash dengan exception
- Fire-and-forget: semua wrapped dalam try-except, tidak pernah crash pipeline
- Per-tenant: `telegram_chat_id` dari `tenant_configs` Supabase, fallback ke env `TELEGRAM_CHAT_ID`
- Format HTML: bold, italic, code block untuk readability di Telegram
- Tambah field ke `TenantRunConfig`: `telegram_enabled`, `telegram_chat_id`, `channel_name`
- Tambah env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` ke `.env` + `.env.example`

#### Migration Supabase yang Diperlukan
Jalankan `scripts/migrate_s81_telegram.sql` di Supabase SQL Editor:
- `ALTER TABLE tenant_configs ADD COLUMN telegram_enabled BOOLEAN DEFAULT true`
- `ALTER TABLE tenant_configs ADD COLUMN telegram_chat_id VARCHAR(50)`
- `ALTER TABLE tenant_configs ADD COLUMN channel_name VARCHAR(100) DEFAULT ''`
- UPDATE `ryan_andrian`: telegram_chat_id=8699847842, channel_name='RAD The Explorer'

#### Cara Test
```bash
# Dari root folder
python3.11 scripts/test_telegram.py
```

#### Bot Info
| Field | Value |
|-------|-------|
| Bot Name | Mesinviral.com |
| Username | @MesinViral_Bot |
| Token | Di `.env` (TELEGRAM_BOT_TOKEN) |
| Chat ID | Di `.env` (TELEGRAM_CHAT_ID) |

#### Format Pesan

**✅ Success:**
```
✅ [RAD The Explorer] Video Published!
🎬 Dark Matter: The Invisible Force...
🎯 Hook score: 92/100  |  🏷 Niche: universe_mysteries
⏱ Durasi: 1:51  |  💾 55.6 MB  |  🎞 6 clips
🔗 https://youtu.be/xxx
⏰ Runtime: 12m 15s  |  📝 216 kata
ryan_andrian_1234567
```

**⚠️ QC Fail:**
```
⚠️ [RAD The Explorer] QC GAGAL — Video tidak dipublish
📋 Topik: The Mystery of Dark Energy...
❌ Alasan: Durasi terlalu pendek: 38.2s < 45s
⏱ Durasi: 38.2s  |  💾 12.5 MB
ryan_andrian_1234567
```

**❌ Pipeline Error:**
```
❌ [RAD The Explorer] Pipeline GAGAL!
🏷 Niche: universe_mysteries
💥 Error: ElevenLabs API timeout after 3 retries...
⏰ Runtime: 4m 5s
ryan_andrian_1234567
```

#### Deploy ke VPS
```bash
# Setelah test lokal berhasil:
git add src/utils/telegram_notifier.py src/orchestrator/pipeline.py \
        src/config/tenant_config.py .env.example scripts/
git commit -m "feat(s81): telegram notifikasi success/qc_fail/failure"
git push origin main

# Di VPS:
git pull origin main
# Edit .env di VPS — tambah TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID
# Jalankan scripts/migrate_s81_telegram.sql di Supabase dashboard
```

---

### ⬜ Item 2 — Regional Targeting Tier-1 di TrendRadar

**Status**: TODO  
**Kode target**: `src/intelligence/trend_radar.py`

#### Rencana
- Tambah parameter `geo` ke Google Trends query (default: `US`)
- Filter YouTube Search result ke region US/UK/CA
- Tambah field `trend_region` di `tenant_configs`: `"us"`, `"uk"`, `"global"`
- Weight sinyal berdasarkan Tier-1 (US bobot tertinggi)
- Update `TenantRunConfig`: gunakan `peak_region` (sudah ada) untuk tentukan geo

#### Schema Change
Tidak ada schema baru — gunakan `peak_region` yang sudah ada di `tenant_configs`.

#### File yang Dimodifikasi
- `src/intelligence/trend_radar.py`
- `src/intelligence/niche_selector.py` (context ke AI: "target audience: US, UK")

---

### ✅ Item 3 — Loop Ending Video

**Status**: SELESAI — 4 April 2026  
**Kode**: `src/production/video_renderer.py` (`_add_loop_ending` method)  
**Config**: `src/config/tenant_config.py` (`loop_ending_enabled`, `loop_ending_duration`)

#### Yang Dikerjakan
- Tambah `TenantRunConfig` fields: `loop_ending_enabled=True`, `loop_ending_duration=1.5`
- Tambah `_add_loop_ending(video_path, loop_duration, output_dir)` di `VideoRenderer`:
  1. ffprobe → dapat durasi video utama
  2. Extract N detik pertama (video only, re-encode) → `_loop_clip.mp4`
  3. xfade `transition=fade:duration=0.5` di offset `main_duration - 0.5`
  4. Replace video asli dengan hasil xfade (fire-and-forget: jika gagal → return video asli)
- Insert setelah music mixing di `render()`: separate try-except block
- load_tenant_config di-cache → panggilan kedua tidak menambah latency

#### Schema Change (Supabase) — Jalankan Manual di Dashboard
```sql
ALTER TABLE tenant_configs
  ADD COLUMN IF NOT EXISTS loop_ending_enabled  BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS loop_ending_duration FLOAT   DEFAULT 1.5;
```

---

### ✅ Item 4a — Niche DB + Schedule Manager + Focus per Slot

**Status**: SELESAI — 4 April 2026  
**Kode**: `src/intelligence/schedule_manager.py`  
**Config**: `src/config/tenant_config.py` (`default_niche_rotation`, `niche_rotation_index`)  
**Migration**: `scripts/migrate_s84_schedules.sql`

#### Yang Dikerjakan
- `niches` table — registry 4 niche aktif (seeded dari NICHES dict)
- `production_schedules` table — 5 slot/hari ryan_andrian, semua `niche_id=NULL` (rotation)
- `ScheduleManager.resolve_slot()` — waterfall 3 layer:
  - Layer 1: production_schedules (niche eksplisit per slot)
  - Layer 2: default_niche_rotation round-robin (index auto-increment)
  - Layer 3: random dari niches table, hindari consecutive duplicate
- `TrendRadar.scan(focus=)` — focus keyword jadi keyword prioritas #1
- `NicheSelector.select(focus=)` — inject FOCUS CONSTRAINT ke AI prompt
- Pipeline resolve_slot sebelum Step 1, override tenant_config.niche
- Verified production: `Layer 2 — rotation: niche=fun_facts` ✅

---

### ✅ Item 4b — ChannelAnalytics — YouTube Analytics Pull

**Status**: SELESAI — 5 April 2026
**Kode**: `src/analytics/channel_analytics.py`
**Migration**: `scripts/migrate_s84b_analytics.sql` — sudah dijalankan di Supabase
**Cron wrapper**: `scripts/fetch_analytics.sh` — perlu ditambah ke crontab VPS

#### Yang Dikerjakan
- Pull YouTube Data API v3: views, likes, comments
- Pull YouTube Analytics API v2: watch_time, avg_view_pct, CTR, subscriber_gain
- Upsert ke `video_analytics`, skip < 48 jam, re-fetch interval 23 jam
- `scripts/reauth_youtube.py` — one-time re-auth untuk full analytics scope

---

### 🔄 Item 4c — PerformanceAnalyzer + channel_insights

**Status**: WIP
**Kode target**: `src/analytics/performance_analyzer.py` (baru)

#### Technical Design — Self-Learning Analytics Engine

Sistem 3 layer yang membuat pipeline makin pintar setiap minggu:



#### A. Hook CTR Analysis
Deteksi pola hook proven tinggi CTR:
- Pattern: "[Entity] that [defies/challenges] [authority]" → CTR 9.2%
- Pattern: "What [scientists/NASA] found [context]" → CTR 8.7%

#### B. Niche Performance Weight
Shift produksi ke niche yang convert ke subscriber tertinggi.

#### C. Content Type Retention


#### D. Historical Factor Score Adjustment
Range: 0.7× (proven poor) → 1.5× (proven winner)

#### Self-Improvement Lifecycle
| Fase | Kondisi | Behavior |
|------|---------|----------|
| `insufficient_data` | < 5 videos | AI estimation murni |
| `learning` | 5–20 videos | Inject top topics, tidak adjust score |
| `optimizing` | 21–50 videos | Full historical_factor + niche weights |
| `peak` | 50+ videos | Hook pattern extraction + A/B testing |

#### File yang Dibuat/Dimodifikasi
- `src/analytics/performance_analyzer.py` (baru)
- `src/intelligence/niche_selector.py` (modified)
- `scripts/compute_insights.sh` (cron mingguan Senin 07:00 UTC)
- `scripts/migrate_s84c_insights.sql` (DDL channel_insights + ALTER video_analytics)

#### Schema Baru (Supabase)
```sql
-- ALTER video_analytics: tambah kolom yang kurang
ALTER TABLE video_analytics
  ADD COLUMN IF NOT EXISTS channel_id     VARCHAR,
  ADD COLUMN IF NOT EXISTS content_type   VARCHAR,
  ADD COLUMN IF NOT EXISTS views_per_sub  FLOAT   DEFAULT 0,
  ADD COLUMN IF NOT EXISTS analytics_date DATE    DEFAULT CURRENT_DATE;

-- Aggregated insights (computed mingguan)
CREATE TABLE IF NOT EXISTS channel_insights (
  insight_id        UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         TEXT      NOT NULL,
  channel_id        VARCHAR,
  computed_at       TIMESTAMP DEFAULT NOW(),
  videos_analyzed   INT       DEFAULT 0,
  niche_weights     JSONB     DEFAULT '{}',
  top_hooks         JSONB     DEFAULT '[]',
  content_type_perf JSONB     DEFAULT '{}',
  avoid_patterns    JSONB     DEFAULT '[]',
  top_topics        JSONB     DEFAULT '[]',
  performance_grade VARCHAR   DEFAULT 'insufficient_data'
);
```

---

### ✅ Item 4d — Feedback Loop NicheSelector (Self-Learning)

**Status**: SELESAI — 5 April 2026
**Kode**: `src/intelligence/niche_selector.py` (modified)

#### Yang Dikerjakan
- Load `channel_insights` terbaru sebelum AI call (fire-and-forget)
- Inject proven patterns ke AI prompt: top topics, high CTR hooks, content type retention, avoid patterns
- Apply `historical_factor` (0.7×–1.5×) ke `viral_score` jika grade >= optimizing
- Grade learning: inject context only, tidak adjust score
- Grade optimizing/peak: full injection + score adjustment
- Tidak pernah crash pipeline jika insights tidak tersedia

#### OAuth Token Refactor (Multi-Channel Ready)
Dilakukan bersamaan dengan 4d untuk fondasi SaaS:
- Konvensi: `tokens/{channel_id}.json` — satu token per channel
- `TenantRunConfig.get_youtube_token_path()` — resolve path otomatis
- `reauth_youtube.py --channel {id}` — re-auth per channel
- `channel_analytics.py` + `youtube_publisher.py` — baca token dari config
- Backward compatible: fallback ke `token_youtube.json`

---

### ⬜ Item 5 — Error Management Profesional

**Status**: TODO  
**Kode target**: `src/utils/exceptions.py` (baru) + semua providers

#### Rencana
- Buat `src/utils/exceptions.py` dengan exception hierarchy:
  ```python
  class MesinViralError(Exception): ...
  class LLMError(MesinViralError): ...
  class TTSError(MesinViralError): ...
  class VisualError(MesinViralError): ...
  class PublishError(MesinViralError): ...
  ```
- Setiap error menyimpan: `provider`, `status_code`, `retry_after`, `is_retryable`
- Rate limit 429: baca header `Retry-After` dan tunggu tepat sesuai instruksi API
- DALL-E content policy rejection: sanitize prompt → retry (max 2×)
- YouTube quota exhausted: langsung `notify_publish_fail` + set flag skip hari ini

---

### ⬜ Item 6 — Niche DB + Keyword Fokus per Slot

**Status**: TODO

#### Schema Baru (Supabase)
```sql
-- Tabel niche resmi
CREATE TABLE niches (
  niche_id         VARCHAR  PRIMARY KEY,
  name             VARCHAR,
  keywords         JSONB,
  style            VARCHAR,
  voice_style      VARCHAR,
  default_hashtags JSONB,
  is_active        BOOLEAN  DEFAULT true,
  created_at       TIMESTAMP DEFAULT NOW()
);

-- Jadwal produksi per channel
CREATE TABLE production_schedules (
  schedule_id      UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id       VARCHAR,
  cron_expression  VARCHAR,
  niche_id         VARCHAR  REFERENCES niches(niche_id),  -- NULL = random
  niche_focus      TEXT,    -- Keyword fokus opsional
  is_active        BOOLEAN  DEFAULT true,
  created_at       TIMESTAMP DEFAULT NOW()
);
```

---

### ⬜ Item 7 — Multi-Channel per Tenant

**Status**: TODO

#### Schema Baru (Supabase)
```sql
CREATE TABLE channels (
  channel_id          VARCHAR  PRIMARY KEY,
  tenant_id           TEXT,
  youtube_channel_id  VARCHAR,
  channel_name        VARCHAR,
  oauth_token_path    VARCHAR,  -- Path ke file token OAuth per channel
  is_active           BOOLEAN  DEFAULT true,
  plan_type           VARCHAR,
  telegram_chat_id    VARCHAR,
  created_at          TIMESTAMP DEFAULT NOW()
);
```

#### File yang Dimodifikasi
- `src/distribution/youtube_publisher.py` — baca oauth_token_path dari channel config
- `src/orchestrator/pipeline.py` — iterate per-channel dari tabel channels

---

### ⬜ Item 8 — Tenant Baru Onboarding

**Status**: TODO  
**Prerequisite**: Item 7 selesai

#### Yang Diperlukan
- Script `scripts/onboard_tenant.py`: interaktif, generate OAuth flow per channel
- Insert ke tabel `tenant_configs` + `channels`
- Test end-to-end dengan 1 tenant baru (channel berbeda)
- Validasi: video berhasil dipublish ke channel baru

---

## CATATAN DEVELOPMENT

### Prinsip yang Tidak Boleh Dilanggar
1. **Pipeline tidak boleh crash** — setiap fitur baru wajib fire-and-forget atau memiliki fallback
2. **Backward compatible** — kode baru tidak boleh merusak pipeline yang sudah berjalan
3. **Supabase kolom baru** — selalu `ADD COLUMN IF NOT EXISTS` + `DEFAULT value` yang aman
4. **Test lokal dulu** — validasi semua fitur di local sebelum push ke VPS
5. **Commit per item** — 1 item selesai = 1 commit + push + deploy VPS

### Deploy Checklist (setiap item)
- [ ] Kode selesai + test lokal OK
- [ ] Migration SQL dijalankan di Supabase dashboard
- [ ] `.env` VPS diupdate jika ada env var baru
- [ ] `git commit` + `git push origin main`
- [ ] `git pull` di VPS
- [ ] Monitor 1 run produksi berikutnya
- [ ] Update `MESIN_VIRAL.md` + `roadmap_1.md` (status → ✅ DONE)
