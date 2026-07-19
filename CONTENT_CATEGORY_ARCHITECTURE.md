# 🎬 CONTENT CATEGORY ARCHITECTURE — kategori konten per-channel: Shorts / Regular

> **SSOT fitur "Content Category"** (tenant memilih PER-CHANNEL: **Shorts** — portrait 9:16, aktif hari ini · **Regular** — landscape 16:9, lahir berstatus "coming soon").
> Lahir 2026-07-19 sebagai `AUDIT_HARDCODE_FORMAT_VIDEO.md` (audit per-baris, mandat owner); **diganti nama + dinaikkan jadi dokumen ARSITEKTUR lengkap ber-Plan-vs-Realisasi atas perintah owner 19-Jul** ("check kembali… harusnya CONTENT_CATEGORY_ARCHITECTURE.md… sempurnakan file arsitektur lengkap dengan plan vs realization").
> **Status dokumen: DESAIN — NOL kode produksi diubah.** Eksekusi hanya lewat gerbang §8 (fase ber-ketok). Semua fakta di sini TERVERIFIKASI grep kode + query DB live 2026-07-19 — nol asumsi.

## 📌 CARA PAKAI DOKUMEN INI (WAJIB — untuk sesi Claude berikutnya & owner)
1. **Urutan baca sesi baru:** §0 kamus → §2 ledger keputusan (apa yang SUDAH/BELUM diputus) → §8 posisi fase → baru bagian teknis sesuai fase aktif. **JANGAN mulai dari asumsi/ingatan.**
2. **HARAM keras:** (a) menulis kode fitur ini sebelum F0 diketok owner; (b) mengaudit ulang §4 (sudah tuntas per-baris — cukup grep ulang anchor `file:baris` yang MAU dipakai); (c) menganggap item TERBUKA di §2 sebagai sudah diputus; (d) mengarang keputusan yang tidak tercatat di §2.
3. **Perawatan (aturan hidup dokumen):** SETIAP kemajuan/keputusan/pergeseran = update file ini SAAT ITU JUGA (ledger §2 bila keputusan baru; REALISASI §8 bila fase maju + bukti; changelog). File ini = SATU-SATUNYA sumber kebenaran fitur Content Category — bila isi chat ≠ file ini, yang belum tercatat di sini dianggap BELUM terjadi.
4. **Untuk owner:** cukup baca §1 (ringkasan) + §2 kolom Status (apa yang menunggu jawaban Anda) + §8 (sampai mana). Cara menjawab: sebut nomornya, mis. "L4: entry = starter+trial · L5 setuju · L7=A".

## §0 KAMUS ISTILAH (patri — anti salah-paham antar sesi)
| Istilah | Arti PERSIS |
|---|---|
| **Content Category** | Pilihan per-channel: `Shorts` atau `Regular`. Di KODE memakai jahitan lama `content_type` bernilai `'short'`/`'long'` (istilah UI ≠ istilah kode, JANGAN bikin nilai baru) |
| **Shorts** | Video portrait 9:16, semesta durasi 8–120 dtk (aturan YouTube: >180 dtk bukan Shorts lagi) |
| **Regular** | Video landscape 16:9, semesta durasi 90–720 dtk; lahir berstatus "coming soon" (tampil di dropdown tapi terkunci) |
| **Preset durasi** | Baris tabel `duration_presets` (detik + susunan segmen + slot visual). Durasi 90 & 120 punya DUA baris (satu per kategori) |
| **Segmen / beat** | Bagian naskah (hook, core_facts, …) — menentukan STRUKTUR CERITA, bukan jumlah gambar |
| **Slot visual** | Jatah gambar/klip per segmen (§7c). 1 slot = 1 gambar (text-to-image) ATAU kelak 1 klip (text-to-video) |
| **Tier / paket** | 4 paket di `plan_limits` + `pricing_config`: **trial** (GRATIS 3 hari, otomatis saat daftar) · **starter** Rp149rb · **pro** Rp349rb · **business** Rp699rb /bulan. Paket tenant tersimpan di `tenant_configs.plan_type`; detail penuh = §3b |
| **Ketok** | Persetujuan eksplisit owner. Tanpa ketok = proposal, bukan izin kerja |

---

## §1 RINGKASAN AWAM (untuk owner)

Hari ini seluruh mesin hanya melahirkan **satu jenis video: Shorts portrait**. Fitur ini menambah pilihan per-channel: **Regular (landscape)** dengan durasi panjang (sampai 12 menit), dibatasi paket berlangganan. Audit membuktikan asumsi "portrait" tertanam di **60+ titik** di 5 permukaan — tapi kabar baiknya: jahitan `short`/`long` sudah setengah jadi di kode (tinggal dialiri), dan katalog durasi/arc naskah memang sudah tinggal di DB (tinggal ditambah baris + dimensi kategori). Yang paling menentukan sukses: **mesin durasi-panjang** (naskah ber-babak, suara panjang, musik panjang, jumlah gambar) — bukan sekadar memutar kanvas.

---

## §2 LEDGER KEPUTUSAN — status per keputusan (JANGAN tanya ulang yang sudah tercatat; JANGAN eksekusi yang belum KETOK)

