# Arsitektur AI Provider & AI Model — MesinViral (end-to-end)

> **STATUS: DOKUMEN REFERENSI — SELESAI (permintaan owner 2026-07-07).** Bukan daftar kerja; tak ada item menggantung di sini. Peta arsitektur untuk dipahami owner+Claude. Update bila arsitektur berubah.

> ## 🎯 DOKUMEN INI ADALAH **SSOT** UNTUK DUA HAL (ditetapkan owner 23-Agu-2026)
> **(1) sinkronisasi harga model AI** — §4 · **(2) estimasi biaya produksi** — §7, §7a–§7e.
> Tarif per-satuan & rumus biaya **HARAM hidup di dokumen lain** (dijaga `tests/test_gerbang_rantai_biaya.py`
> G7). Dokumen lain menunjuk ke sini; `DESAIN_PRODUK_SAAS §10` sudah dicabut angkanya karena
> bertentangan 3× dengan katalog hidup. **Angka HIDUP tidak di dokumen** — ia di `ai_models.pricing`
> (katalog) dan `production_runs.run_metadata.cost` (per produksi). Dokumen ini menjelaskan **aturannya**.
>
> **Beda topik yang sering tertukar:** *harga langganan* (paket tenant) = `finalisasi_tier_plan.md` +
> `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`. *Harga model AI & biaya produksi* = **di sini**.

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
| `src/utils/cost_meter.py` | Meteran konsumsi thread-local: `reset()`, `add_llm(model,tin,tout)`, `add_image(model,n)`, `add_tts(model,chars)`, **`add_tts_tokens(model,tin,tout)`** (22-Agu), `summary()`. ⚠️ Keranjang baru WAJIB didaftarkan di `reset()` — `_bucket()` mengembalikan `None` untuk keranjang tak dikenal, jadi `add_*` jadi **no-op senyap**. |
| `src/billing/ai_cost.py` | `compute_cost_usd(ai_usage)` — konsumsi × harga katalog (`ai_models.pricing`) → `{usd, breakdown:{llm,image,tts,video}, unpriced, priced_at}`. Model gambar ber-tagih token (gpt-image) dihitung di bucket llm. **Suara ber-tagih token** (Gemini TTS) dihitung di bucket `tts` dari `tts_tokens`. |
| `src/billing/price_sync.py` → `report_unpriced_models` | **(22-Agu)** Laporan harian **berbasis BUKTI PRODUKSI**: model yang gagal dihitung biayanya pada run nyata (`cost.unpriced`, jendela `AI_UNPRICED_WINDOW_DAYS`=3) → alarm admin 1×/hari. Dipanggil `buffer_janitor.run_once`. **Sengaja tidak** memakai daftar aturan "jenis X → satuan Y": vendor baru bisa menagih dengan satuan yang belum ada hari ini, daftar semacam itu PASTI tertinggal. |

**Rumus biaya (jujur = konsumsi terukur × harga katalog):**
```
biaya_llm   = Σ (tokens_in/1e6 × in_per_1m + tokens_out/1e6 × out_per_1m)
biaya_image = Σ (jumlah_gambar × per_image)          [kecuali gpt-image → via token llm]
biaya_tts   = Σ (chars/1e6 × per_1m_chars)
              ATAU, bila model TAK punya per_1m_chars & vendor mengirim hitungan token (Gemini TTS):
              Σ (tts_tokens.in/1e6 × in_per_1m + tts_tokens.out/1e6 × out_per_1m)
              Nol dari keduanya → masuk `unpriced` (JUJUR). Urutan per-huruf DULU ⇒ tak mungkin ganda.
biaya_video_USD = biaya_llm + biaya_image + biaya_tts        → disimpan di production_runs.run_metadata.cost
biaya_video_IDR = biaya_video_USD × app_config.usd_idr_rate  (tampilan)
```

---

## 7a. Definisi metrik biaya — apa yang MASUK, apa yang TIDAK

Tanpa bagian ini dua orang membaca angka yang sama dengan arti berbeda. *(Kerangka FinOps
"Unit Economics" mengharuskan definisi + asumsi + cakupan biaya ditulis; lihat §7e.)*

| Metrik | Definisi | Di mana |
|---|---|---|
| **Biaya per produksi** | Σ (jumlah terukur × tarif tercantum) untuk satu run pipeline | `production_runs.run_metadata.cost.usd` |
| **Biaya per tenant** | Σ biaya per produksi dalam jendela waktu | kartu Biaya AI dashboard (30 hari) |

**MASUK hitungan:** naskah (semua panggilan LLM termasuk pemilih topik/hook/penilai) · suara · gambar
(termasuk thumbnail bila dibuat mesin gambar) · video · **run yang GAGAL** (uang tetap terpakai) ·
run uji tenant & "jalankan ulang" (memakai kunci tenant).

**TIDAK masuk:** langganan MesinViral · infrastruktur kami (VPS/S3) · run uji **admin** (kunci admin,
bukan kunci tenant) · **percobaan yang gagal di tengah sebelum vendor membalas** — kita hanya bisa
menghitung yang vendor sebutkan atau yang bisa kita ukur; bila vendor tetap menagihnya, angka kita
lebih rendah dari kenyataan. Ini batas yang **tak bisa dihapus rancangan apa pun**.

**Asumsi yang menempel pada angka** (wajib disebut, bukan disembunyikan):
1. Tarif = **tarif tercantum** (*list price*) penyedia, **bukan** tagihan nyata tenant (*billed cost*)
   — kita tak pernah melihat tagihan tenant (BYOK). Karena itu layar menyebutnya **"perkiraan"**.
2. Tarif per-detik (bila dipakai) adalah **perkiraan yang vendor terbitkan sendiri**; klip sangat
   pendek bisa lebih mahal dari itu.
3. Kurs USD→IDR = tampilan saja (`app_config.usd_idr_rate`); nilai tersimpan selalu USD.

---

## 7b. DAFTAR SATUAN HARGA — tabel kanonik  *(TERPASANG 23-Agu; sumbernya `src/billing/ai_cost.py` → `SATUAN_HARGA`)*

**Sebab bagian ini ada.** 23-Agu ditemukan 10 cacat di rantai ini, dan akarnya satu: pengetahuan
"satuan apa berlaku untuk jenis apa, dihitung sekali di mana" tersebar di **4 tempat** yang tak saling
tahu. Kosakata FinOps FOCUS menamai celah tempat seluruh cacat itu hidup:

| Istilah | Artinya di sini | Contoh cacat 23-Agu |
|---|---|---|
| **satuan terukur** (*Consumed Unit*) | yang mesin kita **ukur** | 1113 **huruf** |
| **satuan tagih** (*Pricing Unit*) | yang vendor **tagih** | **token audio** Gemini |
| **tarif tercantum** (*List Unit Price*) | tarif resmi per satuan tagih | $10/1jt token audio |
| **biaya tercantum** (*List Cost*) ≠ **biaya tertagih** (*Billed Cost*) | yang kita tampilkan vs tagihan tenant | perkiraan vs tak terlihat |

Harga tersimpan dalam **satuan tagih**; pemakaian tercatat dalam **satuan terukur**. Bila konversinya
tak ada, satuan itu **tak bisa dihitung** — dan wajib dinyatakan begitu, bukan dikira-kira.

| Jenis | Prioritas | Kunci harga | Satuan tagih | Satuan terukur (keranjang meter) | Kolom umpan yang BOLEH | Kolom yang **HARAM** |
|---|---|---|---|---|---|---|
| naskah | 1 | `per_request_usd` | per panggilan | `llm.calls` | *(manual saja)* | — |
| naskah | 2 | `in_per_1m`/`out_per_1m` | token | `llm.tokens_in/out` | `input_cost_per_token`, `output_cost_per_token` | — |
| suara | 1 | `per_1m_chars` | huruf | `tts` (huruf) | `input_cost_per_character` | — |
| suara | 2 | `in_per_1m`/`out_per_1m` | **token audio** | `tts_tokens` (token dari vendor) | `output_cost_per_audio_token`, `input_cost_per_token` | **`output_cost_per_token`** |
| suara | 3 | `per_second_usd` | detik audio | `tts_seconds` *(dicatat mesin suara)* | `output_cost_per_second` | — |
| gambar | 1 | `per_image` | per gambar | `image` (jumlah) | `output_cost_per_image` | — |
| gambar | 2 | `in_per_1m`/`out_per_1m` | token gambar | `llm.tokens_in/out` | `output_cost_per_image_token`, `input_cost_per_token` | **`output_cost_per_token`** |

**Harga ESENSIAL per skema.** Satuan bertanda wajib (`wajib=True` di daftar) harus ada, kalau tidak
skemanya **tak berlaku** — hari ini: harga token **audio** (suara) dan token **gambar**. Sebabnya
terukur: harga *masukan* hanya ±1% tagihan; menagih hanya itu menghasilkan angka **kecil yang masuk
akal tapi salah**, dan barisnya jadi **TAMPAK berharga** di panel. Lebih baik jujur "belum terhitung".
| video | 1 | `per_second_usd` | detik | `video.seconds` | `output_cost_per_second` | — |
| video | 2 | `per_video_base_usd` + `base_seconds` + `per_extra_second_usd` | klip + detik lebih | `video.clips/seconds` | *(manual saja)* | — |

