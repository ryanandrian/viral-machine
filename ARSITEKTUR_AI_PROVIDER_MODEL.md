# Arsitektur AI Provider & AI Model — MesinViral (end-to-end)

> **STATUS: DOKUMEN REFERENSI — SELESAI (permintaan owner 2026-07-07).** Bukan daftar kerja; tak ada item menggantung di sini. Peta arsitektur untuk dipahami owner+Claude. Update bila arsitektur berubah.

> **Tujuan dokumen:** peta LENGKAP & akurat rantai AI, dari admin mendaftarkan provider/model → integrasi tenant → dipakai mesin (worker/pipeline) → sinkronisasi harga → biaya produksi per 1 video. Semua nama file & fungsi di bawah **terverifikasi langsung dari kode & DB live** (2026-07-07), bukan asumsi.
>
> **Prinsip yang menopang seluruh arsitektur ini:**
> 1. **Sumber tunggal di KODE.** Nilai-sah (adapter/enum) berasal dari registry kode, dicerminkan ke DB tiap startup → nol drift.
> 2. **Gagal-aman & jujur.** Salah isi → mesin berhenti dengan pesan jelas, bukan diam-diam menghasilkan video rusak.
> 3. **No hardcode.** Provider/model/harga = data (DB), bisa dikelola admin tanpa bongkar skrip.
> 4. **Aktif = terbukti.** Model hanya diaktifkan setelah lulus uji nyata (tombol "Uji").

---

## 1. Peta besar (5 babak)

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  BABAK 1 — ADMIN menyediakan katalog          (Panel Admin → Katalog AI)       │
  │     Provider (adapter, auth, base_url, harga-prefix)                           │
  │       └─ Model (component: llm/tts/image/video, model_id, tier)                │
  │       └─ TTS profile + Voice + Bahasa + Durasi                                 │
  │     Tombol "Uji" → jalankan adapter NYATA → LULUS/GAGAL (cost_hint.audit)       │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                   │ (katalog aktif = boleh dipilih tenant)
  ┌───────────────────────────────▼──────────────────────────────────────────────┐
  │  BABAK 2 — SINKRONISASI HARGA (otomatis, worker)                               │
  │     feed publik (LiteLLM/OpenRouter) → ai_models.pricing  ·  kurs USD→IDR       │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                   │
  ┌───────────────────────────────▼──────────────────────────────────────────────┐
  │  BABAK 3 — TENANT menyetor kredensial          (Panel Tenant → Integrasi)      │
  │     "Simpan & Uji" token → uji nyata ke vendor → status valid/invalid          │
  │     KOLAM kredensial tenant (banyak token, banyak vendor)  → tenant_ai_accounts │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                   │
  ┌───────────────────────────────▼──────────────────────────────────────────────┐
  │  BABAK 4 — TENANT menugaskan di Channel Setting  (Panel Tenant → Channel)      │
  │     Per elemen (LLM/TTS/Visual): pilih Provider → Model → Akun(token)           │
  │     Hanya provider+model AKTIF & terbukti yg muncul  → channels.*_account_id    │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                   │ (channel siap → produksi berjalan)
  ┌───────────────────────────────▼──────────────────────────────────────────────┐
  │  BABAK 5 — MESIN memproduksi + menghitung biaya  (Worker → Pipeline)           │
  │     build provider dari model+akun → panggil API vendor (token tenant)          │
  │     cost_meter mencatat konsumsi → compute_cost_usd → production_runs           │
  └────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tabel database (semua yang terkait rantai ini)

