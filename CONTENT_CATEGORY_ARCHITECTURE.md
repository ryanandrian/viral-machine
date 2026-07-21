# 🎬 CONTENT CATEGORY ARCHITECTURE — kategori konten per-channel: Shorts / Regular

> **SSOT fitur "Content Category"** (tenant memilih PER-CHANNEL: **Shorts** — portrait 9:16, aktif hari ini · **Regular** — landscape 16:9, lahir berstatus "coming soon").
> Lahir 2026-07-19 sebagai `AUDIT_HARDCODE_FORMAT_VIDEO.md` (audit per-baris, mandat owner); **diganti nama + dinaikkan jadi dokumen ARSITEKTUR lengkap ber-Plan-vs-Realisasi atas perintah owner 19-Jul** ("check kembali… harusnya CONTENT_CATEGORY_ARCHITECTURE.md… sempurnakan file arsitektur lengkap dengan plan vs realization").
> **Status dokumen: DESAIN — NOL kode produksi diubah.** Eksekusi hanya lewat gerbang §8 (fase ber-ketok). Semua fakta di sini TERVERIFIKASI grep kode + query DB live 2026-07-19 — nol asumsi.

## 📌 CARA PAKAI DOKUMEN INI (WAJIB — untuk sesi Claude berikutnya & owner)
1. **Urutan baca sesi baru:** §0 kamus → §2 ledger keputusan (apa yang SUDAH/BELUM diputus) → §8 posisi fase → baru bagian teknis sesuai fase aktif. **JANGAN mulai dari asumsi/ingatan.**
2. **HARAM keras:** (a) menulis kode fase mana pun sebelum GERBANG fase itu diketok owner (§8 kolom Gerbang); (b) mengaudit ulang §4 (sudah tuntas per-baris — cukup grep ulang anchor `file:baris` yang MAU dipakai); (c) menganggap item TERBUKA di §2 sebagai sudah diputus; (d) mengarang keputusan yang tidak tercatat di §2.
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
| D3 | `duration_presets` (8/15/30/45/60/75/90 dtk; 8=ai_video; kunci `seconds` TUNGGAL) | Semesta durasi shorts | 🗄️DB — +dimensi kategori di kunci + 8 baris baru → desain final §7g.1 |
| D4 | `format_profiles` (arc naskah, wps) | Profil naskah shorts (4 arc) | 🗄️DB — arc `explainer` (L7=A KETOK) → desain final §7g.2 |
| D5 | `plan_limits` (trial/starter/pro/business) | **Nol kolom durasi/kategori** | 🗄️DB — kolom gating baru (usulan §7d) + kartu admin |

**Katalog `ai_models.default_params` (DB-driven, 7 model ber-ukuran portrait):**
| Model | Param terpatri |
|---|---|
| flux-schnell · flux-dev | `image_size {width:1080, height:1920}` |
| gpt-image-1-mini | `size "1024x1536"` |
| kling-2.5-turbo-pro · seedance-1-pro-t2v · seedance-1-lite-t2v · veo-3.1-fast | `aspect_ratio "9:16"` |
→ 🗄️DB — param ukuran harus per-kategori (params varian), bukan satu nilai mati per model.

**Kenop ENV QC (platform-wide):** `QC_ASPECT="9:16"` · `QC_ASPECT_TOLERANCE` · `QC_MAX_DURATION` (180, semantik Shorts) · `QC_MIN_DURATION` → per-kategori-kan (lokasi env vs DB = keputusan desain, G15).

**DNA niche (`niches.visual_style`) — 10/47 menulis vertical/9:16/portrait:** `ai_tech_frontier, book_wisdom, business_rise_fall, cerita_hikmah, crypto_decoded, culture_shock, geography_explained, history_turning_points, psychology_human_behavior, radiant_affirmations` → L8=A KETOK; prosedur bersih = §7h.5.

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

## §6 REGISTER CELAH G1–G16 (hasil sisir-ulang 19-Jul) — **STATUS: SEMUA sudah punya rumah desain (peta = §7k); tabel ini = konteks fakta per-celah, bukan daftar terbuka**

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
5. **🎨 SATU NUANSA UI (mandat owner 2026-07-20, berlaku SEMUA fase F1–F5):** setiap layar/elemen fitur ini WAJIB memakai **pustaka UI & pola halaman yang SUDAH ADA** di `apps/web` — komponen, tema, tipografi, pola form/tabel/badge/pill/dialog yang sama dengan panel tenant & admin (acuan konkret: kartu "Durasi & segmentasi konten" tenant, pill pemilih penyedia/model, dialog ✎ katalog admin ber-pratinjau, komponen `Bi` dwibahasa). **DILARANG membangun gaya, komponen dasar, atau library baru.** Ukuran lulus: tenant/admin yang membuka layar baru merasa di aplikasi yang sama. (Cermin mandat 17-Jul di SPEC partner §3.9 — kini mengikat fitur ini secara eksplisit.)

### §7b Skema DB usulan (garis besar HISTORIS — bentuk FINAL & lengkap = §7g; dipertahankan sebagai konteks)
- `channels.content_category` TEXT 'short'|'long' NOT NULL DEFAULT 'short' → anggota baru `_CHANNEL_OVERLAY_FIELDS`; mengisi `TenantRunConfig.content_type` (mengganti patri `pipeline.py:106`).
- `duration_presets`: +kolom `content_category`, kunci unik (content_category, seconds); 7 baris existing = 'short'; +6 baris 'long' (L2) + baris 'long' 90/120 bila diketok; +kolom slot visual (G6).
- `videos` / `production_runs`: +`content_category` (atribusi & analytics, G9).
- `ai_models.default_params`: varian ukuran per-kategori (bentuk final di proposal desain — params_landscape vs struktur bersarang).
- QC: kenop per-kategori (rumah final = keputusan G15).

### §7c Slot visual per segmen (✅ KETOK L5 19-Jul — angka hidup di DB, admin bisa tala; pemetaan final ke segmen explainer = §7g.3)
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

