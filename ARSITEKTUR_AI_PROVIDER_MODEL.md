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
| `ai_models` | Model (DETAIL provider). | `model_key`(PK), `provider_key`(FK), `component`(llm/tts/image/video), `model_id`(id resmi vendor), `display_name`, `quality_tier`, `sort_order`, `pricing`(jsonb), `pricing_locked`, `pricing_pending`, `cost_hint`(jsonb; berisi `audit`), `is_active` |
| `tts_profiles` | Protokol TTS per provider. | `provider_key`(PK), `adapter`, `tts_class`(timed/fast_fallback), `delivery_wps`, `speed_param`, `param_schema`, `is_active` |
| `voice_catalog` | Katalog suara (per provider TTS). | `voice_key`(PK), `provider_key`, `locale`, `language`, `gender`, `delivery_wps`, `preview_url`, `default_settings`, `is_active` |
| `content_languages` | Bahasa konten yg didukung. | `locale`(PK), `display_name`, `quality_tier`(official/experimental), `caption_font`, `is_active` |
| `duration_presets` | Preset durasi video. | `seconds`(PK), `use_case`, `is_active`, `is_default` |
| `catalog_valid_values` | **CERMIN nilai-sah dari registry KODE** (adapter/enum). Anti-drift, self-heal tiap startup. | `field`+`value`(PK), `label` |
| `tenant_ai_accounts` | **KOLAM kredensial tenant** (Fernet-encrypted). | `id`(PK), `tenant_id`, `provider_key`, `key_group`, `label`, `key_enc`, `status`(valid/invalid/unchecked), `validated_at` |
| `tenant_youtube_accounts` | Koneksi YouTube tenant (OAuth). | `tenant_id`, `channel/token` |
| `channels` | Channel tenant + penugasan AI. | `id`(PK), `tenant_id`, `llm_library`+`llm_model`+`llm_account_id`, `tts_provider`+`tts_model`+`voice_key`+`tts_account_id`, `visual_mode`(`ai_image:<model_key>`)+`visual_account_id`, `content_language`, `duration_preset` |
| `tenant_configs` | Config tenant-wide + langganan. | `tenant_id`, `plan_type`, `subscription_status`, `usd_idr_rate`(display) |
| `production_runs` | Ledger tiap run produksi (+biaya). | `run_metadata`(jsonb: `ai_usage`, `cost`) |
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
| `src/providers/llm/adapters.py` | `ADAPTERS` (registry: `openai_chat`, `anthropic_messages`); `.complete()` + `cost_meter.add_llm()`. |
| `src/providers/llm/catalog.py` | `get_providers()` — muat `ai_providers` **aktif** dari DB (cache). |
| `src/providers/tts/__init__.py` | `build_tts_provider()`, `_adapter_registry()` (`elevenlabs`/`openai_speech`/`edge`/`gemini_speech`). |
| `src/providers/tts/{elevenlabs,openai_tts,edge_tts,gemini_tts}.py` | Adapter TTS; `.generate()` + `cost_meter.add_tts()`. |
| `src/providers/visual/ai_image.py` | `AIImageProvider`, `_TRANSPORTS` (`openai`/`replicate`/`together`/`gemini`/`cloudflare`), `_generate_image()` + `cost_meter.add_image()`. Cloudflare (2026-07-08): kunci pool `ACCOUNT_ID:API_TOKEN`, prompt murni tanpa negative (NSFW filter CF false-positive), free-tier 10k neuron/hari — model `cf-flux-schnell` LULUS uji nyata. |
| `src/config/format_catalog.py` | `tts_adapter()`, `tts_class()` — baca protokol dari `tts_profiles`. |
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
| Model aktif = pasti jalan | Tombol **Uji** (`model_tester`) + stempel `cost_hint.audit` + badge FE |
| "Valid" = token benar bisa dipakai | `validate_ai_key` (uji nyata, termasuk EL scoped) |
| Yang muncul di Channel = pasti aktif & jalan | filter provider aktif (FE) + `assertEnums` + `get_providers()` (aktif-only) |
| Harga akurat & otomatis | `price_sync` (feed + prefix data-driven, no hardcode) |
| Biaya per video benar | `cost_meter` → `compute_cost_usd` (× `usd_idr_rate`) |
| Adapter/vendor baru tanpa bongkar skrip | `catalog_sync` (cermin registry kode, self-heal) |

---

*Dokumen ini mencerminkan kode s/d commit `390b406`+ (v2-backend, 2026-07-08 — termasuk alur uji/recover channel + reaper + siklus hidup kartu hasil). Bila menambah adapter baru: daftarkan di registry kode (`src/providers/*`) — cermin `catalog_valid_values` memuatnya otomatis pada restart service berikutnya. Bila arsitektur berubah, UPDATE dokumen ini di commit yang sama.*
