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
3. Tiap item punya: TUJUAN · KENAPA · BUKTI · PLAN · DEPENDS · DONE-BILA · REALISASI. Kerjakan sesuai PLAN, validasi sesuai DONE-BILA, isi REALISASI (status+commit). **Item LLM/voice/arsitektur (F1-03/04/05/07/08, F2-01/03, F3-02, F4-02/03/04) menunjuk ke §10 LAMPIRAN — desain SUDAH DISEPAKATI: §10.A durasi-via-speed · §10.B voice (Opsi 2) · §10.C konduktor · §10.E multi-AI-model + channel setup + gerbang aktivasi. IKUTI §10 apa adanya — jangan rancang ulang / berasumsi.**
4. Aturan kerja: lokal → validasi 100% → commit → push → pull+rebuild+restart di VPS. JANGAN ngoding di VPS. JANGAN rusak produksi ryan. Validasi tiap fase sebelum lanjut.
5. **Status global (update 2026-06-20):** ✅ **F1-01** (migr 0061) · ✅ **F1-02** (migr 0062). **Arsitektur FINAL sudah dibungkus** (owner 2026-06-20): multi-AI-model per-elemen (tenant pilih, admin kurasi) · voice **Opsi 2** (default niche per TTS model + pilihan tenant per-channel + **test/preview**) · **TIDAK ada fallback** · channel default non-aktif + **gerbang aktivasi** · caption-styling+hashtag+model+voice = channel · credential per-tenant dipakai-ulang · niche-create gating config-driven. Acuan = §3 (kpts 3-11) + §4 + **§10.B/§10.E**. ✅ **F1-07** (0063) · ✅ **F1-04** (0064) · ✅ **F1-05** (`7a5d030`+0065, deployed; render-level monitor produksi ryan berikutnya) — jahitan tunggal channel-aware + voice single-source + NO-FALLBACK; ryan IDENTIK (config+provider tervalidasi). **Item berikutnya = F1-08** (gerbang aktivasi `channel_readiness` + guard producer + is_active default false). **F1-06 = independen**. Migr nyata terakhir = **0065**. **Urutan FASE 1:** F1-07→F1-04→F1-05→**F1-08**; F1-06 kapan saja. *(Catatan: F1-05 render-level belum dikonfirmasi via produksi nyata — admin_te tak ber-creds; tunggu produksi ryan berikutnya / direct-test.)* Kunci re-evaluasi: F1-03 dilebur ke F1-05 karena semua config per-channel lewat SATU jahitan (`load_tenant_config` di 8 komponen) → hindari sentuh 8 file dua kali. DB-additive (F1-07/04) dulu (nol-risiko spt F1-01/02), baru pembedahan produksi (F1-05). Migr nyata terakhir = **0062**.

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
3. **Voice = Opsi 2 (owner 2026-06-20):** voice milik tiap **TTS model**; admin sediakan voice per TTS model (`voice_catalog`, per `provider_key`). **NICHE memberi voice DEFAULT per TTS model** (DNA/branding); **TENANT memilih TTS model lalu voice saat konfigurasi CHANNEL** (default niche ter-pra-isi, boleh diganti — hak prerogatif tenant). Pilihan final = `channels`. Tanpa voice random; LLM hanya setel DELIVERY per-naskah. **FE WAJIB fasilitas TEST/PREVIEW voice** (dengar sampel sebelum pilih). Detail §10.B + §10.E.
4. **NICHE = DNA** · **CHANNEL = brand skin + knob operasional/biaya + pilihan AI-model & voice** · **TENANT = akun (plan/billing/BYOK keys/notifikasi)**. (Caption+hashtag = channel; visual STYLE & mood-musik = niche; visual_mode/image_quality/music-on-off/volume/quality-gate + model-per-elemen + voice = channel.)
5. **Niche dibuat hanya di:** admin panel, atau tenant **Business** (niche-studio = clone UI admin, **PRIVATE eksklusif** `access_type=private, exclusive_to=tenant_id`). Entry/Pro: pakai niche ada / request via `niche_requests`. **Gating "siapa boleh buat niche" = config-driven** (`app_config`, default `business` + admin; extensible ke Pro tanpa ubah kode). Saat pilih niche di channel-config, list = **semua niche platform + niche custom milik tenant** (`entitled_niches`).
6. **`voice_catalog`/`tts_profiles` field = parameter TTS baku** (portabel lintas provider).
7. **Multi-AI-model per elemen (owner 2026-06-20).** Tiap elemen produksi punya **AI model yang dipilih TENANT per-CHANNEL** dari katalog **yang diaktifkan admin** — biaya produksi = hak prerogatif tenant. Elemen ber-model: **LLM (skrip), image-gen (visual), TTS (voice), video-gen (preset ai_video)**. Admin/dev = **gerbang dukungan**: model baru `is_active` HANYA setelah parameter API-nya terverifikasi didukung (extensible, mis. Fish Audio). Param bisa beda per model → ditampung `ai_providers.adapter`/`request_param_schema` + `ai_models.default_params` + `tts_profiles.param_schema`. Detail §10.E.
8. **TIDAK ADA FALLBACK.** Produksi pakai HANYA model/provider/credential terkonfigurasi; gagal runtime = **gagal jujur + tercatat**, tak pindah provider diam-diam.
9. **Channel default NON-AKTIF + gerbang aktivasi.** Channel `is_active=true` HANYA bila semua syarat (niche, model tiap elemen, voice, credential valid, YouTube OAuth) lengkap & valid. Boleh **save draft** sebelum lengkap. UX **ramah pemula** (checklist sisa). Detail §10.E.
10. **Credential (BYOK key) = per-TENANT, dipakai-ulang** lintas channel (1 key/provider, ramah pemula), divalidasi (test koneksi). YouTube OAuth = per-channel (sudah).
11. **Caption = styling subtitle ON-SCREEN** (font, ukuran, posisi, warna, highlight, outline, dll — `caption_style`) **+ hashtag = CHANNEL** (diatur tenant). Bukan judul/deskripsi YouTube.

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
| **voice (pilihan final)** | tenant_configs + map HARDCODE | tenant ❌ | **CHANNEL** (`channels.voice_key`; default dari niche per TTS model) | channels.voice_key + niche default per model |
| **AI model per elemen** (llm/image/tts/video) | llm=tenant_configs · image/tts=hardcode | tenant/hardcode ❌ | **CHANNEL** (pilih dari katalog `ai_models` aktif) | + kolom channels (model per elemen) + adapter config-driven |
| **visual_mode, image_quality** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **music_enabled, music_volume, music_default_mood** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| **script_min_viral_score, script_max_retry** | tenant_configs | tenant ❌ | **CHANNEL** | + kolom channels + thread |
| visual_style, image_quality_tags, image_negative_prompt, mood_priority, section_timing, emotion_scoring_criteria, voice_profile, **motion_profiles(baru)** | niches | niche ✅ (motion belum) | niche | + motion_profiles |
| *_api_key_enc (BYOK keys), plan_type, subscription_status, telegram_*, timezone, videos_per_day | tenant_configs | tenant ✅ | tenant (key dipakai-ulang lintas channel, divalidasi) | — |
| llm_provider/model/library | tenant_configs | tenant ❌ | **CHANNEL** (pilih per channel) | pindah ke channels (model-per-elemen) |

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
- `voice_catalog` ~~KOSONG & orphan~~ → **✅ F1-01/02: diperkaya field baku + diisi 4 voice EL platform** (masih belum dibaca BE s/d F1-03). Admin CRUD (`catalog/page.tsx`).
- `niches` ~~belum punya voice_key~~ → **✅ F1-02: ADA `voice_key`** (default EL per niche; diperluas jadi `voice_defaults` per provider di F1-07, §10.B). Identitas ryan: `tenant_configs.tts_voice_per_niche.dark_history=VR6AewLTigWG4xSOukaG` (delivery override tetap).

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
### FASE 1 — TUNTASKAN PONDASI MULTI-CHANNEL + Multi-AI-model + Voice (Opsi 2) `[PRIORITAS UTAMA]`
*Sasaran fase: setelah ini, 1 tenant = banyak channel BENAR-BENAR independen — voice/caption/hashtag/visual/music/quality + **AI-model per elemen (LLM/image/TTS/video)** per-channel; pipeline **config-driven multi-model (no-hardcode, no-fallback)**; voice = default niche + pilihan tenant per-channel. Acuan arsitektur = §10.E.*

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
- REALISASI: ✅ | commit: `72d5e51` | catatan: migr **0062** applied DB v2. Seed voice_catalog 4 voice EL platform (Adam/Rachel/Arnold/Bella, `default_settings`=BASELINE BE DEFAULTS) + `niches.voice_key` (nullable, FK→voice_catalog on-update-cascade/on-delete-set-null). Binding: dark_history→VR6(Arnold), universe→pNInz(Adam), fun_facts→21m00(Rachel), ocean→EXAVITQu(Bella). Validasi: 4 niche aktif voice_key valid (join non-null) · dark_history→VR6 · FK ada · `tenant_configs` TAK tersentuh (ryan per_niche=VR6 + settings.speed=0.86 utuh) → NOL dampak ryan (BE belum baca s/d F1-03).
- 🔄 **PENYESUAIAN ARSITEKTUR (Opsi 2, owner 2026-06-20):** `niche.voice_key` (1 voice) = **default ElevenLabs** saja. Akan **diperluas jadi `niches.voice_defaults jsonb` per provider** (EL/edge/openai dari map lama → DATA terkurasi) di **F1-07**, karena voice mengikuti TTS model pilihan tenant (§10.B/§10.E). Voice FINAL = `channels.voice_key` (F1-04). Seed F1-02 tidak terbuang (jadi entri EL di voice_defaults).