### §7d Gating tier (✅ KETOK L4 19-Jul; bentuk kolom final = §7g.4)
`plan_limits` +kolom (bentuk final di proposal): kategori yang diizinkan + durasi maks per-kategori. Isi usulan (selaras §3b): **trial & starter → Shorts saja · pro → Shorts + Regular ≤180s · business → semua.** Ditegakkan BERLAPIS mengikuti pola penegakan existing (§3b): dropdown FE terfilter di titik input (anti-human-error §3.1) + guard PATCH channel + gerbang jalan `gate_for_channel`/producer (anti-bypass; comp ikut plan_type) + perilaku downgrade prinsip §3b.2.

### §7e PROPOSAL DESAIN TEKNIS F1 — Fondasi kategori (disusun 19-Jul pasca F0 tutup; **MENUNGGU KETOK — nol kode sebelum itu**)
**Janji F1: NOL perubahan perilaku** — semua channel jadi 'short' eksplisit; mesin jalan persis seperti kemarin; yang baru hanya fondasi + dropdown terkunci.

| Lapis | Perubahan PERSIS | File/objek |
|---|---|---|
| DB (1 migrasi) | `channels.content_category` TEXT NOT NULL DEFAULT 'short' **+ constraint `channels_content_category_f1_lock` CHECK ='short'** (anti-bypass API sampai F2; teruji 19-Jul: 'long' DITOLAK DB) · kolom sama (CHECK short/long) di `videos` + `production_runs` + **`content_inventory`** (kategori WAJIB menempel item buffer — publisher publish dari buffer, bukan dari channel saat-publish) | `migrations/017x_content_category.sql` *(draf 0173 pernah diterapkan+diverifikasi lalu DICABUT bersih 19-Jul atas perintah owner — tinggal diterapkan ulang)* |
| BE | (1) `_apply_channel_overlay` (tenant_config.py:436) memetakan `content_category`→`config.content_type` (jahitan B9 hidup) · (2) **`TenantConfig` intelligence/config.py +field `content_type` + mapping di `tenant_config_from_channel` :54-78** (temuan 19-Jul: konstruktor producer/publisher TIDAK memetakan — tanpa ini seam mati di jalur terjadwal) · (3) `pipeline.py:106` `resolved_content_type` dari config (patri dibuang) + `result["content_type"]` diisi (dipakai stamp producer) · (4) stamp `production_runs` di **producer.py:126/352/444** · stamp `videos` via param baru 3 metode **supabase_writer.py:149/200/233** + pemanggilnya (pipeline.py:475/533/663 · publisher.py:183) · (5) **publisher.py:150 `publish(content_type="short")` patri → dari channel_row/inventory** (temuan 19-Jul, luput dari tabel audit §4) · (6) stamp `content_inventory` di titik insert producer (inventory.py — anchor digrep saat build) | `src/config/tenant_config.py` · `src/intelligence/config.py` · `src/orchestrator/pipeline.py` · `src/orchestrator/producer.py` · `src/utils/supabase_writer.py` · `src/orchestrator/publisher.py` (+`inventory.py`) |
| FE-tenant | Kartu/dropdown BARU "Kategori Konten" di Channel→Setting (dekat kartu Durasi :899): **Shorts (aktif)** / **Regular — coming soon (terkunci + badge)**, dwibahasa `Bi`, auto-save pola kolom-bersih (spt duration_preset :327) + kolom ikut select :468 *(anchor disegarkan grep 21-Jul — draf 19-Jul: :871/:299/:440 bergeser)* · hint awam + badge = **§7l.1** | `(app)/channels/[id]/page.tsx` |
| FE-admin | TIDAK tersentuh (bukan kenop `app_config` — kolom data channel; §3.3 kenop-lengkap tidak terpicu). Katalog Durasi disentuh di F2 | — |
| FE-marketing/email | TIDAK tersentuh (copy berubah di F4) | — |
| Uji/bukti | Uji unit permanen (overlay + konstruktor + default + writer-param + stamp) · py_compile+import · tsc+build · **regresi runtime: resolve config channel RAD nyata → content_type='short' + run nyata kolom terisi 'short' identik** · klik→layar dropdown (Regular terbukti terkunci) · nol regresi 5 permukaan | `tests/test_content_category_f1.py` (baru) |

Di luar lingkup F1 (tegas): duration_presets/gating/plan_limits (F2) · kanvas/QC/prompt/mesin long (F3) · publish metadata (F4). Deploy F1 = gerbang izin owner terpisah (§5.0 CLAUDE.md).

### §7f Text-to-video (fase susulan — L6)
Fondasi yang dibuat sekarang agar t2v tinggal menyala: konsep slot visual (§7c) netral-sumber · `visual_mode` per-channel sudah ada · rekonsiliasi `duration_presets.render_mode` ⇄ pilihan channel dituntaskan di desain F2. Ekonomi klip (720s = puluhan klip) dihitung saat fasenya tiba.

---

### §7g DESAIN RINCI F2 — KATALOG & GATING (matang 19-Jul · direvisi AUDIT KEMATANGAN 21-Jul; eksekusi menunggu gerbang F2)
*Menutup: G1 · G2 · G6 (rumah DB) · sebagian G15. Legenda: 📏 = angka kalibrasi, diisi dari data uji dgn metode tertulis — BUKAN lubang desain.*

**1. Skema `duration_presets` (kunci ganda):**
- +`content_category TEXT NOT NULL DEFAULT 'short'`; kunci unik lama (`seconds`) → **komposit `(content_category, seconds)`**; `is_default` bermakna per-kategori.
- +`visual_slots JSONB NULL` — peta segmen→jumlah gambar (L5). **NULL = 1 slot/segmen (perilaku lama persis — 7 baris shorts existing tak berubah byte pun).** `visual_beats` tetap = TOTAL slot (kompat; = sum(visual_slots)).
- +`min_hard_seconds NUMERIC NULL` — lantai durasi KERAS one-sided (L9=A): baris long-480 = 480.0; NULL = window dua-sisi lama. Generik, bukan patri angka di kode.
- **Konsumen kunci yang WAJIB ikut** (dari audit 19-Jul; anchor disegarkan grep 21-Jul): `format_catalog.py:35` (dict keyed `int(seconds)` → filter per-kategori dari run config + cache per-kategori) · FE tenant `channels/[id]/page.tsx` — baca `:477` · simpan `:327` · `presetModes` `:313` · fetch render_mode preset `:503` (select + filter kategori channel; keyed seconds tetap valid DALAM satu kategori) · FE admin `catalog/page.tsx:117,119` (PK_OF `durations: seconds` → komposit; tabel tampil ber-kolom kategori).
- `channels.duration_preset` TETAP integer detik; maknanya = pasangan (channels.content_category, seconds). **Aturan ganti kategori:** preset tak tersedia di kategori tujuan → auto-reset ke default kategori itu + pemberitahuan di UI (anti-state yatim). Default long = 180 (pilihan teknis reversible; owner bisa ganti via `is_default`).
- **Baris baru = 8:** short-120 + long-90/120/180/300/480/600/720 (L2+L3; short-120 = Shorts tetap ≤3 mnt aman).

