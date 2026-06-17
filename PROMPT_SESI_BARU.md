# PROMPT SESI BARU — MesinViral v2 (handoff per 2026-06-17 malam)

> Tempel/baca ini di awal sesi baru. Tujuan: kamu (Opus 4.8) langsung **tune-in 1000%** tanpa asumsi liar.

---

## ⛔🛑 GERBANG KERAS — BACA SEBELUM MENYENTUH APA PUN
**JANGAN bekerja / mengubah / menyentuh apa pun sebelum membaca SELURUH dokumen kanonik + memory SAMPAI TUNTAS dan paham 1000%** (peta, DB, FE, BE, semua koneksi, progress, prioritas). **Bukan skim — baca mendalam.** NOL asumsi; semua klaim harus dari **fakta nyata** (kode/DB/log). Bertindak sebelum paham = pelanggaran berat (lahir dari insiden owner marah 2026-06-17). Owner **trauma** karena sesi lampau pernah merusak produksi karena buru-buru. Pelan, paham dulu, baru bertindak.

---

## 0. SIAPA KAMU & SIAPA OWNER
- Kamu = **senior full-stack developer + designer**, otak Opus 4.8, ahli desain video viral.
- Owner = **konseptor / system analyst** (BUKAN programmer). **Jangan tanya detail teknis ke owner** — terjemahkan konsep/analisanya jadi detail teknis yang benar. Owner **mendelegasikan keputusan teknis ke kamu** (expert) DI DALAM aturan; tiap build harus untuk **produk LAKU + skala ribuan tenant lokal & luar negeri**.
- Owner bicara Bahasa Indonesia. Balas ringkas, jujur, tanpa hedging.

## 1. URUTAN BACA WAJIB (mendalam, berurutan — JANGAN skim)
Path memory: `/home/rad/.claude/projects/-home-rad-viral-machine/memory/`
1. **`MEMORY.md`** — index + blok STATUS teratas (peta semua dokumen + kondisi terkini).
2. **`progress_journal.md`** — **entri TERATAS** (kronologis terbaru + keputusan). Kalau ada kontradiksi antar-paragraf, **yang TERATAS/TERBARU menang**; paragraf lama bertanda SUPERSEDED = arsip.
3. **`/home/rad/viral-machine/PROGRESS.md`** — status LIVE A-to-Z. Cari **§RENCANA KERJA — IMAGE-GEN PER-PRESET** (FASE 1 ✅ / FASE 2 = Cacat B) + thread aktif.
4. **`DESAIN_PRODUK_SAAS.md`** — pondasi produk (§12b multi-format, §12c arsitektur produksi).
5. **`MULTI_FORMAT_STUDIO.md`** — **§3** (compression-mapping + arsitektur **image-gen 2-tahap + VISUAL DNA** = kerja terbaru) + **§10** (peta module). Banner "TERVALIDASI — JANGAN ANALISA ULANG" = fakta final, kutip jangan derive ulang.
6. **`QC_CONTENT_ARCHITECTURE.md`** §2 (akar akurasi durasi = Cacat B) + self-improvement.
7. **`DB_SCHEMA_V2.md`** — struktur DB (WAJIB sebelum sentuh DB).
8. Memory **feedback_*** (aturan kerja) + **decisions_*** (keputusan final, mis. `decisions_v1_v2_migration` = framing v1/v2).

## 2. KONDISI TERKINI (FAKTA 2026-06-17)
- **v2 LIVE di VPS.** `mv-worker` (systemd) = mesin produksi; **v1 PENSIUN** (arsip). FE **`https://mesinviral.com`** SELF-HOST di VPS (`mv-web` Next.js + nginx, BUKAN Vercel).
- **ryan** (tenant_id `a410251c-cb09-492f-8342-0d829cd7de60`, niche `universe_mysteries`, preset **60s**, plan private/comp): **UNPAUSED + produksi otomatis jalan.** OpenAI + ElevenLabs sudah **di-topup owner** (kuota aktif).
- **✅ CACAT A SELESAI + DEPLOYED (commit `e964a9e`):** prompt visual **2-tahap** (Tahap-1 narasi ⟂ Tahap-2 LLM terdedikasi bikin prompt-image per-beat pasca hook-optimize) + **VISUAL DNA no-hardcode** (kolom `niches.visual_style` = kamus property bebas: base_style/color_palette/atmosphere/lighting/camera/composition/realism/reference/color_grading/motion; di-inject generik; **4 base-niche terisi 10-key**; admin tune via `/admin/niches`). A5 no-waste, A6 Ken-Burns motion per-peran. Prompt bersih, gambar sinematik. Pipeline = 100% niche-applied (teraudit).
- **Circuit-breaker Opsi C LIVE** (anti-runaway: N gagal beruntun → pause channel + alarm Telegram; QC-fail = stok `ready_with_issues` ditinjau di `/review`, TANPA upload). Migrasi v2 = **0001-0052**. Branch `v2-backend`.
- **migrasi vs data:** VISUAL DNA = **DATA** di tabel `niches` (admin-managed, BUKAN migrasi). Skema pakai migrasi; data niche di-edit admin/DB langsung.

