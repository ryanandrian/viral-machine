# [B6] PRESET 8 DETIK — RENCANA IMPLEMENTASI ai_video (text-to-video)

> **Status:** 📋 RENCANA MATANG (2026-07-14) — hasil deep-dive kode + DB live (nol asumsi), **menunggu ketok owner untuk mulai F0**.
> **Kaitan:** backlog tunggal = `SISA_KERJA_GO_LIVE.md` **[B6]** (dokumen ini = SPEC+tracker-nya, pola `PROGRAM_BUKTI_KECERDASAN.md`). Spec teknis induk = `MULTI_FORMAT_STUDIO.md §3/§5`. Prioritas jujur (§7 kompas): TIDAK memblok tenant berbayar pertama.

## 🧭 CARA LANJUT (resume pasca-compaction/sesi baru — baca INI dulu, jangan riset ulang)
1. **POSISI SEKARANG: 🟡 F0 SELESAI (riset 2026-07-14, mandat owner "mulai kerjakan" + BISMILLAH) — proposal vendor DIAJUKAN, MENUNGGU KETOK OWNER (fal.ai + Kling perdana) sebelum F1.** (Bila baris ini basi vs REALISASI di bawah → REALISASI menang; perbarui baris ini.)
2. Deep-dive & keputusan SUDAH TUNTAS — §0 (keputusan owner, JANGAN tanya ulang) + §1 (inventaris siap-vs-gap, verified 2026-07-14). Anchor `file:baris` wajib di-grep ulang sebelum dipakai (kode bisa bergeser) — tapi KESIMPULANNYA jangan diaudit ulang.
3. Kerjakan fase BERURUTAN F0→F4; tiap fase selesai → **isi kolom REALISASI fase itu SAAT ITU JUGA** (✅ + tanggal + commit + bukti 1-2 kalimat) + perbarui baris POSISI di atas + sinkron header [B6] di `SISA_KERJA_GO_LIVE.md`. Fase ber-tanda "KETOK OWNER" = STOP menunggu jawaban owner, jangan lompati.
4. Aturan kerja penuh = `CLAUDE.md` (§2 pre-touch, §3 pre-done, §5 deploy). Bukti runtime > klaim; durasi = gerbang keras F4 (§7.3).

> **Aturan tracker:** tiap fase punya kolom REALISASI — diisi LANGSUNG saat selesai (bukti + commit). Marker ⬜ di sini BUKAN daftar kerja (daftar kerja = SISA_KERJA [B6]).

## 0. Keputusan owner (FINAL, 2026-07-14 — jangan tanya ulang)
1. **8s = KHUSUS text-to-video** — bukan Ken-Burns 1 gambar (opsi "gambar dulu" DITOLAK owner).
2. **Vendor/model TIDAK PERNAH dikunci** — katalog harus bisa terus bertambah tanpa ubah kode. Langkah awal = **riset vendor+model dengan format parameter seragam & formula biaya seragam** → proposal → ketok owner.
3. **Bukan SaaS baru** — text-to-video = mode render tambahan DI DALAM MesinViral (rekomendasi Claude, disetujui arah owner 2026-07-14): pipeline & moat (self-learning/QC/BYOK/publish) dipakai bersama; SaaS terpisah = duplikasi 90% fondasi.
4. **Konten 8s = kutipan/afirmasi/motivasi** (owner setuju rekomendasi Claude: format paling ideal — pesan tuntas sebelum scroll, rewatch-loop → watch ratio >100%).
5. **Positioning 8s = KHUSUS pemain volume & retensi** — bukan kedalaman cerita; 60s tetap tulang punggung konten. Analisis performa nanti dibandingkan SESAMA durasi.
6. **Niche DEFAULT 8s = niche khusus kutipan/afirmasi/motivasi** dibuat tersendiri (mengejar retensi) — masuk lingkup F1 (data niche: DNA visual sinematik-motivasi + gaya narasi kutipan + kaitan `format_profiles.motivational_quote` §4 MULTI_FORMAT) dan dipakai sebagai niche uji F4.
7. **Formula visual niche default (owner, 2026-07-14): wanita super cantik + narasi afirmasi/motivasi** — pemirsa menikmati visual sambil membaca caption & mendengar motivasi; 8 detik habis sebelum scroll → retensi ~100%. Tujuan bisnis eksplisit: **mengejar syarat YouTube Partner (views tinggi + retensi tinggi)**. Konsekuensi teknis: (a) kualitas **manusia fotorealistis** jadi KRITERIA UTAMA pemilihan vendor/model di F0 (wajah/tangan tanpa cacat); (b) DNA wajib ber-guardrail aman-iklan (elegan, berpakaian pantas, nol pose sugestif) — lihat Risiko §3; (c) diversity engine wajib merotasi wajah/latar/wardrobe antar-video (anti-repetisi).

