# 🎯 DOKUMEN FINAL MENUJU GO-LIVE — Tenant · Channel · Niche · Voice · Pipeline

> **DOKUMEN LIVING (Plan + Realisasi)** — satu-satunya acuan pembenahan menuju **go-live + go-market**. Di-update terus (kolom REALISASI tiap item) hingga TUNTAS.
> **Standar dokumen (WAJIB):** se-clear mungkin, nol miss-persepsi, **NOL asumsi liar**. Tiap klaim ber-bukti `file:baris`/`tabel.kolom` atau bertanda **`[VERIFIKASI DULU]`**. Tiap item self-contained — sesi baru tanpa ingatan chat ini tetap paham & bisa eksekusi.
> **Provenance fakta (PENTING — hasil audit sub-agent TIDAK ditelan mentah):** seluruh fakta load-bearing di §5 sudah **diverifikasi-ulang LANGSUNG** dengan membaca kode/DB sendiri (sub-agent dipakai hanya sebagai *lead*, lalu dicek manual). Tesis utama (config-fanout per-tenant = pondasi belum tuntas, §4) berasal dari **bacaan langsung** `config.py:47-68` + `pipeline.py:58-65`, bukan kesimpulan agent (yang sempat keliru klaim "95% selesai"). Saat mengeksekusi tiap item, **BUKTI-nya wajib dicek-ulang sekali lagi** sebelum mengubah kode.
> **Cakupan:** semua hasil diskusi sesi ini — dari improvement LLM/Cacat B → ambiguitas voice → niche=DNA/channel=brand-skin → operasional per-channel → Business niche → branded-content (disisipkan dari `BRANDED_CONTENT_ARCHITECTURE.md`).
> **Legend:** ⬜ belum · 🟡 jalan · ✅ selesai+validasi · ⏸️ blocked
> **Update terakhir:** 2026-06-20.

---

## 0. ⭐ MULAI DARI SINI (resume guide untuk sesi berikutnya)
1. Baca **§2 Pondasi** + **§3 Keputusan** + **§4 Peta Config-Fanout** (inti pemahaman; 5 menit).
2. Cek **§7 FASE** — cari item pertama ber-status ⬜/🟡 pada FASE prioritas terendah-nomornya. Itu pekerjaan berikutnya.
3. Tiap item punya: TUJUAN · KENAPA · BUKTI · PLAN · DEPENDS · DONE-BILA · REALISASI. Kerjakan sesuai PLAN, validasi sesuai DONE-BILA, isi REALISASI (status+commit). **Item LLM/voice (F1-01, F4-02/03/04) menunjuk ke §10 LAMPIRAN — desain solusi yang SUDAH DISEPAKATI (prompt persis, skema field, kontrak JSON, contoh). IKUTI §10 apa adanya — jangan rancang ulang / berasumsi.**
4. Aturan kerja: lokal → validasi 100% → commit → push → pull+rebuild+restart di VPS. JANGAN ngoding di VPS. JANGAN rusak produksi ryan. Validasi tiap fase sebelum lanjut.
5. **Status global saat tulisan ini:** belum ada kode disentuh. Fakta sudah diaudit penuh (BE hardcode + multi-channel). Item berikutnya = **F1-01**.

---

## 1. 📖 GLOSARIUM (samakan persepsi)
- **User = Tenant**: 1 akun login = 1 tenant (`tenant_id = auth.uid()`). Tak ada tim.
- **Channel**: kanal YouTube milik tenant. **1 tenant = BISA BANYAK channel** (kuota per tier). Tabel `channels` (PK `id` uuid).
- **Niche**: genre konten + DNA-nya (cara menulis, suara, visual, musik, timing). Tabel `niches` (PK `niche_id`).
- **DNA konten**: properti yang menentukan *karakter/genre* konten → milik **NICHE**: `voice_profile` (cara menulis), `visual_style`, `image_quality_tags`, `image_negative_prompt`, `mood_priority`, `section_timing`, `emotion_scoring_criteria`, **voice (identitas)**.
- **Brand skin**: identitas tampilan tiap channel → milik **CHANNEL**: caption style, hashtag, bahasa, logo/CTA/landing.
- **Knob operasional/biaya**: mode & biaya produksi → milik **CHANNEL** (keputusan owner): `visual_mode`, `image_quality`, musik on/off+volume, quality-gate.
- **voice_key**: ID voice di provider TTS (mis. ElevenLabs voice_id). Disimpan di katalog `voice_catalog`.
- **`TenantConfig`** (`src/intelligence/config.py`): objek config **PER-CHANNEL** (dibangun dari row `channels`). Dipakai produksi.
- **`TenantRunConfig`** (`src/config/tenant_config.py`): objek config **PER-TENANT** (dibangun dari `tenant_configs`). Dipakai produksi untuk field yang belum per-channel. **Sumber masalah fanout (lihat §4).**

---

## 2. ⛳ PONDASI NON-NEGOTIABLE
> **1 user = 1 tenant = BISA MULTI CHANNEL (sesuai tier).** Kuota dari `plan_limits` (DB, admin-editable): **trial/starter=1ch · pro=3ch · business=10ch** (`src/config/tenant_config.py:44-47`).
> Konsekuensi: **config konten & brand = milik CHANNEL/NICHE, bukan tenant.** Tiap fase diuji terhadap model ini; tak ada jalur boleh mengasumsikan "1 tenant = 1 channel".

