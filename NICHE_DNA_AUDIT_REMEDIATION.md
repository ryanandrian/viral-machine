# 🧬 NICHE DNA — Audit A-to-Z + Arsitektur Perbaikan (Plan vs Realisasi)

> **Status: DISEPAKATI owner 2026-07-04 (semua §4 = YA; + keputusan tambahan: editor per-field = FE-only/DB tetap JSONB · preset per-properti dua-tingkat "pilih dulu, sunting kalau mau" · pantangan = free text ditegakkan mesin · preset karakter=pilih-satu, preset daftar=merge).**
> **REALISASI: F1–F6 SEMUA ✅ (tuntas & tervalidasi e2e 2026-07-04 — lihat §3; frasa lama "F5 sedang dikerjakan" = snapshot usang, dikoreksi 2026-07-16).**
> **🎙️ TAMBAHAN 2026-07-16 — EKSPRESI VOKAL (ketok owner): `niches.voice_expression` LIVE** — lihat §1.5 (satu-satunya rujukan sah untuk gaya-baca per-niche).
> **📌 Dokumen ini = SINGLE SOURCE OF TRUTH arsitektur Niche DNA (mandat owner 2026-07-16; sinkron penuh ke codebase saat itu).**
> **Tambahan terealisasi (2026-07-04, commit `22ac613`): Catalog wiring selaras arsitektur** — tab Providers di depan (induk; +key_group tampil/editable +jumlah model +tombol "＋ Model" per baris), AI Models dikelompokkan per provider + Add ber-dropdown, pemutar audio TUNGGAL play/stop utk Music & Voice.
> **✅ is_active kini DIHORMATI produksi (2026-07-04, disetujui owner):** `_resolve_niche` menyaring pool rotasi dari niche nonaktif (fallback `channels.niche`; mode 'fixed' = binding eksplisit, tak disaring). Toggle Aktif di Studio kini berfungsi nyata.
> **✅ `DB_SCHEMA_V2.md` DIHAPUS (keputusan owner 2026-07-04):** dokumen skema basi menyesatkan — sumber kebenaran struktur = INTROSPEKSI LANGSUNG DB live (psycopg2) tiap kali menyentuh DB.
> Hub backlog = `SISA_KERJA_GO_LIVE.md`. Terkait: Test Lab Fase 1 (SELESAI, alat validasi audit ini) · Fase 3 test-niche tenant (disepakati, menumpang §3.5).

---

# §1. HASIL AUDIT (fakta terverifikasi)

## 1.1 Peta properti niche → konsumen mesin (17 kolom)

| Properti | Konsumen nyata | Status |
|---|---|---|
| `keywords` | trend_radar (scan tren) · niche_selector (filter) · publisher (`snippet.tags`) | ✅ sehat; ⚠️ `trend_radar.py:443` akses `["keywords"]` langsung → KeyError bila niche tak dikenal & nol niche aktif; keywords kosong (niche custom) = scan tren tanpa kata kunci |
| `style` | prompt seleksi topik · derive persona bila kosong | ✅ sehat — UI editor **SUDAH ADA** (F2; catatan "field hantu" = arsip) |
| `target_emotion` | prompt topik · hook optimizer · emotional-peak retry · scoring | ✅ sehat — UI editor **SUDAH ADA** (F2) |
| `hook_templates` | — | ✅ **SUDAH DI-DROP** (F1, migr 0118) — baris ini arsip temuan |
| `default_hashtags` | publisher (fallback hashtag deskripsi) | ✅ sehat |
| `narration_persona` | prompt naskah (TONE/STYLE/AVOID/ARC/HOOK) + scoring derive | ✅ sehat (dict 5 key). **Jalur ke telinga = via TEKS naskah**; parameter vokal TTS = `voice_expression` (§1.5) |
| `visual_style` | prompt image Tahap-2 (key bebas) · hook-frame + rewrite (key SPESIFIK `base_style,color_palette,atmosphere`) | 🟡 **mismatch bentuk**: 2 konsumen butuh 3 key inti; kalau admin isi key lain saja → jatuh ke default hardcode |
| `visual_fallbacks` | "EXEMPLAR SHOTS" few-shot prompt + padding kandidat | ✅ sehat |
| `mood_priority` | music_selector (safety-net + fallback cascade) · producer (rotasi mood LRU) | ✅ sehat |
| `music_config` | music_selector (mode auto/random/fixed) | ✅ sehat |
| `emotion_scoring_criteria` | script_engine QUALITY BAR + analyzer scoring prioritas-1 | ✅ sehat — bug loader lama **SUDAH FIXED** (F1 2026-07-04) & tervalidasi e2e (F6) |
| `section_timing` | struktur 8-section + word budget prompt naskah | ✅ sehat (validasi ketat 8 key wajib; parsial → default) |
| `image_quality_tags` / `image_negative_prompt` | positive/negative prompt image | ✅ sehat |
| `youtube_category_id` | publisher `snippet.categoryId` (query langsung) | ✅ sehat |
| `voice_key` (niche) | — (di-drop migr 0083; voice = per-channel) | ✅ sudah bersih |
| `voice_expression` 🆕2026-07-16 | adapter ElevenLabs (gaya-baca: style/stability 0–1) via `tenant_config` niche-EFEKTIF (DUA titik-muat seragam — kelas s85) | ✅ LIVE — detail §1.5 |
| `access/exclusive/released/origin/is_base` | entitlement + lifecycle | ✅ sehat |