#### [F1-07] Multi-AI-model BE-ready: katalog TTS/video + `niches.voice_defaults` + audit adapter `[NEW — owner 2026-06-20]`
- ⚠️ **KONFIRMASI OWNER sebelum sentuh BE** (perubahan perilaku produksi). Arsitektur = §10.E.
- TUJUAN: BE+DB siap arsitektur multi-AI-model (param beda per model), pondasi F1-03/05.
- PLAN: (a) migr: tambah model **TTS & video** ke `ai_models` (`component='tts'/'video'`) untuk provider aktif (EL/openai/edge; video=kosong dulu) + `niches.voice_defaults jsonb` (per provider, isi dari map lama EL/edge/openai). (b) Audit pipeline tiap elemen (LLM/image/TTS) → pastikan pemilihan model/provider **config-driven via adapter** (`ai_providers.adapter`), bukan if-else hardcode. (c) Petakan elemen→param via `default_params`/`param_schema`.
- DEPENDS: F1-02.
- DONE-BILA: katalog punya model utk tiap elemen aktif; `niches.voice_defaults` terisi; audit BE terdokumentasi (mana config-driven, mana sisa hardcode→F1-03/F5).
- REALISASI: ✅ | commit: `9dd8b64` | catatan: migr **0063** applied. **Keputusan audit (verified, koreksi rencana lama):** opsi TTS = **`tts_profiles`** (registry existing + `param_schema` + `delivery_wps`) + voice = `voice_catalog`, **BUKAN** `ai_models` (sebab `ai_models.provider_key` FK→`ai_providers` ON DELETE RESTRICT, dan ai_providers LLM-adapter-centric: anthropic_messages/openai_chat/replicate). video → ai_models saat ai_video dibangun (ditunda; component='video' tak ada CHECK, taksonomi siap). **Dikerjakan:** voice_catalog +6 voice (edge GuyNeural/JennyNeural/ChristopherNeural + openai onyx/nova/fable) → **10 voice**; `niches.voice_defaults jsonb` {provider:voice_key} per niche (dari map lama; **100% ref valid** ke voice_catalog); `tts_profiles.display_name`; `get_niches()` expose `voice_key`+`voice_defaults`. **Audit adapter:** LLM=`build_llm_provider` katalog+adapter BERSIH (DB-driven); **TTS**=`get_tts_provider` dict hardcode + map voice hardcode (3 file); **image**=`get_visual_provider` if-else → semua dibereskan di **F1-05**. Fanout terverifikasi: 8 komponen panggil `load_tenant_config(tenant_id)` sendiri. Validasi: migr applied · voice_defaults ref valid · py_compile OK · get_niches 4/4 niche expose voice. NOL dampak runtime (BE belum konsumsi voice_defaults; map hardcode masih jalan s/d F1-05). **DEPLOY:** menyusul (mv-worker pull+restart — config.py additive non-breaking).