---

## 3. 🔒 KEPUTUSAN TERKUNCI (sesi 2026-06-19/20)
1. **Cacat B (durasi) bukan bug prompt.** Akar terukur: budget-wps terlalu rendah (budget 1.55–1.62 vs nyata 1.86–2.0; V1 base **1.97**) + variansi intrinsik + jaring sempit. Solusi: **LLM pilih `words`+`speed` bersama** (durasi via speed) + jaring deterministik tipis. Bukan tuning prompt lagi.
2. **LLM = nyawa konten.** Orchestrator = konduktor: **1 prompt dinamis (preset × niche × voice × pace)** → **1 JSON** = partitur 3 konsumen: narasi (TTS), `tts_params` (voice+delivery), `visual_suggestions` (image-gen).
3. **Voice identitas = NICHE → 1 `voice_key`** (dari `voice_catalog` = single source). Tanpa voice random (branding). LLM hanya setel DELIVERY per-naskah; identitas stabil.
4. **NICHE = DNA** · **CHANNEL = brand skin + knob operasional/biaya** · **TENANT = akun (plan/billing/BYOK keys/notifikasi)**. (Caption+hashtag = channel; visual STYLE & mood-musik = niche; visual_mode/image_quality/music-on-off/volume/quality-gate = channel.)
5. **Niche dibuat hanya di:** admin panel, atau tenant **Business** (niche-studio = clone UI admin, **PRIVATE eksklusif** `access_type=private, exclusive_to=tenant_id`). Entry/Pro: pakai niche ada / request via `niche_requests`.
6. **`voice_catalog`/`tts_profiles` field = parameter TTS baku** (portabel lintas provider).

---

## 4. 🗺️ PETA CONFIG-FANOUT (INTI — verified) — apa di mana SEKARANG vs TARGET
> Produksi memakai DUA objek config sekaligus: `TenantConfig` (per-channel, dari `channels`) + `TenantRunConfig` (per-tenant, dari `tenant_configs`). Bukti: `pipeline.py:99` muat `tenant_config` per-channel; `pipeline.py:58-65` muat `run_config = load_tenant_config(tenant_id)` per-tenant. `tenant_config_from_channel` (config.py:47-68) hanya thread field channel.

| Field | Sekarang | Per- | TARGET | Aksi |
|---|---|---|---|---|
| niche, niche_mode, niche_pool | channels (+duplikat tenant_configs) | channel ✅ | channel | bersihkan duplikat |
| duration_preset, format_profile | channels | channel ✅ | channel | — |
| cta_mode, brand_name/cta_text, brand_logo, logo_*, landing_link, link_position | channels (migr 0015) | channel ✅ | channel | — (FE saja, §branded) |
| publish_privacy, ai_disclosure, publish_slots, buffer_depth, content_language, production_cron | channels | channel ✅ | channel | — |
| **caption_style** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **niche_hashtags** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **tts_voice / tts_voice_per_niche / tts_voice_settings** | tenant_configs + map HARDCODE | tenant ❌ | **NICHE (voice_key)** | voice_catalog + niches.voice_key |
| **visual_mode, image_quality** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **music_enabled, music_volume, music_default_mood** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **script_min_viral_score, script_max_retry** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| visual_style, image_quality_tags, image_negative_prompt, mood_priority, section_timing, emotion_scoring_criteria, voice_profile, **motion_profiles(baru)** | niches | niche ✅ (motion belum) | niche | + motion_profiles |
| llm_provider/model/library, *_api_key_enc (BYOK), plan_type, subscription_status, telegram_*, timezone, videos_per_day | tenant_configs | tenant ✅ | tenant | — |

**Baris ❌ = inti FASE 1 (pondasi multi-channel belum tuntas).**

---

## 5. ✅ FAKTA TERVERIFIKASI (anchor — jangan re-derive)

### 5.1 Durasi/TTS (Cacat B)
- `duration_presets`: 8/15/30/45/60/75/90s; 30s=`[hook,core_facts,cta]` vb=3; 60s=5 beats; 8s=ai_video, sisanya image_seq.
- wps NYATA: V1 `189 kata @speed0.86 → 111.5s` ⇒ base **1.97**; V2 efektif 1.86–2.0. Budget mesin 1.548–1.674 → **under-budget** → audio pendek (39–46s vs band 51–69s).
- `script_engine.py`: WPS=302, total_words=304/315, length_block kaku=370-387, prompt=389+, budget speed-adjust=756-761, word_budget=822, _LEN_TOL=823.
- `tts_engine.py`: `_fit_duration`=243-281; `QC_DURATION_TOLERANCE`(0.15)=255; `TTS_ATEMPO_MIN/MAX`(0.80/1.25)=262-263. **Observability bocor**: durasi hanya ter-log saat atempo (mayoritas run tak tercatat).

