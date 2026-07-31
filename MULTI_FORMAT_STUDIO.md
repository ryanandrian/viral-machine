# Multi-Format Short Studio — Spec Teknis Tervalidasi (Epic)

> ⛔⛔ **KOREKSI MENYELURUH 2026-07-31 — BACA SEBELUM APA PUN DI BERKAS INI.**
> Setiap klaim di berkas ini tentang **durasi video** yang menyebut *durasi-via-speed · atempo ·
> toleransi persen (±12%/±15%) · `_fit_duration` · `TTS_ATEMPO_*` · "speed menyerap variansi"*
> **SUDAH TIDAK BERLAKU.** Mekanismenya DICABUT dari kode: tuas kecepatan suara dilarang owner
> (29-Jul) dan terbukti tidak menghasilkan durasi — terukur dari 294 produksi nyata: 41% render
> mentok di batas paling lambat, NOL render normal, dan hanya **22% dari 243 video mendarat**.
> Penggantinya: alat ukur durasi terkalibrasi + kendali **jumlah kata & jumlah kalimat**.
> **SATU-SATUNYA ACUAN: `QC_CONTENT_ARCHITECTURE.md §2c`.** Titik-titik yang terdampak di berkas ini
> ditandai `⛔[dicabut 31-Jul → §2c]`. Jangan membangun atau memasang ulang apa pun dari klaim itu.


> ✅🔒 **CLOSED sbg backlog aktif (2026-07-01).** Mayoritas LIVE (durasi/QC/logo/link/visual-beats/adapter/compression-mapping). Sisa (**ai_video 8s** + **multi-platform Reels/TikTok**) = tercatat di **[`SISA_KERJA_GO_LIVE.md`](SISA_KERJA_GO_LIVE.md)** (B6/D2). **Dokumen ini = SPEC teknis (rujukan).**

> **Status:** 📋 PROPOSAL TERVALIDASI · 2026-06-11 · **Lampiran teknis** dari konsep di `DESAIN_PRODUK_SAAS.md` (induk). Tracker status A-to-Z di `PROGRESS.md`. Ringkasan + cross-link di memory [[plan_multi_format_studio]].
> Tujuan: MesinViral menampung **sebanyak mungkin kategori creator short-video faceless** (mystery/facts/edukasi-softsell/motivasi/brand) lintas durasi & platform.

---

> **🔄 REKONSILIASI AUDIT 2026-07-01 (verified DB/BE/git):** SEBAGIAN verdict §0 di bawah sudah USANG (diselesaikan): **durasi 30-90s + Cacat-B akurasi = TUNTAS** (F4 durasi-via-speed `8670fc3`) · **QC relatif** LIVE · **logo overlay + link deskripsi + soft-sell** LIVE · **variable visual beats** (N=`visual_beats` per preset) LIVE · **katalog `ai_models` DB-driven + adapter registry TTS/visual** LIVE (F5-06) · **compression-mapping per-preset** LIVE. **Masih BELUM:** `ai_video`/8s (file `ai_video.py` **tak ada** — belum dibangun) · **multi-platform Reels/TikTok** (belum ada abstraksi publisher; butuh audit eksternal 2-4 mgg — fitur tier). **Sisa DEFINITIF = `PROGRESS.md` blok AUDIT REKONSILIASI.** ⛔[dicabut 31-Jul → §2c]

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
| Preset | Word budget* | Beat (segmentasi) | Visual beat | Render mode | "Cocok untuk" (bahasa awam) |
|---|---|---|---|---|---|
| 8s | ~12-16 | `core` | 1 | `ai_video` | Kutipan atau satu fakta mengejutkan |
| 15s | ~21 | `hook-core` | 2 | image_sequence | Satu fakta cepat pemancing penasaran |
| 30s | ~45 | `hook-core-cta` | 3 | image_sequence | Fakta singkat dengan ajakan |
| 45s | ~70 | `+climax` (4) | 4 | image_sequence | Fakta dengan momen kejutan |
| 60s | ~97 | `+build_up` (5) | 5 | image_sequence | Cerita utuh yang padat (paling ideal) |
| 75s | ~120 | `+mystery_drop` (6) | 6 | image_sequence | Cerita dengan sentuhan misteri |
| 90s | ~150 | `+curiosity_bridge` (7) | 7 | image_sequence | Pembahasan mendalam dan lengkap |
\* Word budget = (detik − render_overhead) × **delivery_wps TTS** (overhead-aware). Visual beat = len(beats). **Segmentasi = SINGLE-SOURCE `duration_presets.beats` (migr 0053)** — mesin + panel tenant + admin baca sama.