**2. Arc naskah long (L7=A) — DIREVISI 21-Jul (audit kematangan; menggantikan draf 19-Jul yang salah rumah):**

⚠️ **3 fakta runtime yang mengubah desain (terverifikasi grep + DB live 21-Jul):**
- (a) **`format_profiles.section_template` NOL konsumen di `src/`** — mesin TIDAK pernah membacanya. Satu-satunya kolom `format_profiles` yang dikonsumsi = `default_wps` (via `format_catalog.effective_wps`, dipakai `script_engine.py:970`) — dan itupun di-override pace voice-first (`tts_profiles.delivery_wps` / `voice_catalog.delivery_wps`). **Segmentasi NYATA = `duration_presets.beats` (jsonb)** via `preset_beats()` (`format_catalog.py:81-90`).
- (b) **Beat tak dikenal DIBUANG SENYAP**: `script_engine._beat_plan` (`script_engine.py:222-229`) memfilter `known = [b for b in db if b in _BEAT_WEIGHT]` — beat di `duration_presets.beats` yang tak punya baris kosakata `content_beats` hilang TANPA error. Baris kosakata = prasyarat keras, bukan pelengkap.
- (c) **`content_beats.weight` = GLOBAL per beat_key + DIKALIBRASI OTOMATIS self-learning**: `align_beat_weights` (`pace_calibration.py:177`, dipanggil berkala dari self_learning; sumber `tts_delivery_samples.beat_words`; pagar weight_locked/min-N/step ±20%). Beat yang dipakai BERSAMA dua kategori → kalibrasi saling kontaminasi dua arah (melanggar prinsip benchmark-terpisah §7j.3 dokumen ini sendiri).

**Desain final arc explainer:**
- **Segmentasi tinggal di `duration_presets.beats`** (rumah yang NYATA dibaca mesin — fakta (a)): ke-7 baris preset long diisi `["hook_long","context","chapter_1","chapter_2","chapter_3","recap_bridge","payoff","cta_long"]` (8 segmen untuk SEMUA preset long, sesuai tabel slot §7g.3).
- **8 beat_key BARU SEMUA — NOL yang dipakai bersama shorts** (menutup kontaminasi (c) by-construction): `hook_long · context · chapter_1 · chapter_2 · chapter_3 · recap_bridge · payoff · cta_long`. `align_beat_weights` menghitung rasio DALAM set beat per-sampel → sampel long hanya menggeser beat long, beat shorts tak tersentuh — TANPA perubahan skema `content_beats`, TANPA menyentuh mekanisme kalibrasi, TANPA per-category kolom baru.
- **Baris kosakata WAJIB lahir LENGKAP** (fakta (b) + pola §3.3 CLAUDE.md — bukan cuma weight): tiap beat baru = 1 baris `content_beats` penuh: `beat_key` · `sort_order` **9–16** (melanjutkan shorts 1–8, tidak menyela) · `label_upper` · `label_id`/`label_en` + `hint_id`/`hint_en` (dwibahasa — tampil di form admin & layar tenant) · `weight` (awal proporsional slot §7g.3 kolom 720; kalibrasi menyusul 📏) · `default_timing_sec` · `motion_index`/`motion_mode`/`motion_dir`/`motion_rate` (dipakai Ken Burns `resolve_motion_sequence` — `ai_image.py:142-144`). Baris tanpa motion/label = ranjau senyap = pelanggaran.
- **Baris `format_profiles` explainer TETAP dibuat, dengan peran jujur:** `format_key='explainer'` · `name='Explainer'` · `section_template=[8 beat long]` (dokumentatif — kolom belum dibaca mesin, diisi BENAR agar tak jadi fosil menyesatkan) · `default_wps=2.2` (satu-satunya yang DIKONSUMSI; catatan: pace voice-first menimpanya bila voice punya `delivery_wps`) · `default_cta_mode='implicit'` · `render_mode='image_sequence'`. **Nama kolom di atas = PERSIS skema DB live (verifikasi 21-Jul; draf 19-Jul salah tulis `sections`/`cta_mode`).**
- Channel kategori long ⇒ `format_profile='explainer'` auto-set saat kategori diganti (editable saat arc long >1 kelak) — tak berubah.
- **Bukti anti-regresi shorts terverifikasi 21-Jul:** fallback `beats_for_n` (`beats.py:96-108`) = template TERKUNCI berisi kunci shorts eksplisit → penambahan 8 beat baru TIDAK mengubah jalur fallback shorts satu bit pun.

**3. Isi `visual_slots` per preset long** (distribusi §7c dipetakan ke segmen explainer; kunci JSON `visual_slots` = beat_key long §7g.2 — direvisi 21-Jul ikut namespace; short-120 memakai 8-beat shorts existing + slot §7c kolom 120):
| Segmen | 90L | 120L | 180 | 300 | 480 | 600 | 720 |
|---|---|---|---|---|---|---|---|
| hook_long | 1 | 1 | 1 | 2 | 2 | 3 | 3 |
| context | 1 | 1 | 1 | 2 | 2 | 3 | 3 |
| chapter_1 | 1 | 1 | 2 | 3 | 4 | 4 | 5 |
| chapter_2 | 1 | 2 | 3 | 5 | 9 | 9 | 12 |
| chapter_3 | 1 | 1 | 1 | 2 | 3 | 3 | 4 |
| recap_bridge | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| payoff | 1 | 1 | 2 | 2 | 3 | 4 | 5 |
| cta_long | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| **TOTAL** | **8** | **9** | **12** | **18** | **27** | **30** | **36** |