#### [F1-03] ~~BE resolusi model+voice~~ → **DIGABUNG ke F1-05** (re-evaluasi 2026-06-20)
- 🔁 **MERGED.** Studi mendalam jalur produksi membuktikan: SEMUA pilihan model/voice/caption/visual datang dari **satu jahitan** — tiap komponen memanggil sendiri `load_tenant_config(tenant_id)` (8 file: tts_engine/script_engine/hook_optimizer/niche_selector/visual_assembler/video_renderer/youtube_publisher). Memisah voice (F1-03) dari caption/visual/music (F1-05) = menyentuh 8 file SAMA **dua kali** (boros + risiko regresi ganda di produksi live). → Voice-resolution + no-fallback + buang-hardcode **dilebur** ke **F1-05** (satu pass). Lihat F1-05.

#### [F1-04] Tambah kolom per-channel di `channels` (model-per-elemen + voice + caption/hashtag/operasional)
- TUJUAN: pindahkan pilihan AI-model, voice, brand-skin & operasional ke channel (§4/§10.E).
- PLAN: migr `channels +llm_model, +image_model, +tts_provider, +tts_model, +video_model` (FK/ref `ai_models`), `+voice_key` (ref `voice_catalog`), `+caption_style jsonb, +niche_hashtags jsonb, +visual_mode, +image_quality, +music_enabled, +music_volume, +music_default_mood, +script_min_viral_score, +script_max_retry`; backfill dari `tenant_configs`/default niche → channel(s) tenant (ryan: voice_key=VR6, model EL/gpt-image/llm lama).
- DEPENDS: F1-07.
- DONE-BILA: kolom ada + ter-backfill; ryan channel terisi nilai lama (voice+model identik perilaku).
- REALISASI: ✅ | commit: `a16010c` | catatan: migr **0064** applied. **14 kolom** ditambah ke `channels`: llm_model/llm_library, tts_provider/tts_model/**voice_key**(FK voice_catalog), visual_mode/image_quality, caption_style/niche_hashtags(jsonb), music_enabled/volume/default_mood, script_min_viral_score/max_retry. **Refinement (audit kode):** TANPA `image_model`/`video_model` terpisah — `visual_mode` sudah encode mode+model (`ai_image:gpt-image-1-mini`); video → `visual_mode='ai_video:*'` saat dibangun. Backfill dari `tenant_configs` → **2 channel**: **ryan** (a410251c, SATU-SATUNYA tenant nyata) + **admin_te** (`admin_test_internal` = channel INTERNAL ADMIN, direct-only test — **BUKAN tenant**; admin ≠ tenant, panel terpisah). 3 tenant lain = trial onboarding belum aktif (tanpa channel). **voice_key = NULL** (kedua channel) → voice di-resolve per-niche via `niches.voice_defaults[tts_provider]` = **perilaku sekarang persis** (ryan random multi-niche tak bisa 1 voice tunggal). Validasi: backfill ryan == tenant_configs (llm/tts/visual/qc cocok True) · voice_key NULL · FK voice_catalog ada. NOL dampak runtime (BE belum baca s/d F1-05). DB-only → tak perlu deploy worker.

#### [F1-05] ⭐ JAHITAN TUNGGAL: config per-channel via channel-aware loader + resolusi voice + NO-FALLBACK (gabungan F1-03+F1-05)
- ⚠️ **GERBANG KERAS: KONFIRMASI OWNER DULU** — ini SATU-SATUNYA pembedahan jalur produksi live di FASE 1 (paling berisiko). Propose + uji-regresi ryan sebelum & sesudah.
- 🔴 **TEMUAN (verified):** semua komponen panggil `load_tenant_config(tenant_id)` (per-tenant) → di situlah model/provider/voice/keys diambil. `TenantConfig` (per-channel) yang dioper hanya bawa niche/branded/preset. Plus: semua tenant punya `tts_voice_per_niche` identik (pseudo-default duplikat hardcode); override ASLI ryan = `tts_voice_settings` (delivery speed, WAJIB dipertahankan).
- TUJUAN: produksi baca **model-per-elemen + voice + caption/hashtag/visual_mode/image_quality/music/quality dari CHANNEL**; credential (key) dari tenant; DNA dari niche. **NO FALLBACK.**
- PLAN (satu pass, intervensi TERPUSAT — bukan tulis-ulang 8 file):
  1. **Jadikan `load_tenant_config(tenant_id, channel_id=None)` channel-aware**: overlay kolom `channels` (F1-04: model-per-elemen, voice_key, caption_style, niche_hashtags, visual_mode, image_quality, music_*, script_min_viral_score/max_retry) DI ATAS `TenantRunConfig` per-tenant (key BYOK & plan tetap dari tenant).
  2. **8 call-site** oper `tenant_config.channel_id` ke loader (tts_engine:62, script_engine:514, hook_optimizer:235, niche_selector:610/794, visual_assembler:386, video_renderer:133/160/795/911/930, youtube_publisher:110).
  3. **Resolusi voice**: `channels.voice_key` → (kosong) `niches.voice_defaults[channel.tts_provider]`. Provider/model TTS/LLM/image dari channel.
  4. **Buang hardcode + FALLBACK**: hapus `ELEVENLABS_VOICES/NICHE_VOICES/OPENAI_VOICES` + DEFAULTS; hapus fallback chain `tts_engine` (`tts_fallback_provider`), `visual_assembler` (`visual_fallback_mode`), `production_on_api_error='fallback'` → provider gagal = **gagal jujur + log** (tak pindah). `tts_voice_settings` tetap = delivery override.
- DEPENDS: F1-04, F1-07.
- DONE-BILA: ryan (1ch) **identik perilaku** (voice VR6, speed 0.86, model sama) — uji regresi produksi nyata; tenant uji 2-channel beda model/voice/caption → output beda, tak saling timpa; **grep bersih** (tak ada map/fallback hardcoded); provider gagal → status gagal jujur (bukan diam-diam edge).
- REALISASI: ✅ (config+deploy; render-level monitor) | commit: `7a5d030` (+migr 0065) | catatan: **JAHITAN TUNGGAL** terpasang: `load_tenant_config(tenant_id, channel_id, niche)` overlay 14 kolom channels + resolusi voice (`channels.voice_key`→`niches.voice_defaults[provider]`) + `voice_catalog.default_settings` (baseline delivery, no-hardcode); **backward-compatible** (channel_id=None=lama). **12 call-site** ter-update (pipeline/script_engine/hook_optimizer/niche_selector×2/visual_assembler/video_renderer×5/youtube_publisher). **NO-FALLBACK**: tts_engine chain=[primary] (gagal→jujur); visual_assembler sudah no-fallback. **Hardcode dibuang**: ELEVENLABS_VOICES/NICHE_VOICES/OPENAI_VOICES + DEFAULTS-settings EL → dari voice_catalog/channel; **fix bug** openai_tts (self.voice tak ter-set). migr 0065: rate edge per-voice faithful (Guy+10/Jenny+15/Christopher+5%). **Validasi non-render LULUS:** ryan 4 niche voice + merged-speed **IDENTIK** (0.86/0.93/0.88/0.90 = baseline+override); provider instansiasi benar; admin_te edge voice+rate faithful; py_compile 12 file; **grep map/fallback bersih** (tinggal komentar). **DEPLOYED** mv-worker (pull+restart **active**, Producer+Publisher start nol error). **✅ Render-level CONFIRMED (produksi nyata ryan, direct-test 2026-06-20 13:48-13:54):** overlay `tts=elevenlabs/pNInz llm=gpt-4o visual=ai_image:gpt-image-1-mini`; TTS BENAR-BENAR pakai voice resolved `[ElevenLabs] voice=pNInz6obpgDQGcFmaJgB` (niche universe); settings baseline+override=speed 0.9; **QC PASSED 56.4s**; published private `shorts/55VySDIkE48`; production_run success/qc_passed/viral 81.4; nol error/fallback. **F1-05 BENAR end-to-end, ryan identik.** Stale docstring tts_voice_per_niche (elevenlabs:6/tts_engine:8) = cosmetic, sapu di F5.

#### [F1-08] Gerbang aktivasi channel di BE — `channel_readiness()` + guard produksi `[NEW — owner 2026-06-20]`
- TUJUAN: channel default non-aktif; produksi hanya jalan untuk channel READY (§10.E.7).
- PLAN: fungsi BE `channel_readiness(channel)` cek (niche, model tiap elemen preset, voice, credential valid per provider, YouTube OAuth) → status + daftar sisa. Producer **skip** channel non-ready (tambah ke guard di `plan_and_submit`, sejajar cek `production_paused`/`gate_for_channel`). `channels.is_active` hanya boleh true bila ready (enforce di RPC/gate). Default channel baru = `is_active=false`.
- DEPENDS: F1-04, F1-05.
- DONE-BILA: channel tak lengkap tak diproduksi (terbukti) + tak bisa di-set aktif; channel lengkap jalan; ryan tetap jalan.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F1-06] Backfill channel_id NULLABLE (5 tabel) `[INDEPENDEN — di luar kritis-path; kapan saja]`
- 🔁 **Re-evaluasi 2026-06-20:** TIDAK memblok refactor fanout (data-hygiene murni, risiko rendah). Boleh dikerjakan paling awal (warmup aman) atau paling akhir. Tidak menahan F1-07/04/05/08.
- TUJUAN: tutup gap legacy v1 null.
- BUKTI: **verified DB** — nullable di `content_inventory, production_runs, video_analytics, channel_insights, videos`; `direct_jobs`=NOT NULL.
- PLAN: backfill NULL→channel tenant (via join videos.run_id / channel tertua tenant); (opsi) ALTER NOT NULL per tabel bila aman (hati-hati `videos.channel_id` FK uuid).
- DEPENDS: —
- DONE-BILA: 0 baris channel_id NULL untuk tenant aktif; query per-channel akurat.
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 2 — CHANNEL SETUP (wizard) + gerbang aktivasi + child (FE/BE tenant) `[buka pondasi ke pengguna]`
*Sasaran: form setup channel ramah pemula (§10.E.8) — pilih niche + model per-elemen + voice (+test) + credential + caption/hashtag/branded/operasional; save draft; channel non-aktif s/d lengkap & valid.*

#### [F2-01] Channel setup wizard + entitlement kuota + gerbang aktivasi
- PLAN: FE create/read/update/delete channel sbg **wizard ber-langkah** (§10.E.8), **boleh save draft** tiap langkah; pilih niche dari **platform + custom milik tenant** (`entitled_niches`); enforce `plan_limits.max_channels`; RLS `tenant_id=auth.uid()`; **tombol Aktifkan enabled hanya saat `channel_readiness` lengkap** (F1-08) + tampil **checklist sisa**; channel baru default `is_active=false`.
- DEPENDS: F1-05, F1-08.
- DONE-BILA: wizard jalan + draft tersimpan + kuota + RLS teruji (tak bocor antar-tenant); channel tak lengkap tak bisa diaktifkan; checklist akurat.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-02] Tab Caption (styling subtitle) + Hashtags → `/channels/[id]` (per-channel)
- PLAN: tab **caption_style** (font, **ukuran, posisi, warna**, highlight/outline, kata-per-baris — styling subtitle on-screen, BUKAN deskripsi YouTube) & **hashtags** baca/tulis kolom `channels` (F1-04) via RLS UPDATE; buang dari `config/[tab]` tenant. Preview styling bila memungkinkan.
- DEPENDS: F1-04, F2-01.
- DONE-BILA: 2 channel beda caption_style/hashtag tersimpan terpisah & terpakai produksi (subtitle ter-render sesuai styling).
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-03] Pemilih AI-model per-elemen + voice (+TEST) + knob operasional per-channel
- PLAN: di `/channels/[id]` (atau wizard): **pemilih model per-elemen** (LLM/image/TTS/video) dari katalog `ai_models` **aktif** (tampil cost_hint); **pemilih voice** untuk TTS model terpilih (default niche ter-pra-isi via `voice_defaults`, boleh ganti) + **TOMBOL TEST/PREVIEW voice** (F2-06); knob operasional (visual_mode/image_quality/music on-volume-mood/quality-gate). Tulis ke `channels` via RLS UPDATE.
- DEPENDS: F1-04, F1-05, F2-01, F2-06.
- DONE-BILA: model+voice+operasional tersimpan per-channel + terpakai produksi; voice bisa di-preview sebelum simpan; 2 channel beda model/voice → output beda.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-04] Panel "Branded" per-channel (CTA/logo/landing) + storage logo `[dari branded-content doc]`
- KENAPA: DB+BE branded SUDAH jadi (§5.6), hanya FE+storage kurang.
- PLAN: tab Branded di `/channels/[id]`: CTA radio implicit|soft_sell (+brand_name/cta_text); upload logo→bucket→URL ke `brand_logo` + pemilih posisi(4 sudut)+slider size/opacity+preview 9:16; landing_link + posisi top/bottom. Tulis via RLS UPDATE channels. Buat bucket/route upload logo.
- DEPENDS: F2-01.
- DONE-BILA: tenant set CTA/logo/landing dari UI; video produksi menampilkannya; logo tersimpan & ter-overlay.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-05] Buang tab Voice/Visual-style/Music-DNA dari config tenant
- PLAN: hapus tab Voice (mock) + bagian visual-style/music yang DNA dari `config/[tab]` tenant (pindah ke niche, FASE 3). Sisakan **BYOK keys (per-tenant, dipakai-ulang)**/Notifikasi/plan di tenant. *(Pilihan voice & model pindah ke channel, F2-03; key TETAP tenant.)*
- DEPENDS: F3 (niche editor siap menampung DNA).
- DONE-BILA: config tenant hanya berisi item milik tenant (keys/notif/plan); tak ada config DNA/voice/model-pick di tenant.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F2-06] Endpoint TEST/PREVIEW voice (FE tenant) `[NEW — owner 2026-06-20]`
- TUJUAN: tenant bisa **mendengar sampel voice** sebelum memilih (§3.3/§10.E.4).
- PLAN: endpoint `/api/voice/preview` — kalau `voice_catalog.preview_url` ada → sajikan; kalau tidak → sintesis kalimat pendek via provider voice itu (pakai key tenant bila BYOK; key platform bila platform voice) → audio sementara. FE: tombol ▶ di pemilih voice (F2-03) + di niche editor (F3-02). Sadar-biaya (sampel pendek, cache).
- DEPENDS: F1-01 (voice_catalog), F2-01.
- DONE-BILA: tenant klik ▶ → dengar voice terpilih; jalan untuk EL/openai/edge; aman tanpa key (degradasi jelas).
- REALISASI: ⬜ | commit: — | catatan: —

