# ROADMAP MESIN VIRAL — Phase 8a & 8b
> Tujuan: Meningkatkan kualitas viral → monetisasi → 100% siap SaaS  
> Dimulai: 4 April 2026 | Diupdate setiap item selesai + tervalidasi

---

## PROGRESS TRACKER

| # | Item | Tier | Status | Selesai |
|---|------|------|--------|---------|
| 1 | Telegram Notifikasi | 1 | ✅ DONE | 4 Apr 2026 |
| 2 | Regional Targeting Tier-1 di TrendRadar | 1 | ✅ DONE | 4 Apr 2026 |
| 3 | Loop Ending Video | 1 | ✅ DONE | 4 Apr 2026 |
| 4 | ChannelAnalytics + Feedback Loop NicheSelector | 1 | ⬜ TODO | — |
| 5 | Error Management Profesional (exceptions.py) | 2 | ⬜ TODO | — |
| 6 | Niche DB + Keyword Fokus per Slot | 2 | ⬜ TODO | — |
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

### ⬜ Item 4 — ChannelAnalytics + Feedback Loop NicheSelector

**Status**: TODO  
**Kode target**: `src/analytics/` (modul baru)

#### Rencana
- Buat `src/analytics/channel_analytics.py`:
  - Pull data YouTube Analytics API per channel (views, watch_time, CTR, likes, subscribers)
  - Insert/update ke tabel `video_analytics` Supabase
  - Scheduled: 1× per hari via cron terpisah
- Modifikasi `NicheSelector`:
  - Sebelum pilih topik, query top-performing topics dari `video_analytics`
  - Inject data ini sebagai context ke GPT prompt: "Topik yang terbukti viral di channel ini: ..."
  - Avoid topik dengan avg_view_pct < 30% (penonton skip)

#### Schema Change (Supabase)
```sql
CREATE TABLE IF NOT EXISTS video_analytics (
  video_id         VARCHAR  PRIMARY KEY,
  tenant_id        TEXT,
  views            INT      DEFAULT 0,
  watch_time_mins  INT      DEFAULT 0,
  avg_view_pct     FLOAT    DEFAULT 0,
  ctr              FLOAT    DEFAULT 0,
  likes            INT      DEFAULT 0,
  comments         INT      DEFAULT 0,
  shares           INT      DEFAULT 0,
  subscriber_gain  INT      DEFAULT 0,
  fetched_at       TIMESTAMP DEFAULT NOW()
);
```

#### File Baru
- `src/analytics/channel_analytics.py`
- `src/analytics/__init__.py` (update dari kosong)
- `scripts/fetch_analytics.sh` (cron wrapper)

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
