# Multi-Format Short Studio — Spec Teknis Tervalidasi (Epic)

> **Status:** 📋 PROPOSAL TERVALIDASI · 2026-06-11 · **Lampiran teknis** dari konsep di `DESAIN_PRODUK_SAAS.md` (induk). Tracker status A-to-Z di `PROGRESS.md`. Ringkasan + cross-link di memory [[plan_multi_format_studio]].
> Tujuan: MesinViral menampung **sebanyak mungkin kategori creator short-video faceless** (mystery/facts/edukasi-softsell/motivasi/brand) lintas durasi & platform.

---

## 0. ⚠️ VALIDASI TEKNIS TERVALIDASI (2026-06-11) — PEGANGAN, JANGAN ANALISA ULANG

Diaudit terhadap kode nyata + API eksternal. **Ini fakta acuan; sesi berikutnya pakai ini, jangan ulang audit (buang token).**

### Verdict per item (kode)
| Item | Verdict | Evidence (file:line) | Effort |
|---|---|---|---|
| Durasi 30–75s (section_timing per-preset) | 🟡 feasible | `script_engine.py:206-208` (target_duration, WPS=2.4, words=detik×WPS); `:96-105` `_get_section_timing` baca DB per-niche | medium |
| **Durasi 8–15s ultra-short** | ❌ blocker hari ini | QC `<45s` reject `pipeline.py:519-521`; skema 8-section tetap `:90-94` (Σ=51s); `max(4,words)`/section `:208` → ~13s floor; prompt asumsi naratif panjang `:249` | redesign berat |
| Variable section count/jenis | 🟡 rewrite 40–60% | skema 8-section tetap + `required` `script_engine.py:381` + `_validate_and_fix` + analyzer bergantung. **Pragmatis: compression-mapping per durasi**, bukan section arbitrer | berat |
| Closed-loop akurasi durasi | 🟡 belum ada | one-shot `pipeline.py:195-224`; `get_duration` (ffprobe) ukur saja, tak ada retry; deviasi ±5–15% | medium |
| TTS speed control | ⚠️ parsial | Edge `rate` ✅ (`edge_tts.py`), ElevenLabs `speed` ✅ (`elevenlabs.py`), **OpenAI TTS ❌ tak ada param** → jangan dipakai utk durasi presisi | low |
| Logo overlay | ✅ feasible | FFmpeg `filter_complex` sudah dipakai (`video_renderer.py` Step A `:609-726`, Step B `:737-775`); tambah `-i logo.png` + `overlay` ~50 LOC. Sekarang cuma `drawtext` teks, belum image overlay | low-med |
| QC window relatif | ✅ trivial | hardcode 45/180 `pipeline.py:519-521` → param ~20 LOC | low |
| Link di deskripsi (atas/bawah) | ✅ trivial | `youtube_publisher.py:82-140` `_build_metadata`; sisip link <10 LOC | low |
| **Pinned COMMENT** | ❌ MUSTAHIL | YouTube Data API tak punya endpoint pin (cuma list/insert/update/delete/setModerationStatus). **Bukan link di deskripsi — itu beda & bisa.** | — |
| Variable visual beats (N image) | 🟡 perlu refactor | hardcode `count=6` `visual_assembler.py:146`; preset→clip_count + section_map ~80 LOC; risiko motion-blur jika N kecil | medium |
| Katalog model AI "pure config" | 🟡 nanti | **HARI INI hardcode** `AI_IMAGE_MODELS` `ai_image.py:22-39`; jadi DB hanya setelah **Phase 1.3** (belum mulai) | depends 1.3 |
| Provider "adapter pluggable" | ✅ 85% | ABC `providers/{llm,tts,visual}/base.py` + factory dict `tenant_config.py:221-280`. Tambah provider = class + edit dict + deploy (bukan zero-touch/registry) | low-med |
| ai_video render mode | 🟡 high | `providers/visual/ai_video.py` ADA tapi **DISABLED** `visual_assembler.py:104-108`; integrasi ~115 LOC di video_renderer (branch single-clip, skip xfade, durasi sync) | high |
| Multi-platform publisher | 🟡 high | **belum ada abstraksi** — cuma `youtube_publisher.py`; `pipeline.py:30/53/317` hardcode YouTube; `publish_platforms` field ADA tapi **tak dipakai**. Butuh `base_publisher` + refactor loop dulu | high |