**4. Gating `plan_limits`** (L4 KETOK): +`allow_long BOOLEAN NOT NULL DEFAULT false` + `long_max_seconds INT NOT NULL DEFAULT 0`. Isi: trial/starter `false/0` · pro `true/180` · business `true/720`. Shorts (8–120) = semua tier, tanpa gate durasi (L4). **Kartu admin baru "Kategori & Durasi per Paket"** (§3.3 CLAUDE.md LENGKAP: kelompok sendiri, label+deskripsi dwibahasa, toggle utk boolean, dropdown durasi dari katalog long).

**5. Penegakan berlapis (pola terverifikasi §3b):**
(i) **FE titik input**: dropdown kategori & durasi terfilter paket + label ajakan upgrade (bentuk layar persis = **§7l.2/3/6**); (ii) **DB**: lepas `channels_content_category_f1_lock` → guard UPDATE `channels` (pola RLS migr 0155) memvalidasi (content_category, duration_preset) vs plan tenant; (iii) **runtime**: `gate_for_channel`/producer — channel long milik tenant turun-paket → TIDAK dilayani, data utuh, upgrade = hidup lagi (preseden `_channel_in_quota`, §3b.2) + notifikasi jujur; (iv) comp mengikuti plan_type (§3b).

**6. Rekonsiliasi `render_mode`:** tetap milik PRESET (kini per (kategori, seconds)); `channels.visual_mode` tetap pilihan sumber visual; gating input preset⇄model video ([B6] F3) tetap. Pilihan t2i/t2v penuh per-channel = fase t2v (§7f) — TIDAK dicampur di F2.

**7. Tampilan admin BERKELOMPOK per kategori (patri 21-Jul, lensa owner "konfigurasi jelas terpisah"):** tab Katalog→Durasi WAJIB menyajikan preset & kosakata beat dalam KELOMPOK kategori terpisah (seksi "Shorts" dan "Regular" masing-masing — bukan satu daftar campur 15 preset), memakai pola UI existing (§7a.5); form beat menampilkan penanda kategori tiap baris. Ukuran lulus: admin tidak mungkin salah menyunting baris kategori sebelah. *(Pelajaran insiden 17-Jul "12 kenop berserakan di Lainnya".)*

### §7h DESAIN RINCI F3 — MESIN LONG (matang 19-Jul · direvisi AUDIT KEMATANGAN 21-Jul; eksekusi menunggu gerbang F3 + hasil uji beban)
*Menutup: G3 · G4 · G5 · G7 · G14 · G15 · G6 (sisi render) · L8 · L9-mekanik.*

**0. PRASYARAT — uji beban (metode dipatri, dijalankan SEBELUM kode F3 diketok):** render sintetis di VPS jam sepi: audio sunyi 720s + 36 gambar uji → ukur wall-time/CPU/RAM/disk/ukuran file utk 180/480/720; hasil mengisi semua 📏 G7. Skrip uji sekali-pakai, worktree terpisah, nol sentuh produksi.

**1. Naskah ber-babak (G3):** 2 tahap LLM — (a) **outline**: topik → judul+ringkasan+anggaran kata per segmen (anggaran = durasi_segmen × WPS explainer; durasi segmen dari bobot `content_beats` long) + viral_score di outline; (b) **per-segmen**: generate isi segmen dgn konteks ringkasan segmen sebelumnya (anti-drift, hemat token) → rakit → QC koherensi final. Kalibrasi pace long = mekanisme durasi-via-speed existing (§10.A) diperluas; angka awal WPS 2.2 dari `format_profiles`, dikoreksi data run long pertama 📏.

**2. TTS panjang (G4):** potong per-SEGMEN (bukan per-karakter buta) → sintesis per-chunk provider channel (retry per-chunk; chunk gagal = run GAGAL JUJUR, §0.6) → gabung ffmpeg concat (codec seragam) → `word_timestamps` digeser offset kumulatif per-chunk (caption & beat_durations tetap presisi) → ukur TOTAL → atempo GLOBAL (mekanisme existing) bila di luar window. +kolom **`tts_profiles.max_chars_per_request`** (fakta 19-Jul: kolom belum ada; nilai per vendor diisi dari dokumentasi resmi saat build 📏). Window durasi: dua-sisi seperti sekarang, KECUALI preset ber-`min_hard_seconds` → one-sided [lantai, lantai+2×guard]; guard awal 10 dtk 📏 — **rumah nilai = kenop DB `ops_long_duration_guard_s`** (kartu Internal read-only §3.3d CLAUDE.md; patri 21-Jul lensa hardcode owner: BUKAN literal kode).

**3. Musik long (G5) — FAKTA TERVERIFIKASI 19-Jul: pustaka 28 track SEMUA 80–110 dtk → loop WAJIB, bukan opsi.** Desain: `_mix_music` — bila durasi track < durasi audio: ulang track yang SAMA (mood konsisten) via concat ber-`acrossfade` di tiap sambungan — **durasi crossfade = kenop DB `ops_music_crossfade_s`** (awal 1.0 dtk 📏; kartu Internal §3.3d — patri 21-Jul: BUKAN literal kode); fade-out akhir tetap; `-t total_duration` tetap. Kurasi track panjang = opsional owner kemudian (biaya lisensi), bukan blocker.

**4. Kanvas & slot visual (B1/B2/B15/B18/B19/B21/B23/B33 + G6):** konstanta kanvas → helper tunggal `canvas_for(content_type)` (short 1080×1920 · long 1920×1080) — SEMUA titik dimensi merujuknya (B2 sudah via konstanta = aman); logo maks relatif % lebar kanvas (B33); Ken Burns netral-rasio (B19). Assembler membaca `visual_slots`: segmen ber-slot>1 → prompt varian bernomor (sudut/adegan berbeda per slot, mekanisme prompt per-beat existing diperluas per-slot); Ken Burns per-slot. **📌 PATRI 21-Jul (pengecualian sadar §3.3, lensa hardcode owner): dimensi kanvas + thumbnail (1280×720/1080×1920, B13) = KONSTANTA KODE SENGAJA** — standar teknis platform YouTube, bukan nilai bisnis; dijadikan kenop admin justru ranjau anti-human-error (§3.1: salah 1 angka = semua video gagal QC). Syarat sahnya: SATU titik helper, nol duplikat, thumbnail diturunkan dari helper yang sama.