**Dua aturan yang membuat cacat 23-Agu mustahil kembali:**
1. **PRIORITAS ⇒ satu model satu tagihan.** Satuan bernomor kecil menang; sisanya dilewati. Model
   ber-`per_image` tak bisa lagi ditagih ulang lewat token *(cacat +7,6% pada gambar Gemini)*.
2. **`output_cost_per_token` HARAM untuk suara & gambar.** Di umpan publik kolom itu bermakna **dua**
   hal tanpa penanda: pada `gemini-2.5-pro-preview-tts` ia harga audio yang benar ($10), pada
   `gemini-2.5-flash-preview-tts` ia harga **teks** ($2,5) — dan itulah asal cacat "4× terlalu murah".
   Menerimanya = menebak. Disiplin yang sama dengan tangga bukti karantina: **pasti → bertindak,
   ambigu → lapor.**

---

## 7c. Asal setiap angka (provenance) — wajib, bukan anjuran

`pricing.source` + `pricing.synced_at` menyebut dari mana angka itu datang. Untuk harga yang
**diketik admin**, `pricing.note` **wajib** menyebut sumber + tanggal (contoh yang sudah ada:
`"source": "fal_api 2026-07-16"`). Alasannya terukur: **16 dari 42 model aktif tidak ada di umpan
publik mana pun** (seluruh 5 model video, ElevenLabs, fal, Cloudflare, Edge) ⇒ harganya memang harus
diketik, dan tanpa catatan asal tak ada yang bisa memeriksanya ulang.

---

## 7d. Pembandingan dengan sumber LUAR — berjadwal, tercatat

Uji tak bisa menelepon vendor; **nilai harga yang salah tapi masuk akal tak terdeteksi mesin apa pun.**
Penutupnya: pembandingan dengan sumber luar, dicatat bertanggal di bawah ini.

| Tanggal | Yang dibanding | Hasil |
|---|---|---|
| 2026-08-23 | tarif resmi Google vs katalog (`gemini-2.5-flash-preview-tts`) | **katalog SALAH**: $2,5 vs resmi **$10** audio/1jt token → satuan ambigu, ditolak §7b |
| 2026-08-23 | tarif resmi OpenAI vs katalog (`gpt-4o-mini-tts`) | katalog $10 vs resmi **$12** audio/1jt token; umpan **punya** kolom benarnya, pemeta kita membuangnya |
| 2026-08-23 | log vendor vs meter (huruf suara Gemini) | vendor terima **1113**, meter catat **2226** → dicatat dua lapis |
| 2026-08-23 | hitung-ulang run nyata #503 & #504 | identik dengan yang tersimpan (nol regresi penghitung) |
| 2026-08-23 | cakupan umpan atas 42 model aktif | 26 otomatis · **16 wajib manual** |
| 2026-08-23 **(F7)** | tarif resmi Google, dibaca langsung dari halamannya (`gemini-2.5-flash-preview-tts`) | resmi **$0,50 masuk / $10,00 audio keluar** ⇒ katalog ($0,3/$2,5) DIBETULKAN + DIKUNCI (migr `0214`) |
| 2026-08-23 **(F7)** | tarif API resmi ElevenLabs vs 4 baris katalog | `eleven_v3` **$180 → $100** (umpan memberi tarif KELEBIHAN KUOTA; 1,8× lolos penjaga lonjakan yang butuh 3×) · `multilingual_v2` $100 · `flash/turbo_v2_5` $50 = **sudah benar**, yang hilang JEJAKNYA |
| 2026-08-23 **(F7)** | tarif resmi Cloudflare Workers AI vs baris `cf-flux-schnell` | **$0 masih BENAR**: 10.000 neuron/hari gratis; flux-1-schnell = 4 petak × 4,8 + 8 langkah × 9,6 = **96 neuron/gambar** ⇒ 104 gambar/hari per akun tenant gratis, puncak NYATA terukur **22/hari** = kelonggaran 4,7× |
| 2026-08-23 | **SEMBILAN tarif yang sungguh dipakai 30 hari terakhir**, dibanding satu per satu ke halaman resmi vendornya (OpenAI · Google · Groq) | **8 TEPAT · 1 SALAH**: `gpt-image-1-mini` token MASUK $2,00 vs resmi **$2,50** (keluar $8,00 sudah benar) → dibetulkan + DIKUNCI (migr `0215`); terukur 82 dari 246 produksi, **+0,47%…+1,46%**. Delapan lainnya dibiarkan otomatis agar tetap mengikuti perubahan vendor. Groq 3/3 tepat · Gemini 3/3 tepat · OpenAI 2/3 tepat |
| 2026-08-23 | usulan harga tertahan `gemini-2.5-flash-image` ($2,5 → $30) | **TERJELASKAN, bukan lonjakan liar**: halaman resmi Google menyebut token gambar **$30 per 1jt** dan **$0,039 per gambar** sebagai dua penyebutan hal yang sama. Baris kita berformula **per gambar** ($0,039 — sudah benar) ⇒ usulan itu **boleh diabaikan**; menerapkannya pun tak berdampak biaya |
| 2026-08-23 **(F7)** | hitung-ulang 246 run, tarif lama vs baru | **244 identik · 2 berbeda · nol tak terjelaskan**; komponen suara **×3,96**, total per video **+4,1…+4,5%** |

**Jadwal:** pemeriksaan harian mesin (`report_unpriced_models`, terpasang 22-Agu) melaporkan model yang
**gagal dihitung** dari bukti produksi. Pembandingan **tarif** ke sumber resmi = manual, dicatat di
tabel ini setiap kali dilakukan. *(Rencana S3: mesin ikut membandingkan catatan-vs-kenyataan tiap hari
— huruf vs naskah terkirim, gambar vs adegan, detik vs durasi.)*

**Keadaan terpasang (23-Agu, gerbang G1–G7 HIJAU + tiap gerbang disabotase):**
- ✅ Daftar satuan §7b = **satu-satunya sumber**; penghitung biaya satu putaran atas daftar, nol
  cabang per-kasus · prioritas **"satu model satu tagihan"** · sinkron **menolak kolom ambigu** dan
  tak menulis skema yang harga esensialnya kosong · prefix umpan **hanya dari DB** (daftar 7 prefix
  yang ditanam dibuang; 0 model bergantung padanya) · huruf suara dicatat **sekali** (di mesin suara)
  · **detik audio** dicatat → model suara ber-tagih per-detik terhitung otomatis · satuan+label
  **dicerminkan ke DB** (`catalog_valid_values`, `pricing_unit:<jenis>`, migr **0209** memberi izin
  baca) dan **ketiga layar membacanya** — nol nama satuan diketik di kode layar · kurs hanya dari
  `app_config` (angka cadangan di kode dibuang; kurs belum ada → tampil USD, bukan Rp palsu).
- **Bukti ambang:** 244 run riwayat dihitung ulang → **227 identik**, **17 berbeda dengan SATU sebab
  yang sama** (hitung-ganda gambar Gemini hilang, −7,2%…−7,7%), **nol selisih tak terjelaskan**.
  Sinkron kering atas 47 baris → **3 baris berubah**, 44 tak bergerak:
  `gemini-2.5-flash-image` (token teks $2,5 → token gambar $30, per-gambar tetap) ·
  `gemini-2.5-flash-preview-tts` (satuan ambigu **dibuang** → belum terhitung, jujur) ·
  `gpt-4o-mini-tts` (token audio $10 → **$12** = tarif resmi, + per-detik → **terhitung otomatis**).
- 🔵 **Belum:** dasar tagih agregator **fal** (4 jenis lewat satu penyedia; 0 channel aktif) belum
  diverifikasi ke dokumen vendor — harga naskah fal kini datang dari sumber cadangan, yaitu tarif
  **vendor asal**, bukan tarif fal. · pemeriksaan harian catatan-vs-kenyataan (huruf vs naskah,
  gambar vs adegan, detik vs durasi).

---

## 7f-00. 🔴 PEKERJAAN MENGGANTUNG — SELESAIKAN INI DULU (25-Agu, sesudah restart laptop)

> **Ada perubahan SELESAI tapi BELUM TERSIMPAN di direktori kerja.** Ia TIDAK mengganggu produksi
> (server jalan di `4922451`), jadi tak ada yang mendesak — tapi jangan dibiarkan menggantung, dan
> **jangan dikerjakan ulang dari nol**: kodenya sudah ada, ujinya sudah ada, migrasinya sudah masuk DB.

**ISI PEKERJAANNYA — A·B·C, disetujui owner 24-Agu:**
- **A** biaya HARAM tertukar antar penyedia untuk model bernama sama (penyedia ikut jadi bagian kunci
  pencatatan; bentuk kunci di `ai_cost.kunci_biaya`) — **prasyarat sebelum APIMaster/OpenRouter
  ditambahkan**, sebab router menyebut model dengan nama persis sama dan selisih harganya 150×.