**Pendekatan section (tervalidasi):** JANGAN rewrite skema jadi arbitrer (40–60% rewrite, risiko analyzer). Pakai **compression-mapping**: 8-section kanonik → kelompokkan jadi N beat sesuai preset (mis. 4 beat = hook / mystery+buildup / interrupt+core / bridge+climax+cta). Plus closed-loop speed-adjust (Edge/ElevenLabs) utk menepatkan durasi.

> ✅ **DEPLOYED 2026-06-18 (`05a3339` + migr `0053`) — SEGMENTASI SINGLE-SOURCE + STRUKTUR LEAN + 15s FIX:** segmentasi beat per preset pindah ke **`duration_presets.beats` (SUMBER TUNGGAL)** — dibaca `script_engine._beats_for_preset()` (fallback `_BEATS_FOR_N` pra-migrasi) + panel tenant/admin (anti-drift). **Struktur LEAN progresif** (keputusan owner): 8=`core` · 15=`hook-core` · 30=`hook-core-cta` · 45=+climax · 60=+build_up · 75=+mystery_drop · 90=+curiosity_bridge; `visual_beats=len(beats)`. `_validate_and_fix` required DINAMIS = {hook,core,cta}∩beats-aktif → 15s tanpa-cta & 8s core-saja LOLOS. + tabel `beat_glossary` (label awam dwibahasa, tooltip FE). **✅ Cacat B 15s FIXED** (struktur 2-beat + budget overhead-aware → ~21 kata → 14.5s, validated e2e). **Mapping lama "15→3, 30→5…" di bawah = SUPERSEDED.** Follow-up: analyzer skor hanya dim aktif (jangan hukum beat absen di ultra-short).
>
> ✅ **DIIMPLEMENTASI 2026-06-17 (`script_engine.py`) [mapping visual_beats SUPERSEDED oleh 0053]:** compression-mapping LLM per-preset AKTIF. `visual_beats` preset (15→3, 30→5, 45→6, 60→7, 75→8, 90→9) menentukan **N beat narasi = N scene** (`_BEATS_FOR_N`). Prompt `_build_user_prompt` render **BEAT PLAN dinamis** (beat aktif + budget-kata per-beat + intent naratif per-durasi: ultra-short=1 ide tajam … long=arc penuh). word-budget = `detik × WPS provider terdaftar`, didistribusi ke beat aktif. `_validate_and_fix` scene-count = `visual_beats` (selaras QC clip_count). **Validasi LLM-only (topik sama, 2026-06-17): 15/30/45/60/75/90 SEMUA word_count dalam rentang + scene=beats + durasi-EL pas.** 8s = ai_video (di luar image-sequence, epik terpisah).