**5. Orientasi prompt SATU PINTU (B16/B17/B22/B24/B25/B27/B30):** helper `orientation_suffix(content_type)` di satu modul; semua titik 🤖 memanggilnya — nol string orientasi tersebar lagi. **📌 PATRI 21-Jul (pengecualian sadar §3.3): teks suffix orientasi = di KODE** (helper tunggal) — konsisten idiom existing (seluruh prompt script_engine juga hidup di kode); dicatat eksplisit di sini agar tercatat sebagai KEPUTUSAN, bukan kelalaian. **DNA (L8=A) prosedur:** (a) arsip nilai lama 10 niche (kolom/tabel riwayat) → (b) hapus frasa orientasi → (c) uji banding visual per-niche (1 gambar sebelum-vs-sesudah, owner menilai) → (d) aturan "DNA netral-orientasi" masuk pedoman NICHE_DNA + validasi editor admin (tolak kata orientasi saat simpan).

**6. Caption landscape (B3/G14):** preset caption per-kategori (font, words_per_line, margin_v) = kenop DB ber-kartu admin; ASS PlayResX/Y ikut kanvas; nilai awal long 📏 dari uji visual nyata (§3.4 per-widget).

**7. QC per-kategori (B5/B6/B34/G15):** pindah ENV → `app_config` per-kategori (`qc_aspect_short/long`, `qc_max_duration_short/long`, `qc_min_duration_short/long`; long max awal 780) + kartu admin "QC per Kategori" dwibahasa; ENV lama = fallback transisi 1 rilis lalu dicabut (fosil disapu §3.2).

**8. Katalog model per-kategori (§4e/B20/B21):** +`ai_models.default_params_long JSONB NULL` — NULL = model belum mendukung long → titik input model channel-long HANYA menawarkan model ber-params-long (anti-human-error §3.1); isi awal: flux/gpt-image ukuran landscape, model video aspect 16:9; admin katalog menampilkan kedua varian.

**9. Anti-sumbat antrian (G7, mandat L10):** dari hasil uji beban 📏 → (a) bobot slot: job long menempati ceil(t_long/t_short) slot pool; (b) fair-share round-robin antar tenant di producer; (c) kenop `ops_render_long_max_concurrent` (kartu Internal, read-only tenant); (d) telemetri `elapsed_seconds` per preset + alarm admin ambang antrean (deteksi sebelum tenant merasa).

**10. Kalibrasi bobot sadar-kategori (temuan AUDIT 21-Jul — fakta §7g.2c):** `align_beat_weights` (`pace_calibration.py:177`) menggeser `content_beats.weight` berkala dari data run nyata. Dengan beat long ber-namespace penuh (§7g.2), pemisahan kalibrasi Shorts⇄Regular terjadi by-construction — mekanisme TIDAK diubah. **Kewajiban bukti F3:** uji regresi eksplisit — jalankan kalibrasi atas sampel campuran (shorts+long) → assert weight beat shorts TIDAK berubah oleh sampel long, dan sebaliknya.

### §7i DESAIN RINCI F4 — PUBLISH & RILIS REGULAR (matang 19-Jul; gerbang F4)
*Menutup: G11 · G16 · sisa 📄COPY + 🔀 publish.*

1. **Metadata publish bercabang** (content_type sudah mengalir sejak F1): #Shorts & tags shorts HANYA short (B10/B11) · URL `watch?v=` utk long (B12; konsumen regex producer.py:28-31 sudah siap ✅) · pesan/log/docstring (B7/B8/B14/B31) · contoh hashtag skema naskah (B26) ikut kategori.
2. **Chapters otomatis** (nilai tambah long): deskripsi long diisi "0:00 <judul segmen>" dari `beat_durations` NYATA pasca-render — gratis, menaikkan navigasi & watch-time; judul segmen dari outline naskah.
3. **Thumbnail long:** hero prompt landscape (B22 via `orientation_suffix`) → jalur thumbnail 1280×720 (B13, sudah 2-cabang); kualitas CTR = bahan analis F5.
4. **Rilis & switching:** unlock dropdown Regular per tier (gating F2 hidup) · ganti kategori channel = revalidasi preset+arc (§7g.1) · **video long PERTAMA per channel auto-private untuk review tenant** (kenop; selaras §6.6 CLAUDE.md) → tenant menyetujui → publik berikutnya — **alur layar lengkap (panel status+tombol+notifikasi) = §7l.5**.
5. **Copy semua permukaan** (daftar persis dari §4): FE-marketing M1/M3 + email M4 + admin hints A1–A3 + CMS (1 artikel docs + 5 blog) + email nurture B32 — dwibahasa `Bi`, positioning "Shorts + video panjang". **+ ISI DB halaman pricing (temuan audit 21-Jul, luput dari daftar 19-Jul):** `plan_limits.marketing_features` + `tagline_id/tagline_en` baris pro & business ditambah fitur pembeda Regular ("Video panjang ≤3 mnt" / "Video panjang ≤12 mnt", dwibahasa) — pembeda paket di pricing datang dari kolom ini, bukan kode.
6. **Bukti rantai penuh** (§3.4): checklist klik→layar per permukaan + 1 video long e2e nyata (produksi→publish→tampil benar di YouTube player landscape).

### §7j DESAIN RINCI F5 — KECERDASAN SADAR-KATEGORI (matang 19-Jul; gerbang F5)
*Menutup: G9 · G10 · B28/B29.*

1. **Fondasi = stamp F1** (`videos`/`production_runs`/`content_inventory`.content_category) — semua agregasi kecerdasan bisa memfilter kategori.
2. **Analis (B17 §6):** dosir per-channel menyertakan kategori channel + prompt analis menyebut format nyata (B28); menu keputusan sama, konteksnya benar.
3. **Benchmark terpisah:** kurva retensi M1, top_hooks/topics, avoid_patterns — dianalisis DALAM kategori masing-masing (semesta retensi 60 dtk ≠ 12 menit; jangan banding silang). Data per-channel sudah bersih by-design (kategori = per-channel).
4. **Warisan (W1/K6):** prior hanya dari kategori SAMA; lintas-kategori = label keyakinan-rendah (pola K6 yang sudah diketok) — pelajaran Shorts tidak menyetir long tanpa tanda.
5. **Trend radar (B29/G10):** query per-kategori (short: "shorts"; long: tanpa suffix + istilah long-form) — detail kecil diketok di gerbang F5 dengan sampel hasil nyata. **Rumah nilai = kenop DB per-kategori** (kartu admin dwibahasa §3.3 lengkap; patri 21-Jul lensa hardcode owner: BUKAN literal kode seperti B29 sekarang).

