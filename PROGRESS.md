# MesinViral — Live Progress & Master Plan

> **Single source of truth** untuk status implementasi. Update setiap selesai sub-phase.
> Dibuat: 2026-06-10 | Update terakhir: 2026-06-11

---

## 🎯 Visi Akhir (dari [[project_vision]])

SaaS multi-tenancy, multi-channel — platform produksi konten video viral otomatis berbasis AI.
Setiap tenant: login → dashboard → config API keys → scheduler → lihat laporan & log produksi sendiri.

**Prinsip non-negotiable:**
- Kualitas konten = segalanya (no silent degradation)
- Config-driven, no hardcode biaya AI
- Self-learning & self-improvement
- Tenant isolation total (RLS di DB level)

---

## 📍 STATUS SAAT INI (2 track paralel)

**Track BACKEND:** ⏸️ Menunggu approval user untuk start **Phase 0** (lihat roadmap 12-phase di bawah).

**Track FRONTEND:** 🛠️ in-progress (`apps/web` Next.js 16 + React 19 + Tailwind v4, Hybrid). **DONE + tervalidasi (build PASS + curl 200):**
- ✅ Fondasi: design system port (tokens+components+app-shell), tema dark, lang ID — `36fa616`
- ✅ App Shell (sidebar+topbar `MVShell`) + theme/lang toggle + `/dashboard` placeholder — `ed1b2b5`
- ✅ D5 Run Detail (`/runs/[id]`) — pipeline live + log streaming + cost rail — `97d6f1c`
- ✅ D4 Runs List (`/runs`) — tabel + filter status + drawer slide-in → D5 — `2192488`
- ✅ A1 Landing (`/`) — hero+mockup, stats, problem, pipeline, 6 fitur, comparison, how, testi, pricing, FAQ, CTA + MarketingShell (nav+footer). Xendit→Midtrans. — `a2c2505`
- ✅ A2 Pricing (`/pricing`) — tiers + billing toggle (annual −20%) + full comparison + BYOK calculator (slider) + add-ons + FAQ. Xendit→Midtrans. — `5701cd0`
- ✅ B1-B4 Auth (`/auth`) — multi-view (signup/login/forgot/forgot-sent/verify/verified) split-screen + deep-link `?view=`. Auth nyata = Supabase Phase 4. — `7f413b5`
- ✅ D7 Schedule (`/schedule`) — view toggle week/month/list, AI optimization banner, slot grid 3 channel + pause/switch, month pips, list view — `f2bf4dd`
- ✅ B5 Settings (`/settings`) — tab nav (profil/keamanan/integrasi/notif/bahasa/danger), profil form, 2FA+sesi, integrasi, lang picker + theme toggle, danger zone — `d1a54e9`
- ✅ C1-C5 Onboarding (`/onboarding`) — wizard 5 langkah: paket, connect YouTube (verify sim), API keys BYOK (accordion+test), niche+**Bahasa Konten** (config-driven catalog→voice filtered)+voice+warna, jadwal week. Standalone pre-login. — (commit ini)

**Next:** Config (D8-D19) / Compliance (D20) / Insights (D21) / Admin (E1-E5) / next-intl / shadcn init / **PWA**. *(Chart D1/D2/D3/D6 = batch saat install tremor.)* *(Chart D1/D2/D3/D6 = batch saat install tremor.)* Data: mock → Supabase-first (RLS) saat backend mendarat. ⚠️ Next 16 breaking changes (`apps/web/AGENTS.md`) — baca `node_modules/next/dist/docs/` sebelum routing/middleware (next-intl). Detail [[plan_frontend_via_claude_design]].

> Frontend & backend jalan **paralel** — frontend pakai MOCK DATA dulu (tidak nunggu backend), wire ke Supabase saat phase backend mendarat. Frontend = Phase 9-10 di roadmap, tapi DIMULAI lebih awal secara paralel atas keputusan user.

**Last validated run:** Job #96 (2026-06-10 09:31 WIB) — SUCCESS, published https://www.youtube.com/shorts/Jf-soZuYIOs

**Active tenant:** `ryan_andrian` (single tenant)

---

## 🎨 FRONTEND — DESAIN SELESAI, IMPLEMENTASI HYBRID (Update 2026-06-11)

**Claude Design SELESAI 100%.** Handoff bundle (HTML/CSS/JS + screenshot, **32 file HTML ≈ 30 screen prototype + mobile/states**; spec brief = 39 screen logis) diterima & disimpan di `design-source/mesinviral-com/` (**gitignored** — tidak ke git/VPS). **Pengembangan UI lanjutan TIDAK lagi lewat Claude Design** — dikembangkan langsung di sini.