- **B** alarm harga-basi kini ikut menjaga baris TERKUNCI (30 hari, angka mati atas ketokan owner;
  tanpa tanggal = belum pernah dipastikan). Migr `0216` **SUDAH diterapkan** ke DB.
- **C** sinkron berhenti mempercayai "200 OK" — harga tidak ditulis untuk model yang belum LULUS
  tombol Uji (API fal menjawab 200 untuk endpoint yang TIDAK ADA); satuan vendor tak dikenal
  dialarmkan, bukan cuma masuk log.
Rinciannya di CATATAN PELAKSANAAN A·B·C di §7f. Berkas yang tersentuh terlihat dari `git status`.

**SUDAH DIBUKTIKAN:** 9 uji dibuktikan MERAH dulu · **10 sabotase semuanya tertangkap** · ambang
riwayat lolos (**nol produksi yang BARU jadi belum-terhitung**) · alarm baru diuji pada 47 baris nyata
= **nol alarm palsu** · potongan uji yang sudah hijau: **796 · 309 · 131 · 8**.

**SISA — kecil, jangan dibesarkan:**
1. Jalankan **HANYA** potongan yang belum diverifikasi ulang: `ls tests/*.py | sed -n '63,93p'`
   (±3 menit). Dua uji di dalamnya sempat merah dan **sudah dibetulkan** (`test_naskah_fal_jalur_hidup.py`).
2. Bila hijau → **commit sekali**. Gerbang commit menjalankan uji penuh; di mesin ini itu **±10 menit**
   saat cache dingin, dan tenggat hook-nya 300 detik ⇒ **bisa habis waktu**. Kalau hook gagal karena
   tenggat, LAPOR ke owner dan minta keputusannya — **jangan mengulang-ulang uji penuh.**

**⛔ ATURAN KERAS DARI OWNER (25-Agu, sesudah laptopnya drop DUA KALI karena saya):**
> **Jangan menjalankan uji penuh berulang-ulang.** Jalankan hanya uji yang bisa menangkap perubahan
> yang dibuat. Uji penuh = tugas gerbang commit, SEKALI. **Haram** menjalankan uji di latar
> (`run_in_background`) atau menumpuk beberapa putaran — laptop owner yang menanggungnya, dan itu
> sudah membuatnya mati dua kali. Uji kena tenggat → **BERHENTI dan lapor**, jangan diulang.

---

## 7f-0. ⏩ MULAI DARI SINI (sesi baru / pasca-compacting) — keadaan per 23-Agu-2026

> **Baca 7f-0 lalu §7f. Jangan menyentuh rantai harga/biaya sebelum keduanya dibaca.**

**KEADAAN DEPLOY — SELURUH RANTAI SUDAH TERPASANG (23-Agu 20:15/20:18 WIB, izin owner).**
Produksi (VPS, mesin **dan** web) di **`516fad1`** — F1 s/d F8 + F4b, 15 commit. Diverifikasi
langsung ke server: `mv-worker`=active · `mv-webhook`=active · health 200 · `mv-web`=active ·
situs 200 · worker restart BERSIH (nol galat di log). Migrasi `0209`-`0215` **sudah diterapkan** ke
DB - jangan diulang. Cermin katalog harga sudah ditulis worker saat start (termasuk satuan baru F4b
dan daftar formula tanpa-tarif).
**Yang menyelesaikan diri sendiri pada sinkron harian berikutnya (kurang lebih 18 jam):** 4 baris fal
(flux x2, seedance x2) berpindah ke formula megapiksel / token-video beserta tarif resmi dari API
fal. Angkanya identik dengan yang tersimpan sekarang, jadi **nol geseran**.
**Risiko mesin sinkron LAMA membatalkan perbaikan F4 sudah HILANG** - pagar agregator kini terpasang
di server.

**MIGRASI TERBARU (24-Agu):** `0216` = tanggal pemeriksaan pada 9 harga terkunci (butir B).
Sebelumnya `0215` = tarif `gpt-image-1-mini` dibetulkan. Keduanya SUDAH diterapkan.

**DATABASE PRODUKSI SUDAH BERUBAH** (migrasi + sinkron nyata sudah dijalankan — JANGAN diulang):
`0209` izin baca cermin · `0210` kolom `pricing_model` + 47 baris terisi · `0211` kenop URL sumber
harga · `0212` `ai_providers.price_api_url` + **veo dikunci** · `0213` `price_endpoint_id` untuk 3
baris naskah fal · `0214` **F7**: 2 tarif dibetulkan + 7 baris diberi jejak & kunci.
Sinkron nyata: 35 baris tersinkron · 1 ditahan · 5 tanpa-sumber.

**⏳ MENUNGGU TINDAKAN OWNER (bukan pekerjaan Claude):**
1. **Izin deploy** tujuh commit di atas.
2. **Panel → Catalog → AI Models:** usulan harga `gemini-2.5-flash-image` (token $2,5 → **$30**, 12×)
   **DITAHAN penjaga lonjakan**, menunggu tombol *Terapkan/Abaikan*. Nol dampak biaya (formulanya
   per-gambar), tapi biarkan tercatat sampai diputuskan.
3. **Ganti kunci APIMaster** — pernah tertulis di percakapan 23-Agu. (Berkas kunci ada di direktori
   kerja sesi lama; ikut hilang, tak perlu dicari.)

**✅ F7 SELESAI 23-Agu (migr `0214` SUDAH diterapkan ke DB — jangan diulang).** Tak ada lagi tarif
keliru yang diketahui: suara Gemini **$0,50/$10,00** dan `eleven_v3` **$100**, keduanya **DIKUNCI** +
bercatatan sumber & tanggal; 5 baris lain diberi jejak tanpa menyentuh angkanya. Penjaga `G13`
menegakkan §7c. Rinciannya di CATATAN PELAKSANAAN F7 di §7f.

**✅ F5 SELESAI 23-Agu** untuk *"biaya dilaporkan vendor"* — begitu penyedia router ditambahkan,
biayanya **pasti, bukan taksiran**, dan panel tak lagi menuduhnya "harga kosong".
⛔ *"selisih penghitung akun"* **sengaja TIDAK dipasang** (produksi serentak ⇒ mustahil diatribusikan
per-produksi) — alasan lengkap di §7f, **menunggu ketokan owner**; tempatnya F8.

**✅ F6 SELESAI 23-Agu** — lencana "✓ Teruji" berhenti bisa berbohong untuk model naskah. Dua batas
jujurnya (stempel lama dari uji lemah · uji suara masih pendek) ada di §7f.

**🟡 F8 SEBAGIAN SELESAI 23-Agu** — alarm harian untuk biaya yang salah **tanpa mesin menyadarinya**
sudah terpasang (nol alarm palsu pada data nyata), dan SSOT ini **DITUTUP**. Pembandingan ke pemakaian
nyata akun vendor **tidak bisa** hari ini (9 penyedia aktif tak menerbitkannya · tagihan akun tenant =
keputusan owner · satu kunci bisa dipakai di luar MesinViral) — jalannya lewat penyedia **router**
yang sudah disiapkan F5.

**✅ F4b SELESAI 23-Agu** — gambar per megapiksel (dibulatkan ke atas) & video per token, faktanya
**DIUKUR dari berkas hasil** (fps pun diukur — kita tak pernah menyebutkannya ke vendor). Nol geseran
angka hari ini; nol migrasi. **URUTAN WAJIB: deploy dulu**, baru sinkron harian memutakhirkan keempat
baris fal itu sendiri — jangan dibalik.

**SISA — HANYA menunggu keputusan owner, bukan pekerjaan yang terlupa:**
- **`selisih_akun`** — saran saya: **JANGAN dipasang** per-produksi (produksi serentak ⇒ dua produksi
  tenant yang sama saling mencuri biaya). Bila diinginkan, tempatnya rekonsiliasi tingkat tenant.
- **Menampilkan rincian biaya per komponen di layar tenant** — angkanya sudah dihitung, disimpan di
  setiap produksi, dan kini **beralamat benar** (perbaikan 23-Agu), tapi NOL layar membacanya —
  padahal kelas tampilannya sudah ada di kode layar tanpa dipakai. Menyambungkannya = menambah elemen
  di layar tenant ⇒ **ketokan owner**. Yang bisa dikerjakan tanpa ketokan sudah dikerjakan.
- **Uji suara sepanjang produksi** — nol bukti kegagalan, dan berbiaya nyata tiap tekan.

**Alat bukti yang WAJIB dipakai tiap langkah** (skrip ada di direktori kerja sesi; bila hilang, tulis
ulang — logikanya sederhana): hitung-ulang seluruh run riwayat sebelum-vs-sesudah (**ambang: satu
selisih tak terjelaskan → BERHENTI & lapor**) · sinkron dijalankan **KERING** dulu · alarm
`tests/test_gerbang_rantai_biaya.py` (**G1–G14, 51 uji**) dibuktikan merah lalu hijau lalu
**disabotase** — begitu juga `test_uji_model_sekelas_produksi.py` (F6) dan
`test_rekonsiliasi_biaya_harian.py` (F8). Uji penuh saat ini: **1428 hijau**.
**Dua butir yang menunggu KEPUTUSAN owner** (bukan pekerjaan yang terlupa): menampilkan rincian biaya
per komponen di layar tenant · uji suara sepanjang produksi. Plus satu SARAN: `selisih_akun` jangan
dipasang. Rinciannya di §7f.