| Tabel | Peran | Kolom kunci |
|---|---|---|
| `ai_providers` | Vendor AI (INDUK). 1 baris = 1 penyedia. | `provider_key`(PK), `display_name`, `adapter`, `auth_type`, `key_group`, `base_url`, `price_feed_prefix`, `free_tier_note`, `is_active` |
| `ai_models` | Model (DETAIL provider). | `model_key`(PK), `provider_key`(FK), `component`(llm/tts/image/video), `model_id`(id resmi vendor), `display_name`, `quality_tier`, `sort_order`, `pricing`(jsonb), `pricing_locked`, `pricing_pending`, `cost_hint`(jsonb; berisi `audit` — stempel hasil tombol Uji), `is_active`, **`unavailable_since`** + **`unavailable_reason`** (21-Agu: jejak karantina otomatis saat model TERBUKTI mati di vendor; ditulis mesin. ⚠️ **belum ada jalur bersih dari panel** — lihat §9) |
| `tts_profiles` | Protokol TTS per provider. | `provider_key`(PK), `adapter`, `tts_class`(timed/fast_fallback), `delivery_wps`, `speed_param`, `param_schema`, `is_active` |
| `voice_catalog` | Katalog suara (per provider TTS). | `voice_key`(PK), `provider_key`, `locale`, `language`, `gender`, `delivery_wps`, `preview_url`, `default_settings`, `is_active` |
| `content_languages` | Bahasa konten yg didukung. | `locale`(PK), `display_name`, `quality_tier`(official/experimental), `caption_font`, `is_active` |
| `duration_presets` | Preset durasi video. | `seconds`(PK), `use_case`, `is_active`, `is_default` |
| `catalog_valid_values` | **CERMIN nilai-sah dari registry KODE** (adapter/enum). Anti-drift, self-heal tiap startup. | `field`+`value`(PK), `label` |
| `tenant_ai_accounts` | **KOLAM kredensial tenant** (Fernet-encrypted). | `id`(PK), `tenant_id`, `provider_key`, `key_group`, `label`, `key_enc`, `status`(valid/invalid/unchecked), `validated_at` |
| `tenant_youtube_accounts` | Koneksi YouTube tenant (OAuth). | `tenant_id`, `channel/token` |
| `channels` | Channel tenant + penugasan AI. | `id`(PK), `tenant_id`, `llm_library`+`llm_model`+`llm_account_id`, `tts_provider`+`tts_model`+`voice_key`+`tts_account_id`, `visual_mode`(`ai_image:<model_key>`)+`visual_account_id`, `content_language`, `duration_preset` |
| `tenant_configs` | Config tenant-wide + langganan. | `tenant_id`, `plan_type`, `subscription_status`, `usd_idr_rate`(display) |
| `production_runs` | Ledger tiap run produksi (+biaya). | `run_metadata`(jsonb: `ai_usage`, `cost`), `error_class`, **`failed_model`** (21-Agu: model yang ditolak vendor — dipakai bukti-silang antar-tenant untuk karantina; tanpa FK supaya riwayat utuh walau katalog berubah) |
| `system_state` | Stempel sinkron. | `ai_price_synced_at`, `fx_synced_at` |
| `app_config` | Konfigurasi platform. | `usd_idr_rate`, `usd_idr_rate_locked` |

---

## 3. BABAK 1 — Admin menyediakan katalog

**Layar:** Panel Admin → **Katalog AI** (tab: Providers · AI Models · Music · Moods · Voice · Languages · Durasi · Niche).
Alur: admin daftar **Provider** dulu → tambah **Model** di bawahnya (＋ Model) → set **TTS profile / Voice / Bahasa / Durasi**. Field enum (`adapter`, `auth_type`, `component`, `quality_tier`, `gender`, `tts_class`) = **dropdown** dari `catalog_valid_values`; FK (`provider_key`) = dropdown; angka (`sort_order`, `delivery_wps`) tervalidasi; sisanya free text sah (identifier/label/URL). Tombol **"Uji"** membuktikan model benar jalan sebelum diaktifkan.

**File:**
| File | Fungsi/proses |
|---|---|
| `apps/web/src/app/admin/(panel)/catalog/page.tsx` | Halaman katalog. `ADD_FIELDS`/`ENUM_FIELD_SRC` (definisi field+enum), `renderField` (dropdown/teks terpadu Add+Edit), tombol **Uji** (`runTest`), badge status uji (dari `cost_hint.audit`), `probePrice` (peringatan harga saat simpan). |
| `apps/web/src/app/api/admin/catalog/route.ts` | API CRUD katalog (service_role, super-admin). `CATALOG`(allowlist tabel+kolom), `coerceValue`(JSON/numerik), `ENUM_COLS`+`assertEnums`(tolak nilai di luar `catalog_valid_values`), GET (kirim semua data + `catalog_valid_values`), PATCH/POST/DELETE(+ref-guard). |
| `apps/web/src/app/api/admin/catalog/test-model/route.ts` | Proxy "Uji model" → vault Python (super-admin guard). |
| `apps/web/src/app/api/admin/catalog/price-probe/route.ts` | Proxy probe harga 1 model → vault Python. |
| `src/config/catalog_sync.py` | **Sumber tunggal.** `collect_valid_values()` (kumpulkan adapter dari registry LLM/TTS/visual + konstanta auth_type/component/tier/gender/tts_class), `sync_catalog_valid_values()` (upsert→DB, hapus usang). Dipanggil saat **startup** webhook & worker. |
| `src/config/model_tester.py` | `test_model(model_key, key)` — jalankan adapter **produksi NYATA** sekali (LLM `complete`/TTS `generate`/image `_generate_image`); vendor keyless tanpa kunci; stamp hasil ke `cost_hint.audit`. **2026-07-08:** image memakai injeksi `model_row` (baris DB tanpa filter aktif) — model image NONAKTIF bisa diuji sebelum aktivasi (dulu telur-ayam: mustahil lulus uji). |
| `src/billing/webhook_app.py` | Endpoint `/api/admin/catalog/test-model` & `/api/admin/catalog/price-probe` (auth `X-Internal-Secret`), + startup event `sync_catalog_valid_values()`. |
| `apps/web/src/lib/admin/guard.ts` | `requireSuperAdmin()` — gerbang super-admin semua route admin. |
| `apps/web/src/lib/supabase/admin.ts` | `createAdminClient()` — klien service_role (bypass RLS). |

---

## 4. BABAK 2 — Sinkronisasi harga (otomatis)