---
### FASE 3 — NICHE CRUD + child (admin + Business) `[authoring DNA]`
#### [F3-01] Tombol "Tambah niche" di admin (API sudah ada)
- BUKTI: POST `niches/route.ts:44` SIAP; FE tak ada tombol (§5.4).
- PLAN: tambah form create niche di `admin/(panel)/niches` → POST.
- DONE-BILA: admin buat niche baru dari UI; tercatat audit.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F3-02] Lengkapi editor niche (field hilang + voice DEFAULT per TTS model)
- PLAN: drawer tampil `image_quality_tags, image_negative_prompt, visual_fallbacks, section_timing` (API allow) + **selector voice DEFAULT per TTS model** (`niches.voice_defaults` — 1 default tiap provider aktif, dari `voice_catalog` provider itu) + **TEST/PREVIEW** (F2-06); ganti JSON-textarea rapuh→form terstruktur; tambah `voice_defaults` ke allowlist PATCH (`[id]/route.ts:7-8`).
- DEPENDS: F1-01/02/07.
- DONE-BILA: semua field DNA bisa di-edit aman; voice default per model tersimpan & jadi pra-isi di channel-config (F2-03); preview jalan.
- REALISASI: ⬜ | commit: — | catatan: —

#### [F3-03] Business niche-studio (clone admin, scoped private) + gating config-driven
- PLAN: halaman kelola-niche untuk tier yang diizinkan (clone UI admin niches), niche dibuat `access_type=private, exclusive_to=tenant_id`; **gating config-driven** (`app_config` daftar tier yang boleh buat niche, default `['business']` + admin — **extensible ke `pro` tanpa ubah kode**, sesuai arahan owner); Entry/Pro (di luar daftar) tetap request.
- DEPENDS: F3-01/02.
- DONE-BILA: tier dalam daftar (default Business) buat+edit niche private (tak terlihat tenant lain); tier di luar daftar tak punya akses create; menambah Pro = ubah `app_config` saja.
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
- **2026-06-20 (e)**: ✅ **F1-02 SELESAI** (commit `72d5e51`, migr **0062**). niches.voice_key + seed 4 voice EL platform. NOL dampak ryan.
- **2026-06-20 (f)**: 🏗️ **ARSITEKTUR FINAL DIBUNGKUS** (diskusi owner — keputusan dikunci): **(1)** multi-AI-model per-elemen (LLM/image/TTS/video) — **tenant pilih per-channel** dari katalog **aktif admin**; admin/dev = gerbang dukungan param (extensible mis. Fish Audio). **(2)** Voice **Opsi 2**: niche kasih default per TTS model, tenant pilih final per-channel, **FE wajib test/preview voice**. **(3)** **TIDAK ADA FALLBACK** — produksi hanya pakai config, gagal=jujur. **(4)** Channel default **non-aktif** + **gerbang aktivasi** (lengkap+valid baru aktif), form wizard ramah pemula, save draft. **(5)** caption-styling(subtitle)+hashtag+model+voice = channel; credential per-tenant dipakai-ulang+divalidasi; YouTube OAuth per-channel. **(6)** niche-create gating config-driven (extensible ke Pro); niche picker = platform + custom milik tenant. **Tertuang di:** §3 (kpts 3-11), §4 (fanout), §10.B (voice Opsi 2), **§10.E (arsitektur kanonik)**, FASE 1 (+F1-07 BE-ready, +F1-08 gerbang aktivasi; F1-03 rewrite no-fallback; F1-04 perluas model+voice), FASE 2 (wizard+gate+model/voice picker+F2-06 preview), F3-02/03 (voice default per model + gating config-driven). **Belum ada kode dari arsitektur ini disentuh.**
- **2026-06-20 (g)**: 🔬 **STUDI MENDALAM jalur produksi A-to-Z** (worker→producer/publisher→pipeline 7-step→8 komponen, dibaca sendiri) → **RE-EVALUASI URUTAN FASE 1**. Temuan kunci: semua config per-channel (model/voice/caption/visual) lewat **SATU jahitan** = `load_tenant_config(tenant_id)` yang dipanggil tiap komponen (8 file). **Keputusan:** (1) **F1-03 DILEBUR ke F1-05** (jahitan tunggal channel-aware loader + resolusi voice + no-fallback — satu pass, hindari sentuh 8 file 2×). (2) **F1-06 = independen** (data-hygiene, di luar kritis-path). (3) Urutan: **F1-07 → F1-04 → F1-05(⭐ gerbang owner) → F1-08**; DB-additive dulu (nol-risiko), pembedahan produksi terakhir. **Berikutnya: F1-07** (mulai dgn audit read-only adapter + migr additive).

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

