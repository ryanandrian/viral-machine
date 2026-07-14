# [B6] PRESET 8 DETIK — RENCANA IMPLEMENTASI ai_video (text-to-video)

> **Status:** 📋 RENCANA MATANG (2026-07-14) — hasil deep-dive kode + DB live (nol asumsi), **menunggu ketok owner untuk mulai F0**.
> **Kaitan:** backlog tunggal = `SISA_KERJA_GO_LIVE.md` **[B6]** (dokumen ini = SPEC+tracker-nya, pola `PROGRAM_BUKTI_KECERDASAN.md`). Spec teknis induk = `MULTI_FORMAT_STUDIO.md §3/§5`. Prioritas jujur (§7 kompas): TIDAK memblok tenant berbayar pertama.

## 🧭 CARA LANJUT (resume pasca-compaction/sesi baru — baca INI dulu, jangan riset ulang)
1. **POSISI SEKARANG: 🟢 F0–F3 ✅ TUNTAS 2026-07-14 (kode lengkap, teruji-asap, build bersih, SEMUA dorman, BELUM deploy) — tersisa F4 BUKTI-RUNTIME yang MENUNGGU 3 hal dari OWNER: (1) kunci API fal.ai nyata (owner buat akun fal.ai → API key), (2) izin deploy batch B6 (BE+FE — catatan: deploy BE juga mengaktifkan B15 yang sudah antre), (3) jendela uji. Urutan F4 = deploy → simpan kunci fal (uji validator) → aktifkan model+preset sementara → produksi 8s channel uji PRIVATE ≥3 run (presisi 6.8–9.2s) → regresi 60s → aktivasi final + sinkron dokumen.** (Bila baris ini basi vs REALISASI di bawah → REALISASI menang; perbarui baris ini.)
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

  **PERLUASAN RISET (permintaan owner 2026-07-14): fal.ai vs Replicate + cakupan LLM/TTS/image (visi "1 akun agregator utk seluruh channel tenant"):**
  - **Mengapa fal.ai > Replicate (pertimbangan kuat, terverifikasi):** (1) **API harga programatik terdokumentasi** (`GET api.fal.ai/v1/models/pricing`) → harga BYOK auto-sync ke `ai_models.pricing` (padanan di Replicate TIDAK kami temukan terdokumentasi); (2) **ElevenLabs RESMI tersedia di fal** — `elevenlabs/tts/turbo-v2.5` & `eleven-v3` = MODEL PERSIS yang sudah ada di katalog kita → kualitas suara identik, tenant tak kehilangan apa pun (Replicate: TTS open-source saja, ElevenLabs resmi tidak kami temukan); (3) fal = platform **media-first** (image/video/audio, queue + CDN output) vs Replicate general model-hosting; (4) LLM: KEDUANYA punya jalur OpenAI-compatible (fal: router OpenRouter "GPT/Claude/Gemini dst" auth kunci fal; Replicate: chat-completions + model resmi openai/anthropic/google) — seri; (5) katalog video: keduanya lengkap — seri. Replicate TETAP dicatat sbg transport KEDUA masa depan (vendor tak terkunci).
  - **Cakupan fal utk 4 komponen (peta ke adapter existing kita):** LLM = router OpenAI-compatible → transport `openai` existing (ganti base_url + kunci fal; kerja kecil) · TTS = ElevenLabs model sama (transport fal queue = adapter TTS kecil; Edge-TTS gratis tetap jalur existing) · Image = keluarga FLUX sama dgn yang kita pakai (flux-1-schnell; +1 entry `ai_image._TRANSPORTS`) · Video = adapter baru (inti B6).
  - **⚠️ Kejujuran lingkup:** "1 kunci fal utk semua" BENAR tersedia di sisi fal, tapi tiap komponen tetap butuh transport-fal kecil di sisi kita → masuk **F5 (roadmap opsional, ketok terpisah)** — BUKAN bagian B6/8s (anti scope-creep §2.3e). B6 hanya butuh komponen video.
  Sumber tambahan: [fal ElevenLabs turbo-v2.5](https://fal.ai/models/fal-ai/elevenlabs/tts/turbo-v2.5) · [fal ElevenLabs v3](https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3) · [fal router OpenAI-compatible](https://fal.ai/models/openrouter/router/openai/v1/responses/api) · [fal TTS explore](https://fal.ai/explore/text-to-speech-apis) · [Replicate language models](https://replicate.com/collections/language-models) · [Replicate blog model OpenAI](https://replicate.com/blog/openai-chat-models).
  Sumber: [docs.fal.ai queue](https://docs.fal.ai/model-apis/model-endpoints/queue) · [fal pricing API](https://fal.ai/docs/platform-apis/v1/models/pricing) · [fal model Kling](https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/pro/text-to-video/api) · [Replicate lifecycle](https://replicate.com/docs/topics/predictions/lifecycle) · [fal.ai pricing](https://fal.ai/pricing) · riset harga Veo/Sora Jul-2026 (buildmvpfast/aifreeapi/fluxnote).

### F1 — DB (katalog + niche default + 1 migrasi kecil) — ⬜
- Baris `ai_providers`: vendor terpilih (`provider_key`, `key_group` baru, `auth_type`, `free_tier_note`).
- Baris `ai_models` component=`'video'`: `model_id`, `pricing` (per-detik/per-klip; `pricing_locked`), `default_params` (aspect 9:16, durasi klip, resolusi), `quality_tier`, `cost_hint`.
- **Niche default 8s (keputusan owner §0.6):** niche baru khusus kutipan/afirmasi/motivasi via editor `/admin/niches` (admin-data, bukan hardcode): VISUAL DNA sinematik-motivasi (lighting/camera/motion/atmosphere) + gaya narasi kutipan (1 kalimat kuat) + keywords/hashtag/kategori YouTube + kaitan `format_profiles.motivational_quote`. Redaksi DNA final = proposal → ketok owner.
- Migrasi: `duration_presets.trailing_silence_override numeric NULL` (knob admin-editable; 8s ≈1.0s — default 2.5s = 31% durasi video; NULL = perilaku lama; config-driven §3.3).
- 8s `is_active` TETAP false sampai F4 lulus.
- **REALISASI:** 🟡 **SEBAGIAN 2026-07-14 (ketok owner "setuju fal.ai + Kling"):**
  (a) ✅ **Katalog masuk DORMAN** via REST (pola preseden gemini-image "NONAKTIF s.d. lulus uji"): `ai_providers.fal` (key_group `fal`, base_url queue.fal.run, `is_active=false`) + `ai_models` video: `kling-2.5-turbo-pro` (model_id `fal-ai/kling-video/v2.5-turbo/pro/text-to-video`, $0.35/5s + $0.07/s, default_params 9:16/5s/negative_prompt TERVERIFIKASI dari halaman API) & `veo-3.1-fast` (`fal-ai/veo3.1/fast`, $0.10/s, param API diisi F2), keduanya `is_active=false`. **BUKTI DORMAN (replikasi query permukaan tenant):** model video aktif = `[]` · fal TIDAK ada di provider aktif → nol perubahan perilaku produksi/FE.
  (b) ✅ **Migrasi 0161 APPLIED+VERIFIED** (via pooler v2, kredensial = `SUPABASE-CONNECTION.md` §VER-2 — password mengandung `@`, parse rsplit): kolom + CHECK ada, seed 8s=1.0, preset lain NULL (perilaku lama utuh).
  (c) ✅ **Niche default `radiant_affirmations` DIBUAT DORMAN** (ketok owner "prinsipnya setuju — tetap sopan, tapi wanita SUPER cantik & menarik demi retensi"): DNA 13-key (subject super-cantik-magnetik + `strict_prohibition` aman-iklan + rotasi etnis/rambut/busana/lokasi per-video) · persona 1-kalimat afirmasi orang-kedua · scoring "personal revelation" · 4 exemplar · mood inspirational/calm/upbeat (diverifikasi ada di library) · kategori 22 · `is_active=false`. **BUKTI DORMAN:** tidak muncul di query katalog publik-aktif (replikasi Pustaka Niche).
  **→ F1 TUNTAS 2026-07-14. Berikutnya: F2 (BE inti — adapter fal + prompt video + assembler + cost meter + koherensi STEP 0).**

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
- **REALISASI:** ✅ **KODE TUNTAS + uji-asap 5/5 LULUS 2026-07-14** (bukti runtime e2e = gerbang F4):
  (1) `ai_video.py` DITULIS-ULANG penuh — transport `fal` (submit `queue.fal.run/{model_id}` → poll status_url [IN_QUEUE/IN_PROGRESS/COMPLETED, interval 5s, timeout 600s gagal-jujur] → response_url → unduh; body = default_params − kunci META {duration_param, allowed_durations} + prompt; durasi dipilih TERKECIL-yang-cukup dari allowed [5,10]; ffprobe bukti durasi; `model_row` injection utk Test Lab; no-fallback);
  (2) `cost_meter.add_video` (detik-tertagih) + `ai_cost` video (per-detik ATAU basis+extra — Kling 10s=$0.70 ✓, Veo 8s=$0.80 ✓, usage lama tanpa kunci video AMAN ✓; FE hanya baca usd/unpriced → nol regresi tampilan);
  (3) `script_engine.generate_video_prompt` (Tahap-2 varian VIDEO: DNA penuh + gerak+kamera+larangan, fallback ekstraktif) + STEP 4.5 bercabang `preset_render_mode`;
  (4) STEP 4 SKIP utk preset tanpa beat hook (hook tetap "" → overlay `_add_hook_title` & blok deskripsi publisher otomatis skip — keduanya guard `if hook`);
  (5) STEP 0 koherensi dua-arah preset⇄visual_mode (fail-loud pra-biaya);
  (6) trailing EFEKTIF per-preset SATU rumus di 3 pemakai (script budget · gerbang durasi · renderer) via `format_catalog.effective_trailing` — preset lain NULL → perilaku lama IDENTIK ✓;
  (7) assembler `_try_ai_video` (1 klip ≥ audio, no-fallback) + registry family sudah ada;
  (8) Katalog Kling +META `duration_param`/`allowed_durations`. Kompilasi 8 file OK; pagar dorman terbukti (build via katalog-aktif DITOLAK utk model non-aktif → produksi hari ini mustahil tersentuh).

### F3 — FE + validator kunci (kecil) — 🟡 BERJALAN 2026-07-14
- **TEMUAN pre-touch (jangan riset ulang):** validator kunci tenant NYATA = **vault Python** `src/utils/api_key_vault.py` (`_ai_test`/`validate_ai_key`, jalur `/api/credentials/ai` → mv-webhook) — BUKAN `validate-key.ts` (TS hanya onboarding + admin Test Lab). Resep GENERIK vault (GET {base_url}/models, Bearer) TIDAK cocok utk fal (auth `Key`; base=queue.fal.run bukan API list) → fal wajib resep KHUSUS.
- Eksekusi: (a) vault `_ai_test` case fal (probe `GET api.fal.ai/v1/models/pricing?endpoint_id=…`, header `Authorization: Key`; 200=valid · 401/403=invalid · lainnya='unchecked' JUJUR — kepastian final diuji F4 kunci nyata); (b) `validate-key.ts` case 'fal' (probe sama, satu semantik); (c) Channel setting: gating DI TITIK INPUT preset⇄model-video (dwibahasa `Bi`, §3.1); (d) verifikasi admin catalog menampilkan component video; (e) Test Lab video: CEK — tambah bila trivial, else defer (catat).
- **REALISASI:** ✅ **TUNTAS 2026-07-14** (build FE bersih + vault terkompilasi; belum deploy — gerbang F4):
  (a) ✅ vault `_ai_test` case `fal` (probe pricing-API auth `Key`) + leniency `validate_ai_key` (200=valid · 401/403=invalid · lainnya='unchecked' jujur, anti false-negative pola F1-09 EL — kepastian final = F4 kunci nyata);
  (b) ✅ `validate-key.ts` + `KNOWN_PROVIDERS` case 'fal' (probe & semantik sama — dipakai onboarding+Test Lab);
  (c) ✅ Gating input Channel Setting dua-arah (savePreset ⇄ saveVisual: preset ai_video wajib model video & sebaliknya; pesan dwibahasa "ID / EN"; peta `presetModes` dari `duration_presets` [RLS publik sama dgn preset-tables]; nilai pembanding = nilai TERSIMPAN `ch.*` → konsisten dgn yang dipakai produksi; BE STEP 0 tetap backstop). Channel existing (model gambar + preset non-8s) = lolos tanpa perubahan perilaku;
  (d) ✅ Admin catalog: VERIFIED generik — component video tampil tanpa kode (help text sudah menyebut image/video);
  (e) ✅ Test Lab: VERIFIED SUDAH mendukung model video sejak dibangun (`visualModels` incl component video → prefix `ai_video:`) — nol kode.
  **→ F3 TUNTAS. Berikutnya F4: butuh (1) kunci fal NYATA dari owner, (2) izin deploy BE+FE batch B6, (3) jendela uji.**

### F3b — VALIDASI PRA-DEPLOY (mandat owner 2026-07-14 "pastikan 100% valid sebelum deploy") — ✅ LULUS
- **Review-ulang kritis SELURUH diff batch** (f554e38→HEAD, 20 file kode): pipeline (4 sentuhan — aman; steps.hook.score tanpa konsumen eksternal; FE run-detail derivasi log → efek skip hanya kosmetik-sesaat) · assembler/renderer/vault/meter/ai_cost ✓ · B15 analytics ✓ sesuai desain teruji 8/8.
- **🔴→✅ 1 KELEMAHAN DITEMUKAN & DIPERBAIKI:** `generate_video_prompt` — `get_llm_provider()` RAISE (bukan None) bila LLM tak terkonfigurasi → janji fallback-ekstraktif bisa gagal (di produksi mustahil krn STEP 3, tapi janji harus utuh). Fix: try/except → fallback; re-test LULUS.
- **BUKTI RUNTIME LOKAL jalur 1-klip (simulasi persis klip Kling, TANPA kunci fal):** klip sintetis 10s + audio 6.2s + preset 8 → renderer: trailing override **1.0s AKTIF** · trim presisi (6.233s=audio) · Step B audio+SRT · loop-ending → **OUTPUT FINAL 8.267s — DI DALAM window QC 6.8–9.2s ✓** · overlay judul-hook benar-benar ABSEN (hook kosong) · nol crash. Fallback ekstraktif video-prompt: OK.
- Sisa yang HANYA bisa dibuktikan dgn kunci fal nyata (F4): probe validator fal · generate klip nyata · kualitas visual wanita fotorealistis.

### F3c — KOREKSI TEGURAN OWNER 2026-07-14 (fallback senyap = pelanggaran §3.3) — ✅ DIKOREKSI + AUDIT TOTAL
- **3 fallback senyap buatan saya DIBUANG → gagal-jujur (semua diuji ulang, LULUS):** (1) prompt-video LLM gagal/cacat → `LLMError` STOP (dulu: prompt rakitan mekanis diam-diam); (2) audio > durasi maks vendor → `VisualError` STOP (dulu: freeze-frame); (3) klip vendor < audio → `VisualError` STOP (dulu: freeze-frame). Memory `feedback_no_hardcode` dikeraskan: **perilaku saat-gagal = keputusan produk, default tanpa ketok = GAGAL JUJUR; "pola lama" bukan pembenaran.**
- **Audit total keputusan-sendiri lain (diungkap transparan):** (a) **DEVIASI dari teks rencana:** rencana menulis `script["hook"]=kalimat pertama core utk metadata`, implementasi = hook dibiarkan KOSONG (lebih aman: mencegah overlay judul & blok deskripsi ikut aktif; judul video tetap dari `script['title']`) — menunggu koreksi owner bila tak setuju; (b) vault fal: probe tak terjawab pasti → status **'unchecked'** (bukan valid palsu; kunci unchecked TIDAK dipakai worker — resolver pool hanya ambil status='valid' → gagal-jujur STEP 0) — kepastian probe = F4; (c) konstanta teknis reversible dlm mandat (§2.3c, dicatat): poll 5s/timeout 600s · prompt video temp 0.7/350tok · skema kunci pricing video (per_second_usd / basis+extra); (d) redaksi DNA niche = kerangka diketok owner + penekanan "super cantik & sopan" — baris dorman, wording bisa dikoreksi owner kapan pun.
- **Bukti NOL kerusakan produksi:** semua jalur baru dorman (model non-aktif DITOLAK katalog; preset 8s off; provider fal tersembunyi) · worker VPS belum tersentuh kode ini · produksi harian normal (log 13-14 Jul).

### F4 — BUKTI RUNTIME → aktivasi → deploy — 🟡 BERJALAN 2026-07-14
- **✅ Langkah 1 — DEPLOY (izin owner "silahkan deploy" 2026-07-14):** BE OK 19:13 (mv-worker+mv-webhook active, health=200) · FE OK 19:27 (mv-web active, situs 200) · commit live `2a15df1` · skrip resmi §5 · worker pasca-restart sehat (0 error, siklus normal) · **B15 ikut AKTIF**. Kondisi: kode B6 LEMBAM (model video 0 aktif ✓, preset 8s off ✓).
- **✅ Langkah 2 — vendor fal DIAKTIFKAN di katalog** (muncul di /integrations utk input kunci; model & preset tetap dorman — verified).
- **✅ Langkah 3 — kunci fal owner masuk & PROBE VALIDATOR TERBUKTI: status `valid`** (validated_at 2026-07-14 12:46 UTC — bukti F4 #1: resep vault bekerja pada kunci nyata percobaan pertama). Catatan owner: badge "(model segera hadir)" di /integrations = mekanisme LAMA yang benar (derivasi katalog: vendor aktif tanpa model aktif) — hilang sendiri saat model diaktifkan.
- **✅ Langkah 4a — jendela uji DIBUKA 2026-07-14 ~19:45:** model `kling-2.5-turbo-pro` AKTIF (pricing_locked) + channel **MVT** dikonfigurasi uji: niche `radiant_affirmations` (tetap dorman utk publik — get_niches TANPA filter aktif, verified) · preset 8 (kolom channel langsung; preset publik tetap off) · `visual_mode=ai_video:kling-2.5-turbo-pro` · akun fal owner · **publish_privacy=PRIVATE (§6.6)** · buffer_depth=3 (3 run uji). **SNAPSHOT PEMULIHAN MVT (kembalikan pasca-uji):** niche `legenda_daerah` (pool sama, fixed) · preset 60 · `ai_image:cf-flux-schnell` · visual_account NULL · privacy `public` · buffer_depth NULL. Stok lama 1 video 60s 'ready' akan terbit PRIVATE di slot 19:00 berikutnya (disadari; korban kecil jendela uji).
- **🟡 Langkah 4b — KRONIK UJI 2026-07-14 malam (anti-hilang pasca-compaction):** rentetan kegagalan berlapis NON-kode: saldo fal $0 (403 "User is locked") → kuota harian Groq habis (MVT llm → SEMENTARA openai/gpt-4o; **snapshot asli: groq/llama-3.3-70b-versatile, account NULL — PULIHKAN pasca-uji**) → owner ganti kunci fal 20:47 tapi channel masih menunjuk baris kunci LAMA (run 20:58 gagal 403; channel SUDAH di-repoint ke kunci baru `196f950e`). **Uji langsung setelan-produksi SUKSES 20:57** (klip Kling 10.042s/18.9MB 9:16, $0.70, body identik adapter). **Run pipeline e2e 21:29 SUKSES SAMPAI YOUTUBE PRIVATE** (`youtube.com/shorts/lq9HmUYWWnQ`): durasi video **7.5s = LOLOS window QC durasi**, klip AIVideo 10.0s/15.6MB via adapter DI PRODUKSI, render 3.3MB — satu-satunya flag QC = ukuran file.
- **🔴 2 TEMUAN dari run e2e (bug LAMA pra-B6; PROPOSAL FIX DIAJUKAN — MENUNGGU KETOK OWNER):**
  (1) **DNA visual niche channel tak pernah termuat** — loader `tenant_config._load_from_supabase` mengambil `visual_style` niche level-TENANT sebelum overlay, tanpa muat-ulang utk niche efektif channel. Bukti 3-lapis: sidik jari frasa unik DNA universe "strong single key light" VERBATIM di prompt run · reproduksi lokal (load niche radiant → log "loaded: universe_mysteries", subject KOSONG) · baris kode. Efek nyata: video 8s bergambar ASTRONOT. Fix usulan: muat-ulang visual_style+fallbacks utk niche EFEKTIF (±10 baris).
  (2) **QC ukuran-file rata `QC_MIN_SIZE_MB`=5MB tak sadar-durasi** (`pipeline.py:710`) → video 8s sehat (3.3MB) dicap "render gagal?" → paksa jalur tinjau. Fix usulan: ambang proporsional durasi preset (basis 5MB/60s), tanpa preset = perilaku lama.
  Pasca-ketok: fix → uji lokal → deploy → 1 run pembuktian (±$0.70) + ≥2 run tambahan presisi + 1 run 60s regresi → aktivasi final + PEMULIHAN penuh MVT (snapshot di Langkah 4a + llm groq). Biaya fal terpakai malam ini: $1.40 (2 klip nyata; semua kegagalan = $0).
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

### F5 (ROADMAP OPSIONAL — visi owner "1 kunci fal utk seluruh channel"; ketok terpisah, BUKAN bagian 8s)
Perluas transport fal ke komponen lain agar tenant cukup 1 akun fal: (a) LLM via router OpenAI-compatible fal (transport `openai` existing + base_url); (b) TTS ElevenLabs-via-fal (model identik turbo-v2.5/v3; adapter queue kecil); (c) Image FLUX-via-fal (+1 entry `_TRANSPORTS`). Tiap butir = baris `ai_models` baru + transport kecil; vendor existing (kunci langsung OpenAI/ElevenLabs/dll) TETAP didukung berdampingan — tenant memilih.