Worker menarik harga dari feed publik → mencocokkan tiap model (id persis → prefix per-vendor `price_feed_prefix` → jaring pengaman legacy → fallback OpenRouter utk LLM) → tulis `ai_models.pricing`. Perubahan drastis ditahan di `pricing_pending` (keputusan admin). `pricing_locked` dihormati (harga manual, mis. Edge=0). Kurs USD→IDR disinkron terpisah untuk **tampilan** biaya.

**File:**
| File | Fungsi/proses |
|---|---|
| `src/billing/price_sync.py` | `sync_prices(sb, force, only_model_key)` (sinkron semua / 1 model utk probe), `_feed_entry()` (matching id/prefix), `_sanity_violation()` (guard drastis→pending), `sync_fx_rate()` (kurs USD→IDR ke `app_config.usd_idr_rate`), `_check_staleness()`. |
| `src/orchestrator/trend_refresher.py` / loop worker | Memanggil `sync_prices()`/`sync_fx_rate()` berkala (di `scripts/worker_decoupled.py`). |

---

## 5. BABAK 3 — Tenant menyetor kredensial (Integrasi)

Tenant melihat provider aktif (badge gratis/berbayar), tempel API token, klik **"Simpan & Uji"** → uji nyata ke vendor → status `valid`/`invalid`. Tenant boleh simpan **banyak token** (banyak vendor, >1 per vendor) = KOLAM. Token disimpan **terenkripsi Fernet** di `tenant_ai_accounts`; `.env` HANYA memegang kredensial platform.

**File:**
| File | Fungsi/proses |
|---|---|
| `apps/web/src/app/(app)/integrations/page.tsx` | Halaman Integrasi: daftar provider (per-vendor, incl. model nonaktif + badge "model segera hadir"), form Simpan & Uji, status. |
| `apps/web/src/app/api/credentials/ai/route.ts` (+`/delete`) | Proxy Next → vault Python. |
| `src/utils/api_key_vault.py` | `validate_ai_key()` (uji nyata; ElevenLabs scoped 401→valid; **cloudflare** = kunci gabungan `ACCOUNT_ID:API_TOKEN`, uji `GET /ai/models/search`), `set_ai_account()`/`delete_ai_account()`/`list_ai_accounts()` (kelola KOLAM, key_group dari katalog), `validate_telegram()`. FE Integrasi: provider cloudflare = **dua kolom** (Account ID + Token) digabung sistem — anti salah-format (2026-07-08). |
| `src/utils/crypto.py` | `encrypt()`/`decrypt()` Fernet (master key hanya di server Python). |
| `src/billing/webhook_app.py` | Endpoint `/api/credentials/ai*` (auth `X-Internal-Secret`). |
| `apps/web/src/lib/youtube.ts` | Helper `vault(path, body)` — panggil webhook Python + secret. |

---

## 6. BABAK 4 — Tenant menugaskan di Channel Setting

Per channel, per elemen (LLM/TTS/Visual): pilih **Provider → Model → Akun**. Hanya provider **aktif** (`ai_providers.is_active`) + model **aktif** yang muncul (mesin `get_providers()` hanya kenal provider aktif → yang nonaktif akan ditolak, jadi tak boleh muncul). Channel belum lengkap → ditandai "belum siap" (`channel_missing`) → produksi tak jalan.

**File:**
| File | Fungsi/proses |
|---|---|
| `apps/web/src/app/(app)/channels/[id]/page.tsx` | Setting AI channel: muat katalog (disaring provider aktif), pemilih Provider/Model/Akun per elemen — **budget-aware** (badge tier + tag Gratis + tooltip harga Rp, urut `sort_order`); panel **uji produksi/recover** (konfirmasi + progres + hasil sopan + tautan YT Studio + siklus hidup Tutup/TTL); readiness. |
| `apps/web/src/app/(app)/channels/page.tsx` | Daftar channel + status pause. |
| `apps/web/src/app/api/channels/[id]/test/route.ts` | Endpoint uji channel: GET hasil test terakhir (per-channel) + POST enqueue `direct_jobs` (job_type `test` = upload privat YouTube; gate `channel_readiness`). |
| `apps/web/src/components/test-niche-panel.tsx` | Panel uji bersama (niche + channel): konfirmasi, stepper progres nyata, hasil, polling 5 dtk; props opsional konteks. |
| `apps/web/src/lib/test-run.ts` | `latestTestResult()` — status + progres (parse `pipeline_run_logs`) + `youtube_video_id` + presign video; key per-niche ATAU per-channel. |
| DB fn `channel_missing()` / RPC `channel_readiness` | Satu sumber kesiapan (identik FE & worker). |
| `app_config.test_result_ttl_hours` (migr 0145) | Batas usang kartu hasil uji (admin-editable, fail-soft 24 jam). |

---

## 7. BABAK 5 — Mesin memproduksi + biaya per video

Worker (systemd `mv-worker`) menjalankan loop konkuren. **Producer** mengambil channel siap → **Pipeline** memproduksi 1 video: muat run-config (termasuk **kunci dari KOLAM**), reset `cost_meter`, hasilkan naskah (LLM) → prompt visual → durasi beat → suara (TTS) → gambar (Visual) → render → QC → publish. Tiap panggilan API dicatat `cost_meter`; di akhir, konsumsi dikonversi ke USD lewat harga katalog dan disimpan di `production_runs.run_metadata`.