### 5.2 Voice (4 sumber, voice_catalog orphan)
- Resolusi `elevenlabs.py:84-88`: `tts_voice_per_niche` → `tts_voice` → **map HARDCODE** (`elevenlabs.py:19-24`). Settings hardcode `:115-120`. Edge `edge_tts.py:22-47` & OpenAI `openai_tts.py:24-29` juga map hardcode.
- `voice_catalog` (voice_key, provider_key, display_name, locale, gender, niche_default, preview_url, is_active, sort_order) — **KOSONG & tak dibaca kode** (orphan). Admin CRUD ada (`admin/(panel)/catalog/page.tsx:27,123-145`).
- `niches` **belum punya `voice_key`**. Identitas ryan: `tenant_configs.tts_voice_per_niche.dark_history=VR6AewLTigWG4xSOukaG`.

### 5.3 Multi-channel (hasil audit) — ✅ yang sudah, ❌ yang belum
- ✅ per-channel: config-load channel-fields (`config.py:47`), producer iterasi semua channel (`producer.py:337-390,111-212`), publisher per-channel+timezone (`publisher.py:61-117`), analytics/self-learning per-channel (`self_learning.py:24-67`), FE list/create/edit channel (`channels/`), DB channel_id konsisten.
- ❌ **Config-fanout** (§4): voice/caption/hashtag/visual_mode/image_quality/music/quality masih per-tenant (`pipeline.py:65`).
- ❌ **channel_id NULLABLE** (verified DB) di `content_inventory`, `production_runs`, `video_analytics`, **`channel_insights`, `videos`(uuid)** — 5 tabel (legacy v1). `direct_jobs.channel_id`=NOT NULL. → perlu backfill + (opsi) NOT NULL.

### 5.4 Niche & Channel CRUD (FE/BE)
- **API admin niche SIAP**: GET+POST create (`api/admin/niches/route.ts:44,51`); PATCH allowlist memuat `visual_style, visual_fallbacks, mood_priority, voice_profile, emotion_scoring_criteria, section_timing, image_quality_tags, image_negative_prompt` (`[id]/route.ts:7-8`). **Belum ada `voice_key`** di allowlist.
- **Bug FE niche**: `admin/(panel)/niches/page.tsx` **tak ada tombol "Tambah niche"** (lahir cuma via approve request); drawer edit tak tampilkan `image_quality_tags/image_negative_prompt/visual_fallbacks/section_timing/voice_key` (JSON-textarea parsial & rapuh).
- **FE tenant config** `config/[tab]/page.tsx`: `Voice()`(:171) MOCK + simpan `tts_voice` via RPC `set_tenant_config`; Visual/Music/Captions/Hashtags/Quality wired ke `tenant_configs` via RPC `set_tenant_content_config`. → harus dipindah (Voice/Visual/Music→niche; Captions/Hashtags/operasional→channel).
- **Image-gen sudah LLM-driven** (`ai_image.py:5,213-222` `visual_suggestions`; `_build_image_prompt:308` bungkus DNA niche) — tak dirombak, hanya pastikan DNA mengalir.

### 5.5 Hardcode kritis (hasil audit BE) — eliminasi di fase pemiliknya
| Hardcode | file:baris | Target DB | Fase |
|---|---|---|---|
| Map voice per-niche (EL/edge/openai) | elevenlabs.py:19-24 · edge_tts.py:22-47 · openai_tts.py:24-29 | voice_catalog/niches.voice_key | F1 |
| Setting voice per-niche (speed/style/stability) | elevenlabs.py:115-120 | niches/tts_profiles | F1 |
| Ken Burns motion per-role/zoom | ai_image.py:417-463 | niches.motion_profiles (baru) | F5 |
| Speed-bounds [0.5,1.5] + WPS default 2.4 | script_engine.py:756,302 | tts_profiles | F4 |
| BASE_NICHE_TIERS {"trial","starter"} | billing/limits.py:59 | app_config | F5 |
| OPTIMAL_PUBLISH_SLOTS | tenant_config.py:82-88 | app_config | F5 |
| section_timing/beats/caption/hook-title/image-tags DEFAULT (fallback DB sudah ada) | script_engine.py:90,205 · video_renderer.py:27,144 · ai_image.py:26-35 | (sudah DB-driven; rapikan) | F5 |
| Video dims/codec 1080×1920/30/4000k | video_renderer.py:61-65 | format_profiles | F5 (opsional) |

### 5.6 Branded Content (disisipkan dari BRANDED_CONTENT_ARCHITECTURE.md)
- **DB ✅** (migr `0015_branded_content.sql`): kolom `channels`: `cta_mode`(def implicit), `brand_name`, `brand_cta_text`, `brand_logo`, `logo_position`(top-right), `logo_size`(0.12), `logo_opacity`(0.85), `landing_link`, `link_position`(bottom). + `format_profiles.default_cta_mode` (migr 0012).
- **BE ✅**: soft-sell CTA (`script_engine.py:285,355-356`), logo overlay (`video_renderer.py:937-941,1051-1063`, fail-soft, image_seq & ai_video), link deskripsi (`youtube_publisher.py:128,153-155`).
- **FE ❌** + **Storage logo ❌** (belum ada bucket; BE `_resolve_logo` terima URL http(s) → cukup upload→URL→`channels.brand_logo`).
- Semua opsional & nullable (default tanpa branding) → non-breaking.