### Kendala API EKSTERNAL (gotcha produksi — wajib masuk perencanaan onboarding)
| Platform | Bisa? | Kendala kritis (lead-time / syarat) |
|---|---|---|
| **TikTok** (Scale) | Bisa, syarat berat | Tanpa audit = **SELF_ONLY/private**; **audit TikTok 2–4 minggu** utk post publik; pra-audit max 5 user/24h; ~15 post/hari/creator |
| **Instagram Reels** (Pro) | Bisa, syarat berat | Wajib akun **Business + Facebook Page + Meta App Review (2–4 minggu)** (`instagram_content_publish`); video via **URL publik**; 9:16 ≤90s; rate aman ~25/24h |
| **YouTube auto-pin comment** | ❌ TIDAK BISA | Tak ada endpoint API — final. (Link di deskripsi tetap bisa.) |
| **Text-to-video** (ai_video) | Bisa, sehat | 9:16 + 5–8s didukung semua (Kling/Runway/Luma/Veo/Sora), **BYOK key langsung**; **latency 1–3 menit/klip → WAJIB async** (queue kita sudah async ✓); biaya bervariasi besar → **wajib config-driven** |

**3 jebakan produksi yang harus selalu diingat:** (1) lead-time audit TikTok + App Review IG (2–4 mgg) saat onboarding tenant; (2) auto-pin YouTube **mustahil**; (3) latency video-gen 1–3 menit (jangan sinkron).

---

## 1. Positioning
Dari "tool creator viral faceless" → **studio short-video faceless multi-format**. Tambah segmen bernilai tinggi: **brand/advertiser soft-sell**, **motivational/quote**, **educator**. Contoh pemicu: brand suplemen imunitas → niche custom "imunitas_tubuh", 30s, 3–5/hari, soft-sell CTA + link landing.

## 2. Konsep inti: Section = fungsi (Format × Durasi)
Kategori section bergantung **niat konten**, bukan durasi saja. Dua sumbu: **Duration Preset** (detik + visual beat + word budget) × **Format Profile** (arc section + WPS + cta_mode + render_mode). Mesin existing sudah durasi-driven (§0) — yang berubah: section_timing & WPS jadi turunan (Format × Durasi).

## 3. Duration Presets — 8/15/30/45/60/75/90s
Word budget = detik × WPS(format). Visual beat = retensi vs biaya.
| Preset | Word budget* | Visual beat | Render mode | Catatan kelayakan |
|---|---|---|---|---|
| 8s | ~12-16 (WPS~1.6) | 1 | `ai_video` | butuh ai_video + bypass QC 45s |
| 15s | ~36 | 2-3 | image_sequence | **ultra-short: butuh skema section ringkas + QC relatif** |
| 30s | ~72 | 4-5 | image_sequence | feasible (section_timing preset + compression-map) |
| 45s | ~108 | 5-6 | image_sequence | feasible |
| 60s | ~144 | 6-7 | image_sequence | feasible |
| 75s | ~180 | 7-8 | image_sequence | feasible |
| 90s | ~216 | 8-9 | image_sequence | feasible (>180 lama, naikkan QC max) |
\* WPS per-format: energik ~2.4, edukasi ~2.2, motivasi ~1.6. Visual beat = angka awal, **A/B saat live**.

**Pendekatan section (tervalidasi):** JANGAN rewrite skema jadi arbitrer (40–60% rewrite, risiko analyzer). Pakai **compression-mapping**: 8-section kanonik → kelompokkan jadi N beat sesuai preset (mis. 4 beat = hook / mystery+buildup / interrupt+core / bridge+climax+cta). Plus closed-loop speed-adjust (Edge/ElevenLabs) utk menepatkan durasi.

> ✅ **DIIMPLEMENTASI 2026-06-17 (`script_engine.py`):** compression-mapping LLM per-preset AKTIF. `visual_beats` preset (15→3, 30→5, 45→6, 60→7, 75→8, 90→9) menentukan **N beat narasi = N scene** (`_BEATS_FOR_N`). Prompt `_build_user_prompt` render **BEAT PLAN dinamis** (beat aktif + budget-kata per-beat + intent naratif per-durasi: ultra-short=1 ide tajam … long=arc penuh). word-budget = `detik × WPS provider terdaftar`, didistribusi ke beat aktif. `_validate_and_fix` scene-count = `visual_beats` (selaras QC clip_count). **Validasi LLM-only (topik sama, 2026-06-17): 15/30/45/60/75/90 SEMUA word_count dalam rentang + scene=beats + durasi-EL pas.** 8s = ai_video (di luar image-sequence, epik terpisah).