---

## 7f. RENCANA & PROGRES F1–F8 — *tertulis di sini supaya TIDAK HILANG saat compacting / sesi baru*

> **Sesi baru: baca bagian ini SEBELUM menyentuh apa pun di rantai harga/biaya.** Ditetapkan owner
> 23-Agu-2026 sesudah riset sehari penuh (10 cacat ditemukan, semuanya karya Claude sendiri).
> Penunjuk masuk: `MEMORY.md` → dokumen ini. Backlog satu baris: `SISA_KERJA_GO_LIVE.md`.

**AKAR yang diperbaiki:** kita MENAKSIR biaya (pemakaian × tarif katalog) sambil memperlakukan sumber
harga internet sebagai kebenaran. Empat kebenaran yang riset 23-Agu tetapkan:
1. **Sumber harga umum BUKAN otoritas** — terbukti 3×: suara Gemini 4× terlalu murah (diberi tarif
   teks) · `eleven_v3` 1,8× terlalu mahal (diberi tarif kelebihan-kuota) · tak mampu menyatakan harga
   yang tergantung setelan kita (veo audio, megapiksel dibulatkan, token video).
2. **Satuan yang vendor TAGIH ≠ satuan yang kita UKUR** — di celah itu seluruh keluarga bug hidup.
3. **Ada jalan tanpa taksiran:** vendor melaporkan biayanya sendiri (OpenRouter per panggilan;
   APIMaster lewat selisih penghitung akun `/v1/dashboard/billing/usage`, satuannya **SEN**).
4. **Mutu/biaya kanal hanya terbukti dgn perintah PRODUKSI** — 4 dari 6 model APIMaster lolos
   panggilan pendek lalu GAGAL pada perintah naskah asli (mentok batas keluaran 2.000 token).

| Langkah | Isi | Status |
|---|---|---|
| **F1** | Katalog formula (**15**) + formula di 47 baris model + panel menjelaskannya | ✅ **SELESAI 23-Agu** (migr `0210`; 47/47 terisi; penghitung BELUM membacanya = nol perubahan biaya) |
| **F2** | Penghitung biaya memakai formula (ganti logika urutan-prioritas) | ✅ **SELESAI 23-Agu** — 246 run dihitung ulang: **246 IDENTIK, 0 berbeda** |
| **F3** | Sumber tarif diatur dari panel + 3 pagar (ambigu ditolak · agregator · terkunci) | ✅ **SELESAI 23-Agu** (migr `0211`; sinkron kering: **2 baris bergerak**, 13 tanpa-sumber dipertahankan) |
| **F4** | Sumber API resmi penyedia (migr `0212`/`0213`) → **7 dari 12** model fal otomatis; veo dikunci manual | ✅ **SELESAI 23-Agu** |
| **F4b** | 4 baris fal terakhir: gambar per **megapiksel dibulatkan ke atas** & video per **token**, faktanya DIUKUR dari berkas hasil | ✅ **SELESAI 23-Agu** (13 uji · **11 sabotase**, 3 menangkap celah penjaga saya sendiri · **nol geseran angka**; nol migrasi — sinkron menulis sendiri sesudah deploy) |
| **F5** | Formula "biaya dilaporkan vendor" disambungkan | ✅ **SELESAI 23-Agu** (biaya vendor dipakai apa adanya; `G14` 8 uji + **11 sabotase**) · ⛔ **"selisih penghitung akun" TIDAK dipasang** — alasan terukur di bawah, butuh ketok owner |
| **F6** | **Tombol Uji memakai perintah selengkap produksi** (temuan terbesar 23-Agu) | ✅ **SELESAI 23-Agu** (uji naskah = kontrak produksi: JSON + jatah penuh; 7 uji, **5 sabotase**, 1 di antaranya menangkap celah penjaga saya sendiri) |
| **F7** | Pulihkan baris yang tarifnya SALAH + beri JEJAK & KUNCI (3 naskah fal sudah lewat F4) | ✅ **SELESAI 23-Agu** (migr `0214`; 2 angka dibetulkan · 5 diberi jejak · 246 run → **244 identik, 2 terjelaskan**) |
| **F8** | Rekonsiliasi berjadwal + alarm + SSOT ditutup | 🟡 **SEBAGIAN SELESAI 23-Agu**: alarm harian untuk biaya yang salah **tanpa mesin menyadarinya** (6 uji, **6 sabotase**) + SSOT ditutup. ⛔ Pembandingan ke **pemakaian nyata akun vendor** TIDAK BISA hari ini — alasan terukur di bawah |

**15 formula** (kelompok → nama) — *koreksi: 15, bukan 14; `video_klip` (per klip + detik tambahan) DIPERTAHANKAN karena nyata dipakai Kling dan angkanya identik dengan per-detik untuk klip ≥ jatah dasar; memaksa migrasi = mengubah data tanpa perlu*: *tanpa taksiran* — biaya dilaporkan per panggilan · selisih
penghitung akun · **naskah** — token masuk+keluar · per panggilan · **suara** — per huruf · token
audio · per detik audio · **gambar** — per gambar · token gambar · per megapiksel dibulatkan ke atas ·
**video** — per detik (beda bila audio nyala) · token video `(t×l×fps×durasi)÷1024` · **lain** —
kuota gratis harian · gratis.

**CATATAN PELAKSANAAN F1 (23-Agu).** Kolom `ai_models.pricing_model` (migr `0210`) + 47 baris terisi
dalam migrasi yang SAMA, dengan formula yang **mereproduksi angka hari ini** (dipilih dari kunci harga
yang sudah ada, mengikuti urutan prioritas penghitung) ⇒ **nol perubahan biaya, nol channel tenant
tersentuh**. Sebaran: naskah_token 25 · suara_huruf 9 · gambar_satuan 4 · video_detik 4 ·
gambar_token 2 · suara_token 2 · video_klip 1. Migrasi memakai **ambang**: bila hasilnya tak sama
dengan hitungan kering, transaksi dibatalkan. Formula dicerminkan ke `catalog_valid_values`
(`pricing_model:<jenis>`, label = "nama — penjelasan") → panel menyaring pilihan **per jenis model**,
menampilkan penjelasan cara hitung di bawah field, dan menandai baris **⚠️ formula belum dipilih**;
API memvalidasi nilainya terhadap cermin. Nol nama/penjelasan formula diketik di kode layar.
**Pemindahan formula ke yang lebih tepat** (gambar fal → per megapiksel · seedance → token video ·
Cloudflare → kuota gratis) **sengaja DITUNDA ke F4/F7**, bersama tarif aslinya dari sumber resmi —
memindahkannya sekarang berarti mengubah angka tanpa sumber tarif yang benar. Penjaga: `G9` di
`tests/test_gerbang_rantai_biaya.py` (7 uji, 6 sabotase tertangkap).

**CATATAN PELAKSANAAN F2 (23-Agu).** Penghitung kini memakai formula yang **dinyatakan baris model**
(`_formula_map`, terpisah dari `_pricing_map` supaya kontrak uji lama utuh), bukan menebak dari
urutan prioritas. Perbedaan dua kelas kegagalan ditegakkan: **celah DATA** (baris tanpa formula) →
dilaporkan **jujur** sebagai tak-terhitung; **gangguan KAMI** (peta formula tak terbaca) → jatuh ke
perilaku pra-F2 supaya biaya tak mendadak nol, **tapi dicatat di log** (haram senyap). Formula
`gratis` → biaya 0 dan **bukan** "tak terhitung" (nol alarm palsu). Formula yang penghitung belum
dukung (`biaya_dilaporkan`, `selisih_akun`, `gambar_megapiksel`, `video_token`, `kuota_gratis`)
**HARAM dihitung dengan cara lain** — dilaporkan tak-terhitung sampai langkahnya tiba (F4/F5/F7).
**Ambang terpenuhi:** 246 run riwayat dihitung ulang sebelum-vs-sesudah → **246 identik, 0 berbeda**;
18 model yang dipakai 60 hari terakhir **semuanya** ber-formula ⇒ nol alarm palsu bagi 9 channel
aktif. Penjaga `G10` (6 uji) — termasuk **uji pembeda yang MERAH bila penghitung dikembalikan ke
perilaku pra-F2**; 5 sabotase, semuanya tertangkap.