### §7k MATRIKS CAKUPAN TOTAL — bukti nol titik yatim (setiap ID audit & celah → rumah fase)
| Titik | Rumah |
|---|---|
| B4 B9 (seam) · D1 D2 + `content_inventory` · publisher.py:150 · `tenant_config_from_channel` | **F1** (§7e rev) |
| D3 D4 D5 · T4 (dropdown) · G1 G2 · G6-rumah-DB · rekonsiliasi render_mode | **F2** (§7g) |
| B1 B2 B3 B5 B6 B15–B25 B27 B30 B33 B34 · §4e ai_models · §4e ENV-QC · §4e DNA (L8) · G3 G4 G5 G7 G14 G15 · L9-mekanik | **F3** (§7h) |
| B7 B8 B10–B14 B26 B31 B32 · T1 T2 T3 · A1 A2 A3 · M1–M4 · CMS · G11 G16 | **F4** (§7i) |
| B28 B29 · G9 G10 | **F5** (§7j) |
| `align_beat_weights`/`tts_delivery_samples` (kalibrasi bobot self-learning — temuan audit 21-Jul) | **F2** (namespace beat long §7g.2) + bukti uji **F3** (§7h.10) |
| `plan_limits.marketing_features`+taglines (pembeda paket di pricing — temuan audit 21-Jul) | **F4** (§7i.5) |
| G8 (kuota) = L10 KETOK (tuntas) · G12 (migrasi/nol-regresi) = kewajiban TIAP fase (bukti §3.8 CLAUDE.md) · G13 (istilah) = §0 kamus (tuntas) | — |
| ✅AMAN yang TIDAK diubah: B2(via konstanta) A4 M5 T3(player) | diverifikasi ulang saat fase terkait |
| Standar UI/UX per-peran §7l.1–7 (mandat owner 21-Jul) | **F1** (7l.1) · **F2** (7l.2/3/4/6/7a) · **F4** (7l.2/5/7b) |

### §7l STANDAR UI/UX PER-PERAN (mandat owner 21-Jul "seluruh UI/UX wajib MEMUDAHKAN admin & tenant" — mengikat SEMUA fase; 100% menumpang pola/komponen existing §7a.5, NOL komponen baru; anchor pola diverifikasi grep 21-Jul)

**TENANT (Channel → Setting + daftar channel + runs):**
1. **Kartu "Kategori Konten" ber-hint awam (F1):** pola kartu existing = judul + 1 kalimat pengantar `muted` dwibahasa (cermin kartu LLM `channels/[id]/page.tsx:917-919`). Isi hint: "Shorts = video pendek layar berdiri (8–120 dtk). Regular = video panjang layar mendatar (1,5–12 mnt), untuk konten mendalam & iklan mid-roll." Ukuran lulus: tenant awam paham beda + dampak TANPA membuka dokumentasi.
2. **Opsi terkunci = AJAKAN, bukan tembok (F2 unlock per-tier; F1 "coming soon"):** opsi Regular di luar paket tetap TAMPIL (disabled) + badge nama paket pembuka + banner pola existing PERSIS `channels/page.tsx:75-77` (ikon peringatan + kalimat dampak + link `/billing` "Upgrade paket"). Teks menyebut paket konkret: "Regular ≤3 mnt mulai paket Pro · sampai 12 mnt di Business." F1: badge "Segera hadir/Coming soon" netral (belum menyebut paket — gating baru hidup F2).
3. **Ganti kategori = ConfirmDialog ber-ringkasan dampak (F2):** pola `ConfirmDialog` existing (cermin Pause `channels/[id]/page.tsx:442-448`): sebut PERSIS yang berubah — durasi di-reset ke default kategori tujuan · struktur cerita ganti arc · model visual mungkin perlu dipilih ulang (bila model aktif tak ber-varian kategori tujuan). Pasca-ganti: pesan sukses menyebut nilai baru (pola `presetMsg`). Ukuran lulus: tenant TIDAK PERNAH kaget "setelan saya hilang".
4. **8 preset baru lahir ber-`use_case`/`use_case_en` ramah-awam (F2, satu migrasi dengan barisnya):** tabel penjelas existing `PresetTables` (`channels/[id]/page.tsx:903`) otomatis menampilkannya — maka teksnya WAJIB menjual & mendidik, contoh 480s: "8 menit — ambang minimal iklan mid-roll YouTube" / "8 minutes — YouTube mid-roll ads minimum". Baris tanpa use_case dwibahasa = migrasi DITOLAK review.
5. **Panel review video-Regular-PERTAMA (F4; melengkapi §7i.4):** §3.6 CLAUDE.md — status + tombol dalam SATU panel di halaman channel: badge status "Menunggu review Anda" + tombol "Tonton di YouTube" (link video privat) + tombol "Setujui — video berikutnya tayang publik" (menulis penanda selesai-review channel; auto-save) + notifikasi email/Telegram dwibahasa saat video review terbit (infra notifikasi existing). Ukuran lulus: dari notifikasi → 2 klik → selesai review; video pertama TIDAK PERNAH menggantung sunyi di mode privat.
6. **Turun paket = banner jujur & menenangkan (F2):** perluasan banner kuota existing (`channels/page.tsx:75-77`) di kartu channel Regular yang berhenti dilayani: "Paket Anda tidak lagi mencakup video Regular — produksi channel ini dijeda. Semua data & video AMAN. Upgrade untuk melanjutkan." + link `/billing`. Selaras preseden §3b.2 (data utuh, upgrade = hidup lagi otomatis).
7. **Penanda kategori di semua permukaan hasil:** (a) **F2** — badge kecil `badge-default` "Shorts"/"Regular" di kartu daftar channel (pola badge niche `channels/page.tsx:83`) + di item riwayat runs (tenant multi-channel membedakan sekilas); panel Test (`test-niche-panel.tsx`) menampilkan ekspektasi dwibahasa "video panjang butuh waktu render lebih lama" saat channel Regular. (b) **F4 (admin)** — katalog model: model TANPA `default_params_long` ber-badge "Shorts saja" (di daftar & dialog ✎), sehingga admin tahu model mana yang perlu dilengkapi varian landscape.