### Keputusan implementasi (user-confirmed 2026-06-11)

| Topik | Keputusan |
|---|---|
| **Strategi** | **HYBRID** — reuse CSS desain (tokens+components, 0 redesign) + shadcn/Radix HANYA utk komponen interaktif/a11y, di-tema pakai tokens desain. Charts: tremor. |
| **Repo** | **Monorepo** — frontend di `apps/web/` (Next.js 15) di repo ini. |
| **Sequencing** | Mulai **SEKARANG dgn MOCK DATA**, paralel/mendahului backend. Wire Supabase saat phase backend mendarat. |
| **Deploy** | **Vercel** (bukan VPS). VPS tetap bersih runtime Python. |
| **Data boundary** | **Supabase-first** — frontend→Supabase langsung (client SDK + RLS) + Realtime; **NO API layer Python**; worker = penulis data; endpoint minimal utk webhook Midtrans. |
| **Responsive + PWA** | Responsive: harmonisasi breakpoint (29/33 screen sudah `@media`) saat port. **PWA installable** (manifest + service worker) ditambah saat implementasi — web-only, no native. |

### Sumber desain (single source)

- `CLAUDE_DESIGN_BRIEF.md` — spec brief (39 screen, sudah termasuk multi-bahasa v4). Tetap acuan konten/layout.
- `design-source/mesinviral-com/project/` — bundle final: `CLAUDE.md` (build notes), `*.html` (32 file ≈ 30 screen prototype; brief spec = 39 screen logis, sebagian dibangun saat implementasi), `styles/` (tokens.css, components.css, shell.js/MVShell, icons.js/MVIcons, marketing.*, app-shell.*), `config/` (cfg-content, cfg-engines), `content-languages.js`.
- `CLAUDE_DESIGN_ADDENDUM_v2/v3/v4.md` — referensi delta (niche, pricing config-driven, multi-bahasa). Sudah terserap ke brief + desain; bukan untuk Claude Design lagi.

### Urutan kerja implementasi (NEXT)

1. **Fondasi** ← NEXT — setup `apps/web` (Next.js 15 + Tailwind), port `tokens.css`+`components.css`→global, `MVShell`→layout React, icons (lucide + SVG custom), i18n (next-intl ID/EN), theme (next-themes `data-theme`).
2. **Proof-of-concept:** D5 Run Detail (paling kompleks) → D1 Dashboard.
3. **Marketing:** A1 Landing + A2 Pricing.
4. **Auth + Onboarding** (C4 dropdown Bahasa Konten sebelum voice).
5. Sisa Dashboard (D2-D21) → Admin (E1-E5) → States/Mobile.

**Deviasi desain yg ditangani saat port:** A2/C1 literal "Rp..K"→placeholder `{{pricing.*}}`; ikon custom MVIcons→lucide+SVG; chart mockup→tremor; pola i18n span-ganda→next-intl.

### Decisions UX User-Confirmed (Claude Design Q1-Q9)

| Topik | Pilihan |
|---|---|
| **Start order** | Design system + D5 Run Detail (proof of concept) — BUKAN landing dulu |
| **Presentation** | Hybrid — clickable prototype untuk dashboard, static high-fid untuk marketing |
| **Theme** | Dark default + working light toggle |
| **Language UI copy** | Bahasa Indonesia default + working EN toggle |
| **Viewports** | Desktop 1440px + Mobile 375px untuk key screens (Landing, Pricing, Sign-up, Onboarding 5 step, Dashboard, D5 Run Detail) |
| **Typography** | **Geist Sans** (BUKAN Inter — terlalu generik AI-slop), JetBrains Mono untuk log viewer |
| **Charts** | Fully rendered dengan Indonesian sample data |
| **Real content** | Sample tenant Riko Pratama, channel "Misteri Samudra", niche ID, pricing real Rp 149/349/699K, AI cost real $0.34/video |
| **Priority demo** | D5 Run Detail → D1 Dashboard → A1 Landing → A2 Pricing → Onboarding step 3 (API Keys) → Compliance Score widget |

> Tabel "Decisions UX Q1-Q9" di atas = konteks historis desain (sudah baked-in ke output Claude Design). Bukan pekerjaan terbuka.

### Sumber Referensi untuk Sesi Berikutnya

[[plan_frontend_via_claude_design]] memory file (sudah di-rewrite 2026-06-11) — single source status frontend: lokasi bundle, strategi Hybrid, urutan kerja, fakta design system. **Baca itu + `design-source/.../CLAUDE.md` sebelum implementasi.**

### 🆕 Niche Model + Pricing Decisions (2026-06-11)