### 10.B — Skema Voice (Opsi 2 — owner 2026-06-20) (untuk F1-02/03, F2-03, F3-02)
**Prinsip:** voice = milik tiap **TTS model**; admin menyediakan voice per TTS model (`voice_catalog` per `provider_key`). **NICHE memberi voice DEFAULT per TTS model** (DNA/branding). **TENANT memilih TTS model lalu voice saat konfigurasi CHANNEL** — default niche ter-pra-isi, boleh diganti (hak prerogatif tenant). **Pilihan final = `channels.voice_key`** (otoritatif saat produksi). DELIVERY (speed/style/stability) = LLM setel per-naskah. Rotasi voice **OFF**. **FE WAJIB TEST/PREVIEW voice** (putar sampel `preview_url`/sintesis pendek sebelum pilih). TTS butuh voice_key nyata (LLM tak mengarang voice).
**`voice_catalog` (field baku, portabel — SUDAH F1-01):** `voice_key`(PK) · `provider_key` · `display_name` · `gender` · `age` · `accent` · `language`/`locale` · `use_case` · `description` · `default_settings jsonb`{stability,similarity_boost,style,speed} · `preview_url` · `tenant_id`(NULL=platform/terisi=BYOK) · `is_active` · `sort_order`.
**`tts_profiles.param_schema jsonb` (rentang valid/provider — SUDAH F1-01):** elevenlabs `{speed:[0.7,1.2],stability:[0,1],style:[0,1],similarity_boost:[0,1]}` · openai_tts `{speed:[0.25,4.0]}` · edge_tts `{rate,pitch,volume}`.
**Default voice per niche × TTS model:** `niches.voice_defaults jsonb` = `{provider_key: voice_key, ...}` (mis. dark_history `{elevenlabs:VR6…, edge_tts:en-US-GuyNeural, openai_tts:fable}`). *(F1-02 sudah seed `niches.voice_key`=default ElevenLabs; diperluas jadi `voice_defaults` per provider — isi diambil dari map lama edge/openai, jadi DATA terkurasi, bukan hardcode/fallback.)* Bila niche belum punya default utk suatu model → tenant pilih manual (degradasi anggun, BUKAN fallback runtime).
**Resolusi voice saat produksi (NO FALLBACK):** `channels.voice_key` (pilihan tenant) → bila kosong, `niches.voice_defaults[channel.tts_provider]`. Tidak ada yang valid → channel tak lolos gerbang aktivasi (tak produksi). Provider TTS = `channel.tts_provider/model` (pilihan tenant).
**tts_params yang LLM serahkan ke TTS:** `{voice_key (= channels.voice_key), speed, style, stability, similarity_boost}` — di-clamp ke `param_schema` provider.

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