## 4. Format Profiles (catalog `format_profiles`, admin-managed)
| format_key | Arc (scale dgn durasi) | cta_mode | render_mode |
|---|---|---|---|
| `viral_mystery` (existing) | hook→drop→buildup→facts→climax | implicit | image_sequence |
| `educational_softsell` | hook→masalah→insight→tips→soft CTA brand | soft_sell | image_sequence |
| `listicle_facts` | hook→fakta1→2…→payoff | implicit | image_sequence |
| `motivational_quote` | satu afirmasi (hook=cta) | optional | ai_video |
Kolom: `format_key`, `name`, `section_template` (jsonb roles+bobot), `default_wps`, `default_cta_mode`, `render_mode`, `is_active`.

## 5. Render modes
| Mode | Visual | Status |
|---|---|---|
| `image_sequence` | N image Ken-Burns + TTS + caption | ✅ core |
| `ai_video` | 1 klip text-to-video + voice/musik | 🟡 `ai_video.py` ada tapi DISABLED — integrasi ~115 LOC |

**ai_video = BYOK** (user-confirmed): tenant bawa key text-to-video (Kling/Runway/Luma/Veo/Sora). Async wajib (latency 1–3 mnt — queue kita sudah async). Biaya config-driven. **8s & ai_video TETAP masuk roadmap** (keputusan user: provider sudah support) — sebagai fase berat tersendiri.

### 5b. Katalog AI provider/model & extensibility (BYOK granular)
BYOK pilih **MODEL**, bukan cuma provider (tiap provider banyak model beda kualitas/biaya). **Realita: hari ini hardcode** (`AI_IMAGE_MODELS` `ai_image.py:22`); jadi config setelah Phase 1.3 + perlu diperluas TTS/video. Provider ABC + factory **sudah ada (85% pluggable)**.
- **Tambah model dari provider existing = pure config** (setelah katalog di DB) — admin tambah row, nol koding.
- **Tambah provider baru = adapter** (class implement ABC) + edit factory dict + deploy. Rekomendasi: registry Supabase-driven biar makin mudah.
- Katalog terunifikasi `ai_models` (component/provider/model_id/quality_tier/`cost_hint`/is_active) — `cost_hint` dukung transparansi biaya BYOK.

## 6. Branded Content layer (anti-hard-sell TETAP; logo + soft-sell + link)
**Logo embed:** upload logo → storage (R2/Supabase) → field `brand_logo`/`logo_position`/`logo_size`/`logo_opacity` → FFmpeg `overlay` (~50 LOC; ✅ feasible). Berlaku image_sequence & ai_video.
**Soft-sell CTA:** `cta_mode` = `implicit` | `soft_sell`. `soft_sell` izinkan SATU sebutan brand halus ("hidup sehat bersama [brand]"); TETAP larang hard-sell. Field `brand_name`, `brand_cta_text`.
**Link deskripsi:** `landing_link` + `link_position` (top|bottom) → `youtube_publisher` sisip <10 LOC. **Catatan: pinned comment mustahil; pakai link deskripsi.**

## 7. Multi-platform (tier-gated) — dengan kendala eksternal terdokumentasi
Aset 9:16 reusable. **Starter=YouTube; Pro=YouTube+Reels; Scale=YouTube+Reels+TikTok (ke-3).**
- **Belum ada abstraksi publisher** — butuh `base_publisher` + refactor `pipeline` (loop `publish_platforms`) dulu, baru tambah platform.
- **Reels (Pro):** akun Business + Page + Meta App Review 2–4 mgg; video via URL; ~25/24h.
- **TikTok (Scale):** audit TikTok 2–4 mgg utk publik (tanpa audit SELF_ONLY); ~15/hari/creator.
- Nyambung **BYO-CC** (kredensial IG/TikTok) + **Payment/tier** (Midtrans). **Lead-time audit masuk perencanaan onboarding.**

## 8. QC window
Hardcode 45–180s (`pipeline.py:519-521`) → **relatif `target_duration ± ~15%`** + render_mode-aware (ai_video/ultra-short tak kena aturan image-sequence). ~20 LOC.