## 1.1b 🔒 LARANGAN TENANT KINI BENAR-BENAR DITERAPKAN + GAYA VISUAL JADI MILIK NICHE *(2026-08-14)*

**Dua janji DNA yang selama ini bocor — keduanya ditutup, lihat `SISA_KERJA [B28]` untuk bukti ukur.**

| Properti | Yang dijanjikan layar | Kenyataan sebelum 14-Agu | Sekarang |
|---|---|---|---|
| `image_negative_prompt` ("Larangan gambar") | larangan gambar niche | **DIABAIKAN TOTAL** oleh FLUX/Cloudflare — 6 dari 11 channel. Tenant mengetik, menyimpan, mesin tak pernah membacanya | Dilipat ke **prompt POSITIF** di corong `_generate_image` ⇒ berlaku di **semua** transport, termasuk vendor yang belum ada |
| `narration_persona.avoid` ("Pantangan") | *"dipatuhi mesin apa adanya"* | **Prioritas, bukan kepastian** — pelanggaran hanya memicu retry; percobaan habis → naskah berskor tertinggi dipakai **walau melanggar** | Naskah akhir yang masih melanggar → **run BERHENTI** (§0.6). Terukur: 0 dari 127 produksi nyata terdampak |

### 🆕 `visual_style.render_style` — gaya rupa keluar dari kode

Kata **"photorealistic" dulu dipatri di 6 titik** (4 di `script_engine`, 1 frame pembuka, 1 penulis-ulang).
Akibatnya niche bergaya **animasi/ilustrasi mustahil**: DNA-nya sampai ke mesin gambar lalu **dibantah
kata patri di prompt yang sama**. Kini gaya dibaca dari `visual_style.render_style`.

> ⚠️ **JANGAN TERTUKAR dengan `realism`.** `render_style` = **satu-dua kata** gaya rupa
> (`photorealistic` · `stylized 3D character animation`). `realism` = kalimat tekstur (rata **116
> huruf**, terpanjang 138) — dipakai sebagai baris DNA biasa, **bukan** untuk disisipkan ke kalimat
> pendek seperti *"End with: vertical 9:16, …"*.

**Bawaan `"photorealistic"` ⇒ teks prompt 47 niche lama SAMA PERSIS, termasuk kapitalisasinya**
(3 titik berhuruf besar, 3 huruf kecil — dijaga uji). Editor DNA **sudah** bisa menambah kunci
`visual_style` baru ("properti tambahan"), jadi nol perubahan layar.

**Yang SENGAJA tidak disentuh:** `"No people."` pada frame pembuka (judul pembuka digambar di 15% dari
atas ⇒ membuka "ada orang" di frame itu perubahan tersendiri) · 2 baris cadangan saat `visual_style`
kosong · contoh tetap fitur uji-model admin.

## 1.1c 🧩 SEMANTIK PRESET DIPERTAJAM — "pilih-satu" ≠ "hapus yang lain" *(2026-08-15, `[B32]` T1)*

Kesepakatan 4-Jul di kepala dokumen ini berbunyi **"preset karakter = pilih-satu"**. Editor
menerjemahkannya menjadi *"rakit ulang objeknya dari kunci inti + isi preset"* — sehingga **setiap
properti di luar preset LENYAP**. Ke-6 preset `visual_style` hanya memuat 6 kunci sementara niche
memakai s/d 16 ⇒ **satu klik menghapus s/d 9 properti**, termasuk `strict_prohibition` (larangan agama)
dan `render_style` (§1.1b). Tenant menekan Simpan, larangannya hilang, kotaknya pun ikut hilang dari
layar — tak terlihat siapa pun. *(Terukur 15-Agu: nol niche berjejak 6-kunci-persis ⇒ ranjau, belum meledak.)*