---

## 6. ⚠️ RISIKO & PENJAGAAN
- **Jangan putus ryan**: voice VR6, OAuth, produksi. Uji ryan dulu tiap fase.
- **Titik paling berisiko = F1 (refactor fanout)** — semua produksi lewat config-load. Uji single-channel (ryan) identik SEBELUM multi-channel.
- **Migrasi/backfill** (F1): default aman, reversible, channel tertua sebagai target backfill.
- **VPS**: lokal→validasi→commit→push→pull+rebuild+restart. Doc ini di-exclude dari VPS (sparse-checkout).

---

## 7. 📋 FASE & ITEM (urut prioritas; tiap item = Plan vs Realisasi)
> Prioritas mengikuti arahan owner: **#4 pondasi multi-channel = PRIORITAS UTAMA** → FASE 1. Lalu CRUD yang membuka pondasi itu ke pengguna (FASE 2-3), baru Cacat B/LLM-conductor penuh (FASE 4), lalu sapu-bersih hardcode + go-live (FASE 5).
> **Catatan Cacat B:** relief cepat env-only (lebarkan `TTS_ATEMPO_MIN`, longgarkan `QC_DURATION_TOLERANCE`) BOLEH diterapkan kapan saja sebagai penambal sementara — tapi solusi tuntas (durasi-via-speed) ada di F4 (butuh voice/niche bersih dulu agar tak dikerjakan 2×).

---
### FASE 1 — TUNTASKAN PONDASI MULTI-CHANNEL + Voice single-source `[PRIORITAS UTAMA]`
*Sasaran fase: setelah ini, 1 tenant = banyak channel BENAR-BENAR independen (voice/caption/hashtag/visual/music/quality per-channel/niche), bukan berbagi per-tenant.*

#### [F1-01] voice_catalog jadi single-source + field baku TTS
- TUJUAN: satu sumber identitas voice; matikan 4-sumber ambigu.
- KENAPA: identitas voice tersebar (tenant_configs + map hardcode 3 file) → ambigu (§5.2).
- BUKTI: voice_catalog kosong/orphan; `elevenlabs.py:84,19-24`.
- PLAN: migr perkaya `voice_catalog` (+`age, accent, use_case, description, default_settings jsonb, language, tenant_id NULL=platform/terisi=BYOK`); `tts_profiles` +`param_schema jsonb` (param+rentang per provider). **→ skema field LENGKAP + alasan = §10.B (jangan re-derive).**
- DEPENDS: —
- DONE-BILA: `select` voice_catalog punya field baku; admin catalog FE bisa CRUD; query rentang param per provider tersedia.
- REALISASI: ✅ | commit: `6d3b662` | catatan: migr **0061** applied DB v2 (voice_catalog +age/accent/language/use_case/description/default_settings(jsonb)/tenant_id; tts_profiles +param_schema terisi el `{speed:[0.7,1.2],stability/style/similarity_boost:[0,1]}`/openai `{speed:[0.25,4.0]}`/edge `{rate,pitch,volume}`). Admin catalog route+form di-extend (whitelist + parse jsonb). **Catatan migr-nomor:** REMEDIASI lama tulis "s/d 0059"; nyata terakhir = 0060 → F1-01 = **0061**. `locale` existing dipertahankan, `language`=label manusiawi (§10.B "language/locale"). Validasi: build PASS · CRUD data-layer e2e (create+jsonb-object+toggle+delete) LULUS · voice_catalog tetap 0 row (NOL dampak ryan; BE belum baca s/d F1-03). **DEPLOYED:** pushed origin/v2-backend + VPS mv-web pull+rebuild(EXIT=0)+restart(active); `mesinviral.com`=200, `/admin/catalog`=307 (gate→/admin/login, benar). Worker tak tersentuh (route admin saja).

#### [F1-02] niches.voice_key (binding niche→1 voice) + seed
- TUJUAN: tiap niche tunjuk tepat 1 voice (branding, no-random).
- BUKTI: `niches` belum punya voice_key (§5.2).
- PLAN: migr `niches +voice_key` (FK voice_catalog, nullable); seed voice_catalog (ryan VR6 + platform voices); set `niches.dark_history.voice_key=VR6…`.
- DEPENDS: F1-01.
- DONE-BILA: tiap niche aktif punya voice_key valid; ryan dark_history→VR6.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F1-03] BE baca voice dari niche.voice_key→voice_catalog; buang map hardcode
- TUJUAN: produksi pakai single-source; hapus hardcode (§5.5).
- PLAN: `tts_engine`/`elevenlabs`/`edge`/`openai` resolve `niche.voice_key→voice_catalog`; hapus `ELEVENLABS_VOICES/NICHE_VOICES/OPENAI_VOICES` + DEFAULTS hardcode; `tts_voice_per_niche` jadi override BYOK opsional.
- DEPENDS: F1-02.
- DONE-BILA: produksi ryan pakai VR6 via voice_catalog (suara identik); tak ada map niche hardcoded tersisa (grep bersih).
- REALISASI: ⬜ | commit: — | catatan: —

