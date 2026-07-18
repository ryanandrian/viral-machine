# 🔍 AUDIT HARDCODE FORMAT VIDEO (PORTRAIT/SHORTS) — fondasi fitur "format per-channel"

> **Dibuat 2026-07-19 atas perintah eksplisit owner** ("deep dive, tidak boleh ada 1 baris terlewat, seluruh temuan dalam tabel pada file md baru khusus"). File .md baru = otorisasi owner (pengecualian sadar §1.1 CLAUDE.md).
> **Fitur yang dituju:** tenant memilih PER-CHANNEL: video **Short (portrait 9:16)** — aktif hari ini, atau **Regular (landscape 16:9)** — status "coming soon" dulu.
> **Status dokumen:** INVENTARIS + arah tindakan. **BUKAN rencana eksekusi** — rencana teknis rinci menyusul lewat proposal → ketok owner. Nol kode boleh diubah dari dokumen ini saja.
> Semua baris di bawah TERVERIFIKASI langsung (grep kode + query DB live 2026-07-19) — nol asumsi.

## §1 METODE (agar auditor lain bisa mengulang)
- **Pola sapu:** `1080|1920|1280|720` · `9:16|16:9|9/16|16/9|aspect(:|_|-)ratio` · `portrait|landscape|vertical|horizontal|vertikal` · `shorts|short-form` (ci) · `image_size|size=|1024x|1792|1536` · filter ffmpeg `scale=|crop=|pad=` · `content_type` (jalur short/long).
- **Cakupan:** seluruh `src/` (semua .py) · `apps/web/src` (.tsx/.ts/.css) · `migrations/` · `scripts/` · `tests/` · `.env` (nama kunci saja) · **DB live** (skema + isi katalog `ai_models`/`duration_presets`/`format_profiles`/`niches`/CMS).
- **Dikecualikan secara sadar:** `node_modules`/`.next`/log/aset gambar · direktori eksperimen untracked (`uji-fal/`) · dokumen .md internal (bukan permukaan runtime — dicatat file-level di §8).
- Legenda kolom TINDAKAN: **🔀CABANG** logika bercabang per-format · **⚙️PARAM** jadikan parameter turunan format · **🤖PROMPT** prompt AI ikut format · **📄COPY** teks/copy disesuaikan · **🧷JAHITAN** seam sudah ada, tinggal dipakai · **🗄️DB** butuh skema/katalog · **✅AMAN** diperiksa, tak perlu diubah.

## §2 FAKTA ARSITEKTUR KUNCI (pegangan sebelum menyentuh apa pun)
1. **Jahitan `short`/`long` SUDAH ADA setengah jadi (s92):** `TenantRunConfig.content_type` (`tenant_config.py:152-154`, komentar "long belum diimplementasi") + thumbnail publisher sudah bercabang (`youtube_publisher.py:379-383`). TAPI nilainya **dipatri** di `pipeline.py:106` dan **tak ada kolom DB** yang mengisinya (bukan anggota `_CHANNEL_OVERLAY_FIELDS`).
2. **`channels.format_profile` & `duration_presets` = BUKAN orientasi** — profil alur-narasi & durasi khusus shorts (`MULTI_FORMAT_STUDIO.md`: 0 sebutan landscape). Fitur ini = dimensi BARU.
3. **Tidak ada kolom orientasi** di `channels`/`videos` (verifikasi information_schema 19-Jul).
4. **Gerbang QC pakai ENV, bukan DB:** `QC_ASPECT` (default "9:16"), `QC_MAX_DURATION` (180, "batas platform Shorts") — lihat §7c.
5. Durasi video regular berbeda semesta (menit, bukan 8–90 dtk) → katalog `duration_presets` per-format adalah pertanyaan desain, bukan sekadar cabang kode.

## §3 BACKEND (Python) — tabel lengkap per-baris