**Semantik resmi sekarang** (`terapkanPreset()` di `lib/niche-dna.ts`): preset **berkuasa penuh atas
KELUARGA kuncinya sendiri**, dan **tidak menyentuh apa pun di luar keluarga itu**.
- kunci keluarga yang diisi preset → **diisi**
- kunci keluarga yang TIDAK diisi preset → **dikosongkan** *(inilah "pilih-satu": nol sisa gaya lama)*
- kunci di luar keluarga → **dipertahankan** *(§5b Lapis-2: milik pemilik niche)*

**Keluarga ditemukan dari DATA** — gabungan kunci seluruh preset properti itu ∪ kunci inti — bukan daftar
hafalan; preset baru berkunci baru otomatis terhitung. Berlaku sama untuk `narration_persona`.
Dijaga `tests/test_preset_dna_tak_menghapus.py` (8 uji yang **menjalankan** fungsi TS-nya, bukan membaca
teksnya; merah dibuktikan 3× termasuk 2 sabotase).

## 1.2 Rantai MUSIK (kecurigaan owner — TERBUKTI ada lubang)
- `music_selector` sendiri dirancang baik: mode fixed/random/auto · deteksi mood dari naskah (keyword `moods` table) · cascade **niche-safe**: (1) niche+mood → (1b) niche+mood-lain → (2) mood lintas-niche → (3) fallback moods → **(4) TRACK ACAK APA SAJA**.
- **Lubang DATA**: library 28 track hanya ter-tag 4 niche base. **Niche studio/request: `mood_priority` KOSONG + 0 track** → deteksi keyword gagal (lihat bawah) → cascade jatuh ke (2)/(4) → **musik lintas-niche/acak**. TERBUKTI: test `imunitas_tubuh` memakai track `calm` milik ocean_mysteries.
- **Keyword mood bahasa INGGRIS** (`moods.keywords`: "shocking, incredible…") — naskah Indonesia hampir tak pernah match → deteksi otomatis mati utk konten ID.
- Tabel `moods` **tidak dikelola UI mana pun** (Catalog tak punya tab moods).
- Mixing di renderer: `music_enabled`(default FALSE)/`music_volume`(0.10)/`music_default_mood` = per-channel dari tenant_config — sehat.

## 1.3 DNA niche non-base = KOSONG TOTAL (temuan bisnis terbesar)
Matriks kelengkapan (verified DB): 4 niche base admin = ✓ semua. **`imunitas_tubuh`(studio), `misteri_perang_dunia`(request), `test`(request) = ✗ SEMUA DNA** (persona/visual/mood/timing/scoring/fallbacks/keywords/hooks). Niche baru dibuat hanya dgn id+nama; **tidak ada seeding/template**. Artinya: **custom niche yang DIJUAL (Rp 299K) menghasilkan video generik** (persona default, visual default, musik acak, scoring default) — bertentangan dgn janji produk "DNA kustom".

## 1.4 UX editor (admin & tenant)
- **5 field = JSON MENTAH di textarea** (persona, music_config, visual_style, mood_priority, section_timing); tanpa contoh struktur (kecuali hint kecil); **JSON salah ketik → di-skip DIAM-DIAM, toast tetap "Tersimpan"** (data loss senyap) — admin `niches/page.tsx:111-113`, tenant `niche-studio/page.tsx:76-78`.
- Tenant: panduan lebih tipis dari admin; padahal tenant paling butuh.
- Tanpa validasi skema (mis. `music_config.mode` bebas nilai apa pun; `section_timing` parsial → diabaikan total TANPA pemberitahuan).
- `style`/`target_emotion`/`hook_templates` di allowlist kedua API tapi tak punya UI.
- Tenant TIDAK bisa test niche (admin sudah — Fase 1).

## 1.5 🎙️ EKSPRESI VOKAL — gaya-baca narator per-niche (LIVE 2026-07-16, ketok owner; migr 0167)

**Masalah yang dijawab:** kenop warisan `tenant_configs.tts_voice_settings[niche]` TERBUKTI AKTIF (94/94 render EL di log produksi memakainya — vonis 2026-07-16) tapi: buta-layar (nol UI), hanya 4 niche template, tersalin per-tenant via DEFAULT kolom. Persona niche tak pernah sampai ke parameter vokal utk 43 niche lain.

