# 🧬 NICHE DNA — Audit A-to-Z + Arsitektur Perbaikan (Plan vs Realisasi)

> **Status: MENUNGGU KESEPAKATAN OWNER (2026-07-04).** Audit selesai (verified DB live + kode BE `file:baris` + FE admin/tenant, klaim kritis diverifikasi langsung). JANGAN eksekusi sebelum owner setuju arsitektur §3.
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

### F1 — Perbaikan mesin (BE, kecil tapi berdampak) — ⬜
1. `config.py` loader: **salin `emotion_scoring_criteria`** (bug 1 baris; kriteria scoring admin langsung hidup).
2. Guard `trend_radar.py:443` (`.get("keywords") or []`).
3. `hook_templates`: **DROP** kolom + dari 2 allowlist + loader (fosil; hook sudah dilayani formula+persona). *(butuh restu: hapus vs wire — rekomendasi hapus)*
4. Log WARNING keras di music_selector langkah-4 (track acak) + sebut niche.
- **DONE-BILA**: test produksi niche ber-criteria menunjukkan QUALITY BAR muncul di prompt (log) & skor mengikuti; grep fosil nihil.

### F2 — `NicheDnaEditor` bersama (FE inti) — ⬜
Section (semua per-field, dwibahasa, panduan+contoh, validasi):
- **Identitas**: nama (wajib) · keywords (chip) · hashtag (chip) · kategori (select) · **style & target_emotion (text + contoh — field hantu dihidupkan)**.
- **Kepribadian Narasi**: 5 kotak (`tone`/`style`/`avoid`/`hook_style`/`emotion_arc`) + contoh dari niche base.
- **Musik**: mode (radio 3 pilihan berlabel awam) · mood/track (select dari DB) · **mood_priority = pilih-urut dari daftar `moods`** (chip terurut, min 2) + indikator jumlah track per mood utk niche ini + warning 0-track.
- **Visual**: 3 kotak inti (`base_style`/`color_palette`/`atmosphere` — selaras konsumen) + baris key-value tambahan bebas (lighting/camera/…) + quality tags + negative prompt + exemplar shots (1 baris = 1 shot).
- **Struktur & Penilaian**: `section_timing` = 8 kotak angka ber-label awam + total otomatis + validasi lengkap-atau-kosong yang JELAS; `emotion_scoring_criteria` textarea + panduan menulis kriteria.
- Server: validasi skema di kedua API (tolak + pesan; hapus silent-skip).
- **DONE-BILA**: admin & tenant memakai komponen sama; JSON mentah nihil; salah isi → pesan jelas, nol data-loss.

### F3 — Wizard niche baru ber-template — ⬜
Buat-niche (admin `niches`, tenant `niche-studio`, dan alur deliver `request`): langkah pilih template (4 base + "kosong") → copy DNA → langsung buka editor. Kolom DB nihil perubahan.
- **DONE-BILA**: niche baru apa pun punya DNA terisi dari template; matriks kelengkapan tak pernah ✗ semua lagi.

### F4 — Musik & moods rapi — ⬜
1. Tab **Moods** di Catalog (mood_id, keywords **ID+EN**, aktif) — tabel `moods` akhirnya ter-manage.
2. Keyword moods di-seed dwibahasa (deteksi jalan utk naskah Indonesia).
3. (Bersama F2) editor musik seperti di atas.
- **DONE-BILA**: deteksi mood match utk naskah ID; admin bisa kurasi moods tanpa SQL.

### F5 — Test niche utk TENANT (Fase 3 yang sudah disepakati) — ⬜
Panel SATU card di Niche Studio (aturan `feedback_uiux_design_for_lay_tenants`): tombol test + ConfirmDialog + stepper progres + hasil video — memakai kredensial & channel tenant sendiri, TANPA publish (jalur `_run_test_no_publish` yang sama, job_type `test_nopub` tenant).
- **DONE-BILA**: tenant Business menguji niche studio-nya end-to-end tanpa menyentuh YouTube/kuota.

### F6 — Validasi & data lama — ⬜
Backfill 3 niche non-base via wizard template (imunitas_tubuh, misteri_perang_dunia; `test` dihapus?) + test produksi per niche + dengar musiknya benar + `DB_SCHEMA_V2.md` regenerate bila ada DDL.

---

# §4. KEPUTUSAN YANG DIBUTUHKAN OWNER
1. Setuju arsitektur §2 (editor bersama per-field, tanpa JSON mentah)?
2. `hook_templates`: hapus (rekomendasi) atau di-wire ke hook optimizer?
3. Wizard template: cukup copy-dari-base (rekomendasi, cepat) — draft-DNA-via-AI jadi fase lanjutan terpisah?
4. Niche `test` (origin request, kosong) di DB: hapus?
5. Urutan eksekusi F1→F6 di atas OK? (F1 bisa jalan duluan — murni perbaikan mesin.)

### Changelog
- 2026-07-04 — dokumen dibuat (audit tuntas, menunggu kesepakatan arsitektur).