## 1. Inventaris TERVERIFIKASI 2026-07-14 (kode + DB live — anchor wajib di-grep ulang sebelum dipakai, §1.2)

### 1a. SUDAH SIAP — jangan dibangun ulang
| Aspek | Bukti (verified) |
|---|---|
| Preset 8s di DB | `duration_presets` seconds=8: `beats=["core_facts"]`, `visual_beats=1`, `render_mode='ai_video'`, **`is_active=false`** (owner off 2026-07-06). Toggle aktivasi ada di `/admin/catalog` (`apps/web/src/app/admin/(panel)/catalog/page.tsx:388-395`) |
| Glossary beat | `beat_glossary.core_facts` ada (label "Inti"/"Core", dwibahasa) |
| Naskah 8s | `script_engine._beats_for_preset` (DB single-source, migr 0053) · `_validate_and_fix` required dinamis = {hook,core,cta}∩aktif → 8s core-saja LOLOS (`script_engine.py:639-647`, hook di-setdefault `""`) · word budget overhead-aware · intent ultra-short (`script_engine.py:296`) |
| Skor viral 8s | `script_analyzer._active_dimensions` — dimensi ternormalisasi ke beat aktif; hook_power TIDAK menghukum 8s (`script_analyzer.py:29-48,140`) |
| Gerbang durasi pra-visual | `pipeline.py:245-267` — proyeksi audio+trailing vs window preset ±`QC_DURATION_TOLERANCE` (0.15) SEBELUM biaya visual → otomatis melindungi biaya video-gen |
| QC pre-publish | relatif preset ±15% → 8s = 6.8–9.2s (jalur existing) |
| Registry visual | `build_visual_provider` family `ai_video:` sudah dispatch (`src/providers/visual/__init__.py:34-46`) — tinggal isi kelasnya |
| Validasi kredensial | STEP 0 fail-loud: `visual_mode` `ai_video:*` tanpa key → stop (`tenant_config.py:273` + `pipeline.py:136-141`) |
| Renderer 1-klip | fallback simple concat utk <2 clip (`video_renderer.py:603-620`; strip audio klip `-an`; Step B audio+subtitle+tpad) — jalur ADA, belum pernah diuji dgn video-gen nyata |
| TTS presisi | F4 durasi-via-speed (LLM speed + clamp; sampel delivery `tts_delivery_samples`) — preset-aware |
| FE tenant | picker preset baca `is_active` (8s muncul otomatis saat diaktifkan; `components/preset-tables.tsx:38-41`) · picker model visual SUDAH siap component `video` → prefix `ai_video:` (`channels/[id]/page.tsx:110,241`) |
| Skema channels | `duration_preset`/`visual_mode`/`visual_account_id` per-channel SUDAH ada — **nol kolom baru** |
| Model kredensial | pool `tenant_ai_accounts(key_group)` + `ai_providers.key_group` (pola CHANNEL_LOCK final 2026-06-25) — vendor video tinggal tambah baris provider |
| FE marketing | klaim "durasi 8–90 detik" SUDAH tayang → aktivasi 8s justru menjujurkan klaim; nol perubahan |
| Async queue | worker 7-thread + produksi decoupled — latency video-gen 1–3 mnt tertampung (audit eksternal `MULTI_FORMAT §0` 2026-06-11) |