**CATATAN PELAKSANAAN F3 (23-Agu).** URL sumber harga jadi **kenop admin** (`app_config.ai_price_feed_url`
+ `ai_price_fallback_url`, migr `0211`), dibaca **saat sinkron** (bukan saat impor) ⇒ berlaku tanpa
deploy; kosong → jatuh ke env lalu bawaan (sinkron tak pernah mati total). Tampil di layar
**Konfigurasi Aplikasi** grup "Sumber Harga Model AI" dengan penjelasan dwibahasa.
**PAGAR AGREGATOR:** jalur harga kini membaca penanda `agregator` yang **SUDAH ADA** di
`galat_registry.PENYEDIA` (nol penanda baru) — baris agregator hanya boleh berharga dari **ruang nama
agregatornya sendiri**; **kunci-persis pun ditolak** (sebab id model agregator sering berupa nama
model vendor, mis. `anthropic/claude-haiku-4.5`, dan kunci itu ADA di umpan dengan tarif ANTHROPIC),
dan **sumber cadangan (router, by-suffix) haram** dipakai baris agregator.
**Sinkron kering:** 2 baris bergerak (`gemini-2.5-flash-image` token teks $2,5 → token gambar $30 ·
`gpt-4o-mini-tts` $10 → **$12** + per-detik), 27 tak berubah, 5 terkunci dilewati, **13 dilaporkan
tanpa-sumber** (12 fal + suara Gemini) — harga lamanya **dipertahankan**, bukan dikosongkan.
**Uji lama `test_harga_otomatis_model_fal.py` DITULIS ULANG**: ia dulu MEMAKSA baris fal mengambil
tarif vendor asal dan menghapus `per_request_usd` — mengunci perilaku yang salah. Niat aslinya
("harga jangan membusuk diam-diam") dijaga lewat pelaporan tanpa-sumber.
**⚠️ KEADAAN SEMENTARA YANG JUJUR:** 3 baris naskah fal **masih** memuat tarif per-token vendor asal,
dan suara Gemini **masih** $2,5 (resminya $10) — sinkron kini menolak menimpanya, tapi nilai lamanya
belum dibetulkan. **F7 yang membetulkannya** + mengunci. Sampai itu, biaya suara 4 channel Gemini
**masih dilaporkan ±4× lebih murah** dari kenyataan. Penjaga `G11` (5 uji) + 5 sabotase tertangkap.

**CATATAN PELAKSANAAN F4 (23-Agu).** Penyedia kini boleh punya **API harga resminya sendiri** sebagai
DATA (`ai_providers.price_api_url`, migr `0212`; tampil + berarahan di panel Providers). Ia dicoba
**lebih dulu** daripada umpan umum dan **tak boleh ditimpa** olehnya — sebab hanya agregator yang tahu
tarifnya sendiri. Satuan tagih yang vendor sebutkan dipetakan ke formula kita lewat **data**
(`SATUAN_VENDOR`): `requests`→per-panggilan · `1000 characters`→per-huruf · `seconds`→per-detik.
Tarif **dan FORMULA ditulis bersama** — tanpa itu bentuk harga berubah sementara formula lama tetap,
dan biayanya jadi "tak terhitung" (jebakan Kling: basis-per-klip → per-detik). **Alamat harga boleh
beda dari penanda model** (`default_params.price_endpoint_id`, migr `0213`): agregator satu-pintu
memakai nama model sebagai PARAMETER, bukan alamat — tanpa ini 3 baris naskah fal selalu HTTP 404.
**Jeda antar panggilan** `AI_PRICE_VENDOR_DELAY_SEC` (bawaan 8 dtk): fal menolak panggilan berdempet
(429 sesudah ±7). Kunci pemanggil = kunci **platform** dari vault (bukan tenant), **hanya** untuk
endpoint harga — nol model dijalankan, nol kredit (seluruh riset harga fal 23-Agu = $0).

**HASIL SINKRON NYATA (dijalankan 23-Agu):** 35 baris tersinkron · **1 ditahan penjaga lonjakan**
(`gemini-2.5-flash-image` token $2,5→$30 = 12× → menunggu persetujuan admin di panel; tak berdampak
biaya karena formulanya per-gambar) · **5 tanpa-sumber** (flux ×2 `megapixels` + seedance ×2
`1m tokens` → **F4b**; suara Gemini → satuan ambigu, **F7**).
**Yang jadi otomatis & BENAR:** 3 naskah fal **$0,001 per PERMINTAAN** (sebelumnya tarif per-token
vendor asal — inilah cacat yang F7 tak perlu lagi tangani) · 2 suara fal-ElevenLabs ($50/$100 per 1jt
huruf) · hailuo $0,045/dtk · kling **pindah dari basis-per-klip ke $0,07/detik** (angkanya identik,
sudah dibuktikan aritmetika). **veo-3.1-fast DIKUNCI manual** ($0,10/dtk tanpa audio) — API fal hanya
menyebut angka **beraudio** $0,15, jadi sinkron otomatis akan 50% terlalu mahal.

**AMBANG:** 246 run dihitung ulang → **245 identik, 1 berbeda dan TERJELASKAN**: run #466 memakai
`google/gemini-2.5-flash` **lewat fal**, 5 panggilan → 5 × $0,001 = **$0,005** (sebelumnya $0,0095
memakai tarif per-token Google). Dibuktikan hitungan tangan; channelnya nonaktif. Penjaga `G12`
(7 uji) + 5 sabotase tertangkap.

**CATATAN PELAKSANAAN F7 (23-Agu).** Dua tarif yang **mesin mustahil menangkap** dibetulkan dari
halaman resmi vendor (§7d), lalu — ini bagian yang menentukan — **diberi JEJAK dan DIKUNCI**. Keduanya
lolos SELURUH pengaman yang ada: penjaga lonjakan butuh 3× (selisih `eleven_v3` 1,8×), dan biayanya
tetap **terhitung** sehingga laporan "biaya tak terhitung" pun diam. **suara Gemini** $0,3/$2,5 →
**$0,50/$10,00** (4 channel AKTIF; komponen suara **×3,96**, total per video **+4,1…+4,5%**) ·
**`eleven_v3`** $180 → **$100** (nol channel memakainya, tapi sinkron akan mempertahankan angka salah
itu selamanya bila tak dikunci). **5 baris lain angkanya SUDAH benar tapi tak punya jejak** — 3
ElevenLabs, Edge, Cloudflare — diberi catatan sumber+tanggal **tanpa menyentuh nilai tarifnya**.
Untuk Cloudflare jejaknya memuat **aritmetikanya + batas kapan ia berhenti benar** (96 neuron/gambar
⇒ 104 gambar/hari gratis per akun tenant; puncak nyata 22/hari).
**Penjaga `G13` (1 uji) menegakkan aturan §7c yang sudah tertulis sejak 22-Agu tapi NOL mesin pernah
memeriksanya** — dibuktikan **MERAH lebih dulu: 5 dari 6 baris ketikan-tangan melanggarnya**, lalu
**5 sabotase pada BENDA yang dijaga** (jejak dicabut · catatan dihapus · kunci dilepas ×2 · 4 baris
sekaligus) **semuanya tertangkap**. Perilaku "baris terkunci tak ditimpa sinkron" **tidak** dijaga
ulang di sini — sudah ada penjaganya (`test_harga_otomatis_model_fal.py`); lapis ganda = pengerusakan.
**AMBANG:** migrasi dijalankan **KERING** dulu → tepat **7 baris bergerak, tepat 2 berubah angkanya,
nol formula bergeser, 47 baris tetap 47**; hitung-ulang 246 run → **244 identik, 2 berbeda dan
keduanya memakai suara Gemini, nol tak terjelaskan**; sinkron kering sesudahnya → baris terkunci
**6 → 8** (dua baris itu kini aman). **Riwayat biaya tenant TIDAK ditulis ulang** — layar membaca
angka yang tersimpan per produksi, jadi yang benar berlaku mulai produksi BERIKUTNYA dan nol angka
lama tenant berubah. **Berlaku tanpa deploy** (tarif dibaca dari DB oleh mesin yang sudah terpasang).