| # | Topik | Status | Isi |
|---|---|---|---|
| L1 | Fitur kategori per-channel: Shorts (aktif) / Regular (coming soon dulu) | **ARAHAN OWNER 19-Jul** | Mandat fitur; dropdown per-channel |
| L2 | 6 preset durasi baru: **120 · 180 · 300 · 480 · 600 · 720 dtk**, semuanya 8 segmen naskah | **ARAHAN OWNER 19-Jul** (chat) | Ditambah di atas 7 preset existing |
| L3 | Rentang semesta: **Shorts 8–120s · Regular 90–720s** (90 & 120 hidup di DUA dunia) | **ARAHAN OWNER 19-Jul** + koreksi teknis diterima | ⚠️ Koreksi tercatat: YouTube Shorts maks **180 dtk** — video portrait >180s diperlakukan video biasa; batas 120s pilihan owner = aman. 720s HANYA di dunia Regular |
| L4 | Gating tier kategori | **✅ KETOK OWNER 19-Jul ("setuju, trial & starter shorts saja")** | **Trial & Starter = Shorts saja · Pro = Shorts + Regular ≤180s · Business = semua.** Arsitektur paket = §3b |
| L5 | Jumlah visual dilepas dari jumlah segmen; tabel slot visual per segmen (§7c) | **✅ KETOK OWNER 19-Jul** | Tabel §7c = default; angka hidup di DB (admin-tunable). Pace 13→20 dtk/gambar; total 9–36 gambar |
| L6 | Text-to-video = fase SUSULAN terpisah (fondasi slot visual dibuat kompatibel sekarang) | **✅ KETOK OWNER 19-Jul** | Fase kategori ini = t2i saja; t2v menyusul dengan hitung ekonomi klip |
| L7 | Arc naskah Regular | **✅ KETOK OWNER 19-Jul = A** (1 arc "explainer" perdana, baris baru `format_profiles`; arc lain menyusul dari data) | **📌 CATATAN OWNER (WAJIB, "catat baik-baik — jangan sampai terlewat"):** pengaturan arc/durasi/segmentasi WAJIB dipahami & disesuaikan 100% di KETIGA lapis — terverifikasi anchor 19-Jul: **(a) DB** `duration_presets`+`format_profiles`+`content_beats` · **(b) BE** `format_catalog.py`/`script_engine` · **(c) FE-ADMIN** menu **Katalog → tab "Durasi"** (`admin/(panel)/catalog/page.tsx:106,117,422` — editor preset PK=seconds + form bobot beat via `/api/admin/beats`) · **(d) FE-TENANT** menu **Channel → Setting → kartu "Durasi & segmentasi konten"** (`(app)/channels/[id]/page.tsx:871-877`, simpan `channels.duration_preset` :299, baca preset aktif :475). Keempatnya masuk lingkup wajib F2 |
| L8 | DNA niche ber-orientasi, 10/47 (eks-KARTU 3) | **✅ KETOK OWNER 19-Jul** | Orientasi = milik MESIN: bersihkan 10 DNA sekali + uji banding per-niche sebelum ganti + aturan baru DNA wajib netral-orientasi; mesin menyuntik orientasi per-kategori saat merakit prompt |
| L9 | Verifikasi web aturan YouTube | **✅ TERVERIFIKASI 19-Jul (multi-sumber)** | (1) **Shorts maks 3 menit** (vertikal/persegi, upload pasca 15-Okt-2024) → semesta Shorts 8–120s AMAN. (2) **Mid-roll butuh video ≥8:00 PAS — ambang KERAS** (7:59 = gagal) → **✅ KETOK OWNER 19-Jul = OPSI A:** preset tetap berlabel 8 menit (480s); mesin membidik sedikit di atas (±8:10) dengan window one-sided — render TIDAK PERNAH di bawah 480.0s (masuk G3). (3) Shorts >60 dtk dengan musik ber-lisensi/Content ID DIBLOKIR — musik kita = pustaka internal, aman, tapi patri aturan: pustaka wajib royalty-free utk Shorts >60s |
| L10 | Kuota harian video Regular | **✅ KETOK OWNER 19-Jul** | **1 video = 1 kuota** (fakta: biaya AI = BYOK tenant; beban platform = render VPS + S3). **Mandat owner menyertai ketok: siapkan improvement antisipasi PENYUMBATAN ANTRIAN render** → arah world-class dicatat di G7 (slot berbobot + fair-share per tenant); diketok & dibangun di F3 berbekal angka uji beban nyata |

### §2b PERTANYAAN F0 — **✅ SEMUA TERJAWAB 19-Jul (F0 TUTUP)**
L4 trial&starter=Shorts · L5 tabel slot visual · L6 t2v belakangan · L7=A (1 arc perdana + CATATAN 4 permukaan wajib) · L8 DNA dibersihkan · L9 terverifikasi + jaminan 8:00 opsi A · L10 1 video=1 kuota (+mandat anti-sumbat G7). Pertanyaan owner berikutnya lahir per-fase di proposal desain masing-masing.

---

## §3 FAKTA ARSITEKTUR KUNCI (terverifikasi kode + DB live 19-Jul — pegangan sebelum menyentuh apa pun)

1. **Jahitan `short`/`long` SUDAH ADA setengah jadi (s92):** `TenantRunConfig.content_type` (`tenant_config.py:152-154`, komentar "long belum diimplementasi") + thumbnail publisher sudah bercabang (`youtube_publisher.py:379-383`). TAPI nilainya **dipatri** di `pipeline.py:106` dan **tak ada kolom DB** yang mengisinya (bukan anggota `_CHANNEL_OVERLAY_FIELDS` :436).
2. **`channels.format_profile` & `duration_presets` = BUKAN orientasi** — profil alur-narasi & durasi khusus shorts (`MULTI_FORMAT_STUDIO.md`: 0 sebutan landscape). Kategori konten = dimensi BARU.
3. **Tidak ada kolom orientasi/kategori** di `channels`/`videos` (verifikasi information_schema 19-Jul).
4. **Gerbang QC pakai ENV, bukan DB:** `QC_ASPECT` (default "9:16"), `QC_MAX_DURATION` (180, "batas platform Shorts").
5. **Durasi per-channel = `channels.duration_preset` (integer DETIK polos)**; FE menulis langsung via RLS (`channels/[id]/page.tsx:280,299`) dan me-map preset via angka detik (`page.tsx:247`). Katalog `duration_presets` ber-kunci `seconds` TUNGGAL → 90/120 dua-dunia **mustahil tanpa dimensi kategori** di kunci.
6. **Rumah gating tier = tabel `plan_limits`** (`plan_type` trial/starter/pro/business; kolom saat ini: `max_videos_per_day` 1/1/3/5 · `max_channels` 1/1/3/10 · `niche_studio` · `full_niche_catalog` · marketing) — **belum ada satu pun kolom durasi/kategori**.
7. **TTS = SATU panggilan utuh tanpa pemotongan** (`tts_engine.generate` → `_run_provider(primary, text, …)` sekali jalan) + closed-loop durasi via atempo. Naskah 720s ≈ 1.500+ kata ≈ 9–10rb karakter → melewati batas per-request vendor → **wajib chunk + stitch + gabung word_timestamps** (belum ada mekanismenya).
8. **Musik TIDAK di-loop:** `_mix_music` (`video_renderer.py:1137-1199`) `atrim=0:{audio_duration}` + fade-out di `audio_duration-2`; track dipilih `select_and_download(audio_duration=…)` dari pustaka yang ditala shorts → narasi 12 menit = musik habis di tengah (senyap).
9. **Kapasitas render:** producer paralel `MAX = max_concurrent_render()` (config-driven ✅); render ffmpeg 12 menit = beban CPU/disk VPS berlipat + file & upload YouTube besar — belum pernah diukur di VPS ini.
10. **`visual_mode` (ai_image/ai_video) SUDAH per-channel** (anggota `_CHANNEL_OVERLAY_FIELDS`) — fondasi pilihan t2i/t2v per-channel sudah ada; yang menempel di preset adalah `duration_presets.render_mode` (8s=ai_video) → rekonsiliasi preset⇄channel dituntaskan di desain ini.