#### [F1-04] Tambah kolom per-channel di `channels` (caption/hashtag/operasional)
- TUJUAN: pindahkan field brand-skin & operasional ke channel (§4).
- PLAN: migr `channels +caption_style jsonb, +niche_hashtags jsonb, +visual_mode, +image_quality, +music_enabled, +music_volume, +music_default_mood, +script_min_viral_score, +script_max_retry`; backfill dari `tenant_configs` → channel(s) tenant.
- DEPENDS: —
- DONE-BILA: kolom ada + ter-backfill; ryan channel terisi nilai lama.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F1-05] Refactor config-fanout: thread field per-channel ke pipeline
- TUJUAN: pipeline baca caption/hashtag/visual_mode/image_quality/music/quality dari CHANNEL (bukan tenant); voice dari NICHE.
- BUKTI: `pipeline.py:65` muat per-tenant; `config.py:47-68` TenantConfig lean.
- PLAN: tambah field ke `TenantConfig` + isi di `tenant_config_from_channel` dari channel_row; pipeline/tts_engine/video_renderer/script_engine baca dari objek per-channel (caption/visual/music/quality) & dari niche (voice); `TenantRunConfig` tetap untuk field tenant sejati (LLM/BYOK/plan).
- DEPENDS: F1-03, F1-04.
- DONE-BILA: tenant uji 2-channel beda caption/voice/visual_mode → output beda, tak saling timpa; ryan (1ch) identik perilaku.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F1-06] Backfill channel_id NULLABLE (5 tabel)
- TUJUAN: tutup gap legacy v1 null.
- BUKTI: **verified DB** — nullable di `content_inventory, production_runs, video_analytics, channel_insights, videos`; `direct_jobs`=NOT NULL.
- PLAN: backfill NULL→channel tenant (via join videos.run_id / channel tertua tenant); (opsi) ALTER NOT NULL per tabel bila aman (hati-hati `videos.channel_id` FK uuid).
- DEPENDS: —
- DONE-BILA: 0 baris channel_id NULL untuk tenant aktif; query per-channel akurat.
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 2 — CHANNEL CRUD + child (FE/BE tenant) `[buka pondasi ke pengguna]`
#### [F2-01] Channel CRUD lengkap + entitlement kuota
- PLAN: FE create/read/update/delete channel; enforce `plan_limits.max_channels`; RLS `tenant_id=auth.uid()`.
- DEPENDS: F1-05.
- DONE-BILA: CRUD jalan + kuota + RLS teruji; tak bocor antar-tenant.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-02] Pindah tab Captions + Hashtags → `/channels/[id]` (per-channel)
- PLAN: tab caption-style & hashtags baca/tulis kolom `channels` (F1-04) via RLS UPDATE; buang dari `config/[tab]` tenant.
- DEPENDS: F1-04, F2-01.
- DONE-BILA: 2 channel beda caption/hashtag tersimpan terpisah & terpakai produksi.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-03] Tab knob operasional per-channel (visual_mode/image_quality/music/quality-gate)
- PLAN: pindah Visual(mode/quality)+Music(on/volume/mood)+Quality-gate dari config tenant → `/channels/[id]`.
- DEPENDS: F1-04, F1-05, F2-01.
- DONE-BILA: tersimpan per-channel + terpakai produksi.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-04] Panel "Branded" per-channel (CTA/logo/landing) + storage logo `[dari branded-content doc]`
- KENAPA: DB+BE branded SUDAH jadi (§5.6), hanya FE+storage kurang.
- PLAN: tab Branded di `/channels/[id]`: CTA radio implicit|soft_sell (+brand_name/cta_text); upload logo→bucket→URL ke `brand_logo` + pemilih posisi(4 sudut)+slider size/opacity+preview 9:16; landing_link + posisi top/bottom. Tulis via RLS UPDATE channels. Buat bucket/route upload logo.
- DEPENDS: F2-01.
- DONE-BILA: tenant set CTA/logo/landing dari UI; video produksi menampilkannya; logo tersimpan & ter-overlay.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-05] Buang tab Voice/Visual-style/Music-DNA dari config tenant
- PLAN: hapus tab Voice (mock) + bagian visual-style/music yang DNA dari `config/[tab]` tenant (pindah ke niche, FASE 3). Sisakan AI-keys/Notifikasi/plan di tenant.
- DEPENDS: F3 (niche editor siap menampung DNA).
- DONE-BILA: config tenant hanya berisi item milik tenant; tak ada config DNA di tenant.
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 3 — NICHE CRUD + child (admin + Business) `[authoring DNA]`
#### [F3-01] Tombol "Tambah niche" di admin (API sudah ada)
- BUKTI: POST `niches/route.ts:44` SIAP; FE tak ada tombol (§5.4).
- PLAN: tambah form create niche di `admin/(panel)/niches` → POST.
- DONE-BILA: admin buat niche baru dari UI; tercatat audit.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F3-02] Lengkapi editor niche (field hilang + voice_key selector)
- PLAN: drawer tampil `image_quality_tags, image_negative_prompt, visual_fallbacks, section_timing` (API allow) + **selector `voice_key`** dari voice_catalog; ganti JSON-textarea rapuh→form terstruktur; tambah `voice_key` ke allowlist PATCH (`[id]/route.ts:7-8`).
- DEPENDS: F1-01/02.
- DONE-BILA: semua field DNA bisa di-edit aman; voice_key tersimpan & terbaca pipeline.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F3-03] Business niche-studio (clone admin, scoped private)
- PLAN: halaman kelola-niche untuk tier Business (clone UI admin niches), niche dibuat `access_type=private, exclusive_to=tenant_id`; gating `plan_type='business'`; Entry/Pro tetap request.
- DEPENDS: F3-01/02.
- DONE-BILA: Business buat+edit niche private (tak terlihat tenant lain); Entry/Pro tak punya akses create.
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 4 — Cacat B tuntas + LLM-as-conductor `[kualitas konten]`
#### [F4-01] Observability TTS — tabel `tts_delivery_samples`
- PLAN: tabel (provider, voice_key, speed, words, audio_secs, preset, ts) + log tiap render. Pondasi kalibrasi pace.
- DONE-BILA: tiap produksi menulis 1 baris sample.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F4-02] Prompt durasi-via-speed (buang length_block kaku)
- PLAN: ganti `length_block`(370-387)+pemaksaan `total_words`(304/315) → blok speed/durasi (LLM pilih words+speed, self-check); pertahankan beat_plan + segmentasi (per-beat jadi PROPORSI); inject pace P (seed `tts_profiles`, base ~1.97). Kontrak JSON +`tts_params{speed,voice_key,stability,style}` +`_duration_check{word_count,est_seconds}`. **→ PROMPT BLOCK persis + matematika penyerapan-speed + contoh dark_history = §10.A (verbatim, JANGAN re-design).**
- DEPENDS: F1-03 (voice_key bersih).
- DONE-BILA: ryan 30s & 60s lolos band; durasi terpusat; mutu naik.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F4-03] TTS pakai tts_params + jaring (atempo+gate Shorts) + buang hardcode wps/speed-bounds
- PLAN: `tts_engine` pakai `speed` dari naskah (override static `:758`); lebarkan atempo band; gate Shorts-valid (cap ≤ limit Shorts); buang WPS-default-2.4 & speed-bounds-[0.5,1.5] hardcode (§5.5).
- DEPENDS: F4-02.
- DONE-BILA: produksi multi-preset lolos; tak ada hardcode wps/speed-bounds.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F4-04] Prompt konduktor penuh (niche DNA → 3 konsumen)
- PLAN: inject niche DNA penuh (voice_profile, emotion_scoring, mood, keywords) + voice_key + param_schema; satu JSON: narasi + tts_params + visual_suggestions. Speed lahir dari mood niche, dinudge utk durasi. **→ prinsip konduktor + pemetaan 1-JSON→3-konsumen = §10.C.**
- DEPENDS: F4-02/03, F3-02.
- DONE-BILA: konten lintas niche kualitas tinggi + 3 konsumen tergerakkan dari 1 JSON.
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 5 — Sapu hardcode sisa + kalibrasi + go-live checklist
#### [F5-01] Kalibrasi pace P otomatis (closed-loop)
- PLAN: hitung wps efektif per voice_key×speed dari `tts_delivery_samples` (EWMA) → ganti seed 1.97.
- DEPENDS: F4-01 (data terkumpul).
- DONE-BILA: pace per-voice ter-update dari data nyata; durasi makin presisi.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F5-02] Eliminasi hardcode sisa
- PLAN: Ken Burns motion → `niches.motion_profiles` (ai_image.py:417-463); `BASE_NICHE_TIERS`+`OPTIMAL_PUBLISH_SLOTS` → app_config; (opsi) video dims/codec → format_profiles; rapikan DEFAULT section_timing/caption/image-tags (pastikan DB-driven).
- DONE-BILA: grep hardcode kritis bersih; semua config-driven.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F5-03] /compliance per-channel + cost-tracking live (gap audit)
- PLAN: `/compliance` tampil per-channel (data di `channel_insights.compliance`); worker catat `run_metadata.cost_usd`; FE kartu Biaya AI aggregate per-channel.
- DONE-BILA: compliance & biaya tampil per-channel nyata (bukan mock/coming-soon).
- REALISASI: ⬜ | commit: — | catatan: —