| # | File:Baris | Kutipan/Isi | Jenis | Tindakan |
|---|---|---|---|---|
| B1 | `src/production/video_renderer.py:61-62` | `OUTPUT_WIDTH=1080` `OUTPUT_HEIGHT=1920` — **jantung render**, dipakai SEMUA scale/crop | Dimensi kanvas | ⚙️PARAM (kanvas dari format channel) |
| B2 | `video_renderer.py:526-528, 610-612, 637-639, 691-693, 746, 992` | `scale/crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}` (6 titik, termasuk thumbnail :992) | Filter ffmpeg | ✅AMAN bila B1 di-param (semua merujuk konstanta) |
| B3 | `video_renderer.py:25, 89, 199-200, 332, 377-378` | Posisi caption `margin_v`/`y_start` = % dari `OUTPUT_HEIGHT`; ASS `PlayResX/Y` | Tata letak caption | ✅AMAN bila B1 di-param — TAPI **wajib uji visual landscape** (font 68/58 & words_per_line ditala utk portrait → kemungkinan perlu preset caption per-format) |
| B4 | `src/orchestrator/pipeline.py:106` | `resolved_content_type = "short"` — nilai dipatri, tak pernah dari channel | Jahitan mati | 🧷JAHITAN+🔀CABANG (isi dari kolom channel baru) |
| B5 | `pipeline.py:805-814` | QC aspek `os.getenv("QC_ASPECT","9:16")` + parser rasio | Gerbang QC | 🔀CABANG (target aspek per-format; kenop per-format) |
| B6 | `pipeline.py:741, 759, 785` | `QC_MAX_DURATION` 180 "batas platform Shorts"; pesan "bukan Shorts" | Gerbang QC + pesan | 🔀CABANG+📄COPY |
| B7 | `pipeline.py:434-435` | Rekomendasi error "Rasio video tidak 9:16" | Pesan tenant | 📄COPY (ikut format) |
| B8 | `pipeline.py:520` | Log "Uploading to YouTube Shorts..." | Log | 📄COPY |
| B9 | `src/config/tenant_config.py:152-154` | `content_type: str = "short"` (+komentar long belum ada) | Jahitan config | 🧷JAHITAN (+ masukkan ke `_CHANNEL_OVERLAY_FIELDS` :436 bila jadi kolom channels) |
| B10 | `src/distribution/youtube_publisher.py:157` | Hashtag universal `["#Shorts"]` | Metadata publish | 🔀CABANG (regular tanpa #Shorts) |
| B11 | `youtube_publisher.py:215` | Tags `["shorts","youtubeshorts","viral"]` | Metadata publish | 🔀CABANG |
| B12 | `youtube_publisher.py:333` | URL hasil `youtube.com/shorts/{id}` | URL | 🔀CABANG (regular = `watch?v=`) — ⚠️ konsumen URL: `producer.py:28-31` regex SUDAH mendukung keduanya ✅ |
| B13 | `youtube_publisher.py:363-402` | Thumbnail: `long→1280×720`, `short→1080×1920` | Jahitan siap | 🧷JAHITAN (sudah 2-cabang, tinggal dialiri) |
| B14 | `youtube_publisher.py:63, 267, 489` | Docstring/CLI "YouTube Shorts" | Teks dev | 📄COPY (minor) |
| B15 | `src/providers/visual/ai_image.py:573` | ffmpeg `S="s=1080x1920,setsar=1"` (jalur pad gambar persegi) | Dimensi | ⚙️PARAM |
| B16 | `ai_image.py:487` | Gemini `imageConfig.aspectRatio: "9:16"` | Param API | 🔀CABANG per-format |
| B17 | `ai_image.py:294` | Suffix prompt "vertical 9:16, photorealistic" | Prompt AI | 🤖PROMPT |
| B18 | `ai_image.py:210` | Klip hasil: `width=1080, height=1920` (metadata klip) | Dimensi | ⚙️PARAM |
| B19 | `ai_image.py:617` | Ken Burns "→ video 9:16" | Dimensi efek | ⚙️PARAM |
| B20 | `ai_image.py:71, 442` | Default size `"1024x1536"` (gpt-image, potret 2:3) — sumber = `ai_models.default_params` DB | Param DB-driven | 🗄️DB (lihat §7b — katalog per-format) |
| B21 | `src/providers/visual/ai_video.py:33, 124` | "1 klip 9:16"; `width=1080, height=1920` | Dimensi | ⚙️PARAM + 🗄️DB (aspect_ratio di katalog) |
| B22 | `src/production/visual_assembler.py:322` | Prompt hero/thumbnail "Cinematic vertical 9:16 hero image" | Prompt AI | 🤖PROMPT |
| B23 | `visual_assembler.py:362-363` | `width=1080, height=1920` (metadata klip) | Dimensi | ⚙️PARAM |
| B24 | `src/intelligence/script_engine.py:797, 836, 921` | Prompt gambar "vertical 9:16 / Vertical 9:16" (3 titik) | Prompt AI | 🤖PROMPT |
| B25 | `script_engine.py:820, 908` | "short-form vertical video / vertical clip" | Prompt AI | 🤖PROMPT |
| B26 | `script_engine.py:646` | Contoh hashtag `"#shorts"` di skema output naskah | Prompt AI | 🔀CABANG |
| B27 | `src/intelligence/niche_selector.py:428` | Prompt "PLATFORM: YouTube Shorts, TikTok, Instagram Reels" | Prompt AI | 🤖PROMPT |
| B28 | `src/intelligence/channel_analyst.py:297` | Prompt analis "automated YouTube Shorts machine" | Prompt AI | 🤖PROMPT (ikut format channel) |
| B29 | `src/intelligence/trend_radar.py:249` | Query pencarian default `"shorts"` | Sinyal tren | 🔀CABANG (regular: query beda? = keputusan desain) |
| B30 | `src/config/model_tester.py:117` | Prompt uji "vertical 9:16" | Alat uji admin | 🤖PROMPT |
| B31 | `src/utils/telegram_notifier.py:142` | Klasifikasi pesan QC "aspect/rasio/9:16" | Pesan | 📄COPY |
| B32 | `src/utils/email.py:306, 313` | Copy email nurture menyebut konteks video otomatis/Shorts | Copy email | 📄COPY |
| B33 | `migrations/0016_branding_config.sql:8` | `logo_max_w_px 220` ("≈20% dari 1080") | Batas logo | ⚙️PARAM (relatif thd lebar kanvas) |
| B34 | `.env` kunci `QC_ASPECT`, `QC_ASPECT_TOLERANCE`, `QC_MAX_DURATION`, `QC_MIN_DURATION` | Nilai QC platform-wide di env | Config lokasi | 🗄️DB/🔀 (per-format; pindah/turunkan — keputusan desain) |

## §4 FE-TENANT

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| T1 | `apps/web/src/app/(app)/channels/[id]/page.tsx:952-963` | Pratinjau caption `aspectRatio: "9/16"` | 🔀CABANG (pratinjau ikut format channel) |
| T2 | `(app)/runs/[id]/run-detail.css:72` | `.thumb { aspect-ratio: 9/16 }` | 🔀CABANG (thumbnail runs) |
| T3 | `components/test-niche-panel.tsx:118` | Pemutar video hasil Test (style mengikuti video) | ✅AMAN (player HTML menyesuaikan) — verifikasi visual saat landscape |
| T4 | `channels/[id]` — **dropdown format BELUM ADA** | Titik lahir UI fitur: pilihan "Short / Regular (coming soon)" | 🔀CABANG (elemen UI baru = wajib ketok §2.3d) |

## §5 FE-ADMIN

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| A1 | `admin/(panel)/content/page.tsx:50-54` | Hint upload showcase "MP4 9:16 / PNG 9:16" | 📄COPY (bila showcase kelak menampung landscape) |
| A2 | `api/admin/showcase/upload/route.ts:8` | Komentar "MP4 ... 9:16" | 📄COPY |
| A3 | `admin/(panel)/niches/page.tsx:236` | Teks bantuan menyebut shorts | 📄COPY |
| A4 | `admin/(panel)/content/page.tsx:19-20` | Cover blog "16:9 1376×768" | ✅AMAN (blog memang landscape — bukan video produk) |

## §6 FE-MARKETING + EMAIL

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| M1 | `(marketing)/page.tsx:96` (+2 titik lain, total 3 sebutan) | Copy hero "50 video Shorts per hari" dll. | 📄COPY (positioning saat regular rilis) |
| M2 | `(marketing)/showcase/showcase.css:17-21` | Bingkai ponsel `aspect-ratio: 9/16` | 🔀CABANG (galeri bila ada contoh landscape) |
| M3 | `app/layout.tsx:15` | Meta description "video YouTube Shorts otomatis" | 📄COPY |
| M4 | `lib/email/templates.ts:40-41` | Footer email "Mesin produksi konten YouTube Shorts" | 📄COPY |
| M5 | `(marketing)/page.tsx:37` | `CMP_COLS ["AutoShorts",...]` | ✅AMAN (nama kompetitor, bukan format) |

## §7 DATABASE LIVE

### §7a Skema
| # | Objek | Temuan | Tindakan |
|---|---|---|---|
| D1 | `channels` | **TIDAK ADA kolom format/orientasi** | 🗄️DB — kolom baru (mis. `video_format` 'short'/'long', NULL=short) + masuk `_CHANNEL_OVERLAY_FIELDS` |
| D2 | `videos` / `production_runs` / `content_inventory` | Tak menyimpan format (semua implisit shorts) | 🗄️DB — pertimbangkan kolom format utk atribusi/analytics (keputusan desain) |
| D3 | `duration_presets` (8/15/30/45/60/75/90 dtk; 8=ai_video) | Semesta durasi shorts | 🗄️DB — regular butuh kebijakan durasi sendiri (menit) = keputusan produk |
| D4 | `format_profiles` (arc naskah, wps) | Profil naskah shorts | 🗄️DB — arc naskah regular = keputusan produk (bukan sekadar cabang) |

### §7b Katalog `ai_models.default_params` (DB-driven, 7 model ber-ukuran portrait)
| Model | Param terpatri |
|---|---|
| flux-schnell · flux-dev | `image_size {width:1080, height:1920}` |
| gpt-image-1-mini | `size "1024x1536"` |
| kling-2.5-turbo-pro · seedance-1-pro-t2v · seedance-1-lite-t2v · veo-3.1-fast | `aspect_ratio "9:16"` |
→ Tindakan: 🗄️DB — param ukuran harus per-format (kolom/params varian), bukan satu nilai mati per model.

### §7c Kenop ENV terkait QC (platform-wide)
`QC_ASPECT="9:16"` · `QC_ASPECT_TOLERANCE` · `QC_MAX_DURATION` (180, semantik Shorts) · `QC_MIN_DURATION` → per-format-kan (lokasi env vs DB = keputusan desain).

### §7d DNA niche (isi `niches.visual_style`) — 10/47 menulis vertical/9:16/portrait
`ai_tech_frontier, book_wisdom, business_rise_fall, cerita_hikmah, crypto_decoded, culture_shock, geography_explained, history_turning_points, psychology_human_behavior, radiant_affirmations`
→ Tindakan: 🤖PROMPT/🗄️DB — kata orientasi di DNA harus netral-format atau di-overlay saat render (jangan edit 10 DNA manual tiap kali; cari mekanisme).

### §7e Konten CMS (copy user-facing, bukan kode)
`docs_articles`: 1 artikel menyebut Shorts · `blog_posts`: 5 post → 📄COPY saat regular rilis.

## §8 Dokumen internal .md yang membahas shorts/format (file-level, bukan runtime)
`MULTI_FORMAT_STUDIO.md` (SPEC shorts multi-durasi; 0 landscape) · `DESAIN_PRODUK_SAAS.md` §12b · tracker-tracker lain menyebut "Shorts" sebagai konteks. → Saat fitur dibangun: rekonsiliasi §3.7.

## §9 Diperiksa & TIDAK terkait (bukti ketelitian — jangan diaudit ulang)
`blog.css:11` cover 16:9 (gambar blog) · `docs.css:47` `max-width:1080px` (media query layout) · `agent-shell.tsx:53,59` `maxWidth:1080` (lebar halaman) · semua `size_kb/size_mb/1024*1024` (ukuran file) · `chunksize 1024*1024*5` (upload chunk) · `tests/` & `scripts/` nol temuan · `performance_analyzer.py` sebutan "Shorts loop" = komentar M2 (perilaku, bukan format).

## §10 RINGKASAN & POSISI
- **Total titik:** BE 34 · FE-tenant 4 · FE-admin 4 · FE-marketing/email 5 · DB 9 objek/katalog · CMS 6 konten.
- **Kabar baik:** jahitan `content_type` short/long sudah ada (B4/B9/B13) — fitur ini = *mengalirkan nilai dari kolom channel baru melalui jahitan itu* + mem-parameterkan kanvas render (B1) + cabang prompt/QC/metadata + UI dropdown ("Regular — coming soon") + copy.
- **3 keputusan PRODUK yang tak bisa diputuskan kode** (wajib owner): durasi regular (D3) · arc naskah regular (D4) · perlakuan DNA niche orientasi (§7d).
- **STATUS: MENUNGGU KETOK** — langkah berikutnya bila owner setuju: proposal desain teknis rinci (file/tabel/urutan fase + "coming soon" di FE) → ketok → bangun.

## §11 BAHAN KEPUTUSAN OWNER — 3 kartu matang (disusun 2026-07-19 atas perintah "matangkan dan bungkus dulu")

### KARTU 1 — Durasi video Regular (landscape)
**Fakta kode:** seluruh mesin durasi (preset 8–90 dtk · anggaran kata = detik×WPS · beat plan · kalibrasi pace F1–F5 · QC maks 180 dtk) DITALA di semesta shorts. Regular = semesta menit.
| Opsi | Isi | Konsekuensi |
|---|---|---|
| **A (rekomendasi)** | Regular perdana = **1–3 menit** (preset baru mis. 60/120/180 dtk landscape) | Memakai ulang mesin naskah/durasi/kalibrasi yang ada (rentang masih dekat); biaya per video ±2–3× video 60 dtk (TTS+gambar+render linear); tercepat keluar dari "coming soon" |
| B | Langsung long-form 8–15 menit | Mesin naskah/beat/kalibrasi harus didesain ulang (bab/segmen); biaya per video ±8–15×; kerja besar |
| C | Tunda keputusan durasi — fase 1 fitur hanya pipa+dropdown "coming soon" | Nol risiko sekarang; keputusan durasi diketok saat Regular mau diaktifkan |
⚠️ Fakta luar yang BELUM diverifikasi: aturan monetisasi YouTube utk video regular (ambang iklan mid-roll dsb.) — bila jadi dasar pemilihan durasi, wajib verifikasi web dulu.

### KARTU 2 — Alur naskah (arc) video Regular
**Fakta kode:** `format_profiles` (DB) memang rumah arc naskah (kolom: sections, wps, cta_mode, render_mode) — mekanismenya SUDAH DB-driven; `script_engine._get_section_timing` baca per-niche. Arc shorts 8-beat direntang ke 3 menit = pacing rusak (bukan opsi).
| Opsi | Isi | Konsekuensi |
|---|---|---|
| **A (rekomendasi)** | 1 arc regular generik perdana (mis. "explainer": intro-hook → 3–4 segmen isi → payoff+CTA) sebagai BARIS BARU `format_profiles` | Memakai mekanisme katalog yang ada; arc lain menyusul dari data |
| B | Banyak arc sejak hari-1 (dokumenter/listicle/story) | Desain & uji berlipat sebelum ada bukti permintaan |

### KARTU 3 — DNA niche yang menulis orientasi (10/47 niche)
**Fakta kode+keputusan terekam:** [[decisions_niche_owns_content_config]]: NICHE memiliki gaya konten; CHANNEL memiliki format tampilan. Orientasi = turunan FORMAT (milik channel) → kata "vertical/9:16" di DNA niche **melanggar pembagian kepemilikan yang sudah Anda ketok dulu**.
| Opsi | Isi | Konsekuensi |
|---|---|---|
| **A (rekomendasi)** | **Orientasi = milik MESIN**: bersihkan kata orientasi dari 10 DNA (sekali, hati-hati, uji output) + ATURAN baru: DNA wajib netral-orientasi; mesin menyuntik orientasi per-format saat merakit prompt | Satu sumber kebenaran; nol konflik prompt; konsisten dgn keputusan lama. Risiko: edit DNA bisa menggeser gaya visual → wajib uji banding per-niche sebelum ganti |
| B | DNA dibiarkan; mesin menimpa dgn suffix format saat render | Nol edit DNA, tapi prompt bisa memuat DUA instruksi bertentangan ("vertical…" + "landscape 16:9") → hasil gambar tak deterministik |

**Cara ketok:** sebut saja mis. "Kartu 1=A, Kartu 2=A, Kartu 3=A" (atau kombinasi lain/koreksi). Setelah ketok → proposal desain teknis rinci disusun di atas ketiganya.

### Changelog
- 2026-07-19 (2) — §11 kartu keputusan matang ditambahkan (perintah owner "matangkan dan bungkus dulu 3 hal").
- 2026-07-19 — dokumen lahir (audit tuntas 5 permukaan, per-baris, oleh Claude; mandat owner "tidak boleh ada 1 baris terlewat").