**CATATAN PELAKSANAAN F5 (23-Agu).** Bila vendor MENYEBUT biayanya sendiri, mesin memakai angka itu
dan **berhenti menaksir** — seluruh rantai "jumlah yang kita ukur × tarif yang kita simpan" (tempat
kesepuluh cacat 23-Agu hidup) tidak dilewati sama sekali. Terverifikasi ke dokumen resmi OpenRouter:
`usage.cost` **selalu** dikirim (parameter `usage:{include:true}` sudah usang & tak berpengaruh),
satuannya *credit* dan **1 credit = 1 USD** (*"the base currency is US dollars"*). Angka itu dibaca
dari objek `usage` yang **sudah** kita terima ⇒ **nol panggilan tambahan, nol kredit**.
**Keranjang meter SENDIRI** (`biaya_vendor`) — bukan ditumpangkan ke keranjang token — sebab satu
panggilan yang punya dua cara ditagih di satu tempat adalah bentuk cacat "tertagih dua kali" yang
baru ditutup. Yang menentukan mana yang ditagih tetap **FORMULA di baris modelnya** ⇒ mustahil ganda
secara struktur. Baris ber-formula ini **tidak butuh tarif apa pun**, dan itu dicerminkan ke DB
(`pricing_model_tanpa_tarif`) supaya **panel berhenti memberi peringatan PALSU** "satuan harga kosong"
pada baris yang justru paling akurat — nol nama formula diketik di kode layar. Nama kolom vendor
**tidak ditebak**: hanya `cost` yang diterima; vendor lain yang memakai nama lain akan muncul di
laporan harian sebagai belum-terhitung (**berisik**, bukan salah diam-diam). Vendor diam → **JUJUR**
belum-terhitung, **haram** ditaksir dari token.
**BUKTI:** `G14` (8 uji, 4 dibuktikan MERAH lebih dulu) + `add_biaya_vendor` masuk batas "satu
pencatat" `G3` + **11 sabotase, semuanya tertangkap** · hitung-ulang 246 run: **0 run** punya
keranjang `biaya_vendor` dan **0 baris model** ber-formula ini ⇒ jalur baru mustahil menggeser angka
riwayat; ke-19 run yang berbeda dari angka TERSIMPAN **seluruhnya bernama** (16 hitung-ganda gambar
Gemini · 2 gambar+suara Gemini · 1 naskah fal per-permintaan), **nol tak terjelaskan** · 1399 uji
hijau · build FE lulus. **Batas jujur yang diuji, bukan didugaan:** penjaga cabang LAYAR berbasis
teks — ia menangkap pencabutan, tapi **tidak** menangkap pelumpuhan isi fungsi sementara namanya
dibiarkan (dicoba, tetap hijau). Menutupnya butuh penjalan uji layar yang belum ada di proyek ini.

**⛔ F5 SEPARUH DITOLAK DENGAN ALASAN TERUKUR — "selisih penghitung akun" TIDAK dipasang.**
Rencananya menyebut APIMaster diukur dengan menyelisihkan penghitung pemakaian akun
(`/v1/dashboard/billing/usage`, satuan SEN) sebelum & sesudah produksi. **Itu mustahil benar di mesin
kita**: produksi berjalan **SERENTAK** (`ThreadPoolExecutor`, `MAX_CONCURRENT_RENDER` = jumlah core),
jadi selisih penghitung satu akun tak bisa diatribusikan ke satu produksi — dua produksi tenant yang
sama akan saling mencuri biaya. Memasangnya = memasukkan kembali kelas cacat yang F1–F7 tutup, kali
ini dengan angka yang **tampak** pasti. Tempatnya yang benar = **rekonsiliasi tingkat TENANT (F8)**:
membandingkan total taksiran vs total pemakaian akun untuk satu periode, bukan per-produksi. Sampai
diketok owner, formula itu tetap dilaporkan **belum-terhitung** (jujur, berisik). Model APIMaster
sebaiknya memakai `naskah_token` dengan tarif resmi APIMaster.

**CATATAN PELAKSANAAN F6 (23-Agu).** Tombol Uji naskah dulu memanggil vendor dengan
`"Reply with exactly one word: OK"`, jatah **512** token, **tanpa** menuntut JSON. Produksi memanggil
hal yang jauh berbeda: `as_json=True` dengan jatah **1.200–2.000**, dan hasilnya wajib bisa diurai.
Bedanya bukan teori — **4 dari 6 model APIMaster LULUS panggilan pendek itu lalu GAGAL** pada
perintah naskah sesungguhnya (jawaban terpotong di batas keluaran, JSON gugur). Akibatnya lencana
**"✓ Teruji"** bisa BOHONG, dan gerbang DB `trg_gate_aktif_terbukti` (migr `0208`) yang menolak
menyalakan model tanpa audit LULUS **ikut tertipu** — ia menegakkan stempel yang isinya tak sepadan.
**Kini uji naskah memakai KONTRAK YANG SAMA dengan produksi:** minta JSON · jatah token = jatah
TERBESAR produksi (kenop `uji_model_max_tokens`, bawaan 2000) · hasilnya diurai oleh parser **yang
sama** (`parse_json_lenient`) · dan **kunci yang produksi baca** wajib ada & tak kosong. Vonis
gagalnya memisahkan dua sebab supaya admin tahu tindakannya: balasan **kosong** (jatah habis untuk
nalar internal) vs balasan **ada tapi tak bisa dipakai** (batas keluaran model lebih kecil dari jatah
naskah kita). Dialog Uji di panel menyebut apa adanya bahwa untuk model naskah kuota yang terpakai
lebih besar dari sekadar cek koneksi.
**BUKTI:** 7 uji, **5 dibuktikan MERAH lebih dulu** · **5 sabotase, semuanya tertangkap** — dan
sabotase-lah yang menemukan celah di penjaga saya sendiri (JSON **sah tapi tanpa kunci** yang produksi
baca tetap diluluskan; uji ke-7 ditambahkan untuk itu) · 1406 uji hijau · build FE lulus.
**BATAS JUJUR — wajib disebut:** (1) **20 dari 20 model naskah aktif** hari ini ber-stempel LULUS dari
uji **LAMA yang lemah**; stempel itu **tidak** dibatalkan (membatalkannya = mengunci model yang sedang
dipakai tanpa alasan terukur, dan itu keputusan owner). Menekan Uji sekali akan memperbaruinya.
(2) Uji **suara** masih memakai satu frasa pendek, padahal produksi mengirim naskah penuh — kelas yang
mungkin sama, tapi **belum ada satu pun bukti kegagalannya**, dan uji suara sepanjang produksi
berbiaya nyata tiap tekan. Tidak diubah tanpa ketokan owner.

**CATATAN PELAKSANAAN F8 (23-Agu).** Alarm yang sudah ada (`report_unpriced_models`, 22-Agu) menyala
bila penghitung **MENGAKU** gagal. Celah yang tersisa justru lebih berbahaya: penghitung **tidak
tahu** — angkanya keluar, tampak wajar, nol alarm menyala. Itu bentuk insiden 22-Agu (16 produksi,
biaya suara Rp 0, seluruh mesin diam). `report_rekonsiliasi_biaya` menutupnya dengan dua tanda yang
bisa diperiksa dari catatan kita sendiri, **nol panggilan ke vendor**, dan keduanya berarti uang nyata
tak tertagih: **(a)** ada PANGGILAN tercatat tapi token nol (vendor berhenti melaporkan pemakaian) ·
**(b)** ada pemakaian, biaya total 0, dan daftar belum-terhitung KOSONG. Dijalankan petugas harian
(1×/hari, dedup), **gagal-lunak mutlak** — ia pengawas, bukan jalur kerja.
**BUKTI:** 6 uji dibuktikan MERAH lebih dulu · **6 sabotase, semuanya tertangkap** (termasuk
"berhenti dipanggil petugas harian" = kode mati, dan "gagal-lunak dicabut") · dijalankan pada **data
produksi nyata**: `panggilan_tanpa_token = {}` · `nol_senyap = []` ⇒ **nol alarm palsu hari ini**;
nilainya menangkap REGRESI kelas itu, bukan memperbaiki angka hari ini · 1412 uji hijau.

**⛔ YANG TIDAK BISA DIKERJAKAN HARI INI — pembandingan ke PEMAKAIAN NYATA AKUN VENDOR.** Rencana
F8 menyebutnya; diperiksa, dan ground truth-nya **tidak tersedia**: (1) tak satu pun dari **9 penyedia
aktif** kita menerbitkan penghitung pemakaian yang bisa dibaca dengan kunci biasa; (2) membaca tagihan
akun **tenant** = keputusan owner, bukan keputusan saya — BYOK, itu akun mereka; (3) satu kunci tenant
bisa dipakai juga di luar MesinViral, jadi selisihnya akan memuat belanja yang bukan milik kita ⇒
alarm palsu yang **tampak** meyakinkan. Jalan yang BENAR untuk ground truth sudah dipasang di **F5**:
penyedia router melaporkan biaya per panggilan, tanpa menebak dan tanpa menyentuh tagihan tenant.
Begitu penyedia router ditambahkan, rekonsiliasi taksiran-vs-laporan-vendor menjadi mungkin dan
**akurat**; sebelum itu, memaksakannya = memasukkan kembali kelas cacat yang seluruh F1–F7 tutup.

**🔎 DUA TEMUAN DARI PENGUKURAN F8 — dilaporkan, TIDAK saya ubah sendiri (menyentuh layar).**
1. **`cost.breakdown` punya NOL pembaca.** Rincian biaya per komponen (naskah/suara/gambar/video)
   dihitung dan disimpan di **setiap** produksi, dan tak ada satu pun yang membacanya. Menurut
   definisi owner 19-Agu (`[B38]`) *"data yang dikumpulkan tapi tidak digunakan"* = **BUG**. Yang
   membuatnya lebih dari sekadar fosil: kelas CSS `.cost-bar`/`.cost-legend`/`.cost-item` **sudah ada**
   di `runs/[id]/run-detail.css` dan juga **tak dipakai siapa pun** — jadi layarnya pernah dirancang
   lalu tak pernah disambungkan. Menyambungkannya = menambah elemen di layar tenant ⇒ **ketokan owner**.