#### [F5-04] Go-live checklist: regression + regenerate DB_SCHEMA_V2.md + bersih dok
- PLAN: regression end-to-end semua preset×beberapa niche×multi-channel; regenerate `DB_SCHEMA_V2.md` (stale di 0043); pastikan ryan stabil. *(`BRANDED_CONTENT_ARCHITECTURE.md` sudah di-merge ke §5.6/F2-04 & DIHAPUS 2026-06-20.)*
- DONE-BILA: semua hijau; siap go-live + go-market.
- REALISASI: ⬜ | commit: — | catatan: —

---

## 8. 🔜 LANGKAH SETELAH SELURUH FASE (1–5) TUNTAS → Onboarding Funnel
> **Gerbang ke go-market.** Begitu FASE 1–5 di dokumen ini **terealisasi & tervalidasi** (semua item REALISASI = ✅), langkah berikutnya:
> 1. **Selaraskan `ONBOARDING_FUNNEL_PLAN.md`** dengan HASIL NYATA dokumen ini — karena onboarding bersinggungan langsung dengan struktur final: tenant→**multi-channel** (CRUD), pemilihan **niche** (DNA, voice per-niche), **brand-skin per-channel** (caption/hashtag/branded), **BYOK + OAuth per-channel**, tier (Entry/Pro/Business + Business niche-studio). Banyak asumsi lama di funnel plan bisa berubah setelah remediasi (mis. cara user pilih niche/voice, set channel pertama, BYO-CC). **Funnel plan WAJIB di-update agar konsisten — bukan dibangun di atas struktur lama.**
> 2. **Buat Plan vs Realisasi** untuk menuntaskan onboarding funnel (format sama dengan dokumen ini: item self-contained + DONE-BILA + kolom REALISASI), sebagai dokumen lanjutan ATAU FASE 6 di sini (diputuskan saat itu).
> 3. Prinsip funnel tetap: "pikat dulu, todong belakangan" (lihat `ONBOARDING_FUNNEL_PLAN.md`), kini disesuaikan dengan kapabilitas multi-channel/niche/brand-skin yang sudah jadi.
>
> **Catatan:** JANGAN mengerjakan onboarding funnel sebelum FASE 1–5 tuntas — agar funnel dibangun di atas fondasi yang sudah benar (hindari rework). Item ini = penanda arah, belum aktif.