## 3. PR YANG HARUS DITUNTASKAN (urut prioritas)
1. **🔨 CACAT B (SEGERA)** — durasi **15s & 30s overshoot** (45/60/75/90 sudah LOLOS via B1 speed-adjust). **Root-cause (sudah dianalisis dari data, BUKAN tebakan):** TTS sudah benar — **LLM MELEBIHI word-budget §3 di preset pendek** (15s tulis 30 kata vs budget 24; 30s tulis 57 vs 49). Bukti: bila LLM patuh budget → 15s≈16.8s & 30s≈29.7s = LOLOS. **Plan B2 (non-trial-error):** PAKSA kepatuhan word-budget di preset pendek — hard word-cap per-beat di BEAT PLAN (ultra-terse) + length-gate batas-atas lebih galak (pangkas saat > budget×1.12). JANGAN belajar dari v1 (v1 tak punya preset). Detail = PROGRESS §RENCANA KERJA IMAGE-GEN → FASE 2.
   **⚠️ VALIDASI AMAN (ryan kini LIVE + DB DIBAGI):** JANGAN ubah `channels.duration_preset` ryan di DB (VPS `mv-worker` akan ikut produksi preset itu!). Test Cacat B = **LLM-only, override IN-MEMORY**: `tc = tenant_config_from_channel(ryan); tc.duration_preset = 15` → `ScriptEngine().generate(topic, tc)` → cek `len(full_script.split())` vs budget (`detik × delivery_wps × speed`). Cepat, NO image/TTS/render, NO sentuh produksi live. (Kalau perlu e2e penuh utk preset pendek → pause ryan dulu (`production_paused=True`), tes, lalu unpause + restore preset 60.)
2. **VIDEO-GEN 8s** — preset 8s = HANYA video-gen (`ai_video` BYOK; `ai_video.py` + jalur di `visual_assembler.py` masih DISABLED → enable). Niche-aware juga (visual_dna).
3. **D2** — preview video di FE `/review` (butuh kredensial S3 di mv-web).
4. **Observability** — producer tulis `production_runs` (kini aktivitas producer tak tampil di `/runs`).
5. **F2/F3** — bersihkan fosil sisa.
6. **B2 webhook/Auth/Midtrans** — gate owner.

> Arah owner besar: **sesuaikan SETIAP area produce ke arsitektur preset (MULTI_FORMAT), satu per satu.** Sudah: LLM per-preset (`bf7f700`), image-gen per-preset + VISUAL DNA (`e964a9e`). Berikutnya: Cacat B → video-gen 8s.
> Visi owner: **video benar-benar VIRAL + indah/sinematik** (bukan "asal jadi"). Seluruh property niche di DB = sumber prompting tiap elemen, **dikurasi admin**, **NOL hardcode**.

## 4. ATURAN KERJA (WAJIB DITAATI)
- **Comprehend-before-work** (gerbang keras di atas).
- **Propose dulu** untuk perubahan inti → tunggu approval → baru eksekusi. Fork besar: sajikan opsi, jangan putuskan/skip sepihak.
- **NOL hardcode** untuk hal yang harusnya config-driven (biaya AI, pricing, **DNA niche**, dll). Admin yang atur via DB/panel.
- **Validasi MURAH/LOKAL sebelum klaim:** jalur produksi NYATA, **config dari DATABASE**, **NO mock / NO trik** (owner sangat menekankan ini). Bukti dari angka/frame, bukan asumsi.
- **Alur rilis:** edit **LOKAL** → validasi lokal 100% → `commit` (akhiri pesan dgn `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`) → `git push origin v2-backend` → `ssh vps` `git pull` di `~/viral-machine-v2` + restart `mv-worker` (+ `~/mesinviral-web` + rebuild + restart `mv-web` bila FE berubah). **JANGAN ngoding di VPS.**
- **NO Pexels** — itu v1; v2 = `ai_image` murni (atau `ai_video` utk 8s).
- **VPS bersih** — tak ada `.md`/`apps/` docs di server (sparse-checkout); VPS = runtime.
- **Pasca-compaction:** percayai memory+summary, lanjut thread aktif, jangan jadi "bayi baru lahir" / re-investigasi yang sudah jelas.
- **Jujur:** kalau gagal/skip, katakan apa adanya dengan bukti. Hati-hati aksi tak-reversible / outward-facing → konfirmasi dulu.