### 1b. GAP — yang harus dibangun
1. **Katalog kosong:** `ai_models` component `'video'` = NOL baris; `ai_providers` belum punya vendor t2v (isi live: anthropic/openai/elevenlabs/edge_tts/gemini/groq/openai_tts/cloudflare).
2. **Mesin belum ada:** `src/providers/visual/ai_video.py` = stub yang raise VisualError.
3. **Branch assembler kosong:** `visual_assembler._try_provider` `ai_video:` → return `[]` + warning (`visual_assembler.py:81-83`).
4. **Prompt video belum ada:** STEP 4.5 (`script_engine.generate_visual_prompts`) hanya menghasilkan prompt GAMBAR; butuh varian prompt gerak/kamera.
5. **Meter biaya:** `src/utils/cost_meter.py` punya add_llm/add_image/add_tts — belum `add_video`.
6. **Validator kunci FE:** `apps/web/src/lib/providers/validate-key.ts` `KNOWN_PROVIDERS` = anthropic/openai/elevenlabs saja — vendor video butuh case (dipakai /integrations + admin Test Lab, satu sumber).
7. **Kebijakan hook 8s belum didefinisikan:** STEP 4 hook-optimize memakai `script['hook']` (kosong utk 8s) + overlay judul-hook renderer.
8. **Bukti presisi durasi 1-klip belum ada** — gerbang keras F4 (§7.3 CLAUDE.md): perubahan menyentuh durasi WAJIB membuktikan presisi output.
9. **Catatan arsitektur:** `duration_presets.render_mode` ada di DB tapi TIDAK dibaca BE mana pun (grep nol) — koherensi preset↔visual_mode harus ditegakkan (lihat F2).

## 2. Fase implementasi (tiap fase ber-gerbang; deploy per §5 CLAUDE.md)