**Arsitektur resmi kini:**
- **Kolom:** `niches.voice_expression` jsonb `{"style": 0..1, "stability": 0..1}` — NULL = ikut karakter bawaan suara (`voice_catalog.default_settings`). **TANPA `speed`** (tempo = milik eksklusif mesin durasi §10.A — mencampurnya merusak presisi).
- **Seed:** 4 niche template diisi PERSIS nilai warisan yang berbunyi (dark 0.55/0.28 · fun 0.35/0.50 · ocean 0.40/0.35 · universe 0.50/0.30) → bukti merge byte-identik.
- **Rantai baca:** `niches.voice_expression` → `tenant_config` (dimuat utk NICHE EFEKTIF di **DUA titik-muat** `_load_from_supabase` + `_reload_niche_visual` — WAJIB seragam, kelas bug s85; ranjau satu-titik tertangkap uji-live pra-ship 2026-07-16) → `tts_engine._get_provider_config` → adapter `elevenlabs.py` merge: **bawaan-suara ⊕ ekspresi-niche ⊕ warisan-tenant** (warisan TERAKHIR = suara channel berjalan IDENTIK; guard: hanya key style/stability, angka 0..1, nilai liar dibuang).
- **UI:** seksi "Ekspresi Vokal" di `NicheDnaEditor` (SATU komponen → admin `/admin/niches` + tenant Niche Studio): checkbox "Atur khusus" + 2 slider (Kedramatisan/Kestabilan) + **narasi fungsi** (dwibahasa): berlaku utk suara premium EL · kosong = ikut bawaan suara · tempo TIDAK diatur di sini. Validasi klien+server (`lib/niche-dna.ts` + 2 allowlist API). Ikut `TEMPLATE_COPY_COLUMNS` (niche baru dari template mewarisi jiwa vokal).
- **⬜ Fase pembongkaran warisan** (`tenant_configs.tts_voice_settings` kolom + DEFAULT-nya): TERPISAH, ber-ketok owner, setelah lapisan baru terbukti aman berminggu — HARAM dicabut sekarang (mengubah suara channel produksi).

---

# §2. PRINSIP ARSITEKTUR (untuk disepakati)

1. **SATU editor bersama** — komponen `NicheDnaEditor` dipakai admin & tenant (fungsi & alur sama; beda hanya kepemilikan/akses: admin +tab Access/is_base/base-management; tenant dipaksa private+milik-sendiri di server — enforcement yang ada dipertahankan).
2. **NOL JSON mentah** — setiap properti dipecah jadi field ber-label bahasa awam + placeholder contoh nyata (diambil dari niche base) + penjelasan 1 kalimat "apa dampaknya ke video".
3. **Validasi jujur dua lapis** — klien (per-field, tombol Simpan disabled + pesan jelas) & server (skema; tolak dgn pesan, BUKAN skip senyap).
4. **Niche baru TIDAK pernah lahir kosong** — wizard "mulai dari template": pilih niche base terdekat → DNA di-copy sebagai titik awal → user menyunting. (Fase lanjut opsional: draft DNA di-generate AI dari deskripsi niche.)
5. **Musik by-design, bukan kebetulan** — mood_priority wajib ≥2 (dipilih dari `moods`, bukan ketik bebas); editor menampilkan "X track tersedia utk pilihanmu" + warning bila 0 (admin: link kelola Catalog); cascade acak (langkah 4) diberi log WARNING keras.
6. **Perbaiki mesin dulu** (bug loader scoring dsb.) supaya editor yang baru benar-benar berefek.

---

# §3. PLAN (fase eksekusi — setelah disepakati)

### F1 — Perbaikan mesin (BE, kecil tapi berdampak) — ✅ *(2026-07-04)*
> Realisasi: loader `config.py` salin `emotion_scoring_criteria` ✓ · guard trend_radar ✓ · `hook_templates` DI-DROP (migr 0118 + 2 allowlist + loader) ✓ · WARNING keras music last-resort ✓ · niche `test` dihapus ✓.
1. `config.py` loader: **salin `emotion_scoring_criteria`** (bug 1 baris; kriteria scoring admin langsung hidup).
2. Guard `trend_radar.py:443` (`.get("keywords") or []`).
3. `hook_templates`: **DROP** kolom + dari 2 allowlist + loader (fosil; hook sudah dilayani formula+persona). *(butuh restu: hapus vs wire — rekomendasi hapus)*
4. Log WARNING keras di music_selector langkah-4 (track acak) + sebut niche.
- **DONE-BILA**: test produksi niche ber-criteria menunjukkan QUALITY BAR muncul di prompt (log) & skor mengikuti; grep fosil nihil.