## 9. Schema changes
**Channel/tenant config (atau per-slot `production_schedules`):** `duration_preset`, `format_profile`, `render_mode`, `cta_mode`, `brand_name`, `brand_cta_text`, `landing_link`, `link_position`, `brand_logo`+`logo_position`/`logo_size`/`logo_opacity`, `video_provider`+`video_api_key_enc`, model selection per komponen, `publish_platforms` (tier-validated), `qc_min/max_duration`.
**Catalog tables baru (admin-managed):** `format_profiles` (§4); `ai_models` terunifikasi (§5b, konsolidasi `ai_image_models` Phase 1.3 + TTS/video); (opsional) `duration_presets`; storage bucket `brand_logo`.

## 10. Module changes (peta + LOC tervalidasi)
| Modul | Perubahan | Effort |
|---|---|---|
| `script_engine.py` | section_timing & WPS dari (Format×Durasi) via compression-map; prompt dari `format_profiles`; `cta_mode=soft_sell` relax anti-promo + inject brand | medium |
| `tts_engine.py` + providers | closed-loop speed-adjust (Edge/ElevenLabs; OpenAI TTS dikecualikan) | medium |
| `video_renderer.py` | overlay logo (~50); branch `render_mode` ai_video (~115); QC relatif (~20) | medium-high |
| `visual_assembler.py` | visual beat dari preset (~80); enable ai_video (kini DISABLED) | medium |
| NEW `providers/video/*` | adapter text-to-video (BYOK, ABC pattern) | high |
| `youtube_publisher.py` | `landing_link`+`link_position`; brand CTA (<10) | low |
| NEW `distribution/base_publisher.py` + refactor `pipeline` | abstraksi publisher + loop `publish_platforms` (publish flow hardcode `pipeline.py:30/53/317`) | medium |
| NEW `distribution/reels_publisher.py`, `tiktok_publisher.py` | publisher (BYO-CC; +audit eksternal) | high+external |
| `tenant_config.py` | field baru (§9) + factory provider | low-med |
| katalog | `ai_models` + `format_profiles` loader (Phase 1.3 konsolidasi) | medium |

## 11. UI (dibangun langsung — Hybrid, BUKAN Claude Design)
Screen baru (tidak ada di bundle desain): format config (duration_preset/format_profile/render_mode + **model picker per komponen** dgn quality/cost), Branded Content panel (**upload logo** + soft-sell + link), Distribution panel (tier-gated, lock Reels/TikTok + **info lead-time audit**), Admin `format_profiles` + `ai_models` editor. Reuse token/komponen desain.

## 12. Roadmap placement (reklasifikasi tervalidasi)
- **A. Cheap wins (config+prompt, murah, value tinggi) → Phase 1.x:** QC relatif, link deskripsi, logo overlay, soft-sell CTA, durasi **30–75s** (section_timing preset + compression-map), katalog `ai_models` (konsolidasi Phase 1.3).
- **B. Medium → setelah cheap wins:** closed-loop akurasi durasi (speed-adjust), variable visual beats, provider registry polish.
- **C. Big/eksternal → fase tersendiri:**
  - **ai_video** (provider BYOK + integrasi renderer) — utk 8s motivasi & ultra-short.
  - **ultra-short 15s image_sequence** (skema section ringkas + QC) — kalau tanpa ai_video.
  - **Multi-platform** (base_publisher + Reels Pro + TikTok Scale) — nyambung BYO-CC Phase 4 + tier Phase 8; **terkunci audit TikTok/IG 2–4 mgg**.

## 13. Scope & keputusan (final)
- **Bahasa:** Latin saja (EN/ID/MY) — drop non-Latin. Selaras [[decisions_content_language]].
- **ai_video & ultra-short 8s:** **TETAP masuk** (user-confirmed; provider sudah support) — sebagai fase berat C.
- **ai_video = BYOK**; provider TBD (Kling/Runway/Luma/Veo/Sora — semua BYOK + 9:16/5-8s).
- **Section/visual mapping §3:** angka awal, A/B saat live.
- **Tier multi-platform:** Starter=YT, Pro=YT+Reels, Scale=ke-3.
- **Pinned comment dihapus dari scope** (mustahil API) — diganti link deskripsi.
- **Payment = Midtrans** (akun tenant/owner sudah ada) — Phase 8.

## 14. Dampak positioning
Memperluas TAM: faceless viral creator + brand/advertiser soft-sell + motivational + educator, sambil jaga filosofi anti-hard-sell (soft-sell terkontrol). Fondasi "MesinViral menampung sebanyak mungkin kategori creator short faceless".