## §3b ARSITEKTUR PAKET & BILLING (deep-dive 19-Jul, perintah owner "deep dive lagi agar tidak ada yang miss" — SEMUA terverifikasi kode + DB live)

### Paket & harga
| plan_type | Harga/bulan (`pricing_config`, admin-editable) | max_videos_per_day | max_channels | full_niche_catalog | niche_studio | custom niche |
|---|---|---|---|---|---|---|
| **trial** | **GRATIS** — otomatis saat daftar, durasi `app_config.trial_duration_days` = **3 hari** | 1 | 1 | ❌ (niche dasar) | ❌ | ❌ |
| **starter** | Rp149.000 (`plan_starter`) | 1 | 1 | ✅ | ❌ | ✅ |
| **pro** | Rp349.000 (`plan_pro`) | 3 | 3 | ✅ | ❌ | ✅ |
| **business** | Rp699.000 (`plan_business`) | 5 | 10 | ✅ | ✅ | ✅ |

- Paket tenant tersimpan di **`tenant_configs.plan_type`** + **`tenant_configs.subscription_status`** (BUKAN tabel subscriptions terpisah). Caps paket = tabel `plan_limits` (config-driven, admin-tunable). Harga = tabel `pricing_config` (IDR + USD cents; kunci `plan_{tier}`; no-hardcode — `midtrans.price_by_key` raise bila tak ada).
- **`trial` = plan_type SEKALIGUS status** — trial adalah baris paket sungguhan di `plan_limits` (bukan sekadar flag), lahir via trigger DB `handle_new_tenant` (migr 0028).

### Mesin status langganan (`src/billing/renewal.py` + `limits.py`)
- **Boleh produksi/publish** hanya status `{active, trial, grace}` (`PRODUCING_STATUSES`). Alur: `trial → trial_expired` (email nurture; tuas perpanjang gratis `nurture_trial_extend_days`=3) · `active → grace → suspended → blocked → deleted`.
- **Comp/internal:** `is_developer=true` ATAU diskon efektif ≥100% = gratis selamanya/selama berlaku, TAPI **caps tetap ikut `plan_type`-nya** — preseden penting: gating kategori nanti juga wajib ikut plan_type, comp bukan pengecualian.
- **Upgrade/downgrade:** pro-rata — sisa hari dikonversi rasio harga (`compute_checkout_amount`); trial tak berharga → kredit 0.

### Titik penegakan paket yang SUDAH ada (pola yang WAJIB diikuti gating kategori)
| Gerbang | Mekanisme | Lokasi |
|---|---|---|
| Produksi & publish | `gate_for_channel` → can_produce + daily_cap per-channel (published hari ini vs cap) | `limits.py:158` dipakai producer+publisher |
| Cap harian | `min(videos_per_day tenant, plan max_videos_per_day)` | `limits.py:68` |
| LAHIR channel | RLS INSERT `channels` vs `max_channels` (migr 0155) — gerbang KERAS di DB | DB |
| JALAN channel (downgrade-safe) | `_channel_in_quota`: hanya N channel TERTUA dilayani; lebih dari kuota → **berhenti dilayani TANPA hapus data; upgrade → hidup lagi otomatis** | `limits.py:104` |
| Katalog niche | RPC `set_channel_niche` + `full_niche_catalog` (migr 0124) | DB |
| Custom niche | RLS INSERT `niche_requests` + `can_request_custom_niche` (migr 0130) | DB |

### Populasi nyata (DB live 19-Jul)
19 tenant: **14 trial** (11 status trial · 3 trial_expired) · **1 starter active** · **1 pro active** · 2 business = keduanya comp developer (`admin_test_internal` + ryan). → Tenant BERBAYAR nyata = 2 (starter+pro); desain gating jangan pernah memakai ryan/comp sebagai patokan perilaku bayar.

### Implikasi langsung ke fitur Content Category
1. Gating kategori/durasi = **kolom baru di `plan_limits`** (rumah caps satu-satunya) + ditegakkan MINIMAL di: dropdown FE (titik input) + guard PATCH channel + `gate_for_channel`/producer (gerbang jalan). Pola RLS/RPC DB-level dipertimbangkan di proposal desain (selaras preseden 0124/0130/0155).
2. **Perilaku downgrade sudah punya preseden dipatri** (`_channel_in_quota`): hak di luar paket → berhenti dilayani, data TIDAK dihapus, upgrade menghidupkan lagi otomatis. Channel Regular pada tenant yang turun paket harus mengikuti prinsip yang sama (bentuk persis = keputusan desain F2, bukan asumsi).
3. Comp account ikut plan_type — tidak ada jalan pintas kategori untuk akun developer.

---

## §4 INVENTARIS HARDCODE PER-BARIS (audit tuntas 19-Jul — JANGAN audit ulang; anchor `file:baris` wajib di-grep ulang sebelum dipakai eksekusi)

### §4.0 Metode (agar auditor lain bisa mengulang)
- **Pola sapu:** `1080|1920|1280|720` · `9:16|16:9|9/16|16/9|aspect(:|_|-)ratio` · `portrait|landscape|vertical|horizontal|vertikal` · `shorts|short-form` (ci) · `image_size|size=|1024x|1792|1536` · filter ffmpeg `scale=|crop=|pad=` · `content_type` (jalur short/long).
- **Cakupan:** seluruh `src/` (semua .py) · `apps/web/src` (.tsx/.ts/.css) · `migrations/` · `scripts/` · `tests/` · `.env` (nama kunci saja) · **DB live** (skema + isi katalog `ai_models`/`duration_presets`/`format_profiles`/`niches`/CMS).
- **Dikecualikan secara sadar:** `node_modules`/`.next`/log/aset gambar · direktori eksperimen untracked (`uji-fal/`) · dokumen .md internal (bukan permukaan runtime — dicatat file-level di §4f).
- Legenda kolom TINDAKAN: **🔀CABANG** logika bercabang per-kategori · **⚙️PARAM** jadikan parameter turunan kategori · **🤖PROMPT** prompt AI ikut kategori · **📄COPY** teks/copy disesuaikan · **🧷JAHITAN** seam sudah ada, tinggal dipakai · **🗄️DB** butuh skema/katalog · **✅AMAN** diperiksa, tak perlu diubah.