> ✅ **DIIMPLEMENTASI 2026-06-17 (Opsi A — image-gen per-preset + VISUAL DNA; validated-lokal):** Pembuatan prompt visual dipisah **DUA TAHAP** (akar Cacat A "prompt asal jadi"):
> - **Tahap-1** (`script_engine._generate_one`) = NARASI saja — skema JSON bersih (buang visual_suggestions dari call narasi; slot `core_facts_2`; guard tiap beat aktif non-kosong).
> - **Tahap-2** (`script_engine.generate_visual_prompts`, dipanggil pipeline **STEP 4.5** SETELAH hook-optimize → grounded ke hook FINAL) = 1 LLM call TERDEDIKASI: baca narasi final per-beat → `thumbnail_concept` (hook-frame, ruang-negatif judul) + N−1 prompt scene KONKRET. **Clue per-scene = teks beat FINAL + VISUAL DNA niche + peran arc.** Sanitize + fallback ekstraktif (nol "N/A"/echo → tahan model image murah).
>
> **VISUAL DNA (no-hardcode, admin-curated):** kolom `niches.visual_style` di-perkaya jadi **kamus property bebas** (base_style, color_palette, atmosphere, **lighting, camera, composition, realism, reference, color_grading, motion**, …). Tahap-2 meng-inject **SELURUH key generik** (blok "VISUAL DNA") + `style_exemplars` (eks-`visual_fallbacks`, di-repurpose jadi few-shot acuan kualitas) + mandat "beauty-first". **Admin tambah/ubah key di `/admin/niches` → langsung berpengaruh, TANPA ubah kode.** `ai_image._build_image_prompt` tetap menempel `image_quality_tags`+`image_negative_prompt` per-niche. **Keempat base-niche terisi DNA 10-key.** Pipeline visual = **100% niche-applied** (audit: tenant.niche → fresh-load `visual_style`+`visual_fallbacks` → Tahap-2 + ai_image; no default-leak).
>
> **A5** scene-0 = thumbnail (no-waste, hapus image dibuang). **A6** Ken-Burns motion per-PERAN beat (bukan idx%6). **Validasi SOP lokal:** 6 preset jalur nyata config-DB → prompt bersih 6/6, image=`visual_beats`, ai_image murni (NO pexels); universe 60s = gambar sinematik nyata (ARRI/chiaroscuro/god-rays).
>
> ⚠️ **Akurasi durasi (Cacat B) — SEBAGIAN:** B1 budget speed-adjust (`detik × delivery_wps × niche_speed`) → **45/60/75/90 LOLOS QC**; **15s/30s overshoot** krn LLM melebihi word-budget §3 di preset pendek (root-cause data: TTS sudah benar — bila LLM patuh budget, 15s→16.8s & 30s→29.7s LOLOS). Fix B2 = paksa kepatuhan word-budget preset pendek (detail di `PROGRESS.md` §RENCANA KERJA IMAGE-GEN).

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

> ✅ **IMPLEMENTASI Cacat A — image-gen per-preset + VISUAL DNA (2026-06-17, validated-lokal):**
> - `script_engine.py` — Tahap-1 narasi-bersih (`_build_user_prompt`/`_validate_and_fix`: skema bersih, slot `core_facts_2`, guard beat aktif) · NEW `generate_visual_prompts()` = Tahap-2 (inject SELURUH `visual_dna` generik + `style_exemplars` + sanitize/fallback) · `compute_beat_durations()` (durasi per-beat) · B1 budget speed-adjust.
> - `pipeline.py` — **STEP 4.5** panggil `generate_visual_prompts` (pasca hook-optimize); set `script["beat_durations"]` pasca-TTS.
> - `visual_assembler.py` — image=`visual_beats` dari `beat_durations` (kompensasi xfade) · **A5** clip0=hook-frame, fetch hanya scene beats[1:] (no-waste) · pass `beat_roles`.
> - `ai_image.py` — `fetch_clips(beat_roles=…)` · `_image_to_video(role=…)` **A6** motion per-peran · `extract_keywords(n=…)`.
> - `video_renderer.py` — clip_durations dari `beat_durations` (fix bug −9s, bake==concat).
> - **DB (admin-data, bukan migrasi):** `niches.visual_style` keempat base-niche di-perkaya jadi VISUAL DNA 10-key. Admin edit via `/admin/niches` (update-API sudah whitelist `visual_style`).

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
