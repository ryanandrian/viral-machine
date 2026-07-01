# 🚀 PROMPT SESI BARU — MesinViral (tempel/baca ini PALING AWAL)

> Halo Claude (sesi baru). Kamu melanjutkan **MesinViral** — SaaS multi-tenant yang **otomatis memproduksi + publish YouTube Shorts faceless**, LIVE di `https://mesinviral.com`. **JANGAN bertindak sebelum paham 100%.** Ikuti 4 langkah di bawah PERSIS, lalu konfirmasi ke owner sebelum eksekusi.
> **Dokumen ini di-refresh 2026-07-01** (menggantikan versi lama yang usang). Sumber kebenaran terkini di bawah.

---

## LANGKAH 1 — BACA (berurut, sampai paham; jangan skim)
1. **`MEMORY.md`** (auto-load) — ikuti "URUTAN BACA KANONIK". Pointer teratas mengarahkanmu ke file fokus:
2. **⭐ `SISA_KERJA_GO_LIVE.md`** = **FILE FOKUS TUNGGAL.** Baca UTUH. Isinya self-contained:
   - **§0** = peta sistem + akses (DB/VPS/S3) + **VISI/MISI** + **18 ATURAN KERJA** (wajib patuh).
   - **📸 Snapshot LIVE** = apa yang SUDAH jadi (jangan ulang).
   - **Kelompok A–E** = yang BELUM tuntas, format **Plan vs Realisasi** (TUJUAN·KONTEKS·BUKTI·PLAN·DONE-BILA·REALISASI). **Ini daftar kerjamu.**
3. **`progress_journal`** (memory, entri 2026-07-01 teratas) — kronologi + hasil audit menyeluruh.
> Dokumen lain (PROGRESS/REMEDIASI/CHANNEL_LOCK/QC/TREND/MULTI_FORMAT/DEPLOY_RUNBOOK/CUSTOM_NICHE/ONBOARDING_FUNNEL/DESAIN) = **SPEC/ARSIP** (rujuk untuk DETAIL arsitektur). **JANGAN pakai marker `[ ]`/⬜ mereka sbg daftar kerja** — hanya `SISA_KERJA_GO_LIVE.md` yang otoritatif.

## LANGKAH 2 — PAHAMI PETA KONDISI (verified 2026-07-01: DB+kode+FE+git+ssh VPS)
- **v2 LIVE di VPS**, v1 pensiun. `mv-web`+`mv-worker`+`mv-webhook`=active, situs 200. Branch `v2-backend`, migrasi ~0107.
- **SUDAH SELESAI & LIVE** (nol re-work): produksi+publish jalan · FE tenant+admin (Phase 9-10) · kredensial POOL + lock aktivasi · config+voice per-channel · Cacat-B durasi · niche/hashtag/custom-niche · OAuth platform Google · compliance/AI-slop defense · self-learning loop.
- **YANG BELUM (ringkas — detail di backlog):** **[A] gate eksternal owner** (Midtrans PRODUKSI = **pemblokir jualan utama** · Supabase SMTP+Google · rotasi secret · verifikasi Google) · **[B] dev pasca-launch** (system-secrets, cost-tracking, sapu hardcode, analytics-pivot, ai_video, go-live checklist) · **[C] data-gated** · **[D] keputusan owner** (growth funnel, multi-platform).
- **⭐ ARAH OWNER: SEGERA JUALAN.** "Selesai" = bisa dijual ke tenant baru, BUKAN sempurna untuk ryan (tenant test). Pertanyaan pemandu: *"apakah ini memblok tenant berbayar pertama?"* Tidak → defer.

## LANGKAH 3 — PATUHI ATURAN KERJA (18, di §0 backlog — INTI)
Paham-dulu-sebelum-kerja · **nol asumsi** (ground truth = KODE+DB LIVE, dok bisa drift) · **propose-dulu + tunggu approval** untuk perubahan · **bahasa sederhana** ke owner (non-teknis, jelaskan DAMPAK) · **JANGAN ubah UI tanpa izin** · no-hardcode (config-driven) · world-class (reuse UI bagus, nol duplikat) · desain multi-channel · aset di S3 · **validasi PENUH di LOKAL → deploy VPS 1× per-batch** · perintah VPS lama = detached+poll. **JANGAN:** sentuh v1 · drop `niche_pool`/`niche_mode` · ngoding di VPS · commit/deploy tanpa izin.

## LANGKAH 4 — MULAI (setelah paham)
1. **Konfirmasi ringkas ke owner** (bahasa sederhana): peta kondisi + 1 kalimat "sisa utama = gate Midtrans; fungsi inti sudah live" + tawarkan langkah berikut.
2. **Pilih item** dari `SISA_KERJA_GO_LIVE.md` (urutan rekomendasi ada di sana):
   - Owner urus **gate eksternal [A]** → Claude **siapkan materi & pandu** (mis. [A4] teks/demo verifikasi Google; pandu [A1] Midtrans, [A2] Supabase).
   - ATAU owner minta **dev [B]** → ambil item (mis. [B1] system-secrets), **propose plan dulu**, kerjakan, isi REALISASI.
3. Tiap item selesai + tervalidasi → **update kolom REALISASI di `SISA_KERJA_GO_LIVE.md`** (jaga tetap sumber kebenaran tunggal) + sinkronkan dokumen SPEC bila perlu.

---
**Akses:** DB v2 psycopg2 pooler (`postgres.atliatnjhysdibmfypul`, password di `SUPABASE-CONNECTION.md` — redact di chat) · `ssh vps` (repo `~/viral-machine-v2` worker, `~/mesinviral-web` FE) · S3 `mesinviral-assets`. Repo lokal `/home/rad/viral-machine` branch `v2-backend`.
**Workflow:** LOKAL → validasi 100% → commit (saat owner minta) → push → `git pull` VPS + rebuild + restart. Detail lengkap = `SISA_KERJA_GO_LIVE.md §0`.