---

## 9. 🧾 LOG PROGRES (append-only)
- **2026-06-20 (a)**: Dokumen final dibuat. Audit BE-hardcode + multi-channel SELESAI (terverifikasi langsung). **Temuan kunci: pondasi multi-channel BELUM tuntas** — config-fanout voice/caption/hashtag/visual/music/quality masih per-tenant (`pipeline.py:65`) → FASE 1 = prioritas utama. Keputusan operasional→channel & Business-niche→private dikunci.
- **2026-06-20 (b)**: PROGRESS.md direkonsiliasi (banner: pending teknis → remediasi; PROGRESS = arsip+gate ops/eksternal). `BRANDED_CONTENT_ARCHITECTURE.md` di-merge ke §5.6/F2-04 lalu **DIHAPUS** (link di PROGRESS dialihkan; nol link putus).
- **2026-06-20 (c)**: Ditambah **§10 LAMPIRAN desain-disepakati** (prompt durasi-via-speed + skema voice + konduktor + data wps) supaya sesi baru TAK re-derive/asumsi. Belum ada kode produksi disentuh. **Berikutnya: F1-01.**
- **2026-06-20 (d)**: ✅ **F1-01 SELESAI** (commit `6d3b662`, migr **0061** applied DB v2). voice_catalog diperkaya field baku §10.B + tts_profiles.param_schema; admin catalog route+form extended (whitelist + parse jsonb). Validasi: build PASS + CRUD data-layer e2e LULUS + voice_catalog 0 row (nol dampak ryan). **Migr nyata terakhir = 0061** (doc lama "0059" tertinggal; F1-01 ambil 0061 karena 0060=channel_credentials sudah ada). **Berikutnya: F1-02** (niches.voice_key + seed VR6 ryan).

---

## 10. 📐 LAMPIRAN — DESAIN SOLUSI YANG SUDAH DISEPAKATI (verbatim — JANGAN re-derive/asumsi)
> Hasil diskusi penuh 2026-06-19/20. Item FASE menunjuk ke sini untuk "BAGAIMANA persisnya". Bila ragu → ikuti ini apa adanya, jangan rancang ulang.

