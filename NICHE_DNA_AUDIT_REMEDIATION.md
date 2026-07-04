# 🧬 NICHE DNA — Audit A-to-Z + Arsitektur Perbaikan (Plan vs Realisasi)

> **Status: DISEPAKATI owner 2026-07-04 (semua §4 = YA; + keputusan tambahan: editor per-field = FE-only/DB tetap JSONB · preset per-properti dua-tingkat "pilih dulu, sunting kalau mau" · pantangan = free text ditegakkan mesin · preset karakter=pilih-satu, preset daftar=merge).**
> **REALISASI: F1 ✅ · F2 ✅ · F3 ✅ · F4 ✅ · F6 ✅(backfill; test produksi validasi menyusul) · F5 🔨 SEDANG DIKERJAKAN (2026-07-04: migr 0119 job_type test_nopub + inventory status 'test' + janitor ✓; API tenant + panel Studio + preview musik menyusul di batch ini).**
> **Tambahan terealisasi (2026-07-04, commit `22ac613`): Catalog wiring selaras arsitektur** — tab Providers di depan (induk; +key_group tampil/editable +jumlah model +tombol "＋ Model" per baris), AI Models dikelompokkan per provider + Add ber-dropdown, pemutar audio TUNGGAL play/stop utk Music & Voice.
> **Temuan baru (belum dieksekusi, keputusan owner):** `niches.is_active` SETENGAH-FUNGSI utk produksi — `producer._resolve_niche` memilih dari `channels.niche_pool` TANPA cek is_active → niche dinonaktifkan tenant TETAP diproduksi bila masih di pool channel. Rekomendasi: hormati is_active di _resolve_niche (filter pool; fallback channels.niche).
> Hub backlog = `SISA_KERJA_GO_LIVE.md`. Terkait: Test Lab Fase 1 (SELESAI, alat validasi audit ini) · Fase 3 test-niche tenant (disepakati, menumpang §3.5).

---

# §1. HASIL AUDIT (fakta terverifikasi)

## 1.1 Peta properti niche → konsumen mesin (17 kolom)

| Properti | Konsumen nyata | Status |
|---|---|---|
| `keywords` | trend_radar (scan tren) · niche_selector (filter) · publisher (`snippet.tags`) | ✅ sehat; ⚠️ `trend_radar.py:443` akses `["keywords"]` langsung → KeyError bila niche tak dikenal & nol niche aktif; keywords kosong (niche custom) = scan tren tanpa kata kunci |
| `style` | prompt seleksi topik · derive persona bila kosong | ✅ sehat; 🟡 **TIDAK ADA UI editor** (field hantu di allowlist) |
| `target_emotion` | prompt topik · hook optimizer · emotional-peak retry · scoring | ✅ sehat; 🟡 **TIDAK ADA UI editor** |
| `hook_templates` | **NOL konsumen** (hook_optimizer pakai `HOOK_FORMULAS` hardcode) | 🔴 **FOSIL** |
| `default_hashtags` | publisher (fallback hashtag deskripsi) | ✅ sehat |
| `narration_persona` | prompt naskah (TONE/STYLE/AVOID/ARC/HOOK) + scoring derive | ✅ sehat (bentuk: dict 5 key `tone,style,avoid,hook_style,emotion_arc`) |
| `visual_style` | prompt image Tahap-2 (key bebas) · hook-frame + rewrite (key SPESIFIK `base_style,color_palette,atmosphere`) | 🟡 **mismatch bentuk**: 2 konsumen butuh 3 key inti; kalau admin isi key lain saja → jatuh ke default hardcode |
| `visual_fallbacks` | "EXEMPLAR SHOTS" few-shot prompt + padding kandidat | ✅ sehat |
| `mood_priority` | music_selector (safety-net + fallback cascade) · producer (rotasi mood LRU) | ✅ sehat |
| `music_config` | music_selector (mode auto/random/fixed) | ✅ sehat |
| `emotion_scoring_criteria` | script_engine QUALITY BAR + analyzer scoring prioritas-1 | 🔴 **BUG: loader `config.py:134-152` TIDAK menyalin kolom ini** → nilai admin TIDAK PERNAH sampai (selalu fallback derive). Verified: dict loader tanpa key ini; kedua konsumen baca via `get_niches()` |
| `section_timing` | struktur 8-section + word budget prompt naskah | ✅ sehat (validasi ketat 8 key wajib; parsial → default) |
| `image_quality_tags` / `image_negative_prompt` | positive/negative prompt image | ✅ sehat |
| `youtube_category_id` | publisher `snippet.categoryId` (query langsung) | ✅ sehat |
| `voice_key` (niche) | — (di-drop migr 0083; voice = per-channel) | ✅ sudah bersih |
| `access/exclusive/released/origin/is_base` | entitlement + lifecycle | ✅ sehat |

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

### F6 — Validasi & data lama — ✅ backfill / ⏳ test produksi
> Realisasi 2026-07-04: `misteri_perang_dunia` ← template dark_history + keywords perang · `imunitas_tubuh` ← komposisi preset kesehatan (persona hangat, visual cerah, mood tenang, scoring inspirasi) + keywords imunitas · matriks kelengkapan kedua niche = ✓ semua. **Menyusul pasca-deploy:** test produksi via Test Lab per niche (dengar musik benar + QUALITY BAR muncul di log) + regenerate `DB_SCHEMA_V2.md`.

---

# §4. KEPUTUSAN YANG DIBUTUHKAN OWNER
1. Setuju arsitektur §2 (editor bersama per-field, tanpa JSON mentah)?
2. `hook_templates`: hapus (rekomendasi) atau di-wire ke hook optimizer?
3. Wizard template: cukup copy-dari-base (rekomendasi, cepat) — draft-DNA-via-AI jadi fase lanjutan terpisah?
4. Niche `test` (origin request, kosong) di DB: hapus?
5. Urutan eksekusi F1→F6 di atas OK? (F1 bisa jalan duluan — murni perbaikan mesin.)

### Changelog
- 2026-07-04 — dokumen dibuat (audit tuntas, menunggu kesepakatan arsitektur).