### 10.E — ARSITEKTUR MULTI-AI-MODEL + CHANNEL SETUP & GERBANG AKTIVASI (owner 2026-06-20) (untuk F1-03/04/05/07, F2-01/03)
**Acuan kanonik** untuk arahan: model AI per-elemen dipilih tenant, voice Opsi-2, tidak ada fallback, channel default non-aktif. Ikuti apa adanya.

**1) Elemen produksi & taksonomi model.** Ber-AI-model (butuh model + credential, param bisa beda): **LLM** (skrip, `component=llm`), **image-gen** (visual bila `render_mode=image_sequence`, `component=image`), **TTS** (voice, `component=tts`), **video-gen** (bila `render_mode=ai_video`, `component=video`). **Bukan** ber-model (tanpa credential): music (library), caption (turunan word-timestamp), render (ffmpeg), publish (YouTube OAuth). *(Verified DB: `ai_models.component` nyata baru `{llm,image}` → TTS & video BELUM masuk katalog sbg model terpilih → ditambah di F1-07.)*

**2) Gerbang dukungan model (admin/dev).** Model baru `is_active=true` **hanya** setelah developer verifikasi parameter API-nya didukung. Struktur penampung param (SUDAH ADA): `ai_providers.adapter` (protokol) + `request_param_schema`; `ai_models.default_params` + `cost_hint`; `tts_profiles.param_schema`. **Extensible (mis. Fish Audio):** (a) dev cek/implement adapter+param, (b) admin daftarkan provider+model (`is_active`), (c) admin isi voice library provider itu ke `voice_catalog`, (d) tenant bisa memilih.