### F2 — `NicheDnaEditor` bersama (FE inti) — ✅ *(2026-07-04)*
> Realisasi: `components/niche-dna-editor.tsx` (per-field + preset 2 tingkat + chip + validasi) dipakai admin (`/admin/niches` drawer tab DNA) & tenant (`/niche-studio`) · `lib/niche-dna.ts` = skema+validasi BERSAMA klien+server (kedua API PATCH tolak+pesan per-field, silent-skip DIHAPUS) · tabel `niche_property_presets` (migr 0118, 30 preset seed dwibahasa, RLS publik-baca) · field hantu `style`/`target_emotion` dihidupkan di editor.
Section (semua per-field, dwibahasa, panduan+contoh, validasi):
- **Identitas**: nama (wajib) · keywords (chip) · hashtag (chip) · kategori (select) · **style & target_emotion (text + contoh — field hantu dihidupkan)**.
- **Kepribadian Narasi**: 5 kotak (`tone`/`style`/`avoid`/`hook_style`/`emotion_arc`) + contoh dari niche base.
- **Musik**: mode (radio 3 pilihan berlabel awam) · mood/track (select dari DB) · **mood_priority = pilih-urut dari daftar `moods`** (chip terurut, min 2) + indikator jumlah track per mood utk niche ini + warning 0-track.
- **Visual**: 3 kotak inti (`base_style`/`color_palette`/`atmosphere` — selaras konsumen) + baris key-value tambahan bebas (lighting/camera/…) + quality tags + negative prompt + exemplar shots (1 baris = 1 shot).
- **Struktur & Penilaian**: `section_timing` = 8 kotak angka ber-label awam + total otomatis + validasi lengkap-atau-kosong yang JELAS; `emotion_scoring_criteria` textarea + panduan menulis kriteria.
- Server: validasi skema di kedua API (tolak + pesan; hapus silent-skip).
- **DONE-BILA**: admin & tenant memakai komponen sama; JSON mentah nihil; salah isi → pesan jelas, nol data-loss.

### F3 — Wizard niche baru ber-template — ✅ *(2026-07-04)*
> Realisasi: POST admin & tenant terima `template_niche_id` → copy `TEMPLATE_COPY_COLUMNS` (gaya; keywords TIDAK) · modal create kedua sisi ada pemilih "Mulai dari template" (base publik) · GET mine kirim `templates`.
Buat-niche (admin `niches`, tenant `niche-studio`, dan alur deliver `request`): langkah pilih template (4 base + "kosong") → copy DNA → langsung buka editor. Kolom DB nihil perubahan.
- **DONE-BILA**: niche baru apa pun punya DNA terisi dari template; matriks kelengkapan tak pernah ✗ semua lagi.

### F4 — Musik & moods rapi — ✅ *(2026-07-04)*
> Realisasi: tab **Moods** di Catalog (keywords editable + indikator jumlah track + add) · keywords 15 mood di-seed DWIBAHASA (migr 0118 — deteksi naskah ID hidup) · editor musik per-field (mode radio + pemilih mood/track dari DB + indikator ketersediaan + warning 0-track) · `niche_property_presets`+`moods` masuk registry catalog API (kelola tanpa SQL).
1. Tab **Moods** di Catalog (mood_id, keywords **ID+EN**, aktif) — tabel `moods` akhirnya ter-manage.
2. Keyword moods di-seed dwibahasa (deteksi jalan utk naskah Indonesia).
3. (Bersama F2) editor musik seperti di atas.
- **DONE-BILA**: deteksi mood match utk naskah ID; admin bisa kurasi moods tanpa SQL.