2. **Model gambar ber-tagih TOKEN masuk baris "naskah", bukan "gambar"** — **SUDAH DIPERBAIKI
   23-Agu.** Baris rincian kini ditentukan **jenis model yang skema tagihnya miliki**, bukan
   keranjang meter tempat pemakaiannya kebetulan tercatat (jenis tak pernah ambigu, keranjang bisa).
   Terukur pada hitung-ulang 246 produksi: **total TIDAK bergeser** (tetap 19 selisih dari sebab yang
   sama & sudah bernama), sementara **101 dari 246 produksi** rinciannya salah alamat — biaya gambar
   tersembunyi di baris naskah, dan baris gambar terbaca **Rp 0**. Riwayat tersimpan **tidak** ditulis
   ulang; yang benar berlaku mulai produksi berikutnya. Ini bukan lagi keputusan owner: nol layar
   tersentuh, nol angka total berubah, dan alamat yang salah tak punya pembelaan.
   Penjaganya: `test_biaya_megapiksel_dan_token_video.py::TestRincianBiayaTakSalahAlamat`
   (dibuktikan MERAH dulu; dijaga dua arah — naskah tetap naskah, suara tetap suara).

**CATATAN PELAKSANAAN F4b (23-Agu).** Empat baris fal ditagih dengan cara yang **tak bisa diwakili
satu angka tetap**: gambar per **megapiksel dibulatkan KE ATAS**, video seedance per **token**
`(tinggi×lebar×fps×durasi)÷1024`. Katalog kita menyimpannya sebagai angka yang dihitung TANGAN untuk
satu ukuran (1080×1920, 24fps) — benar hari ini, dan berhenti benar **tanpa suara** begitu resolusi,
fps, atau durasi berubah. Kelas yang sama dengan tarif suara Gemini: bukan angka hilang, tapi angka
yang berhenti cocok dengan cara vendor menagih.
**Yang dikerjakan:** dua keranjang meter baru (`image_megapiksel`, `video_token`) + dua pencatat, dan
**faktanya DIUKUR dari berkas hasil** — ukuran gambar dari berkasnya, dimensi & **fps** klip dari
`ffprobe` (satu panggilan, sama seperti probe durasi yang sudah ada). Sengaja mengukur, bukan memakai
angka katalog: kita **tak pernah menyebutkan fps** kepada vendor, dan resolusi yang dikirim vendor bisa
berbeda dari yang diminta ⇒ angka katalog adalah TEBAKAN. Pembulatan megapiksel terjadi **per gambar**
di pencatat (itu cara vendor menagih; membulatkan di akhir menghasilkan angka lebih kecil dari
tagihan). Gagal-lunak mutlak: satu fakta tak terukur → tak dicatat → biaya dilaporkan **jujur**
belum-terhitung, produksi jalan terus.
**NOL MIGRASI, NOL TULISAN TANGAN:** karena satuan vendor `megapixels` / `1m tokens` sekarang punya
jalan ke formula kita, **sinkron harian menulis tarif DAN formulanya sendiri** sesudah deploy.
Dibuktikan dengan **sinkron KERING ke API resmi fal** (endpoint harga, nol kredit): flux-schnell
`$0,003/MP` · flux-dev `$0,025/MP` · seedance-lite `$1/1jt token` · seedance-pro `$2,5/1jt token`,
dan formulanya bergerak `gambar_satuan → gambar_megapiksel` · `video_detik → video_token`.
**AMBANG — nol geseran hari ini:** flux-dev 1080×1920 = 2,07 MP → ditagih **3 MP** × $0,025 =
**$0,075** = persis `per_image` sekarang · seedance-pro 1080×1920 24fps 8s = **388.800 token** ×
$2,5/1jt = **$0,972** = persis 8 dtk × $0,1215 sekarang. Jadi F4b **tidak menggeser satu angka pun**;
yang ia beli adalah angka yang tetap benar bila ukuran/fps/durasi berubah. veo tetap **DIKUNCI** —
API fal menyebut $0,15 (beraudio) padahal pipeline kita mematikan audio ($0,10); sinkron kering
membuktikan kuncinya menahan.
**BUKTI:** 13 uji, **14 dibuktikan MERAH lebih dulu** · **11 sabotase, semuanya tertangkap — dan 3 di
antaranya menemukan celah di penjaga saya sendiri**: uji memakai `assertFalse` pada nilai yang
kebetulan 0 sehingga lolos saat penolaknya dicabut (dua kali), dan **mengganti pengukuran berkas
dengan angka tetap 1080/1920/24 lolos seluruh uji lama** — padahal itu justru inti F4b. Ketiganya
ditutup (kunci wajib TIDAK ADA, angka negatif besar dipakai, dan fakta yang diserahkan ke pencatat
haram berupa angka tetap di kode) · 246 run dihitung ulang: **nol geseran baru**, ke-19 selisih tetap
yang sama & tetap bernama · **0 run riwayat** punya keranjang baru · 1425 uji hijau · build FE lulus.
**Nol channel aktif memakai flux/seedance** hari ini ⇒ radius perubahan ini nol bagi tenant.
**Urutan yang WAJIB:** deploy dulu, baru sinkron harian memutakhirkan keempat baris itu sendiri.
Menyinkronkannya SEBELUM deploy akan membuat mesin lama (yang belum mengenal formula) melihat kunci
tarif yang tak ia pahami ⇒ biaya flux/seedance dilaporkan belum-terhitung. Nol channel aktif memakainya,
tapi urutannya tetap jangan dibalik.

**CATATAN PELAKSANAAN A·B·C (24-Agu, ketokan owner).** Tiga perbaikan bug di jalur yang SUDAH ada —
nol jalur baru, nol kolom baru, nol layar tersentuh.

**A · BIAYA TAK BOLEH TERTUKAR ANTAR PENYEDIA.** Ketokan owner: *"yang harus dipastikan tidak
overlaping adalah model yang sama tapi dari provider yang berbeda (direct, agregator, router)
masing-masing punya harga yang berbeda."* Diperiksa, dan bugnya nyata: meteran biaya mencatat **nama
model saja**, peta harga memakai nama itu sebagai kunci, dan `ai_models.model_id` **tak punya aturan
keunikan** (hanya `model_key`) ⇒ dua baris bernama sama, yang kedua **menimpa** yang pertama tanpa
suara. Hari ini aman **karena kebetulan** namanya berbeda (`gemini-2.5-flash` vs
`google/gemini-2.5-flash`), tapi router ber-protokol OpenAI menyebut model dengan nama **persis
sama** — jadi begitu APIMaster/OpenRouter ditambahkan, tabrakan itu PASTI terjadi, dengan selisih
**150×** ($0,15 per 1jt token langsung vs $0,001 per panggilan lewat fal).
**Perbaikannya:** titik pencatat **sudah tahu** penyedianya (`self.provider_key` / `platform` /
`provider_name`) — ia kini ikut jadi bagian kunci, dan bentuk kuncinya hidup di **satu tempat**
(`ai_cost.kunci_biaya`). Peta harga & formula mendaftarkan kunci ber-penyedia **selalu**, dan nama
polos **hanya bila tak ambigu**; nama polos yang dipakai >1 baris sengaja **tidak** didaftarkan ⇒
catatan tanpa penyedia dilaporkan **jujur** belum-terhitung alih-alih ditebak.
**AMBANG:** seluruh produksi riwayat dihitung ulang → **nol produksi yang BARU jadi belum-terhitung**;
101 selisih angka terjelaskan tepat = **19** (F2/F4/F7) **+ 82** (perbaikan tarif `gpt-image-1-mini`,
migr `0215`). 13 titik pencatat menyerahkan penyedianya, dijaga AST.

**B · GEMBOK TAK LAGI BERARTI DILUPAKAN.** Alarm harga-basi dulu berbunyi `if pricing_locked:
continue` — persis TERBALIK: baris **otomatis** dijaga alarm padahal ia memutakhirkan diri sendiri,
sementara baris **TERKUNCI** (satu-satunya yang BISA basi) tak dijaga apa pun. Kini dua kelompok, dua
jendela: sumber otomatis mandek **7 hari** · harga ketikan tangan belum diperiksa **30 hari**
(ANGKA MATI, keputusan owner: *"bukan bagian dari produksi, hanya pengingat"*). **Tanpa tanggal =
belum pernah dipastikan** ⇒ ikut berbunyi. Pesannya **memisahkan dua sebab** karena tindakannya beda,
dan menyebut cara mematikannya lewat jalur yang sudah ada: **✎ → Simpan** (memperbarui tanggal +
mengunci ulang) — nol tombol baru. Migr `0216` memberi **tanggal pemeriksaan yang sebenarnya** pada 6
baris (4 masih bertanggal Juli, 2 tanpa tanggal); tanpa itu alarm berteriak palsu di hari pertama.
**Dibuktikan pada 47 baris NYATA: nol alarm.**