**3) Pilihan tenant per-CHANNEL (biaya = hak prerogatif tenant).** Tiap channel pilih model untuk tiap elemen yang dipakai preset-nya, dari katalog **aktif** (admin). `cost_hint` ditampilkan. Disimpan di `channels` (kolom model per-elemen). Provider TTS channel menentukan voice yang tersedia.

**4) Voice (Opsi 2 — ringkas, detail §10.B).** Pilih TTS model → pilih voice (default niche ter-pra-isi via `niches.voice_defaults[provider]`, boleh ganti). **FE wajib TEST/PREVIEW voice.** Final = `channels.voice_key`. NO fallback runtime.

**5) Credential.** Per-TENANT, dipakai-ulang lintas channel (1 key/provider, terenkripsi di vault). Divalidasi (test koneksi) saat diisi. YouTube OAuth = per-channel (sudah).

**6) TIDAK ADA FALLBACK.** Produksi pakai HANYA model/provider/credential/voice terkonfigurasi. Gagal runtime → status gagal + log jujur, tak pindah diam-diam.

**7) Gerbang aktivasi channel (readiness).** `channels` default `is_active=false`. Boleh **save draft** kapan saja. Channel READY (boleh diaktifkan) bila SEMUA:
- niche dipilih (list = platform + custom milik tenant);
- model dipilih untuk tiap elemen preset (LLM selalu; image bila image_sequence; video bila ai_video; TTS selalu);
- voice dipilih untuk TTS model terpilih;
- credential ADA & VALID untuk tiap provider yang dipakai model di channel itu;
- YouTube OAuth terkoneksi.
FE tampilkan **checklist sisa** (ramah pemula); tombol "Aktifkan" enabled hanya saat lengkap. BE sediakan fungsi `channel_readiness(channel)` (dipakai FE gate + guard produksi: producer skip channel non-ready).