### F5 — Test niche utk TENANT (Fase 3 yang sudah disepakati) — ✅ *(2026-07-04, commit `2e1d964`)*
> Realisasi: migr 0119 (`job_type` +'test_nopub'; +drop constraint ganda `chk_direct_jobs_type`) · worker `_run_test_no_publish` melayani admin_test & test_nopub · **inventory status `'test'`** (`mark_test`) — tak diklaim publisher (KRITIS: channel tenant AKTIF) + tak mengotori `/review` + TTL janitor · API `/api/niches/mine/test` (enforce studio+milik-sendiri+plan; kredensial/channel tenant = biaya BYOK mereka) · **komponen `TestNichePanel` BERSAMA** admin+tenant (SATU card: tombol+Confirm+stepper+video; panel inline admin lama & tombol footer dihapus) · `lib/test-run` hasil-test bersama · **preview musik ▶/⏹ pemutar tunggal di editor** (+tombol "pakai" mode fixed) via `/api/music/preview` presign (bucket aset privat) · tombol Batal editor · Catalog Music play → presign (fix 403 laten).
Panel SATU card di Niche Studio (aturan `feedback_uiux_design_for_lay_tenants`): tombol test + ConfirmDialog + stepper progres + hasil video — memakai kredensial & channel tenant sendiri, TANPA publish (jalur `_run_test_no_publish` yang sama, job_type `test_nopub` tenant).
- **DONE-BILA**: tenant Business menguji niche studio-nya end-to-end tanpa menyentuh YouTube/kuota.

### F6 — Validasi & data lama — ✅ TUNTAS *(2026-07-04; SELURUH PLAN NICHE_DNA TEREALISASI 100%)*
> **Validasi e2e (3 test produksi nyata, tanpa publish):** imunitas_tubuh QC✓ skor 82,1 · misteri_perang_dunia QC✓ skor 86,9 · rerun-musik QC✓ skor 83,2. **Bukti musik by-design:** log MusicSelector run `direct-5a8c` — 15 mood dwibahasa dimuat → mood_priority DNA niche terbaca (calm/ambient/inspirational) → deteksi 'suspense' tak ada track → fallback **calm (prioritas DNA)** → 'abyssal_silence' (BUKAN acak lintas-niche). **Bukti scoring:** loader (kode deployed) mengembalikan emotion_scoring_criteria kedua niche ✓. Video test = inventory status 'test', TTL 7 Juli ✓; transisi job antre→berjalan→done otomatis ✓.
> **⚠️ 2 temuan tambahan (follow-up, di luar plan ini):** (1) test pertama 2026-07-03 ternyata TANPA musik (channels.music_enabled test=false; klaim lama "musik calm ocean" = salah-baca log StorageCleaner — dikoreksi). Channel test kini music_enabled=true. (2) cache config worker: **SUDAH BER-TTL** — run-config `_CACHE_TTL_S=120s` (verified kode 2026-07-16) + plan_limits TTL 300s (ditambah 2026-07-16). Catatan lama "tanpa kedaluwarsa" = usang.
> Realisasi 2026-07-04: `misteri_perang_dunia` ← template dark_history + keywords perang · `imunitas_tubuh` ← komposisi preset kesehatan (persona hangat, visual cerah, mood tenang, scoring inspirasi) + keywords imunitas · matriks kelengkapan kedua niche = ✓ semua. **Menyusul pasca-deploy:** test produksi via Test Lab per niche (dengar musik benar + QUALITY BAR muncul di log) (`DB_SCHEMA_V2.md` DIHAPUS — keputusan owner 2026-07-04: sumber kebenaran = introspeksi DB live).

---

# §4. KEPUTUSAN YANG DIBUTUHKAN OWNER
1. Setuju arsitektur §2 (editor bersama per-field, tanpa JSON mentah)?
2. `hook_templates`: hapus (rekomendasi) atau di-wire ke hook optimizer?
3. Wizard template: cukup copy-dari-base (rekomendasi, cepat) — draft-DNA-via-AI jadi fase lanjutan terpisah?
4. Niche `test` (origin request, kosong) di DB: hapus?
5. Urutan eksekusi F1→F6 di atas OK? (F1 bisa jalan duluan — murni perbaikan mesin.)

### Changelog
- **2026-07-16 — SINKRON PENUH ke codebase (mandat owner: single source of truth, nol asumsi/ambigu).** Banner F5 kontradiktif dikoreksi (semua F1–F6 ✅ sejak 04-Jul); baris §1.1 yang sudah FIXED diberi cap (scoring-loader/hook_templates/field-hantu); +kolom 18 `voice_expression`; **+§1.5 EKSPRESI VOKAL** (arsitektur lengkap: kenop warisan aktif-94/94 → kolom resmi ber-UI dua panel, merge byte-identik, fase pembongkaran warisan ber-ketok); catatan cache F6 di-update (TTL 120s/300s live).
- 2026-07-04 — dokumen dibuat (audit tuntas, menunggu kesepakatan arsitektur).