### F0 — RISET VENDOR (tanpa kode) — ⬜
Verifikasi **dokumen resmi vendor** (web, bukan ingatan model) sesuai kriteria owner (parameter seragam + biaya seragam):
- **Kandidat utama (rekomendasi Claude): AGREGATOR model-video** — mis. **fal.ai**, **Replicate**: SATU format API + SATU billing utk BANYAK model (Kling/Veo/Hunyuan/LTX/…) → 1 adapter transport, model baru = baris DB (nol kode), vendor tak pernah terkunci. Persis kriteria owner.
- Pembanding langsung: Runway · Kling · Luma · **Veo via Gemini API** (key_group `gemini` SUDAH ada di sistem) · Sora.
- Diverifikasi per kandidat: dukungan **9:16** · durasi klip **5–10s** · pola **async submit→poll** · harga per-detik/per-klip · BYOK (tenant bikin akun sendiri) · rate limit · ketersediaan region · **KRITERIA UTAMA (§0.7): kualitas manusia fotorealistis** (wajah/tangan bersih, gerak natural — uji sampel nyata per model, bukan klaim brosur) + kebijakan konten vendor soal penggambaran manusia.
- **Keluaran:** matriks perbandingan + rekomendasi 1 transport perdana + model perdana → **KETOK OWNER** (gerbang F0→F1).
- **REALISASI:** ✅ **RISET SELESAI 2026-07-14 (verifikasi web dokumen resmi + agregator) — PROPOSAL DIAJUKAN, MENUNGGU KETOK OWNER.** Hasil:

  | Kandidat | Pola API | 9:16 | Durasi | Harga (verifikasi 07-2026) | Catatan |
  |---|---|---|---|---|---|
  | **fal.ai (agregator) — REKOMENDASI** | Queue seragam SEMUA model: `POST queue.fal.run/{model}` → request_id+status_url → poll → hasil; webhook opsional; auth `Authorization: Key` (1 kunci semua model) | ✓ | per-model (Kling: 5/10s) | per-detik/per-video per-model (Kling 3 ~$0.03–0.28/s · Wan 2.5 $0.05/s · Veo 3 $0.4/s) + **API harga programatik `GET api.fal.ai/v1/models/pricing`** | Persis kriteria owner: parameter seragam + billing seragam + katalog 1000+ model → vendor TAK terkunci; pricing API = auto-sync harga BYOK (selaras B2) |
  | Replicate (agregator) | Predictions API async (status starting/processing/succeeded/failed; poll/webhook; timeout 30m) | ✓ (per-model) | per-model | per-model | Layak = transport KEDUA nanti (arsitektur _TRANSPORTS memungkinkan) |
  | Veo via Gemini API (langsung) | Gemini API | ✓ (Veo 3.1: 4/6/8s) | 4/6/8s | Fast $0.15/s · Std $0.40/s | key_group `gemini` SUDAH ada; minus: hanya keluarga Veo, premium (8s Fast ≈ $1.2/klip) |
  | Kling direct / Runway / Luma / Sora | API masing-masing (Sora akses publik standalone masih terbatas; Runway/Luma kredit-based) | ✓ sebagian | bervariasi | Sora $0.10/s base | Format TIDAK seragam antar-vendor → biaya adapter per-vendor; lewat agregator lebih efisien |

  **Proposal ketok:** transport perdana = **fal.ai**; model perdana di katalog = **Kling text-to-video** (fotorealistis manusia kuat, 9:16, 5/10s, murah — varian persis + harga dikunci di F1 via pricing API) + opsional baris premium **Veo 3.1 Fast (via fal)**. Uji kualitas "wanita fotorealistis" dgn sampel NYATA = bagian F1/F4 (butuh kunci nyata), sesuai §0.7.
  Sumber: [docs.fal.ai queue](https://docs.fal.ai/model-apis/model-endpoints/queue) · [fal pricing API](https://fal.ai/docs/platform-apis/v1/models/pricing) · [fal model Kling](https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/pro/text-to-video/api) · [Replicate lifecycle](https://replicate.com/docs/topics/predictions/lifecycle) · [fal.ai pricing](https://fal.ai/pricing) · riset harga Veo/Sora Jul-2026 (buildmvpfast/aifreeapi/fluxnote).

### F1 — DB (katalog + niche default + 1 migrasi kecil) — ⬜
- Baris `ai_providers`: vendor terpilih (`provider_key`, `key_group` baru, `auth_type`, `free_tier_note`).
- Baris `ai_models` component=`'video'`: `model_id`, `pricing` (per-detik/per-klip; `pricing_locked`), `default_params` (aspect 9:16, durasi klip, resolusi), `quality_tier`, `cost_hint`.
- **Niche default 8s (keputusan owner §0.6):** niche baru khusus kutipan/afirmasi/motivasi via editor `/admin/niches` (admin-data, bukan hardcode): VISUAL DNA sinematik-motivasi (lighting/camera/motion/atmosphere) + gaya narasi kutipan (1 kalimat kuat) + keywords/hashtag/kategori YouTube + kaitan `format_profiles.motivational_quote`. Redaksi DNA final = proposal → ketok owner.
- Migrasi: `duration_presets.trailing_silence_override numeric NULL` (knob admin-editable; 8s ≈1.0s — default 2.5s = 31% durasi video; NULL = perilaku lama; config-driven §3.3).
- 8s `is_active` TETAP false sampai F4 lulus.
- **REALISASI:** ⬜

### F2 — BE (inti mesin) — ⬜
| File | Perubahan |
|---|---|
| `src/providers/visual/ai_video.py` | Tulis ulang jadi provider NYATA pola `ai_image.py`: `_TRANSPORTS` per-platform (perdana = hasil F0), submit→poll async→download klip 9:16; `cost_meter.add_video`; no-fallback (gagal = VisualError jujur, §3.8) |
| `src/utils/cost_meter.py` | `add_video(model, seconds/clip)` + harga dari `ai_models.pricing` (selaras add_image) |
| `src/intelligence/script_engine.py` | STEP 4.5 cabang render `ai_video`: SATU prompt gerak (narasi final + VISUAL DNA incl. key `motion` + arah kamera + larangan teks-dalam-video) |
| `src/orchestrator/pipeline.py` | STEP 4: skip hook-optimize bila `hook` ∉ beats aktif; `script["hook"]` = kalimat pertama core UTK metadata; STEP 0: koherensi preset ber-`render_mode='ai_video'` (via `format_catalog`) WAJIB `visual_mode` `ai_video:*` → fail-loud |
| `src/production/visual_assembler.py` | Branch `ai_video:` NYATA: registry → 1 klip durasi ≥ (audio+trailing) → path; no-fallback |
| `src/production/video_renderer.py` | Verifikasi jalur 1-klip (trim `-t`, tpad freeze, trailing dari knob preset F1); ubah HANYA bila bukti uji menuntut — nol perombakan spekulatif |
- Overlay judul-hook TIDAK dirender utk 8s (hook kosong — verifikasi `_add_hook_title` skip).
- **REALISASI:** ⬜

### F3 — FE (kecil) — ⬜
- `validate-key.ts` + `KNOWN_PROVIDERS`: case vendor F0 ("Test koneksi" /integrations + Test Lab — satu sumber, nol duplikat).
- Channel setting: cegah DI TITIK INPUT (§3.1) — pilih preset 8s tanpa model video → disabled + keterangan dwibahasa (mekanisme `Bi`).
- `/admin/catalog`: verifikasi baris component video tampil (editor generik — kemungkinan nol kode).
- Test Lab: dukung model video utk uji admin (cek; tambah kecil bila perlu).
- **REALISASI:** ⬜

### F4 — BUKTI RUNTIME → aktivasi → deploy — ⬜
1. Produksi 8s NYATA e2e di channel uji **dengan niche default kutipan/motivasi (F1)**, **publish PRIVATE** (§6.6), kunci vendor nyata.
2. **Presisi durasi (gerbang F4 §7.3): ffprobe output 8s ±15% (6.8–9.2s), MINIMAL 3 run.**
3. Bukti per-permukaan (§3.4 per-WIDGET): QC pass · baris biaya video tercatat + tampil di FE run cost · caption/karaoke tampil · musik (bila aktif) · Telegram report normal · analytics snapshot masuk · analyzer tidak error dgn video 8s.
4. **Nol regresi (§3.8):** 1 run preset 60s channel nyata TETAP normal.
5. Baru: flip `duration_presets.8.is_active=true` via admin + sinkron dokumen ([B6] + `MULTI_FORMAT_STUDIO` changelog) + **deploy per §5 (izin eksplisit owner)**.
- **REALISASI:** ⬜

## 3. Risiko & mitigasi
- **⚠️ Monetisasi YouTube vs konten AI repetitif (relevan LANGSUNG dgn tujuan §0.7 "kejar YPP"):** genre "quote + wanita AI cantik" = genre farm yang populer justru KARENA formula ini — dan karena itu masuk radar kebijakan "inauthentic/mass-produced content" YouTube (syarat monetisasi). Mitigasi: diversity engine merotasi wajah/latar/wardrobe/voice antar-video (jangan 1 wanita template) + narasi afirmasi unik per-video (bukan daur ulang) + AI disclosure existing + posisikan 8s sebagai PELENGKAP channel (60s tetap mayoritas) — bukan channel 100% quote-farm.
- **⚠️ Batas aman-iklan penggambaran wanita:** "super cantik" TIDAK boleh tergelincir sugestif (limited ads / age-restriction / demonetisasi). Mitigasi: guardrail keras di VISUAL DNA niche (elegan, berpakaian pantas, framing wajah-dan-bahu/full-figure berkelas, larangan pose/pakaian sugestif — pola `strict_prohibition` yang sudah ada) + review manual video-video awal via publish private.
- **Latency vendor 1–3 mnt/klip** → submit→poll ber-timeout; worker async menampung; timeout = gagal jujur + Telegram (no-fallback).
- **Klip vendor < durasi audio** → minta durasi klip ≥ audio+trailing; renderer trim; vendor durasi-fix (5/10s) → pilih ≥ kebutuhan lalu trim.
- **Harga vendor berubah** → `ai_models.pricing` admin-editable + `pricing_locked`; tanpa harga → badge "belum lengkap" (mekanisme existing).
- **Model menolak 9:16 / menyisipkan teks dalam video** → `default_params` per-model (DB) + negative instruction di prompt video; QC visual manual awal via publish private.

## 4. Bukan lingkup (temuan baru → daftar usulan, §2.3e — dilarang "sekalian")
Multi-klip ai_video utk preset >8s · multi-platform Reels/TikTok ([D2]) · perubahan word-budget di luar jalur existing · perubahan UI besar.