**8) Form add/setup channel (UX pemula).** Langkah jelas & boleh simpan sebagian: (1) info channel · (2) pilih niche · (3) pilih model per-elemen (+ cost_hint) · (4) pilih voice (+ test/preview) · (5) isi credential (validasi inline) · (6) caption_style + hashtag + branded + operasional (visual_mode/image_quality/music/quality-gate) · (7) publish settings (privacy/slot/bahasa/AI-disclosure) + connect YouTube.

**9) Fanout penyimpanan.** `channels`: model-per-elemen, `voice_key`, `caption_style`, `niche_hashtags`, branded, operasional, publish settings. `tenant_configs`/vault: BYOK keys (per-tenant), plan/billing. `niches`: DNA + `voice_defaults` per provider. `channel_credentials`: YouTube OAuth (per-channel).

**10) FE WAJIB BERBARENGAN (owner 2026-06-20).** UI/UX **admin panel + tenant panel** harus selaras arsitektur ini secara **in-tandem** — supaya saat seluruh proses selesai, FE sudah sesuai (tak ada BE-FE drift). **⚠️ GAP AKTIF pasca-F1-05:** BE kini baca config dari CHANNEL, tapi FE tab config tenant (Voice/Visual/Music/Caption/Hashtag) masih tulis ke `tenant_configs` → **edit di tab itu tak berefek** ke produksi (ryan aman krn channel ter-backfill; tapi edit baru via tab itu mubazir). **Penutup gap = FASE 2** (pindah ke channel) + FASE 3 (niche editor admin/Business). Prinsip: tiap area BE yang dipindah ke channel/niche → FE-nya WAJIB ikut dipindah di fase yang sama, jangan menyisakan tab yang menulis ke tempat yang tak dibaca BE. Admin: voice_catalog CRUD (✅ F1-01) · niche editor voice_defaults+test (F3-02) · tts_profiles display. Tenant: channel setup wizard + pemilih model/voice(+test)/caption/hashtag/branded + gerbang aktivasi (FASE 2).