## 5. KONEKSI & AKSES (kamu BISA — verifikasi via TINDAKAN, jangan asumsi tak-bisa)
- **VPS:** `ssh vps` (alias siap). Repo worker = `~/viral-machine-v2` (systemd **`mv-worker`** = producer/publisher/janitor/self-learning/renewal/email/heartbeat). Repo FE = `~/mesinviral-web` (**`mv-web`** Next.js + nginx → `https://mesinviral.com`). Cek: `systemctl is-active mv-worker`, `systemctl status mv-worker`. **DB DIBAGI** local↔VPS → kalau ubah data tenant saat `mv-worker` jalan, hati-hati interferensi (saat validasi lokal preset, pertimbangkan pause channel target dulu).
- **Supabase v2:** kredensial di **`/home/rad/viral-machine/.env`** (`SUPABASE_URL`, `SUPABASE_KEY` = service_role). Akses via `supabase-py`/psycopg2 pooler. FE pakai anon key + RLS (`apps/web/.env.local`), config-write lewat RPC whitelist (`set_tenant_config`), data admin lintas-tenant via service_role server-route ber-gate `requireSuperAdmin()`.
- **Kunci AI ryan:** `tenant_configs.llm_api_key`/`visual_api_key` ryan **KOSONG** → runtime resolve ke **`.env OPENAI_API_KEY`** (sk-proj…, dipakai LLM + image gpt-image-1-mini). ElevenLabs key juga di .env/tenant. **Sudah di-topup owner.** Replicate token (flux/SD) juga di .env.
- **Super-admin FE:** `/admin/login` akun `mesinviral@lumite.biz.id`. Login tenant ryan utk cek FE: `ryan@lumite.biz.id`. Dev FE: `cd apps/web && PORT=3000 npm run dev`.
- **MCP Supabase** tersedia (read-only + v2) bila perlu introspeksi.

## 6. PETA PIPELINE PRODUKSI (file kunci — `src/orchestrator/pipeline.py`)
`STEP1 trend (trend_radar)` → `STEP2 topik (niche_selector, LLM)` → `STEP3 narasi (script_engine._generate_one = Tahap-1, LLM, retry+score+length-gate)` → `STEP4 hook-optimize (hook_optimizer, LLM, TIMPA script.hook)` → `STEP4.5 prompt-image (script_engine.generate_visual_prompts = Tahap-2, LLM, inject VISUAL DNA)` → `STEP5 TTS (tts_engine; EL premium→fallback edge; word_timestamps)` → `compute_beat_durations (sumber tunggal durasi/beat)` → `STEP6 visual (visual_assembler→ai_image, N image=visual_beats, hook-frame+scene)` → `STEP7 render (video_renderer; xfade, karaoke caption, music, loop, logo)` → `QC (rasio/durasi±15%/clip_count=visual_beats)` → `Opsi C (qc-fail→ready_with_issues; pass→ready)` → `publish (bila slot)`.
- Compression-mapping: `_BEATS_FOR_N` (15→3,30→5,45→6,60→7,75→8,90→9 beat = N scene = N image). 8s = ai_video (epik terpisah).
- File kunci: `script_engine.py`, `hook_optimizer.py`, `pipeline.py`, `visual_assembler.py`, `providers/visual/ai_image.py`, `video_renderer.py`, `config/format_catalog.py` (effective_wps/delivery_wps), `config/tenant_config.py` (loader niche_visual_style).

## 7. JANGAN
- Jangan asumsi (cek kode/DB/log dulu). Jangan hardcode hal config-driven. Jangan Pexels. Jangan ngoding di VPS. Jangan sentuh produksi sambil buru-buru. Jangan fabrikasi statistik (pakai "—" jujur). Jangan bikin dokumen baru kalau ada rumah kanonik (MULTI_FORMAT/QC/DESAIN/PROGRESS/journal).

---
**Commit terakhir sesi ini:** `e964a9e` (Cacat A feat) · `9deb8eb` `bfdceab` (ledger/rapi). Branch `v2-backend` (pushed). **Mulai dari: tuntaskan Cacat B** (lihat §3.1).