**Rantai build provider (DB-driven, gagal-jujur):**
```
channels.llm_library  → get_providers()[key].adapter → ADAPTERS[adapter] → provider.complete()
channels.tts_provider → tts_profiles.adapter → _adapter_registry()[adapter] → provider.generate()
   model suara: channels.tts_model → resolve_model_id() → ai_models.model_id → dikirim ke vendor
   (22-Agu: SEBELUM ini jalur suara mengirim model_key APA ADANYA — melanggar §2. Model ber-key≠id
    LULUS tombol Uji tapi PASTI gagal produksi; kini selaras dgn naskah/gambar/video.)
channels.visual_mode  → platform=provider_key → _TRANSPORTS[platform] → _generate_image()
kunci: channels.*_account_id → tenant_ai_accounts (decrypt Fernet)
```

**File:**
| File | Fungsi/proses |
|---|---|
| `scripts/worker_decoupled.py` | Entrypoint worker. Start thread: producer, publisher, janitor, self_learning, dll + startup `sync_catalog_valid_values()`. |
| `src/orchestrator/producer.py` | `produce_one()` (produksi→buffer), direct-jobs (test/recover; sukses → auto-unpause channel), `_cost_fields(result)` (→ `compute_cost_usd`, simpan `ai_usage`+`cost` ke `run_metadata`). |
| `src/orchestrator/buffer_janitor.py` | Janitor: sweep stale/orphan S3, prune logs, pemicu `sync_prices`/`sync_fx_rate`, **`reap_stuck_direct_jobs()`** (job uji macet > `DIRECT_JOB_TTL_MINUTES` → failed + pesan). |
| `src/orchestrator/pipeline.py` | `Pipeline.run()` — orkestrasi 1 video A-Z; `_load_tenant_run_config()`; reset & `cost_meter.summary()` masuk `result["ai_usage"]`. |
| `src/orchestrator/publisher.py` | Publikasi video buffer → YouTube. |
| `src/config/tenant_config.py` | `load_tenant_config()` (gabung channels + tenant_configs; **cache TTL 120s** — perubahan setelan terbaca tanpa restart worker, fix insiden 2026-07-08), `_set_key_from_pool()` (ambil kunci elemen dari `tenant_ai_accounts` sesuai `*_account_id`), `llm_model_for(task)` (**penyedia channel ≠ tenant → `llm_models` tenant gugur, model channel dipakai semua task** — G3-slice 2026-07-08). |
| `src/intelligence/config.py` | `TenantConfig`, `tenant_config_from_channel()` (channel row → config; `content_language`→bahasa). |
| `src/providers/llm/__init__.py` | `build_llm_provider(cfg)` — resolve provider dari katalog + `ADAPTERS[adapter]`; gagal-jujur bila adapter tak didukung. |
| `src/providers/llm/adapters.py` | `ADAPTERS` (registry: `openai_chat`, `anthropic_messages`, **`fal_any_llm`** — ditambah sesudah 9-Jul); `.complete()` + `cost_meter.add_llm()`. |
| `src/providers/llm/catalog.py` | `get_providers()` — muat `ai_providers` **aktif** dari DB (cache). |
| `src/providers/tts/__init__.py` | `build_tts_provider()`, `_adapter_registry()` (`elevenlabs`/`openai_speech`/`edge`/`gemini_speech`/**`fal_tts`**). ⚠️ Protokol TTS dibaca dari **`tts_profiles.adapter`**, BUKAN `ai_providers.adapter`. Peta legacy `_LEGACY_ADAPTER` hanya menutup 3 penyedia lama (`elevenlabs`·`openai_tts`·`edge_tts`) bila kolomnya NULL — penyedia BARU dengan adapter kosong gagal jujur (`TTSError`). |
| `src/providers/tts/{elevenlabs,openai_tts,edge_tts,gemini_tts}.py` | Adapter TTS; `.generate()` + `cost_meter.add_tts()`. |
| `src/providers/visual/ai_image.py` | `AIImageProvider`, `_TRANSPORTS` (`openai`/`gemini`/`cloudflare`/**`fal`** — Replicate+Together DIBUANG TUNTAS 2026-07-09, wajib kartu kredit & kalah dari Cloudflare gratis), `_generate_image()` + `cost_meter.add_image()`. Cloudflare (2026-07-08): kunci pool `ACCOUNT_ID:API_TOKEN`, prompt murni tanpa negative (NSFW filter CF false-positive), free-tier 10k neuron/hari — model `cf-flux-schnell` LULUS uji nyata. |
| `src/providers/visual/ai_video.py` | `AIVideoProvider` (text-to-video 1 klip 9:16, `component='video'`). Transport = **`provider_key` mentah**, dan hari ini hanya **`fal`**. Butuh `duration_presets` ber-`render_mode='ai_video'` aktif, serta `default_params` `{aspect_ratio,duration,duration_param,allowed_durations}`. ⚠️ Gambar & video **tak punya lapis adapter** — vendor baru SELALU butuh kode kecuali `provider_key`-nya persis salah satu transport yang ada. |
| `src/config/format_catalog.py` | `tts_adapter()`, `tts_class()`, `tts_max_chars()` — baca protokol & batas huruf dari `tts_profiles`. ⚠️ Dibaca **tanpa** filter `is_active`: mematikan `tts_profiles` tidak menghentikan produksi, ia hanya menyembunyikan penyedia dari pemilih tenant. |
| `src/production/{tts_engine,video_renderer,visual_assembler}.py` | Sintesis suara, rakit visual, render video. |
| `src/intelligence/script_engine.py` | Hasilkan naskah + prompt visual (LLM). |

**Biaya produksi per 1 video:**
| File | Fungsi/proses |
|---|---|
| `src/utils/cost_meter.py` | Meteran konsumsi thread-local: `reset()`, `add_llm(model,tin,tout)`, `add_image(model,n)`, `add_tts(model,chars)`, `summary()`. |
| `src/billing/ai_cost.py` | `compute_cost_usd(ai_usage)` — konsumsi × harga katalog (`ai_models.pricing`) → `{usd, breakdown:{llm,image,tts}, unpriced, priced_at}`. Model gambar ber-tagih token (gpt-image) dihitung di bucket llm. |

**Rumus biaya (jujur = konsumsi terukur × harga katalog):**
```
biaya_llm   = Σ (tokens_in/1e6 × in_per_1m + tokens_out/1e6 × out_per_1m)
biaya_image = Σ (jumlah_gambar × per_image)          [kecuali gpt-image → via token llm]
biaya_tts   = Σ (chars/1e6 × per_1m_chars)
biaya_video_USD = biaya_llm + biaya_image + biaya_tts        → disimpan di production_runs.run_metadata.cost
biaya_video_IDR = biaya_video_USD × app_config.usd_idr_rate  (tampilan)
```

---

## 8. Ringkasan "siapa menegakkan janji apa"

| Janji ke tenant | Ditegakkan oleh |
|---|---|
| Model aktif = pasti jalan | Tombol **Uji** (`model_tester`) + stempel `cost_hint.audit` + badge FE — **dan sejak 22-Agu DITEGAKKAN MESIN**: trigger `trg_gate_aktif_terbukti` (migr `0208`) menolak menyalakan model yang auditnya bukan `LULUS`, **atau** yang auditnya **lebih tua dari `unavailable_since`**-nya. Sampai 22-Agu janji ini bersandar DISIPLIN saja |
| "Valid" = token benar bisa dipakai | `validate_ai_key` (uji nyata, termasuk EL scoped) |
| Yang muncul di Channel = pasti aktif & jalan | filter provider aktif (FE) + `assertEnums` + `get_providers()` (aktif-only) |
| Harga akurat & otomatis | `price_sync` (feed + prefix data-driven, no hardcode) |
| Biaya per video benar | `cost_meter` → `compute_cost_usd` (× `usd_idr_rate`) |
| Adapter/vendor baru tanpa bongkar skrip | `catalog_sync` (cermin registry kode, self-heal) |

---

---

## 9. PRASYARAT & KORIDOR menambah provider/model — *ditetapkan 22-Agu atas permintaan owner*

> Owner 21-Agu: *"anda harus menetapkan prasyarat yang jelas untuk menambahkan provider dan model baru
> yang sesuai dengan kondisi mesin (bisa di support oleh mesin) tanpa menimbulkan masalah."*
> Bagian ini menetapkannya. Prasyarat **registry galat** ada terpisah di `AI_ERROR_MANAGEMENT §5`.

### 9.1 KORIDOR — 7 langkah, urut, tak boleh dilompati

| # | Langkah | Layar | Berlaku |
|---|---|---|---|
| 1 | Buat **Provider** | tab Providers | semua |
| 2 | Buat **Model** (`＋ Model` dari baris provider) | tab AI Models | semua |
| 3 | **Setelan suara** (`tts_profiles`) + ≥1 **karakter suara** (`voice_catalog`) | tab Voice | **hanya `tts`** |
| 4 | **Preset durasi** ber-`render_mode='ai_video'` aktif | tab Durasi | **hanya `video`** |
| 5 | **Uji** — panggilan NYATA ke vendor → `cost_hint.audit` | tombol Uji | semua |
| 6 | Nyalakan (`is_active`) | saklar | semua |
| 7 | Tenant memasang kunci → memilih model di channel | Integrasi & Channel | semua |

**Fakta yang menopang urutan ini (terukur 22-Agu):**
- Provider **tidak tampil** di layar Integrasi tenant sampai ia punya **≥1 model** (aktif atau tidak).
  ⇒ langkah 1 tanpa langkah 2 = provider tak terlihat siapa pun.
- Model **nonaktif tetap bisa diuji** (injeksi `model_row`, 8-Jul) ⇒ urutan "buat → uji → nyalakan" sah,
  bukan telur-ayam.
- Layar Integrasi sengaja membaca model **aktif + nonaktif** + badge *"model segera hadir"* ⇒ baris baru
  yang lahir nonaktif **tidak** menyembunyikan providernya.
- 41 dari 41 model aktif ber-`cost_hint.audit` = LULUS ⇒ langkah 5 sudah jadi **kebiasaan**, tapi
  **belum jadi aturan yang ditegakkan mesin** (janji §8 "Model aktif = pasti jalan" bersandar pada
  disiplin admin).

### 9.2 Prasyarat per kolom — dan akibat NYATA bila salah

| Kolom | Aturan | Akibat bila salah/kosong |
|---|---|---|
| `ai_providers.adapter` | ∈ `catalog_valid_values` — **dropdown**, mustahil salah ketik | protokol tak dikenal = **butuh pekerjaan KODE** |
| `ai_providers.auth_type` | `api_key` / `none` — dropdown | `api_key` tanpa resep uji ⇒ kunci `unchecked` = **tersimpan tapi tak pernah dipakai** |
| `ai_providers.key_group` | vendor pemilik kunci; 1 kunci melayani semua elemennya | **kunci tenant tak ditemukan** meski sudah dipasang |
| `ai_providers.base_url` | wajib untuk vendor OpenAI-compatible | panggilan ke alamat salah |
| `ai_models.model_id` | **ID resmi vendor** (bukan `model_key`), sertakan versi | gagal di vendor tiap produksi |
| `ai_models.default_params` | **gambar** `{size,steps}` · **video** `{aspect_ratio,duration,duration_param,allowed_durations}` · naskah/suara `{}` | dikirim **apa adanya** ke vendor: kunci ngawur = 400, dan penolakan parameter berkelas `UNKNOWN` = **boleh diulang** ⇒ kredit tenant terbakar (anatomi insiden `seed`, 37 kejadian) |
| `ai_models.pricing` | wajib sebelum dinyalakan; `per_request_usd`/`per_second_usd`/trio video **tak pernah** ditulis sinkron otomatis | biaya tenant **dilaporkan lebih murah dari kenyataan**, produksi tetap jalan (**nol rem berbasis biaya**) |
| `tts_profiles.adapter` | ∈ `tts_adapter` | penyedia BARU dengan adapter kosong ⇒ `TTSError` |
| `tts_profiles.delivery_wps` | wajib benar | kosong ⇒ jatuh **senyap** ke 2.4 ⇒ anggaran kata salah ⇒ durasi melenceng ⇒ QC menolak |
| `voice_catalog.preview_url` | wajib (ditegakkan `tests/test_katalog_suara_tak_menipu.py`) | tenant memilih suara tanpa mendengarnya |
| `galat_registry.PENYEDIA` | wajib punya baris (`AI_ERROR_MANAGEMENT §5`) | galat vendor → `UNKNOWN` = **diulang 3×** ⇒ **kredit TENANT terbakar** |

### 9.3 CUKUP DATA vs BUTUH KODE — pembeda "mudah" atau tidak

| Komponen | Sumber dispatch | Didukung hari ini |
|---|---|---|
| naskah | `ai_providers.adapter` | `anthropic_messages` · `openai_chat` · `fal_any_llm` |
| suara | **`tts_profiles.adapter`** | `fal_tts` · `elevenlabs` · `openai_speech` · `edge` · `gemini_speech` |
| gambar | **`provider_key` mentah** (nol lapis adapter) | `openai` · `gemini` · `cloudflare` · `fal` |
| video | **`provider_key` mentah** (nol lapis adapter) | `fal` **saja** |

⇒ Vendor berprotokol OpenAI-chat = **cukup data, nol kode**. Selain itu **butuh kode**.

### 9.4 TITIK LEMAH — status 22-Agu (B1–B6 · F1–F5 · G1–G5 SUDAH ditutup)

> **Pemicu G1–G5:** owner menyalakan kembali `gemini-2.5-flash` dari panel dan bertanya *"MENGAPA
> TIDAK ADA INDIKATOR UNTUK YANG MATI?"*. Terukur saat itu: lencana berbunyi **"✓ Teruji"** — dari
> **6 Juli** — sementara model itu **terbukti mati di vendor 18-Agu** dan `Abyss ID` (channel AKTIF)
> memakainya. Jejak karantina SUDAH dikirim rute ke layar tapi layar **nol kali** menampilkannya,
> dan **B5 (dipasang beberapa jam sebelumnya) justru MENGHAPUS jejak itu** saat model dinyalakan —
> penghapus bukti dibangun sebelum penampil bukti. Cacat rancangan saya.
>
> | | Ditutup |
> |---|---|
> | **G1** | tabel AI Models menyebut **"dipakai berapa channel"** (kuning = ada channel AKTIF) — dihitung server sekali per muat, bukan per baris |
> | **G2** | jejak karantina **DITAMPILKAN** sebagai lencana `terbukti mati` + alasan vendor di tooltip |
> | ~~**G3**~~ | ⛔ **DIBUANG owner 22-Agu.** Label `BASI` + umur uji menetapkan kewajiban kerja (uji ulang tiap 30 hari) **tanpa kesepakatan owner**, ambangnya **hardcode** (nilai bisnis wajib dari config), dan angka 30 itu **karangan** dari dua titik data. Akibat terukur: **29 dari 42 model (69%) berlencana kuning** ⇒ peringatan yang menyala di dua pertiga baris MENYEMBUNYIKAN yang benar-benar bermasalah. Risikonya sudah dijaga karantina + label `terbukti mati` dengan biaya NOL dan tanpa beban kerja admin. Dilarang kembali oleh uji. |
> | **G4** | migr `0208` — **menyalakan wajib TERBUKTI**: audit `LULUS` **dan lebih baru dari bukti kematian**. Di DB, bukan panel, karena jalur yang memutari panel sudah terbukti dipakai. Terukur: 43/43 model aktif lolos ⇒ nol terkunci |
> | **G5** | **koreksi B5**: jejak dibersihkan HANYA bila ada uji yang lebih baru daripada jejak itu — bukan sekadar karena model dinyalakan |
>
> **Bukti G4 pada kasus nyata (bertransaksi, seluruhnya di-rollback):** 43 baris aktif tersunting
> tanpa ditahan · mematikan tetap bebas · 3 model tanpa uji **ditolak** · audit 6-Jul + kematian
> 18-Agu **ditolak** (`uji_lebih_tua_dari_kematian`) · audit 22-Agu sesudah kematian **lolos**.

#### Sisa kondisi lapangan

> **Penjaganya:** `tests/test_panel_katalog_menuntun_bukan_menjebak.py` (B1–B6) + `tests/test_katalog_nol_fosil_nol_lapis_ganda.py` (F1–F5) + `tests/test_panel_mengatakan_kebenaran_status_model.py` (G1–G5: pemakaian, jejak karantina, umur uji, gerbang terbukti, koreksi pembersihan) — 17 uji, **14 dibuktikan
> MERAH dulu**, **20 sabotase** semuanya merah. Sabotase menangkap **9 uji palsu saya sendiri**
> (substring `xhelp_id` masih memuat `help_id` · dua bahasa diperiksa sebagai satu teks · kata
> `catch` bebas · jendela karakter yang tak mencapai kodenya · kata "suara" yang sudah ada di
> kalimat pertama). Semuanya diganti.

Dokumen ini menulis bahwa admin "set TTS profile / Voice / Bahasa / Durasi" di BABAK 1. Diperiksa ke
kode 22-Agu: **`tts_profiles` tak punya jalur BUAT dari panel** — ia satu-satunya tabel yang boleh
DIHAPUS panel tapi tak bisa dibuat darinya. Itu sebab TTS Gemini dulu lahir dari **skrip**, bukan layar.

| Titik | Keadaan terukur |
|---|---|
| ~~`tts_profiles.display_name` + `adapter`~~ | ✅ **DITUTUP 22-Agu (B4)** — dulu DIBUANG SENYAP — form mengirim, whitelist API tak memuatnya ⇒ hilang, toast tetap "Tersimpan". Efek ikutan: `ENUM_COLS.tts_profiles.adapter` = **kode mati** |
| ~~`tts_profiles` (barisnya)~~ | ✅ **DITUTUP 22-Agu (B6)** — barisnya kini **disiapkan otomatis** saat admin membuat model ber-`component='tts'` (langkah 2 koridor), lahir **NONAKTIF** dengan `adapter` **kosong** (protokol tak boleh ditebak sistem), tak menimpa baris yang sudah ada, dan **fail-soft**. Dilengkapi lewat editor ✎ yang SUDAH ADA di tabel setelan suara. **Nol tombol/tab baru** — rancangan 21-Agu yang menambah pintu baru DITOLAK owner |
| ~~`ai_models.default_params`~~ | ✅ **DITUTUP 22-Agu (B2)** — kini berlabel manusiawi + arahan dwibahasa yang menyebut contoh siap-tempel per jenis. Dulu: **nol label & nol arahan** — padahal penentu gambar/video. **Titik terlemah seluruh rantai** |
| ~~Koridor §9.1~~ | ✅ **DITUTUP 22-Agu (B3)** — arahan pada isian **Jenis model** menunjuk tab tujuannya (tab Voice utk suara, tab Durasi utk video) lalu Uji → nyalakan. Dulu: **nol** tuntunan di layar: jenis `tts` butuh langkah 3, `video` butuh langkah 4 — tak disebut sepatah pun |
| ~~Jendela pop-up katalog~~ | ✅ **DITUTUP 22-Agu (B1)** — form katalog 720px, sisanya 560px, pola `min(px,vw)` dipertahankan agar tetap responsif. Dulu **440px** untuk form 15 isian (voice) & baris JSON panjang (models) ⇒ **terpotong** |
| ~~Form `voice` · `moods` · `durations`~~ | ✅ **DITUTUP 22-Agu (B3)** — seluruh isian di 7 form katalog kini berlabel manusiawi; isian yang berakibat bila salah punya arahan dwibahasa. Dulu: 7 · 2 · 2 tanpa label; 4 · 0 · 3 tanpa arahan |
| ~~`ai_models.unavailable_since`/`unavailable_reason`~~ | ✅ **DITUTUP 22-Agu (B5)** — menyalakan kembali model membersihkan jejaknya, **hanya** pada arah nyala (karantina menulis jejak saat mematikan). Kedua kolom sengaja **tetap di luar** whitelist: jejak adalah tulisan MESIN, admin tak boleh mengarangnya |
| ~~`ai_providers.request_param_schema`~~ | ✅ **DITUTUP 22-Agu (F2)** — kini ada di form penyedia, berlabel + arahan dwibahasa, diurai sebagai JSON (tanpa penguraian ia tersimpan sebagai string mentah dan mesin membacanya kosong — gagal senyap). Dulu **HIDUP tapi tak terkelola**; dokumen lain pernah menyebutnya "kolom mati" — **klaim itu SALAH & sudah ditarik** |
| `ai_models.quality_tier` | **nol pembaca di mesin** — murni tampilan pemilih tenant. Bukan fosil: ia DIPAKAI layar tenant, jadi dibiarkan |
| ~~3 kolom fosil~~ | ✅ **DIBUANG 22-Agu (F1, migr `0207`)** — `tts_profiles.has_word_timeframe` (sumber kebenaran KEDUA untuk `tts_class`, nilainya cermin 1:1), `voice_catalog.pace_sample_n` + `pace_updated_at` (0 dari 44 terisi). Nol pembaca & nol penulis. Kalibrasi tempo yang sungguhan hidup di `tts_pace_calibration` |
| ~~`voice_catalog` boleh dihapus TANPA penjaga~~ | ✅ **DITUTUP 22-Agu (F5)** — **bug yang ditemukan saat menyatukan penghitung**: tabel ini ada di `DELETABLE` tapi `refGuard` tak punya cabang untuknya ⇒ karakter suara yang sedang dipakai channel tenant bisa TERHAPUS dan channel itu menggantung. Saat ditemukan: 6 channel memakai suara, 3 di antaranya AKTIF. Kini ditolak + disarankan nonaktifkan, dan **setiap** tabel `DELETABLE` wajib punya penjaga (dikunci uji) |
| ~~Jalur suara mengirim `model_key`~~ | ✅ **DITUTUP 22-Agu** — produksi suara kini memakai `model_id` seperti tiga jenis lain (satu titik: `tts_engine._get_provider_config`, memakai penerjemah yang sudah ada, fail-safe dipertahankan). Terukur: 11 model suara, **nol** ber-key≠id ⇒ nol perubahan perilaku; yang ditutup adalah kegagalan-yang-menunggu (LULUS Uji tapi gagal produksi). Biaya tetap terhitung — `ai_cost._pricing_map` memetakan kedua bentuk ID. |
| ~~Tombol Edit terbuka penuh~~ | ✅ **DITUTUP 22-Agu** — `provider_key`·`component`·`model_id` **readonly selama model dipakai channel** (dua lapis: layar + server, karena penjaga di panel saja tak menahan jalur skrip). `channels` menyimpan rujukan sebagai TEKS tanpa FK (nol FK ke `ai_models`) ⇒ mengubahnya MEMUTUS rujukan, bukan mengalirkannya. Terbuka kembali bila nol pemakai. **Tidak** dikunci: `is_active` (mematikan wajib tetap bisa) · nama · tier · urutan · harga. Terukur: 15 dari 47 model terkunci, 32 masih bebas. |
| ~~Duplikasi penghitung~~ | ✅ **DITUTUP 22-Agu (F3)** — satu fungsi `channelPemakai(a, table, key, hanyaAktif)` melayani kedua jalur. Beda yang SAH dipertahankan: MEMATIKAN → channel aktif saja · MENGHAPUS → semua channel. Gagal baca pada jalur hapus **menahan** (bukan meloloskan) |
| ~~Fosil data `groq`~~ | ✅ **DIBERSIHKAN 22-Agu (F4)** — 1 setelan suara + 2 karakter suara dihapus (nol model `tts`, nol channel memakainya; penyedia `groq` untuk NASKAH tak disentuh & tetap aktif). Bila Groq TTS kelak dihidupkan, barisnya lahir otomatis lewat B6 |

*Rencana perbaikan + progresnya TIDAK ditulis di sini (dokumen ini bukan daftar kerja) — backlognya di
`SISA_KERJA_GO_LIVE.md`.*

*Dokumen ini mencerminkan kode s/d 2026-08-22 (§9 + koreksi registry/kolom); badan §1–§8 s/d commit `f2ea9a1`+ (2026-07-09 — termasuk purge tuntas Replicate+Together; sebelumnya: alur uji/recover channel + reaper + siklus hidup kartu hasil). Bila menambah adapter baru: daftarkan di registry kode (`src/providers/*`) — cermin `catalog_valid_values` memuatnya otomatis pada restart service berikutnya. Bila arsitektur berubah, UPDATE dokumen ini di commit yang sama.*