User confirm via AskUserQuestion 3-question session:
- **Niche granularity:** Hybrid broad + sub-tag layer (4 broad default + monthly release + tag pool per niche di videos)
- **Custom niche workflow:** Monthly release + on-demand custom request (hybrid model)
- **Exclusivity:** Public-after-90d (Rp 299K default) ATAU Permanent Private (Rp 1.499K default)
- **🚨 CRITICAL: Pricing CONFIG-DRIVEN** — semua nominal disimpan di table `pricing_config`, adjustable by sysadmin via admin panel E5 (NEW screen di brief)

Detail permanent reference: [[decisions_niche_model]] memory file.

**Implication backend (untuk Phase implementasi nanti):**
- Schema: tambah `tag_pool`, `released_at`, `access_type`, `exclusive_*` ke `niches`; `topic_tags` ke `videos`; NEW table `pricing_config`
- Helper `src/utils/pricing.py` dengan `get_price(key)` + caching 5 menit
- API `/api/pricing` endpoint untuk UI render

**Implication design brief (sudah di-update dalam session ini):**
- D18 Config Niches: dual-option request (public/private dengan pricing dari DB)
- E2.3 Admin Niches: tag pool editor + monthly release scheduler + exclusivity manager (expanded detailed)
- E5 NEW: Admin Pricing Config screen (CRUD pricing entries + audit log)
- Screen inventory 38 → 39

### Integration Tech Stack Target

Next.js 15 (App Router) + shadcn/ui + Tailwind + tremor.so + Geist Sans + next-intl (i18n) + Supabase Auth + Supabase Realtime + Vercel deploy. Detail per layer di [[plan_frontend_via_claude_design]].

**Repo structure:** ✅ DIPUTUSKAN (2026-06-11) — **monorepo**, frontend di `apps/web/` di repo ini. `apps/web` di-exclude dari sparse-checkout VPS; deploy ke Vercel.

**Domain:** `mesinviral.com` (landing) + `app.mesinviral.com` (dashboard) + `admin.mesinviral.com` (internal).

---

## 🗺️ MASTER ROADMAP (12 Phase)