### 10.A — Durasi-via-speed (untuk F4-02, F4-03)
**Akar (data §5.1):** budget pakai ~1.55–1.62 wps, padahal delivery NYATA 1.86–2.0 → LLM mematuhi jumlah-kata yang SALAH → audio sistematis pendek. Prompt tak pernah salah; KONSTANTA wps-nya yang salah → berhenti tuning prompt; beri LLM 2 tuas.
**Insight kunci:** LLM kontrol **words + speed** sekaligus. Alur: (1) pilih base-speed sesuai mood niche; (2) tulis naskah natural per beat; (3) HITUNG kata sendiri (W); (4) NUDGE speed dalam [0.7,1.2] agar `W ÷ (P×speed) ≈ T_spoken`. **Speed MENYERAP error hitung-kata.** Untuk 60s (T_spoken≈56.5s, P≈1.97): W boleh **77–132 kata** & tetap mendarat → sebaran gagal lama (72–115) hampir seluruhnya tertutup. LLM tak perlu presisi kata.
**Beat-plan TETAP** (N beat = visual_beats = scene = QC clip), tapi per-beat = **PROPORSI %** (bukan kata absolut — absolut lama = bias wps salah). `T_spoken = preset − overhead-render (trailing_silence + loop net)`.
**PROMPT BLOCK (drop-in, ganti `length_block` 370-387; bhs prompt = English):**
```
📐 BEAT PLAN — {T}s video = {N} BEATS (compression-mapping, non-negotiable):
{narrative_intent}
Write EXACTLY these {N} beats IN ORDER — keep their relative weight:
   beat 1 — {ROLE} (~{p1}% ...)   ...   (inactive JSON fields → "")

🎙️ THIS SCRIPT WILL BE SPOKEN — you control BOTH the words and the pace.
VOICE: {voice_name} ({provider}) speaks ≈{P} words/sec at speed 1.0.
Set `speed` ∈ [0.7,1.2] to match the mood of {niche}/{topic}
(somber/dramatic→~0.85, punchy/urgent→~1.05, neutral→~0.95).
The {N} beats TOGETHER must last ≈{T}s (acceptable {T_lo}–{T_hi}s), keeping proportions.
 1. Pick a mood-fitting base speed.
 2. Write the {N} beats naturally — STORY FIRST.
 3. Count words W. Spoken ≈ W ÷ ({P} × speed).
 4. PREFER nudging `speed` within [0.7,1.2] to fit your actual W; rewrite length only if speed can't reach {T_lo}–{T_hi}s.
 5. Report word_count + est_seconds; confirm in range.
Words serve the story; speed makes it land on time.
```
**Kontrak JSON output (+):** `"tts_params":{voice_key,speed:0.7–1.2,stability,style}` · `"_duration_check":{word_count,est_seconds}`. Server validasi/clamp ke param_schema (§10.B). `_duration_check` = paksa chain-of-thought → akurasi count LLM naik.
**Contoh terisi (dark_history @30s, nilai NYATA DB):** beats=[hook,core_facts,cta] proporsi ~14/72/14%; P≈1.97; base speed 0.83 (mood somber niche, dari `tts_voice_settings`); T_spoken≈26.5s; band ~24–29s; ≈43 kata. Semua var dari config niche (no-hardcode).
**Jaring (F4-03):** lebarkan `TTS_ATEMPO_MIN/MAX` (env) + gate QC durasi → **Shorts-valid** (cap ≤ batas Shorts; hard-fail hanya ekstrem); STOP paksa durasi-tepat; buang hardcode WPS-2.4 & speed-bounds-[0.5,1.5].

### 10.B — Skema Voice baku (untuk F1-01/02/03, F3-02)
**Prinsip (disepakati):** IDENTITAS voice (voice_key/gender/timbre) = **stabil per niche** (branding; TTS butuh voice_key nyata, LLM TAK bisa mengarang voice). DELIVERY (speed/style/stability) = **LLM setel per-naskah**. Rotasi voice **default OFF**. "LLM memilih voice" hanya sekali saat setup niche (rekomendasi), bukan per-video.
**`voice_catalog` (field = label baku ElevenLabs, portabel):** `voice_key`(PK) · `provider_key` · `display_name` · `gender` · `age` · `accent` · `language`/`locale` · `use_case` · `description` · `default_settings jsonb`{stability,similarity_boost,style,speed} · `preview_url` · `tenant_id`(NULL=platform/terisi=BYOK) · `is_active` · `sort_order`.
**`tts_profiles.param_schema jsonb` (rentang valid/provider):** elevenlabs `{speed:[0.7,1.2],stability:[0,1],style:[0,1],similarity_boost:[0,1]}` · openai_tts `{speed:[0.25,4.0]}` · edge_tts `{rate,pitch,volume}`.
**`niches.voice_key`** (FK→voice_catalog) = binding 1-voice-per-niche.
**tts_params yang LLM serahkan ke TTS (TTS tinggal eksekusi):** `{voice_key (default=niche.voice_key), speed, style, stability, similarity_boost}`.

### 10.C — LLM-as-conductor (untuk F4-04)
Orchestrator meramu **1 prompt dinamis** (per preset×niche×voice×pace), semua var dari **config niche** (no-hardcode). LLM balas **1 JSON** = partitur **3 konsumen**: (1) **`beats`**→narasi→TTS · (2) **`tts_params`**(voice+delivery §10.B)→TTS eksekusi · (3) **`visual_suggestions`**(prompt per-scene buatan LLM, `ai_image.py:213`)→image-gen, dibungkus DNA visual niche (`_build_image_prompt:308`). Niche menyuntik "jiwa": `voice_profile`+`emotion_scoring_criteria`(quality-bar 80+)+`mood_priority`+`keywords`+`style`.

### 10.D — Data wps terukur (justifikasi seed P — jangan re-derive)
| sumber | kata | audio | speed | wps efektif | base(÷speed) |
|---|---|---|---|---|---|
| V1 log | 189 | 111.5s | 0.86 | 1.695 | **1.97** |
| V2 log | 88 | 46.0s | 0.86 | 1.91 | 2.22 |
| V2 log | 92 | 46.0s | 0.86 | 2.00 | 2.33 |
| V2 log | 83 | 44.7s | 0.86 | 1.86 | 2.16 |
| V2 log | 72 | 38.0s | 0.86 | 1.90 | 2.20 |

Budget DIPAKAI mesin: 1.548–1.674 (terlalu rendah). **Kesimpulan:** tak ada satu konstanta wps benar (variansi intrinsik per konten) → (1) seed **P≈1.97** = INFO acuan ke LLM (bukan rumus paksa), (2) **speed = tuas penyerap** variansi, (3) self-calibrate per `voice_key×speed` dari `tts_delivery_samples` (F5-01). Observability bocor (durasi hanya ter-log saat atempo) → F4-01 menutupnya.