### §4a BACKEND (Python)

| # | File:Baris | Kutipan/Isi | Jenis | Tindakan |
|---|---|---|---|---|
| B1 | `src/production/video_renderer.py:61-62` | `OUTPUT_WIDTH=1080` `OUTPUT_HEIGHT=1920` — **jantung render**, dipakai SEMUA scale/crop | Dimensi kanvas | ⚙️PARAM (kanvas dari kategori channel) |
| B2 | `video_renderer.py:526-528, 610-612, 637-639, 691-693, 746, 992` | `scale/crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}` (6 titik, termasuk thumbnail :992) | Filter ffmpeg | ✅AMAN bila B1 di-param (semua merujuk konstanta) |
| B3 | `video_renderer.py:25, 89, 199-200, 332, 377-378` | Posisi caption `margin_v`/`y_start` = % dari `OUTPUT_HEIGHT`; ASS `PlayResX/Y` | Tata letak caption | ✅AMAN bila B1 di-param — TAPI **wajib uji visual landscape** (font 68/58 & words_per_line ditala utk portrait → kemungkinan perlu preset caption per-kategori) |
| B4 | `src/orchestrator/pipeline.py:106` | `resolved_content_type = "short"` — nilai dipatri, tak pernah dari channel | Jahitan mati | 🧷JAHITAN+🔀CABANG (isi dari kolom channel baru) |
| B5 | `pipeline.py:805-814` | QC aspek `os.getenv("QC_ASPECT","9:16")` + parser rasio | Gerbang QC | 🔀CABANG (target aspek per-kategori; kenop per-kategori) |
| B6 | `pipeline.py:741, 759, 785` | `QC_MAX_DURATION` 180 "batas platform Shorts"; pesan "bukan Shorts" | Gerbang QC + pesan | 🔀CABANG+📄COPY |
| B7 | `pipeline.py:434-435` | Rekomendasi error "Rasio video tidak 9:16" | Pesan tenant | 📄COPY (ikut kategori) |
| B8 | `pipeline.py:520` | Log "Uploading to YouTube Shorts..." | Log | 📄COPY |
| B9 | `src/config/tenant_config.py:152-154` | `content_type: str = "short"` (+komentar long belum ada) | Jahitan config | 🧷JAHITAN (+ masukkan ke `_CHANNEL_OVERLAY_FIELDS` :436 bila jadi kolom channels) |
| B10 | `src/distribution/youtube_publisher.py:157` | Hashtag universal `["#Shorts"]` | Metadata publish | 🔀CABANG (regular tanpa #Shorts) |
| B11 | `youtube_publisher.py:215` | Tags `["shorts","youtubeshorts","viral"]` | Metadata publish | 🔀CABANG |
| B12 | `youtube_publisher.py:333` | URL hasil `youtube.com/shorts/{id}` | URL | 🔀CABANG (regular = `watch?v=`) — ⚠️ konsumen URL: `producer.py:28-31` regex SUDAH mendukung keduanya ✅ |
| B13 | `youtube_publisher.py:363-402` | Thumbnail: `long→1280×720`, `short→1080×1920` | Jahitan siap | 🧷JAHITAN (sudah 2-cabang, tinggal dialiri) |
| B14 | `youtube_publisher.py:63, 267, 489` | Docstring/CLI "YouTube Shorts" | Teks dev | 📄COPY (minor) |
| B15 | `src/providers/visual/ai_image.py:573` | ffmpeg `S="s=1080x1920,setsar=1"` (jalur pad gambar persegi) | Dimensi | ⚙️PARAM |
| B16 | `ai_image.py:487` | Gemini `imageConfig.aspectRatio: "9:16"` | Param API | 🔀CABANG per-kategori |
| B17 | `ai_image.py:294` | Suffix prompt "vertical 9:16, photorealistic" | Prompt AI | 🤖PROMPT |
| B18 | `ai_image.py:210` | Klip hasil: `width=1080, height=1920` (metadata klip) | Dimensi | ⚙️PARAM |
| B19 | `ai_image.py:617` | Ken Burns "→ video 9:16" | Dimensi efek | ⚙️PARAM |
| B20 | `ai_image.py:71, 442` | Default size `"1024x1536"` (gpt-image, potret 2:3) — sumber = `ai_models.default_params` DB | Param DB-driven | 🗄️DB (lihat §4e — katalog per-kategori) |
| B21 | `src/providers/visual/ai_video.py:33, 124` | "1 klip 9:16"; `width=1080, height=1920` | Dimensi | ⚙️PARAM + 🗄️DB (aspect_ratio di katalog) |
| B22 | `src/production/visual_assembler.py:322` | Prompt hero/thumbnail "Cinematic vertical 9:16 hero image" | Prompt AI | 🤖PROMPT |
| B23 | `visual_assembler.py:362-363` | `width=1080, height=1920` (metadata klip) | Dimensi | ⚙️PARAM |
| B24 | `src/intelligence/script_engine.py:797, 836, 921` | Prompt gambar "vertical 9:16 / Vertical 9:16" (3 titik) | Prompt AI | 🤖PROMPT |
| B25 | `script_engine.py:820, 908` | "short-form vertical video / vertical clip" | Prompt AI | 🤖PROMPT |
| B26 | `script_engine.py:646` | Contoh hashtag `"#shorts"` di skema output naskah | Prompt AI | 🔀CABANG |
| B27 | `src/intelligence/niche_selector.py:428` | Prompt "PLATFORM: YouTube Shorts, TikTok, Instagram Reels" | Prompt AI | 🤖PROMPT |
| B28 | `src/intelligence/channel_analyst.py:297` | Prompt analis "automated YouTube Shorts machine" | Prompt AI | 🤖PROMPT (ikut kategori channel) |
| B29 | `src/intelligence/trend_radar.py:249` | Query pencarian default `"shorts"` | Sinyal tren | 🔀CABANG (regular: query beda? = keputusan desain) |
| B30 | `src/config/model_tester.py:117` | Prompt uji "vertical 9:16" | Alat uji admin | 🤖PROMPT |
| B31 | `src/utils/telegram_notifier.py:142` | Klasifikasi pesan QC "aspect/rasio/9:16" | Pesan | 📄COPY |
| B32 | `src/utils/email.py:306, 313` | Copy email nurture menyebut konteks video otomatis/Shorts | Copy email | 📄COPY |
| B33 | `migrations/0016_branding_config.sql:8` | `logo_max_w_px 220` ("≈20% dari 1080") | Batas logo | ⚙️PARAM (relatif thd lebar kanvas) |
| B34 | `.env` kunci `QC_ASPECT`, `QC_ASPECT_TOLERANCE`, `QC_MAX_DURATION`, `QC_MIN_DURATION` | Nilai QC platform-wide di env | Config lokasi | 🗄️DB/🔀 (per-kategori; pindah/turunkan — keputusan desain) |

### §4b FE-TENANT

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| T1 | `apps/web/src/app/(app)/channels/[id]/page.tsx:952-963` | Pratinjau caption `aspectRatio: "9/16"` | 🔀CABANG (pratinjau ikut kategori channel) |
| T2 | `(app)/runs/[id]/run-detail.css:72` | `.thumb { aspect-ratio: 9/16 }` | 🔀CABANG (thumbnail runs) |
| T3 | `components/test-niche-panel.tsx:118` | Pemutar video hasil Test (style mengikuti video) | ✅AMAN (player HTML menyesuaikan) — verifikasi visual saat landscape |
| T4 | `channels/[id]` — **dropdown kategori BELUM ADA** | Titik lahir UI fitur: pilihan "Shorts / Regular (coming soon)" | 🔀CABANG (elemen UI baru = wajib ketok §2.3d) |

### §4c FE-ADMIN

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| A1 | `admin/(panel)/content/page.tsx:50-54` | Hint upload showcase "MP4 9:16 / PNG 9:16" | 📄COPY (bila showcase kelak menampung landscape) |
| A2 | `api/admin/showcase/upload/route.ts:8` | Komentar "MP4 ... 9:16" | 📄COPY |
| A3 | `admin/(panel)/niches/page.tsx:236` | Teks bantuan menyebut shorts | 📄COPY |
| A4 | `admin/(panel)/content/page.tsx:19-20` | Cover blog "16:9 1376×768" | ✅AMAN (blog memang landscape — bukan video produk) |

### §4d FE-MARKETING + EMAIL

| # | File:Baris | Isi | Tindakan |
|---|---|---|---|
| M1 | `(marketing)/page.tsx:96` (+2 titik lain, total 3 sebutan) | Copy hero "50 video Shorts per hari" dll. | 📄COPY (positioning saat regular rilis) |
| M2 | `(marketing)/showcase/showcase.css:17-21` | Bingkai ponsel `aspect-ratio: 9/16` | 🔀CABANG (galeri bila ada contoh landscape) |
| M3 | `app/layout.tsx:15` | Meta description "video YouTube Shorts otomatis" | 📄COPY |
| M4 | `lib/email/templates.ts:40-41` | Footer email "Mesin produksi konten YouTube Shorts" | 📄COPY |
| M5 | `(marketing)/page.tsx:37` | `CMP_COLS ["AutoShorts",...]` | ✅AMAN (nama kompetitor, bukan format) |

### §4e DATABASE LIVE

**Skema:**
| # | Objek | Temuan | Tindakan |
|---|---|---|---|
| D1 | `channels` | **TIDAK ADA kolom kategori/orientasi** | 🗄️DB — kolom baru (usulan §7b) + masuk `_CHANNEL_OVERLAY_FIELDS` |
| D2 | `videos` / `production_runs` / `content_inventory` | Tak menyimpan kategori (semua implisit shorts) | 🗄️DB — kolom kategori utk atribusi/analytics (keputusan desain) |
| D3 | `duration_presets` (8/15/30/45/60/75/90 dtk; 8=ai_video; kunci `seconds` TUNGGAL) | Semesta durasi shorts | 🗄️DB — +dimensi kategori di kunci (90/120 dua-dunia, L3) + 6 baris baru (L2) |
| D4 | `format_profiles` (arc naskah, wps) | Profil naskah shorts (4 arc) | 🗄️DB — arc Regular = L7 (terbuka) |
| D5 | `plan_limits` (trial/starter/pro/business) | **Nol kolom durasi/kategori** | 🗄️DB — kolom gating baru (usulan §7d) + kartu admin |

**Katalog `ai_models.default_params` (DB-driven, 7 model ber-ukuran portrait):**
| Model | Param terpatri |
|---|---|
| flux-schnell · flux-dev | `image_size {width:1080, height:1920}` |
| gpt-image-1-mini | `size "1024x1536"` |
| kling-2.5-turbo-pro · seedance-1-pro-t2v · seedance-1-lite-t2v · veo-3.1-fast | `aspect_ratio "9:16"` |
→ 🗄️DB — param ukuran harus per-kategori (params varian), bukan satu nilai mati per model.

**Kenop ENV QC (platform-wide):** `QC_ASPECT="9:16"` · `QC_ASPECT_TOLERANCE` · `QC_MAX_DURATION` (180, semantik Shorts) · `QC_MIN_DURATION` → per-kategori-kan (lokasi env vs DB = keputusan desain, G15).

**DNA niche (`niches.visual_style`) — 10/47 menulis vertical/9:16/portrait:** `ai_tech_frontier, book_wisdom, business_rise_fall, cerita_hikmah, crypto_decoded, culture_shock, geography_explained, history_turning_points, psychology_human_behavior, radiant_affirmations` → L8 (terbuka).

**Konten CMS:** `docs_articles` 1 artikel menyebut Shorts · `blog_posts` 5 post → 📄COPY saat Regular rilis.

### §4f Dokumen internal .md yang membahas shorts/format (file-level, bukan runtime)
`MULTI_FORMAT_STUDIO.md` (SPEC shorts multi-durasi; 0 landscape) · `DESAIN_PRODUK_SAAS.md` §12b · tracker lain menyebut "Shorts" sebagai konteks. → Saat fitur dibangun: rekonsiliasi §3.7 CLAUDE.md.

### §4g Diperiksa & TIDAK terkait (bukti ketelitian — jangan diaudit ulang)
`blog.css:11` cover 16:9 (gambar blog) · `docs.css:47` `max-width:1080px` (media query layout) · `agent-shell.tsx:53,59` `maxWidth:1080` (lebar halaman) · semua `size_kb/size_mb/1024*1024` (ukuran file) · `chunksize 1024*1024*5` (upload chunk) · `tests/` & `scripts/` nol temuan · `performance_analyzer.py` sebutan "Shorts loop" = komentar M2 (perilaku, bukan format).

---

## §5 PRESET DURASI EXISTING (potret DB live 19-Jul — baseline yang TIDAK boleh regresi)

| Durasi | Segmen (beats) | Visual | Render | Default |
|---|---|---|---|---|
| 8s | core_facts | 1 | ai_video (silence_override 1.0) | — |
| 15s | hook → core_facts | 2 | image_seq | — |
| 30s | hook → core_facts → cta | 3 | image_seq | — |
| 45s | hook → core_facts → climax → cta | 4 | image_seq | ✅ |
| 60s | hook → build_up → core_facts → climax → cta | 5 | image_seq | — |
| 75s | + mystery_drop | 6 | image_seq | — |
| 90s | + curiosity_bridge (7 beat) | 7 | image_seq | — |

Pola: segmen bertambah bertingkat; pace visual 7,5→12,9 dtk/gambar. `format_profiles` existing: viral_mystery (8 beat) · educational_softsell (5) · listicle_facts (5) · motivational_quote (1, ai_video).

---

## §6 CELAH YANG BELUM DIBUNGKUS (hasil sisir-ulang 19-Jul, perintah owner "apa lagi yang belum dibahas") — tiap item = aspek yang WAJIB masuk proposal desain rinci

| # | Celah | Fakta terverifikasi | Aspek yang harus diputuskan/didesain |
|---|---|---|---|
| G1 | **Rumah gating tier** | `plan_limits` nol kolom durasi/kategori; pola penegakan existing + preseden downgrade `_channel_in_quota` = §3b | Kolom baru per-plan (usulan §7d) + kartu admin dwibahasa (§3.3 CLAUDE.md) + filter dropdown FE DI TITIK INPUT + guard PATCH + gerbang jalan `gate_for_channel` (anti-bypass) + perilaku downgrade mengikuti prinsip §3b.2 (berhenti dilayani, data utuh, upgrade hidup lagi) |
| G2 | **Kunci ganda katalog durasi** | `duration_presets` kunci `seconds` tunggal; `channels.duration_preset` int detik; FE map by-seconds (§3.5) | Skema kunci (kategori, seconds) · bentuk kolom channel (tetap int + kategori terpisah, atau FK komposit) · migrasi mulus channel existing · FE presetModes |
| G3 | **Naskah durasi panjang** | Anggaran kata = detik×WPS; 720s ≈ 1.500+ kata > 1 panggilan LLM sehat; kalibrasi pace F1–F5 ditala 8–90s | Generasi ber-babak (per-segmen/bab) · kalibrasi pace khusus long · **presisi durasi tetap terbukti (gerbang terkunci §7.3 CLAUDE.md — durasi = HULU pipeline)** · window atempo di semesta menit · **preset 480s: window WAJIB one-sided ≥480.0s (ambang keras mid-roll, L9)** |
| G4 | **TTS panjang** | 1 panggilan tunggal, nol chunking (§3.7) | Pemotongan per-segmen + penyambungan audio + **penggabungan word_timestamps lintas-chunk** (caption & beat_durations bergantung padanya) + closed-loop atempo per-chunk vs global |
| G5 | **Musik durasi panjang** | Musik di-atrim ke audio_duration, TIDAK loop; pustaka ditala shorts (§3.8) | Loop/stitch musik (crossfade) atau kurasi track panjang; mood konsisten 12 menit |
| G6 | **Slot visual & distribusi per-segmen** | `visual_beats` = jumlah segmen (1:1) hari ini; L5 KETOK memisahkannya. **Temuan 19-Jul: mekanisme bobot per-segmen SUDAH ADA — `content_beats.weight/weight_locked` + form admin di tab Durasi (`/api/admin/beats`)** | Rumah DB slot visual menumpang/meniru pola `content_beats` (jangan bikin mekanisme kembar!) · admin bisa tala tanpa kode · kompatibel t2v (1 slot = 1 gambar ATAU 1 klip) |
| G7 | **Kapasitas render & anti-penyumbatan antrian** (mandat owner 19-Jul menyertai ketok L10) | `max_concurrent_render()` config ✅; render/upload 12-menit belum pernah diukur di VPS (§3.9); pool = ThreadPoolExecutor tunggal (semua job berbobot sama) | Uji beban render 720s (CPU/RAM/disk/waktu) DULU → lalu desain anti-sumbat world-class berbasis angka nyata: **(a) slot berbobot** — job long menempati >1 slot pool sesuai biaya render terukur (bukan 1 job = 1 slot buta); **(b) fair-share per tenant** — giliran round-robin antar tenant supaya 1 tenant ber-video-panjang tak memblok tenant lain; **(c) cap konkurensi long terpisah** (kenop DB) supaya jalur Shorts selalu lancar; **(d) telemetri durasi render per preset + alarm ambang antrian** (deteksi sumbat SEBELUM tenant merasakan). Bentuk final = proposal F3 ber-angka, bukan asumsi |
| G8 | **Kuota & ekonomi** | `max_videos_per_day` menghitung semua video sama (L10) | KEPUTUSAN OWNER: kuota/harga sadar-kategori; proyeksi biaya per preset (±linear: 720s ≈ 7–8× video 60s) |
| G9 | **Kecerdasan sadar-kategori** | Analyst prompt "Shorts machine" (B28); warisan W1 & `niche_weights` lahir dari data shorts; benchmark retensi shorts ≠ long (semesta beda) | Kategori masuk dosir analis · warisan TIDAK menyeberang kategori tanpa label · benchmark/kurva retensi dipisah per-kategori (data per-channel sudah terpisah by-design karena kategori per-channel) |
| G10 | **Trend radar** | Query default `"shorts"` (B29) | Sinyal tren utk konten Regular = keputusan desain (query per-kategori?) |
| G11 | **Thumbnail Regular** | Publisher 2-cabang siap (B13); hero prompt masih vertical (B22) | Thumbnail landscape = penentu CTR long-form → prompt hero per-kategori; **peluang: YouTube chapters otomatis dari beat_durations** (nilai tambah long, belum pernah dibahas) |
| G12 | **Migrasi & nol regresi** | Channel existing (RAD dkk.) semua implisit shorts | Default kolom = shorts (nol perubahan perilaku); bukti regresi 5 permukaan (§3.8 CLAUDE.md); "coming soon" = Regular tampil tapi terkunci |
| G13 | **Penamaan & istilah** | Produk: "Content Category: Shorts/Regular" ↔ kode: `content_type` 'short'/'long' (jahitan s92) | Patri kamus istilah SEKALI (UI pakai label Bi dwibahasa; kode tetap 'short'/'long' agar jahitan existing terpakai — usulan) |
| G14 | **Caption landscape** | Font 68/58 & words_per_line ditala portrait (B3) | Preset caption per-kategori + uji visual nyata landscape |
| G15 | **Rumah QC per-kategori** | QC di ENV platform-wide (B34) | Pindah ke DB per-kategori (selaras §3.3 config-driven) vs ENV per-kategori — keputusan desain |
| G16 | **Marketing & positioning** | Copy hero/meta/email semua "Shorts" (M1/M3/M4) | Copy saat Regular rilis + fitur pembeda tier di pricing (ikut G1/G8) |

---

## §7 ARSITEKTUR TARGET (PROPOSAL — menunggu ketok owner; nilai rinci final di proposal desain teknis per-fase)

### §7a Prinsip
1. **Kategori = milik CHANNEL** (selaras [[decisions_niche_owns_content_config]]: niche = gaya konten, channel = format tampilan). Nilai mengalir lewat jahitan s92 yang SUDAH ada: kolom channel → `_CHANNEL_OVERLAY_FIELDS` → `TenantRunConfig.content_type` → seluruh cabang (render/QC/prompt/publish).
2. **Config-driven total (§3.3 CLAUDE.md):** dimensi/durasi/slot visual/gating tier = baris DB + kartu admin dwibahasa; nol literal baru di kode.
3. **Gagal jujur:** kombinasi tak valid (preset di luar tier, model tanpa varian landscape) DITOLAK di titik input, bukan fallback senyap.
4. **Nol regresi shorts:** default semua channel existing = shorts; jalur shorts tidak berubah perilaku satu bit pun tanpa bukti uji.

### §7b Skema DB usulan (garis besar)
- `channels.content_category` TEXT 'short'|'long' NOT NULL DEFAULT 'short' → anggota baru `_CHANNEL_OVERLAY_FIELDS`; mengisi `TenantRunConfig.content_type` (mengganti patri `pipeline.py:106`).
- `duration_presets`: +kolom `content_category`, kunci unik (content_category, seconds); 7 baris existing = 'short'; +6 baris 'long' (L2) + baris 'long' 90/120 bila diketok; +kolom slot visual (G6).
- `videos` / `production_runs`: +`content_category` (atribusi & analytics, G9).
- `ai_models.default_params`: varian ukuran per-kategori (bentuk final di proposal desain — params_landscape vs struktur bersarang).
- QC: kenop per-kategori (rumah final = keputusan G15).

### §7c Slot visual per segmen (PROPOSAL L5 — angka hidup di DB, admin bisa tala)
Prinsip: pace melambat bertahap 13→20 dtk/gambar · hook terpadat · core_facts porsi terbesar.

| Segmen | 120s | 180s | 300s | 480s | 600s | 720s |
|---|---|---|---|---|---|---|
| hook | 1 | 1 | 2 | 2 | 3 | 3 |
| mystery_drop | 1 | 1 | 2 | 2 | 3 | 3 |
| build_up | 1 | 2 | 3 | 4 | 4 | 5 |
| pattern_interrupt | 1 | 1 | 1 | 2 | 2 | 2 |
| core_facts | 2 | 3 | 5 | 9 | 9 | 12 |
| curiosity_bridge | 1 | 1 | 2 | 3 | 3 | 4 |
| climax | 1 | 2 | 2 | 3 | 4 | 5 |
| cta | 1 | 1 | 1 | 2 | 2 | 2 |
| **TOTAL** | **9** | **12** | **18** | **27** | **30** | **36** |
| dtk/gambar | 13,3 | 15 | 16,7 | 17,8 | 20 | 20 |
| ±biaya visual vs 60s | 1,8× | 2,4× | 3,6× | 5,4× | 6× | 7,2× |

Catatan: nama segmen final mengikuti keputusan arc L7; tabel = pola distribusi, bukan patri nama.

### §7d Gating tier usulan (menunggu L4 dikonfirmasi)
`plan_limits` +kolom (bentuk final di proposal): kategori yang diizinkan + durasi maks per-kategori. Isi usulan (selaras §3b): **trial & starter → Shorts saja · pro → Shorts + Regular ≤180s · business → semua.** Ditegakkan BERLAPIS mengikuti pola penegakan existing (§3b): dropdown FE terfilter di titik input (anti-human-error §3.1) + guard PATCH channel + gerbang jalan `gate_for_channel`/producer (anti-bypass; comp ikut plan_type) + perilaku downgrade prinsip §3b.2.

### §7e PROPOSAL DESAIN TEKNIS F1 — Fondasi kategori (disusun 19-Jul pasca F0 tutup; **MENUNGGU KETOK — nol kode sebelum itu**)
**Janji F1: NOL perubahan perilaku** — semua channel jadi 'short' eksplisit; mesin jalan persis seperti kemarin; yang baru hanya fondasi + dropdown terkunci.

| Lapis | Perubahan PERSIS | File/objek |
|---|---|---|
| DB (1 migrasi) | `channels.content_category` TEXT NOT NULL DEFAULT 'short' CHECK IN ('short','long') · kolom sama di `videos` + `production_runs` (atribusi; baris lama otomatis 'short' — benar secara sejarah) | `migrations/017x_content_category.sql` |
| BE | (1) `content_category` masuk `_CHANNEL_OVERLAY_FIELDS` → mengisi `TenantRunConfig.content_type` (jahitan B9 hidup) · (2) `pipeline.py:106` baca dari config channel, patri "short" DIBUANG (B4) · (3) stamp kategori ke `production_runs`/`videos` saat run/video lahir (titik persis diverifikasi grep saat build) | `src/config/tenant_config.py` · `src/orchestrator/pipeline.py` (+titik stamp) |
| FE-tenant | Kartu/dropdown BARU "Kategori Konten" di Channel→Setting (dekat kartu Durasi :871): **Shorts (aktif)** / **Regular — coming soon (terkunci + badge)**, dwibahasa `Bi`, auto-save pola kolom-bersih (spt duration_preset :299) | `(app)/channels/[id]/page.tsx` |
| FE-admin | TIDAK tersentuh (bukan kenop `app_config` — kolom data channel; §3.3 kenop-lengkap tidak terpicu). Katalog Durasi disentuh di F2 | — |
| FE-marketing/email | TIDAK tersentuh (copy berubah di F4) | — |
| Uji/bukti | Uji unit permanen (overlay field + default + stamp) · tsc+build · **regresi runtime: run produksi nyata tetap 'short' identik + kolom terisi** · klik→layar dropdown (Regular terbukti terkunci) · nol regresi 5 permukaan | `tests/test_content_category_f1.py` (baru) |

Di luar lingkup F1 (tegas): duration_presets/gating/plan_limits (F2) · kanvas/QC/prompt/mesin long (F3) · publish metadata (F4). Deploy F1 = gerbang izin owner terpisah (§5.0 CLAUDE.md).

### §7f Text-to-video (fase susulan — L6)
Fondasi yang dibuat sekarang agar t2v tinggal menyala: konsep slot visual (§7c) netral-sumber · `visual_mode` per-channel sudah ada · rekonsiliasi `duration_presets.render_mode` ⇄ pilihan channel dituntaskan di desain F2. Ekonomi klip (720s = puluhan klip) dihitung saat fasenya tiba.

---

## §8 PLAN vs REALISASI (fase ber-gerbang — TIAP fase butuh ketok owner sebelum kode; kolom REALISASI diisi HANYA dengan bukti)

| Fase | Isi | Gerbang masuk | REALISASI |
|---|---|---|---|
| **F-1 Audit + arsitektur** | Audit hardcode 5 permukaan per-baris · kartu keputusan · sisir-ulang celah G1–G16 · dokumen arsitektur ini | mandat owner 19-Jul | ✅ 19-Jul: audit tuntas (§4) · ledger keputusan (§2) · celah terbungkus (§6) · file di-rename & disempurnakan |
| **F0 Keputusan & verifikasi** | Owner ketok L4–L10 + verifikasi web L9 | — | ✅ **TUTUP 19-Jul**: L4/L5/L6/L7=A/L8/L9=A/L10 semua diketok (ledger §2) + web terverifikasi + catatan owner L7 (4 permukaan) & L10 (anti-sumbat G7) terekam |
| **F1 Fondasi kategori (nol perubahan perilaku)** | Kolom `channels.content_category` + aliran ke seam s92 (B4/B9) + `videos`/`production_runs` atribusi + dropdown channel "Shorts / Regular (coming soon)" terkunci | F0 ✅ · **proposal rinci = §7e, menunggu ketok** | ⏳ |
| **F2 Katalog & gating** | `duration_presets` ber-dimensi kategori + 6 preset baru + slot visual (G6) + `plan_limits` gating (G1) + filter FE + guard BE + rekonsiliasi render_mode | F1 terbukti nol regresi | ⏳ |
| **F3 Mesin long** | Naskah ber-babak + kalibrasi (G3) · TTS chunk (G4) · musik loop (G5) · kanvas/prompt/QC per-kategori (B1–B34 kelompok ⚙️/🤖/🔀) · caption landscape (G14) · uji beban render (G7) · **bukti presisi durasi (gerbang §7.3)** | F2 live | ⏳ |
| **F4 Publish & rilis Regular** | Metadata publish bercabang (B10–B13) + thumbnail landscape/chapters (G11) + copy marketing/email/CMS (G16) + buka kunci "coming soon" | F3 terbukti end-to-end | ⏳ |
| **F5 Kecerdasan sadar-kategori** | Dosir analis + warisan + benchmark per-kategori (G9) + trend radar (G10) | F4 live + data long masuk | ⏳ |

Aturan pengisian REALISASI: bukti runtime nyata (uji + angka), bukan "build lulus"; tiap fase tutup administrasi §3.7 (file ini + MEMORY.md + SISA_KERJA).

---

## Changelog
- 2026-07-19 (8) — **F0 TUTUP PENUH: KETOK L7=A** (+catatan owner "catat baik-baik": 4 permukaan durasi/segmentasi wajib disesuaikan — anchor admin Katalog→Durasi & tenant Channel→Durasi & segmentasi konten TERVERIFIKASI) **+ L9=A** (label 8 menit, mesin jamin ≥480.0s). Temuan baru: `content_beats.weight` + form admin = rumah alami distribusi slot visual (G6 di-update, anti mekanisme-kembar). NEXT: proposal desain teknis F1.
- 2026-07-19 (7) — **KETOK L5 · L6 · L8 · L10** (owner). L10 menyertakan mandat antisipasi penyumbatan antrian → G7 diperluas (slot berbobot · fair-share per tenant · cap long terpisah · telemetri+alarm; final di F3 ber-angka uji beban). Sisa terbuka: L7 (arc) + L9-lanjutan (jaminan 8:00) — menunggu jawaban owner pasca penjelasan sederhana.
- 2026-07-19 (6) — **L4 KETOK** (trial & starter = Shorts saja · pro ≤180s · business semua) + **L9 TERVERIFIKASI web** (Shorts maks 3 mnt ✅ · mid-roll ambang KERAS ≥8:00 → G3 window one-sided utk 480s · musik Shorts >60s wajib royalty-free) + L10 dimatangkan (fakta BYOK: biaya AI = tanggungan kunci tenant) + §2b disegarkan.
- 2026-07-19 (5) — **§3b ARSITEKTUR PAKET & BILLING** ditambahkan (teguran owner "belum paham 100% arsitektur business — deep dive lagi"): 4 paket + harga `pricing_config` + mesin status `renewal.py` + 6 titik penegakan existing + preseden downgrade `_channel_in_quota` + populasi tenant nyata; L4/G1/§7d/§2b/§0 disinkronkan (usulan pemetaan: trial&starter=Shorts · pro=+Regular≤180s · business=semua).
- 2026-07-19 (4) — Penguatan SSOT (perintah owner "lengkap, jelas, tanpa ambigu, mudah dipahami, dirawat"): blok CARA PAKAI wajib + §0 kamus istilah + §2b daftar pertanyaan bahasa awam + aturan perawatan dokumen.
- 2026-07-19 (3) — **Rename → `CONTENT_CATEGORY_ARCHITECTURE.md`** + naik jadi dokumen arsitektur: ledger keputusan §2 · fakta baru terverifikasi (plan_limits/TTS/musik/kunci preset) §3 · celah G1–G16 §6 · arsitektur target §7 · Plan-vs-Realisasi §8 (perintah owner).
- 2026-07-19 (2) — §11 kartu keputusan matang ditambahkan (perintah owner "matangkan dan bungkus dulu 3 hal") — kini dilebur ke ledger §2 (L7/L8) + arahan durasi owner menggantikan opsi Kartu 1.
- 2026-07-19 — dokumen lahir sebagai `AUDIT_HARDCODE_FORMAT_VIDEO.md` (audit tuntas 5 permukaan, per-baris; mandat owner "tidak boleh ada 1 baris terlewat").