**ADMIN:** pengelompokan tab Durasi per kategori + penanda kategori form beat = §7g.7 (sudah dipatri) · kartu paket/QC/caption per kategori = §7g.4/§7h.7/§7h.6 (kartu sendiri, dwibahasa, tipe input tepat §3.3) · badge "Shorts saja" katalog model = butir 7b di atas. Ukuran lulus seluruh §7l: admin & tenant TIDAK MUNGKIN salah konfigurasi dari layar (salah = tertolak/terfilter DI TITIK INPUT), dan setiap keadaan sistem (terkunci paket · menunggu review · dijeda downgrade) SELALU tampil dengan alasan + tombol tindak lanjut di panel yang sama.

## §8 PLAN vs REALISASI (fase ber-gerbang — TIAP fase butuh ketok owner sebelum kode; kolom REALISASI diisi HANYA dengan bukti)

| Fase | Isi | Gerbang masuk | REALISASI |
|---|---|---|---|
| **F-1 Audit + arsitektur** | Audit hardcode 5 permukaan per-baris · kartu keputusan · sisir-ulang celah G1–G16 · dokumen arsitektur ini | mandat owner 19-Jul | ✅ 19-Jul: audit tuntas (§4) · ledger keputusan (§2) · celah terbungkus (§6) · file di-rename & disempurnakan |
| **F0 Keputusan & verifikasi** | Owner ketok L4–L10 + verifikasi web L9 | — | ✅ **TUTUP 19-Jul**: L4/L5/L6/L7=A/L8/L9=A/L10 semua diketok (ledger §2) + web terverifikasi + catatan owner L7 (4 permukaan) & L10 (anti-sumbat G7) terekam |
| **F1 Fondasi kategori (nol perubahan perilaku)** | Kolom `channels.content_category` + aliran ke seam s92 (B4/B9) + `videos`/`production_runs` atribusi + dropdown channel "Shorts / Regular (coming soon)" terkunci | F0 ✅ · proposal §7e diketok 19-Jul · **⛔ eksekusi DITAHAN owner 19-Jul sampai dokumen matang 100%** | ⏳ (migr 0173 sempat APPLIED → DICABUT bersih 19-Jul atas perintah owner; verifikasi titik stamp TETAP berlaku: `producer.py:126/352/444` · `supabase_writer.py:149/200/233` · +temuan `publisher.py:150` patri content_type="short" & `tenant_config_from_channel` tanpa content_type — masuk lingkup F1 saat dilanjut) |
| **F2 Katalog & gating** | Desain rinci = **§7g** (kunci ganda preset · visual_slots · arc explainer · gating plan_limits · penegakan 4 lapis) | F1 terbukti nol regresi · ketok proposal eksekusi F2 | ⏳ |
| **F3 Mesin long** | Desain rinci = **§7h** (uji beban dulu · naskah 2-tahap · TTS per-segmen · musik loop · kanvas/orientasi/QC/caption per-kategori · anti-sumbat) · **bukti presisi durasi (gerbang §7.3 CLAUDE.md)** | F2 live · hasil uji beban mengisi 📏 · ketok | ⏳ |
| **F4 Publish & rilis Regular** | Desain rinci = **§7i** (metadata bercabang · chapters otomatis · first-long-private · copy semua permukaan · bukti klik→layar e2e) | F3 terbukti end-to-end · ketok | ⏳ |
| **F5 Kecerdasan sadar-kategori** | Desain rinci = **§7j** (dosir+benchmark per-kategori · warisan pola K6 · trend radar) | F4 live + data long masuk · ketok | ⏳ |

Aturan pengisian REALISASI: bukti runtime nyata (uji + angka), bukan "build lulus"; tiap fase tutup administrasi §3.7 (file ini + MEMORY.md + SISA_KERJA).

---