> **Roadmap konsep di `DESAIN_PRODUK_SAAS.md §12`; STATUS LIVE = tabel ini (MASTER status — jangan duplikat status di tempat lain).** Disinkronkan 12-phase: Self-Learning+Diversity **Phase 6 (CORE MOAT)**, Compliance 7, Payment 8 (Midtrans), UI 9-10, Beta 11, Public 12.
>
> **Konvensi status (PRINSIP: tahap jadi ✅ HANYA jika TERBUKTI valid / running well — wajib ada bukti):** ⏸️ pending approval · 🔒 blocked · 🛠️/⏳ in-progress · ✅ DONE+VALIDATED (sertakan bukti: production run #, `npm build` PASS, curl 200, migration applied — catat di Status/VALIDATION HISTORY) · 🔄 continuous. **Update tabel ini tiap sub-phase yang lulus validasi.**

| Phase | Nama | Tujuan | Estimasi | Status |
|-------|------|--------|----------|--------|
| **0** | Audit & Persiapan | Verifikasi semua klaim SOFTCODE_AI_CONFIG vs kode | – | ⏸️ Pending approval |
| **1** | SOFTCODE AI Config | Hilangkan hardcode AI, hapus silent fallback (6 sub-phase) | 4-6 jam | 🔒 Blocked by Phase 0 |
| **2** | Error Mgmt Terpusat | `src/exceptions.py` + structured error flow | 2 jam | 🔒 Blocked by Phase 1 |
| **3** | Pipeline Run Logs (DB) | `pipeline_run_logs` table, RLS-ready, UI-facing | 2 jam | 🔒 Blocked by Phase 2 |
| **4** | BYO-CC Phase 1 | `tenant_credentials` + Fernet + auth foundation | 1 minggu | 🔒 Blocked by Phase 3 |
| **5** | Multi-Channel | `channels` table, channel_id propagation | 1 minggu | 🔒 Blocked by Phase 4 |
| **6** | 🥇 Self-Learning + Diversity Engine | **CORE MOAT** — pull YT Analytics 24-72h post-publish + adapt config; voice/hook/niche rotation | 2 minggu | 🔒 Blocked by Phase 5 |
| **7** | 🛡️ Compliance Score + AI Slop Defense | **SURVIVAL** — compliance calculator + polish diversity | 1 minggu | 🔒 Blocked by Phase 6 |
| **8** | Payment Integration | **Midtrans** (akun owner sudah ada) webhook handler + Email (Resend) + tier-gating | 2 minggu | 🔒 Blocked by Phase 7 |
| **9** | UI Foundation | Next.js + landing + dashboard + Supabase Realtime + RLS | 4-6 minggu | 🔒 Blocked by Phase 8 |
| **10** | UI Polish | Onboarding wizard + admin (E1-E5) | 2-3 minggu | 🔒 Blocked by Phase 9 |
| **11** | Beta Launch | 10 hand-picked tenant + feedback iteration | 1 bulan | 🔒 Blocked by Phase 10 |
| **12** | Public Launch | Marketing kick-off | – | 🔒 Blocked by Phase 11 |

**Cross-cutting (bukan phase bernomor):** Docs Sync — update `MESIN_VIRAL.md` + `roadmap_1.md` + memory tiap selesai sub-phase (lihat "Aturan Lintas Phase" di [[plan_master_softcode_to_saas]]).

**Catatan:** Detail sub-phase di bawah baru lengkap untuk Phase 0-5 (foundation backend). Detail Phase 6-8 ada di `DESAIN_PRODUK_SAAS.md`; detail UI Phase 9-10 mengacu `CLAUDE_DESIGN_BRIEF.md` + [[plan_frontend_via_claude_design]] (Claude Design workflow).

### 🧩 EPIC — Multi-Format Short Studio (proposal TERVALIDASI, 2026-06-11)

Perluasan produk: menampung **banyak kategori creator short faceless** (mystery/facts/edukasi-softsell/motivasi/brand). **Konsep/positioning** di `DESAIN_PRODUK_SAAS.md` (induk) · **spec teknis + validasi** di `MULTI_FORMAT_STUDIO.md` · ringkasan [[plan_multi_format_studio]].

> ✅ **Sudah divalidasi terhadap kode + API eksternal (2026-06-11)** — verdict per item ada di `MULTI_FORMAT_STUDIO.md §0`. **Jangan analisa ulang.**

**Plan-vs-realisasi (status per item):**
| Item | Feasibility | Status |
|---|---|---|
| QC window relatif · link deskripsi · logo overlay · soft-sell CTA | ✅ murah (~20-50 LOC each) | ⏳ Phase 1.x |
| Durasi 30–75s (section_timing preset + compression-map) | 🟡 medium | ⏳ Phase 1.x |
| Closed-loop akurasi durasi (speed-adjust Edge/ElevenLabs) | 🟡 medium | ⏳ setelah cheap wins |
| Variable visual beats · katalog `ai_models` (konsolidasi Phase 1.3) | 🟡 medium | ⏳ |
| **ai_video (BYOK)** + ultra-short 8–15s | 🟡 berat (`ai_video.py` DISABLED; redesign section) | ⏳ fase C |
| **Multi-platform** (base_publisher + Reels/TikTok) | 🟡 berat + **eksternal** | ⏳ fase C |

**⚠️ Kendala eksternal terdokumentasi (masuk perencanaan onboarding):** TikTok auto-post publik butuh **audit 2–4 mgg** (tanpa audit SELF_ONLY); IG Reels butuh akun Business+Page+**App Review 2–4 mgg**; **auto-pin YouTube comment MUSTAHIL** (pakai link deskripsi); ai_video latency 1–3 mnt → **wajib async** (queue kita sudah async).

**Keputusan final:** 8s & ai_video **tetap masuk** (provider support); Bahasa Latin saja; pinned-comment dihapus (mustahil); Payment = **Midtrans**; tier: Starter=YT, Pro=+Reels, Scale=ke-3 platform.
**Placement:** cheap wins → **Phase 1.x**; medium → setelah cheap wins; ai_video + multi-platform → fase C (nyambung **BYO-CC Phase 4** + tier **Phase 8 Midtrans**).

### ⚙️ ARSITEKTUR — Produksi & Scaling (TERVALIDASI 2026-06-12)

**Konsep/pondasi + pseudo-code di `DESAIN_PRODUK_SAAS.md §12c`** (rumah utama). Angka detail + bukti file:line di [[decisions_production_scaling]] (memory). Section ini = ringkasan status/roadmap. **Berbasis benchmark/log VPS nyata — jangan analisa/benchmark ulang.**

> 🔴 **Kritikal:** produksi 1 video = **35 mnt** terukur (render ~21 mnt dominan). Banyak tenant berbagi slot publish → spike → **VPS down** (terbukti live: 2-core/swap-0 OOM-mati di bawah render konkuren).

**Keputusan:**
- **Decouple produksi ↔ publish** — producer kontinu jaga **buffer per-channel**; publisher di slot ambil video ready (ringan). "Jadwal" = jadwal **publish**, bukan produksi.
- **Buffer = Biznet Gio S3** (co-located, ~50MB/file) + tabel **`content_inventory`** (source of truth status).
- **Concurrency cap = jumlah core + RAM ≥ ~2GB/core + tambah swap** (terbukti wajib).
- **Scale by core/node** (orkestrator bagi job), BUKAN lebih banyak proses di core sama.
- **Optimasi render = prioritas #1** — **2,87× terukur** (21→7 mnt) gabung 3 pass→1 + `veryfast`; + paralel image (10→2 mnt) → total **35→~13 mnt**.
- **Capacity model** (cores/RAM vs tenant) di memory: ~50 tenant→4 core, ~100→8 core, lalu multi-node 16-core.

**Placement:** optimasi render + paralel image + swap → **Phase 1.x** (murah, dampak terbesar, prasyarat scale). Decouple + buffer S3 + content_inventory + orkestrator multi-node → arsitektur dekat **Phase 5** / sebelum scale tenant.

---

## 🔍 PHASE 0 — Audit & Persiapan

**Tujuan:** verifikasi setiap klaim SOFTCODE_AI_CONFIG masih akurat di kode hari ini (file/line bisa shifted setelah 2 bulan).

### Checklist
- [ ] Git status bersih + `main` up-to-date dengan origin
- [ ] Verifikasi 7 lokasi hardcode LLM (SOFTCODE §1):
  - `src/intelligence/script_engine.py:415` (`"claude-sonnet-4-6"`)
  - `src/intelligence/script_engine.py:442` (`"gpt-4o-mini"`)
  - `src/intelligence/script_analyzer.py:149` (`"gpt-4o-mini"`)
  - `src/intelligence/hook_optimizer.py:143` (`"gpt-4o-mini"`)
  - `src/intelligence/niche_selector.py:412` (`"gpt-4o-mini"`)
  - `src/providers/visual/ai_image.py:310` (`"claude-haiku-4-5-20251001"`)
  - `src/providers/visual/ai_image.py:319` (`"gpt-4o-mini"`)
- [ ] Verifikasi 3 lokasi hardcode TTS (SOFTCODE §2):
  - `src/production/tts_engine.py:154` (chain `["elevenlabs", "openai_tts", "edge_tts"]`)
  - `src/production/tts_engine.py:156` (chain `["openai_tts", "edge_tts"]`)
- [ ] Verifikasi catalog `AI_IMAGE_MODELS` di `src/providers/visual/ai_image.py:20-38`
- [ ] Verifikasi 7 lokasi hardcode niche_fallback `"universe_mysteries"` (SOFTCODE §6)
- [ ] Cek `tenant_configs` schema sekarang (list semua kolom)
- [ ] Snapshot daftar file yang akan diubah + rencana commit per file

**Validation gate:** Tabel "klaim docs vs realita kode" disetujui user.

---

## 🔧 PHASE 1 — SOFTCODE AI CONFIG (6 sub-phase)

### 1.1 — LLM Refactor (paling besar, paling penting)
**Scope:**
- Schema: tambah `llm_library` (text), `llm_models` (jsonb) ke `tenant_configs`
- Code: refactor `script_engine`, `script_analyzer`, `hook_optimizer`, `niche_selector`, `ai_image` (untuk rewrite)
- **Hapus silent fallback Claude→GPT** di `script_engine._call_llm()`
- Per [[plan_s93_config_driven_llm]] yang sudah dimatangkan

**File yang berubah:**
- `src/intelligence/script_engine.py` — hapus fallback + fix ScriptAnalyzer key
- `src/intelligence/script_analyzer.py` — dual provider support
- `src/intelligence/niche_selector.py` — ganti `visual_api_key` → `llm_api_key` + dual provider
- `src/intelligence/hook_optimizer.py` — sama dengan niche_selector
- `src/providers/visual/ai_image.py` — prompt rewrite via `llm_models.rewrite`
- `src/config/tenant_config.py` — tambah field baru

**Validation gate:**
- Push ke main → SSH VPS → git pull → restart worker
- Update `tenant_configs` di Supabase: set `llm_library='anthropic'` + `llm_models` jsonb
- Enqueue 1 production run
- ✅ **Lulus jika:** pipeline COMPLETE + zero OpenAI call di log untuk komponen LLM (NicheSelector pakai Claude saat tenant Claude)

### 1.2 — Niche Fallback Config
**Scope:**
- Schema: tambah `niche_fallback` (text, default `'universe_mysteries'`) ke `tenant_configs`
- Code: hapus 7 hardcode `"universe_mysteries"` di:
  - `src/orchestrator/pipeline.py:575,595,599`
  - `src/intelligence/schedule_manager.py:110-111`
  - `src/intelligence/config.py:14`
  - `src/config/tenant_config.py:86,452,488,503`
  - `scripts/worker.py:79`
  - `src/production/visual_assembler.py:287`

**Validation gate:** `grep -r "universe_mysteries" src/ scripts/` = zero match (kecuali file provider/test/youtube_publisher data).

### 1.3 — Visual Image Catalog → DB
**Scope:**
- Schema: buat tabel `ai_image_models` (`model_key` PK, `platform`, `model_id`, `description`, `size`, `is_active`)
- Seed data: 3 model existing (flux-schnell, gpt-image-1-mini, stable-diffusion)
- Code: `ai_image.py` load catalog dari Supabase
- `visual_assembler.py` — hapus default `"gpt-image-1-mini"`

**Validation gate:** 1 production run sukses dengan model dipilih via DB row.

### 1.4 — TTS Fallback Softcode
**Scope:**
- Schema: tambah `tts_library` (text), `tts_fallback` (text) ke `tenant_configs`
- Code: `tts_engine.py` — bangun fallback chain dari config, bukan hardcode

**Validation gate:** fallback hanya dalam ekosistem yang sama (e.g., elevenlabs → edge_tts, BUKAN elevenlabs → openai_tts).

### 1.5 — Music + R2 Defaults Hapus
**Scope:**
- Schema: tambah `music_default_mood` ke `tenant_configs`
- Code: `music_selector.py:88` hapus default `"dramatic"`, baca dari config
- Code: `intelligence/config.py:35` hapus default `"viral-machine"` untuk R2 — wajib di `.env`, raise error jika kosong

**Validation gate:** start worker tanpa `R2_BUCKET` → error message jelas + tenant pakai mood dari config.

### 1.6 — Bug Fixes Bundle (pasangan refactor hari ini)
- **Dispatcher timezone bug**: `dispatch_pipeline_jobs()` saat ini compare publish_slots dengan UTC, tidak hormati `tenant_configs.timezone`. Fix: konversi target ke timezone tenant sebelum compare.
- **`AIImageProvider._generate_image()` signature mismatch**: warning saat hook_frame generation:
  ```
  WARNING [s6c7] Hook frame generation failed (AIImageProvider._generate_image() 
  missing 1 required positional argument: 'output_path')
  ```

**Validation gate:** dispatcher fire pada slot WIB yang benar + hook_frame generated tanpa warning.

---

## 🔁 GitHub Workflow Per Sub-Phase

```
1. Code change di /home/rad/viral-machine (WSL dev)
2. Test lokal jika applicable
3. git add <files> → git commit (per sub-phase, commit message standar)
4. git push origin main
5. ssh vps → cd ~/viral-machine → git pull origin main
6. pip install -r requirements.txt (jika ada)
7. Apply SQL migration via Supabase MCP (jika ada)
8. Restart worker: ssh vps → kill PID + nohup restart
9. Enqueue test job (INSERT pipeline_queue)
10. Monitor pipeline_queue + worker.log
11. ✅ Validate pass → UPDATE PROGRESS.md + memory + roadmap_1.md → commit "docs: phase X.Y validated"
    ❌ Fail → rollback (git revert) → diagnose → retry
12. → next sub-phase
```

### Commit Message Standar
```
feat(s93): softcode LLM library/models — niche_selector, hook_optimizer, script_analyzer

Phase 1.1 of master_softcode_to_saas. Removes hardcode model strings.
Validation: production run #97 success with claude-sonnet-4-6 end-to-end.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 📝 PHASE 2 — Error Management Terpusat
**Scope:**
- Buat `src/exceptions.py` dengan hierarchy: `PipelineError` → `ConfigError` / `LLMError` / `TTSError` / `VisualError` / `PublishError`
- Refactor semua `raise Exception(...)` → typed exceptions
- Pipeline catch typed → log + Telegram + write ke `pipeline_errors` (existing table)

**Validation gate:** simulasi 4 jenis error → semua tercatat di Supabase + Telegram notif sesuai jenis.

---

## 📊 PHASE 3 — Pipeline Run Logs (DB-based)
**Scope:**
- Schema: `pipeline_run_logs` table dengan `tenant_id`, `channel_id` (placeholder), `queue_id` FK, `level`, `step`, `message`, `metadata` jsonb
- RLS policy (placeholder, aktif setelah Phase 4)
- Custom loguru sink: `src/utils/db_log_sink.py` — batch insert ke DB
- Konsolidasi `pipeline_errors` + `qc_failed_videos` jadi views dari `pipeline_run_logs`
- Hapus rencana file-based `PIPELINE_LOG_SEPARATION` (superseded)

**Validation gate:** pipeline run → events appear in DB dalam < 5 detik dari emit.

---

## 🔐 PHASE 4 — BYO-CC Phase 1 + Auth foundation
> **Auth model DIPUTUSKAN ([[decisions_auth_rbac]]):** `tenant_id = auth.uid()` (1 user=1 tenant, no team); RLS=`tenant_id=auth.uid()`; super-admin via `app_metadata`; migrasi "ryan_andrian"→UUID di sini.

**Scope (per [[project_byocc_roadmap]]):**
- Tabel `tenant_credentials` di Supabase
- `src/utils/crypto.py` Fernet utility, master key di `.env` VPS (`ENCRYPTION_KEY`)
- Modifikasi `youtube_publisher.py` & `channel_analytics.py` load OAuth dari DB
- Mandatory key validation di pipeline start (per provider yang dipilih tenant)
- Hapus semua `.env` fallback untuk API key tenant

**Validation gate:** tenant tanpa required key → pipeline berhenti + Telegram notif yang jelas; tenant dengan key valid → pipeline jalan normal.

---

## 🎬 PHASE 5 — Multi-Channel per Tenant
**Scope:**
- Tabel `channels` (channel_id, tenant_id, youtube_channel_id, oauth_creds_enc, niche_default, is_active)
- `channel_id` propagation di pipeline (di-pass dari worker → orchestrator → publisher)
- `production_schedules` dapat `channel_id`
- Analytics isolation: `video_analytics` filter per channel
- Update `pipeline_run_logs.channel_id` aktif

**Validation gate:** 1 tenant 2 channel berbeda niche → both produce + publish independently.

---

## 🥇 PHASE 6 — Self-Learning + Diversity Engine (CORE MOAT)
**Scope (detail di `DESAIN_PRODUK_SAAS.md`):**
- Self-Learning Feedback Engine — pull YouTube Analytics 24-72h post-publish, adapt config per channel (niche/hook/visual weighting)
- Diversity Engine — voice/hook/niche rotation algorithm (AI Slop Defense)

**Validation gate:** TBD saat phase dimulai (post Phase 5).

---

## 🛡️ PHASE 7 — Compliance Score + AI Slop Defense Polish (SURVIVAL)
**Scope:**
- Compliance Score calculator (5 dimensi) — feed widget D20
- Polish diversity rotation + threshold tuning

**Validation gate:** TBD.

---

## 💳 PHASE 8 — Payment Integration
**Scope:**
- **Midtrans** (Indonesia-native, **akun owner sudah tersedia** per 2026-06-11) webhook handler — ganti rencana Xendit/Stripe
- Email service (Resend)
- Subscription state ↔ scheduler gate (suspend → stop produksi)
- Tier-gating: caps videos/day + platform (Pro=Reels, Scale=TikTok) + add-on (custom niche, ai_video BYOK)

**Validation gate:** TBD.

---

## 🎨 PHASE 9-10 — UI Foundation + Polish
**Scope (sesi terpisah — via Claude Design workflow, lihat [[plan_frontend_via_claude_design]]):**
- Next.js app baru atau subdir `apps/web/`
- Supabase Auth — login per tenant
- Page: dashboard, config, scheduler, reports, **logs per tenant**
- Supabase Realtime subscription untuk live tail `pipeline_run_logs`
- Deploy: Vercel atau VPS terpisah

**Validation gate:** tenant A login → hanya lihat data tenant A (RLS test).

---

## 📋 Docs Sync (Cross-Cutting, Continuous — bukan phase bernomor)
- Update `MESIN_VIRAL.md` per perubahan arsitektur (worker, dispatcher, tabel baru)
- Update `roadmap_1.md` per item completed (mark ✅ dengan tanggal)
- Delete `SOFTCODE_AI_CONFIG - BELUM DI EKSEKUSI.md` setelah Phase 1 selesai
- Delete `PIPELINE_LOG_SEPARATION - BELUM DI EKSEKUSI.md` setelah Phase 3 selesai
- Sync memory files dengan realitas baru

---

## 🐛 KNOWN ISSUES (Hari Ini, 2026-06-10)

| # | Issue | Severity | Phase | Notes |
|---|---|---|---|---|
| 1 | NicheSelector/HookOptimizer/ScriptAnalyzer hardcode OpenAI meskipun config Claude | 🔴 Critical | Phase 1.1 | Root cause kegagalan job 94 & 95 hari ini |
| 2 | Dispatcher `dispatch_pipeline_jobs()` tidak hormati `tenant_configs.timezone` — publish_slots di-treat UTC | 🟠 High | Phase 1.6 | publish_slots `[14:00, 23:00]` WIB sebenarnya fire pada 05:30 & 20:30 WIB karena UTC interpretation |
| 3 | `AIImageProvider._generate_image()` signature mismatch saat hook_frame | 🟡 Medium | Phase 1.6 | Non-fatal, fallback ke clip[0] |
| 4 | `tenant_configs.publish_slots` setting WIB tapi treated UTC | 🟠 High | Phase 1.6 | Bagian dari issue #2 |

---

## 📂 FILE REGISTRY

### Project root (this repo) — semua `.md` di-exclude dari VPS (sparse-checkout aktif)
- `PROGRESS.md` — **this file** — live status A-to-Z (plan vs realisasi) + master roadmap 12-phase + EPIC tracker
- `DESAIN_PRODUK_SAAS.md` — **konsep induk produk** (business, pricing, roadmap, epic concept §12b, payment Midtrans)
- `MULTI_FORMAT_STUDIO.md` — **spec teknis epic Multi-Format Studio** + **§0 validasi tervalidasi (jangan analisa ulang)**
- `CLAUDE_DESIGN_BRIEF.md` — spec desain UI (39 screen); bundle final di `design-source/` (gitignored)
- `CLAUDE_DESIGN_ADDENDUM_v2/v3/v4.md` — delta prompt desain (historis; sudah terserap ke brief+bundle)
- `MESIN_VIRAL.md` — dokumentasi arsitektur teknis (perlu sync, terakhir update 8 Apr 2026)
- `roadmap_1.md` — checklist roadmap (perlu sync, terakhir update 8 Apr 2026)
- `SOFTCODE_AI_CONFIG - BELUM DI EKSEKUSI.md` — spec Phase 1, akan dihapus saat selesai
- `PIPELINE_LOG_SEPARATION - BELUM DI EKSEKUSI.md` — superseded oleh Phase 3 DB-based

### Memory (auto-loaded sesi baru)
- `MEMORY.md` — index
- `plan_master_softcode_to_saas.md` — ringkasan master plan (this doc → memory)
- `progress_journal.md` — per-phase completion log
- `project_vision.md` — visi & prinsip non-negotiable
- `project_byocc_roadmap.md` — BYO-CC roadmap (memory)
- `plan_s93_config_driven_llm.md` — **superseded** oleh Phase 1.1
- `feedback_workflow.md` — wajib propose dulu
- `feedback_no_hardcode.md` — no silent fallback
- `feedback_analysis_discipline.md` — no asumsi liar

---

## 🚀 QUICK-START UNTUK SESI BARU

**Urutan baca kanonik = `MEMORY.md` (auto-loaded) — ikuti itu.** Ringkas:
1. `MEMORY.md` (index + urutan baca) → 2. `progress_journal.md` (kronologis terbaru) → 3. **file ini** (status LIVE + next step) → 4. `DESAIN_PRODUK_SAAS.md` (pondasi: bisnis, arsitektur §12b/§12c).
   Lalu sesuai TRACK: **Backend** → [[decisions_production_scaling]] + `MULTI_FORMAT_STUDIO.md §0` + `SOFTCODE_AI_CONFIG…md`; **Frontend** → [[plan_frontend_via_claude_design]] + `design-source/mesinviral-com/project/CLAUDE.md` + `CLAUDE_DESIGN_BRIEF.md`.
5. Verify state: `git status` + `git log -5` + (track backend) `ssh vps && tail logs/worker.log`.
6. Tanya user: "Lanjut dari [next-step di STATUS SAAT INI] atau ada arahan baru?"

**⛔ Jangan jadikan acuan:** `MESIN_VIRAL.md`, `roadmap_1.md` (usang April), `PIPELINE_LOG_SEPARATION` (superseded Phase 3), `plan_s93` (superseded Phase 1.1) — semua sudah ada banner.

---

## 📊 VALIDATION HISTORY

| Tanggal | Phase | Job ID | Hasil | Notes |
|---------|-------|--------|-------|-------|
| 2026-06-10 09:31 | Pre-Phase-0 | #96 | ✅ SUCCESS | OpenAI billing aktif, pipeline normal, dipakai sebagai baseline |
| 2026-06-10 05:30 | — | #95 | ❌ FAILED | OpenAI 429 billing_not_active — root cause yang memicu refactor |
| 2026-06-09 20:30 | — | #94 | ❌ FAILED | Same as #95 |
| 2026-06-09 05:30 | — | #93 | ✅ SUCCESS | Sebelum billing OpenAI berhenti |

---

**END OF FILE. Update setiap selesai sub-phase.**
