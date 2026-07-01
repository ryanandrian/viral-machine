# PROMPT SESI BARU — Lanjutkan menuju Go-Live (TANPA asumsi liar)

> 🎯🔒 **FOKUS KERJA SESI BARU = [`SISA_KERJA_GO_LIVE.md`](SISA_KERJA_GO_LIVE.md)** (backlog tunggal, verified 2026-07-01 DB/BE/FE/git/VPS). Baca gerbang-paham (§1) untuk konteks, tapi **daftar kerja aktif = file backlog itu** — bukan §2/§3 di bawah (banyak USANG: FASE 1 selesai, kredensial POOL selesai, Cacat-B selesai). Semua dokumen lain sudah di-CLOSE jadi spec/arsip + ber-banner ke file backlog.

> **🔄 KOREKSI AUDIT 2026-07-01 (terverifikasi DB/kode — §2 di bawah USANG di beberapa titik):**
> - **"FASE 1 config-fanout masih per-tenant" = USANG.** FASE 1 SUDAH SELESAI: `channels` punya semua kolom per-channel (`voice_key`/`caption_style`/`niche_hashtags`/`visual_mode`/`image_quality`/`music_*`/quality + `*_account_id`), `pipeline.py:65` muat config **per-channel**. → JANGAN kerjakan F1-01 sebagai "berikutnya".
> - **"belum ada kode PRODUKSI disentuh" = SALAH BESAR.** v2 LIVE di VPS (`mesinviral.com`, mv-web/mv-worker/mv-webhook aktif); banyak fitur deployed.
> - **Sisa pekerjaan SEBENARNYA** = `PROGRESS.md` blok "AUDIT REKONSILIASI 2026-07-01" + tabel sisa (journal). Pakai ITU sebagai sumber prioritas, BUKAN §2 di bawah.
> Gerbang-paham & aturan kerja (§1) tetap berlaku; hanya status/prioritas (§2) yang basi.

> Tempel/baca ini di awal sesi baru. Kamu melanjutkan pekerjaan **MesinViral v2**. **JANGAN bertindak / menyentuh apa pun sebelum benar-benar MENGUASAI kondisi terkini.** Ikuti urutan di bawah PERSIS. Insiden berulang: bertindak sambil berasumsi karena belum paham → pelanggaran berat.

## 1. ⛔ GERBANG PAHAM (wajib tuntas SEBELUM kerja) — baca DETAIL, bukan skim
Baca berurutan, sampai paham 1000% (peta, DB, BE, FE, semua koneksi, progress, prioritas):
1. **`MEMORY.md`** (index, auto-load) — ikuti "URUTAN BACA KANONIK" di atasnya.
2. memory **`decisions_v1_v2_migration`** — framing v1/v2 (v2 LIVE di VPS; v1 pensiun).
3. memory **`decisions_niche_owns_content_config`** — NICHE=DNA · CHANNEL=brand-skin+knob operasional/biaya · TENANT=akun; niche dibuat hanya di admin/Business.
4. memory **`progress_journal`** (2 entri teratas) + **`PROGRESS.md`** (baca banner §RESUME POINT: pending TEKNIS sudah pindah ke remediasi; PROGRESS = arsip + gate ops/eksternal go-live).
5. **`/home/rad/viral-machine/REMEDIASI_NICHE_CHANNEL_VOICE_LLM.md` — BACA SELURUHNYA, DETAIL, TERMASUK §10 LAMPIRAN.** Ini **dokumen MASTER menuju go-live**. Kunci: §0 (mulai dari sini) · §4 (peta config-fanout) · §5 (fakta terverifikasi + anchor file:baris) · §7 (FASE & item) · **§10 (desain solusi yang SUDAH DISEPAKATI — prompt persis, skema field, kontrak JSON, contoh — IKUTI VERBATIM, jangan rancang ulang).**

**Aturan keras (selalu):** `feedback_comprehend_before_work` · `feedback_no_hardcode` · `feedback_analysis_discipline` · `feedback_workflow` (propose dulu utk perubahan besar). **NOL asumsi liar** — tiap klaim dari fakta nyata (file:baris / query DB). **Hasil audit/agent = LEAD, WAJIB diverifikasi sendiri** sebelum dipakai.

## 2. 📌 KONDISI TERKINI (terkunci 2026-06-20 — jangan re-litigasi)
- **PONDASI:** 1 user = 1 tenant = **MULTI channel** (kuota `plan_limits`: starter 1 / pro 3 / business 10).
- **TEMUAN KUNCI (verified langsung, bukan agent):** pondasi multi-channel **BELUM tuntas** — config-fanout `voice/caption/hashtag/visual_mode/image_quality/music/quality` masih **per-tenant** (`pipeline.py:58-65` muat `load_tenant_config(tenant_id)`), padahal `niche/durasi/format/branding/privacy` sudah per-channel (`config.py:47-68`). → **FASE 1 = prioritas utama.**
- **Keputusan terkunci** (detail REMEDIASI §3 & §10): Cacat-B durasi = **LLM pilih words+speed** (durasi-via-speed, §10.A — bukan tuning prompt) · voice identitas = **niche.voice_key** dari `voice_catalog` single-source (§10.B) · niche=DNA/channel=skin+operasional · Business niche = **private eksklusif** · field voice = **baku TTS**.
- **Branded-content** sudah di-merge ke REMEDIASI §5.6/F2-04 (file lama `BRANDED_CONTENT_ARCHITECTURE.md` DIHAPUS).
- **Status:** belum ada kode PRODUKSI disentuh. Semua sejauh ini = penataan dokumen.

## 3. 🎯 TUGAS
Eksekusi **REMEDIASI FASE 1 → 5 BERURUT**, mulai item **F1-01** (perkaya `voice_catalog` jadi single-source — desain di §10.B). Untuk TIAP item:
1. **Cek-ulang BUKTI** (file:baris / DB) lebih dulu — jangan percaya catatan begitu saja.
2. Kerjakan sesuai **PLAN** (item LLM/voice: ikuti **§10** apa adanya).
3. Validasi sesuai **DONE-BILA** (uji nyata; ryan tak boleh putus: voice VR6, OAuth, produksi 60s).
4. Isi kolom **REALISASI** (status + commit) di dokumen.
5. **Validasi tiap FASE 100% sebelum lanjut.** Propose dulu bila perubahan besar/berisiko.
- Workflow: **lokal → validasi → commit → push → `git pull` di VPS + rebuild + restart.** JANGAN ngoding di VPS.
- Setelah FASE 1–5 tuntas → selaraskan `ONBOARDING_FUNNEL_PLAN.md` (go-market) lalu buat plan-vs-realisasinya (REMEDIASI §8).

## 4. 🔑 AKSES
`ssh vps` + DB v2 (pooler Supabase) + file connection (kredensial) = ADA (`project_access_capabilities`). Verifikasi via tindakan, jangan asumsi tak-bisa. **Password DB JANGAN dibagikan di chat** (selalu redact `sed -E 's/Rad@[0-9]*/***/g'`). `S3-CONNECTION.md`/`SUPABASE-CONNECTION.md` sensitif.

## 5. ▶️ MULAI
Setelah membaca semua di atas: **konfirmasikan dulu ke owner** pemahamanmu secara singkat (peta kondisi + temuan kunci + item berikutnya = F1-01) **SEBELUM** eksekusi. Lalu kerjakan F1-01 dengan validasi penuh.