## Changelog
- 2026-07-21 (2) — **§7l STANDAR UI/UX PER-PERAN lahir (ketok owner "pastikan seluruh UI/UX memudahkan admin & tenant"):** 7 patrian tenant+admin, semua menumpang pola existing ber-anchor terverifikasi (kartu ber-hint `:917` · banner upgrade `channels/page.tsx:75-77` · ConfirmDialog pola Pause `:442-448` · PresetTables `:903` · badge `:83`): hint awam kartu Kategori · opsi terkunci=ajakan upgrade ber-paket-konkret · ganti kategori=konfirmasi ber-ringkasan dampak · preset baru wajib use_case dwibahasa menjual · panel review video-Regular-pertama (SATU panel status+tombol+notifikasi — melengkapi §7i.4 yang under-specified) · banner downgrade jujur-menenangkan · badge kategori di channel/runs/Test + badge "Shorts saja" katalog model admin. +rujukan silang §7e/§7g.5/§7i.4→§7l + baris matriks §7k. NOL komponen baru (§7a.5), NOL kode disentuh.
- 2026-07-21 — **AUDIT KEMATANGAN F2–F5 (ketok owner; verifikasi ulang SEMUA klaim desain vs kode + DB live):** mayoritas desain TERBUKTI benar (preset 7 baris kunci tunggal · plan_limits nol kolom durasi · musik 28 track 80–110s · 7 model portrait · 0173 tercabut bersih · patri pipeline:106 & publisher:150 · fallback `beats_for_n` terkunci = aman). **3 lubang dipatri:** (1) §7g.2 DITULIS ULANG — segmentasi explainer pindah ke rumah yang NYATA dibaca mesin (`duration_presets.beats`; fakta: `format_profiles.section_template` nol konsumen, `format_profiles` hanya menyumbang `default_wps`); (2) 8 beat long ber-NAMESPACE penuh (`hook_long`…`cta_long`, nol beat dipakai bersama shorts) — menutup kontaminasi dua-arah kalibrasi otomatis `align_beat_weights` (+§7h.10 kewajiban uji anti-kontaminasi); (3) baris kosakata beat wajib lahir LENGKAP (label dwibahasa/hint/sort_order 9–16/motion/weight — beat tak dikenal DIBUANG SENYAP oleh `script_engine:222-229`). **3 koreksi:** nama kolom presisi (`section_template`/`default_cta_mode`) · §7i.5 +`plan_limits.marketing_features`/taglines (pricing) · anchor FE disegarkan (kartu Durasi :899 · simpan :327 · baca :477 · presetModes :313/:503). **4 patrian lensa owner (hardcode & pemisahan konfigurasi):** kanvas+thumbnail & suffix orientasi = pengecualian sadar di kode (§7h.4/§7h.5, alasan tercatat) · guard durasi & crossfade musik = kenop `ops_*` (§7h.2/§7h.3) · query tren = kenop DB per-kategori (§7j.5) · tab Durasi admin wajib BERKELOMPOK per kategori (§7g.7 baru). §7k matriks +2 baris (nol titik yatim dipertahankan). NOL kode produksi disentuh.
- 2026-07-20 — **§7a.5 SATU NUANSA UI dipatri** (ketok owner "patri"): seluruh layar F1–F5 wajib pustaka/pola UI existing, dilarang komponen/gaya/library baru — dulu hanya tersirat di proposal F1, kini mengikat eksplisit (cermin SPEC partner §3.9).
- 2026-07-19 (10) — **PEMATANGAN 100% (mandat owner "dokumen wajib matang dulu"):** +§7g desain rinci F2 (kunci ganda preset + visual_slots + min_hard_seconds + arc explainer 8 segmen + tabel slot long-90..720 + gating plan_limits allow_long/long_max_seconds + penegakan 4 lapis) · +§7h desain rinci F3 (uji beban ber-metode; naskah 2-tahap; TTS potong-per-segmen + max_chars_per_request; **musik: FAKTA 28 track semua 80–110 dtk → loop wajib**; canvas_for(); orientation_suffix() satu-pintu; prosedur DNA L8; caption+QC per-kategori; ai_models params_long; anti-sumbat 4 komponen) · +§7i F4 (publish bercabang + chapters otomatis + first-long-private + copy semua permukaan) · +§7j F5 (kecerdasan sadar-kategori, benchmark terpisah, warisan pola K6) · +§7k MATRIKS cakupan total (nol titik yatim) · §7e F1 direvisi lengkap (publisher.py:150 + tenant_config_from_channel + content_inventory + 6 titik stamp ber-anchor). Titik kalibrasi ditandai 📏 + metode pengisiannya tertulis. Sapu koherensi: §7b/§7c/§7d diberi banner status final · D3/D4/DNA/G-register disinkronkan ke rumah desainnya · CARA-PAKAI 2(a) diperluas ke gerbang per-fase.
- 2026-07-19 (9) — **Eksekusi F1 DITAHAN owner** ("bersihkan dulu, dokumen wajib matang 100%"): migr 0173 yang sempat diterapkan DICABUT bersih (3 kolom+constraint drop, verified NOL sisa; file migrasi dihapus; kode BE/FE belum tersentuh). Warisan berharga dari persiapan F1 dipatri di §8 F1: titik stamp terverifikasi + 2 temuan baru (publisher.py:150 patri "short" di luar tabel audit; `tenant_config_from_channel` intelligence/config.py TIDAK memetakan content_type → wajib dipetakan saat F1). Fase berikutnya = PEMATANGAN dokumen (F2–F5 rinci).
- 2026-07-19 (8) — **F0 TUTUP PENUH: KETOK L7=A** (+catatan owner "catat baik-baik": 4 permukaan durasi/segmentasi wajib disesuaikan — anchor admin Katalog→Durasi & tenant Channel→Durasi & segmentasi konten TERVERIFIKASI) **+ L9=A** (label 8 menit, mesin jamin ≥480.0s). Temuan baru: `content_beats.weight` + form admin = rumah alami distribusi slot visual (G6 di-update, anti mekanisme-kembar). NEXT: proposal desain teknis F1.
- 2026-07-19 (7) — **KETOK L5 · L6 · L8 · L10** (owner). L10 menyertakan mandat antisipasi penyumbatan antrian → G7 diperluas (slot berbobot · fair-share per tenant · cap long terpisah · telemetri+alarm; final di F3 ber-angka uji beban). Sisa terbuka: L7 (arc) + L9-lanjutan (jaminan 8:00) — menunggu jawaban owner pasca penjelasan sederhana.
- 2026-07-19 (6) — **L4 KETOK** (trial & starter = Shorts saja · pro ≤180s · business semua) + **L9 TERVERIFIKASI web** (Shorts maks 3 mnt ✅ · mid-roll ambang KERAS ≥8:00 → G3 window one-sided utk 480s · musik Shorts >60s wajib royalty-free) + L10 dimatangkan (fakta BYOK: biaya AI = tanggungan kunci tenant) + §2b disegarkan.
- 2026-07-19 (5) — **§3b ARSITEKTUR PAKET & BILLING** ditambahkan (teguran owner "belum paham 100% arsitektur business — deep dive lagi"): 4 paket + harga `pricing_config` + mesin status `renewal.py` + 6 titik penegakan existing + preseden downgrade `_channel_in_quota` + populasi tenant nyata; L4/G1/§7d/§2b/§0 disinkronkan (usulan pemetaan: trial&starter=Shorts · pro=+Regular≤180s · business=semua).
- 2026-07-19 (4) — Penguatan SSOT (perintah owner "lengkap, jelas, tanpa ambigu, mudah dipahami, dirawat"): blok CARA PAKAI wajib + §0 kamus istilah + §2b daftar pertanyaan bahasa awam + aturan perawatan dokumen.
- 2026-07-19 (3) — **Rename → `CONTENT_CATEGORY_ARCHITECTURE.md`** + naik jadi dokumen arsitektur: ledger keputusan §2 · fakta baru terverifikasi (plan_limits/TTS/musik/kunci preset) §3 · celah G1–G16 §6 · arsitektur target §7 · Plan-vs-Realisasi §8 (perintah owner).
- 2026-07-19 (2) — §11 kartu keputusan matang ditambahkan (perintah owner "matangkan dan bungkus dulu 3 hal") — kini dilebur ke ledger §2 (L7/L8) + arahan durasi owner menggantikan opsi Kartu 1.
- 2026-07-19 — dokumen lahir sebagai `AUDIT_HARDCODE_FORMAT_VIDEO.md` (audit tuntas 5 permukaan, per-baris; mandat owner "tidak boleh ada 1 baris terlewat").