**C · SINKRON BERHENTI MEMPERCAYAI "200 OK".** Diuji ke API nyata: **API harga fal menjawab HTTP 200
untuk endpoint yang TIDAK ADA** — nama karangan dijawab tarif GPU bawaannya. Jadi "200 OK" bukan bukti
modelnya ada, dan satu salah ketik penanda model bisa menulis harga yang tampak wajar untuk model yang
tak pernah ada; kita selamat hari ini hanya karena satuannya tak dikenali — **kebetulan, bukan
pemeriksaan**. Penutupnya memakai syarat yang sudah dipegang mesin: **harga tidak ditulis untuk model
yang belum pernah LULUS tombol Uji**. Terukur: 42 baris aktif **semuanya lulus** ⇒ nol kehilangan
pemutakhiran; 5 yang belum lulus semuanya **nonaktif**. Berlaku juga untuk probe satu-model dari panel
(model baru dapat harganya SESUDAH Uji). Ditambah: satuan vendor yang belum punya formula kini
**dialarmkan**, bukan cuma tercatat di log — vendor mengganti cara tagih adalah kejadian yang wajib
terlihat.

**BUKTI A·B·C:** 12 + 11 + 4 uji, **9 dibuktikan MERAH lebih dulu** · **10 sabotase, semuanya
tertangkap** — dan satu di antaranya menemukan celah di penjaga saya sendiri: melumpuhkan penyusun
kunci di meteran LOLOS seluruh uji lain (sebab uji-uji itu menyusun catatannya sendiri), ditutup
dengan penjaga perilaku pada meteran yang sesungguhnya · 131 uji rantai biaya hijau · migr `0216`
dijalankan KERING dulu dengan ambang yang membatalkan sendiri.
**Utang yang saya betulkan sendiri:** butir C membuat 3 uji lama merah karena data ujinya belum
memuat stempel "lulus uji" — **prasyaratnya dipenuhi di data uji, bukan dilonggarkan di kodenya.**

**ATURAN MENGIKAT tiap langkah** *(dilanggar = pengerusakan; sudah terjadi 21-Agu)*:
- **Satu langkah sekali jalan**, berhenti, lapor angkanya, baru langkah berikutnya.
- **Ambang berhenti:** seluruh produksi lama dihitung ulang; **satu selisih tak terjelaskan → BERHENTI & lapor.**
- **Ambang sinkron:** dijalankan KERING dulu; hanya baris yang seharusnya bergerak, yang bergerak.
- Alarm **dibuktikan MERAH dulu** → hijau → **disabotase**. `tests/test_gerbang_rantai_biaya.py` (17 alarm).
- **FE wajib memakai pustaka komponen yang ada** (nol komponen baru), seragam & estetik — bukan asal jadi.
- **Kolom baru → jawaban untuk baris LAMA wajib ada.** F1: kolom formula nullable, tapi **47 baris diisi
  dalam batch yang sama**; gerbang aktivasi baru menyala SESUDAH terisi ⇒ nol channel tenant terganggu.
- Deploy: **izin owner terpisah per langkah**. Ada tenant BERBAYAR yang produksi tiap hari.

**Angka acuan riset 23-Agu** (untuk membandingkan hasil kerja): 47 model terjelaskan · 244 run
dihitung ulang (227 identik · 17 beda satu sebab) · sinkron kering menggerakkan 3 baris · fal 11/12
bisa otomatis · `claude-haiku-4-5` lewat APIMaster **$0,00091** vs tarif langsung **$0,00982** ·
OpenRouter 0 model video, APIMaster 7.

---

## 7e. Batas jujur & tingkat kematangan

**Yang mesin TIDAK bisa jamin** (sebut, jangan sembunyikan): nilai tarif yang salah-tapi-masuk-akal ·
tagihan vendor atas percobaan yang gagal sebelum ia membalas · cara tagih yang belum pernah kita kenal
(butuh 1 baris di §7b — tapi ia **tak akan diam**: muncul di laporan harian).

**KUOTA GRATIS HARIAN — batas jujur yang berlaku HARI INI (F7, 23-Agu).** `cf-flux-schnell` tercatat
**$0/gambar**, dan itu BENAR selama pemakaian harian akun tenant di bawah kuota gratis Cloudflare
(10.000 neuron/hari). Aritmetikanya: 96 neuron/gambar ⇒ **104 gambar/hari masih gratis**; puncak nyata
yang terukur **22 gambar/hari per tenant** = kelonggaran 4,7×. **DI ATAS kuota, biayanya jadi nyata
sementara mesin tetap melaporkan $0** — formula `kuota_gratis` ada di katalog formula tapi penghitung
**belum mendukungnya** (butuh penghitungan neuron harian per akun tenant). Ini **tidak** disembunyikan
di angka: jejaknya tertulis di baris modelnya sendiri (§7c). Pemicu meninjau ulang: ada tenant yang
melewati ±100 gambar/hari pada satu akun Cloudflare.

**Tingkat kematangan** (tangga FinOps *crawl → walk → run*): sesudah F1–F8 kita berada di **walk** —
tiap model menyatakan formula hitungnya, tiap tarif ketikan-tangan berjejak & terkunci, kegagalan
hitung **berisik** (dua alarm harian: yang mesin sadari DAN yang tidak), dan untuk penyedia yang
melaporkan biayanya sendiri kita **berhenti menaksir**. **Bukan "run"**, dan syarat naik ke "run"
sudah jelas: ground truth dari luar (biaya yang vendor laporkan lewat penyedia router) + rekonsiliasi
berjadwal terhadapnya.

**RANTAI HARGA & BIAYA — DITUTUP 23-Agu.** F1–F7 + F4b tuntas; F8 sebagian (ground truth dari luar
belum tersedia — alasannya di §7f). Sisa yang menunggu **KEPUTUSAN owner**, bukan pekerjaan yang
terlupa: menampilkan rincian biaya per komponen di layar tenant · uji suara sepanjang produksi. Plus
satu SARAN: `selisih_akun` jangan dipasang per-produksi (produksi serentak).

**FOCUS (FinOps Open Cost and Usage Specification) — diperiksa 23-Agu, TIDAK diadopsi sebagai format.**
Sebabnya terverifikasi: FOCUS menormalkan **ekspor tagihan dari penyedia**, dan kita tak pernah
menerimanya (BYOK: tagihan milik tenant; vendor AI kita tak menerbitkan format itu). Yang **diadopsi**
hanya kosakatanya (§7b) karena ia menamai celah penyebab cacat. **Pemicu meninjau ulang:** bila
MesinViral membayar AI-nya sendiri (bukan BYOK), atau vendor mulai menerbitkan ekspor FOCUS.

---

## 8. Ringkasan "siapa menegakkan janji apa"

| Janji ke tenant | Ditegakkan oleh |
|---|---|
| Model aktif = pasti jalan | Tombol **Uji** (`model_tester`) + stempel `cost_hint.audit` + badge FE — **dan sejak 22-Agu DITEGAKKAN MESIN**: trigger `trg_gate_aktif_terbukti` (migr `0208`) menolak menyalakan model yang auditnya bukan `LULUS`, **atau** yang auditnya **lebih tua dari `unavailable_since`**-nya. Sampai 22-Agu janji ini bersandar DISIPLIN saja |
| "Valid" = token benar bisa dipakai | `validate_ai_key` (uji nyata, termasuk EL scoped) |
| Yang muncul di Channel = pasti aktif & jalan | filter provider aktif (FE) + `assertEnums` + `get_providers()` (aktif-only) |
| Harga akurat & otomatis | `price_sync` (feed + prefix data-driven, no hardcode). **BATAS TERUKUR (22-Agu): 16 dari 42 model aktif TIDAK ADA di umpan publik** — seluruh 5 model video, ElevenLabs (3), fal (11 total), Cloudflare, Edge ⇒ harganya **wajib diketik admin**. Panel menyebut asalnya (`manual` / `otomatis`) supaya penambahan vendor baru tak salah harap |
| Biaya per video benar | `cost_meter` → `compute_cost_usd` (× `usd_idr_rate`). **Kegagalan hitung tak lagi senyap** (22-Agu): tiap run mencatat `cost.unpriced`, dan `report_unpriced_models` melaporkannya harian ke admin. Layar tenant menyebutnya **perkiraan** (bukan "nyata") + penanda `≈` bila ada komponen yang belum terhitung — nol kode internal model dicetak ke tenant |
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
| `ai_models.pricing` | wajib sebelum dinyalakan; `per_request_usd`/`per_second_usd`/trio video **tak pernah** ditulis sinkron otomatis. **SATUANNYA harus yang dikenali `ai_cost` untuk JENIS itu** — bukan sekadar "ada isinya": umpan menulis satuan yang vendor pakai, dan itu bisa bukan satuan yang mesin kita hitung *(22-Agu: `gemini-2.5-flash-preview-tts` ber-harga token pada baris `component=tts` → biaya suara **Rp 0** di 4 channel aktif selama 16 produksi; lencana "harga kosong" tak menyala karena harganya memang tidak kosong)*. Penuntun satuan per jenis kini tampil di editor harga panel | biaya tenant **dilaporkan lebih murah dari kenyataan**, produksi tetap jalan (**nol rem berbasis biaya**). **Sejak 22-Agu tak lagi senyap:** `report_unpriced_models` melapor harian dari bukti produksi |
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
