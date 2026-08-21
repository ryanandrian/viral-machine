# 🎯 SISA KERJA MENUJU GO-LIVE — Backlog Tunggal + Plan vs Realisasi

> ⛔⛔ **KOREKSI MENYELURUH 2026-07-31 — BACA SEBELUM APA PUN DI BERKAS INI.**
> Setiap klaim di berkas ini tentang **durasi video** yang menyebut *durasi-via-speed · atempo ·
> toleransi persen (±12%/±15%) · `_fit_duration` · `TTS_ATEMPO_*` · "speed menyerap variansi"*
> **SUDAH TIDAK BERLAKU.** Mekanismenya DICABUT dari kode: tuas kecepatan suara dilarang owner
> (29-Jul) dan terbukti tidak menghasilkan durasi — terukur dari 294 produksi nyata: 41% render
> mentok di batas paling lambat, NOL render normal, dan hanya **22% dari 243 video mendarat**.
> Penggantinya: alat ukur durasi terkalibrasi + kendali **jumlah kata & jumlah kalimat**.
> **SATU-SATUNYA ACUAN: `QC_CONTENT_ARCHITECTURE.md §2c`.** Titik-titik yang terdampak di berkas ini
> ditandai `⛔[dicabut 31-Jul → §2c]`. Jangan membangun atau memasang ulang apa pun dari klaim itu.


> **File ini = SATU-SATUNYA daftar kerja belum-tuntas + progress-nya.** Dibuat 2026-07-01 dari audit menyeluruh (**verified: DB LIVE + kode BE `file:baris` + FE tenant/admin + `git log` + `ssh vps`**). Sesi baru **fokus & eksekusi dari sini** — tanpa audit ulang, tanpa asumsi.
>
> **CARA PAKAI (WAJIB):**
> 1. Ambil item ⬜/🟡 pada kelompok prioritas terendah nomornya (A dulu). Baca **TUJUAN · KONTEKS · BUKTI · PLAN · DONE-BILA**.
> 2. **CEK-ULANG BUKTI dulu** (`file:baris`/query DB) sebelum ubah kode — anchor di sini dari audit 2026-07-01; tetap verifikasi karena kode bisa bergerak. Anchor bertanda **[cek-baris]** = nomor baris dari dokumen sumber, belum di-grep-ulang sesi ini → grep dulu.
> 3. Kerja: **LOKAL → validasi 100% → commit → push → `git pull` VPS + rebuild + restart.** JANGAN ngoding di VPS. JANGAN sentuh v1 (sudah pensiun). JANGAN drop `channels.niche_pool`/`niche_mode` (AKTIF).
> 4. Selesai + tervalidasi → **isi kolom REALISASI** (status + commit + bukti) di item ini. Update juga dokumen SPEC terkait bila perlu.
> 5. Legend status: **⬜ belum · 🟡 sebagian · ✅ selesai+validasi · ⏳ data-gated · 🔒 nunggu keputusan/aksi owner.**
>
> **Sumber kebenaran status = FILE INI.** Dokumen lain (REMEDIASI/CHANNEL_LOCK/QC/TREND/MULTI_FORMAT/DEPLOY_RUNBOOK/CUSTOM_NICHE/ONBOARDING_FUNNEL/**PAYMENT_AND_TENANT_GATE_ARCHITECTURE**/**LIFECYCLE_NURTURE_ARCHITECTURE**) = **SPEC/ARSIP** (rujuk untuk detail arsitektur; jangan pakai marker `[ ]` mereka sbg daftar kerja).
>
> **🔗 RANTAI KANONIK BILLING & SIKLUS-HIDUP (jangan miss-link):** `SISA_KERJA` (backlog/status = **HUB**) → **`PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`** (arsitektur bayar Midtrans + gate `trial→active→grace→suspended`; **SELESAI + deployed `04cf0a2`**) → **`LIFECYCLE_NURTURE_ARCHITECTURE.md`** (LANJUTAN: nurture trial-lapse + dunning `suspended→blocked→deleted`+hapus-data; **rencana, belum build**). Pemetaan item: **[A1]/[E1]** (Midtrans) → PAYMENT · **[B8]** (/feedback) + **[B9]** (mesin siklus-hidup) → LIFECYCLE · **[D1]** (funnel) ⟷ LIFECYCLE.

---

## 🧭 §0. UNTUK SESI BARU — BACA INI DULU (peta sistem + akses; agar nol asumsi)

**Urutan paham (5 menit) sebelum eksekusi:**
1. **Framing v1/v2** → memory `decisions_v1_v2_migration`: v1 = mesin lama (PENSIUN). v2 = yang kita kerjakan, **LIVE di VPS** (`mesinviral.com`). DB v2 sendiri.
2. **Model produk** (JANGAN keliru): **1 user = 1 tenant = MULTI channel** (kuota `plan_limits`: starter 1/pro 3/business 10). **NICHE = DNA konten** (voice/visual/musik/narasi — dibuat admin atau Business niche-studio). **CHANNEL = brand-skin + operasional** (caption/hashtag/bahasa/logo + pilih AI-model+voice+akun). **TENANT = akun** (plan/billing/kredensial). Detail: memory `decisions_niche_owns_content_config` + `decisions_niche_model`.
3. **Cara mesin jalan** (BUKAN cron — 1 proses `scripts/worker_decoupled.py`, 7 thread): **PRODUCER** (loop, jaga stok buffer `content_inventory`, TAK publish) → **PIPELINE** (`orchestrator/pipeline.py`: script→hook→prompt-gambar→TTS→visual→render→QC) → **PUBLISHER** (loop, saat slot `channels.publish_slots` due → ambil `ready` tertua → upload YouTube → tulis `videos`+`production_runs`) → **self_learning** (analytics→`channel_insights`). Peta tabel/fosil TERVERIFIKASI = memory `reference_be_pipeline_tables_fossils`. Bisnis/pricing = `DESAIN_PRODUK_SAAS.md`.
4. **Kredensial (model POOL, FINAL)**: kunci AI di `tenant_ai_accounts` (per-vendor `key_group`), koneksi YouTube di `tenant_youtube_accounts`, channel tunjuk via `channels.{llm,tts,visual,youtube}_account_id`. `.env` = HANYA platform. Detail = `CHANNEL_LOCK_ACTIVATION_PLAN.md`.

**Akses (verified — pakai via tindakan, jangan asumsi tak-bisa):**
- **DB v2**: psycopg2 pooler `aws-1-ap-southeast-1.pooler.supabase.com:5432`, db `postgres`, user `postgres.atliatnjhysdibmfypul`. **Password** = di `SUPABASE-CONNECTION.md` (gitignored) atau skrip `scratchpad/apply_*.py` lama. **JANGAN print password di chat** (redact `sed -E 's/Rad@[0-9]*/***/g'`).
- **VPS**: `ssh vps` (alias; `rad4vm@103.103.22.227`, key `~/.ssh/vps_key`). Repo worker `~/viral-machine-v2`, FE `~/mesinviral-web`. Service `mv-worker`/`mv-web`/`mv-webhook`. Log worker = `~/viral-machine-v2/worker.log` (bukan journald) — memory `reference_vps_logs`.
- **S3** (aset/video/logo) = Biznet bucket `mesinviral-assets`, kredensial `S3-CONNECTION.md`. Supabase = DB saja.
- **Repo lokal** = `/home/rad/viral-machine`, branch `v2-backend`. FE = `apps/web` (Next.js 16; `npm --prefix apps/web run build`). `.md` di-exclude dari VPS (sparse-checkout).

### 🎯 VISI / MISI (WAJIB paham — arah tiap keputusan) — sumber: `DESAIN_PRODUK_SAAS.md §1/§8/§9` + memory `project_vision`
- **Tagline/misi:** *"Mesin produksi konten YouTube Shorts otomatis yang **belajar dari channelmu sendiri**."* Untuk **faceless creator (Indonesia-first)** yang mau scale ke 5+ video/hari — video viral-grade harian + adaptasi real-time dari analytics channel mereka.
- **3 pembeda / MOAT:** (1) **BYOK transparan** (tenant bawa kunci AI sendiri, tanpa vendor lock-in, jauh lebih murah/video) · (2) **Self-learning loop** dari YouTube Analytics post-publish (tak ada kompetitor lakukan — moat 12-18 bln) · (3) **Indonesia-first** (UI ID, Midtrans, niche kurasi, concierge).
- **Prinsip NON-NEGOTIABLE:** kualitas>kuantitas (lebih baik tak produksi daripada jelek) · **no silent degradation** (gagal→tenant tahu via Telegram+dashboard) · **diversity/compliance-first** (bertahan dari YouTube AI-slop crackdown Jan 2026 = **PILAR SURVIVAL**, bukan opsional) · self-learning · **almost fully config-driven (no-hardcode)** · transparansi (BYOK + biaya AI terlihat + log auditable).
- **⭐ TUJUAN OWNER = SEGERA JUALAN (go-to-market).** Ukuran "SELESAI" yang BENAR = **produk bisa DIJUAL ke tenant baru**, BUKAN menyempurnakan internal/ryan. Pertanyaan pemandu tiap saat: *"apakah ini memblok tenant berbayar pertama?"* Tidak → DEFER (pasca-launch). STOP rabbit-hole perfeksionisme. (memory `project_audit_setup_gaps_2026_06_23`)

### 📏 ATURAN KERJA LENGKAP → **`/home/rad/viral-machine/CLAUDE.md`** (satu-satunya sumber, auto-dimuat tiap sesi)

> 🔴 **RANJAU DICABUT 2026-08-05 — daftar di bawah ini menunjuk 18 berkas yang SUDAH TIDAK ADA.**
> Diperiksa satu per satu: **18 dari 18 HILANG.** Ke-24 berkas `feedback_*` dipusatkan ke `CLAUDE.md`
> lalu **dibuang 2026-07-15** atas perintah owner (*"pusatkan 1 lokasi, buang fosil"*) — tapi baris-baris
> di bawah **tak pernah ikut diperbarui**. Akibatnya berkas yang setiap sesi baca PERTAMA memerintahkan
> mematuhi aturan yang tak bisa dibuka: sesi baru mencari, tak menemukan, lalu **menebak**.
> Inilah bentuk "basi tapi terkesan hidup" yang paling merusak — dan ia bertahan **3 minggu**.
>
> **YANG BERLAKU: `CLAUDE.md`** — seluruh 18 aturan itu sudah ada di sana, lengkap beserta konteks
> insidennya. Daftar di bawah **DISIMPAN sebagai peta-silang saja** (mana aturan lama jatuh ke pasal mana),
> **BUKAN sebagai perintah membaca berkas memory.**
> Peta silang: A.1-5 → `CLAUDE.md` §0 & §2 · B.6-10 → §0.1, §2.3, §4 · C.11-14 → §3.2, §3.3, §6.7, §7.2 ·
> D.15-18 → §3.4, §5, §7.3.

**A. Sebelum bertindak — paham & disiplin** *(peta-silang ke `CLAUDE.md`; berkas memory-nya SUDAH TIADA)*
1. **`feedback_comprehend_before_work` *(berkas TIADA)*** ⛔ — paham **1000%** peta (DB/BE/FE/koneksi/progress/prioritas) SEBELUM menyentuh apa pun. Darurat = containment dulu, baru diagnosa (jangan menebak komponen).
2. **`feedback_post_compaction` *(berkas TIADA)*** — pasca-compaction JANGAN "bayi baru lahir": percayai summary+memory, baca URUTAN KANONIK berurut, tulis peta-state, lanjut thread aktif — jangan re-investigasi yang sudah jelas.
3. **`feedback_analysis_discipline` *(berkas TIADA)*** — **NOL asumsi.** Trace end-to-end dgn angka nyata; baca kode sebelum klaim; **build PASS ≠ running well** (validasi RUNTIME sebelum klaim selesai).
4. **`feedback_master_docs_first` *(berkas TIADA)*** — kuasai dokumen dulu; **GROUND TRUTH = KODE + DB LIVE** (dok bisa drift/aspiratif — jangan kutip dok sbg bukti perilaku); kontradiksi→terbaru+konfirmasi; hormati banner "JANGAN ANALISA ULANG"; FE = referensi backend.
5. **`feedback_review_whole_remediation_before_item` *(berkas TIADA)*** 🔗 — sebelum kerjakan 1 item: review SELURUH dokumen terkait + cek DEPENDS + item yang menumpang seam (hindari rework).

**B. Cara memutuskan & komunikasi**
6. **`feedback_workflow` *(berkas TIADA)*** — **propose dulu + tunggu approval** untuk perubahan; saat ditanya: jawab+opsi+rekomendasi+tunggu konfirmasi (jangan langsung bongkar kode).
7. **`feedback_owner_delegates_expert_decisions` *(berkas TIADA)*** — owner delegasi teknis: putuskan yang reversible/jelas; **propose untuk yang berisiko/fork bisnis**. North-star = produk **LAKU + skala ribuan tenant + viral NYATA**.
8. **`feedback_plain_language` *(berkas TIADA)*** 🗣️ — owner **non-teknis**: bahasa dampak bukan mekanisme; nol jargon; status = checklist sederhana.
9. **`feedback_no_silent_ui_changes` *(berkas TIADA)*** 🚫🎨 — JANGAN tambah/ubah/hapus elemen UI tanpa izin owner. Tugas BE/logika = ubah itu SAJA; usul dulu bila perlu UI.
10. **`feedback_define_done_no_scope_creep` *(berkas TIADA)*** — tarik garis tegas **SELESAI / poles-opsional / wajib-jualan**; defer opsional; menjelaskan ≠ tugas baru; jangan bingkai follow-up sbg "cacat".

**C. Standar kualitas & teknis**
11. **`feedback_world_class_quality` *(berkas TIADA)*** 🏆 — DB/BE/FE semua TERBAIK; reuse/relokasi UI bagus yang ada (jangan bikin lebih jelek); nol-duplikat; "selesai" = kualitas + lama-dibereskan + tervalidasi.
12. **`feedback_no_hardcode` *(berkas TIADA)*** — AI/pricing/business = config-driven (`pricing_config`/`app_config`/DB); no silent fallback (gagal→stop+notify); nol literal nominal/model di kode.
13. **`feedback_design_for_multichannel_scale` *(berkas TIADA)*** — asumsi default **tenant MULTI-channel**; atribusi data **per-entitas** (per-video/run), bukan "channel tenant"; ryan (1 channel) = test, bukan patokan.
14. **`feedback_all_assets_on_s3` *(berkas TIADA)*** 🗄️ — semua aset/media di **S3** (`mesinviral-assets`); Supabase = DB saja. **JANGAN keputusan biaya/infra tanpa izin owner.**

**D. Validasi & deploy**
15. **`feedback_local_test_batch_deploy` *(berkas TIADA)*** ⚡ — validasi PENUH di LOKAL (dev box mampu render-test/build/DDL); deploy VPS **1× di akhir task** (rebuild FE VPS lambat), jangan per-langkah.
16. **`feedback_vps_clean` *(berkas TIADA)*** — VPS = runtime bersih (`.md` di-exclude sparse-checkout); alur lokal→commit→push→`git pull` VPS+restart.
17. **`feedback_vps_ssh_long_commands` *(berkas TIADA)*** — perintah VPS lama/menunggu = **detached + poll** (SSH nganggur diputus→error 255); jangan foreground.
18. **`feedback_f4_locked_gate` *(berkas TIADA)*** — *(GERBANG SUDAH TERBUKA — F4 durasi SELESAI `8670fc3`)*; prinsip tetap: durasi = hulu, hilir rusak bila hulu meleset.

**⛔ PANTANGAN keras:** JANGAN sentuh v1 (pensiun; arsip+DB disimpan) · JANGAN drop `channels.niche_pool`/`niche_mode` (AKTIF) · JANGAN ngoding di VPS.

---

## 📚 §0b. DAFTAR STATUS SELURUH DOKUMEN — SATU-SATUNYA acuan "mana yang valid" (2026-08-05)

> **Lahir dari teguran owner 5-Agu:** *"Anda tidak pernah tahu dokumen mana yang sudah dikerjakan dan valid,
> mana yang belum, mana yang dibatalkan."* **Benar** — daftar ini tak pernah ada, dan itu akar seluruh
> kekacauan: setiap sesi baru (termasuk Claude) MENEBAK dokumen mana yang boleh dipercaya.
> **Aturan pakai:** dokumen di luar kelompok 1 **TIDAK BOLEH** dijadikan acuan implementasi tanpa
> diverifikasi ulang ke KODE + DB LIVE (CLAUDE.md §1.2).

**KELOMPOK 0 — PETA UNTUK OWNER (1).** `PETA_MESINVIRAL.md` — satu halaman, bahasa owner, dibaca
3 menit: apa yang mesin kerjakan · apa yang terbukti jalan (berangka) · apa yang rusak · apa yang
dijanjikan tapi belum dibangun · apa yang haram tanpa ketokan owner · cara owner memeriksa hasil
kerja tanpa perlu memercayai laporan. **Lahir dari teguran owner 19-Agu:** *"tidak ada satupun
pegangan arsitektur."* **WAJIB diperbarui setiap kali daftar rusak/belum-dibangun berubah** — peta
basi = owner kehilangan pegangan lagi.

**KELOMPOK 1 — SSOT HIDUP, DIJAGA MESIN (10).** Boleh dipercaya: bila isinya melenceng dari kode, uji
MERAH. Tiap satunya sudah dibuktikan merah dengan sengaja membusukkan dokumennya.
`CLAUDE.md` · `SISA_KERJA_GO_LIVE.md` · `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` ·
`PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` · `LIFECYCLE_NURTURE_ARCHITECTURE.md` ·
`AGENT_AND_AFILIATION_ARCITECTURE.md` · `PROGRAM_BUKTI_KECERDASAN.md` · `DESAIN_PRODUK_SAAS.md` ·
`QC_CONTENT_ARCHITECTURE.md` · `CONTENT_CATEGORY_ARCHITECTURE.md`

**KELOMPOK 2 — BERSPANDUK (23).** Dokumennya SENDIRI memperingatkan (CLOSED/ARSIP/USANG/SELESAI/
"bukan daftar kerja"). Aman dibaca sebagai sejarah; **jangan** jadi acuan implementasi.

**KELOMPOK 3 — ALAT KERJA, bukan arsitektur (5).** `CLAUDE_DESIGN_BRIEF.md` + `ADDENDUM v2/v3/v4`
(kepalanya sendiri berbunyi *"copy-paste ke Claude Design"*) · `PANDUAN_CLAUDE_CODE.md` (panduan memakai
CLI, lintas-proyek). **⚠️ `CLAUDE_DESIGN_BRIEF` memuat spesifikasi layar untuk Webhook · Priority Queue ·
API access — TIGA fitur yang TIDAK ADA di aplikasi (lihat [D8])**; jangan dijadikan dasar membangun.

**KELOMPOK 4 — CATATAN BERTANGGAL (2).** `RISET_NICHE_TRENDING_2026-07-05.md` ·
`AUDIT_ATRIBUSI_NICHE_2026-07-15.md`. Bahan riset/rekaman audit — bukan keadaan sistem.

**KELOMPOK 5 — MENUNJUK SUMBER LAIN (5).** `PHASE4_DESIGN.md` · `PHASE5_DESIGN.md` · `PHASE6_DESIGN.md` ·
`PHASE9_FRONTEND_WIRING.md` · `PHASE10_ADMIN_WIRING.md` — dokumen fase pembangunan; kepalanya menunjuk
*"Status LIVE = `PROGRESS.md`"*. **Baca sumber yang ditunjuknya, bukan isinya.**
*(Nama ditulis PENUH satu per satu — bukan disingkat "PHASE4/5/6" — supaya penjaga uji bisa membacanya;
bentuk singkat itu membuat 4 dokumen tak terhitung berstatus, tertangkap uji 05-Agu.)*

**KELOMPOK 6 — PERLU DIBERESKAN: ✅ NOL (dituntaskan 2026-08-05).**
`SOFTCODE_AI_CONFIG - BELUM DI EKSEKUSI.md` — namanya menjanjikan "belum dieksekusi", padahal tujuannya
**SUDAH TERCAPAI**. Diverifikasi, bukan diklaim: nol nama model AI terpatri di `src/` (disapu gpt-4o ·
claude-3 · gemini-2 · llama-3 · flux · dall-e) · **48 `ai_models`** + **9 `ai_providers`** di DB · **12
titik** kode membaca katalog itu · adapter LLM = registry per-PROTOKOL (vendor baru = +1 baris DB, nol
koding) · nol nominal rupiah terpatri · 117 kenop ber-label. Spanduk bukti dipasang di kepala berkas;
nama berkas TIDAK diubah agar tautan lama tak putus.
*(Klaim awal §0b bahwa "indeks memory menyatakannya SUPERSEDED" juga SALAH — yang superseded adalah
`plan_s93` & `PIPELINE_LOG_SEPARATION`. Itu kekeliruan klasifikasi KETUJUH; tertangkap sebelum bertindak.)*

**KELOMPOK 7 — BERKAS RAHASIA, SENGAJA DI LUAR GIT (2).** `S3-CONNECTION.md` · `SUPABASE-CONNECTION.md`.
Keduanya tercantum EKSPLISIT di `.gitignore` di bawah komentar **"# secrets (JANGAN commit)"** (baris 22 &
25) ⇒ tak-terlacak-git adalah **desain yang benar**, bukan kelalaian. **JANGAN commit, JANGAN tampilkan
isinya di chat** (§6.3). Catatan: `SUPABASE-CONNECTION.md` berjudul *"DATABAE VER-1"* = kredensial DB **v1
yang sudah PENSIUN** — menghapusnya = keputusan owner (bisa jadi masih dibutuhkan untuk akses arsip).

> 🔴 **KOREKSI 2026-08-05 atas daftar ini sendiri.** Versi pertama §0b menaruh kedua berkas rahasia itu di
> KELOMPOK 6 ("perlu dibereskan") karena "tak pernah di-commit". **SALAH** — `.gitignore` memang
> memerintahkannya. Itu **kekeliruan klasifikasi keenam** dalam satu sesi (sebelumnya: "14 ranjau dokumen"
> yang ternyata 3 · alat "artefak masih ada" salah 5 dari 5 · penjaga migrasi beralarm palsu belasan kolom).
> **Pelajaran yang harus dibaca sesi berikutnya:** klasifikasi apa pun di daftar ini yang TIDAK berlabel
> "dijaga uji" adalah **dugaan yang harus diverifikasi ke bukti** (kode · DB · `.gitignore` · isi berkas) —
> bukan vonis. Verifikasi kelompok 2–7 belum selesai, dan itu dinyatakan terbuka, bukan disembunyikan.

**⚠️ BATAS KEJUJURAN DAFTAR INI (jangan dibaca lebih kuat dari isinya):** pengelompokan 2–6 dibuat dari
**membaca kepala** tiap dokumen + memeriksa penunjuk & penjaga — **BUKAN** membaca seluruh isinya.
`CLAUDE_DESIGN_BRIEF` membuktikan risikonya: kepalanya tampak tak berbahaya, isinya (2.003 baris) memuat
fitur yang tak ada. **Jadi: kelompok 1 = terbukti; kelompok 2–6 = belum diverifikasi isi, bukan "aman".**
Upaya memverifikasi isi secara otomatis (skor "artefak masih ada") **GAGAL TOTAL — salah 5 dari 5** dan
dibuang; satu-satunya cara yang terbukti = membaca + membandingkan klaim yang tumpang tindih.

**PRESEDEN RESOLUSI TUMPANG TINDIH (contoh cara memutuskan, 5-Agu):** 7 dokumen menyebut batas video/hari
dengan angka berbeda. Vonis diambil dari DB live (`plan_limits` = 1/1/3/5): VALID = `CONTENT_CATEGORY`,
`finalisasi_tier_plan`, `ONBOARDING_FUNNEL`, `PAYMENT_GATE`, halaman pemasaran ("50/hari" = 5×10 channel).
BASI = `CLAUDE_DESIGN_BRIEF`, `DESAIN_PRODUK_SAAS` (6 baris naratif), `RISET_NICHE_TRENDING` — ketiganya
kini bertanda. Dijaga `tests/test_kuota_tak_ditanam_di_dokumen.py`.

---

## 📸 SNAPSHOT KONDISI LIVE (verified 2026-07-01 — baseline; JANGAN kerjakan ulang)
- **v2 LIVE di VPS**, v1 PENSIUN. `mv-web`+`mv-worker`+`mv-webhook` = **active**. `mesinviral.com`=200, `/api/youtube/oauth/callback`=302. Worker HEAD `8d44f01`, web HEAD `ee01575`, branch `v2-backend`, migrasi terakhir ~0107.
- **Mesin produktif**: `videos`=273 (185 published), `production_runs`=130. 2 channel (ryan aktif, kumala belum lengkap).
- **DB v2** = `atliatnjhysdibmfypul` (pooler `aws-1-ap-southeast-1.pooler.supabase.com:5432`, user `postgres.atliatnjhysdibmfypul`). Migrasi via psycopg2 pooler.
- **SUDAH SELESAI & LIVE (terbukti — nol re-work):** wiring FE Phase 9-10 (tenant+admin) · kredensial **model POOL** (`tenant_ai_accounts` key_group + `tenant_youtube_accounts`; channel `*_account_id`; fosil `tenant_credentials`/`channel_credentials`/`channels.*_key_enc`/`token_path` DI-DROP migr 0090/0095) · **lock aktivasi** (trigger `channels_activation_gate` BEFORE INSERT/UPDATE, fungsi `channel_missing`) · config per-channel + voice per-channel (migr 0082/0083) · **Cacat-B durasi-via-speed** (F4, `8670fc3`, migr 0078/0079) · image-gen per-preset 2-tahap + VISUAL DNA (`e964a9e`) · trend cache (0048)+source_weights (0049)+YouTube velocity · self-learning loop (`viral_score_weights` hidup, `21f41fe`) · niche/hashtag remediasi (BATCH 1-5) · **alur custom-niche A-Z** (`e263e1a`, concierge/manual) · niche origin (studio/request/admin) · OAuth PLATFORM Google (`GOOGLE_CLIENT_ID/SECRET` .env; ryan verified) · compliance/AI-slop defense (DiversityEngine + ComplianceScorer + ai_disclosure) · onboarding credential-first (setup 2-langkah) · bersih FE (notif/config/danger dihapus, Pustaka Niche). ⛔[dicabut 31-Jul → §2c]
- **Peran:** owner = konsep/bisnis + gate eksternal; Claude = detail teknis. Ryan = tenant test (grandfathered). **Acceptance sebenarnya = tenant BARU dari nol.**

---

# 🔑 KELOMPOK A — GATE EKSTERNAL / OWNER *(SATU-SATUNYA pemblokir MULAI JUALAN)*
> Hanya owner yang bisa eksekusi (butuh dashboard/akun/browser); Claude siapkan materi + pandu. Spec: `PROGRESS.md §GATE CUTOVER` + `DEPLOY_RUNBOOK.md` + `GOOGLE_OAUTH_PLATFORM_MIGRATION.md`.

### [A1] Midtrans PRODUKSI — ✅ SELESAI TOTAL (2026-07-04) — pembayaran nyata pertama SUKSES, JUALAN TERBUKA
- **TUJUAN:** tenant bisa BAYAR sewa (subscription) + add-on custom-niche → uang masuk.
- **KONTEKS:** BE pembayaran (Snap redirect) SUDAH jadi & lulus e2e sandbox — `src/billing/midtrans.py` (`snap_create_transaction` env-driven sandbox/prod · `verify_signature` SHA512 · `handle_notification`→aktivasi), tabel `payments` (migr 0022), webhook route di `mv-webhook`. **Arsitektur lengkap = `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md`.** ⚠️ **Switch sandbox↔production = ubah `MIDTRANS_ENV` di `.env` + restart** (§3.2 doc; BUKAN tombol admin — tombol itu = [B1], belum ada). **✅ Verified 2026-07-02: kunci PRODUKSI Server+Client SUDAH ADA di `.env` VPS (format `Mid-server-`/`Mid-client-` valid) + merchant dibagi dgn aiwa yang SUDAH LIVE produksi → merchant approved.** Jadi [A1] ≈ **flip `MIDTRANS_ENV=production` + restart + 1 transaksi konfirmasi** — bukan "cari kunci". Pemblokir tersisa = KEPUTUSAN owner KAPAN go-live (idealnya bareng [A2]✓ + [A4] verifikasi Google + [A5] smoke-test).
- **BUKTI kondisi sekarang (verified DB 2026-07-01):** `payments`=**0 baris**; `.env` `MIDTRANS_ENV`=sandbox. → produksi belum pernah jalan. **Verified 2026-07-02 (VPS `.env`):** `MIDTRANS_PRODUCTION_SERVER_KEY`+`_CLIENT_KEY` **ADA & format valid** → kunci produksi SIAP; tinggal flip+restart+konfirmasi.
- **PLAN (aksi owner + Claude bantu):**
  - Owner: dapatkan **Server key + Client key PRODUKSI** Midtrans; isi ke `.env` VPS + `MIDTRANS_ENV=production`; daftar **Notification URL** (payment/recurring/pay-account) + Finish/Error URL → `https://mesinviral.com/api/webhooks/midtrans`.
  - Claude: verifikasi route webhook `mv-webhook` menerima notifikasi prod; restart `mv-webhook`+`mv-worker` (baca env baru).
- **DONE-BILA:** 1 transaksi nyata (sandbox→prod) → webhook masuk → `payments` terisi + `tenant_configs.subscription_status`→active. FE Billing tombol Snap enabled (kini disabled+note gate).
- **DEPENDS:** — (BE siap). **Nyambung:** [E1] add-on custom-niche.
- **REALISASI:** 🟡 **2026-07-04: `MIDTRANS_ENV=production` DI-FLIP Claude** (instruksi owner) + `mv-webhook`/`mv-worker` restart + **kunci produksi TERVERIFIKASI diterima API Midtrans produksi** (auth-check: 404 "Transaction doesn't exist" ter-autentikasi, bukan 401) + tombol bayar Billing FE sudah hidup (catatan "disabled gate" lama = basi). **✅ TUTUP 2026-07-04 sore: pembayaran NYATA pertama SUKSES A-Z** — owner bayar Rp 149.000 via **GoPay** (order `MV-starter-eb5e3f0d1eda-1783160261`): webhook settlement masuk dari IP Midtrans `149.129.192.10` 17:42 WIB (`activated=True`, log mv-webhook) → `payments` settlement/gopay → effi `trial→active` plan starter, period_end 2026-08-03 → kuitansi email "Payment received" terkirim. **BONUS terbukti di kondisi nyata:** anti dobel-bayar bekerja 2× (2 order lama auto-cancel saat re-checkout) + email payment-link terkirim tiap order. Temuan proses: GoPay merchant = mode deeplink saja (muncul HANYA di HP; desktop butuh aktivasi GoPay-QRIS terpisah — opsional owner) + bug menu mobile hilang di HP DIPERBAIKI (drawer ☰, commit `227f2f8`). ~~Minor: `payments.transaction_id`/`paid_at`~~ **✅ DITUNTASKAN 2026-07-04 (owner: "jangan biarkan bug")** — ralat: kolomnya memang BELUM ADA (bukan "tak diisi") → migr **0123** tambah kolom + backfill dari `raw_notification` (settlement effi terisi: txn `c2343706...`, paid 17:42:32 WIB) + `_apply_settlement` kini mengisinya. **Sekalian keputusan owner A+C:** katalog niche publik utk SEMUA tier berbayar + config-driven `plan_limits.full_niche_catalog` (migr **0124**; RPC `set_channel_niche` + 3 halaman FE + `limits.py` diseragamkan — hardcode tier dibuang). **⛔ JANGAN sentuh Notification URL dashboard Midtrans (milik aiwa!)** — arsitektur kita menitipkan notifikasi PER-TRANSAKSI via `X-Override-Notification` (midtrans.py:140) + order prefix `MV-` (koreksi 2026-07-04: instruksi dashboard sebelumnya salah — diluruskan owner).

### [A2] Supabase Auth — SMTP + Google provider — ✅ *(validated 2026-07-01)*
- **TUJUAN:** email auth (verify/reset) ber-brand + terkirim andal; "Daftar dengan Google" jalan untuk tenant publik.
- **KONTEKS:** kode auth (signup/verify/reset/OAuth callback) SUDAH jalan (Phase 9.1, runtime-validated). Kurang = konfig dashboard Supabase.
- **BUKTI:** reset email dulu kena rate-limit default Supabase (bukan bug kode); Google provider status di dashboard = belum aktif. SMTP tersedia (`mail.lumite.biz.id:465`, di `S3-CONNECTION.md`).
- **PLAN (aksi owner):** Supabase Dashboard `atliatnjhysdibmfypul` → Authentication → (1) **custom SMTP** `mail.lumite.biz.id` (host/port/user/pass/from) · (2) **Google provider** = Client ID/Secret app lumite (`153190496639-i41l1fp3...`).
- **DONE-BILA:** signup email verify terkirim ber-brand; "Daftar dengan Google" e2e sukses (redirect `mesinviral.com`, bukan localhost — bug ini sudah fix `a18d451`).
- **REALISASI:** ✅ **SELESAI + VALIDATED 2026-07-01** (owner setting di dashboard Supabase; Claude validasi otomatis dari server, bukan tebakan). (1) **Custom SMTP lumite** dibuktikan END-TO-END: trigger `POST /auth/v1/recover` (200) → email masuk inbox `mesinviral@lumite.biz.id` (dibaca via IMAP) dgn **From: `Mesin Viral <mesinviral@lumite.biz.id>`** (bukan `noreply@…supabase.io`) → SMTP lumite aktif & dipakai Supabase. (2) **Google provider** valid: `GET /auth/v1/authorize?provider=google` → 302 ke `accounts.google.com` dgn `client_id=153190496639-i41l1f…` (app lumite) + `redirect_uri=…supabase.co/auth/v1/callback` benar + scope `email profile` → provider aktif & terwire benar. Yang TAK-testable headless = klik-pilih-akun interaktif utk PUBLIK (butuh browser + app di Production) → menyusul saat **[A4] publish**; selama Testing hanya test-user (normal). Catatan minor (poles opsional, non-blocker): template email auth Supabase masih bhs Inggris ("Reset your password"). **Investigasi link-reset 2026-07-01 (owner lapor "link tak benar"):** alur RESET dari SITUS (PKCE) TERBUKTI benar — verify → `…/auth/callback?code=…&next=%2Fauth%3Fview%3Dreset` → callback `exchangeCodeForSession` (route.ts:33-36) → form set-password (same-device OK). Gejala owner = klik EMAIL TES raw-API (tanpa PKCE → jatuh ke beranda/fragment `#access_token` yg tak terbaca server), BUKAN alur situs. ⚠️ **KELEMAHAN NYATA (hardening, non-blocker):** PKCE reset gagal **LINTAS-ALAT** (minta di laptop, buka email di HP → tak ada code_verifier → "link tidak valid"). ✅ **DIBERESKAN 2026-07-01 (commit `db3d859`, deployed + LIVE-validated) — world-class in-code:** reset email kini **DIKIRIM SENDIRI oleh mv-web** (bukan Supabase): route `/api/auth/forgot-password` → `admin.generate_link` (service_role) → link **`token_hash`** → `/auth/callback` `verifyOtp` → **JALAN DI SEMUA ALAT** (tak butuh browser asal; PKCE dibuang utk reset). Template email **ID/EN ber-brand di kode** (`apps/web/src/lib/email/templates.ts`) + pengirim SMTP (`smtp.ts`, nodemailer, config env, anti-enumeration). **Template Supabase reset TAK dipakai lagi.** Validasi LIVE (nol asumsi): POST→email brand `mesinviral@lumite.biz.id`→link `mesinviral.com/auth/callback`→callback 307 `/auth?view=reset` (nol error). **Konfirmasi SIGNUP:** template ID/EN SUDAH dibuat (siap), tapi **wiring MENYUSUL** — signup masih `supabase.auth.signUp` (template Supabase); wiring butuh cek dulu setelan Supabase "Confirm email" (nol asumsi) → item berikutnya.

### [A3] Rotasi semua secret dev — 🔒⬜
- **TUJUAN:** secret yang dipakai saat dev tidak bocor ke produksi publik.
- **PLAN:** rotate: DB password (`Rad@...` → baru; update `.env` + semua skrip), `SUPABASE` service_role + anon, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET` (worker==mv-web WAJIB sama), `SMTP_*`, `MIDTRANS_*`, ElevenLabs key ryan. Update `.env` VPS + `.env.local` mv-web + restart.
- **DONE-BILA:** semua service tetap jalan dgn secret baru; secret lama invalid.
- **DEPENDS:** paling akhir sebelum publik (agar tak rotate 2×). Terkait [B1] (system-secrets bisa jadi tempat kelola).
- **REALISASI:** ⬜

### [A4] Verifikasi Google app + kumala reconnect — ✅ **APPROVED GOOGLE 2026-07-15 21:16 WIB** (email resmi Third Party Data Safety Team; dicatat 2026-07-16)
- **🏁 HASIL:** OAuth App Verification **DISETUJUI** utk project 153190496639 (`mesin-viral`) — scope `youtube.readonly` + `youtube.upload`. ±10 hari dari submit (2026-07-05), lulus di percobaan ke-2 (video ulang consent-utuh §8b-REV = kuncinya). **Dampak: layar "unverified" HILANG · cap 100 test-user DICABUT · refresh-token PERMANEN → gerbang eksternal go-live terakhir TERBUKA (Midtrans produksi ✅ sejak 2026-07-04) = TINGGAL JUALAN.**
- **⚠️ Aturan pasca-lulus (dari email Google, PERMANEN):** (1) scope baru / ubah consent screen = WAJIB verifikasi ulang → JANGAN utak-atik console tanpa kebutuhan nyata (§6.5 tetap berlaku); (2) jaga akun Project Owner/Editor aktif; (3) verifikasi tak diwariskan. *(Catatan: `yt-analytics.readonly` tak disebut di email approval — analytics fetch BERJALAN NORMAL; bila kelak dibatasi Google, tangani saat itu dgn bukti, jangan pre-emptive utak-atik console.)*
- **⬜ Verifikasi mata-kepala (owner, 5 mnt):** alur "Hubungkan dengan Google" akun uji → consent bersih tanpa warning → catat di sini.
- *(Riwayat di bawah = arsip perjalanan review.)*
- ~~**TUJUAN:**~~ pelanggan asing lihat brand MesinViral (bukan warning "unverified"); refresh-token permanen (bukan kedaluwarsa 7 hari mode Testing). ✅ TERCAPAI.
- **KONTEKS:** materi SIAP di `GOOGLE_OAUTH_PLATFORM_MIGRATION.md` — justifikasi scope (§8a, 3 scope: youtube.upload/readonly/yt-analytics.readonly), shot-list demo video (§8b), `/privacy`+`/terms` sudah LIVE & patuh. Scope SENSITIVE (bukan Restricted → tanpa CASA berbayar).
- **PLAN (aksi owner):** Google Auth Platform (akun `lumite.biz.id@gmail.com`, project `mesin-viral`) → Publish app (Testing→Production) → Verification Center → submit (justifikasi §8a + demo video §8b). Timeline ~10 hari. ~~+ kumala reconnect~~ → **kumala reconnect YouTube = ✅ SELESAI (owner konfirmasi 2026-07-01)**. Sisa A4 = HANYA Langkah 9 (publish + submit verifikasi).
- **DONE-BILA:** app verified (warning hilang, token permanen).
- **REALISASI:** 🟡 **SUBMITTED owner 2026-07-05** — seluruh prasyarat tuntas & terverifikasi: domain `mesinviral.com` verified Search Console (TXT, akun lumite) · Branding+privacy/terms live · 3 scope sensitive declared + justifikasi gabungan + Additional info · demo video Unlisted (`youtu.be/xeTCF73pWkg`, channel mesinviral milik lumite; adegan consent+upload+analytics+revoke nyata) · kuesioner (4×No + 2 acknowledge; TANPA CASA — bukan restricted scope). **Konfirmasi Google:** kontak pertama T&S 3-5 hari, total review **s/d 4-6 MINGGU** (lebih lama dari estimasi 10 hari di doc lama); consent screen lama tetap berlaku selama review. ⚠️ JANGAN ubah publish status/user type/scope di console selama review (peringatan resmi Google — perubahan = antre ulang).
- **📩 EMAIL T&S PERTAMA MASUK 2026-07-13 17:09 (H+8) — ACTION NEEDED (protokol #2 AKTIF):** Google minta SATU perbaikan: *"demo video does not show the OAuth consent screen workflow — click '3 services' to reveal the scopes"*. **AKAR PASTI (screenshot video lama, 2026-07-14):** video lama memakai akun ryan yang SUDAH pernah memberi izin → consent tampil sbg "additional access" + kotak "already has some access / 3 services" → total scope tak terbukti. **FIX: rekam ulang dgn consent pertama-kali utuh** (klik tiap "See access details"; bahasa English) — 2 opsi akun (§8b-REV; koreksi owner: revoke ryan = mati SEMENTARA, pulih via reconnect 2× RAD+MVT, bukan permanen) — lalu **balas email di thread yang sama dari lumite** dengan link video baru. **Materi lengkap SIAP (2026-07-14): shot-list rekaman ulang + draf email balasan = `GOOGLE_OAUTH_PLATFORM_MIGRATION.md §8b-REV`.** CATATAN POSITIF: bukan penolakan — item lain (privacy/scope/branding) TIDAK dipermasalahkan; JANGAN ubah apa pun di Cloud Console.
  **✅ DIJAWAB owner 2026-07-14:** video ulang direkam sesuai §8b-REV (3 segmen, akun demo fresh `rw23mutiara` daftar email+password, consent utuh) → upload Unlisted `https://youtu.be/0cyiIbvw9QI` (verified aksesibel via oEmbed 200, judul "MesinViral — OAuth Verification Demo (Updated: full consent screen workflow)", channel Mesin Viral) → **email T&S DIBALAS owner di thread yang sama dari lumite** (draf §8b-REV + link). Status: menunggu respons reviewer berikutnya — protokol pantau harian inbox lumite berlanjut.
- **CHECKPOINT 2026-07-11 (H+6):** belum ada email T&S; Verification Center = *"Privacy policy requirements under review"* (normal, masih dalam estimasi). **Audit mandiri privacy/terms vs regulasi Google (support 13806988) LULUS semua butir wajib** — verified baris-per-baris di halaman live: Limited Use disclosure + link kebijakan, pernyataan no-sell/no-ads/no-transfer, link Google Privacy + YouTube ToS, cara revoke, hapus data Google ≤7 hari, brand 46×, HTML non-PDF, link menonjol di homepage (footer, HTTP 200). Keputusan: TIDAK mengubah apa pun; lanjut pantau email harian.
- **📬 PROTOKOL FOLLOW-UP (wajib diikuti sesi mana pun):**
  1. **Pantau `lumite.biz.id@gmail.com` (+folder spam) tiap hari** — kontak pertama T&S dijanjikan **3-5 hari** dari submit (2026-07-05) → harusnya masuk **≤ 2026-07-10**; bila lewat, cek status di Verification Center dulu (bisa saja langsung approved tanpa email).
  2. **Email minta klarifikasi/perbaikan** → owner teruskan isi email ke Claude → Claude draft jawaban (Inggris, rujuk materi: video `youtu.be/xeTCF73pWkg`, privacy/terms, justifikasi §8a doc OAuth) → owner balas DARI email lumite di thread yang sama (jangan buat thread baru). Respons cepat = review tak molor.
  3. **Ditolak (rejected)** → JANGAN panik/utak-atik console dulu → baca alasan persis → perbaiki HANYA yang diminta → resubmit dari Verification Center. (Penolakan umum: video tak menampilkan address bar/consent, link mati, scope tak terdemo — semua sudah kita antisipasi.)
  4. **Approved** → verifikasi nyata: (a) OAuth connect TANPA layar "unverified" (b) refresh-token permanen (bukan 7 hari) → [A4] ✅ → langsung eksekusi **[A5] smoke-test** → pintu publik resmi terbuka.
  5. **>6 minggu tanpa kabar** (> ~2026-08-16) → balas thread email T&S menanyakan status / gunakan tombol kontak di Verification Center.

### [A5] Smoke-test live end-to-end (tenant baru dari nol) — ✅ SUDAH DILAKSANAKAN owner (koreksi 2026-07-13: dokumen telat update — pelanggaran administrasi Claude)
- **TUJUAN:** bukti acceptance utama CHANNEL_LOCK — tenant BARU (bukan ryan) bisa jalan penuh.
- **PLAN (owner + Claude):** signup tenant uji baru → `/integrations` isi kunci AI + connect YouTube (OAuth consent 1× nyata di browser) + Telegram → `/channels/[id]` set niche/model/voice/jadwal → semua 🟢 → Aktifkan → produksi + publish + analytics jalan. + transaksi Midtrans 1× + email egress dari VPS.
- **DONE-BILA:** tenant baru sampai aktif + 1 video publish + bayar — mulus, nol error mentah.
- **REALISASI (dicatat TERLAMBAT — teguran owner 2026-07-13 "selesai tak langsung update = progress terkesan stuck"):**
  smoke-test registrasi+pembayaran SUDAH dilakukan owner memakai akun uji miliknya: **effi** (starter,
  bayar GoPay nyata Rp149rb 2026-07-04 — pembayaran produksi pertama A-Z, lihat [A1]) + **kumala.rw22c**
  (pro, aktif) — keduanya akun demo owner (uang owner), BUKAN pelanggan. + **Rush-Q** (2026-07-13,
  teman owner test registrasi SSO Google → sukses sampai /onboarding, bukti log nginx 17:07). Temuan
  UX dari Rush-Q: pasca-SSO tak ada sapaan/arahan di onboarding → tenant awam bingung (usulan fix
  menunggu ketok owner — lihat changelog 2026-07-13 (4)).
- **DEPENDS:** A1, A2, A4.
- **REALISASI:** ⬜ *(butuh browser owner untuk OAuth consent)*

### [A6] Email deliverability ke EKSTERNAL — ✅ *(RESOLVED 2026-07-02: SPF fix owner + Message-ID/Date fix kode → app-email MASUK INBOX Gmail, verified)*
- **TUJUAN:** email transaksional (verifikasi daftar, reset password, nurture, tagihan) **sampai inbox pelanggan Gmail/eksternal**, bukan bounce.
- **BUKTI (bounce Gmail 550-5.7.26, verified):** kirim ke `kumala.rw22c@gmail.com` DITOLAK — *"sender is unauthenticated… DKIM = did not pass … SPF [lumite.biz.id] with ip: [103.193.179.117] = did not pass"*. Relay keluar = `relay.idcloudhost.com` (`103.193.179.117`) yang **TIDAK ada di SPF** lumite (SPF cuma `103.76.121.147/180`+`103.123.62.104`+antispamcloud) + DKIM `default` terpublish tapi relay tak menandatangani lumite dgn selector itu. Kirim ke lumite-internal (mesinviral@lumite) "berhasil" karena tak lewat cek-auth Gmail → menyesatkan.
- **DAMPAK:** SEMUA email ke pelanggan nyata (mayoritas Gmail) bounce → memblok signup/verify/reset/billing. Sistem/kode BENAR; ini murni DNS/mail-domain (kendali owner).
- **✅ SOLUSI PASTI (verified 2026-07-02):** akar = relay keluar `relay.idcloudhost.com` (`103.193.179.117`) TAK ada di SPF lumite; `include:spf.antispamcloud.com` juga tak memuatnya. **`spf.idcloudhost.com` = `v=spf1 ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148 ~all`** (memuat relay). **FIX: edit TXT SPF lumite.biz.id (cPanel→Zone Editor, BUKAN tombol Repair yg melewatkan smarthost)** → tambah `ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148` (atau `include:spf.idcloudhost.com`). SPF-only cukup (Gmail: SPF OR DKIM). Record final: `v=spf1 ip4:103.76.121.147 ip4:103.76.121.180 ip4:103.193.179.117 ip4:103.193.179.147 ip4:103.193.179.148 include:spf.antispamcloud.com +a +mx +ip4:103.123.62.104 ~all`. DKIM (d=lumite.biz.id ditandatangani tapi gagal verifikasi — selector/kunci tak selaras) = poles terpisah utk DMARC. Opsi world-class: provider transaksional (SES/SendGrid/Postmark). Claude uji-ulang pasca-propagasi.
- **DONE-BILA:** kirim ke Gmail → masuk inbox, header SPF=pass & DKIM=pass, nol bounce.
- **DEPENDS:** — (mandiri, DNS). **Nyambung:** [A2] auth email · [A5] smoke-test · [B9] nurture · [A1] tagihan.
- **✅ RESOLVED — AKAR SEBENARNYA (verified INBOX 2026-07-02, commit `ebb5d90`, deployed mv-worker):** DUA sebab, keduanya beres:
  **(1) SPF** — relay `relay.idcloudhost.com` (103.193.179.117) tak terdaftar → owner tambah `103.193.179.117/147/148` ke SPF → Gmail **SPF=pass, DMARC=pass** (via SPF; walau DKIM=fail). **(2) CACAT KODE** — `email.py::send_email` membangun pesan **TANPA `Message-ID`+`Date`** (RFC 5322) → Gmail buang diam-diam sbg malformed (webmail Roundcube sampai karena header lengkap; email app cuma 632 byte). Fix `ebb5d90`: `make_msgid`+`formatdate` (domain selaras From). **Verified: `notify_payment_receipt` + tes → MASUK INBOX kumala** (bukan spam). Header Gmail email Roundcube membuktikan spf=pass/dmarc=pass/dkim=fail.
  ⚠️ **KOREKSI catatan lama saya:** kesimpulan *"app-mail mati di outbound idcloudhost"* + *"provider transaksional WAJIB"* = **SALAH/keras-kepala**. Penyebab nyata = **cacat header di kode kita sendiri** — bisa & sudah diperbaiki tanpa provider. **DKIM=fail (relay) = poles OPSIONAL** (penempatan-inbox lebih baik / DMARC-strict), non-blocker. Provider transaksional = peningkatan reputasi jangka-panjang, **bukan keharusan**. Pelajaran: bila OUTPUT APLIKASI kita gagal, **periksa output kita sendiri (byte/header) DULU** sebelum menyalahkan infra. `feedback_inspect_our_output_before_blaming_infra` *(aturan kini di CLAUDE.md; berkas memory TIADA)*
- **REALISASI (2026-07-02):** 🟢 **BOUNCE TERATASI** — owner tambah 3 IP relay idcloudhost ke SPF (`103.193.179.117/147/148`) + TTL→300. Verified: uji ke `kumala.rw22c@gmail.com` (tag MVCHECK/recheck) → **NOL bounce** = Gmail TERIMA (SPF lolos). 🟡 **TAPI masuk Spam/Promosi, bukan Inbox** (kumala lapor tak lihat di Inbox) — sebab **DKIM masih gagal** (sig `d=lumite s=default`, kunci `default._domainkey` terpublish TAPI Gmail "DKIM did not pass" → kunci publik tak cocok dgn yg dipakai relay/SpamExperts menandatangani ulang) + reputasi domain baru. **SISA (agar INBOX, penting utk verify/reset/tagihan pelanggan):** (a) mark "Not spam" + reputasi, (b) perbaiki DKIM via support idcloudhost (relay invalidasi tanda tangan), **atau (c) ⭐ pakai provider transaksional (SES/SendGrid/Postmark) = solusi world-class andal utk SaaS.** Keputusan (c) = owner (biaya/infra); Claude siap integrasi bila disetujui.

---

# 🛠️ KELOMPOK B — DEV *(Claude kerjakan; pasca-launch/hardening — TIDAK memblok jualan)*

### [B1] System-secrets admin panel (S1-S4) — ⬜
- **TUJUAN:** secret operasional (Midtrans/SMTP/S3/YouTube-platform-key) editable + rotatable dari admin panel, bukan hanya file `.env`.
- **KONTEKS/BUKTI (verified DB 2026-07-01):** tabel **`system_secrets` TIDAK ADA**; semua secret operasional dari `.env` (interim sah). Spec lengkap = `PROGRESS.md §ADMIN SYSTEM SECRETS`.
- **PLAN:**
  - **S1 (DB):** migr `system_secrets` (`key` PK, `value_enc` Fernet, `category`, `updated_by`, `updated_at`) — RLS **service-role only** (pola `tenant_ai_accounts`). 
  - **S2 (BE):** `src/config/system_secrets.py` — baca DB (Fernet decrypt) → **fallback env** (transisi mulus). Worker/webhook pakai untuk **Kategori A** (Midtrans/SMTP/S3/`YOUTUBE_PLATFORM_API_KEY`/opsional `OAUTH_STATE_SECRET`).
  - **S3 (FE admin):** `/admin/integrations` (service-role, `requireSuperAdmin`) — status set/kosong (masked) + set/rotate + **"Test koneksi"** (reuse pola Test Lab) + audit→`admin_audit`. **Kategori B read-only** (env-managed: `ENCRYPTION_KEY`/service_role+DB-pw/`MV_INTERNAL_SECRET` — chicken-egg, TAK bisa di-DB).
  - **S4:** seed nilai env→DB + validasi (worker baca DB; rotate dari panel berlaku; restart-safe).
- **DONE-BILA:** admin set/rotate secret Kategori A dari panel → worker pakai nilai baru tanpa edit file; Kategori B ditolak edit.
- **REALISASI:** ⬜

### [B2] Cost-tracking REAL per-konten (BYOK) — ✅ *(2026-07-04 — desain disepakati owner: usage on-the-fly + harga auto-sync feed)*
- **TUJUAN:** tampilkan biaya produksi VALID per-video (REAL dari pemakaian), label "biaya provider AI/BYOK — bukan biaya kami". Spec = REMEDIASI **F5-03**.
- **BUKTI kondisi sekarang:** tak ada cost-tracking. Satu-satunya harga = `ai_models.cost_hint` (admin-editable). GAP: (a) adapter LLM `complete()` tak kembalikan token usage; (b) `tts_profiles` tanpa cost_hint; (c) `production_runs` tanpa kolom cost (cuma `run_metadata` jsonb). FE = "Biaya AI coming-soon".
- **PLAN:** (1) adapter LLM (anthropic+openai) kembalikan `usage{input,output tokens}`; pipeline kumpulkan per run. (2) tangkap jumlah gambar (=visual_beats) + karakter TTS. (3) DB: `tts_profiles +cost_hint` (per-char); simpan biaya aktual `production_runs.run_metadata.cost` (breakdown llm/image/tts). (4) hitung Σ. (5) FE kartu "Biaya AI" (dashboard) + kolom Runs — REAL pasca-produksi (ganti coming-soon), label BYOK.
- **DONE-BILA:** tiap run baru tulis biaya breakdown nyata; FE tampil per-konten.
- **REALISASI:** ✅ **2026-07-04.** (1) **Konsumsi on-the-fly, NOL overhead**: `cost_meter` (thread-local per-run) — adapter LLM tangkap `resp.usage` (Anthropic+OpenAI), gpt-image-1 tangkap token usage respons Images API, TTS catat karakter (edge=Rp0), pipeline reset/summary (run GAGAL pun dicatat — uang terpakai). (2) **Harga TANPA beban manual**: `price_sync` tarik feed komunitas LiteLLM harian (via janitor, guard `app_config.ai_price_synced_at`) → `ai_models.pricing` jsonb (migr 0120); `pricing_locked` = override admin (wajib utk ElevenLabs — harga tergantung paket langganan; edge di-set Rp0+locked); verified sync nyata: 7 model terisi otomatis, harga cocok list resmi (gpt-4o-mini $0.15/$0.60 dst). (3) `ai_cost.compute_cost_usd` → `run_metadata.{ai_usage,cost}` (USD beku saat produksi + breakdown llm/image/tts + `unpriced` jujur) di 3 penulis run (scheduled/direct/test). (4) FE: Catalog kolom harga+🔒lock+edit manual+⚠️model-aktif-tanpa-harga · dashboard kartu "Biaya AI (30 hari)" REAL (Σ×kurs `app_config.usd_idr_rate` admin-editable) · kolom "Biaya AI" di Runs (+⚠️ bila ada model unpriced). Uji: skenario 60s ≈ $0.108/video; thread-isolation meter terbukti. **Aksi owner 1×: isi harga ElevenLabs di Catalog (sesuai paket langganan) + lock.**

### [B3] Sapu hardcode sisa — ✅ SELESAI TOTAL (2026-07-05, deployed `6147918`+`6d76cb3`+`1670a1f`)  (REMEDIASI **F5-02**)
- **TUJUAN:** nol hardcode kritis; semua config-driven.
- **PLAN + anchor [cek-baris] (grep dulu):** Ken-Burns motion per-role/zoom `ai_image.py:~417-463` → `niches.motion_profiles` (kolom baru) · `BASE_NICHE_TIERS` `billing/limits.py:~59` → `app_config` · `OPTIMAL_PUBLISH_SLOTS` `tenant_config.py:~82-88` → `app_config`.
- **DONE-BILA:** grep hardcode kritis bersih; perilaku produksi identik (uji ryan).
- **REALISASI (proposal→approval owner→eksekusi, 2026-07-05):**
  - ✅ `BASE_NICHE_TIERS` — tuntas 2026-07-04 via **0124** `plan_limits.full_niche_catalog` (lebih tepat dari rencana app_config).
  - ✅ `OPTIMAL_PUBLISH_SLOTS` — deep-dive membalik solusi: **FOSIL** (nol pemakai; jadwal nyata = `channels.publish_slots` per-channel, dibaca publisher) → DIHAPUS tuntas (+field dataclass `publish_slots`/`auto_schedule`); verified load config ryan mulus.
  - ✅ **BONUS gap timezone (temuan deep-dive):** tenant tak bisa set zona waktu → semua tenant baru terjebak UTC (slot "20:00" = 03:00 WIB!). Fix **0125**: auto-detect zona browser saat load app (hanya bila belum manual) + field "Zona waktu" di Settings (dropdown IANA + pratinjau jam) + RPC `set_tenant_timezone` (SECURITY DEFINER, tervalidasi `pg_timezone_names` — tz asing DITOLAK, diuji live) + flag `timezone_set_by_user`.
  - ✅ **Default slot channel baru** `["13:00"]` FE → `app_config.default_publish_slots` (kolom baru `value_text` utk config teks/JSON + editor admin render baris teks + PATCH validasi JSON).
  - ✅ **Ken-Burns motion Fase 1 — SELESAI + DEPLOYED `1670a1f` (2026-07-05).** Configurable per-niche via `niches.visual_style.camera_motion.intensity` (JSONB, nol migrasi kolom). **4 tingkat** Halus(0.6×)/Normal(1.0×)/Dinamis(1.5×)/Cepat(2.2×). Perbaikan world-class atas kode lama: **kecepatan-konstan + full-span** (gerak menyapu SELURUH klip, hilang "ekor statis" paruh-kedua di klip panjang; travel di-clamp [0.10,0.30] bentuk-durasi lalu ×faktor, batas mutlak 0.60). **Durasi preset TERKUNCI** (motion tak sentuh `-t`; uji 2s–15s output tepat + 72 kombinasi vf valid + fallback ngawur→normal). Seed 6 niche per-karakter (migr 0127: fun_facts→dinamis, misteri/imunitas→halus). Default niche baru = normal (template warisi karakter). UI seksi "Gerakan Kamera" di editor DNA (admin+tenant, dwibahasa). Validasi `validateDnaPatch` terima camera_motion. "Seimbang"→"Normal". Sampel disetujui owner (4 klip dari frame ryan nyata).
  - ✅ **Unifikasi kosakata peran (Stage 1 Fase 2, deployed `8bfb85c` 2026-07-05):** SATU SUMBER `content_beats` (migr 0128) + `src/content/beats.py` (DB+fallback). script_engine/tts/renderer/ai_image derive dari 1 sumber (dulu tersebar ~10 tempat). **core_facts_2 mati DIBUANG** (kanonik 8 peran); pattern_interrupt tetap (cadangan preset 8-segmen). Turunan==nilai lama PERSIS (terbukti DB+fallback, zero-behavior-change). FE niche-dna.ts sudah kanonik-8 (mirror).
  - ✅ **Fase 2 motion (arah) — SELESAI + DEPLOYED `44b6f9c` (2026-07-05):** arah per-segmen level SYSTEM, mode **Fix/Cerdas** per 8 segmen (migr 0129 di content_beats: motion_mode/motion_dir/motion_rate). **9 arah** (zoom in/out, pan kiri→kanan/kanan→kiri/atas→bawah/bawah→atas/diagonal/diagonal-balik/diam). **Cerdas** = variasi deterministik anti dua-adegan-searah-berturut, hormati momen. UI tabel di System Configuration (dwibahasa) + API `/admin/beats`. **Default Fix-semua = perilaku Fase 1 PERSIS** (96 kombinasi terbukti → deploy nol-perubahan; arah baru/cerdas DORMAN sampai admin aktifkan per-segmen). Durasi terkunci (9 arah render tepat). **Audit final temukan+perbaiki 3 isu** (hook-frame ikut config, rate≤0 zoom default, bug `or` swallow rate 0.0). Ken Burns configurable = **TUNTAS A-Z**. Nuansa disclosed: cerdas hook↔adegan-2 adjacency (hook selalu zoom_in → dampak ~nol).
  - ✅ **Temuan kualitas owner (2026-07-05, approved "SEGERA BERESKAN" — DEPLOYED+LIVE `6d76cb3`, 3 service active + situs 200 + log worker nol error):** (1) state mesin (`ai_price_synced_at`+`ai_price_stale_alerted_at`) pindah ke tabel baru **`system_state`** (migr 0126, RLS service-only) + tampil manusiawi read-only dwibahasa di Kesehatan Sistem ("terakhir disinkron: 04 Jul 2026, 17.24 WIB"); (2) **kurs USD→IDR auto-sync harian** (`sync_fx_rate` via janitor, band waras 5k-60k, fail-soft) — uji live: 16500 basi → **17982** kurs pasar; edit manual → auto-lock `usd_idr_rate_locked` (mesin berhenti menimpa); (3+4) **System Configuration dwibahasa PENUH** — 39 key label+desc+unit ID/EN, toast & error dwibahasa (server kirim kode, FE terjemahkan). Aturan baru dipatri+diterapkan: `feedback_bilingual_mandatory` *(aturan kini di CLAUDE.md; berkas memory TIADA)*.
  - ✅ **Koreksi perilaku timezone (pertanyaan owner Jakarta→Bali):** auto-detect = INISIALISASI SEKALI (hanya saat zona masih UTC default & belum manual) — bepergian TIDAK menggeser jadwal; ubah zona = sadar via Settings→Profil.

### [B4] Pivot Analytics FE → kinerja-mesin — ✅ SELESAI (dikonfirmasi owner + divalidasi data 2026-07-05)
- **TUJUAN:** `/analytics` jangan duplikat YouTube Studio; fokus KINERJA MESIN (success-rate/QC/durasi trend, self-learning niche/hook, biaya per-konten) + link YT Studio.
- **REALISASI (verified 2026-07-05):** desain final TERBAGI DUA dan koheren (menggantikan ide lama "buang semua YT-raw dari /analytics"):
  - **Per-channel** (`channels/[id]` tab Analytics): PERSIS spec — "Kinerja mesin — channel ini" (total run/success-rate/QC/gagal, count penuh) + kalimat eksplisit "metrik YouTube mentah ada di YouTube Studio — kami tak menduplikasinya" + tombol YouTube Studio.
  - **Lintas-channel** (`/analytics` menu utama): total/avg SEMUA channel + per-niche + top video + self-learning (hook/topik) — BUKAN duplikat Studio (Studio tak bisa agregasi lintas channel); CTR dibuang (tak tersedia API). Biaya AI = kartu dashboard + kolom Runs (B2).
  - **Validasi 100%:** 5 RPC halaman (`get_tenant_analytics_overview/by_niche/monthly/top_videos/learning`) diuji sebagai ryan (emulasi JWT di DB) → semua OK berisi data nyata (191 video, 41.6K views, dst.). Owner konfirmasi visual.

### [B5] Sapu fosil inert — ⬜
- **BUKTI (verified 2026-07-01):** `channels.production_cron` (kolom masih ada; dimuat ke dataclass `tenant_config.py:539` tapi v2 pakai loop+`publish_slots`, TAK menjadwalkan) · tabel `pipeline_queue` (ADA tapi cuma disebut di komentar `producer.py:92,269`, tak dibaca). ⚠️ **`channels.niche_pool`/`niche_mode` = AKTIF, JANGAN drop.**
- **PLAN:** setelah pastikan nol pembaca (grep) → migr drop `production_cron` + evaluasi drop `pipeline_queue`. Hati-hati, nilai rendah — kerjakan hanya bila bersih.
- **DONE-BILA:** kolom/tabel fosil hilang, nol regresi.
- **REALISASI:** ⬜

### [B6] ai_video 8s (render mode text-to-video) — 🟡 **FITUR LIVE utk tenant sejak 2026-07-14** (preset 8s + niche radiant DNA v3 + 5 model video [kling/veo/hailuo aktif · seedance×2 nonaktif [B18]]) — SISA: turnamen Test owner pilih model pemenang → 1 run e2e final → tutup
- **SPEC + tracker LENGKAP = `AI_VIDEO_8S_PLAN.md`** (deep-dive terverifikasi 2026-07-14: inventaris siap-vs-gap ber-anchor + fase F0 riset-vendor → F1 DB → F2 BE → F3 FE → F4 bukti-runtime; tiap fase ber-gerbang). Keputusan owner FINAL tercatat di §0 dokumen itu: 8s KHUSUS text-to-video · vendor TIDAK dikunci (katalog extensible, riset dulu vendor ber-parameter+biaya seragam; rekomendasi = agregator fal.ai/Replicate) · BUKAN SaaS baru · konten 8s = kutipan/afirmasi/motivasi, positioning KHUSUS volume+retensi · niche DEFAULT 8s dibuat tersendiri khusus kutipan/motivasi (masuk F1).
- **Temuan kunci deep-dive:** jauh lebih siap dari catatan lama — preset 8s SUDAH di DB (is_active=false), naskah/skor-viral/QC/gerbang-durasi sudah sadar-8s, FE picker sudah siap component video, `providers/visual/ai_video.py` ADA tapi stub. Gap inti = adapter t2v + prompt-video + katalog `ai_models` video (NOL baris) + cost meter + validator kunci + bukti presisi durasi (gerbang F4 §7.3).
- **DONE-BILA:** preset 8s produksi 1 klip ai_video + audio + publish (F4 dokumen plan: presisi 6.8–9.2s min 3 run + nol regresi 60s).
- **REALISASI:** 🟡 LIVE (tracker penuh = `AI_VIDEO_8S_PLAN.md` — F0–F3 deployed; DNA v3; harmonisasi durasi F4-program). Header lama "menunggu ketok F0" = basi, dikoreksi 2026-07-16. SISA: Test owner (5 kandidat) → pemenang → e2e → tutup.

### [B7] Go-live checklist teknis / PROGRAM PENYAPU RANJAU — ✅ **RESMI DITUTUP OWNER 2026-07-21** (tak perlu putaran tambahan) · E2E terbukti tenant nyata (daftar/bayar/hubung-YouTube/video-terbit terbukti data produksi) · sapu kode+DB nol ranjau berbahaya (T1 fix · T2 ditolak · C1-C3 bukan ranjau)
- **MANDAT & METODE (dikunci 2026-07-15):** B7 = 2 fase berurutan.
  **Fase-STUDI (prasyarat mutlak, sesi khusus ber-konteks segar):** baca TUNTAS urutan kanonik MEMORY.md → progress_journal → PROGRES.md → seluruh dokumen SPEC (DESAIN/MULTI_FORMAT/QC/REMEDIASI/CHANNEL_LOCK/PER_CHANNEL_OAUTH/PAYMENT/LIFECYCLE/AI_VIDEO_8S/AUDIT_ATRIBUSI) + introspeksi DB live + git log penuh → hasilkan **PETA-BENAR** (spesifikasi perilaku-benar per subsistem — baseline utk memvonis "salah").
  **Fase-SAPU:** regresi e2e semua preset(8/15/30/45/60/75/90) × niche nyata × kedua channel × kedua mode visual + sisiran kelas-bug terbukti (atribusi lintas-permukaan 5 area · fosil/label basi · fallback senyap · konsumen-per-kolom sebelum klaim "tak dipakai") — tiap butir ber-BUKTI eksekusi; keluaran = dokumen audit yang bisa diaudit owner.
- **DONE-BILA:** Peta-Benar terbit + seluruh matriks sapu hijau/temuan-tereksekusi.
- **⚖️ PERINTAH PEMBERESAN (owner 2026-07-15 ~04:00 — MENGIKAT SEMUA SESI s/d owner menyatakan selesai):** (1) HANYA perbaiki yang terbukti rusak — haram fitur baru/ubah arsitektur/file baru/"sekalian"; (2) urutan: jalani perjalanan calon pembeli dari nol → temuan DILAPORKAN ber-bukti → fix HANYA setelah owner "setuju" → ulang sampai LULUS 3× beruntun tanpa temuan; (3) laporan bahasa sederhana tanpa jargon/kode-item; (4) deploy hanya dgn kata "deploy"; progres dicatat DI FILE INI SAJA; (5) butuh tangan owner → BERHENTI & sebut persis kebutuhannya; (6) SELESAI = vonis OWNER dari bukti.
- **🔁 REFRAME FINAL (mandat owner 2026-07-15, "JALANKAN; bug fixing — bukan memenggal arsitektur; SATU daftar kerja ini saja, JANGAN tambah file):** prioritas [B7] = **buktikan jalur calon pembeli berulang sampai membosankan** (daftar → trial → bayar → hubungkan YouTube → set channel → video pertama TERBIT BENAR → dashboard benar), tiap langkah ber-BUKTI di kolom REALISASI SINI; temuan = lapor → ketok → mati di titiknya. **Yang menyatakan "siap jualan" = OWNER** dari bukti di item ini. Pinggiran disapu setelah jalur inti bosan-karena-lulus.
- **REALISASI (Putaran-1, porsi otonom, 2026-07-15 ~05:00): 7 LANGKAH PEMBELI LULUS SEMUA, temuan bug NOL.** Sebagai orang asing sungguhan (akun `pembeli-uji-01@example.com`, jembatan tunggal = link konfirmasi diambil setara-isi-email): daftar via endpoint asli ✓ → klik konfirmasi ✓ (redirect verified) → login ✓ → **trial 3 hari otomatis** ✓ (s/d 18-Jul) → 45 niche terlihat + 3 base ✓ → buat channel via RLS asli ✓ (draft non-aktif, benar) → setelan gratis tersimpan ✓ → **gerbang kesiapan bicara JUJUR & spesifik**: "kurang: kunci naskah, kunci visual, koneksi YouTube, Telegram" ✓. **Catatan produk (bukan bug, utk owner):** (a) di titik inilah 2 pembeli nyata dulu berhenti — tembok upaya BYOK (buat kunci Groq/CF gratis + OAuth) adalah gesekan funnel terbesar; (b) Telegram ikut WAJIB di gerbang kesiapan — konfirmasi owner: memang by-design? **LANJUTAN BUTUH TANGAN OWNER (±15 mnt):** (1) kunci Groq & Cloudflare gratis BARU (daftar sbg pembeli; JANGAN kunci milik channel lama — realistis), (2) hubungkan YouTube akun uji segar, (3) chat-id Telegram uji / keputusan soal (b) — lalu porsi saya lanjut: produksi video pertama pembeli → terbit → dashboard, dgn bukti per-langkah. Akun uji sintetis DIHAPUS BERSIH 2026-07-15 (izin owner "ya hapus"; verified auth+DB kosong). **Subjek putaran selanjutnya = PEMBELI NYATA: kumala (pro berbayar, YouTube sudah valid — disiapkan owner) lalu mutiara (trial).**
  **REALISASI (Putaran-SAPU-KODE otonom, 2026-07-21): sapuan read-only 7 kelas-bug × 5 permukaan (kode+DB live), nol kode disentuh.** Hasil: sistem SANGAT bersih pada kelas-bug terbukti. **2 temuan minor + 3 catatan-konfirmasi (semua ber-bukti, MENUNGGU ketok sebelum fix apa pun):** (T1 fosil, LOW) `tenant_config.py:667-668,673` komentar rujuk kolom `channels.{tts,visual,llm}_key_enc` yang SUDAH DI-DROP migr 0095 (nilai=None benar, kredensial via POOL — hanya komentar menyesatkan); (T2 ketahanan email — ❌ DITOLAK OWNER 2026-07-21, JANGAN diungkit lagi) `email_outbox.py:43-48` SMTP gagal transien → status='failed' PERMANEN, nol retry; provider idcloudhost konfirmasi gangguan = sisi relay mereka (transien, sudah diperbaiki, bisa terulang); owner memutuskan TIDAK perlu retry otomatis — biarkan apa adanya; (C1 ✅ VONIS: BUKAN ranjau) `admin_test_internal` tanpa auth.users = fixture uji internal by-design — biarkan; (C2 ✅ VONIS: BUKAN ranjau) `channel_analyst.py:221` dosir weekly `[:10]` = ringkasan SENGAJA (input LLM ringkas); kurva retensi 15-mgg B17 jalur terpisah `video_retention_curves` tak terpengaruh — biarkan; (C3 ✅ VONIS: BUKAN ranjau) 2 `tenant_youtube_accounts` 'unchecked' = artefak onboarding NORMAL (riandipantria daftar 21-Jul, di tengah proses hubungkan YouTube) — hapus justru ganggu tenant; `_delete_placeholder` menangani saat selesai — biarkan. **TERBUKTI BERSIH (bukan ranjau — bukti ketelitian):** nol `except:pass`/fallback senyap · `_fetch_paged` = paginasi benar anti-cap-1000 · nol hardcode harga/model (DB-driven) · nol orphan lintas 24 tabel tenant (2 auth-orphan = admin platform + agen THETANGGA by-design) · `ready_with_issues` punya jalur tinjau `/review` + janitor tutup-loop · gerbang `channel_missing` blokir 'unchecked' benar (gagal-jujur) · katalog DB nol residu uji. Bagian perjalanan-pembeli e2e TETAP menunggu tangan owner (kunci segar+OAuth+Telegram, sudah tercatat di atas). **PUTARAN-SAPU-KODE DITUTUP 21-Jul:** T1 ✅ diperbaiki+push (`343b2f2`, komentar fosil→POOL; nol runtime) · T2 ❌ ditolak owner · C1/C2/C3 ✅ divonis BUKAN ranjau (biarkan). Nol ranjau berbahaya tersisa dari sapuan kode+DB.
  **PERJALANAN-PEMBELI E2E ✅ TERBUKTI TENANT NYATA (vonis owner 21-Jul + verifikasi DB live):** setiap MATA RANTAI terbukti oleh data produksi nyata — **daftar** (semua) · **bayar** (kumala pro + effi starter = pembayaran Midtrans SUKSES nyata) · **hubungkan YouTube** (tessartea/tomasterix/m.yusroon/kumala = tenant_youtube_accounts status valid) · **video PERTAMA TERBIT** (tessartea 1, tomasterix 2, m.yusroon 1 = videos status='published' NYATA di YouTube). Catatan jujur: tak ada 1 tenant yang lakukan SEMUA langkah dalam satu rantai (3 trial terbit tanpa bayar; 2 berbayar belum produksi), tapi tiap link terbukti hidup; ada kegagalan video wajar (m.yusroon 1/4 pub, tomasterix 2/3 — QC/retry normal, pace m.yusroon sudah ditangani 20-Jul). Mesin inti pencetak-uang (produksi→publish) BEKERJA utk orang asing nyata. **B7 = tuntas kecuali owner ingin putaran tambahan.**
  *(Riwayat)* Putaran-0 (probe permukaan publik): 11/11 LULUS, temuan NOL — landing/pricing/signup/showcase/docs/privacy/terms semua 200 · www→apex ✓ · harga anon benar (149/349/699rb) · preset tampil 8–90s · 45 niche publik. **Putaran-1 (perjalanan penuh akun segar)** = porsi Claude (signup email+pass, set channel, produksi, dashboard — per-langkah ber-bukti) + **2 segmen tangan-owner:** OAuth YouTube akun segar & 1 pembayaran nyata (atau keputusan owner: jalur trial dulu).

### [B8] Halaman `/feedback` (masukan trial-lapse) — perbaiki link MATI di email — ✅ *(SELESAI + LIVE-validated 2026-07-03)*
- **TUJUAN:** tenant yang trial habis (dan siapa pun penerima email trial-lapse) punya halaman masukan NYATA ber-brand → kumpulkan alasan tak-upgrade (lead insight berharga) + hilangkan kesan buruk link mati. **Keputusan owner 2026-07-01: Opsi B (halaman sendiri, bukan Google Form).**
- **KONTEKS:** email `notify_trial_lapse` (`src/utils/email.py:92-101`) mengajak isi survei ke `_survey_url()` → default `https://mesinviral.com/feedback` (`email.py:72-73`), TAPI rute `/feedback` **TIDAK ADA** di FE → **404 LIVE** ke tenant nyata (dilaporkan owner: email trial-lapse yang diterima). Trial-expired ditandai **LEAD marketing** (`billing/renewal.py:49`) → masukan ini punya nilai bisnis. Kata "feedback" lain di FE hanya copy marketing (`(marketing)/page.tsx:168`) + widget docs "Apakah artikel ini membantu" (`docs/page.tsx:47`) — **bukan** halaman.
- **BUKTI (verified 2026-07-01):** `curl -L https://mesinviral.com/feedback` → **HTTP 404**. `find/grep apps/web/src/app` → nol rute `/feedback`. Saklar `TRIAL_SURVEY_URL` sudah ada (env-override, default arahkan ke halaman ini → nol perubahan email saat halaman hidup).
- **PLAN (world-class; propose rincian sebelum koding — `feedback_workflow` *(aturan kini di CLAUDE.md; berkas memory TIADA)* + `feedback_world_class_quality` *(aturan kini di CLAUDE.md; berkas memory TIADA)*):**
  - **FE:** halaman **publik** `/feedback` (marketing group — penerima email mungkin belum login) — form ber-brand: alasan belum upgrade (pilihan terkurasi + isian bebas) + pesan + email (prefill bila token/login) + i18n ID/EN (pola Bi seperti halaman lain). Sukses → state terima-kasih (bukan reload). Reuse komponen/kelas UI yang ada (jangan bikin versi lebih jelek).
  - **Atribusi:** email sisipkan token/ref tenant (mis. `?ref=<token>`) agar masukan terhubung ke lead/tenant tanpa tenant mengetik ulang.
  - **DB (no-hardcode, RLS service-role):** simpan submission — putuskan saat propose: perluas `leads` (trial-expired sudah lead) ATAU tabel `feedback_submissions` dedicated. 
  - **Notifikasi + admin:** Telegram admin saat masuk + tampil di admin panel (reuse pola **Leads** `/admin`, Phase 10.1) — jangan bikin subsistem duplikat.
  - **Email:** pertahankan `TRIAL_SURVEY_URL` (default kini VALID) → link email otomatis hidup, nol link mati.
- **DONE-BILA:** klik link di email trial-lapse → halaman `/feedback` hidup (bukan 404); kirim masukan → tersimpan di DB + admin bisa lihat + Telegram masuk; email tetap arahkan ke sini.
- **DEPENDS:** — (mandiri). **Nyambung:** admin **Leads** (Phase 10.1), email `notify_trial_lapse`; halaman ini **di-reuse [B9] LIFECYCLE** utk feedback 1-klik (`?reason=`).
- **REALISASI:** ✅ **SELESAI + LIVE-validated 2026-07-03** (commit `3927c41`). Verifikasi menemukan 2 gap → keduanya DIBERESKAN: (1) **Notif Telegram admin saat masukan masuk** (sebelumnya TIDAK ADA): method `TelegramNotifier.notify_admin_feedback` (reuse `notify_admin` → `company_profile.admin_telegram_chat_id`) + endpoint internal `webhook_app` `POST /api/feedback/notify-admin` (X-Internal-Secret; token bot hanya sisi Python) + route `/api/feedback` panggil `vault()` pasca-insert (fail-soft, tak blokir submit). (2) **Atribusi `?ref=`**: `notify_trial_lapse`/`notify_trial_ending` sebelumnya kirim link POLOS (`_survey_url()`) → kini `_feedback_url(tenant_id, "trial_lapse"/"trial_ending")` (jalur nurture [B9] sudah benar sejak awal). Yang sudah benar & TIDAK disentuh: halaman `/feedback` (baca `?ref/?source/?reason`), API insert, `/admin/feedback`, migr 0110. **Bukti LIVE e2e:** POST `/api/feedback` produksi → `{"ok":true}` + row DB dgn `tenant_id` dari ref + log mv-webhook `[Telegram] ✓ Notifikasi terkirim` + pesan masuk ke Telegram admin; row tes dihapus. Deploy: mv-worker+mv-webhook restart, mv-web rebuild+restart, situs 200.

### [B9] Mesin siklus-hidup & nurture (trial-lapse + suspended→blocked→deleted) — ✅ *(DEPLOYED + LIVE 2026-07-02)*
- **TUJUAN:** selamatkan trial-lapse + pelanggan berhenti-bayar (dunning/win-back) + blokir & **hapus data** yang tak kembali (bebaskan storage) — world-class, no-hardcode, patuh UU PDP.
- **KONTEKS:** SATU mesin (perluas thread `billing_renewal`/`renewal.py`, BUKAN thread baru). Keputusan owner TERKUNCI (nurture 4–5 email/~2–3 mgg; suspended 30h → blocked 30h → deleted; purge S3 video-mentah dini; hot-lead→Telegram admin; ekspor self-service DITUNDA). Reuse `/feedback` [B8] + Leads admin + email lifecycle.
- **SPEC LENGKAP + Plan-vs-Realisasi (13 item) = `LIFECYCLE_NURTURE_ARCHITECTURE.md`** (sumber kebenaran fitur ini).
- **DONE-BILA:** sekuens nurture jalan; `suspended→blocked→deleted` otomatis + peringatan H-30/7/1; purge S3 dini; token YouTube dicabut saat delete; knob tampil di System Config.
- **DEPENDS:** idealnya SETELAH **[A1]** (butuh aliran tenant nyata). **Nyambung:** [B8] /feedback · [D1] funnel · `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` (state machine gate).
- **REALISASI:** ✅ **DEPLOYED + LIVE 2026-07-02** (commit `db589b1`). Mesin lifecycle PENUH LIVE: nurture trial-lapse (5-email config) + suspended→blocked→deleted (30+30h) + purge S3 dini + revoke token YT (UU PDP) + diskon comeback + reaktivasi 1-klik (`/reactivate`) + banner blocked + admin lead_temp. Sweep terverifikasi bersih (nol hapus mendadak; timing di `app_config`). Detail+tracker = `LIFECYCLE_NURTURE_ARCHITECTURE.md §11`. **Follow-up SELESAI 2026-07-03:** ✅ tombol aksi-manual admin (`6a5f798`: Perpanjang trial / Undur hapus / Aktifkan-bersih / Hapus-permanen + ConfirmDialog + footgun Suspend@blocked) · ✅ Telegram admin di-wire ke `company_profile.admin_telegram_chat_id` (`603640e`, migr 0114, editable via `/admin/company-profile` — **bukan env**). **LIFECYCLE = 100% & dokumen di-CLOSE (direkonsiliasi vs realita via 2 verifikator 2026-07-03).**

- **✅ TEMUAN AUDIT 2026-08-04 — TUNTAS TANPA PERLU KETOK BARU (jawabannya SUDAH ada di SPEC):**
  Keempat tabel diselesaikan dengan MEMBACA dokumen, bukan menanyakan owner — teguran owner:
  *"anda sudah baca AGENT_AND_AFILIATION? buat apa file MD dibuat? pajangan?"*
  | Tabel | Putusan | Pasal yang mengetoknya |
  |---|---|---|
  | `commission_ledger` | **SIMPAN** | AGENT §5g.8 "seluruh ledger/payout DISIMPAN (kewajiban audit & pajak)" |
  | `tenant_attribution` | **SIMPAN** | AGENT §1.3/§2 "terkunci PERMANEN"/"selamanya" · "Masa komisi: SELAMANYA" |
  | `video_retention_curves` | **HAPUS** | LIFECYCLE §4.2 (data per-video, sekeluarga `video_analytics`) |
  | `channel_decisions` | **HAPUS** | LIFECYCLE §4.2 (data per-channel, sekeluarga `channel_insights`) |
  **Alasan atribusi jauh lebih berat dari "kerapian data"** (diverifikasi, bukan dugaan): akun login tenant
  TIDAK ikut dihapus (nol `deleteUser` di seluruh jalur) DAN atribusi hanya ditulis saat PENDAFTARAN ⇒
  bila dihapus lalu tenant kembali & bayar, `partner.record_settlement_commission` tak menemukan
  atribusinya → tenant jadi "bukan bawaan siapa pun" (§1b) → **agen kehilangan komisi SELAMANYA tanpa tahu.**
  **Hasil:** 19 tabel dihapus · 5 disimpan (tiap satu menyebut pasalnya) · **nol tabel ber-`tenant_id`
  tanpa kategori** (24/24). `LIFECYCLE §4.2` diperbarui — daftarnya sudah sebulan basi.
  **PENJAGA (akar masalahnya, bukan gejalanya):** `tests/test_purge_pdp_lengkap.py` — 9 uji; MERAH bila
  (a) tabel ber-`tenant_id` tak masuk kategori mana pun, (b) alasan simpan tak menyebut pasal SPEC
  (memaksa sesi berikutnya MEMBACA dokumen, bukan bertanya), (c) dua tabel uang agen masuk daftar hapus,
  (d) **daftar di DOKUMEN §4.2 tak selaras dengan kode** — merah dibuktikan dengan sengaja membusukkan
  dokumennya. Suite 647 → **650**.
- **❓ TERBUKA, BELUM PERNAH DIKETOK (jangan diputuskan sendiri):** hard-delete **tidak menghapus akun
  login** tenant ⇒ **email tenant tetap ada di `auth.users`** padahal ia minta datanya dihapus. Mungkin
  DISENGAJA sebagai anti-abuse (penanda masa-coba ikut bertahan sebagai jangkar → cegah panen trial ulang),
  tapi **nol baris di dokumen mana pun menyatakannya** — jadi tak diketahui rencana atau terlewat.
  Keputusan ini TIDAK mengubah putusan 4 tabel di atas (atribusi tetap wajib disimpan dalam kedua
  kemungkinan). Diusulkan dibahas bersama konsultan pajak/hukum (AGENT §6b) — bukan diputuskan terpisah.
- **~~TEMUAN AUDIT (versi awal, sudah digantikan blok di atas)~~:** daftar
  penghapusan data (`_PURGE_TABLES` di `renewal.py`) **tertinggal dari skema**. Diukur, bukan ditebak:
  **24 tabel di DB live punya kolom `tenant_id`**; 17 dihapus, 3 terdokumentasi disimpan
  (`payments` legal · `tenant_configs` dianonimkan · `feedback_submissions` anonim) ⇒ **4 TABEL TIDAK
  DIHAPUS DAN TIDAK ADA KETERANGAN MENGAPA DISIMPAN**: `channel_decisions` · `commission_ledger` ·
  `tenant_attribution` · `video_retention_curves`.
  **Akar (bertanggal, bukan tuduhan):** spec purge dibekukan **3-Jul** (`LIFECYCLE_NURTURE_ARCHITECTURE.md`
  §98); keempat tabel itu lahir **SESUDAHNYA** (program agen [B21] · kecerdasan [B17] · retensi). Kode
  PATUH pada spec — spec-nya tak diperbarui saat tabel baru ditambah. Pola yang sama akan terulang setiap
  kali tabel ber-`tenant_id` baru lahir.
  **BOBOT: kepatuhan UU PDP** (hak hapus data), bukan kerapian. **HARAM Claude putuskan sendiri** —
  menghapus data = aksi IRREVERSIBLE (CLAUDE.md §2.3d), dan dua di antaranya (`commission_ledger`,
  `tenant_attribution`) sangat mungkin WAJIB DISIMPAN sebagai catatan keuangan/komisi seperti `payments`
  — itu ranah konsultan pajak/hukum (lihat `AGENT_AND_AFILIATION_ARCITECTURE.md` §6b), bukan ranah kode.
  **Usul: (a)** owner putuskan per-tabel: hapus · simpan-dengan-alasan · anonimkan; **(b)** pasang uji
  anti-drift yang MERAH bila ada tabel ber-`tenant_id` tak terdaftar di salah satu kategori — supaya
  tabel berikutnya tak lolos diam-diam lagi.

### [D9] ✅ SELESAI 2026-08-05 — "Perlu Ditinjau" dipakai untuk pekerjaan yang tak pernah ada
> **⛔ PASCA-COMPACTION: BACA SELURUH ITEM INI SEBELUM MENYENTUH panel tenant / runs-table / janitor.**
> Analisis LIMA RANTAI (`CLAUDE.md` §0.7) sudah TUNTAS. **JANGAN diulang, JANGAN dianalisis ulang.**
>
> **✅ REALISASI (ketok owner 05-Agu: "kerjakan tanpa merusak yang sudah berjalan"). SSOT = `QC_CONTENT_ARCHITECTURE.md §7.5` blok "PEMISAHAN NAMA".**
> **Vonisnya: bukan penutup baru yang dibutuhkan, melainkan NAMA YANG JUJUR.** Nama "Perlu Ditinjau"
> dikembalikan ke pemiliknya (antrean `content_inventory.ready_with_issues` — menu + `/review`, satu-satunya
> tempat ada tombol Pakai/Buang); buku-besar `production_runs` memakai **"Ada catatan QC"**.
> **Nol kolom baru · nol RPC · nol migrasi · nol sentuhan mesin · nol pekerjaan untuk tenant.**
> 4 berkas layar: `runs-table.tsx` (lencana+tab+laci) · `runs/[id]/page.tsx` (lencana+2 jalan buntu ditutup
> via `punyaItemTinjau`) · `dashboard/page.tsx` (label; sekalian 3 label yang dulu monolingual → §3.5) ·
> `channels/[id]/page.tsx` (label KPI). Penjaga: `tests/test_label_tinjau_tak_bohong.py` (11 uji, **merah
> dibuktikan lebih dulu: 5 gagal**). Bukti: tsc bersih · build ✓ · **779 uji lulus** (dari 768) · replikasi
> predikat pada **9 baris nyata** → 8 run uji **nol tombol ke halaman kosong**, 1 run terjadwal (#344)
> tombolnya muncul dan memang berisi · aritmetika buku-besar **232+79+9+9 = 329 COCOK**.
> **⏳ Belum di-deploy — menunggu izin owner per §5.0.**
>
> **DUA RANCANGAN SAYA SENDIRI YANG DIGUGURKAN — jangan dihidupkan lagi:**
> 1. ❌ *Tombol "Sudah saya tangani" + status ledger baru* → **akan mengubah rem darurat channel diam-diam**:
>    `inventory.py:164` menghitung `qc_failed` sebagai +1 kegagalan; status lain = netral. Mengubah status =
>    mengurangi hitungan = rem melonggar tanpa ketok (§0.6 perilaku-saat-gagal = keputusan produk).
> 2. ❌ *Tombol + kolom penanda `reviewed_at`* → tombolnya **upacara**: nol bagian sistem yang menunggu
>    jawaban tenant (publisher tak punya barisnya · kuota sudah terhitung · rem tak terpengaruh). Meminta
>    tenant membereskan pembukuan atas cacat kita = beban yang tak semestinya ada.
>
> **Yang TIDAK diubah, dan alasannya:** sumber angka Beranda & KPI channel **tetap** `production_runs` —
> keduanya rincian buku-besar (`dibuat = sukses+gagal+catatan+dibuang`); mengambil salah satunya dari tabel
> antrean akan memecah jumlahnya = bug baru. (Saya sempat menjanjikan ini ke owner, lalu **mencabutnya**
> setelah membaca widget-nya.)

**GEJALA (dilaporkan owner):** di menu **Run → tab Need Review** dan **Channel Setting → Runs → Need
Review** muncul 2 item (tenant ryan, channel *Mesin Viral (Test)*), **tapi di menu Need Review tersendiri
kosong**. Video kedua item ada di YouTube Studio tenant (privat) — keputusan tenant di YouTube di luar
kendali aplikasi, jadi item takkan pernah hilang.

**LIMA RANTAI — terverifikasi ke kode + DB live:**
| # | Mata | Temuan |
|---|---|---|
| 1 | **BACA DARI MANA** | `runs-table.tsx` & tab channel baca **`production_runs`**; halaman `/review` baca **`content_inventory`** (`page.tsx:105` `.eq("status","ready_with_issues")`). **Dua tabel berbeda** ⇒ itulah sebab isinya beda. |
| 2 | **PREDIKAT** | `runs-table.tsx:27` `statusKey()`: status memuat `qc_fail`/`ready_with_issues`/`issue` → label **"Perlu Ditinjau"**. Run kedua item = `qc_failed` ⇒ masuk. Di `/review` tak ada baris ⇒ kosong. |
| 3 | **SIAPA MEMBUAT** | `direct_jobs.job_type = **"test"`** (Test Channel), `publish_privacy=private` — **dibuktikan langsung dari tabel**, bukan ditebak. Jalur `run_direct` **jatuh terus** ke pipeline `publish=True`. **Test Channel TIDAK PERNAH membuat baris `content_inventory`** (diverifikasi: 0 baris) **dan tidak membuat baris `videos`** (diverifikasi: 0). Hanya `production_runs`. |
| 4 | **APA YANG MENUTUP** | **TIDAK ADA.** `buffer_janitor.sweep_stale` memadamkan `qc_failed → discarded` HANYA bila ada baris inventory ber-status `ready_with_issues`. Test Channel tak punya artefak apa pun di aplikasi ⇒ **secara struktur mustahil tertutup**. Bukan TTL terlewat. |
| 5 | **JALUR SAUDARA** | 4 jalur lewat `run_direct`: `test` (unggah privat) · `retry` (unggah privat) · `test_nopub` (Test Niche, **tanpa** unggah, inventory `status='test'`) · `admin_test`. **Cakupan nyata: 9 run `qc_failed` seluruh tenant — 8 di antaranya `job_type=test`**, 1 produksi terjadwal. Owner melihat 2 karena hanya membuka channel itu. |

**DUA HIPOTESIS SAYA YANG SUDAH DIGUGURKAN — JANGAN DIHIDUPKAN LAGI:**
1. ❌ *"Sembunyikan saja run uji yang sudah terunggah"* → menghapus satu-satunya jejak 2 video privat di
   Studio tenant **beserta catatan mutunya**; nol dari 4 cacat UX di bawah teratasi.
2. ❌ *"Penyapu terlewat untuk status `test`"* → **salah sasaran**: itu jalur Test **Niche**; Test
   **Channel** tak punya baris inventory sama sekali (mata 3).

**EMPAT CACAT UX yang TERUKUR (jalan buntu berlapis bagi tenant):**
1. Lencana **"Perlu Ditinjau"** ⇒ mengesankan aplikasi punya sesuatu, padahal peninjauannya di YouTube.
2. Laci run menampilkan **langkah pipeline**, BUKAN catatan QC (`runs-table.tsx` cabang `st === "failed"`
   saja). Yang disembunyikan justru nilainya: *"Durasi 35.2s di luar ±15% target 60s"* dan *"File terlalu
   kecil: 3.3MB < 5.0MB (render gagal?)"*.
3. `/runs/[id]` menampilkan tombol **"Tinjau" → `/review`** tanpa syarat ⇒ **jalan buntu** (halaman kosong
   untuk jalur ini). *(Adil: `runs-table` SUDAH benar — ia menampilkan tautan "tinjau di YouTube".)*
4. **Nol penutup** — keputusan tenant terjadi di YouTube; aplikasi takkan pernah tahu.

**DUA ITEM NYATA (bukti):** `direct-71680a68` 08-Jul (*Kisah Islami Anak-Anak*, durasi 35,2s vs target 60)
· `direct-1c5d4bcb` 14-Jul (*Ubahlah Hari Anda dengan Afirmasi Harian*, 3,3MB — render diduga gagal).
Keduanya **3–4 minggu** privat di Studio tenant.

**✅ PERTANYAAN ITU TERJAWAB SENDIRI OLEH RANCANGAN FINAL — jangan ditanyakan lagi ke owner.**
Pertanyaan lamanya: *"apakah hasil Test Channel harus hilang dari daftar setelah ditangani, atau tetap
tinggal sebagai riwayat?"* Premisnya **salah**: ia mengandaikan ada sesuatu yang "ditangani". Tidak ada —
nol bagian sistem menunggu jawaban tenant. Jadi hasil uji **TETAP tinggal sebagai riwayat**, hanya dengan
nama yang jujur ("Ada catatan QC"), dan **tak ada yang perlu ditutup**. Ketiga opsi (i)/(ii)/(iii) gugur
bersama premisnya.

Keempat cacat di atas: **1 · 2 · 3 SUDAH DIPERBAIKI** (label · catatan QC ditampilkan di laci · dua jalan
buntu ke halaman kosong ditutup). **4 ("nol penutup") GUGUR sebagai cacat** — tak ada yang perlu ditutup.

**AKAR yang masih terbuka, SENGAJA tak disentuh di sini:** 8 dari 9 catatan QC = **DURASI**, dan **20% dari
seluruh video uji yang berhasil dirender keluar dengan keluhan durasi**. Itu milik utas
`QC_CONTENT_ARCHITECTURE.md §2c` + **[D7]** — bukan menumpang pekerjaan ini. Label yang jujur membuat
masalah itu **terlihat apa adanya**, bukan menghilangkannya.

### [D8] 🔴🔴 JANJI HALAMAN HARGA vs KENYATAAN — 3 fitur DIJUAL tapi TIDAK ADA, 5 tak ber-gerbang — 2026-08-05
> **Ini menjawab pertanyaan owner "kenapa pelanggan tidak bertambah". Bukan bug — janji vs barang.**
> Diverifikasi ke KODE + DB + MIGRASI satu per satu (bukan dibaca dari dokumen).

**A. DIJUAL di paket Business (Rp 699K) tapi NOL implementasi:**
| Janji di `/pricing` | Bukti |
|---|---|
| **Webhook** | nol berkas menyebut `tenant_webhook`/`webhook_url` keluar di `src/` & `apps/web/src/` |
| **API access** | tak ada `/api/v1`; nol `tenant_api_key`/`api_token` |
| **Priority queue** | nol prioritas di `producer.py`/`publisher.py` — antrean tunggal |
⇒ **Business tidak bisa dijual jujur hari ini.** Menagih Rp 699K untuk tiga fitur yang tak ada = risiko
reputasi & hukum, bukan sekadar pemasaran.

**B. Ditulis "Pro-only" (Starter = ❌) tapi TIDAK ADA GERBANGNYA — tenant Starter mendapatkannya:**
`Quality Gate kustom` · `Compliance detail` · `Custom voice (ElevenLabs)` · `Captions style kustom` ·
`Hashtags kustom`.
**Bukti:** `plan_limits` hanya punya 4 kolom pembatas (`max_videos_per_day`, `max_channels`,
`full_niche_catalog`, `niche_studio`) — nol kolom untuk kelima fitur itu. Tenant menyimpan setelan channel
lewat **RLS UPDATE `channels`** yang WITH CHECK-nya hanya `tenant_id = auth.uid()` (migr 0029) — **nol
pemeriksaan tier**. Nol RPC ber-gerbang untuk kelimanya (yang ada hanya `set_channel_niche` &
`set_channel_publish_slots`).

**C. Matriks bertentangan dengan DB:** matriks menulis Starter *"Niche tersedia: 3"*, sedangkan migr 0124
menyetel `full_niche_catalog = true` untuk **starter/pro/business** ⇒ Starter sebenarnya dapat
**katalog penuh**. Salah satu dari keduanya salah, dan keduanya hidup.

**D. GABUNGAN dengan [D6] = sebab konversi:** Trial & Starter identik (1 video/hari, 1 channel), lima
fitur "Pro" bebas dipakai Starter, tiga fitur Business tak ada. ⇒ **hampir tak ada yang didapat tenant
berbayar yang tidak didapat tenant murah/gratis.** 5 aktif dari 17 pendaftar, dan 9 dari 10 masa-coba
habis tanpa pernah menerbitkan satu video (bukti [D6]).

**KEPUTUSAN OWNER (uang + arah produk, §2.3d — Claude TIDAK memutuskan):**
1. **Business:** (a) bangun 3 fitur itu · (b) **cabut dari matriks sampai ada** (paling cepat & jujur) ·
   (c) ganti dengan fitur yang sudah ada.
2. **Lima fitur "Pro-only":** (a) tegakkan gerbangnya (butuh 5 kolom `plan_limits` + guard) ·
   (b) pindahkan ke kolom Starter juga (jujur bahwa memang tersedia).
3. **Katalog niche:** samakan matriks dengan DB, atau sebaliknya.
**Nol baris kode boleh berubah sebelum ketok** — mengubahnya = mengubah apa yang dijual.

**DONE-BILA:** setiap baris di matriks `/pricing` punya bukti gerbang di kode/DB, atau tak lagi tertulis.

### [D7] ⏱️ TARGET durasi per-video belum terekam — audit presisi durasi historis MUSTAHIL — 🟠 2026-08-05
- **TEMUAN (diukur ke DB live):** `videos.duration_secs` merekam durasi AKTUAL, tapi **tak ada satu pun
  kolom/metadata yang merekam TARGET (preset) yang dituju video itu.** `run_metadata` hanya memuat
  `{ai_usage, cost, mode, scheduled, video_title}` — diperiksa langsung, bukan dibaca dari dokumen.
- **AKIBAT:** presisi durasi — gerbang PALING TERKUNCI menurut kompas owner (§7.3 *"durasi video = HULU
  pipeline"*) — **tak bisa diaudit secara historis.** `channels.duration_preset` adalah nilai SEKARANG;
  begitu owner menggesernya, seluruh video lama seolah menyimpang.
- **HAMPIR MEMBUAT SALAH LAPOR:** perbandingan pertama (preset sekarang vs 160 video lama RAD The
  Explorer) menunjukkan selisih **+15,9 detik** dan tampak seperti cacat produksi besar. Setelah
  dipersempit ke jendela di mana presetnya pasti, angka itu **artefak perbandingan**, bukan cacat.
  Selisih historis TIDAK diklaim sebagai bug — dan tak akan bisa diklaim sampai target ikut terekam.
- **SUDAH DIKERJAKAN (aman, satu baris):** durasi AKTUAL kini terekam juga di jalur terjadwal
  (sebelumnya 55 dari 75 video/14 hari berkolom kosong = 73%). Dijaga
  `tests/test_durasi_terekam_jalur_terjadwal.py`.
- **BUTUH KETOK OWNER:** merekam TARGET per-video = menambah kolom/metadata di jalur produksi (§2.3d).
  Pilihan: (a) tambah `target_seconds` ke metadata stok — paling murah, nol migrasi; (b) kolom baru di
  `videos`; (c) biarkan, terima bahwa audit durasi hanya berlaku maju (bukan historis).
- **DONE-BILA:** untuk video yang lahir SESUDAH keputusan, presisi durasi bisa diaudit tanpa bergantung
  pada nilai preset channel saat ini.

### [D6] ⚖️ KUOTA VIDEO PER PAKET — Trial & Starter IDENTIK (butuh ketok owner) — 🔴 2026-08-04
- **TEMUAN (terukur ke DB live + kode, bukan dokumen):** pada kenop HIDUP `plan_limits.max_videos_per_day`
  (admin-editable `/admin/pricing`, migr 0073), **Trial = 1 · Starter = 1 · Pro = 3 · Business = 5**
  video/hari/channel; `max_channels` Trial 1 · Starter 1 · Pro 3 · Business 10.
  ⇒ **Trial dan Starter IDENTIK dalam produksi.** Tenant membayar **Rp 149K** dan mendapat jumlah video
  yang SAMA dengan masa coba gratis. Yang bertambah hanya katalog niche penuh + boleh pesan niche kustom.
  **Dugaan kuat (belum dibuktikan sebab-akibat):** ini salah satu sebab 10 dari 17 tenant tidak lanjut.
- **KAPASITAS TERBUKTI:** puncak produksi yang PERNAH tercapai **34 video/hari** (16-Jun, seluruh tenant);
  rata-rata 3,6/hari selama 121 hari aktif. ⇒ ada ruang menaikkan kuota **tanpa** infra baru, tapi
  angka dokumen lama (Business 24/hari/channel × 10 channel = **240/hari**) **7× di luar** yang pernah terbukti.
- **BAHAYA yang nyaris terjadi 04-Agu:** `DESAIN_PRODUK_SAAS` memuat angka mati 5/10/24. Menyelaraskan
  kenop ke angka itu = beban render **5×**. Owner sendiri yang menahan (*"dokumen bisa basi, kalau
  dijadikan acuan tunggal bisa berantakan"*) — kekhawatiran itu TERBUKTI benar.
- **SUDAH DIKERJAKAN (aman, nol perubahan perilaku):** dokumen berhenti menanam angka mati → menunjuk
  kenopnya + mencatat nilai hidup 04-Agu + peringatan beban render + penanda "jangan pakai klaim 7,5×
  lebih murah" (klaim itu dihitung dari 150 video/bulan; pada kenop hidup ~30/bulan ⇒ ~3,7×).
  Dijaga `tests/test_desain_produk_tak_tanam_angka_mati.py` (5 uji, merah dibuktikan).
- **BUTUH KETOK OWNER (uang + arah produk, §2.3d — Claude TIDAK memutuskan):**
  (a) naikkan kuota Starter agar upgrade Trial→Starter terasa · (b) biarkan, jual nilai lain
  (katalog/niche kustom) · (c) sesuaikan harga. **Nol baris kode menunggu** — ini murni kenop admin.
- **DONE-BILA:** owner menggeser kenop di `/admin/pricing` (atau memutuskan (b)/(c)), lalu baris nilai
  hidup di `DESAIN_PRODUK_SAAS` §Struktur Paket diperbarui tanggalnya.

### [B10] UX AI-Catalog & Channel — audit terpadu (AUDIT_UX_AI_CATALOG.md) — 🟡 Fase 1-4 ✅ (2026-07-08) · sisa: konfirmasi visual owner
- **TUJUAN:** UI/UX area AI provider/model world-class utk tenant awam + admin (visi budget-aware + anti-bingung).
- **SPEC + status detail = `AUDIT_UX_AI_CATALOG.md`** (temuan ber-bukti file:baris + fase + realisasi). Arsitektur rantai AI = `ARSITEKTUR_AI_PROVIDER_MODEL.md` (referensi, wajib sync per-commit).
- **REALISASI:** ✅ **Fase 1 (2026-07-08)** — test/recover channel jelas (reuse TestNichePanel) + picker budget-aware + reaper + lifecycle kartu hasil; commits `f2defec`→`c9aea19`, disegel verifikasi 10-butir. ✅ **Fase 2-4 (2026-07-08, deployed `5055dbc`+`647f1c0`)** — form Katalog: label manusiawi dwibahasa+help/contoh (FIELD_META), duplikat-PK 409 kode `duplicate_key`, error INLINE dwibahasa (API kode→FE Bi); cari+saring tab Models; badge Integrasi "Tersimpan (belum diuji)"+tooltip; Uji model kunci-kosong→kunci Test Lab otomatis (divalidasi nyata); key_group datalist. Bug pra-deploy tertangkap sendiri di validasi final (nested-component → fokus input lepas) & diperbaiki sebelum rilis. Gerbang: tsc+build 0 err, localhost:3000, deploy per-batch setelah izin owner. Sisa: review visual owner.
- **DONE-BILA:** ✅ tercapai — menunggu konfirmasi visual owner (tandai final bila owner puas).

### [B11] Multi YouTube channel A-Z (tenant nyata: channel ke-2 ryan, akun Google sama) — 🟡 **KOREKSI STATUS 2026-07-18 (deep-dive ground-truth, teguran owner "progress tak di-update"):** Batch 1 ✅ · **2.1 analytics per-channel ✅ (13-Jul `f554e38`, LUPUT dicatat) · 3.1 kuota ✅ (migr 0155)** · **SISA NYATA: 3.2 invalid_grant ✅ DEPLOYED 18-Jul (`dd8fcdc`) · 2.2 viral-weights per-channel ⬜ (deep-dive lanjutan) · 2.3 6-field konten per-channel ⬜ (deep-dive lanjutan) · 3.3/3.4 ⬜**
- **TUJUAN:** tenant mudah & AMAN menambah channel YouTube tambahan + mengaktifkannya; data/analytics/otak per-channel tak bocor. Pemicu: owner buat channel YouTube ke-2 (akun Google sama) 2026-07-08; arsitektur multi-channel belum pernah diuji A-Z.
- **SPEC + audit lengkap + Plan-vs-Realisasi = `MULTI_YOUTUBE_CHANNEL_ARCHITECTURE.md`** (sumber kebenaran fitur ini; JANGAN audit ulang — semua bukti file:baris + DB live ada di §2).
- **KONTEKS singkat:** pondasi per-channel SUDAH benar (producer/publisher/gate/config — §2a doc). 5 gap kritis (§2b): G1 koneksi YT tanpa pagar human-error (tanpa nama/foto, tanpa unique, tanpa verifikasi token-vs-target) · G2 analytics penuh channel-2 nol (token channel-1, `channel==MINE`) · G3 viral_score_weights + 6 field konten per-tenant bocor antar channel · G4 Telegram buta channel · G5 invalid_grant senyap. Kalibrasi jujur: sistem TIDAK rusak hari ini; gap menggigit saat channel ke-2 aktif.
- **PLAN (disetujui owner 2026-07-08):** Batch 1 = pagar 3 lapis + koneksi "berwajah" (nama+foto) + picker galeri + Telegram per-channel (§3 doc) → uji A-Z acceptance §5 bareng owner. Batch 2 = analytics+otak per-channel (G2/G3). Batch 3 = hardening (kuota DB, invalid_grant, dashboard per-channel).
- **DONE-BILA:** acceptance §5 doc lulus — owner connect channel tambahan (konfirmasi visual nama benar), aktifkan channel-2, 1 video terbit ke channel YANG BENAR, Telegram sebut nama channel; Batch 2: analytics per-channel terisi terpisah.
- **DEPENDS:** — (mandiri). **Nyambung:** [A4]/[A5] (verifikasi Google & smoke-test memakai alur connect yang sama) · `CHANNEL_LOCK_ACTIVATION_PLAN.md` (pool) · `PER_CHANNEL_OAUTH_MIGRATION.md` (historis, gap §7-nya diserap ke sini).
- **REALISASI:** 🟡 audit + desain + doc ✅ 2026-07-08 · **Batch 1 ✅ DEPLOYED + LIVE 2026-07-08** (`382afdf`; migr 0146; insiden "No topics" 5× → 3 akar fixed `f07d44c`+`7fe489e`; 1 video terbit ke channel-2 benar) · **4 cacat FE picker ✅ `d0e0575`**.
  - **✅ 2.1 ANALYTICS PER-CHANNEL — SELESAI 2026-07-13 (`f554e38`+`ee9bc01`; koreksi tracker 18-Jul: dikerjakan dalam remediasi [B16] tapi LUPUT dicerminkan ke sini — kelalaian administrasi Claude).** Ground-truth DB live 18-Jul: `channel_insights` terpisah (RAD 155/MVT 22) · `videos.channel_id` terisi (303/11) · fetch per-channel dgn koneksi masing2. Kedua channel ryan belajar TERISOLASI — celah G2 sudah TIDAK menggigit.
  - **✅ 3.1 KUOTA max_channels — SELESAI (migr 0155 tier_enforcement + RLS `channels_tenant_insert`).**
  - **⬜ SISA NYATA — VONIS FINAL pasca deep-dive+review 5 dokumen (18-Jul; detail = progress_journal 18-Jul(3)):**
    - **3.2 invalid_grant = ✅ SELESAI + DEPLOYED PRODUKSI 2026-07-18 12:07 (`dd8fcdc`, izin owner "deploy BE"; skrip resmi OK health=200 mv-worker/webhook active)** (ketok "izin mulai kerjakan" + "rem segera, jangan bakar duit"). Koneksi YouTube putus kini GAGAL JUJUR: tangkap `invalid_grant` di 2 titik refresh (`youtube_publisher._get_credentials` + `channel_analytics._load_credentials`) → helper `mark_youtube_account_invalid` (idempoten, notif tenant SEKALI) set `status='invalid'` → gerbang DB `channel_missing` menutup → **produksi channel berhenti SEKETIKA** (rem, hemat biaya) + publish menahan video (bukan "akan diulang" menyesatkan) + badge invalid FE. Menempel [B22] `AUTH_INVALID` (masuk FAST_FAIL). RefreshError non-invalid_grant = transien (tak ditandai — anti asumsi liar). Pulih otomatis saat reconnect. Bukti: uji **`tests/test_youtube_auth_invalid.py` 10/10** + py_compile/import worker bersih. **Sisa: izin DEPLOY owner** (BE only — FE `/integrations` badge invalid sudah ada). Deep-dive 5 permukaan + rekonsiliasi doc di commit yang sama = TUNTAS.
    - **2.2 viral_score_weights per-channel = ✅ VONIS FINAL 18-Jul: PREMIS GUGUR → DILEBUR ke B17 §6 (ketok K1–K6).** Bukti empiris: fitur `topic_scores` hampa informasi (korelasi \|r\|≤0,24 vs hasil nyata, n=130) → per-channel-isasi sia-sia; digantikan arsitektur "Mesin Cerdas 3-Lapis" (kurva retensi per-momen → analis+buku keputusan → warisan). Sumber kebenaran = `PROGRAM_BUKTI_KECERDASAN.md` §6. Item 2.2 bentuk lama JANGAN dikerjakan.
    - **peak_region per-channel = BELUM SIAP** — terikat trend radar tanpa region 'id' (`RISET_NICHE:201`); owner dulu TUNDA ke "Phase 6". Butuh rekonsiliasi trend dulu.
    - **2.3 lain (tts_voice_settings dll) = BUKAN BUG** — tts_voice_settings=EKSPRESI VOKAL per-niche by-design (NICHE_DNA §1.5, ketok owner 16-Jul). Jangan sentuh.
    - **3.3 = sebagian besar SUDAH JADI** (tab per-channel Runs/Insights live); sisa kecil = kolom nama-channel di daftar Runs gabungan (belum diverifikasi). Bukan bug.

---

# ⏳ KELOMPOK C — DATA-GATED *(mekanisme SIAP; matang seiring data pasca-cutover — bukan "koding besar")*

### [B12] Sapu-bersih temuan audit 2026-07-11 (3 kelemahan kelas-skala) — ✅ TUNTAS (keputusan owner "jangan biarkan bug")
- **3 temuan dibereskan 1 batch:** (1) tiebreaker `id` paginasi email recap (urutan total deterministik) · (2) "Video terbit" /channels → count-exact per-channel (kebal cap 1000; validasi MVT=5 RAD=202 Σ=207 identik metode lama) · (3) kartu "Biaya AI 30 hari" dashboard → paginasi berurutan stabil (cap 8k run/30hr). Semua pre-existing/kosmetik — hari itu belum ada angka salah yang tampil ke tenant mana pun.
- **REALISASI:** ✅ deployed 2026-07-11 (lihat commit "sapu-bersih audit"); recap tetap 207/42.363 ground-truth; tsc+build 0 err. **Pasca-batch ini: NOL temuan diketahui tersisa → FREEZE KODE berlaku** (kode hanya disentuh bila memblok/menipu tenant berbayar atau permintaan Google).
- **[B13] fix realtime kartu F2:** ✅ **TUTUP 2026-07-11** — deployed 01:36 (`f9a7f2e`, mv-web active, situs 200; izin eksplisit owner). Verifikasi visual formal di-CLOSE keputusan owner 2026-07-11 sore ("sudah bisa di-close sambil kita lihat lagi kedepannya") — dipantau berjalan; ada anomali → lapor, rollback 1 perintah tetap siap.

### [B16] PULIHKAN SINYAL RETENSI self-learning — ✅ TUNTAS TOTAL 2026-07-13 (dua akar: scopes 11-Jul + AKAR SEJATI per-channel 13-Jul `f554e38` deployed; lihat changelog 2026-07-13 (3))
- **⚠️ RALAT ANALISA (2026-07-11, dua iterasi):** dugaan awal "consent tak dicentang → owner reconnect" = **SALAH**. Probe API nyata membuktikan **kedua token ryan PUNYA izin analytics penuh** (RAD: 1.206 views/ret 63,88% · MVT: ret 96,81% — API menjawab data). Reconnect = sia-sia.
- **AKAR SEJATI (verified kode+DB+probe):** tabel pool `tenant_youtube_accounts` **TIDAK PUNYA kolom `scopes`** → loader `tenant_credentials.py:31` `r.get("scopes") or []` senyap mengembalikan KOSONG (pola fallback-senyap terlarang) → gerbang scope kolektor `channel_analytics._init_clients:111` mematikan Analytics API **utk SEMUA koneksi/tenant sejak migrasi pool 24 Jun**, sambil menyalahkan tenant di log.
- **DAMPAK:** retensi/watch-time/subscriber-gain=0 semua snapshot baru → widget Content-types 0, kolom retensi 0%, avoid_patterns skip, bobot niche fallback views — self-learning setengah buta 2+ minggu, termasuk kumala (pro, berbayar). Data di sisi YouTube UTUH (tinggal dijemput).
- **PLAN (kode kecil, nol aksi tenant):** (1) migr 0149 kolom `scopes` (text[]) di pool; (2) callback OAuth simpan scope granted dari respons Google (selama ini dibuang); (3) backfill 3 koneksi eksisting via probe API (ryan×2 terbukti; kumala probe saat terap); (4) loader & kolektor TAK berubah (otomatis benar begitu kolom terisi). Lalu rotasi harian menjemput ulang retensi (delay 48j/video normal).
- **DONE-BILA:** snapshot baru `has_full_analytics=true` + log berhenti warning + retensi terisi bertahap → widget Content-types/retensi/avoid_patterns hidup utk ryan & kumala.
- **REALISASI:** ✅ **TUNTAS+DEPLOYED+VERIFIED 2026-07-11 (ketok owner "kerjakan sampai deploy"):** migr **0149** applied (kolom `scopes` + comment) · `_store_tokens` simpan granted scopes (komentar sejarah diluruskan) · **backfill 3/3 koneksi via probe API — SEMUA LULUS analytics (incl. kumala)** · loader produksi mengembalikan 3 scopes ✓ · deploy BE `b3e528c` OK · **bukti hidup: log "Analytics API v2 siap (full metrics)" (pertama sejak 24 Jun) + sync nyata 48 video ter-update 0 error + snapshot baru ber-retensi nyata (95,5% · 92,9% · 87,9%…) & subscriber_gain & watch_time, `has_full_analytics=true`**. Kekayaan penuh insight (content-types/avoid_patterns) terisi bertahap seiring rotasi harian menyapu 199 video. Catatan proses: 1 salah-panggil di UJI saya terdeteksi & dikoreksi — bukan bug produk. **ADDENDUM (sesi sama): temuan lanjutan owner ('layar tak berubah') membongkar cacat ke-2 kelas sama — ROTASI kolektor berputar di tempat** (peta kesegaran `fetched_at` dibaca tanpa paginasi/order → cap 1000 korupkan peta → 98/205 video kelaparan permanen, terukur 15 run). Fix `ee9bc01` (paginasi+order first-seen) → konvergen [50,7] ✓ → sensus 205 video segar, 150 ber-retensi → otak dihitung ulang → **widget LIVE: Content types 0→5 (history 100%, facts 77,9%, listicle 74,2%, question 70,7%, mystery 62,9%) + kolom retensi hooks hidup (42,4%…)**.

### [B14] QC deteksi-wajah utk niche ber-larangan figur (lanjutan guardrail syariah P4a) — ⬜ DORMAN
- **KONTEKS:** insiden 2026-07-11 (visual menyerupai Nabi ﷺ di niche islami). DNA kini larangan mutlak (`strict_prohibition`) — tapi model gambar BISA melanggar prompt; belum ada lapisan QC yang menolak otomatis.
- **PLAN:** QC pra-publish deteksi wajah (mis. cv2/face-detect ringan) HANYA utk niche ber-flag larangan → gagal jujur, bukan terbit.
- **PEMICU KERJAKAN:** SEBELUM niche islami (atau niche ber-larangan lain) ditawarkan/dipakai tenant mana pun.
- **REALISASI:** ⬜

### [B15] Video terhapus/di-private di YouTube → otomatis KELUAR dari pembelajaran — ✅ TUNTAS + DEPLOYED 2026-07-14 19:13 (batch B6; izin owner "silahkan deploy"; skrip resmi OK health=200 commit 2a15df1; lokal teruji 8/8)
- **KONTEKS:** insiden 2026-07-11 — owner hapus konten di YouTube tapi sistem tetap belajar dari analitik lamanya (tak ada sinkronisasi status).
- **REALISASI 2026-07-14 (ketok owner; kertas-keputusan → rencana matang → uji):** migr **0160** status
  `delisted` (constraint lama chk_video_status ganda tertangkap verifikasi → disatukan) · sapu analytics
  menandai OTOMATIS hanya pada jawaban PASTI YouTube (not-found/private; error jaringan TIDAK menandai)
  · analyzer memfilter snapshot delisted (konsumen lain otomatis via status='published') · reversible.
  Bukti 8/8 pada 3 video hantu nyata: delisted ✓, video sehat utuh ✓, keluar antrean sapu ✓, insight
  203→202 ✓, kurva utuh 16 mgg ✓. Commit + deploy: ✅ 2026-07-14 19:13 batch B6 (commit `2a15df1`, skrip resmi OK health=200) — selaras header item. *(Baris "menunggu izin owner" lama = basi; dikoreksi 2026-07-16 sapu status total.)*
- **PLAN & PEMICU (arsip pra-eksekusi):** kolektor analytics menandai video yang tak lagi ditemukan API (deleted/private) → analyzer/optimizer eksklusi — SUDAH terealisasi di blok REALISASI di atas.

### [B17] PROGRAM BUKTI KECERDASAN — real self-learning terukur→terasa→terjual — 🟡 F0 ✅ DEPLOYED · **⭐ 18-Jul: §6 "MESIN CERDAS 3-LAPIS" DIKETOK PENUH (K1–K6) — fase aktif berikutnya = M1**
- **SPEC + tracker = `PROGRAM_BUKTI_KECERDASAN.md`** (alasan + arsitektur di atas fondasi terverifikasi 07-11 + hasil per-fase + gerbang + risiko). **⭐ EVOLUSI DIKETOK 2026-07-18 = §6 dokumen itu (WAJIB baca sebelum menyentuh kecerdasan):** Lapis 1 MATA (kurva retensi per-momen — probe API sukses, scope sudah ada) → Lapis 2 OTAK ANALIS + BUKU KEPUTUSAN (mode bayangan 2 mgg dulu; BYOK) → Lapis 3 WARISAN (dari vonis, benih RAD, K6 label keyakinan-rendah). §6 menyerap F1.1/F2/F3 lama (🔀 di tracker §5) + mengoreksi B11-2.2 (premis gugur). Fase: **M1 kolektor kurva → M2 dua-sinyal loop → A1 analis bayangan → A2 live+hakim → W1 warisan** — tiap fase lewat ritual §2c.6 (PEMAHAMAN SAYA → konfirmasi owner). Urutan hukum lama tetap utk yang TIDAK dilebur: **G1 kurva sehat ≥3 mgg → F1.2 laporan mingguan email**.
- **Keyakinan jujur:** F0 = 100% tanpa syarat; fase lanjut terkunci gerbang data — bukan janji buta.
- **REALISASI:** 🟡 **F0 ✅ TUNTAS+DEPLOYED 2026-07-11 (`3c1fd76` + migr 0150; izin eksplisit owner terapkan+deploy):** RPC `get_channel_learning_curve` (kohort minggu-publish; retensi bacaan-valid-terakhir ≤100; views ber-jendela 7-hari anti bias-umur) + kartu `LearningCurveCard` dua-skop (/channels/[id] Wawasan + /insights) + garis penanda 11-Jul + chip delta dashboard + 3 knob `app_config` ber-label admin. Bukti: SQL vs ground-truth Python IDENTIK 100% (RAD 15 mgg · MVT empty-state · gabungan) · uji live sbg tenant (isolasi ✓, anon ditolak ✓) · deploy OK situs 200 · bundle live terverifikasi. Detail = tracker §5 dokumen program. **G1 dievaluasi saat kurva pasca-11-Jul ≥3 minggu; sekarang fokus panduan tenant [D1]-F0.**

### [C1] Closed-loop kalibrasi durasi — 🟡 AKTIF (PROGRAM DURASI 5-FASE, mandat owner 2026-07-16 "tuntas 100% no turn-back")
- **TUJUAN:** durasi presisi PERMANEN — estimator terukur (F1) → kalibrasi dari data nyata (F2) → prompt+toleransi 1-sumber (F3) → jalur khusus DNA (radiant 1-kalimat + ai_video diskrit) (F4) → swa-kalibrasi+alarm (F5, superset plan EWMA/F5-01 lama).
- **ROOT-CAUSE (data 110 render, 2026-07-15):** 85% video keluar PENDEK; biang = taksiran pace salah per (voice×gaya-DNA-niche) — voice sama beda niche pace nyata beda 25% (Ardi: legenda 2.53 vs radiant 2.00). Niche dgn pace kebetulan pas (dark_history) = 86% tepat → kalibrasi = kunci. `delivery_wps` provider global SUDAH akurat <1% (jangan diutak-atik). `voice_catalog.delivery_wps` mayoritas NULL.
- **REALISASI:**
  - ✅ **F1 INSTRUMEN — DEPLOYED 2026-07-16** (`fe83d28`, migr 0162 applied+verified): +5 kolom nullable `tts_delivery_samples` (`predicted_secs`/`raw_audio_secs` pra-atempo/`target_secs`/`pause_secs`/`pause_counts`); `_log_delivery_sample` rekam taksiran-vs-aktual; durasi mentah diukur 1× & dipakai-ulang `_fit_duration` → **NOL ffprobe/waktu tambahan** (uji 5/5). Insiden dihindari: file koneksi berisi 2 URI, URI v1 nyaris terpakai → kini guard identitas DB sebelum tulis. ⛔[dicabut 31-Jul → §2c]
  - ✅ **BACKFILL MINING LOG — 2026-07-16** (izin eksplisit owner): worker.log (16-Jun→16-Jul) ditambang → **78/112 baris lama terisi** (73 dgn taksiran; 0 ambigu; 34 pra-era-log jujur dilewati); kolom lama TERBUKTI utuh (md5 identik). Error taksiran per-niche kini terukur: ocean 3% · dark 6% · legenda ~10% · radiant ~12% · **fun_facts ~20%**.
  - ✅ **DURASI-3 KOREKTOR — DEPLOYED 2026-07-16** (`a4ea83e`, deploy_be OK health=200): STEP 5 atempo dulu pakai env trailing 1.5 umum ≠ 3 titik lain (`effective_trailing` per-preset) → 8s: naskah 7.0s dipaksa atempo ke 6.5s (suara dipercepat percuma, final ~7.6s). Kini SATU rumus; uji 3/3 (kasus-8s-nyata tanpa-atempo · meleset-parah tetap gagal-jujur · tanpa-param = jalur lama persis). ⛔[dicabut 31-Jul → §2c]
  - ✅ **F2 KALIBRASI — DEPLOYED 2026-07-16** (`4fee742`, deploy_be OK health=200; izin eksplisit owner; opsi A diputuskan Claude atas delegasi owner): migr 0163 `tts_pace_calibration` + 0164 `tts_speed_response` (applied; kalibrasi perdana: α edge=1.02/EL=**1.324** [EL melebih-lebihkan speed, R²=0.80] + 10 sel pace voice×niche); modul `pace_calibration.py` (pagar: min-sampel env, pace_locked skip+hapus, nilai liar DITOLAK); jalur-baca `tenant_config._load_pace_calibration` (niche efektif semantik s85) → `script_engine` lapis terkalibrasi + solver/estimator sadar-α (default 1.0 = lama persis). **BUKTI replay LOO 73 render: error 9.3%→4.7%, dalam-±10% 54%→74%, SEMUA 8 niche membaik** (fun_facts 20.5→5.1). ✅ **F3 PROMPT+TOLERANSI-1-SUMBER — DEPLOYED 2026-07-16** (`916e72f`, deploy_be OK health=200): `_script_len_tol()` satu-sumber (env `SCRIPT_LENGTH_TOLERANCE` hidup dari config-mati, pagar `min(·,QC_TOL)`; 6 angka terpatri + fosil `_Tlo/_Thi` dibuang) · BEAT PLAN otoritas tunggal (target+**MIN anti-kependekan**+MAX per-beat; swa-verifikasi `_beat_words`) · prompt seragam EN (hardcode 14-kata/kalimat dibuang) · feedback retry ground-truth per-beat ("OFF-BUDGET BEATS"). Uji: 3 preset + toleransi + grep-nol-terpatri. Bukti runtime = otomatis via timbangan F1. ✅ **F4 OVERHEAD-PENUH + DNA — DEPLOYED 2026-07-16** (`7dd42cd` health=200): ranjau overhead-loop mati (`effective_overhead` = trailing efektif + loop bersih, SATU rumus 4 titik — dulu korektor/gerbang trailing-saja → regang audio benar, 8s ±12%); DNA radiant style diharmonisasi ke anggaran F3 (config, guard hanya `style`, reversibel); klip-diskrit = fakta harga (bahan keputusan model [B6]). ✅ **F5 SWA-PEMELIHARAAN — DEPLOYED 2026-07-16** (`7dd42cd` health=200) (migr 0165 `beat_words`+`weight_locked`; `run_maintenance` di self_learning cadence: kalibrasi pace+α otomatis · bobot-beat dinamis-terbatas [±20%/siklus, min-n 10, lock dihormati, ground-truth sistem] · alarm drift Telegram admin [ambang 10%, anti-palsu]; alarm NYATA berbunyi 12.5% saat uji = taksiran era pra-kalibrasi, ekspektasi <10% pasca-deploy). Form admin bobot-beat ✅ **DEPLOYED FE 2026-07-16** (`f6950a6` situs 200 + teks diperjelas pasca-teguran owner [legenda abu-abu · 'Kunci angka' · analogi pelatih]; Catalog>Durasi seksi 'Bobot antar-adegan': bobot auto-save ber-pagar server 1–30 · kunci 🔒 weight_locked · pratinjau % porsi per-preset rumus persis _distribute_words · panduan dwibahasa; guard hook API dipersempit ke kolom motion — bobot hook kini bisa diatur; build Next lulus)
- **DONE-BILA:** akurasi durasi per-niche ≥ patokan dark_history (86% dalam ±15%) DIBUKTIKAN dari render nyata pasca-kalibrasi; alarm drift hidup.

### [B18] Ekspansi katalog fal.ai (TTS·image·video satu kunci) — 🟡 TAHAP-1 LIVE 2026-07-16
- **KONTEKS:** owner ingin fal sbg agregator media (tenant hemat kunci: 4→2). Riset verified: fal = media generatif (image/video/TTS termasuk endpoint ElevenLabs $0.05/1k char) TAPI **BUKAN LLM** (tenant tetap butuh 1 kunci LLM terpisah).
- **REALISASI Tahap-1 (mandat owner "kerjakan 1+2", commit `01be29c` DEPLOYED):** (1) VIDEO nol-kode: Seedance 1.0 Pro ($0.1215/s 1080p) + Lite ($0.0486/s — 8s≈$0.39, termurah; durasi FLEKSIBEL 2-12s = bayar pas, tak dipaksa klip 10s spt Kling/Hailuo) — skema OpenAPI + API-harga fal diverifikasi mesin, rumus dicek-silang halaman. (2) IMAGE: transport `ai_image._generate_fal` (pola queue ai_video teruji; FLUX tanpa kanal negative → prompt murni; seed §9.1) + FLUX schnell ($0.009/gbr 1080×1920) & dev ($0.075) — **BUKTI runtime: 1 gambar nyata OK 353KB 9:16**. Ke-4 model `is_active=FALSE` → menunggu owner Test di admin lalu aktifkan.
- **~~⬜ Tahap-2 (riset dulu)~~ → ✅ SUDAH DIBANGUN & LULUS 2026-07-28** (`3421a1a`+`0a0c2b9`): word-timestamps fal TERBUKTI (per-karakter → per-kata, karaoke setara ElevenLabs langsung) · `speed` didukung (`tts_profiles.fal.param_schema`) · 12 suara. Catatan "riset dulu" di atas **BASI 19 hari** — itu sebabnya sesi-sesi berikutnya mengira pekerjaan ini belum ada.
- **⚠️ KONTEKS DI ATAS SALAH SEJAK 28-Jul:** "fal BUKAN LLM" tidak lagi benar — fal menyediakan naskah lewat kunci yang sama.
- **🔧 Tahap-3 — 3 BUG NASKAH DIPERBAIKI + HARGA OTOMATIS (2026-08-16, mandat owner "aktifkan model fal yang belum aktif"):**
  Ketiganya lolos berbulan-bulan karena modelnya nonaktif sejak lahir; ditemukan sebelum menyala, bukan sesudah.
  1. **ALAMAT (fatal).** Migrasi 0180 menyatukan 3 baris penyedia fal (koreksi yang benar), tapi `ai_providers.base_url` fal = alamat ANTREAN jalur VISUAL → jalur naskah memungutnya → **HTTP 404 di panggilan pertama**, terbukti. Alamat protokol kini milik ADAPTER (pola yang sudah dipakai adaptor suara fal & ElevenLabs). **Sekaligus pindah dari endpoint `fal-ai/any-llm` yang DIPENSIUNKAN vendornya** ("This endpoint is deprecated", dokumen resmi fal dibaca 16-Agu) ke alamat yang masih didukung — yang juga MELAPORKAN token, syarat mutlak agar tabel harga otomatis punya angka untuk dikalikan.
  2. **BIAYA TAK TERCATAT.** `cost_meter.add_llm` dipanggil adapter Anthropic & OpenAI tapi TIDAK di adapter fal → naskah fal terbaca Rp 0 oleh seluruh sistem tagihan, rem pelindung uang tenant buta. Ditambahkan dgn pola yang sama persis + penjaga generik: **setiap** adapter naskah wajib mencatat, jadi vendor berikutnya tertangkap merah bila lupa.
  3. **GALAT TAK BERGOLONGAN.** fal membalas HTTP 200 dengan field `error` terisi; jalur itu melempar tanpa golongan → UNKNOWN = boleh-diulang. Akibat nyata bila saldo tenant habis: **3 produksi terbuang** sebelum channel direm, tenant tak pernah tahu harus mengisi saldo. Kini digolongkan lewat penilai yang SATU itu juga (`QUOTA_EXHAUSTED` ∈ FAST_FAIL → rem setelah 1 kegagalan).
  4. **HARGA OTOMATIS.** Sumber harga cadangan naskah dipetakan **by suffix** (kata penjelasan fungsinya sendiri) tapi dicari dengan penanda UTUH → model berawalan vendor (seluruh naskah fal) tak pernah ketemu. Satu baris diselaraskan ⇒ **12/12 model fal punya harga di tabel**, 3 model naskah kini `source=openrouter` (per-token, terbarui otomatis harian), 9 sisanya harga manual yang sinkron TIDAK sentuh (dilaporkan jujur sbg tanpa-sumber). Harga otomatis dicek-silang thd tagihan NYATA fal: **3/3 cocok sampai digit terakhir**.
- **BUKTI (16-Agu, jalur produksi, bukan skrip terpisah):** alamat `fal.run/openrouter/router` · 3 model naskah menjawab JSON lengkap · meter mencatat token & panggilan · `compute_cost_usd` = $0,000578 dgn **nol model tanpa harga** · 12/12 suara fal hidup + penanda waktu benar · **5/5 model LULUS tombol Uji model admin** (stempel audit tertulis di katalog) · **1.123 uji hijau** (+12 penjaga baru, ke-7 penjaga dibuktikan MERAH dulu).
- **✅ TERPASANG & AKTIF 16-Agu** (`d2dd344`, BE+FE `OK`): 12/12 model fal menyala + mesin suara fal. Dibuktikan dari SISI TENANT (kunci publik, RLS): 3 penulis naskah tampil berikut harganya · mesin suara "fal.ai (ElevenLabs)" muncul · 2 model suara · 12 suara terpilih. Dijalankan DARI SERVER: alamat `fal.run/openrouter/router` · naskah jadi · meter mencatat 44/30 token · biaya $0,000088 tanpa model tanpa-harga.
- **🔧 TEMUAN SUSULAN — tombol "Uji model" MEMBUANG hasil yang sudah dibayar (owner, 16-Agu):** layar memvonis *"respons tidak valid"* pada MiniMax Hailuo 02, seolah modelnya rusak. Log server membuktikan sebaliknya: `17:59:07` mulai → `18:00:37` **klip 5,9s (0,9MB) JADI** → `200 OK`. Mesin berhasil dan vendor MENAGIH (±Rp 4.000); yang putus SAMBUNGANNYA — uji makan **90 detik**, melewati batas tunggu jalur perantara, balasannya bukan JSON lagi. Kelasnya bukan "video lambat" melainkan **menunggu di tempat untuk pekerjaan panjang**; menaikkan batas hanya memindahkan garis putus. **Perbaikan memakai pola yang SUDAH ADA** (titip lalu tanya berkala, spt tombol Pratinjau 1 gambar): hasil uji memang sudah tersimpan permanen di `ai_models.cost_hint.audit`, jadi saat sambungan putus layar MENUNGGU jejak itu berubah. Stempel audit kini menyertakan JAM (bertanggal saja ⇒ uji ulang di hari sama menghasilkan catatan identik ⇒ penantian menggantung), plus penanda `SEDANG DIUJI` sebelum vendor dipanggil. 4 penjaga baru, **dibuktikan MERAH dulu**.
- **✅ VIDEO UTUH — syarat 28-Jul AKHIRNYA DITUTUP (16-Agu).** Migrasi 0179 mensyaratkan *"diaktifkan hanya setelah terbukti lewat uji rantai penuh sampai video jadi"*; pembuktian 28-Jul berhenti di subtitle, dan **19 hari tak ada yang kembali**. Kini dijalankan lewat jalur RESMI (job `test_nopub` dari Niche Studio, dikerjakan worker server — bukan skrip lokal): channel *Mesin Viral (Test)*, niche `radiant_affirmations`.
  **Hasil: `success` · QC lulus · skor viral 81,1 · video 22,08 dtk / 10 MB (privat, tak terbit) · 201 dtk proses.**
  Model: naskah **Gemini 2.5 Flash (via fal)** · suara **ElevenLabs Turbo v2.5 (via fal), suara Luna (ID)** · gambar **Cloudflare FLUX schnell — SENGAJA bukan fal** (jalur visual fal sudah terbukti sampai video jadi 14–15 Jul; menggantinya hanya menambah biaya tanpa membuktikan hal baru).
  **Rantai biaya UTUH — inti perbaikan hari ini:** naskah 5 panggilan / 8.383 token masuk / 2.795 keluar ⇒ $0,009502 · suara 295 karakter ⇒ $0,014750 · **total $0,024252 dengan NOL model tanpa-harga**. Sebelum perbaikan, seluruh baris naskah itu terbaca **Rp 0** dan rem pelindung uang tenant buta terhadapnya.
  Setelan channel uji **TETAP memakai fal** (ketok owner 16-Agu); channel `is_active=false` sehingga tak menghasilkan jadwal otomatis.
- **DONE-BILA:** ✅ SELURUHNYA TERPENUHI — [B18] DITUTUP.

### [B19] Suara ElevenLabs BAHASA INDONESIA — ✅ LIVE 2026-07-16 (nol kode, nol deploy)
- **GUGATAN owner:** katalog cuma 2 suara ID (Ardi/Gadis, edge gratisan) padahal EL punya banyak — mayoritas tenant Indonesia. BENAR: kesenjangan kurasi (EL key era seeding lapse), bukan arsitektur.
- **REALISASI:** kunci EL ryan di-upgrade izin owner (read+write; sebelumnya TTS-only — akar "401" yang sempat salah kuvonis expired) → kurasi dari API resmi Voice Library `language=id` (30+ suara; dipilih 8 narasi/edukasi, semua `free_users_allowed` + preview): Luna·Aluna·Arunika·Dila (♀) + Bambang·Andi·Senja·Menit (♂) → `voice_catalog` (locale id-ID, preview ▶ di admin) → **owner dengar & AKTIFKAN SEMUA**.
- **TEMUAN penting (koreksi klaimku):** suara Voice Library kini bisa dipakai TTS **LANGSUNG TANPA add-to-account** (uji nyata: synth pra-add ✅ 12KB audio; add via API juga ✅ bila kelak perlu) → wiring auto-add yang direncanakan = **TIDAK DIBUTUHKAN**; nol gesekan tenant sejak hari ini. Model: 4 model EL katalog semuanya multibahasa (multilingual_v2 teruji ID).
- **Efek samping uji:** voice "Luna (ID)" tertambah di akun EL ryan (harmless; boleh dihapus manual). Tempo 8 suara baru → swa-kalibrasi F1/F5 otomatis dari render nyata.
- **DONE-BILA:** ✅ tercapai (aktif semua + rantai TTS terbukti). Lanjutan opsional: kurasi halaman-2 library bila tenant minta variasi.

### [B20] "Hubungkan Telegram" 1-KLIK — ✅ TUNTAS + DEPLOYED 2026-07-16 (`9129007` BE+FE OK; bukti linker hidup di log: start + drain 1 update basi tanpa tindak)
- **KELUHAN owner:** tenant kesulitan menemukan chat-ID Telegram. **SOLUSI:** tombol "Hubungkan Telegram" di /integrations → t.me deep-link ber-token → tenant tekan START → chat_id tercatat OTOMATIS + balasan bot dwibahasa + badge "Terhubung" (FE poll 3s×40). Manual = jalur cadangan (details).
- **Teknis:** token HMAC stateless (nol migrasi; kunci=sha256(SUPABASE_KEY|tg-link); 56 char ≤64 t.me; TTL env `TELEGRAM_LINK_TTL_MIN` 15m) · endpoint vault `/api/credentials/telegram/link` (pola telegram/test) + route authed FE · listener `telegram_linker` thread worker (long-poll; webhook bot diverifikasi KOSONG; offset persisten `app_config ops_tg_update_offset`; init-drain anti-token-basi; 5 cabang balasan dwibahasa; fail-soft). Artikel `notifikasi-telegram` ID+EN tersinkron (live). Uji: token 4 kasus + linker 6 cabang + build.
- **Keamanan (didokumentasi):** token hanya terbit dlm sesi login, TTL pendek, konfirmasi dua sisi; pemegang link dlm TTL bisa mengikat chat-nya → risiko diterima owner via desain ini.
- **✅ Bukti mata-kepala LULUS (owner, 2026-07-16):** klik tombol → START → "sukses terhubung" — rantai FE→vault→t.me→linker→DB→balasan TERBUKTI end-to-end di produksi. **ITEM DITUTUP.**

### [B21] PROGRAM AGEN & AFILIASI (partner B2B, bagi hasil selamanya) — 🟢 **F1–F4 + AUDIT A–Z ✅ SEMUA LIVE PRODUKSI 2026-07-17** (batch audit 18:30 `3172088`; SPEC §9b: 4 fix teruji incl. kritikal refund-approve) · **sisa NON-TEKNIS owner:** F0 (angka default + konsultan pajak/hukum) + bukti klik-layar + agen nyata pertama terbayar (=DONE-BILA tutup) · **➕ 19-Jul (SPEC §9a): ✅ SEMUA LIVE PRODUKSI 23:28 (`a124857`)** — tenant-hantu (migr 0173 applied + baris hantu terhapus) · anti-komisi-diri (uji 5/5) · Google login agen (bukti layar produksi) · pagar email-PIC · **MGM tenant⇄reseller SATU login (§9a.5) + link nav Portal Reseller gated** — sisa jujur: bukti klik-layar saat tenant nyata pertama ditautkan reseller
- **SPEC + tracker = `AGENT_AND_AFILIATION_ARCITECTURE.md`** (single source of truth, mandat owner 2026-07-17 — ringkasan awam + keputusan FINAL + arsitektur A–Z + rencana kerja F0–F4 urut prioritas; JANGAN riset/tanya ulang keputusan §1–§2 dokumen itu).
- **INTI:** kami developer tanpa tim marketing → AGEN (perusahaan mitra) investasi iklan+rekrut RESELLER; tenant bayar ke Midtrans KAMI; komisi agen (Rp/% per-agen, diatur admin) cair 1×/bulan ber-gerbang owner; reseller dibayar AGEN (kami sediakan hitungan + Excel transfer-massal); atribusi = kode saat daftar, permanen; portal agen+reseller menumpang infra existing.
- **URUTAN:** F0 🟡 (draf kontrak Lampiran-A + riset pajak §6b ✅ 17-Jul; sisa angka & validasi = owner, paralel) → F1 mesin uang (atribusi+ledger+admin; program bisa jalan tanpa portal) → F2 portal agen → F3 reseller+Excel → F4 pelengkap. Tiap fase: rencana rinci → ketok → bukti runtime → izin deploy eksplisit.
- **🎯 PERINTAH OWNER 2026-07-17: sesi berikutnya FOKUS menyelesaikan modul ini** — mulai dari rencana teknis rinci F1 + daftar file → ketok.
- **DONE-BILA:** per-fase di SPEC §7; item tutup saat F1–F3 live + ≥1 agen nyata terbayar benar.
- **REALISASI:** ⬜

### [B22] MANAJEMEN ERROR AI + REM-CEPAT non-retryable — ✅ LIVE PRODUKSI 2026-07-18 01:04 (`99b1c32`)
- **SPEC/SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md`.** Pemicu: insiden RAD 2026-07-17 (langganan ElevenLabs gagal-bayar → 3× produksi gagal beruntun, tiap percobaan bakar biaya LLM sebelum mati di TTS → circuit-break). Owner: rem SEGERA utk error mustahil-sembuh (kredit/pembayaran), + kerangka error world-class extensible SEMUA adapter (bukan tambalan EL).
- **REALISASI:** taksonomi `ErrorClass` + `FAST_FAIL={billing,quota}` (exceptions.py) · classifier EL-direct terverifikasi (elevenlabs.py) · propagasi last_* (tts_engine→pipeline) · persistensi migr **0170** `production_runs.error_class` · circuit-breaker semantik + reorder produce_one (producer.py) · helper `inventory.latest_failure`. **Uji 13/13 vs DB live** (classifier 2 string EL nyata · persistensi e2e · rem-di-1 utk billing/quota · regresi UNKNOWN tetap streak-3 · success memutus streak) · py_compile+import bersih · FE tak tersentuh · data uji 0 sisa.
- **DEPLOYED 2026-07-18 01:04** (izin owner; BE OK health=200; nol error import, 3 thread produksi start bersih). **Sisa:** bukti hidup alami saat insiden billing/quota berikutnya (rem di 1×); extension OpenAI/fal `classify_error` menyusul saat ada sampel (registry §4).

### [B23] CONTENT CATEGORY per-channel (Shorts / Regular) — 🟡 F0 ✅ diketok penuh 19-Jul · **dokumen MATANG 100% + AUDIT KEMATANGAN ✅ 21-Jul — eksekusi F1 menunggu owner buka gerbang** (migrasi 0173 sempat diterapkan → DICABUT BERSIH atas perintah; nol jejak di DB/kode)
- **SPEC/SSOT = `CONTENT_CATEGORY_ARCHITECTURE.md`** (eks AUDIT_HARDCODE_FORMAT_VIDEO; WAJIB baca blok CARA PAKAI + ledger §2 sebelum menyentuh — semua keputusan L4–L10 sudah diketok, JANGAN tanya ulang).
- **TUJUAN:** tenant memilih per-channel: Shorts (portrait, aktif) vs Regular (landscape 90–720 dtk, "coming soon" → hidup bertahap F2–F4); gating tier trial&starter=Shorts · pro=+Regular≤180s · business=semua.
- **FASE (gerbang per-fase, §8 SPEC):** F0 keputusan ✅ TUTUP 19-Jul · **F1 fondasi kategori (ketok 19-Jul, nol perubahan perilaku)** · F2 katalog+gating · F3 mesin long (menunggu uji beban) · F4 publish+rilis · F5 kecerdasan.
- **DONE-BILA:** channel Regular pertama tenant nyata memproduksi + mempublikasikan video landscape sesuai tier, nol regresi jalur Shorts.
- **REALISASI:** 21-Jul — AUDIT KEMATANGAN dokumen tuntas (ketok owner): semua klaim desain F2–F5 diverifikasi ulang vs kode+DB live; 3 lubang desain dipatri + 3 koreksi + 4 patrian + **§7l standar UI/UX per-peran** (mandat owner "memudahkan admin & tenant"; 7 patrian menumpang pola UI existing — rincian = changelog SPEC 21-Jul & 21-Jul (2)); keputusan owner terekam: Regular TETAP satu aplikasi (bukan v3 terpisah). Fase teknis belum mulai — per-fase diisi dengan bukti, lihat §8 SPEC.

### [B24] GERBANG UJI PRODUKSI — tutup 4 pintu "konten gratis tanpa bayar" — 🟢 F1–F7 SELESAI + TERVALIDASI (707 uji lulus), **BELUM DEPLOY** (2026-08-02)
- **SPEC/SSOT = `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` §10** (WAJIB baca UTUH sebelum menyentuh; §10a = fakta terverifikasi, JANGAN audit ulang; §10b = keputusan owner K1–K6, JANGAN tanya ulang).
- **SEBAB (owner 2-Agu):** video uji ter-unggah PRIVAT ke YouTube Studio tenant → tenant bisa mengubahnya jadi Publik sendiri → dapat konten tanpa bayar. Bukti nyata: m.yusroon (trial, jatah 1 video/hari) menekan uji 11×, **7 ter-publish**.
- **TEMUAN:** **4 pintu** menghasilkan video tanpa cek status langganan (Test Run · Test Niche · Jalankan-ulang lewat **browser→DB langsung** · unduh stok) + **5 jalur reaktivasi** yang tak satu pun melepas rem channel (billing nol sentuhan ke tabel `channels`) ⇒ tenant bisa terjebak setelah bayar.
- **RANCANGAN:** satu otak (`tenant_test_gate` fungsi DB) + 3 lapis pagar (RLS · API · worker — masing-masing menjaga jalur berbeda, tak saling menggantikan) + `tenant_resume_channels` dipanggil kelima jalur reaktivasi. **6 kenop admin (NO-HARDCODE)** termasuk saklar induk `test_gate_enabled` = rollback tanpa deploy.
- **FASE:** F1 migrasi 0190/0191 · F2 mesin (limits/producer/midtrans/webhook_app) · F3 API (5 route) · F4 layar admin · F5 layar tenant (+buang fosil `trialing`) · F6 matriks regresi §10f · F7 dokumen. **Tracker per-berkas = §10e SPEC.**
- **DONE-BILA:** tiap status tenant × tiap pintu terbukti sesuai matriks §10f lewat uji nyata (bukan baca kode), nol regresi 5 permukaan, pesan penolakan dwibahasa, kenop terlihat & bisa diubah owner dari `/admin/app-config`.
- **REALISASI:** 2-Agu — deep-dive tuntas + rencana ditulis ke SPEC §10, lalu **F1–F7 DIKERJAKAN TUNTAS**: 3 migrasi APPLIED ke DB live (0190 kenop · 0191 fungsi+RLS · 0192 gerbang produksi) · 16 berkas kode disunting + 4 berkas baru · **707 pemeriksaan lulus di 5 jalur, 0 gagal** (DB 64 · RPC 30 · suite 581 · API 13 · layar 19) · 4 bug ditemukan & dituntaskan selama siklus validasi (1 di kode produksi, 3 di perkakas uji) · fosil `trialing` dibuang dari 3 tempat · produksi tak tergores (direct_jobs tetap 98, channel terjeda tetap 3). Bukti + rincian + pelajaran = SPEC §10e. **AUDIT FINAL pra-deploy (perintah owner) menemukan & menutup 2 LUBANG TAMBAHAN:** (1) tautan unduh hasil uji terbit tanpa gerbang — pintu keluar KEENAM yang terlewat di sapuan pertama (uji pertamanya sempat HIJAU PALSU karena subjeknya tak punya video; diperbaiki + diberi uji pembanding); (2) **JEBAKAN yang lahir dari gerbang ini sendiri** — tenant masa-tenggang & masa-coba-jatah-habis punya hak produksi tapi tombol pemulih remnya ikut terkunci → ditutup dengan migr 0193 + endpoint `channels/[id]/resume` + tombol **"Pulihkan produksi"** (tidak memproduksi apa pun). **AUDIT PUTARAN KETIGA (owner: "kalau masih menemukan bug, berarti audit terakhir juga bisa miss") menemukan 3 CELAH LAGI — dua di antaranya LINTAS-TENANT dan lebih serius dari semuanya:** (A) pekerjaan bisa **disamarkan sebagai `admin_test`** → melewati jatah DAN gerbang worker sekaligus (dibuktikan HTTP 201); (B) **produksi bisa dipicu di channel MILIK TENANT LAIN** → memakai kunci AI + koneksi YouTube korban (dibuktikan HTTP 201; nol kejadian historis); (C) **link perpanjang masa coba bisa diulang tanpa batas** = masa coba gratis selamanya. **A & B lebih tua dari gerbang uji — tapi Claude menyentuh persis aturan yang bocor di 0191 dan melewatkannya.** Ketiganya ditutup (migr 0194 + worker + webhook + layar reaktivasi). **Jalur konversi C diganti, bukan dibuang:** klik pertama tetap gratis · sudah pernah → diarahkan **UPGRADE** · pernah bayar → diarahkan **PERPANJANG** (jawaban pertanyaan owner). **PUTARAN KEEMPAT (menyisir apa yang tenant boleh ubah sendiri) menemukan 2 celah lagi:** (D) tenant bisa **MEMATIKAN REM DARURAT sendiri** lewat perubahan langsung — melumpuhkan pelindung slot render kita DAN membuat gerbang pemulihan jadi hiasan (dibuktikan HTTP 200); (E) akun YouTube diambil **tanpa cek pemilik** — saudara kembar celah B. Ditutup (migr 0195 trigger rem read-only + validasi kepemilikan akun); regresi trigger diuji 9/9 (tenant tetap bebas mengubah kolom lain). **Total 787 pemeriksaan lulus, 0 gagal; 11 pintu/celah ditutup.** **SISA: izin deploy owner (§5.0) — lapis DB sudah aktif, lapis API & layar menunggu deploy. [Keputusan owner 2-Agu: m.yusroon DIBIARKAN sesuai aturan; perpanjangan HANYA lewat layar admin — terbukti menyegarkan jatah.]**

### 🧭🛑 POSISI 2026-08-03 13:45 — BACA INI SEBELUM MENYENTUH ALUR GERBANG/REM/PEMULIHAN
> **Ditulis sebagai antisipasi compaction (perintah owner). Kalau Anda baru "bangun": JANGAN bongkar
> kode apa pun sebelum membaca blok ini + `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §8–§10 + [B24]/[B25].**

**SUDAH LIVE DI PRODUKSI:** FE & BE `9ba3075`, tiga layanan aktif, situs 200.
**8 migrasi SUDAH APPLIED** ke DB live: `0190`–`0197` (kenop gerbang · fungsi+RLS · gerbang produksi ·
pulihkan per-channel · rem read-only · antrean tak bisa disamarkan · rem simpan sebab · pemulihan
memutus hitungan). **JANGAN diterapkan ulang. JANGAN dibuat migrasi yang mengulang isinya.**

**⛔ KEPUTUSAN YANG SUDAH DIKETOK — HARAM dibalik tanpa ketok owner baru:**
1. **Pemulihan produksi = keputusan TENANT.** Sistem TIDAK PERNAH melepas rem sendiri karena sebab
   teknis dianggap lewat. (Pengecualian tunggal: reaktivasi LANGGANAN — bayar/admin aktifkan.)
2. **Petakan per KELAS error, TIDAK PERNAH per nama penyedia** — penyedia akan terus bertambah.
   Menyebut merek di kode UI = pelanggaran, dan sudah ditegakkan uji.
3. **Jalur yang MEMBUKTIKAN didahulukan.** Selama uji masih boleh dijalankan, tawarkan "Jalankan uji
   & pulihkan" (memproduksi → membuktikan sehat → rem lepas). Tombol "Pulihkan produksi" HANYA untuk
   yang ujinya terkunci. **Membalik ini = mengulang insiden yang membuat tenant komplain.**
4. **Masa tenggang (grace):** produksi & publish TETAP JALAN, tombol uji DIKUNCI.
5. **Perpanjangan masa coba hanya lewat layar admin.** m.yusroon dibiarkan terkunci sesuai aturan.
6. **HARAM memperbaiki channel tenant lewat jalur belakang (DB).** Pemulihan lewat produk.

**💣 JEBAKAN YANG SUDAH DIBAYAR MAHAL — jangan diulang:**
- **Melepas rem TANPA memutus hitungan kegagalan** → penjadwal mengerem lagi dalam HITUNGAN DETIK.
  Terjadi ke tenant nyata (11:01:19 tekan → 11:01:30 rem lagi). Kolom `production_resumed_at` +
  filter `sejak` pada `recent_nonready_streak`/`latest_failure` adalah OBATNYA — jangan dicabut.
- **Uji yang berhenti di detik pertama.** Apa pun yang berjalan periodik BELUM SELESAI sampai satu
  siklus penuh terlewati. "Tombol berhasil" ≠ "keadaan bertahan".
- **Alat verifikasi yang bisa MENULIS.** Uji pernah memulihkan channel tenant sungguhan. Uji terhadap
  produksi wajib read-only.
- **`SELF_HEALING` punya EMPAT cermin** (kode · dokumen §1 · `pemulihan-channel.tsx` · `admin/system`).
  Menambah kelas error = perbarui KEEMPATNYA; uji `test_pemulihan_channel.py` menjaga semuanya.
- **Server lokal untuk uji layar:** SELALU bandingkan waktu-mulai proses vs `.next/BUILD_ID`. Sudah
  2× menguji build LAMA dan menyimpulkan salah.

**BUKTI TERAKHIR (jangan diaudit ulang):** BISIK NUSANTARA dipulihkan 11:48 → penjadwal 12 siklus →
**12:09 memproduksi video SUKSES** → rem tetap mati. Sebelumnya menyala lagi dalam 1–11 detik.

**SISA — dan alasan kenapa BELUM dikerjakan (bukan kelalaian):**
| Sisa | Kenapa belum |
|---|---|
| Bang Us-Dat & Abyss ID masih ter-rem | Keputusan TENANT. Layarnya sudah mengarahkan ke jalur yang benar. JANGAN dipulihkan dari DB. |
| ~~`notify_publish_fail` belum seragam~~ | ✅ **SELESAI 4-Agu** (SSOT §8b) — anjuran per-KELAS; 6 uji sampel-produksi |
| ~~Kartu admin "failures by type" menebak dari teks~~ | ✅ **SELESAI 4-Agu** — pendekatan GABUNGAN: kelas tersimpan = fakta, tebakan-teks hanya utk data lama & **DITANDAI**; kartu menyebut perbandingannya. Cermin KELIMA dijaga uji. |
| ~~Registry §4: baris ⏳ fal & OpenAI billing~~ | Sampel NYATA sudah ditemukan & dicatat 4-Agu (fal 403 saldo habis ×6 · billing hard limit ×1). Menaikkan ke ✅ = **§8e-B**, butuh ketok owner. |
| Registry §4: Anthropic | Belum ada sampel error nyata. Aturan emas: jangan menebak. |
| ~~`MEMORY.md` mendekati batas baca~~ | ✅ **SELESAI 3-Agu** — 20,6KB → 12,4KB, 18 penunjuk terverifikasi utuh |
| ~~**§8e-B: kelas error jalur GAMBAR/VIDEO**~~ | ✅ **SELESAI 11-Agu — DIKETOK OWNER** (SSOT §8j). Kekhawatiran lama ("salah golong → channel berhenti padahal cukup ditunggu") **tertutup oleh sumber pemetaannya**: bukan tebakan, tapi tabel resmi Cloudflare & Gemini — dan kasus "cukup ditunggu" (`3040` kapasitas sesaat · `3007`/`3008` timeout · `resource_exhausted` Gemini yang ambigu) sengaja **TIDAK** ikut FAST_FAIL, jadi toleransi 3-kegagalan mereka utuh. Ketokan owner: rem cepat **DINYALAKAN** — alasannya nama baik MesinViral, karena tanpa itu tenant melihat **3 produksi gagal berturut-turut** (sekaligus membakar jatah naskah+suaranya) dan menyimpulkan MesinViral yang rusak, alih-alih membaca kalimat penyedianya sendiri sekali dan berhenti. |

**REALISASI 2026-08-04 (perintah owner "jangan berhenti sebelum zero bug"):** 3 benang diluruskan, semuanya
dengan **merah dibuktikan lebih dulu** (uji gagal tanpa perbaikan) — (1) **§8e-A** jalur gambar/video berhenti
membuang sebab penyedia; tenant kini melihat *"saldo habis — isi ulang di …/billing"* alih-alih *"no clips
downloaded"* (sampel nyata 14-Jul: 3 run terbakar 55-85 dtk tanpa tenant tahu apa pun). (2) **§8b** notifikasi
gagal-unggah kini menjawab "perlu bertindak atau cukup ditunggu". (3) **Kartu admin** berhenti menampilkan
angka tebakan. Suite **623 → 641 lulus, nol regresi**; nol tulisan ke DB; nol deploy.
**KOREKSI JUJUR:** putaran ini juga MENGGUGURKAN satu "temuan" Claude sendiri (404 Gemini) — sampel ujinya
DIKARANG, teks produksinya sudah tertangani sejak 22-Jul. Dari 5 sampel error nyata yang diuji ke kode
berjalan, **4 sudah benar sejak lama.** Pelajaran mengikat → memory `feedback_sampel_uji_wajib_dari_produksi`.

**REALISASI 2026-08-11 (rencana disetujui owner — SSOT `AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8j):**
Pemulihan gambar **MATI 2 bulan** karena **satu baris setelan yang tak pernah diserahkan** (`llm_model`),
bertemu penjaga koherensi [B11]-G3 yang benar → nama model perbaikan **kosong melompong** ⇒ 49× *"Model
untuk 'Groq' tidak ditentukan"*. **17 dari 18 tenant terdampak; satu-satunya yang sehat = channel owner
sendiri** — itulah sebabnya kerusakan ini tak pernah terlihat dari tempat owner menguji. Terukur: **28
adegan mati**, pemulihan berhasil **1×**, dan **35 kegagalan penyedia yang sebabnya tak pernah tersimpan**
(itu sebabnya "jatah Cloudflare habis" tak bisa dibuktikan ada MAUPUN tidak ada). Sekaligus ditutup: cacat
`0d64f79` yang membuat MesinViral **menuduh penyedia AI tenant atas bug MesinViral** (kejadian nyata 11-Agu
12:21; **75 kegagalan di worker.log milik KITA**). **Aturan emas §1 dibalik atas ketok owner:** pemetaan galat
wajib dari **dokumen resmi penyedia SEBELUM dipakai**, bukan menunggu kerusakan — dokumen itu menyelamatkan
kita dari bug yang hampir saya tanam (Cloudflare `3036` berhenti vs `3040` ulangi, **dua-duanya HTTP 429**).
Bukti runtime: **7/7 channel aktif** kini memilih model perbaikan yang cocok dengan penyedianya (sebelumnya
6 dari 7 kosong). Suite **826 → 852 lulus, nol regresi.** Penjaga permanen `tests/test_setelan_ai_tak_pernah_hilang.py`
(26 uji) membuat **model AI baru tak bisa dinyalakan tanpa tabel galatnya**. Nol migrasi DB · nol komponen FE baru.

**REALISASI 2026-08-12 — PENYATUAN GALAT AI (SSOT §8j lanjutan):** EMPAT penilai galat tersebar jadi
**SATU** (`src/providers/galat_registry.py`) — sebab "setiap perbaikan menambah kekusutan": vendor baru
dulu berarti menulis penilai baru. Sekarang **vendor/model baru = menambah baris data, nol koding**, dan
agregator (fal.ai kini; blackbox.ai dsb. nanti) ditandai satu penanda sehingga galat vendor di baliknya
ikut terbaca. Seluruh **9 penyedia katalog** dipetakan dari **dokumen RESMI** + tanggal baca, termasuk 3
yang sebelumnya NOL golongan (Anthropic · OpenAI TTS · Edge TTS). Sekaligus **mengoreksi cacat yang saya
kirim sendiri jam sebelumnya**: jatah gratis harian Cloudflare masuk rak "kredit habis" ⇒ layar & Telegram
sama-sama berkata "tidak akan pulih sendiri, isi ulang saldo" untuk jatah yang pulih tengah malam.
Pagar `tests/test_galat_generik.py` (16 uji) **dibuktikan merah** untuk 3 bentuk pelanggaran. Suite
**869 lulus, nol regresi.** Nol migrasi DB · nol perubahan tampilan · nol komponen baru.

**REALISASI 2026-08-12 — SEBAB YANG PULIH SENDIRI BERHENTI MEMATIKAN CHANNEL (SSOT §9a):**
Layar berkata *"pulih sendiri, Anda tidak perlu mengubah apa pun"*, tapi channelnya tetap mati sampai
tenant menekan tombol. Bang Us-Dat: jatah token harian Groq habis 01-Agu, pulih keesokan pagi
(02-Agu produksi BERHASIL 2×), status berhenti menempel **11 hari** — pola yang pernah membuatnya
mati 44 jam. Kini kegagalan yang pulih sendiri **netral** dalam hitungan rem (bukan pemutus, supaya
rem tidak lumpuh untuk sebab nyata). Keputusan [B25] tidak dibalik — lingkupnya dikembalikan ke sebab
yang memang menuntut tindakan tenant. Bukti data nyata: Abyss ID (`model_unavailable`) tetap direm,
benar. Batas jujur: kegagalan lama ber-kelas `unknown` tak ikut tersembuhkan — pencegahan ke depan,
bukan penyembuhan ke belakang. Suite **880 lulus**, pagar dibuktikan merah dua arah. Nol DB · nol
tampilan · nol komponen baru.

**REALISASI 2026-08-12 — PEMBERITAHUAN TELEGRAM BISA DITINDAK (owner menunjukkan 3 pesan nyata):**
(1) Pesan "calon pelanggan panas" dulu hanya kode mesin + istilah Inggris → kini nama, email, channel,
alasan panas (**sudah pernah produksi video**), umur lapse, jumlah email pengingat, tautan admin.
(2) Pesan "video terbit" dulu jauh lebih miskin dari pesan video uji — sebabnya penerbit tak pernah
diserahkan angka produksi yang **sudah ada di metadata item** (durasi · ukuran · skor · jumlah kata);
kini diserahkan, **nol kueri baru**. (3) `⏰ Runtime: 0m 0s` — bukan salah hitung tapi salah URUTAN:
angka dibaca di pipeline baris ~689, ditulis ±70 baris di bawah; kini diisi sebelum dikirim.
(4) Nomor produksi internal (`run_id`) **dicabut dari mata tenant** di 4 pesan; tetap dicatat di log.
(5) `notify_failure` masih memotong pesan galat **senyap** di 250 huruf — pola yang sudah diketok
terlarang (§8h); kini memakai pemendek yang MENGUMUMKAN, sama dengan fungsi sebelahnya.
(6) Nilai yang diselipkan ke pesan OWNER kini dibersihkan (`TelegramNotifier.aman`) — tanpa itu teks
galat ber-`<`/`&` (balasan S3 berbentuk XML) membuat Telegram menolak pesannya dan **alarm terpenting
hilang tanpa jejak**; bahaya ini belum pernah terjadi (nol pesan ditolak sepanjang log), ditutup karena murah.
Suite **880 → 893 lulus**, pagar dibuktikan merah 4 bentuk pelanggaran. Nol DB · nol tampilan · nol komponen baru.

**REALISASI 2026-08-13 — LOG & PENYAPUNYA DITUNTASKAN (ketok owner: "tidak boleh ada lagi issue
terkait log dan log sweeper di seluruh area mesinviral v2"):** Tiga cacat, satu pola — **kegagalan
yang melapor ke ruang kosong.**
**(1) Penyapu log menyapu alamat yang salah selama 2 bulan.** Aturan `/etc/logrotate.d/viral-machine`
ditulis **24-Apr** (era v1) menunjuk `/home/rad4vm/viral-machine/logs/*.log`; proyek pindah ke v2
**17-Jun** dan aturannya tertinggal. Tiap hari ia melapor *"does not exist -- skipping"* — folder itu
memang **tidak ada** — sementara `worker.log` tumbuh ke **48 MB tanpa satu pun berkas hasil putaran**.
**Akar strukturalnya: berkas setelan ada DI LUAR repo** → tak terversikan, tak terperiksa, tak
terlihat saat melenceng. Kini hidup di `scripts/logrotate-viral-machine.conf`, **dipasang
`deploy_be.sh`**, dan deploy **MEMPERINGATKAN** bila `worker.log` melewati batas — kegagalan senyap
jadi kegagalan yang menyalakan lampu. Dua baris wajib ditemukan lewat **jalan-kering, bukan
penalaran**: `su root root` (tanpa itu logrotate menolak: *parent directory has insecure permissions*
— usulan pertama pun akan gagal diam-diam) dan `copytruncate` (systemd memegang berkas terus).
**(2) Mesin terlalu berisik** — channel tak aktif dicatat ulang tiap **15,6 detik** (terukur):
**9.950 baris/24 jam = 44% isi log**. Kini dicatat sekali; penanda dihapus saat channel kembali aktif
sehingga **perubahan keadaan tetap tercatat**. Alur keputusan produksi **tidak disentuh** (dijaga uji).
**(3) Daftar sapuan berkas kerja tertinggal saat format berganti** — penyapu hanya kenal
`.json`/`.mp3`/`.srt`; produksi menulis `.ass` (subtitle, dulu `.srt`), `.txt`, `.jpg`, `.mp4`.
Terukur **634 dari 808 berkas >7 hari, ±73 MB**, tertua **16/17-Jun**. Ditambahkan ke penyapu yang
**SUDAH ADA** (bukan penyapu kedua); `.mp4` sengaja berambang panjang — satu-satunya berkas yang
kehilangannya tak bisa dipulihkan. Lama simpan dipindah dari angka mati ke setelan (§3.3).
Pagar `tests/test_log_tidak_membanjir.py` (14 uji) **dibuktikan merah 4 bentuk pelanggaran**.
Suite **893 → 907 lulus**. Nol DB · nol tampilan · nol komponen baru.
**MASIH KETOKAN OWNER:** batas jurnal sistem (`SystemMaxUse` belum pernah disetel → memakai bawaan
±5,8 GB; kini terpakai 2,1 GB). Bukan bom, tapi angkanya tak pernah dipilih siapa pun.

### [B25] REM DARURAT: simpan sebabnya & katakan apa artinya — 🟢 A–D SELESAI + TERVALIDASI (2026-08-03)
- **SPEC/SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §8a (celah, kini TERTUTUP) + §9 (kontrak tampilan per-KELAS).** WAJIB baca §9 sebelum menyentuh UI kegagalan produksi.
- **SEBAB:** rem darurat MEMBUANG kelas error yang sudah diketahui sistem → layar & Telegram cuma bisa menebak ("mis. saldo/kredensial AI") → tenant tak pernah tahu **apakah sebabnya pulih sendiri**. Dampak terukur pada tenant BERBAYAR: **Bang Us-Dat mati ±44 jam** menunggu jatah harian yang sudah pulih keesokan harinya; BISIK NUSANTARA pola yang sama sehari kemudian.
- **ARAHAN OWNER yang mengikat:** (1) **jangan perbaiki lewat jalur belakang** — pemulihan lewat produk, bukan DB; (2) penyedia & model AI **akan terus bertambah** → antisipasi **GENERAL: petakan per KELAS, tidak pernah per nama penyedia**; (3) **jangan otomatis aktif** — UI/UX yang harus user-friendly & well-informed, pemulihan tetap keputusan tenant.
- **REALISASI:** (A) migr **0196** `production_paused_class` + alasan memuat penyebab nyata utk KEDUA cabang · (B) **panel pemulihan per-KELAS** di layar channel (apa yang terjadi · **pulih sendiri?** · langkah + tautan + tombol *Pulihkan produksi*; kelas tak dikenal tidak mengarang) · (C) Telegram beda anjuran pulih-sendiri vs butuh-tindakan + tautan ke channel · (D) `/admin/system` daftar seluruh channel berhenti + sebab. Himpunan **`SELF_HEALING`** jadi sumber tunggal, hidup di 3 tempat (Python · dokumen · layar) dan **keselarasannya diuji**; larangan menyebut nama penyedia di layar **ditegakkan uji**.
- **BUKTI:** 12 uji unit + **22 pemeriksaan klik→layar** (7 kelas × judul & status · kelas tak-dikenal · daftar admin), nol galat halaman; suite proyek 600 → **612**.
- **DONE-BILA:** channel berbayar yang berhenti bisa dipulihkan tenant SENDIRI dari layar, tanpa bertanya, dan tanpa jalur belakang. ⏳ menunggu kejadian nyata pertama pasca-deploy.

### [B26] PENERBITAN & ALARM TAK BOLEH SENYAP — 🟢 A·B·C SELESAI (2026-08-13) · ⏳ 1 pemulihan data menunggu izin owner
- **SPEC/SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §4b (galat penyimpanan KITA) + §9 kecualian "milik kita" + §10 penjaga no.4-5 + §11 changelog 13-Agu.** WAJIB dibaca sebelum menyentuh jalur terbit / alarm penyimpanan.
- **SEBAB (satu akar, tiga wujud):** keadaan penting disimpan di **ingatan proses**, sementara proses itu bisa mati kapan saja — dan pada 27-Jul→13-Agu ia mati **10 kali**.
- **(A) Kabar "penyimpanan PULIH" tak pernah datang.** Akun penyimpanan diblokir penyedia 04:24–10:21 (tagihan belum dibayar — dikonfirmasi owner). Alarm bahaya terkirim 04:54 ✅, lalu penyimpanan pulih dan **owner tidak pernah dikabari** — terukur: hari itu HANYA 2 notifikasi keluar dari mesin. Sebab: hitungan gagal ada di ingatan, terhapus 2× (mesin mati 07:54 · restart 10:21) → saat pulih hitungannya < ambang → mesin menyimpulkan "tak pernah ada masalah". **Alarm bahaya selamat dari restart, kabar pulih tidak.** → status alarm pindah ke `system_state` (pola terbukti dari alarm drift durasi, ketok owner 16-Jul); penanda dinyalakan **hanya bila alarm benar-benar terkirim**.
- **(B) Pesan gagal-terbit berhenti melempar kode.** Yang tenant terima 06:00: `403 HeadObject Forbidden` + nama berkas internal — untuk kegagalan yang **100% milik kita**. Owner: *"pesan errornya tidak jelas hanya kode saja. ANEH"*. → digolongkan di **satu rumah** (`galat_registry.golongkan_penyimpanan`), kalimatnya **mengaku di sisi MesinViral**, kode aslinya tetap di catatan server + alarm admin. Berkas hilang (`NoSuchKey`) dapat kalimat BERBEDA — tak menjanjikan "terbit otomatis" yang mustahil.
- **(C) Stok nyangkut di "sedang diterbitkan" akhirnya punya penyapu.** Korban NYATA: 12-Agu 19:00 mesin mati 7 detik sesudah unggahan selesai → video `xa3Rbi-SbXM` **hidup, PUBLIK, 1.024 penonton · 11 suka · 1 komentar** di channel **BISIK NUSANTARA (tenant BERBAYAR)**, sementara bagi sistem kita ia **tidak pernah ada**: `videos` tanpa barisnya · tautan YouTube di catatan produksi kosong · tenant tak dikabari · aset kekal (status itu justru DILINDUNGI penyapu-yatim) · mesin pembelajaran tak pernah melihat video yang paling laku. Satu-satunya status dalam-proses tanpa penyapu (produksi 3 jam ✓ · uji-manual 30 menit ✓ · terbit ✗). → penyapu memutuskan dari **jejak unggahan**: nomor YouTube ada → pembukuan dituntaskan (waktu terbit dikoreksi ke waktu sebenarnya) · unggahan belum dimulai → kembali ke stok · **sudah dimulai tapi nomor tak tercatat → TIDAK diterbitkan ulang, dilaporkan ke owner**.
- **⚠️ KEPUTUSAN YANG MENGIKAT — jangan dibalik:** rencana pertama berbunyi *"tak ada nomor YouTube ⇒ terbitkan ulang"*. **Itu salah**: unggahan bertahap punya celah sempit di mana YouTube sudah menerima tapi kita belum tahu nomornya ⇒ **VIDEO KEMBAR** di channel tenant. Cabang ketiga (lapor, jangan tebak) = §0.6 gagal jujur.
- **KECELAKAAN YANG IKUT DIPERBAIKI (dicatat supaya tak terulang):** uji versi pertama **menulis ke baris PRODUKSI** — penyapu memanggil `inventory.mark_published()` yang membuat klien Supabase-nya SENDIRI dari env, sehingga baris `content_inventory` id=231 berubah status dari sebuah uji lokal. → penyapu kini memakai `sb` yang diberikan (seragam dengan seluruh berkas itu) DAN berkas uji memasang pagar yang **menolak sambungan sungguhan**.
- **BUKTI:** 41 uji baru (`tests/test_terbit_dan_alarm_tak_senyap.py` 23 · `tests/test_notifikasi_owner_dan_tenant.py` +5, total 18). Keduanya dibuktikan **merah lebih dulu lewat sabotase sengaja**: galat mentah dikembalikan ke pesan tenant → merah · penyapu dikembalikan memakai sambungan sendiri → merah. Suite 907 → **935**, nol regresi. **Nol migrasi DB** (tak ada kolom baru; penanda hidup di `metadata` + `system_state`).
- **DONE-BILA:** (1) alarm penyimpanan mengabari BAHAYA **dan** PULIH walau mesin restart di tengah ✅ kode+uji · (2) tenant tak pernah lagi menerima kode mesin dari jalur terbit ✅ kode+uji · (3) tak ada video yang bisa terbit tanpa tercatat ✅ kode+uji · (4) ⏳ **bukti runtime pasca-deploy** · (5) ⏳ **video korban `xa3Rbi-SbXM` tercatat lengkap** — butuh izin owner (satu tulisan DB; jalur terbersih = kembalikan baris id=231 ke status "sedang diterbitkan" + isi jejak nomor YouTube-nya, lalu **penyapu baru merapikannya sendiri** = sekaligus bukti runtime pada kasus nyata).
- **(D) MESIN YANG MATI MENDADAK AKHIRNYA BERSUARA** — 🟢 SELESAI (ketok owner 13-Agu "kerjakan D hingga tuntas"). Mesin mati mendadak **11×** (1× 3-Jul, lalu **10× dalam 18 hari** sejak 27-Jul, terakhir 13-Agu 07:54); server menghidupkannya lagi dalam 10 detik sehingga dari luar tampak normal dan **tak seorang pun pernah diberi tahu**. Dua hal dipasang di titik-mulai mesin: **(1) perekam detik kematian** — menuliskan apa yang sedang dikerjakan SETIAP bagian mesin (berkas + nomor baris) plus penunjuk bagian yang benar-benar mati; **(2) penanda keadaan** — kabar ke owner bila mesin sebelumnya tidak pernah berhenti dengan wajar, ber-jeda 1 jam supaya kematian beruntun tak jadi teror.
  - **Yang SUDAH disingkirkan (bukan dugaan):** pustaka gambar/font **DICABUT** — catatan inti sistem menunjuk kematian terjadi **di dalam mesin bahasa Python sendiri** (satu melompat ke alamat kosong), dan hanya 4 dari 10 kematian punya jejak render di dekatnya. Kehabisan memori **disingkirkan** (2,9 GB bebas, nol catatan OOM). **Hanya proses produksi** yang mati — webhook 0×, proses lain di server 0×.
  - **Kerugian terukur — DIKOREKSI dari laporan pertama:** semula saya sebut **7** produksi mati di tengah; angka itu **SALAH** karena alat ukur saya hanya menghitung penutup *"PIPELINE COMPLETE"* padahal produksi gagal ditutup dengan *"PIPELINE FAILED"* → setiap kegagalan tampak menggantung. Setelah diukur ulang: **297 produksi dimulai · 293 ditutup benar · 3 mati di tengah karena mesin mati** (satu di antaranya = kasus 12-Agu yang sudah diperbaiki bagian C). Jadi alasan mengerjakan D **bukan** "kerusakan besar", melainkan "**kita buta pada kerusakan yang lajunya naik tajam**".
  - **Keputusan teknis:** penanda keadaan di **berkas `/var/tmp`**, bukan basis data — (a) tetap terbaca saat DB/jaringan bermasalah (justru keadaan yang paling mungkin menyertai kematian), (b) **nol tambahan tulisan ke basis data** (ketok owner: *"pastikan ini tidak memberatkan mesin itu sendiri"*), (c) BUKAN `/tmp` yang bisa dibersihkan saat server dinyalakan ulang → alarm palsu. **Tiga** keadaan (belum pernah jalan · jalan · berhenti wajar) — tanpa yang pertama, pemasangan pertama selalu melapor kematian palsu.
  - **BUKTI:** perekam **dibuktikan dengan kematian sungguhan** pada tiruan mesin ini (bukan dari dokumentasi) → rekaman memuat semua bagian + nomor baris · penanda diuji ke **data nyata 4 dari 4 tepat** (07:54 & 12-Agu 19:00 mati mendadak → tak ada baris penutup; 10:21 & 15:05 restart wajar → ada) · 11 uji baru, **tiga sabotase** dibuktikan merah. ⚠️ **Sabotase pertama sempat LOLOS** karena penjaganya membaca komentar (`# faulthandler.enable()` masih mengandung kalimatnya) — penjaga diganti jadi **uji perilaku di penerjemah bersih** (di luar pytest yang punya perekamnya sendiri). Itu **kali keempat** komentar menipu alat ukur di sesi ini; `_kode_berkas()` sekarang menyaring komentar untuk semua uji urutan.
- **⏳ MASIH TERBUKA:** **sebab kematian belum diketahui.** D tidak menyembuhkan — ia membuat kematian BERIKUTNYA berbicara (pada laju sekarang: beberapa hari). Jalan pintas yang **belum diketok**: berkas rekaman sistem operasi 7-Agu (145 MB) masih ada dan bisa dibaca **bila alat baca dipasang di server** — peluang berhasil sedang, dan selama berkas itu belum diambil, kematian baru **tidak ikut terekam** oleh sistem operasi (itu sebab 9 kematian terakhir tanpa rekaman).

### [B27] LARANGAN NASKAH DINILAI ULANG UNTUK KEBUTUHAN VIRAL — 🟢 P4·P3·P1 SELESAI · 🔴 P2 DICABUT (2026-08-13)
- **SPEC/SSOT = `QC_CONTENT_ARCHITECTURE.md §2c` → blok "LARANGAN NASKAH DINILAI ULANG".** WAJIB dibaca sebelum menyentuh teks perintah penulis naskah.
- **SEBAB:** owner minta seluruh larangan hardcode dinilai dari sudut pandang **kebutuhan viral**, lalu memperingatkan *"perubahan anda jika salah bisa merusak metode preset durasi quality"*. **Peringatan itu terbukti benar.**
- **(P4) Mesin berhenti bertengkar dengan dirinya sendiri.** Satu prompt melarang elipsis mutlak (*"NEVER use '...'"*) sementara prompt lain di berkas yang SAMA menyuruh memakainya untuk ketegangan — dan pemeriksa menandai setiap tanda. Alasannya pun salah: prompt mengklaim ">1 detik", kalibrasi hidup menunjukkan **0,156–0,376 dtk** (setara satu koma, 4–8× lebih murah dari titik). Kini **satu jatah** (1/naskah, klimaks) dengan **satu angka** dipakai prompt & pemeriksa.
- **(P3) Gema penutup diizinkan sekali** — alat retensi terkuat di format pendek, dulu terlarang. **Wajib MENGGANTI kalimat penutup**, bukan menambah (bila menambah: ±4,4 dtk = 7% preset 60).
- **(P1) Mode CTA ketiga `explicit`, opt-in per channel.** Dulu hanya `implicit` (10 channel) & `soft_sell` (1) — **keduanya melarang meminta apa pun**, jadi tak ada satu pun cara mengubah penonton jadi pengikut. Yang dibuka: SATU ajakan khas video itu + alasannya, di dalam jatah detik penutup. **Ajakan generik tetap terlarang di semua mode.** Ikut ditutup: kata yang tenant tulis sendiri di teks CTA tak lagi dituduh melanggar larangan niche — sementara larangan niche tetap berkuasa penuh di bagian lain (diuji dua arah).
- **🔴 (P2) DICABUT SETELAH DIUKUR — jangan dihidupkan tanpa rencana sendiri.** "Panjang kalimat & sudut pandang ke DNA niche" merusak durasi: preset 60 dtk suara Ardi → 15 kata/kalimat **−7,9%** · 20 **−14,4%** · 25 **−18,4% (QC MENOLAK)** · 30 **−21,0%**. Sebabnya `words_per_sentence` adalah **penyebut rumus anggaran** dan **dilatih per-suara**; bahaya kedua, ia dilatih lintas-niche (`niche='*'`) sehingga satu niche berkalimat panjang menggeser durasi seluruh niche lain di suara itu.
- **BUKTI:** 22 uji baru (`tests/test_larangan_naskah.py`), **3 sabotase dibuktikan merah** (larangan mutlak dihidupkan lagi · gema jadi tambahan · jatah dua tempat dibuat beda). Uji saya sendiri menangkap **satu cacat di kode saya**: klausa pengecualian CTA ikut terbaca di mode `implicit` → diperbaiki jadi hanya muncul saat modenya aktif. Suite **946 → 968**, nol regresi. `tsc` FE lulus. **Nol migrasi DB** (kolom `cta_mode` teks bebas, tanpa batasan).
- **DI LUAR DAFTAR BERKAS RENCANA (disebut terbuka):** 2 berkas uji lama (`test_artefak_sambungan_bukan_elipsis.py`, `test_script_checker.py`) menegakkan aturan elipsis yang BARU SAJA diubah owner → naskah ujinya diselaraskan (dibuat melebihi jatah) dengan maksud asli uji dipertahankan utuh. Tanpa ini suite merah, dan aturan 4 dilanggar.
- **DONE-BILA:** (1) nol perintah yang saling membatalkan ✅ · (2) angka biaya jeda di prompt cocok kalibrasi hidup ✅ · (3) tenant punya cara mengajak tanpa ajakan generik ✅ · (4) ⏳ **bukti runtime: satu video uji di RAD The Explorer, dinilai owner** — belum dikerjakan · (5) ⏳ deploy (gerbang izin terpisah).

### [B28] PATRI LARANGAN + KEBOCORAN LARANGAN TENANT + GAYA VISUAL KE DNA — 🟢 SELESAI (2026-08-14) · ⏳ menunggu deploy & video uji
- **SPEC/SSOT = `DESAIN_PRODUK_SAAS.md §5b` (3 lapis + 5 patri, ketetokan owner) + `NICHE_DNA_AUDIT_REMEDIATION.md §1.1b` (penegakan larangan tenant + `render_style`).**
- **KETETAPAN OWNER:** patri di kode HANYA yang merugikan MesinViral (hukum · izin terbit · nama baik) + 2 ketetapan agama. **Selebihnya milik tenant** lewat DNA niche + disclaimer. Cakupan sengaja **tidak** diperluas ke nabi/malaikat lain. Syarat tambahan owner: **"HARUS BERSIFAT GENERIK, BERLAKU UNTUK SETIAP PENAMBAHAN AI MODEL/VENDOR BARU KEDEPANNYA"**.
- **5 PATRI:** Allah SWT · Nabi Muhammad ﷺ · tulisan Arab/Al-Qur'an terbaca · keselamatan anak · konten seksual.
- **CARA MENGUNCI (bukan janji — struktur):** patri ditempel **sebelum pembagian ke vendor** di `_generate_image`/`_generate_video` ⇒ **vendor baru otomatis terikat tanpa menyentuh kode patri** (dibuktikan uji dengan transport palsu "vendor besok") · **penyaring keluar**: prompt yang meminta hal terlarang **tidak pernah dikirim** · konstanta **di kode**, tak pernah dari DB · **penolakan saat simpan DNA** (dua pintu tulis memakai validator bersama) · **uji anti-jalan-pintas** (nol kode memanggil transport vendor langsung) · **uji per-transport**.
- **TIGA JEBAKAN DITEMUKAN & DITUTUP SEBELUM SATU BARIS KODE DITULIS (semua terukur pada 679 prompt produksi nyata):**
  - **(1) Penyaring naif membunuh produksi sah.** Daftar kata-benda (mushaf/Qur'an/kaligrafi) memblokir **8** produksi SAH; versi "berbasis niat" pertama masih memblokir **3** — ketiganya sah (halaman masjid *"melambangkan perjalanan Nabi Muhammad"* · mushaf *"perwujudan wahyu"* · timbangan *"merenungkan mukjizat"*). Rancangan final **bertingkat**: BLOKIR hanya niat tak terbantahkan, **KUATKAN** bila nama hanya konteks ⇒ **0 dari 679 diblokir**, 10/10 uji tandingan benar.
  - **(2) Patri dimakan pemotong prompt.** Cloudflare memotong keras di 2.048 huruf; patri di akhir = korban pertama. Terukur **12 dari 679 (2%)** melewati batas. `potong_aman` mengorbankan rincian adegan, **tidak pernah** patri. Batas panjang kini dari **DATA** (`ai_models.default_params.prompt_max_chars`) ⇒ vendor baru cukup mendeklarasikannya.
  - **(3) Penjaga hampir memblokir kalimatnya sendiri** — teks patri memuat *"depict … the Prophet Muhammad"*; dibuang dulu sebelum diperiksa.
- **DUA KEBOCORAN DITUTUP:** larangan gambar tenant **diabaikan total oleh FLUX** (6/11 channel) → kini dilipat ke prompt positif di corong · larangan narasi tenant **bisa kalah** (retry habis → naskah pelanggar dipakai) → kini **penghenti** (terukur 0 dari 127 produksi terdampak).
- **GAYA VISUAL KE DNA:** kata "photorealistic" dipatri di **6 titik** → `visual_style.render_style`. Bawaan membuat teks prompt **47 niche SAMA PERSIS termasuk kapitalisasi**. Ini yang membuat niche bergaya animasi 3D mungkin.
- **BUKTI:** 23 uji baru (`tests/test_patri_larangan.py`) · **4 sabotase dibuktikan merah** (patri dicabut dari corong · pemotong Cloudflare dibutakan · penyaring dilemahkan jadi daftar kata · penghenti narasi dicabut). Suite **968 → 991**, nol regresi. `tsc` FE lulus. **Nol migrasi DB, nol perubahan layar.**
- **CACAT SAYA SENDIRI YANG IKUT DITANGKAP SUITE:** berkas uji baru mencemari uji lain (mendaftarkan transport palsu ke daftar KELAS tanpa mengembalikannya) → uji penggolongan galat per-transport merah padahal kodenya sehat. Ditutup dengan pemulihan di `tearDown`/`addCleanup`.
- **BATAS YANG DIAKUI TERANG:** (a) **logo yang diunggah tenant** tidak melewati pintu mana pun — bukan buatan mesin ⇒ tanggung jawab tenant lewat disclaimer; menutupnya = pekerjaan tersendiri · (b) patri menang atas **setelan** apa pun, **tidak** menjamin mesin gambar pihak ketiga tak keliru · (c) prompt di channel tanpa kanal larangan **bertambah satu kalimat** ⇒ pergeseran gaya halus **hanya bisa dinilai dari video uji**.
- **DONE-BILA:** (1) patri sampai di setiap transport + vendor yang belum ada ✅ · (2) nol produksi sah diblokir ✅ · (3) larangan tenant benar-benar berlaku ✅ · (4) gaya jadi milik niche tanpa mengubah 47 niche ✅ · (5) ⏳ **deploy** (gerbang izin terpisah) · (6) ⏳ **video uji** di channel berkanal-larangan & tanpa kanal-larangan, dinilai owner.

### [B29] REM YANG DILUMPUHKAN → BANJIR KABAR KE TENANT — 🟢 DICABUT + 6 DRIFT DOKUMEN DIBETULKAN (2026-08-14) · ⏳ 4 butir menunggu ketok owner
- **SPEC/SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8k`** (+ koreksi §7 · §8j · §9a · §10 · §11).
- **DILAPORKAN OWNER dari keluhan tenant** — *"sebelumnya sudah berjalan baik, 3 kali gagal langsung kena rem; tapi setelah anda bug fixing, malah timbul bug baru"*. Benar seluruhnya. **Ini bug yang Claude tanam sendiri saat memperbaiki bug lain.**
- **AKARNYA, satu kalimat:** rem itu mengerjakan **DUA** hal — menghentikan **CHANNEL** *dan* menghentikan **PERCOBAAN**. Perbaikan 12-Agu hanya mengincar yang pertama; yang kedua ikut hilang, dan **tak ada apa pun di aplikasi ini yang menggantikannya** (nol penahan laju · nol jeda · nol batas percobaan per jam).
- **TERUKUR (production_runs + worker.log VPS), dua channel tenant yang SAMA, dua hari berurutan:** 13-Agu Thetangga Property **30 kegagalan / 8 menit** (29 jatah-harian) · 14-Agu BISIK NUSANTARA **23 / 11 menit** (21 jatah-harian) — rem **tidak menyala** di keduanya. Laju: satu produksi baru tiap **±14 detik** ⇒ **±257 kabar gagal per JAM** ke Telegram tenant; tiap percobaan menembak penyedia **3×**. Dari 53 kegagalan `rate_limit` sepanjang umur aplikasi, **50 (94%) di dua hari itu**. Rem terakhir menyala **3-Agu**; sejak perbaikan naik (12-Agu 19:54) **tak sekali pun**. **Yang menghentikannya: tenant mematikan channelnya sendiri.**
- **KENAPA 880 UJI HIJAU TAK MENANGKAPNYA:** semua uji rem memeriksa **angka di dalam mesin** (`streak == 3`) — dan angka itu MEMANG benar (21 dilewati + 2 dihitung = 2 dari ambang 3). Yang salah adalah **akibatnya**. Commit-nya bahkan menulis *"jangkauan terbukti sempit — dipakai di SATU tempat untuk SATU keputusan"*: benar secara harfiah, menyesatkan secara akibat — **titik panggil** dihitung, **akibat** tidak.
- **PERBAIKAN:** pengecualian dicabut → setiap kegagalan dihitung kembali, apa pun kelasnya (perilaku sebelum 12-Agu, yang owner sendiri sebut "sudah berjalan baik"). **Aman, bukan sekadar mundur:** mudarat yang dikejar 12-Agu (channel menganggur lama) akarnya sudah ditutup 3-Agu oleh **[B25]** — kelas error TERSIMPAN saat rem menyala ⇒ panel per-KELAS + tombol *Pulihkan produksi* + Telegram membedakan pulih-sendiri. Bang Us-Dat menganggur 11 hari karena kelasnya `unknown` sehingga panelnya **bisu**, bukan karena rem menyala.
- **DIUKUR SEBELUM DIKIRIM (bukan sesudah):** ke-12 channel diperiksa satu per satu dengan dua aturan hitung pada data produksi ⇒ **nol channel aktif yang langsung direm** saat perbaikan naik.
- **6 DRIFT DOKUMEN SSOT DIBETULKAN** (semuanya diverifikasi dengan menjalankan kode, bukan membaca): §1 & §3 menjanjikan *"toleransi normal → rem di kegagalan ke-3"* untuk perilaku yang sudah tidak ada · §8j memuat **dua jawaban berlawanan** tentang Cloudflare `3036` berjarak 16 baris · tabel §9a **terbelah** (catatan 12-Agu disisipkan antara baris judul & pemisahnya ⇒ tabelnya berhenti ter-render) · angka bukti §7 basi (9 & 12 → nyata 20 & 35) · bukti produksi masih `rate_limit` 3× (nyata **53×**) · celah §8k belum tercatat. `MEMORY.md` ikut dikoreksi (2 catatan basi yang akan membuat sesi berikutnya mengerjakan ulang yang sudah ada).
- **PENJAGA BARU — menyerang sebab kebocorannya, bukan gejalanya:** `tests/test_rem_tak_boleh_lumpuh.py` (**PERILAKU**: berapa kali produksi di-submit · berapa kabar terkirim · apakah mesin berhenti sendiri; ditulis atas SELURUH anggota `ErrorClass` ⇒ kelas baru ikut terjaga tanpa uji disunting) + 3 penjaga dokumen di `test_ssot_error_mgmt.py`: **kolom "Sikap" §1 dibandingkan dengan PERILAKU mesin** (bukan dengan teks) · **struktur tabel utuh** · **angka §7 dihitung dari suite**, bukan diketik tangan.
- **BUKTI MERAH LEBIH DULU:** pengecualian 12-Agu dihidupkan kembali → **14 uji gagal**; dua penjaga dokumen merah pada dokumen apa adanya, hijau setelah dibetulkan. Suite **991 → 1002 lulus, nol regresi**. **Nol migrasi DB, nol perubahan layar.**
- **🟢 FASE 1 SELESAI 14-Agu — TIGA CELAH SISANYA IKUT DITUTUP, semuanya dibuat GENERIK.** Ketetapan owner hari itu: *"pastikan setiap perbaikan sedapat mungkin bersifat GENERIK, karena AI model dan AI vendor akan terus bertambah"* — dan prinsip itu diterapkan pada **JALUR** juga, bukan hanya vendor.
  - **`seed` → uang tenant berhenti terbakar.** `seed` **tidak ada di skema resmi** Cloudflare FLUX schnell (hanya `prompt`+`steps`, dibaca 14-Agu). Kita mengirimnya; CF menerimanya diam-diam berbulan-bulan lalu mulai memvalidasi skema: **1× 8-Agu · 1× 11-Agu · 10× 13-Agu · 22× 14-Agu** (37×, tren NAIK). Satu adegan gagal menggagalkan SELURUH produksi (§8i) ⇒ yang hangus pekerjaan yang hampir jadi: **248/442/341 detik · 15/34/26 panggilan LLM · 4/6/5 gambar ⇒ ±$0,068 uang TENANT dalam 2 hari, untuk kesalahan KITA.** Rem "jangan bakar duit tenant" (ketok owner 17/18-Jul) **masih hidup & tak disentuh**, tapi secara struktur tak bisa menangkap ini — sebabnya bukan "kredit habis". **Perbaikan:** seed dikirim HANYA bila skema model menyatakan menerimanya (`ai_models.default_params.supports_seed`); **default = TIDAK kirim ⇒ vendor/model BARU otomatis aman tanpa satu baris kode.** `fal flux/dev` ditandai mendukung (skema resminya memuat `seed`, dibaca 14-Agu) ⇒ Diversity §9.1 utuh di sana. **Nol migrasi.**
  - **Salah kita berhenti ditimpakan ke tenant — lintas-vendor.** Jaring `_RX_PARAM_CACAT` di jalur **generik**, bukan di tabel Cloudflare: penolakan atas PARAMETER ⇒ `milik_kita=True` di vendor mana pun, **termasuk yang belum ada** (alasannya semantik: parameter hanya bisa datang dari kami). **Sengaja sempit** — pola lebar (*"not allowed"*/*"bad input"*/*"invalid"*) diuji pada seluruh pesan vendor nyata dan **DITOLAK** karena menangkap *"API key invalid"*; salah-alamat ke arah sebaliknya sama merusaknya. Kelas tetap `unknown` ⇒ **nol perubahan perilaku rem**.
  - **migr 0198 — menyalakan channel menutup periode kegagalan + jam perubahan tercatat.** Dipasang sebagai **trigger DB, bukan 2 baris di layar**: layar hanya menutup jalur yang ada HARI INI, dan justru begitulah cacat ini lahir (0197 menutup 3 jalur, melewatkan saklar aktif). **Tidak menyentuh `production_paused`** ⇒ channel yang direm tetap direm, [B25] utuh. **Bukti runtime pada baris NYATA di dalam transaksi yang DIBATALKAN ⇒ nol data tenant berubah:** matikan → titik pemulihan tidak bergeser · nyalakan → bergeser · update biasa → tidak · kolom rem tak tersentuh · urutan trigger terverifikasi (gerbang aktivasi → 0198 → penjaga rem).
  - **Butir 8 rencana (pemulihan data 2 channel) jadi TIDAK PERLU** — dengan 0198, BISIK & Thetangga sembuh **sendiri** saat tenantnya menyalakan channel. Nol data tenant kami sentuh.
  - **Bukti:** `tests/test_parameter_kita_tak_ditimpakan_tenant.py` (10 uji, **merah dibuktikan dua arah: 8 & 10 gagal**) + penjaga trigger di `tests/test_migrasi_selaras_db.py`. Suite **1002 → 1014 lulus, nol regresi**.
- **⏳ SATU-SATUNYA YANG MENUNGGU KETOK OWNER (§0.6 perilaku-saat-gagal):** **jeda sementara** untuk sebab yang pulih sendiri — mesin berhenti mencoba lalu jalan lagi otomatis, **satu** kabar saja, sehingga channel tidak menganggur menunggu tombol. Ini satu-satunya butir yang memilih **angka & kebijakan baru**, jadi bukan keputusan Claude. Rekomendasi yang sudah diajukan: jeda bertingkat **1 jam → 4 jam → 12 jam** dihitung dari hitungan kegagalan yang sudah ada (nol kolom baru, nol pembacaan teks) · **satu** kabar saat jeda mulai · tombol Uji ikut ditahan (menekannya saat jatah habis dijamin gagal + membakar sisa jatah tenant). Konsekuensi yang harus diketok: agar channel benar-benar tidak menganggur, rem **tidak** menyala untuk kelas pulih-sendiri — dengan jeda sebagai penggantinya, dan penjaga `test_rem_tak_boleh_lumpuh.py` yang mengukur hasilnya (±5 kabar/hari, bukan 257/jam).
- **DONE-BILA:** (1) banjir tertutup — mesin berhenti sendiri di ambang ✅ · (2) nol channel aktif jadi korban pencabutan ✅ (diukur) · (3) dokumen SSOT berhenti menyatakan perilaku yang tak ada ✅ · (4) penjaga berbasis PERILAKU + 3 penjaga dokumen, merah dibuktikan ✅ · (5) uang tenant berhenti terbakar + salah kita berhenti ditimpakan, keduanya GENERIK ✅ · (6) menyalakan channel tak lagi mengerem seketika ✅ (migr 0198, bukti runtime) · (7) ⏳ **deploy** · (8) ⏳ **jeda sementara** — menunggu ketok owner.

### [B30] MESIN MATI MENDADAK (SIGSEGV) — 🟢 AKAR DITEMUKAN & DITUTUP (2026-08-15)
- **SPEC/SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8L`.**
- **PENYAKIT LAMA, bukan kerusakan baru:** `systemd` mencatat **6 SEGV sejak 1-Agu**. Tiap kali, produksi yang sedang berjalan **hilang tanpa jejak** — proses mati sebelum sempat menulis `production_runs`, jadi bagi sistem kita produksi itu tak pernah ada dan tenant tak dikabari. Bentuk kerugian yang sama dengan video `xa3Rbi-SbXM` (12-Agu). Catatan resmi sebelumnya: *"sebab belum diketahui"*.
- **YANG MEMBUATNYA TERLIHAT:** perekam kematian ([B26]-D, naik 13-Agu) **berbicara untuk pertama kalinya** 14-Agu 23:00:52 — alat yang dipasang kemarin langsung membayar dirinya sendiri.
- **🎯 AKARNYA — CACAT PENGUMPUL SAMPAH (GC) PADA `Python 3.11.0rc1`, dibongkar dari INSTRUKSI MESIN.** Ketiga titik crash memuat pola identik: `and $0xfffffffffffffffc,%rdx` (buang 2 bit penanda) → `mov %rcx,(%rdx)` ← **MATI** → `and $0x3` (pasang ulang penanda). Pola **masker `~3` + dua bit penanda** = tanda tangan `_PyGCHead_SET_NEXT/SET_PREV`, yaitu **pembaruan rantai-ganda milik pengumpul sampah CPython**. Alamat yang ditulisi bernilai **NOL** ⇒ **rantai objek GC-nya RUSAK**. Dibongkar dari biner rc1 ASLI yang diunduh ulang — cap waktunya **identik sampai detik** dengan yang tercatat di laporan crash (`1660298534` = 12-Agu-2022 17:02:14). **Dan cacat itu terdokumentasi resmi:** CPython 3.11 punya beberapa cacat korupsi memori di GC yang **baru diperbaiki pada 3.11.2 & 3.11.3** (**gh-101975** *"corruption on garbage collection"* · **gh-102397** *"segfault from race condition … during garbage collection"* · crash GC subinterpreter di 3.11.2). **Mesin kita di `3.11.0rc1` — keluar SEBELUM 3.11.0 final, jadi tak memuat SATU PUN perbaikan itu.** `dmesg` merekam **11 crash antara 3-Jul dan 13-Agu**: alamat kesalahan **`0` (5×)** · `1` · `ffffffffffffffff` · acak · satu *general protection fault* — dan **10 alamat instruksi BERBEDA, semuanya di dalam biner `python3.11` sendiri**. Penunjuk kosong/liar + titik crash berlainan = **kerusakan memori di penerjemah**, bukan bug satu jalur kode. **Penyebab lain disingkirkan dengan pemeriksaan:** bukan tumpukan jebol (alamat kesalahan jauh dari penunjuk tumpukan; pembangunan skema butuh **64–96 KB**, thread produksi punya **8 MB** = 128× lebih) · bukan perangkat keras (**nol** galat memori kernel, **nol** proses selain python yang crash di server yang sama) · bukan kehabisan memori (**nol** catatan OOM).
- **PERBAIKAN AKAR: penerjemah dimutakhirkan DI TEMPAT** — `python3.11` sistem dari **3.11.0rc1 → 3.11.15 stabil**, lewat paket yang memang sudah ditunjuk `venv` (`venv/bin/python3.11 → /usr/bin/python3.11`). **Nol lingkungan baru · nol jalur baru · nol perubahan kode.** Diverifikasi: **24 pustaka + 18 modul mesin termuat sempurna**, paket terkompilasi utuh (wheel `cp311` sekompatibel di seluruh 3.11.x).
- **LAPIS PERTAHANAN (bukan perbaikan akar — jangan salah baca):** skema SDK dipanaskan di **alur UTAMA saat start** (1.049 model, 2,4 detik) ⇒ pembangunan skema tak lagi terjadi di dalam thread produksi. Berdiri sendiri, nol perubahan perilaku, gagal-terbuka. **GENERIK** atas ketetapan owner: yang didaftar **awalan modul** (`openai`·`anthropic`), bukan nama kelas ⇒ menambah vendor = **satu kata**.
- **🔬 CARA TEMUAN INI DIDAPAT:** rekaman memori **387 MB** dibongkar (`apport-unpack`), keadaan prosesor **ke-14 thread** dibaca langsung dari catatan ELF, `rip` dipetakan ke pustaka lewat `ProcMaps`, lalu alamat crash diterjemahkan jadi **instruksi mesin** dengan `objdump` pada biner rc1 asli. **Temuan yang membalik pembacaan awal:** `rip` crash 14-Agu jatuh di **`pthread_kill` (libc)** — itu **BUKAN** titik crash, melainkan tempat perekam kematian **melempar ULANG** sinyalnya. Karena perekam baru naik 13-Agu, **hanya crash SEBELUM 13-Agu yang alamatnya asli** — dan alamat itulah yang dibongkar.
- **⚠️ EMPAT DUGAAN SAYA GUGUR SEBELUM YANG BENAR KETEMU — semuanya DIUJI, bukan ditinggalkan:** *"tumpukan Python jebol"* (rekaman cuma **57 frame**, butuh ribuan) · *"tumpukan C jebol"* (butuh 64–96 KB, tersedia 8 MB) · *"Python 3.11.0 saja"* (**dipasang 3.11.0 asli di komputer lokal, jalur crash sama → selamat**) · *"versi pydantic"* (**diuji dengan versi PERSIS server 2.13.4 → selamat**). **Yang menuntun ke jawaban bukan reproduksi, melainkan catatan KERNEL — lapis yang sejak awal menyimpan jawabannya dan paling belakangan saya baca. Pelajaran mengikat: baca lapis TERDALAM lebih dulu, jangan menebak dari lapis aplikasi.**
- **BUKTI:** `tests/test_mesin_tak_mati_mendadak.py` (9 uji) — **reproduksi crash dua arah** (tanpa pemanasan proses dibunuh sinyal · dengan pemanasan selesai wajar) · uji inti memeriksa **perilaku akhir** (mengurai balasan nyata tak lagi memanggil `model_rebuild`) · urutan dibaca dari **pohon sintaks**, bukan pencarian teks. **Merah dibuktikan lebih dulu: 6 & 2 gagal.** Suite **1014 → 1023**, nol regresi. **Nol migrasi DB, nol perubahan layar.**
- **DONE-BILA:** (1) akar terbukti, bukan ditebak ✅ · (2) pemanasan menutup SELURUH model, dibuktikan perilaku ✅ · (3) penerjemah stabil, pustaka terverifikasi ✅ · (4) penjaga permanen + merah dibuktikan ✅ · (5) ⏳ **deploy + restart** (mesin baru memakai 3.11.15 sesudah restart) · (6) ⏳ pantau: nol SEGV baru (garis dasar 6 sejak 1-Agu).

### [B31] DUA CACAT "KETERANGAN DITANGKAP LALU DIBUANG" — 🟢 SELESAI (2026-08-15)
- **SSOT = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8f` + `§8m`.** Nol migrasi · nol tabel · nol kolom · nol perubahan perilaku mesin · **nol jalur baru** (keduanya menyambung ujung yang sudah menganga).
- **⛔ SATU AKAR, TIGA KALI — ini temuan terpentingnya, bukan dua bug terpisah:** keterangan **DITANGKAP lalu DIBUANG** sebelum sampai ke siapa pun. (1) golongan galat ada di `production_runs`, layar tak membacanya · (2) sebab frame pembuka ada di memori, tak ada yang menyimpan · (3) pesan MENTAH penyedia ada di dalam galat, ditimpa pesan kita saat menyimpan (§8k). **MENANGKAP ≠ MENYAMPAIKAN.**
- **§8f — penurunan mutu berhenti senyap.** Frame pembuka gagal ⇒ video tetap terbit dengan pembuka lebih lemah, **tanpa seorang pun tahu**. Nilainya SUDAH ditangkap sejak 5-Agu lalu dimasukkan `result["steps"]` — tapi `steps` **tak pernah ditulis ke tabel mana pun**, dan komentar di `visual_assembler.py` **mengakuinya sendiri sejak 8-Agu**. Terukur: **85 run sejak 8-Agu, NOL tersimpan.** Kini `producer._mutu_fields()` menyambungkannya ke `run_metadata` lewat jalur simpan yang SUDAH terbukti (`_cost_fields`), pada **KEDUA** jalur produksi. **Yang TIDAK diubah: video tetap terbit** — menghentikan produksi = keputusan produk (§0.6), yang §0.6 larang adalah *senyap*-nya. **Frekuensinya sudah turun sendiri:** dari 13 kegagalan (653 percobaan), **3 adalah bug `seed` KITA** yang ditutup 14-Agu, 2 lagi bug kita di Juni (nihil sejak).
- **§8m — golongan kosong melumpuhkan panel.** migr 0196 hanya MENAMBAH kolom; **nol pengisian baris lama** (`UPDATE`=0), dan komentar kolomnya **menuliskan sendiri** *"NULL = rem menyala sebelum kolom ini ada"* — disadari, ditulis, tak pernah ditangani. Bukan sekadar pesan tumpul: `ujiJalurYangBenar = bisaUji && r.pulihSendiri === false` ⇒ kosong **mengubah jalur pemulihan yang disarankan** ⇒ tenant diarahkan menekan "Pulihkan" padahal harus memperbaiki dulu = jebakan insiden 3-Agu. **Terukur: 2 channel tenant BERBAYAR diam 13 & 24 hari** membaca *"belum bisa memastikan penyebabnya"*, padahal golongannya tersimpan rapi di catatan produksi mereka. Kini layar mengambil golongan **cadangan dari kegagalan terakhir** — sumbernya `production_runs`, tabel yang SAMA dengan yang dibaca rem di mesin.
- **BUKTI pada data NYATA + batas jujurnya:** **Abyss ID** berubah dari *"hubungi dukungan"* → **"Ganti model"** ✅. **Bang Us-Dat TIDAK berubah** — golongan kegagalan terakhirnya memang `unknown`, jadi mesin sungguh tak tahu dan layar tak boleh mengarang. **Menolong 1 dari 2**, disebut apa adanya.
- **PENJAGA + merah dibuktikan:** `tests/test_penurunan_mutu_tak_senyap.py` (6 uji; sambungan dicabut dari satu jalur ⇒ merah) · `tests/test_pemulihan_tak_menjebak.py` +1 (cadangan dicabut ⇒ merah). Uji lama yang mengikat **teks harfiah** titik panggil **diperketat ke kontraknya** — niat aslinya utuh, berhenti mengunci susunan huruf (bukan dilonggarkan agar hijau).
- **DIAKUI, tidak diperluas:** layar admin memakai kolom yang sama & menampilkan `—` untuk rem lama — informatif saja, tak menyesatkan siapa pun, jadi sengaja tak disentuh.

### [B33] GROQ MEMENSIUNKAN 2 MODEL · TENANT DISURUH "PILIH MODEL LAIN" TANPA DIBERI TAHU YANG MANA — 🟢 SELESAI (2026-08-17)
- **Pemicu = keluhan tenant BISIK NUSANTARA**, bukan temuan internal. Produksi berhenti; pesannya *"Model AI ini sudah tidak tersedia… Pilih model lain di setting channel."* — **tanpa menyebut model yang mana.** Satu channel memakai TIGA slot AI (naskah · suara · gambar) ⇒ anjurannya mustahil dikerjakan.
- **⛔ AKAR = kelas `[B31]` TERULANG: keterangan DITANGKAP lalu DIBUANG.** Vendor menyebutnya tepat — *`The model 'llama-3.3-70b-versatile' does not exist`* (log `direct-61d31ce5`, 17-Agu 13:21). Kita memegang **ketiganya** (penyedia `Groq` · slot penulis naskah · nama model), lalu membuang semuanya. Janggalnya **asimetris**: dari 4 golongan di tabel pesan jalur naskah, TIGA sudah menyebut slotnya; hanya golongan ini yang tidak — justru satu-satunya yang tindakannya *"ganti model"*. Sejalan ketetapan owner 08-Agu (*pesan penyedia jangan diterjemahkan*).
- **PERBAIKAN 1 — identitas ikut, GENERIK.** `_anjuran` menerima sisipan identitas → *"Model AI penulis naskah **'llama-3.3-70b-versatile' (Groq)** sudah tidak tersedia…"*. Nol jalur baru (tabel & penilai yang sudah ada) · tanda tangan 1-argumen tetap sah · penampung tak terisi tak bocor ke mata tenant · berlaku otomatis untuk vendor/model yang **belum ada** (terbukti: OpenAI · Gemini · fal). Satu titik perbaikan ⇒ **layar tenant (kotak "Alasan gagal") + Telegram** ikut benar, karena keduanya membaca `production_runs.error_message` yang sama.
- **PERBAIKAN 2 — 2 model mati dimatikan di katalog.** Uji nyata: `llama-3.3-70b-versatile` **MATI** · `llama-3.1-8b-instant` **MATI** · `openai-gpt-oss-120b` & `-20b` HIDUP. Keduanya masih `is_active=TRUE` ⇒ **tenant baru masih bisa memilihnya** dan menabrak dinding yang sama. Setelah dimatikan, gerbang kesiapan memblokir **6 channel** dengan alasan `model naskah` **SEBELUM membakar produksi** (dibuktikan lewat `channel_missing_by_id`) — perilaku yang memang dirancang untuk model nonaktif, bukan jalur baru.
- **KENAPA BARU GAGAL HARI INI:** dokumen resmi Groq (`console.groq.com/docs/deprecations`, dibaca 17-Agu) — keduanya dipensiunkan **16-Agu 2026**, diumumkan lewat surel **17-Jun**. Cocok dengan data: BISIK NUSANTARA **sukses 16-Agu 12:57**, gagal 17-Agu 12:00. **Kita punya 2 bulan peringatan dan melewatkannya** — lihat celah terbuka di bawah.
- **PENGGANTI — anjuran resmi Groq TIDAK semuanya cocok (mandat owner: "parameter format yang sesuai").** Diuji dengan bentuk permintaan PRODUKSI (system+user · temperature · max_tokens · mode JSON):
  | Model | Hasil | Catatan |
  |---|---|---|
  | `openai/gpt-oss-120b` | ✅ 4,3 dtk · JSON 7/7 kunci · 111 kata | **pengganti `llama-3.3-70b`** — sudah aktif di katalog |
  | `openai/gpt-oss-20b` | ✅ 2,9 dtk · JSON 7/7 kunci · 114 kata | **pengganti `llama-3.1-8b`** — sudah aktif di katalog |
  | `qwen/qwen3.6-27b` | ❌ **400 `json_validate_failed`** | **DIANJURKAN GROQ tapi TAK LAYAK di sini** — model BERNALAR: keluarannya dibuka `<think>` ⇒ mode JSON gugur, `failed_generation` kosong. Kelas SAMA dgn `gpt-5-nano` yang sudah ditolak 28-Jul. **Jangan didaftarkan.** |
  | `groq/compound-mini` | ✅ 6,5 dtk · JSON 7/7 kunci | Sistem AGENTIK (pakai alat/web), bukan model murni — perilaku & biaya kurang terduga. **Tidak dianjurkan** untuk naskah. |
  ⇒ **Nol model baru perlu didaftarkan**: kedua pengganti sudah ada, aktif, dan lulus uji.
- **PENJAGA + merah dibuktikan:** `tests/test_galat_menyebut_model_yang_harus_diganti.py` (11 uji; **8 merah** di kode lama). Penjaga anti-drift `test_ssot_error_mgmt` menangkap berkas baru yang belum tercatat di `AI_ERROR_MGMT §7` ⇒ **dokumen diperbaiki, penjaga TIDAK dilemahkan.** **1.138 uji hijau.**
- **🔒 MENUNGGU KETOK OWNER (sengaja tak dikerjakan):** **6 channel masih menunjuk model mati** (BISIK NUSANTARA · Bang Us-Dat *(keduanya sudah berhenti)* · JaydenSaverio · RETRO REWIND GARAGE · BJ Yusroon · Thetangga Property *(nonaktif)*). Mengalihkannya = menyentuh **setelan milik tenant** ⇒ keputusan owner, bukan keputusan saya.
- **🔴 CELAH TERBUKA — belum ada ketokan:** **tak ada apa pun di sistem yang memeriksa ulang apakah model katalog masih hidup di vendornya.** Stempel audit `llama-3.3-70b` masih *"LULUS 20-Jul"* — benar hari itu, basi sejak 16-Agu. Vendor akan terus memensiunkan model; tanpa pemeriksaan berkala, tenant selalu jadi yang pertama tahu.

### [B41] SAYA MENANAM HARDCODE DI DALAM PERBAIKAN SAYA SENDIRI — 🟢 SELESAI (2026-08-20)
- **Ditemukan owner:** *"aplikasi ini anda bangun full configuration, minim hardcode, semuanya bisa diadjust lewat database (admin panel), ini rancangan anda, tapi anda rusak rancangan anda sendiri."*
- **BENAR, dan waktunya memberatkan:** saya menanam dua angka bisnis sebagai literal (`4000`, `2000`) di dalam perbaikan `[B35]` — **beberapa jam setelah saya sendiri mengutip aturan** *"nilai bisnis dari DB/config, nol literal di kode"* pada sesi yang sama.
- **KENAPA MERUGIKAN, bukan sekadar tidak rapi:** angka itu menentukan seberapa jauh mesin menaikkan jatah token sebelum menyerah. Vendor & model berganti generasi terus — **2× dalam 3 hari** (Groq memensiunkan 2 model 16-Agu; Google menutup model untuk akun baru). Selama literal, owner **tak bisa menyetelnya sendiri**: tiap penyesuaian menuntut sunting kode + deploy.
- **PERBAIKAN:** kedua angka pindah ke `app_config` — mekanisme yang **sudah ada** (`get_int`, cache, fail-soft), tempat 30+ kenop bisnis lain sudah tinggal. Kunci: `llm_jatah_token_batas_atas` (4000) · `llm_jatah_token_kenaikan_min` (2000), keduanya **berketerangan lengkap** untuk admin, memuat angka terukur dan peringatan "Groq MENOLAK 8000". Batas per-model (`ai_models.default_params.max_output_tokens`) tetap menang; angka global jadi cadangannya. **Cadangan bernama tetap ada** di kode: gangguan DB tak boleh melumpuhkan produksi. Dibuktikan terbaca: `4000` & `2000` dari DB.
- **⚠️ UJI SAYA SALAH LAGI (ketiga kali hari ini), DIBETULKAN:** versi pertama menuntut **angka MENTAH** sebagai argumen cadangan — padahal cadangan **bernama & berketerangan** justru lebih baik. Uji harfiah = uji palsu ⇒ diperketat ke **kontraknya**: cadangan ada · bernilai angka · pembacaannya dibungkus penanganan galat.
- **PENJAGA:** `tests/test_jatah_token_dari_database.py` (3 uji, **3 merah dibuktikan dulu**) — mengikat pembacaan dari `app_config`, keberadaan kenop + keterangannya di DB, dan kewajaran angkanya terhadap batas terukur vendor (≥2500 karena jawaban sah ±1.280 token · ≤6000 karena Groq menolak 8000).
- **1.169 uji hijau.** Nol setelan tenant disentuh. ⏳ menunggu izin deploy (perubahan `app_config` sudah berlaku; yang menunggu = kode pembacanya).

### [B40] SAYA MERUSAK RANCANGAN 1-AGU DENGAN ANGKA BUATAN TANGAN — 8 PRODUKSI TENANT TERBUANG — 🟢 DIPERBAIKI (2026-08-19)
- **Ditemukan owner** lewat pertanyaan *"mengapa tessartea banyak konten yang terkena qc_failed"*. Bukan temuan internal.
- **KERUSAKAN TERUKUR: 8 produksi terbuang · $2,30 ≈ Rp 37.956 uang TENANT**, seluruhnya sejak suara Gemini dinyalakan 18-Agu 13:00. Menimpa **4 channel dari 3 tenant** (BJ Yusroon · BISIK NUSANTARA · PENJAGA DAKWAH · Thetangga Property). **8 dari 8** berbunyi *"kependekan"*, **nol** "kepanjangan" — satu arah, jadi sebabnya sistematis, bukan kebetulan.
- **⛔ AKAR: SAYA MELANGGAR RANCANGAN SAYA SENDIRI.** `pause_probe.py` (1-Agu) menuliskan pelajarannya hitam di atas putih: *"angka yang tampak masuk akal tapi salah"*, dan mensyaratkan **dua** cara sah — alat ukur `scripts/ukur_jeda_suara.py` **atau** kalibrasi dari sampel produksi. **Saya memakai cara ketiga yang tidak ada dalam rancangan: SATU teks 32 kata**, lalu memasang hasilnya ke katalog (Kore 1,93 · Aoede 2,05 · pace dasar 1,91). Alatnya sudah ada di repo; saya tidak membukanya. Dokumen itu bahkan sudah menghitung akibatnya: *"pada naskah 90 dtk dengan 25 koma, selisih 0,17 dtk/koma = 4,3 detik — cukup untuk melempar video keluar batas sah."*
- **RANTAI KERUSAKAN (terukur pada produksi nyata 19-Agu):** angka dipakai vs nyata → Kore **1,93 vs 2,38 (+23%)** · Aoede **2,05 vs 2,67 (+30%)** · 2,05 vs 2,34 (+14%) · 2,05 vs 2,45 (+20%). Mesin menyangka suara LAMBAT ⇒ resep menuntut lebih SEDIKIT kata (preset 90: 181–207 kata, seharusnya ±214) ⇒ suara yang sebenarnya CEPAT selesai lebih awal ⇒ video kependekan ⇒ **QC menolak**. Satu run BISIK: naskah 156 kata → **3 putaran refit terbakar** mentok di 75s → audio 72,3s vs target 86,5s → ditolak.
- **PERBAIKAN — memakai sumber yang rancangan 1-Agu tetapkan, bukan tangan saya lagi:** angka diambil dari **`tts_delivery_samples`, sampel produksi yang mesin kumpulkan sendiri** (Aoede 8 · Kore 3). Hasil: pace **dasar** mesin Gemini **1,91 → 2,59** (median 11 produksi) · **Kore 2,38** · **Aoede 2,66** · **Puck & Charon DIKOSONGKAN** (nol sampel ⇒ ikut pace dasar terukur, **bukan angka karangan saya**). Dibuktikan mesin memuatnya: `voice_delivery_wps = 2.38`.
- **PENJAGA + merah dibuktikan:** `tests/test_pace_suara_selaras_produksi.py` (2 uji; **merah** pada angka lama). Mengikat angka katalog **dan** pace dasar mesin ke median sampel produksi (toleransi ±15%, min 3 sampel). ⇒ **kelas kesalahan ini tak bisa saya ulangi tanpa ditolak mesin.**
- **⚠️ UJI SAYA SENDIRI SALAH LAGI, DIBETULKAN:** uji kedua versi pertama menuduh *"suara tanpa angka = cacat"* — padahal suara jatuh ke pace DASAR mesin itu **RANCANGAN yang sah** (banyak suara lama sengaja begitu). Uji yang menuduh rancangan = uji palsu ⇒ diganti menjadi mengikat **pace dasar** itu sendiri, yang justru diwarisi setiap suara baru.
- **BELUM DIKERJAKAN, disebut terang:** **Puck & Charon belum diukur sendiri** — keduanya kini mewarisi pace dasar dari suara LAIN. Cara sah menurut rancangan 1-Agu = jalankan `scripts/ukur_jeda_suara.py` (memakai kredit vendor) atau tunggu 14 sampel produksi. **Menunggu ketokan owner.**
- **KALIBRASI OTOMATIS BELUM BISA MENOLONG:** ambangnya **14 sampel** per suara; Kore 3 · Aoede 8. Jadi selama belum cukup, angka KATALOG yang menentukan — itulah kenapa angka salah saya langsung memakan produksi.
- **1.166 uji hijau.**

### [B39] DUA DUGAAN BUG YANG WAJIB DITUNTASKAN SESI BERIKUTNYA — 🔴 BELUM DIBUKTIKAN (dicatat 2026-08-19)
> **Pesan untuk sesi berikutnya:** dua butir ini **belum boleh disebut bug** sampai ujinya MERAH (aturan `PETA §4b`). Tapi keduanya juga **haram menguap**. Owner bertanya *"apakah yang anda bug sudah anda catat untuk dituntaskan di sesi berikutnya?"* — jawaban jujur saat itu: **belum**, dan inilah penutupannya. Salinan ringkasnya di `PETA_MESINVIRAL.md §3b` (dibaca owner).

**D1 — HASIL BELAJAR DIKUMPULKAN LALU TIDAK DIPAKAI** *(kandidat BUG menurut definisi owner: "data yang dikumpulkan tapi tidak digunakan")*
- **TERUKUR 19-Agu:** `channel_insights` menyimpan **10 `top_topics` + 10 `top_hooks`** per channel. Yang dikirim ke mesin AI: `top_topics[:3]` · `top_hooks[:3]` · `content_type_perf` ranked `[:4]` (`niche_selector._build_insights_block`) dan `top_hooks[:3]` lagi di `hook_optimizer._build_historical_block`. ⇒ **7 dari 10 dibuang di depan pintu.**
- **Bukti dampaknya:** RAD The Explorer **239 video** → blok wawasan **983 karakter**; BISIK **18 video** → **1.049 karakter**. Channel yang sejarahnya **13× lebih banyak** mendapat jendela LEBIH KECIL. Jendelanya tetap 3, berapa pun yang dipelajari.
- **JANGAN ULANGI KEKELIRUAN CLAUDE 18-Agu:** ia menyebut ini "improvement" (mutu kecerdasan). Menurut definisi owner 19-Agu ini **BUG**. Tapi tetap: **buktikan MERAH dulu**, jangan langsung menyunting.
- **HATI-HATI (jangan menukar bug dengan bug baru):** angka `[:3]`/`[:4]` **disengaja** — tercatat *"ringkasan SENGAJA (input LLM ringkas)"* (`channel_analyst.py:221`, divonis "BUKAN ranjau" 21-Jul). Menaikkannya membesarkan perintah ke mesin AI ⇒ bersinggungan dengan **jatah token** yang baru ditangani `[B35]`. Ukur dulu, jangan tebak.

**D2 — 80 DARI 144 KEGAGALAN PRODUKSI TANPA GOLONGAN** *(kandidat BUG: "berpotensi merusak" — rem otomatis & pesan ke tenant membaca golongan)*
- **TERUKUR 19-Agu (paginasi penuh, bukan sampel):** 144 kegagalan sepanjang riwayat; **80 bergolongan kosong/`unknown`**. Sidik jarinya: **27** tak-ada-topik · **21 gambar** · **14 suara** · **7** gerbang durasi menolak naskah · **5** rem laju vendor · **2** vendor menolak JSON · **4** lain-lain.
- **KENAPA INI BERPOTENSI MERUSAK:** golongan galat dibaca **rem otomatis** (FAST_FAIL ⇒ rem setelah 1 kegagalan) **dan** layar tenant. Golongan kosong ⇒ tenant dapat pesan tumpul, dan rem memutuskan dengan informasi yang tidak ada — kelas yang sama dengan `§8m` (2 channel berbayar diam 13 & 24 hari).
- **BELUM DITELUSURI SATU PUN.** Yang paling perlu dibedah: **gambar (21)** dan **suara (14)** — isinya belum pernah dibuka.
- **CATATAN KEJUJURAN:** angka-angka ini saya ukur 19-Agu lalu **saya tinggalkan tanpa mencatatnya** — yaitu persis pelanggaran definisi bug owner (*data dikumpulkan tapi tidak dipakai*) oleh saya sendiri, di hari definisinya diketok. Owner yang menagihnya.

### [B38] DEFINISI BUG vs IMPROVEMENT — KETOKAN OWNER 19-Agu (berlaku surut ke seluruh temuan)
- **Ketetapan owner, kata demi kata:** **BUG** = *"sesuatu yang rusak, atau berpotensi merusak, termasuk **fosil**, atau **objek pada screen yang tidak berfungsi / tidak terwiring**, **data yang dikumpulkan tapi tidak digunakan**, dan sebagainya."* · **IMPROVEMENT** = *"sesuatu yang saat ini berjalan dengan baik tapi secara mutu belum tercapai, belum memuaskan dan berpotensi ditingkatkan, termasuk **kualitas konten** (narasi, suara, gambar, video, durasi, dsb), serta yang terkait dengan **self-learning & self-improvement**."*
- **KENAPA DIKETOK:** Claude salah menggolongkan **dua kali dalam satu sesi** (menyebut kontrak rancangan "rusak"; menyebut rancangan keyakinan mesin "bug" lalu menariknya). Owner: *"anda sendiri tidak paham apa itu bedanya bug dan improvement, tapi anda mau cari bug."* Maka definisinya **milik owner**, bukan tafsiran Claude. Tercatat di `PETA_MESINVIRAL.md §4b` (dijaga `test_peta_tak_menyebut_bug_tanpa_bukti.py`).
- **UJIAN MEKANIS** (supaya penilaian Claude tak masuk hitungan): **bisa ditulis uji yang MERAH di kode sekarang ⇒ BUG. Tidak bisa ⇒ IMPROVEMENT.**
- **REKLASIFIKASI temuan 18/19-Agu menurut definisi ini:**
  | Temuan | Golongan | Dasar |
  |---|---|---|
  | Tombol mutu gambar tak berpengaruh di 9/12 channel | **BUG** | objek layar tak terwiring → `[B36]` ✅ |
  | Suara aktif pada mesin suara yang mati (fal 16-Agu · Gemini 18-Agu) | **BUG** | objek layar tak terjangkau → `[B34]` ✅ |
  | Jawaban terpotong diulang 3× sia-sia | **BUG** | rusak + merusak (uang tenant) → `[B35]` ✅ |
  | Data belajar diberi label karangan | **BUG** | data dikumpulkan lalu dipakai salah → `[B37]` ✅ |
  | **10 topik & 10 hook DIPELAJARI, hanya 3+3 dikirim ke mesin AI** | **🔴 BUG BARU — BELUM DIPERIKSA** | **"data yang dikumpulkan tapi tidak digunakan"** — 7 dari 10 dibuang di depan pintu. Sebelumnya Claude menyebutnya "improvement"; **menurut definisi owner ini BUG.** Wajib dibuktikan MERAH dulu sebelum disebut apa pun. |
  | Jumlah gambar mengikuti babak, bukan panjang tayangan | IMPROVEMENT | mutu konten (gambar) → `PETA §4c` |
  | Mesin percaya 100% pada korelasi lemah | IMPROVEMENT | self-learning → keputusan owner, belum diketok |
- **⚠️ KONSEKUENSI YANG HARUS DISEBUT:** definisi ini **memperluas** apa yang terhitung bug. "Fosil" dan "data dikumpulkan tapi tak dipakai" belum pernah disapu dengan kacamata ini. Sapuan itu **belum dikerjakan** dan **belum diketok**.

### [B37] MESIN BELAJAR DARI LABEL YANG IA KARANG SENDIRI — 🟢 SELESAI, ⏳ MENUNGGU IZIN DEPLOY (2026-08-19)
- **TERUKUR (bukan pendapat — siapa pun bisa mengulangi):** `_compute_performance_scores` menulis `avg_view_pct = ... or 0.0` ⇒ retensi yang **BELUM TERAMBIL** jadi **0,0** lalu dibobot **0,30** ⇒ video yang datanya belum turun dinilai **GAGAL TOTAL**. Bahwa itu label PALSU terbukti tanpa berdebat: video ber-`views > 0` **MUSTAHIL** retensi 0% — kalau ada yang menonton, ada durasi yang tertonton.
- **BESARNYA, apa adanya (tidak dibesar-besarkan):** hari ini **2 dari 132** video (1%) ⇒ korelasi bergeser **0,0004** — praktis nol. **TAPI** cakupan retensi per bulan terukur (paginasi penuh): **Apr 4% · Mei 0% · Jun 51% · Jul 49% · Agu 92%** ⇒ pada bulan seperti **Mei, seluruh label palsu**. Nilainya = perlindungan saat pengambilan analitik tersendat lagi (sudah 2× terjadi), bukan perbaikan angka hari ini.
- **PERBAIKAN:** degradasi **JUJUR** yang memang sudah dijanjikan docstring berkas itu — dimensi yang datanya tak ada **DIKELUARKAN**, bobot sisanya dinormalkan ulang. Baris yang datanya ADA: **skornya identik** (total bobot tetap 1,0) ⇒ nol regresi pada data sehat.
- **⚠️ DUA KALI UJI SAYA SENDIRI SALAH — dicatat karena itu bagian dari cara kerjanya, bukan aib yang disembunyikan:** (1) uji pertama lulus karena **alasan yang salah** (membandingkan retensi kosong vs 1%, yang memang beda angkanya) → diperketat; (2) premis uji berikutnya **MUSTAHIL** ("0% dengan 1.000 penonton = sungguh nol") → **ujinya yang dibetulkan, bukan kodenya yang dilonggarkan**, dan ditambah penjaga tegas: 0-ber-penonton WAJIB diperlakukan sebagai data-tak-ada, sementara retensi jelek yang MUNGKIN (1%) tetap dibedakan. Keduanya tertangkap **sebelum apa pun terpasang** — justru karena aturan "uji harus MERAH dulu": uji yang tak bisa dibuat merah **adalah** uji yang salah.
- **🔒 BUKAN BUG, KEPUTUSAN OWNER — BELUM DIKETOK:** keyakinan mesin (`alpha`) dihitung **hanya dari jumlah video**, bukan kekuatan sinyal. Terukur: pada n=132 ambang layak-percaya **±0,171**, korelasi terkuat **0,081** ⇒ **0 dari 5 layak**, tapi alpha = **1,0** (percaya penuh) dan bobot rancangan produk (0,25/0,25/0,20/0,15/0,15) tergantikan yang hampir rata (0,176×3). **Claude menyebut ini "bug" 19-Agu lalu MENARIKNYA** setelah teguran owner: *"anda yang merancang ini dengan penuh keyakinan, sekarang anda gugurkan sendiri."* **Apakah keyakinan seharusnya menakar kekuatan sinyal = keputusan owner.** Sesi berikutnya: **HARAM menyebut ini bug**; datang dengan angka, bukan keyakinan.
- **VERIFIKASI:** 5 penjaga baru (2 dibuktikan merah dulu) · **1.161 uji hijau** · baris ber-data identik.
- **⛔ TIDAK DIPASANG KE SERVER** — menunggu izin owner (§1.1).

### [B36] KENOP MUTU GAMBAR MENGELABUI 9 DARI 12 CHANNEL — 🟢 SELESAI, ⏳ MENUNGGU IZIN DEPLOY (2026-08-19)
- **Temuan owner 18-Agu, dan premisnya BENAR:** *"hemat/seimbang/terbaik bukannya tergantung model yang dipilih?"* Tiga tombol itu sebenarnya parameter milik SATU pemasok (OpenAI `quality`); mesin hanya mengirimkannya di jalur OpenAI. Untuk Cloudflare · fal · Gemini — **9 dari 12 channel** — tombolnya **DIABAIKAN sepenuhnya**. Tenant menekan "Terbaik", nol yang berubah.
- **Tuas mutu NYATA berbeda per model, dan sudah jadi DATA di katalog:** `cf-flux-schnell` steps **8** (batas maksimum Cloudflare) · fal `flux-schnell` **4** langkah · fal `flux-dev` **28** langkah · Gemini image **tak punya tuas apa pun**. ⇒ Di fal, beda "hemat" vs "terbaik" adalah **beda MODEL**. Tombol terpisah menyiratkan mutu bisa dinaikkan tanpa ganti model — tidak benar.
- **RIWAYATNYA (mata ke-3 §0 — dikutip, bukan ditebak):** tombol ini **TIDAK salah saat dibuat**. `REMEDIASI_NICHE_CHANNEL_VOICE_LLM.md`: *"kenop biaya & mode produksi milik CHANNEL, keputusan owner"* — dan saat itu katalog hanya berisi OpenAI. Yang salah: **SAYA menambah pemasok lain lalu meninggalkan tombolnya.** Maka yang diperbaiki = PENERAPANNYA, bukan rancangannya.
- **PERBAIKAN — layar saja, MESIN TIDAK DISENTUH.** Jalur produksi sudah benar sejak awal (hanya mengirim `quality` pada jalur yang menerimanya). Yang berbohong hanya LAYAR. Penandanya **DATA**: `ai_models.default_params.supports_quality_tier`, **default TIDAK** — pola sama persis `supports_seed` (ketetapan owner 14-Agu: jangan kirim parameter yang skema resmi model tak menyatakan menerimanya ⇒ **model & vendor BARU otomatis aman tanpa satu baris kode**). Ditandai pada 2 model OpenAI; 4 model lain tetap tidak mengaku.
- **TENANT TIDAK KEHILANGAN KENDALI DIAM-DIAM:** saat modelnya tak punya setelan mutu, layar berkata *"Mutu mengikuti model yang Anda pilih di atas — model ini tidak punya setelan mutu terpisah."* Menyembunyikan tombol tanpa penjelasan = memindahkan kendali tanpa memberi tahu.
- **VERIFIKASI:** 5 penjaga baru, **3 DIBUKTIKAN MERAH dulu** — termasuk satu uji yang awalnya lulus karena **alasan yang salah** (kata "dari model" kebetulan ada di tempat lain) lalu **diperketat ke kalimat yang harus benar-benar ada**, bukan dibiarkan hijau palsu. Penjaga regresi mengunci **mesin tak tersentuh** (hanya `_generate_dalle` yang mengirim setelan mutu). **1.156 uji hijau · tsc bersih · build FE sukses.**
- **⛔ TIDAK DIPASANG KE SERVER** — menunggu izin owner (§1.1). Nol setelan tenant disentuh.

### [B35] JAWABAN TERPOTONG DIULANG 3× SIA-SIA — SEPARUH PERBAIKAN 16-JUL YANG TERTINGGAL — 🟢 SELESAI, ⏳ MENUNGGU IZIN DEPLOY (2026-08-18)
- **⛔ AKAR = KARYA SAYA SENDIRI, DIPERBAIKI SEPARUH.** Mekanisme ini saya temukan & tulis sendiri di **`ede8a88` (16-Jul)**: *"model bernalar menghabiskan jatah token untuk berpikir di dalam → jawaban kosong → vonis gagal PALSU"*. Saya perbaiki **HANYA di jalur uji** (`model_tester` 16→512); **jalur produksi ditinggalkan**. Sebulan kemudian ia memakan tenant berbayar. Leluhurnya lebih tua lagi: **`b4effb3` (27-Mar)** — dua hari setelah berkasnya lahir, gejala "JSON gugur" muncul dan saya menambal dengan **ulangi 3× + paksa mode JSON**, tanpa pernah bertanya KENAPA JSON-nya gugur. Pengulangan yang membakar uang tenant hari ini = tambalan saya bulan Maret.
- **MEKANISME:** jatah token = SATU kantong untuk berpikir + menjawab. Jawaban sah terukur **1.235–1.280 token**; jatahnya 2000 (cadangan hanya sepertiga). Model generasi baru memakai kantong itu untuk berpikir ⇒ jawaban terpotong di tengah kalimat. **Terukur 3× berturut:** Gemini 3.6/3.7/flash-latest TERPOTONG di 2000, LULUS di 4000 · Groq **MENOLAK 8000** (413). Bukan angka tebakan.
- **PERILAKU SEBELUM (diukur di jalur produksi, bukan diduga):** 3 panggilan ke vendor · jatah `[2000, 2000, 2000]` identik · 0 topik · golongan `UNKNOWN` · **pesan untuk tenant: TIDAK ADA**.
- **PERBAIKAN — SATU tempat, berlaku 11 jalur:** ditangani di adapter OpenAI-compatible (dipakai openai · gemini · groq), **nol perubahan di 11 pemanggil**. Jawaban terpotong ⇒ jatah dinaikkan **sekali** (2× , berbatas) lalu dimemo per **(vendor, model, jatah-diminta)** supaya panggilan berikutnya langsung benar. Masih terpotong di batas atas ⇒ **gagal jujur** + tenant diberi tahu: *"model ini tidak sanggup menyelesaikan permintaan — pilih model lain"*. Batas atas = **DATA** (`ai_models.default_params.max_output_tokens`), fail-soft ke angka terukur.
- **BUKTI RANTAI PENUH** (adapter produksi + putaran ulang produksi; hanya kabel vendor dipalsukan): model butuh ruang ⇒ **2 panggilan `[2000, 4000]`, PULIH SENDIRI 5 topik**, tenant tak melihat kegagalan · model tak sanggup ⇒ gagal jujur + pesan sampai ke tenant.
- **⚠️ RISIKO YANG SAYA TEMUKAN SENDIRI SAAT MEMBANGUNNYA, dan penjaganya dipasang:** memo tersimpan per-proses; bila kuncinya hanya (vendor, model), pelajaran dari tugas BESAR (seleksi topik 2.000) **menular ke tugas KECIL** (penilai naskah 500 · hook 1.200) ⇒ model diberi ruang bicara di atas rancangan tugas & panjang keluaran yang sudah dikalibrasi bergeser. Kunci diperketat memuat **jatah-diminta**; 3 penjaga tambahan mengunci: tak menular · memo tak pernah MENURUNKAN jatah · batas katalog dihormati.
- **HARGA YANG SAYA SEBUT TERANG:** pada model yang memang tak sanggup, panggilan menjadi **4× (dari 3×)** — satu lebih banyak. Sengaja: membuatnya berhenti lebih cepat berarti mengubah **perilaku-saat-gagal**, dan itu **keputusan owner** (§1.3), bukan keputusan saya.
- **BELUM TERTUTUP (jujur):** jalur Groq **mode JSON** tidak melaporkan "terpotong" — ia melempar galat 400 `json_validate_failed` (pada kegagalan BISIK, keterangannya **kosong**), jadi kelas itu **tidak tercakup** perbaikan ini. Yang tercakup = kelas Gemini/OpenAI (yang dipakai seluruh channel tenant saat ini). Menebak dari galat buta = menanam bug baru.
- **VERIFIKASI:** 9 penjaga baru, **3 DIBUKTIKAN MERAH dulu** (uji merah dijalankan sebelum satu baris pun diperbaiki) · **1.151 uji hijau, nol regresi** · penjaga regresi mengunci: panggilan sehat & teks biasa **tak tersentuh**.
- **⛔ TIDAK DIPASANG KE SERVER** — menunggu izin owner (§1.1). Nol setelan tenant disentuh.

### [B34] KATALOG MENJANJIKAN YANG TAK BISA DIPAKAI — 2 TENANT DIAM BERMINGGU-MINGGU — 🟢 SELESAI (2026-08-18)
- **Pemicu = keluhan tenant BISIK NUSANTARA (kedua kalinya) + pertanyaan owner:** *"mengapa tts gemini belum ada audio test"*. Owner: *"saya malu"*.
- **⛔ AKAR: ketersediaan model kini PER-AKUN, katalog kita menilainya GLOBAL.** Google menutup `gemini-2.5-flash` **hanya untuk akun baru** (*"no longer available to new users"*). Dibuktikan pada 4 kunci Gemini: **1 kunci lama HIDUP · 3 kunci lain 404** (termasuk BISIK). Katalog bilang "aktif" karena diuji dgn kunci KITA ⇒ tenant melihat model yang tampak siap, memilihnya, ditolak; mencoba yang lain, gagal lagi. **Bukan salah jalur kita** — jalur NATIF Google pun 404 dgn kunci tenant.
- **KORBAN KEDUA yang tak pernah melapor: `Abyss ID` gagal `model_unavailable` sejak 22-Jul — ±4 minggu diam.**
- **🔴 AKAR TEKNIS TERDALAM (di KODE KITA, bukan vendor) — DILAPORKAN, BELUM DIKERJAKAN (di luar lingkup yang diketok):** `niche_selector` meminta **10 topik × 6 field** dengan `max_tokens=2000` **literal di kode**. Model generasi baru lebih boros/bernalar ⇒ jawaban **TERPOTONG** ⇒ JSON gugur. Terukur 3× berturut, konsisten: `gemini-3.6-flash` · `gemini-3.7-flash` · `gemini-flash-latest` = **TERPOTONG di 2000, LULUS di 4000**. Ini juga dugaan terkuat kegagalan `openai-gpt-oss-20b` 3× di produksi BISIK 18-Agu 06:56 (`json_validate_failed`, `failed_generation` KOSONG = nol keluaran) — **BELUM TERBUKTI**, sebab uji ulang saya (prompt kecil DAN 6.104 karakter) LULUS. ⇒ **Selama batas ini 2000, seluruh model naskah kelas STANDARD tak bisa didaftarkan; hanya kelas LITE yang aman.**
- **PENGAKUAN: rekomendasi saya 17-Agu (`openai-gpt-oss-20b`) TIDAK CUKUP DIUJI** — lulus sekali, lalu gagal 3× di produksi tenant. **Aturan baru yang saya terapkan hari ini: kualifikasi model = 3× berturut dengan bentuk permintaan PRODUKSI**, bukan sekali.
- **ITEM 1 — Gemini TTS: model AKTIF + suara AKTIF + LULUS uji 18-Agu 07:56, tapi PROFIL MESINnya MATI** ⇒ layar channel menyaring suara menurut mesin, jadi **4 suara itu tak pernah terlihat siapa pun**. **KELAS SAMA DUA HARI BERTURUT** (16-Agu: 12 suara fal, mesin mati). Dikerjakan: 4 contoh audio dibuat lewat **adaptor produksi** (konvensi yang sudah dipakai 38 suara lain: `mesinviral-assets/voice-previews/<voice_key>.mp3`, **HTTP 200 diverifikasi**) · mesin dinyalakan · **kunci Gemini MILIK OWNER** yang dipakai, bukan kunci tenant lain.
  **⚠️ BUG BARU DICEGAH — durasi = hulu:** profil Gemini tertulis **2,4 kata/dtk** padahal **terukur 1,91** (−21%) ⇒ menyalakannya apa adanya membuat tiap video **21% lebih panjang** dari target dan ditolak gerbang durasi. Diperbaiki dgn angka TERUKUR: pace dasar mesin **1,91** + pace **per-suara** (Kore 1,93 · Puck 1,94 · Charon 1,71 · Aoede 2,05) — memakai kolom yang memang dirancang untuk itu di Katalog admin.
  **Groq TTS: 2 suara aktif tapi NOL model TTS di katalog** ⇒ suara HANTU, contoh audionya mustahil dibuat. **Menyimpang dari mandat dgn sebab tertulis:** alih-alih mengisi audio (tak mungkin), keduanya **dinonaktifkan** — nol dampak ke tenant (sudah tak terjangkau sejak mesinnya mati), katalog berhenti berbohong.
- **ITEM 2 — model Gemini hidup didaftarkan (kualifikasi 3× berturut, bentuk produksi, `max_tokens=2000` apa adanya):** `gemini-3.5-flash-lite` (10 topik, 4–5 dtk, 3/3) · `gemini-flash-lite-latest` (3/3; **penanda ALIAS — Google memindahkannya sendiri, jadi tak bisa dipensiunkan** = penawar langsung untuk pelajaran hari ini). Harga **terisi otomatis** oleh sinkron (`source=litellm`), nol angka manual. Stempel audit lewat tombol **Uji model** admin. `gemini-2.5-flash` & `-lite` **dinonaktifkan** (mati utk akun baru = jebakan bagi setiap tenant baru); nol channel sehat bergantung padanya. Channel **BISIK NUSANTARA → `gemini-3.5-flash-lite`**, gerbang kesiapan **BERSIH** (`[]`).
- **SENGAJA TIDAK DIKERJAKAN:** produksi uji BISIK **tidak** saya jalankan — job `test` mengunggah ke **YouTube milik tenant** dan memakai **kredit mereka**; tenant cukup menekan *"Jalankan uji & pulihkan"*. `Abyss ID` & `komedi.kocak` masih menunjuk model mati (setelan milik tenant = ketokan owner).
- **PENJAGA + merah dibuktikan:** `tests/test_katalog_suara_tak_menipu.py` (4 uji; **2 merah** — suara aktif di mesin mati · suara tanpa contoh audio). **1.142 uji hijau.** Nol perubahan kode mesin ⇒ **tak butuh deploy**; seluruhnya data katalog + aset S3, berlaku seketika.
- **❌ USULAN SAYA DITOLAK OWNER (jangan diungkit lagi):** "uji ketersediaan model dgn kunci tiap tenant" — *"ratusan tenant kita coba kunci mereka 1 per 1? yang bener saja? kunci itu rahasia."* **BENAR.** Celahnya tetap terbuka: tak ada apa pun yang memeriksa apakah model katalog masih hidup, dan solusinya **HARAM menyentuh kunci tenant**.

### [B32] NICHE DNA: DARI "TERSIMPAN" JADI "DITEGAKKAN" — 🔵 RENCANA MATANG, MENUNGGU KETOK OWNER (2026-08-15)
> **Mandat owner 2026-08-15:** *"Niche DNA adalah NILAI JUAL UTAMA aplikasi ini. Niche Library dan Niche
> Studio harus dibuat sebaik mungkin, semaksimal mungkin, bukan asal jadi."* + *"MesinViral = world-class
> application, seluruh unsur dibangun dengan world-class best practice."*
> **SSOT arsitektur = `NICHE_DNA_AUDIT_REMEDIATION.md`** · larangan konten = `DESAIN_PRODUK_SAAS §5b` ·
> alur pesanan = `CUSTOM_NICHE_REQUEST_FLOW.md` · atribusi = `AUDIT_ATRIBUSI_NICHE_2026-07-15.md` ·
> model niche = memory `decisions_niche_model`.

**🎯 TUJUAN TUNGGAL — tiap properti DNA wajib lulus TIGA syarat:** (1) **terlihat & bisa diubah**
pemiliknya · (2) **sampai** ke mesin · (3) **ditegakkan** pada hasil. Hari ini ±60% properti lulus
ketiganya; yang bolong **terpusat di visual** — separuh nilai jual niche.

#### 📏 FAKTA TERUKUR (2026-08-15, dari DB & kode live — JANGAN diselidiki ulang)
- **48 niche · 27 kolom · 16 kunci `visual_style`.** Sebaran: `camera`/`realism`/`lighting`/`reference`/
  `atmosphere`/`base_style`/`color_grading`/`color_palette` = 48/48 · `motion`/`composition`/`camera_motion`
  = 47/48 · `strict_prohibition` 3/48 · `subject`/`environment`/`mandatory_motion`/`render_style` 1/48.
- **T1 RANJAU PRESET:** `applyVisual` (`niche-dna-editor.tsx:434`) MENGGANTI, bukan menggabung. Ke-6 preset
  `visual_style` hanya memuat 6 kunci (atmosphere·base_style·camera·color_palette·lighting·realism) ⇒ satu
  klik **menghapus s/d 9 properti**, termasuk `strict_prohibition` (larangan agama) & `render_style`.
  **Belum meledak:** nol niche berjejak 6-kunci-persis di DB. `camera_motion` selamat (disuntik ulang di perakit patch).
- **T2 LUBANG TULIS PUBLIK:** dengan **kunci publik, TANPA login**, `niches`/`moods`/`music_library` bisa
  **DITULIS** (dibuktikan: UPDATE nilai-sama pada `sunnah_harian` → server balas 1 baris). 16 tabel lain
  tertutup rapat (channels·tenant_configs·videos·production_runs·kunci AI·akun YT·direct_jobs·niche_requests
  ·admin_audit·content_inventory·plan_limits·ai_models·ai_providers·app_config·content_beats·presets).
  Sebab: RLS ketiganya sengaja OFF (migr 0071) + izin tulis publik tak pernah dicabut.
  ⚠️ **BEDAKAN dari celah yang owner TUNDA 30-Jun** (`authenticated` bisa UPDATE `channels.niche` — butuh
  login, terbatas baris sendiri). Ini kelas lain: nol login, seluruh 48 niche.
- **T3 FRAME PEMBUKA:** hanya membaca 4 dari 16 properti (`base_style`/`color_palette`/`atmosphere`/
  `render_style`). Sudah tercatat 🟡 di `NICHE_DNA §1.1` sejak **4-Jul**, tak pernah ditutup.
  `"No people."` = **keputusan sengaja** (`§1.1b`, 14-Agu), BUKAN kelalaian — jangan dicabut diam-diam.
- **T4 MESIN GAMBAR MENGABAIKAN LARANGAN (akar mutu visual):** satu video uji, DUA pengukuran —
  *"NOT photorealistic"* diabaikan (3 dari 6 frame keluar seperti foto) **dan** *"No people."* diabaikan
  (frame pembuka tetap menggambar orang). ⇒ **setiap properti DNA berbentuk larangan tidak andal** pada
  `gpt-image-1-mini`, termasuk kotak "Larangan gambar" milik tenant.
- **T5 13 DARI 16 PROPERTI TAMPIL SEBAGAI NAMA KODE.** `VISUAL_CORE_KEYS` hanya 3. Melanggar `§5b` Lapis-2
  (*"milik pemilik niche, terlihat & bisa diubah"*) DAN janji `NICHE_DNA §2` butir 2 (*"NOL JSON mentah"*).
- **T6 TIGA JALUR BACA:** (a) `config.py::_load_from_supabase` = **daftar 15 kolom tulis-tangan** (TTL 300s)
  · (b) `tenant_config` 2 titik (`visual_style`,`visual_fallbacks`,`voice_expression`, baca-hidup) ·
  (c) kueri langsung per-konsumen (`music_selector`=`music_config`, `youtube_publisher`=`youtube_category_id`
  +`keywords`+`default_hashtags`). Kolom di luar daftar (a) **hilang senyap** — sudah memakan korban 2×:
  `emotion_scoring_criteria` (4-Jul) & `description` (1-Agu). **Diperiksa 15-Agu: nol kolom menganggur sekarang.**
  ⚠️ Ini BUKAN bug atribusi — `AUDIT_ATRIBUSI_NICHE` tetap sah, seluruh titik baca memakai kunci niche yang benar.
- **T7 JEDA 300 DETIK:** DNA yang baru disimpan baru dipakai mesin s/d 5 menit kemudian; nol kalimat di layar
  yang memberi tahu. Tenant menyangka sedang menguji DNA barunya.
- **[B14] PEMICUNYA SUDAH LEWAT:** channel **"Bang Us-Dat"** (tenant `6f044e7d…`, BUKAN akun owner) memakai
  `kisah_teladan_islami`, produksi harian, **2 video TERBIT** (31-Jul & 1-Agu). `sunnah_harian` ditambahkan
  15-Agu sebagai publik+aktif ⇒ terlihat oleh starter/pro/business. Patri 14-Agu menahan **permintaan** yang
  melanggar; **nol pemeriksaan pada GAMBAR yang keluar** — dan T4 membuktikan mesin gambar memang melanggar.

#### 🧹 KOREKSI DOKUMEN BASI (peringatan owner: dokumen basi = sumber pengerusakan)
- `NICHE_DNA §1.1b` menulis larangan gambar tenant kini *"berlaku di semua transport"*. **Yang benar: SAMPAI
  ke semua transport, TIDAK DIPATUHI oleh keluarga OpenAI** (terukur 15-Agu). Wajib diubah jadi
  **"dikirim ≠ dipatuhi"** — kalimat sekarang membuat pembaca menyangka fitur itu aman.
- `decisions_niche_model` Layer-2 sub-tag (`niches.tag_pool`/`videos.topic_tags`) = **aspiratif, kolomnya
  TIDAK ADA di DB** (diverifikasi ulang 15-Agu). Siklus rilis bulanan juga belum dibangun. **Keduanya DI LUAR [B32].**

#### 🛡️ PROTOKOL NOL-BUG — syarat lulus tiap tahap, tanpa kecuali
1. **Uji dibuktikan MERAH dulu** di kode sekarang. Uji yang sudah hijau sebelum perbaikan = uji palsu.
2. **Potret 48 niche sebelum–sesudah** untuk tiap perubahan mesin; wajib identik kecuali satu selisih yang diniatkan.
3. **Sabotase penjaganya** sampai merah — penjaga yang tak bisa merah tidak menjaga apa pun.
4. **Layar sungguhan dibuka** (kunci publik nyata + akun tenant nyata), bukan "build lulus".
5. **Nol suntingan di luar daftar berkas tahap itu.** Temuan baru → usulan (§0.3), bukan dikerjakan sekalian.
6. Dokumen SSOT diperbarui di **commit yang sama** (§3.7). Deploy tetap izin owner per-batch (§5.0).

#### 📐 STANDAR WORLD-CLASS (ketok owner 15-Agu) — berlaku di SETIAP tahap
- **Properti DNA dideklarasikan SATU KALI** (nama awam ID/EN · penjelasan dampaknya ke video · contoh · jenis
  isian · konsumen di mesin). Editor admin, editor tenant, dan validasi server lahir dari deklarasi itu ⇒
  properti ke-14 tak mengulang masalah properti ke-13.
- **Kemampuan vendor = DATA, bukan cabang kode** (`ai_models.default_params`: punya saluran larangan? patuh
  negasi? menerima `seed`?). Vendor ke-20 cukup menambah baris DB. *(Mandat generik owner 14-Agu.)*
- **Hasil diperiksa, bukan diharapkan** — tiap penegakan meninggalkan bukti terbaca di laporan run.
- **Penjaga yang tak bisa lapuk:** uji MERAH otomatis bila kolom DNA baru tak tersambung · properti tanpa
  label manusiawi · vendor gambar baru tanpa deklarasi kemampuan.

#### 📋 DELAPAN TAHAP (berurutan; centang saat tuntas)
| # | Isi | Berkas | Penjaga (uji) | REALISASI |
|---|---|---|---|---|
| **T1** | Preset **menggabung**, bukan mengganti; properti di luar preset dipertahankan; layar menyebut apa yang berubah | `components/niche-dna-editor.tsx` · `lib/niche-dna.ts` · `tests/test_preset_dna_tak_menghapus.py` | uji `applyVisual` mempertahankan 9 kunci; merah di kode sekarang | ✅ **2026-08-15** |
| **T2** | Kunci tulis publik di `niches`·`moods`·`music_library`; niche privat hanya terbaca pemiliknya (dijaga DB, bukan disaring browser) | `migrations/0199_kunci_tulis_publik_katalog_niche.sql` · `tests/test_katalog_niche_tak_bisa_ditulis_publik.py` | sapuan izin: tulis DITOLAK ketiganya; baca 5 layar tetap jalan | ✅ **2026-08-15** (migrasi APPLIED) |
| **T3** | 13 properti visual dapat label+penjelasan+contoh via **deklarasi tunggal** (§5b Lapis-2 "terlihat") | `lib/niche-dna.ts` · `niche-dna-editor.tsx` · `tests/test_properti_visual_berlabel.py` | uji: tiap kunci `visual_style` di 48 niche WAJIB punya deklarasi label | ✅ **2026-08-15** |
| **T4** | **Satu jalur baca DNA** (daftar 15 kolom dibuang) + frame pembuka memakai SELURUH DNA | `config.py` · `tenant_config.py` · `visual_assembler.py` · `music_selector.py` · `youtube_publisher.py` · `tests/test_dna_niche_sampai_utuh.py` | potret 48 niche identik; uji merah bila kolom baru tak terbawa | ✅ **2026-08-15** |
| **T5** | DNA yang baru disimpan **langsung** dipakai uji niche; layar menyatakan kapan berlaku | `producer.py` · `test-niche-panel.tsx` · `niche-dna-editor.tsx` · `tests/test_dna_uji_selalu_terbaru.py` | sunting→uji→terbukti versi BARU; uji merah bila jalur segar dicabut | ✅ **2026-08-15** |
| **T6** | Penegakan gaya visual: **uji terkendali dulu** (1 adegan × 4 versi), lalu gaya di depan perintah; `"No people."` pindah dari kode ke DNA | `ai_image.py` · `visual_assembler.py` · `lib/niche-dna.ts` · `tests/test_gaya_niche_ditegakkan.py` | 47 niche lama tak bergeser sehuruf | ✅ **2026-08-15** |
| **T7** | **DIGANTI DUA KALI OLEH OWNER** → hasil akhir: **pastikan fasilitas `avoid` milik tenant berjalan baik** (bukan menambah patri apa pun) | `niche-dna-editor.tsx` · `tests/test_pantangan_jujur.py` | mesin TIDAK berubah; layar berhenti menjanjikan yang tak ditepati | ✅ **2026-08-15** |
| **T9** | ⭐ **TUJUAN UTAMA OWNER:** kotak Pantangan tenant **benar-benar ditaati** — narasi DAN gambar; patri mesin turun jadi penjagaan KEDUA | `script_engine.py` · `script_analyzer.py` · `tests/test_pantangan_benar_benar_ditaati.py` | larangan gambar sampai ke penulis adegan; pantangan narasi ikut dinilai | ✅ **2026-08-15** |
| **T8** | `F-2` substitusi senyap → gagal jujur. **TERNYATA SUDAH dikerjakan 15-Jul; dokumennya yang basi.** Yang kurang = PENJAGA | `tests/test_niche_tak_dikenal_gagal_jujur.py` · `AUDIT_ATRIBUSI_NICHE` (koreksi) | niche hilang → berhenti+lapor, bukan substitusi senyap | ✅ **2026-08-15** |

#### ✅ REALISASI T1 (2026-08-15)
`terapkanPreset()` lahir di `lib/niche-dna.ts` — **preset berkuasa penuh atas KELUARGA kuncinya sendiri
dan tidak menyentuh apa pun di luar itu.** Ini satu-satunya semantik yang memenuhi DUA keputusan owner
sekaligus: 4-Jul *"preset karakter = pilih-satu"* (kunci keluarga yang tak diisi preset baru DIKOSONGKAN
⇒ nol sisa gaya lama) **dan** `DESAIN §5b` Lapis-2 14-Agu (aniconism & gaya rupa milik pemilik niche ⇒
haram lenyap sebagai efek samping). **Keluarga DITEMUKAN dari data** (gabungan kunci seluruh preset
properti itu ∪ kunci inti) — preset baru berkunci baru otomatis terhitung, jadi kelas "pemeriksa buta
terhadap yang baru" tak lahir lagi. Berlaku untuk `visual_style` **dan** `narration_persona` (kelas cacat
identik: hari ini tak merugikan karena ke-6 preset persona memuat semua 5 kunci, tapi kunci persona ke-6
akan jadi korban). Layar kini menyebut akibat kliknya: *"…N kotak diisi, M properti Anda dipertahankan,
K kotak gaya lama dikosongkan"* — dulu 9 properti bisa lenyap tanpa satu pun kalimat.
**Bukti:** uji `tests/test_preset_dna_tak_menghapus.py` (8 uji) **MENJALANKAN** fungsi TS-nya sungguhan
(transpilasi `tsc` repo → node), bukan mencocokkan teks — pelajaran [B30] butir 2 (uji PERILAKU AKHIR).
Merah dibuktikan **3×**: sebelum perbaikan 8/8 gagal · sabotase pustaka (properti luar keluarga dibuang)
→ 4 merah · sabotase editor (kembali merakit objek sendiri) → 1 merah. Sesudah dipulihkan 8/8 hijau.
**Regresi:** `tsc --noEmit` seluruh `apps/web` EXIT=0 · **suite penuh 1041 lulus**.
Data produksi TIDAK disentuh (ranjau memang belum meledak: nol niche berjejak 6-kunci-persis).

#### ✅ REALISASI T2 (2026-08-15) — migr **0199 APPLIED ke DB v2**
RLS dinyalakan di `niches` · `moods` · `music_library`, dan izin INSERT/UPDATE/DELETE untuk peran
`anon`+`authenticated` **DICABUT** (dua lapis: policy tulis tak ada, plus REVOKE sebagai sabuk kedua).
Policy BACA `niches` **menyalin PERSIS penyaring yang selama ini dipakai layar** (`exclusive_to = saya`
ATAU `exclusive_to IS NULL AND is_active AND access_type='public'`) — jadi yang berubah hanya SIAPA yang
menegakkannya: dari browser (bisa dilewati) pindah ke database (tidak bisa). Niche milik sendiri tetap
terlihat **walau belum aktif** (syarat `CUSTOM_NICHE_REQUEST_FLOW §3.1` "Belum aktif").
⚠️ `exclusive_to` bertipe TEXT sedangkan `auth.uid()` UUID ⇒ **cast wajib**; tanpa itu migrasi ditolak
Postgres (*"operator does not exist: text = uuid"*) — tertangkap saat penerapan, bukan setelahnya.
**Bukti dijalankan sebagai peran & sesi sungguhan** (dalam transaksi yang di-ROLLBACK, nol data berubah):
tenant pemilik melihat **48** niche termasuk 2 privat miliknya · tenant LAIN melihat **46**, nol privat
orang lain (sebelumnya browser-nya menerima 48 lalu menyaringnya sendiri ⇒ **tampilan di layar sama
persis**, yang hilang cuma kebocorannya) · pengunjung tanpa login **46**, `moods`/`music_library` **0** ·
**mesin (`service_role`) tetap 48/15/28 ⇒ produksi nol terganggu.**
Diverifikasi sebelum menyentuh DB: mesin memakai `service_role` (peran kunci `.env` diperiksa) · seluruh
route API admin & Studio memakai `createAdminClient()` · hanya **4 titik** membaca dari browser · seluruh
RPC penyentuh `niches` = `SECURITY DEFINER` ⇒ tak dihalangi RLS.
**Merah dibuktikan:** sebelum migrasi 7 uji gagal (tulis diterima di 3 tabel · DNA privat bocor ·
katalog musik terbuka tanpa sesi). Sesudah: 5 lulus + 5 subuji. **Suite penuh 1046 lulus.**
*(Alat ukurnya sendiri sempat salah — mengharapkan "0 baris" padahal server melempar `permission denied`;
diperbaiki agar menerima KEDUA bentuk penolakan. Pelajaran `test_rute_api_terjaga.py`: alat ukur yang
salah lebih berbahaya daripada tidak mengukur.)*

#### ✅ REALISASI T3 (2026-08-15)
`VISUAL_PROPS` lahir di `lib/niche-dna.ts` — **satu-satunya tempat properti gaya visual dijelaskan**:
15 properti × (label ID · label EN · penjelasan DAMPAKNYA ke video ID/EN · contoh nyata · jenis kotak).
Editor admin **dan** editor tenant merender SELURUH kotaknya dari daftar itu; menambah properti ke-17 =
**satu baris** di deklarasi, kotak+label+panduan+contoh muncul sendiri di KEDUA layar. Ini menuntaskan
janji `NICHE_DNA §2` butir 2 ("NOL JSON mentah") yang tertunda sejak 4-Jul, dan `DESAIN §5b` Lapis-2
("milik pemilik niche, **terlihat** & bisa diubah") untuk `strict_prohibition` + `render_style`.
Penjelasan ditulis untuk pemilik niche awam, termasuk yang paling sering keliru: **`render_style` = 1–2
kata** (penentu foto vs animasi) vs **`realism` = kalimat tekstur** — kekeliruan yang §1.1b sendiri
peringatkan. `camera_motion` sengaja di luar daftar (objek bersarang, sudah punya seksi 4-tombol sendiri).
Properti yang ditambahkan sendiri pemilik niche tetap boleh tampil apa adanya, tapi kini **ditandai
jujur** *"belum punya panduan"* — bukan disamarkan seolah setara properti resmi.
**Bukti:** `tests/test_properti_visual_berlabel.py` membaca daftar kunci **dari 48 niche di DB** (bukan
dari daftar di dalam uji) ⇒ properti ke-17 yang lahir tanpa label = **MERAH otomatis**; deklarasinya
DIJALANKAN lewat `tsc`+node, bukan dicocokkan teksnya. Merah dibuktikan 2×: sebelum perbaikan 5 gagal ·
sabotase (mencabut `strict_prohibition`+`render_style` dari deklarasi) → 2 merah. Sesudah 6 lulus + 15 subuji.
**Regresi:** `tsc --noEmit` EXIT=0 · **`next build` lulus** · **suite penuh 1052 lulus**.
*(Dua uji saya sendiri sempat terlalu kasar — menolak label EN "Atmosphere"/"Lighting" karena kebetulan
sama kata dengan kuncinya, dan melarang SELURUH kotak bernama-kode padahal properti buatan pemilik niche
memang tak punya label. Keduanya **diperketat ke KONTRAK**-nya, bukan dilonggarkan agar hijau — pelajaran [B31].)*

#### ✅ REALISASI T4 (2026-08-15)
**Daftar kolom tulis-tangan DIBUANG** — `_rapikan_baris()` menyalin SELURUH baris niche. Terukur:
**16 kunci → 27 kunci** sampai ke mesin; 11 yang dulu hilang senyap kini ikut (`music_config`,
`voice_expression`, `youtube_category_id`, `niche_id`, `access_type`, `origin`, `is_base`,
`exclusive_to/until`, `released_at`, `created_at`). Kolom DNA yang admin tambahkan besok otomatis sampai
**tanpa menyentuh kode** — kelas cacatnya dihapus, bukan kejadian ketiganya ditambal (korban 1
`emotion_scoring_criteria` 4-Jul, korban 2 `description` 1-Agu).
**Tiga jalur baca → SATU PINTU:** hanya `intelligence/config.py` yang boleh menyentuh tabel `niches`.
`tenant_config` (2 titik-muat), `music_selector` (2 fungsi), `youtube_publisher` (3 helper) kini lewat
pintu itu. ⚠️ **Kesegaran tidak ikut jadi korban:** pintu menyediakan dua daun — `get_niches()` bercache
300 dtk dan `muat_niche_segar()` langsung-DB. Pembaca yang selama ini selalu mutakhir TETAP mutakhir;
menyatukan jalur tidak boleh menukar satu cacat dengan cacat lain (jeda 300 dtk).
**Frame pembuka memakai SELURUH DNA** — dulu hanya 4 dari 16 properti (utang 🟡 `NICHE_DNA §1.1` sejak
4-Jul). Kini pencahayaan · kamera · komposisi · realisme · gradasi · rujukan · gerak **dan larangan figur
niche** ikut ke frame terpenting sebuah Short. `"No people."` **sengaja belum disentuh** (keputusan sadar
§1.1b 14-Agu) → dipindah ke DNA di T6.
**Bukti:** potret 48 niche sebelum–sesudah = **48 × 16 properti IDENTIK**, nol nilai lama bergeser ·
5 niche nyata × 5 properti dibandingkan dengan pembacaan LANGSUNG ke DB = **nol selisih** · jalur
gagal-lunak untuk niche tak dikenal berperilaku sama persis (`{}`/`[]`/`"27"`) · `tenant_config` dua
channel produksi tetap memuat 11 kunci visual + 6 contoh shot + ekspresi vokal.
Merah dibuktikan 2×: sebelum perbaikan 7 gagal · sabotase (daftar kolom dikembalikan) → 1 merah.
**Suite penuh 1060 lulus.**
*(Satu uji saya sendiri sempat mengikat huruf besar-kecil `render_style` — diperketat ke KONTRAK
"nilainya sampai", bukan "susunan hurufnya sama".)*

#### ✅ REALISASI T5 (2026-08-15)
`segarkan_dna_sebelum_direct()` dipanggil di **awal `run_direct`** ⇒ SELURUH job yang dipicu manusia
(uji niche tenant · uji admin · ulangi) membuang potret DNA lebih dulu. Tidak disaring per-jenis job:
semuanya dipicu orang yang menunggu hasilnya sekarang, dan menyaring per-jenis hanya menambah satu
tempat baru untuk salah menggolongkan. **GAGAL-LUNAK** (§0.6): penyegaran gagal → kembali ke perilaku
lama, produksi tidak dijatuhkan.
⚠️ `invalidate_niches_cache()` sudah ditulis **2-Agu dengan NOL pemanggil** — mekanisme lahir mati yang
komentarnya sendiri mengakuinya. Inilah pemanggilnya; cacat lama tidak ditambal dua kali.
**Layar berhenti membiarkan tenant menebak:** panel uji menyatakan *"Test selalu memakai DNA terbaru
yang sudah Anda simpan."*, dan di bawah tombol Simpan: *"Test niche langsung memakai DNA terbaru.
Produksi terjadwal menyusul dalam beberapa menit."* (dwibahasa, §3.5).
**Bukti runtime — putaran nyata pada `sunnah_harian`** (nol channel memakainya; nilainya dikembalikan
persis): mesin memuat DNA → DNA disunting di DB → **tanpa penyegaran mesin MASIH membaca yang lama**
(cacatnya terbukti hidup) → jalur uji menyegarkan → DNA baru terbaca. Merah dibuktikan 2×: sebelum
perbaikan 5 gagal · sabotase (pemanggilan dicabut) → 1 merah. `tsc` bersih · **suite penuh 1065 lulus**.

#### ✅ REALISASI T6 (2026-08-15) — **DIUKUR, BUKAN DIDUGA**
Uji terkendali: SATU adegan yang sama → `gpt-image-1-mini` → **7 gambar**, DNA `sunnah_harian` (minta
animasi 3D). Hasil: gaya di **EKOR** ⇒ **foto** (A 2/2 · C 1/1) · gaya di **DEPAN** ⇒ **animasi 3D**
(B 2/3, satu setengah jalan). **Pengungkitnya LETAK**, bukan panjang perintah: mesin gambar menimbang
kata-kata awal jauh lebih berat, jadi gaya yang menempel sesudah paragraf deskriptif praktis tak
terdengar. Inilah sebab video uji 15-Agu keluar seperti foto padahal DNA-nya benar dan sudah sampai.
⛔ **DUGAAN SAYA 15-Agu GUGUR** — saya menduga kalimat `Avoid: photorealistic…` yang MEMANGGIL
fotorealisme. Varian D (gaya di depan, TANPA daftar Avoid) justru **lebih buruk** ⇒ daftar itu **tetap
dikirim**. Dicatat supaya sesi berikutnya tak menghidupkannya lagi.
⚠️ **Jujur soal batasnya:** memperbaiki, **tidak menjamin** (1 dari 3 hanya setengah bergaya) ⇒ lapis
pemeriksaan hasil = **T7**.
**Penegakan hanya untuk niche yang MEMILIH `render_style`** ⇒ 47 niche lama **byte-identik** (jaminan
14-Agu utuh), dan niche/vendor baru otomatis ikut tanpa menyentuh kode (mandat generik owner).
**`"No people."` PINDAH dari kode ke DNA** (`hook_frame_people`): bawaan tetap melarang (47 niche lama
sama persis), tapi niche yang subjeknya justru manusia — seperti sunnah harian, yang DNA-nya sendiri
berbunyi *"orang biasa masa kini ADALAH subjeknya"* — tak lagi dibantah kodenya sendiri. Kenop itu ikut
berlabel manusiawi di T3, jadi terlihat & bisa diubah pemilik niche (§5b Lapis-2).
📌 **Lapis "kemampuan vendor sebagai DATA" TIDAK jadi dibangun — sengaja.** Pengungkit yang menang
(letak) berlaku **universal** untuk semua mesin gambar; menambah kenop per-vendor untuk sesuatu yang
tidak berbeda per-vendor = kerumitan tanpa manfaat. Perbedaan vendor yang NYATA sudah jadi data sejak
14-Agu (`supports_seed`, `prompt_max_chars`).
**Bukti runtime:** satu gambar lewat **jalur produksi apa adanya** sesudah perbaikan → prompt dimulai
*"premium 3D animated feature film still."* → hasilnya animasi 3D. Merah dibuktikan 2×: sebelum 3 gagal ·
sabotase (gaya dikembalikan ke ekor) → 1 merah. `tsc` bersih · **suite penuh 1072 lulus**.

#### ✅ REALISASI T8 (2026-08-15) — **dokumen basi hampir membuat saya "memperbaiki" yang sudah benar**
Rencana menyebut F-2 "belum pernah diketok" karena `AUDIT_ATRIBUSI_NICHE` masih menulis **MENUNGGU
KETOK**. Diperiksa baris-per-baris: **keenam titik SUDAH gagal-jujur sejak 15-Jul** (script_engine ·
hook_optimizer · niche_selector ×2 · tenant_config), lengkap dengan komentar bertanggal. Dokumennya yang
tertinggal sebulan. Kalau saya percaya dokumen dan "memperbaikinya", saya akan menyentuh kode yang sudah
benar — persis peringatan owner *"dokumen basi bisa jadi sumber pengerusakan"*.
Yang benar-benar kurang: **penjaganya**. Kini `tests/test_niche_tak_dikenal_gagal_jujur.py` — 4 uji yang
MEMANGGIL ketiga titik dengan niche karangan dan menuntut run berhenti, plus sapuan kode agar pola
substitusi (`next(iter(niches…))`) tak bisa kembali. Sabotase satu titik ⇒ **2 merah**. Dokumen
`AUDIT_ATRIBUSI_NICHE` dikoreksi di commit yang sama.

#### ✅ REALISASI T7 (2026-08-15) — **rancangan saya DITOLAK DUA KALI; yang benar jauh lebih kecil**
**Tolakan-1** (periksa GAMBAR hasil: pengenal wajah / "mata" AI / tolak semua kata bertubuh) — owner:
*"jangan over engineering, yang membuat niche jadi kaku."* Benar: ketiganya melarang **seluruh manusia**,
padahal yang terlarang **dua sosok**.
**Tolakan-2** (patri kalimat larangan Rasulullah & Allah di penulis NASKAH — sempat saya pasang lalu
**DICABUT UTUH**) — owner: *"jangan over protective. Kita sudah buat rem yang terpatri. Tenant juga
harus buat di niche masing-masing, mereka paham itu. Yang bertanggung jawab tenant itu sendiri, di
channelnya, bukan channel kita. **Yang kita buat adalah TOOLS, bukan mengarahkan/membatasi konten
tenant.**"* Selaras `DESAIN §5b`: *"patri di kode HANYA yang merugikan MesinViral; sisanya milik niche.
Selera tidak pernah milik mesin."* Kode dikembalikan bersih — nol sisa.
**PEKERJAAN YANG SESUNGGUHNYA:** *"pastikan fasilitas yang kita sediakan berjalan dengan baik."*
Diukur, dan fasilitas "Pantangan" ternyata **bekerja separuh**: `script_checker` mencocokkan **harfiah
per-butir** ⇒ `kadrun` **tertangkap** (naskah ditolak) tapi `kata KADRUN` / `menggambarkan atau
menyuarakan Nabi` **LOLOS**. Terukur: **187 butir pantangan di 48 niche, 79 (42%) berupa kalimat** yang
tak akan pernah cocok harfiah — dan pemilik niche **tak punya cara tahu**, karena layar menjanjikan
*"teks bebas, **dipatuhi mesin apa adanya**"*.
**MESIN TIDAK DIUBAH SEDIKIT PUN** (kalimat panjang tetap berguna: ikut jadi arahan ke AI penulis; dan
mencocokkan kalimat secara harfiah akan menolak banyak naskah SAH — kelas cacat "keras"→"kekerasan"
yang sudah pernah dibayar). Yang diperbaiki: **keterangannya**. Label palsu dicabut; tiap butir kini
dihitung di layar — *"N butir ditegakkan harfiah (naskah ditolak) · M butir jadi arahan untuk AI"* —
dwibahasa. Itu memperbaiki ALAT, bukan mengatur isi konten tenant.
**Bukti:** `tests/test_pantangan_jujur.py` (6 uji) mengunci **kontrak mesin apa adanya** (1–2 kata =
keras · kalimat = tidak harfiah · pelanggaran = parah) + menuntut layar jujur. **Suite penuh 1082 lulus.**
⛔ **JANGAN hidupkan lagi:** pengenal wajah · "mata" AI per-gambar · penolak kata bertubuh · patri
larangan sosok di penulis naskah · pencocokan makna (semantik) · memaksa tenant menulis kata tunggal.

#### ⭐ REALISASI T9 (2026-08-15) — **TUJUAN UTAMA OWNER, yang justru TIDAK ada di rencana saya**
Ketetapan owner: *"kotak avoid pada Niche Studio dan Niche Library, baik untuk LLM maupun visual,
BENAR-BENAR DITAATI oleh mesin produksi. Titik."* + *"patri 2 hal terkait Allah dan Rasulullah juga
hanya penjagaan KEDUA; yang pertama harus dari tenant sendiri melalui kotak avoid."*
⚠️ **Kesalahan saya:** rencana [B32] memetakan apa yang RUSAK, bukan apa yang owner INGINKAN. Delapan
tahap dikerjakan tanpa satu pun menyentuh tujuan utamanya. Dicatat sebagai pelajaran menyusun rencana.
**Dua lubang yang ditutup:**
1. **Larangan GAMBAR tenant tak pernah sampai ke PENULIS ADEGAN** — hanya ditempel di ekor perintah ke
   mesin gambar. Akibatnya penulis adegan bebas mengarang *"seorang pemuda duduk bersila…"* walau tenant
   melarang manusia, lalu mesin gambar menuruti ADEGAN, bukan larangan yang menempel belakangan.
   Terukur 15-Agu: larangan dipatuhi **4/4** selama adegan tak memintanya, diabaikan begitu adegan
   memintanya. ⇒ **larangan TENANT kalah oleh kalimat yang KITA tulis sendiri.** Kini
   `bagian_larangan_gambar()` menyerahkannya ke penulis adegan ⇒ adegan lahir sudah patuh.
2. **Pantangan NARASI hanya ditegakkan bila 1–2 kata.** Butir berupa kalimat (79 dari 187 butir di 48
   niche) nol penjagaan — termasuk pantangan terpenting `kisah_teladan_islami`: *"depicting/voicing
   revered figures directly"*. Kini ikut dinilai **penilai naskah yang SUDAH dipanggil tiap percobaan**
   ⇒ **nol panggilan AI tambahan, nol biaya tambahan**; melanggar ⇒ nilai <60 ⇒ ditulis ulang oleh
   putaran retry yang sudah ada.
**Pemeriksa harfiah TIDAK diubah** (mencocokkan kalimat secara harfiah akan menolak naskah SAH — kelas
"keras"→"kekerasan" yang sudah dibayar). Niche tanpa isian ⇒ perintah **sama persis** seperti sebelumnya.
**Bukti pada niche NYATA:** `kisah_teladan_islami` & `sunnah_harian` — larangan gambar ✅ sampai ke
penulis adegan · pantangan narasi ✅ sampai ke penilai. Merah dibuktikan 2×: sebelum 5 gagal · sabotase
(dua sambungan dicabut) → 2 merah. **Suite penuh 1088 lulus.**

#### ✅ T10 & T11 SELESAI (ketok owner 2026-08-15)
**T10 ✅ — judul topik tunduk pada kotak Pantangan niche.** Terukur DUA kali: aturan niche sampai ke
pemilih topik hanya sebagai SARAN. `sunnah_harian` menyatakan tegas di kalimat PERTAMA deskripsinya
"SATU sunnah per video, judul dilarang memuat angka" — tetap **1 dari 5** judul berbunyi *"7 Daily
Sunnah Practices…"*, dan **3 dari 5** memuat lambang ﷺ (kotak kosong di takarir). ⇒ instruksi tak
mengikat, penyaring mengikat. `saring_judul_terlarang()` membuang judul yang melanggar **kata terlarang
milik niche itu sendiri**, memakai pemeriksa harfiah yang SUDAH ada — bukan aturan baru, bukan selera
mesin (`DESAIN §5b`). Niche tanpa pantangan → nol perubahan. Semua kandidat melanggar → daftar dipakai
apa adanya + WARNING (produksi tak pernah berhenti). Berkas: `niche_selector.py` · `tests/test_judul_patuh_pantangan_niche.py`.
⚠️ **Ambang panjang SENGAJA beda dari `script_checker`:** pemeriksa naskah mengabaikan butir <4 huruf (benar untuk naskah 130 kata — butir sependek "7" akan salah-tuduh di mana-mana), tapi JUDUL pendek & ditulis sengaja ⇒ butir 1 karakter pun dihormati. Tanpa itu pantangan `ﷺ` dan `7` **tak pernah terpakai** (terukur: keduanya lolos memakai ambang naskah).
**BUKTI:** 5 kandidat → judul ber-"7" dan ber-ﷺ DIBUANG, 3 judul bersih lolos. Merah dibuktikan (5 gagal sebelum, termasuk 2 gagal saat ambang naskah masih dipakai). Suite penuh **1093 lulus**.

**T11 — "Pratinjau 1 gambar" di editor DNA (Niche Studio + Niche Library).** ⭐ *Jawaban atas pertanyaan
owner "apa pantas dijual": hari ini satu-satunya cara mencocokkan gaya visual adalah memproduksi VIDEO
PENUH — ±4 menit, ±Rp 1.500 sekali coba. Itu membuat penyetelan gaya mahal & lambat bagi kita MAUPUN
tenant.* Pratinjau: **±6 detik, ±Rp 250, nol video**.
⚠️ **SYARAT MUTLAK:** pratinjau WAJIB memakai perakit prompt yang SAMA PERSIS dengan produksi
(`ai_image._build_image_prompt` + corong patri). Merakit sendiri = kebenaran KEDUA yang suatu hari
berbeda — persis kelas cacat yang [B32] tutup seharian ini. Karena itu ia lewat **pekerja**, bukan
dirakit di layar.
**✅ REALISASI T11:** migr **0200 APPLIED** (`job_type='preview_image'` + kolom `result_key`) ·
`producer.run_preview_image()` · rute `api/niches/preview-image` (POST antre + GET polling, tautan
berjangka — kunci S3 tak pernah dikirim mentah) · tombol di `niche-dna-editor.tsx` ⇒ **Niche Studio DAN
Niche Library sekaligus** (satu komponen) · `tests/test_pratinjau_gambar_dna.py`.
**Nol tabel baru · nol layanan baru · nol jalur baru** — menumpang antrean `direct_jobs` yang sudah teruji.
⚠️ **Percobaan pertama saya merakit konfigurasi provider SENDIRI dan langsung patah** (`TenantConfig`
tak punya `visual_provider`). Itu justru bukti kenapa pratinjau tak boleh punya jalur sendiri: kini ia
memakai `VisualAssembler._load_run_config()` + bentuk config yang SAMA PERSIS dengan `_try_ai_image`.
**BUKTI RUNTIME:** job pratinjau dijalankan sungguhan → gambar 1,9 MB jadi, gaya niche terbaca.
⚠️ **ANGKA SAYA KELIRU & DIKOREKSI:** bukan ±6 detik melainkan **±25 detik** (terukur). Teks di layar,
rute, dan docstring sudah diperbaiki — janji di layar harus sama dengan kenyataan.
Merah dibuktikan (6 gagal sebelum). `tsc` bersih · `next build` lulus · **suite 1099 lulus**.

#### ⛔ LARANGAN DALAM [B32] — jangan dikerjakan, jangan "sekalian"
- **Jangan** membangun sub-tag/`tag_pool` atau siklus rilis bulanan (aspiratif, di luar lingkup).
- **Jangan** mencabut `"No people."` diam-diam — pindahkan ke DNA (T6), keputusan sadar 14-Agu.
- **Jangan** mengubah atribusi niche (`AUDIT_ATRIBUSI_NICHE` = sehat) — [B32] menyentuh KELENGKAPAN & PENEGAKAN, bukan pemilihan niche.
- **Jangan** membuka lagi celah `authenticated`→`channels.niche` (owner sengaja menunda 30-Jun).
- **Jangan** melonggarkan uji yang menghalangi; perketat ke KONTRAK-nya (pelajaran [B31]).

#### ⏳ MENUNGGU KETOK OWNER
Ketok "jalan" = T1→T8 dikerjakan **berurutan sampai 100% tuntas** (§0.8). Deploy tetap minta izin per-batch.

### [C2] Self-learning deepening + trend F3/F4 — 🟡  (TREND_RADAR **F3/F4**)
- **TUJUAN:** kalibrasi `source_weights` (bobot sumber trend) dari outcome nyata per (niche,geo) + panen sinyal Analytics kaya (retensi/trafficSource/searchTerms) + agregat lintas-tenant anonim (cold-start moat).
- **BUKTI:** loop inti hidup (`viral_score_weights`/`historical_factor`); `channel_analytics` sebagian sinyal sudah. CTR per-video=0 PERMANEN (batas API YouTube, bukan bug).
- **PLAN:** F3 ukur-dimensi lanjutan (`videos.list topicDetails` sudah; kalibrasi `competition_gap`/`emotional_trigger` dari angka) + F4 umpan-balik outcome eksplisit + agregat lintas-tenant. **Butuh akumulasi analytics nyata pasca-cutover.**
- **DONE-BILA:** bobot ter-kalibrasi dari data; seleksi topik makin tajam terukur.
- **REALISASI:** 🟡 mekanisme siap; aktivasi = DATA (post-cutover).

---

# 🔒 KELOMPOK D — KEPUTUSAN OWNER *(belum bisa dimulai tanpa jawaban)*

### [D1] Growth funnel ("pikat dulu, todong belakangan") — ✅ **TUNTAS (ditutup 2026-07-16 — seluruh DONE-BILA terpenuhi, diverifikasi live)**
- **KONTEKS (direvisi 2026-07-11 pasca deep-dive FE/BE/DB):** infrastruktur funnel TERNYATA sebagian besar SUDAH LIVE — onboarding setup credential-first ✅ · `/showcase` (galeri contoh, CMS `showcase_videos`) ✅ TERBANGUN tapi **tabel kosong** · docs CMS `/docs` ✅ TERBANGUN tapi **13/14 artikel masih draft** · banner trial hitung-mundur + email `notify_trial_ending` H-x + nurture pasca-lapse ✅ LIVE. Spec lama `ONBOARDING_FUNNEL_PLAN.md` = BASI sebagian (ditulis pra-OAuth-platform; usulan "traktir video gratis" TIDAK dipakai — strict-BYOK owner tetap).
- **KEPUTUSAN OWNER 2026-07-11:** celah nyata = KONTEN, bukan kode → **F1 (isi showcase) = tugas OWNER** · **F0 (lengkapi seluruh panduan /docs, ±29 artikel + tombol Help buka tab baru) = mandat AKTIF Claude** (daftar panduan diajukan, menunggu ketok) · F2 (kartu channel-belum-aktif di dashboard) & F3 (personalisasi recap-nilai) = DITANGGUHKAN — hanya bila terbukti 100% perlu.
- **DONE-BILA:** showcase terisi (owner) + 29 panduan published + tombol Help live.
- **REALISASI FINAL 2026-07-16 (verifikasi live saat penutupan):** F0 ✅ 31 artikel PUBLISHED /docs + tombol Help & help kontekstual LIVE + sapu-silang istilah ✅ 16-Jul + /support dwibahasa ✅ 16-Jul (tracker `PANDUAN_TENANT_TRACKER.md`) · F1 ✅ showcase TERISI owner (4 video aktif; /showcase HTTP 200, verified DB 16-Jul) · F2+F3 ✅ deployed 11-Jul. **SEMUA DONE-BILA terpenuhi → item DITUTUP.** Yang tersisa di jalur jualan = aksi owner (review isi /docs · consent-check · uji model fal · putaran kumala [B7]) + keputusan bisnis mendatangkan trafik (promosi/iklan — di luar lingkup backlog teknis, belum pernah dimandatkan).
- *(arsip realisasi lama)* 🟡 F0: SELURUH 30 artikel DITULIS & DI-SEED ke CMS (draft) 2026-07-11 — urut proses bisnis 6 tahap, struktur baku 8-bagian, dwibahasa, katalog-AI tak dipatok, label UI dari kode live (tracker = `PANDUAN_TENANT_TRACKER.md`). Sisa: koreksi owner → publish → tombol Help (FE, mandat terpisah). **F2+F3 ✅ TUNTAS+DEPLOYED 2026-07-11 (`a26aa55`, BE+FE OK via skrip resmi):** F2 = kartu kondisional dashboard "Channel perlu perhatian" (incomplete/halted; reuse `effectiveStatus`+RPC `channel_readiness` — sumber sama /channels; varian tanpa-channel → onboarding; hilang saat sehat) · F3 = recap-nilai nyata di banner trial + email `notify_trial_ending` (n video + views latest-per-video; validasi diskriminatif: ryan 207 video/42.046 views vs tenant kosong senyap; fail-soft). Keduanya dormant-aman: hanya tampil saat kondisinya ada. **Nyambung:** `LIFECYCLE_NURTURE_ARCHITECTURE.md` (CLOSED — mesin nurture live).

### [D2] Multi-platform (Reels/TikTok) — 🔒⬜
- **KONTEKS:** kini YouTube-only (cukup untuk launch, Starter=YouTube). Reels(Pro)/TikTok(Business) = fitur tier. Spec `MULTI_FORMAT_STUDIO.md §7`.
- **BUKTI:** belum ada abstraksi publisher (`youtube_publisher.py` saja; `pipeline.py` hardcode YouTube). `publish_platforms` field ada tapi tak dipakai.
- **KENDALA EKSTERNAL (masuk perencanaan):** audit TikTok 2-4 minggu (tanpa audit=private), Meta App Review IG 2-4 minggu.
- **PLAN (setelah diputuskan):** `distribution/base_publisher.py` + refactor loop `publish_platforms` + `reels_publisher.py`/`tiktok_publisher.py` (BYO-CC) + tier-gating.
- **REALISASI:** 🔒 nunggu keputusan owner + audit eksternal.

---

# 📌 KELOMPOK E — MENUMPANG GATE

### [E1] Add-on custom-niche via Midtrans live — ✅ *(TERNYATA SUDAH TERBANGUN — audit 2026-07-04)*
- **KONTEKS:** lifecycle custom-niche SUDAH jalan (concierge/manual "Tandai lunas"). Pondasi bayar disiapkan (`niche_requests.paid_at`/`order_id`/status `awaiting_payment`). Spec persis = `CUSTOM_NICHE_REQUEST_FLOW.md §7` + arsitektur bayar/settlement = `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §3`.
- **PLAN:** (1) generalisasi `midtrans.snap_create_transaction` dari plan_type → `price_key` add-on (insert `payments` kategori add-on + `order_id`). (2) `niche_requests.order_id` ← order_id Midtrans. (3) `handle_notification`: settlement add-on → set `paid_at` + `awaiting_payment`→`in_progress` **otomatis** (ganti manual). (4) tombol bayar Snap di Pustaka Niche. (5) teruskan/hapus jalur concierge sesuai kebutuhan.
- **DONE-BILA:** tenant bayar custom-niche via Snap → status auto-maju + niche mulai dibangun.
- **DEPENDS:** [A1] Midtrans produksi.
- **REALISASI:** ✅ **Sudah terbangun penuh sejak epic PAYMENT (`53e272c`)** — verified 2026-07-04: `snap_create_niche_addon` (midtrans.py:175, validasi kepemilikan+awaiting_payment → order category=addon → tautkan `niche_requests.order_id`) + settlement webhook → RPC `settle_niche_request_paid` (auto-maju `in_progress`) + FE route `/api/niche-requests/[id]/pay`. Backlog ini basi. Hidup otomatis begitu A1 tuntas (env kini production).

---

## 🧭 URUTAN REKOMENDASI (efektif menuju jualan)
1. **[A1] Midtrans prod** (+ Claude siapkan **[A4]** materi verifikasi Google + pandu **[A2]**) → buka pintu jualan. Bareng: **[E1]**.
2. **[B1] system-secrets + [A3] rotasi** — hardening pra-publik.
3. **[A5] smoke-test** tenant-baru e2e (validasi acceptance).
4. Sisa **[B2-B8]** — poles pasca fungsi jualan aktif. *(**[B8]** = fix link mati email trial-lapse; bug live customer-facing, layak didahulukan meski bukan pemblokir jualan.)*
5. **[D1] funnel** + **[B9] siklus-hidup/nurture** (`LIFECYCLE_NURTURE_ARCHITECTURE.md`) setelah [A1] go-live & ada aliran tenant nyata; **[C]** matang otomatis; **[B6]/[D2]** prioritas terendah.

## ⛔ PANTANGAN (agar tak muncul "bug"/kerancuan)
- JANGAN sentuh v1 (pensiun; arsip+DB disimpan). JANGAN drop `niche_pool`/`niche_mode`. JANGAN ngoding di VPS.
- JANGAN anggap marker `[ ]`/⬜ di dokumen SPEC lain sbg daftar kerja — **hanya FILE INI** otoritatif.
- Test-job jangan makan kuota publish live (private/tak-terhitung-cap).

---
### Changelog
- **2026-08-21 — 🔌 PINTU KEDUA TERSAMBUNG: channel yang DIAM akhirnya bersuara (Batch A `0204` + Batch B `0205` **TERPASANG di produksi**).** Owner melaporkan 2 kegagalan; penelusuran menemukan yang **tidak** dilaporkan: **4 channel mati 4 hari** sejak 17-Agu (2 tenant **BERBAYAR**) karena model naskahnya dimatikan di katalog **tanpa seorang pun diberi tahu**. **SSOT rencana, bukti & batas jujur = `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §9b.** Batch B menambah: gagal-baca sesaat berhenti menuduh tenant (`TRANSIENT`) · **karantina model bebas-biaya** (A + B1|B2|B3; rancangan uji-berbayar dengan kunci admin **dibuang** atas keberatan owner) · mematikan baris katalog menyebut channel terdampak. Prinsip owner yang mengikat: **jangan sentuh database tenant** — sistem yang bersuara, tenant yang memilih penggantinya. Bukti: 1231 uji hijau · 26 sabotase merah (3 uji palsu saya sendiri tertangkap & diganti) · rujukan menggantung **tetap 5 (4 aktif)** ⇒ nol data tenant tersentuh. Deploy 21-Agu 21:25 & 22:34, bukti di server pada data nyata. ⛔ **Batch C (6c panel katalog) DIBATALKAN & DIKEMBALIKAN SELURUHNYA atas keputusan owner 21-Agu 23:0x** — sebabnya BUKAN uji dan BUKAN bug: saya membuat **PINTU BARU** di panel katalog (tombol "Tambah mesin suara" di tab Voice) padahal yang diminta **memperbaiki jalur yang SUDAH ADA**; menambah model TTS memang sudah punya tempatnya di tab **AI Models**. Pengembalian: `git revert` (kode terbukti **identik** dgn sebelum Batch C — nol berkas berbeda) + 4 trigger & 2 fungsi `catalog_missing*` di-DROP + 9 baris cermin `galat_registry_provider` dihapus. **Terbukti nol fosil & nol kerusakan:** katalog aktif kembali 9/41/5/42 (sama seperti sebelum) · **nol** channel tersentuh · rujukan menggantung tetap 5 (4 aktif) · 3 trigger `channels` utuh · jalur kesiapan 9 channel aktif nol rusak · nol galat di log · 1231 uji hijau. ⚠️ **ATURAN YANG MENGIKAT dari kejadian ini:** perbaikan panel = **perbaiki jalur yang ADA**; menambah tombol/tab/pintu baru = **HARAM tanpa ketokan owner terpisah**, sekalipun rencana lama menyebutnya. Sisa 6c yang belum dikerjakan (isian dibuang senyap · lahir nonaktif · gerbang kelayakan) **menunggu rancangan ulang yang menempel pada jalur yang ada** — jangan kerjakan ulang rancangan yang sudah ditolak. Sesi baru: **Batch D** (penjaga §7) atau rancangan-ulang 6c sesudah diketok.
- **2026-08-22 — 🧰 PANEL KATALOG AI: prasyarat & koridor DITETAPKAN; 6 butir perbaikan MENUNGGU KETOKAN (nol kode disentuh).** Latar: Batch C (21-Agu) dibatalkan seluruhnya karena membuat PINTU BARU di panel padahal yang diminta memperbaiki jalur yang ADA. Owner menuntut rencana matang & TERCATAT supaya sesi baru (yang "seperti bayi baru lahir") tak mengulang pengerusakan.
  **SSOT peta & prasyarat = `ARSITEKTUR_AI_PROVIDER_MODEL.md` §9** (koridor 7 langkah · prasyarat per kolom + akibat bila salah · cukup-data vs butuh-kode · 11 titik lemah terukur). Dokumen itu BUKAN daftar kerja — backlognya di sini.
  **ATURAN MENGIKAT pekerjaan ini** *(dilanggar 21-Agu ⇒ pengerusakan)*: (1) **satu butir sekali jalan**, lapor + tunjukkan diff, owner lihat layarnya, baru butir berikutnya; (2) **nol butir di luar B1–B6** — menemukan hal lain = LAPOR, jangan kerjakan; (3) pembuktian = **apa yang TIDAK berubah** (B1–B3 wajib nol baris logika berubah); (4) menambah **tombol/tab/pintu/lencana = HARAM** tanpa ketokan owner terpisah, sekalipun rencana menyebutnya; (5) **baca `ARSITEKTUR_AI_PROVIDER_MODEL.md` §1–§8 DULU** — kalau butirnya ternyata sudah ditangani sesuatu yang ada di sana, BERHENTI & lapor (21-Agu: lencana "belum layak" jadi lapis KETIGA di atas lencana harga & lencana uji yang sudah ada).
  **BUTIR (urutan wajib B1→B2→B3→B4, lalu B5/B6 hanya sesudah owner menentukan bentuk/tempat):**
  · **B1** ✅ lebar jendela: form katalog 720px · sisanya 560px · pola `min(px,vw)` dijaga uji. **Bukti: 5 baris berubah, NOL di antaranya bukan atribut lebar.**
  · **B2** ✅ `default_params` berlabel manusiawi + arahan dwibahasa ber-contoh siap-tempel per jenis (naskah/suara kosong · gambar `size,steps` · video `aspect_ratio,duration,duration_param,allowed_durations`). *Versi "berubah mengikuti jenis" TIDAK dikerjakan* — ia menuntut logika baru, dan jaminan B2 adalah nol-logika. Dicatat, bukan disembunyikan.
  · **B3** ✅ seluruh isian 7 form katalog berlabel manusiawi; isian yang berakibat bila salah punya arahan dwibahasa; arahan **Jenis model** menunjuk tab tujuan (tab Voice / tab Durasi) lalu Uji → nyalakan.
  · **B4** ✅ `display_name`+`adapter` masuk whitelist ⇒ berhenti dibuang; penolak salah-ketik yang tadinya **kode mati** kini hidup (nilai di luar daftar sah ditolak + daftar pilihannya disebut). Nol berkas layar tersentuh.
  · **B5** ✅ menyalakan kembali model membersihkan jejak karantina — **hanya** pada arah nyala. Kedua kolom tetap DI LUAR whitelist (jejak = tulisan mesin, haram dikarang admin). Bentuknya sudah ditetapkan komentar migr 0205 sendiri: *"dibersihkan admin saat menghidupkan kembali"* — ini melunasi hutang itu, bukan menebak.
  · **B6** ✅ baris `tts_profiles` **disiapkan otomatis** saat admin membuat model `component='tts'` — lahir NONAKTIF, `adapter` KOSONG (protokol haram ditebak sistem), tak menimpa yang sudah ada, fail-soft. Dilengkapi lewat editor ✎ yang SUDAH ADA. **Nol tombol/tab/pintu baru** — rancangan 21-Agu yang menambah pintu DITOLAK owner dan tidak diulang.
  **BUKTI B1–B6 (22-Agu):** 17 uji baru (**14 merah dulu**) · **20 sabotase semuanya MERAH** — menangkap **9 uji palsu saya sendiri** · **1248 uji hijau** · build FE lulus · berkas layar berubah HANYA pada atribut lebar & peta teks (**0 baris di luar itu**) · lima angka acuan **tetap**: 41 model aktif · 9/13 channel aktif · rujukan menggantung 5 (4 aktif) · **0** channel tersentuh · 6 baris `tts_profiles`. ⏳ **BELUM DEPLOY.**
  **➕ 22-Agu (F1–F5) — FOSIL & LAPIS GANDA DIBERESKAN, bukan dilabeli "batas".** Teguran owner: melabeli bug sebagai batas = meninggalkan bug. Menurut definisi owner sendiri (fosil · objek tak terwiring · data dikumpulkan tapi tak dipakai = BUG), lima hal dibereskan: **F1** migr `0207` membuang 3 kolom fosil (`tts_profiles.has_word_timeframe` = sumber kebenaran KEDUA untuk `tts_class`, nilainya cermin 1:1 · `voice_catalog.pace_sample_n`+`pace_updated_at` = 0/44 terisi) — nol pembaca & nol penulis, **diterapkan ke DB**. **F2** `request_param_schema` (dibaca mesin, tak terkelola panel) kini ada di form penyedia + arahan dwibahasa + diurai sebagai JSON. **F3** dua penghitung "channel yang memakai baris ini" disatukan jadi `channelPemakai(…, hanyaAktif)`; beda SAH dipertahankan (matikan→aktif saja · hapus→semua), dan gagal baca pada jalur hapus **menahan**, bukan meloloskan. **F4** fosil data `groq` dibersihkan (1 setelan suara + 2 suara; nol model tts, nol channel memakai — penyedia groq untuk NASKAH utuh & tetap aktif). **F5** 🔴 **BUG BARU DITEMUKAN & DITUTUP**: `voice_catalog` ada di `DELETABLE` tapi `refGuard` **tak punya penjaga** ⇒ suara yang sedang dipakai channel tenant bisa TERHAPUS (saat ditemukan: 6 channel memakai suara, 3 AKTIF). Kini ditolak + disarankan nonaktifkan, dan **setiap** tabel `DELETABLE` wajib punya penjaga (dikunci uji). Bukti: 15 uji baru (**9 merah dulu**) · **12 sabotase MERAH** (2 uji palsu tertangkap: penjaga hapus yang bisa jadi KODE MATI `const n = 0`, dan saringan aktif yang lolos karena kata di definisi fungsi) · **1263 uji hijau** · build FE lulus · lima angka acuan TETAP (41 model aktif · 9/13 channel · menggantung 5/4 · **0** channel tersentuh) · nol suara yang dipakai channel hilang dari katalog. Satu penjaga Batch B diperbarui karena kuerinya berpindah ke penghitung bersama — ia dulu mengikat TEMPAT, kini mengikat PERILAKU. ⏳ **BELUM DEPLOY.**
  **➕ 22-Agu (G1–G5) — PANEL MENGATAKAN KEBENARAN TENTANG STATUS MODEL.** Pemicu: owner menyalakan `gemini-2.5-flash` lalu bertanya *"mengapa tidak ada indikator untuk yang mati?"* — terukur: lencana "✓ Teruji" **dari 6 Juli**, model **terbukti mati 18-Agu**, `Abyss ID` (channel AKTIF) memakainya, jejak karantina dikirim ke layar tapi **nol kali** ditampilkan, dan **B5 saya justru menghapus jejak itu**. **G1** tabel AI Models menyebut "dipakai berapa channel" (kuning = ada channel aktif). **G2** jejak karantina tampil sebagai lencana `terbukti mati` + alasan vendor. **G3** lencana uji menyebut umurnya & bertanda **BASI** >30 hari. **G4** migr `0208` — menyalakan wajib audit `LULUS` **dan lebih baru dari bukti kematian**; di DB (bukan panel) karena jalur pemutar panel sudah terbukti dipakai; terukur 43/43 model aktif lolos ⇒ **nol terkunci**. **G5** koreksi B5 — jejak dibersihkan hanya bila ada uji yang lebih baru. Bukti: 15 uji baru (**15 merah dulu**) · **15 sabotase MERAH** (4 uji palsu tertangkap, semuanya kelas "kata masih ada di tempat lain") · **1278 uji hijau** · build FE lulus · gerbang dibuktikan bertransaksi pada kasus NYATA lalu di-rollback (nol baris berubah). ⚠️ **Perlu tindakan owner:** `gemini-2.5-flash` sekarang AKTIF dengan audit 6-Jul dan jejaknya sudah terhapus B5 lama ⇒ gerbang tak bisa menahannya (ia sudah aktif). Lencana **BASI** akan memperingatkan, tapi **klik Uji** untuk memastikan — `Abyss ID` memakainya. ⏳ **BELUM DEPLOY.**
  **➕ 22-Agu — PINTU KETIGA disambungkan + `gemini-2.5-flash` DIMATIKAN (perintah owner).** Owner memerintahkan uji model itu; Google menjawab **"no longer available to new users… use models/gemini-3.6-flash"** — frasa itu persis kata-global B1 karantina, tapi karantina tak menyala karena jalur UJI tak tersambung (hanya jalur produksi). Kini tersambung: `model_tester` memanggil penilai yang SUDAH ADA (ambang tak diulang · `dasar` dari galat sesungguhnya, tidak dipatok · yang dinilai galat vendor apa adanya, bukan teks kita · fail-soft mutlak). Model dimatikan + jejak berisi jawaban Google apa adanya; gerbang `0208` langsung menahan penyalaan ulang (`belum_lulus_uji`); `Abyss ID` kini menyebut alasan di layar tenant. Bukti: 6 uji baru (**4 merah dulu**) · **5 sabotase MERAH** · **1284 uji hijau** · model aktif 43→42 (SENGAJA, perintah owner) · **0** channel tersentuh. Uji dijalankan memakai kunci kolam tenant pemilik Abyss ID — **atas izin tenant yang owner nyatakan 22-Agu**; nilai kunci tak ditampilkan & tak disimpan. 📌 **Pengganti:** `gemini-3.6-flash` yang Google sarankan **belum ada di katalog**. Tiga model naskah Gemini lain aktif, dua di antaranya lulus uji 18-Agu (`gemini-3.5-flash-lite`, `gemini-flash-lite-latest`) — `gemini-2.5-flash-lite` auditnya 6-Jul (BASI, sebaiknya diuji dulu). ⏳ **BELUM DEPLOY.**
  **PERTANYAAN yang HARAM DITEBAK** (sisa, belum dijawab owner): (setelan suara + 2 suara tanpa model tts, migr 0138) — hapus atau biarkan? (e) kolom "dipakai N channel" di tabel AI Models — **tak pernah ada** di 42 versi riwayat; menambahkannya = penambahan layar ⇒ butuh ketokan.
  **BATAS KEJUJURAN:** peta ini sempat saya anggap lengkap, lalu ternyata layar tenant **Integrasi** terlewat sama sekali, dan dokumen `ARSITEKTUR_AI_PROVIDER_MODEL.md` (ada sejak 9-Jul) tak saya baca sebelum merencanakan Batch C. Sebelum menyentuh apa pun, sesi baru WAJIB memastikan tak ada pembaca katalog lain yang terlewat: `grep -rln 'ai_models\|ai_providers\|tts_profiles\|voice_catalog' apps/web/src src/`
- **2026-08-20 (4) — 🔐 KUNCIAN KLAIM CHANNEL YOUTUBE — ✅ TUNTAS & TERPASANG (commit `79c7317`, deploy BE+FE OK).** Dibuktikan di server pada data nyata: akun baru menyambung channel yang sudah diklaim = DITOLAK · pemilik sah menyambung ulang = BOLEH. **SSOT tunggal = `CHANNEL_LOCK_ACTIVATION_PLAN.md` §7** (persoalan · fakta terukur · arsitektur · 4 temuan evaluasi final · batas jujur · tracker T0–T7 · bukti wajib). Sesi baru: baca §7, lanjut dari baris ⬜ pertama di §7f. Jangan salin isinya ke sini — satu tempat saja.
- **2026-08-20 (3) — ketokan owner: 10 niche Islam DIAKTIFKAN + `sunnah_harian` DILENGKAPI (migr `0202`, DATA-ONLY).** (1) Ke-10 niche `0201` → `is_active=true`; katalog publik aktif **46 → 56**. (2) `sunnah_harian` diisi 2 kunci inti visual yang kosong sejak 15-Agu (`color_palette`, `atmosphere`) — nilainya disusun dari nyawa niche itu, selaras `lighting` yang sudah ada; niche ini dipakai channel tenant **Penjaga Dakwah**, karena itu hanya disentuh atas izin owner. **Terukur sesudahnya: 58/58 niche di pustaka lengkap 3 kunci inti — NOL yang jatuh ke default hardcode.** Nol perubahan kode, nol deploy (FE tenant & admin membaca DB langsung).
- **2026-08-20 (2) — 10 NICHE ISLAM masuk pustaka tenant (permintaan owner; migr `0201`, DATA-ONLY — nol perubahan kode).** Tiap niche disusun dari NYAWA-nya sendiri (bahasa visual, busur emosi, pantangan, bar mutu) — bukan salinan. **Dua doktrin visual, keduanya sudah terbukti di pustaka:** (A) **nol manusia** (pola `kisah_teladan_islami`, 2 video terbit) → `kisah_islami_dramatis` · `kisah_nabi_rasul_sahabat` · `akhirat_kematian_ghaib` · `rahasia_fakta_islam` · `sejarah_peradaban_islam`; (B) **manusia biasa masa kini** (pola `sunnah_harian`, 13 test Test Lab `done`) → `dosa_taubat_pengampunan` · `jodoh_cinta_pernikahan` · `masalah_hidup_islami` · `rezeki_ujian_takdir` · `islam_psikologi_kehidupan`. **Cacat yang sengaja TIDAK diwarisi:** `sunnah_harian` kosong pada `color_palette`+`atmosphere` sehingga hook-frame & rewrite jatuh ke default HARDCODE (jebakan yang saya dokumentasikan sendiri di `NICHE_DNA_AUDIT_REMEDIATION` baris 26, lalu saya langgar hari yang sama) — ke-10 niche mengisi KETIGA kunci inti. Lambang penghormatan non-Latin tidak ditulis di DNA mana pun (font takarir → kotak kosong); pantangannya disebut dengan kata. **Struktur diverifikasi 4 permukaan:** DB 27 kolom · BE `config.py` `select(*)` salin seluruh baris (dijaga `test_dna_niche_sampai_utuh.py`) · FE admin & tenant = satu editor `lib/niche-dna.ts` (16 properti visual · 5 persona · 8 seksi). Bukti: 10/10 terbaca ulang dari DB live — visual 15 properti · 3 kunci inti terisi · 8 seksi · 5 persona · HARD FAIL di tiap bar mutu; pustaka 48 → **58**. `is_active=false` mengikuti pola seed `0132` (aktivasi = ketok owner, nol tenant terpapar). ✅ **SISA INI SUDAH DITUTUP** di catatan 2026-08-20 (3) — `sunnah_harian` dilengkapi atas izin owner (migr `0202`).
- **2026-08-20 — label `is_base` di Katalog>Niches MENGELABUI — ✅ TERPASANG (`9cac128`, deploy 21-Agu).** Layar admin menulis `is_base (trial/starter only)` — salah di DUA hal: (a) **"only"** keliru, predikat entitlement adalah **ATAU** (`exclusive_to=saya` ∨ (publik ∧ (`plan_limits.full_niche_catalog` ∨ `is_base`))), jadi niche dasar TETAP dipakai pro/business; (b) **"starter"** basi sejak keputusan owner 04-Jul (opsi A+C, migr **0124**): tier berbayar = katalog penuh. Bukti DB live: `full_niche_catalog` starter/pro/business=true · trial=false; `is_base`=3 niche aktif-publik (universe_mysteries, dark_history, ocean_mysteries); niche publik aktif total **46** → trial **3**, starter/pro/business **46**. Gerbang server BERSIH (overload lama 3-argumen `set_channel_niche` sudah di-DROP di 0096; 0124 satu-satunya yang hidup) — **yang basi hanya tulisannya, bukan aturannya**. Fix: kedua label (modal "Niche baru" + panel Access) → dwibahasa **tanpa menyebut nama paket** ("niche dasar — semua paket, termasuk Trial") supaya tak bisa basi lagi ketika owner mengubah `plan_limits` dari admin. **Nol uji baru** (§3: uji mengikat perilaku, bukan teks harfiah); 1175 uji tetap hijau + build FE lulus.
- **2026-07-15 — perbaikan DURASI (root-cause) + pesan tenant manusiawi (commit `d27273b`; keputusan owner; lokal-teruji, ⏳ BELUM deploy).** Masalah "pipeline sering GAGAL durasi + pesan teknis bikin panik" ditangani 3-serangkai: (1) video near-miss durasi TIDAK lagi dibunuh → tetap diproduksi → masuk "perlu ditinjau" (tenant putuskan terbit/buat-ulang); hanya meleset PARAH (±30%, `QC_DURATION_GROSS_FACTOR`) di-stop hemat render. (2) Pesan Telegram QC dimanusiakan ("1 video menunggu keputusan Anda", nol jargon "±15%/GAGAL"). (3) Prompt naskah diperbaiki (cabut "pintu-kabur" yg mengajari LLM abaikan panjang → target struktur-kalimat + preset-aware) utk menekan peluang meleset. Dokumen QC_CONTENT_ARCHITECTURE §root-cause/§5b/changelog + `.env` disinkronkan. **Sisa: bukti runtime (ukur durasi audio nyata beberapa preset) + izin deploy owner.**
- **2026-07-15 (2) — Katalog admin: 3 keluhan owner dibedah.** (1) Gembok = BERFUNGSI (verified 3 lapis; price_sync skip locked). (2) 2 BUG NYATA edit-harga: kolom harga model VIDEO tampil kosong (formatter) + menyimpan form MENGHAPUS harga video (replace total) → fix MERGE + field /dtk (`56fd25b`). (3) Uji katalog component video "belum didukung" = kelalaian F3 → penguji video NYATA via adapter (`8e6fc4b`). Kling di-stamp "✓ Teruji" (bukti produksi 14-Jul); Veo/Hailuo jujur "belum diuji". **⚠️ Kedua fix commit-only saat dicatat; ✅ IKUT TERANGKAT deploy batch 2026-07-16** (BE `01be29c`+FE `f6950a6`, health/situs OK). **Catatan pelanggaran (diakui):** fix dikerjakan sebelum lapor-rencana-tunggu (§2.3b) — pelanggaran prosedur ke-3 dalam 2 hari, pola momen-panas; tercatat utk akuntabilitas. **MVT kini FULL setelan owner via UI** (8s+hailuo+radiant+edge Gadis+gpt-4.1) — READY, tak disentuh Claude; janji pemulihan-LLM gugur (owner sudah menimpa dgn pilihannya sendiri).
- **2026-07-15 — 🔎 AUDIT ATRIBUSI NICHE TUNTAS (mandat owner "kritikal, 5 area, nol asumsi") = `AUDIT_ATRIBUSI_NICHE_2026-07-15.md`.** Verdict: pasca fix DNA `ee125eb`, **SEMUA 12 kelompok titik-baca produksi ber-atribusi BENAR** (niche run ter-resolve; publisher memakai niche SAAT-PRODUKSI dari baris inventory — aman walau channel ganti niche sebelum slot; musik/mood/persona/timing/emosi/hashtag/kategori/analytics ✅) + FE 3 permukaan ✅ + DB ✅. 2 temuan non-aktif menunggu ketok: **F-2** fallback senyap "niche tak dikenal → niche aktif pertama" di 6 titik (kelas §3.3; usulan gagal-jujur) · **F-3** duplikat vestigial `tenant_configs.niche/niche_pool` → [B5].
- **2026-07-14 (2) — Ilustrasi biaya AI DIPINDAH landing → /pricing seksi BYOK (mandat owner; ✅ DEPLOYED `68e219f` 01:37, skrip resmi OK situs 200; bukti live: landing 0 teks terlarang + 3 rujukan baru, bundle /pricing memuat query & `.cost-grid`).** + ikutan izin owner: 3 kartu paket landing dirapikan SAMA TINGGI (`.price-grid` stretch + `.pcard` flex-kolom, tombol rata dasar — pola `.tier` /pricing; aturan terverifikasi di CSS live). Worker BE TIDAK di-restart saat itu → B15 non-aktif sementara *(→ ✅ aktif malamnya: deploy 2a15df1 19:13, lihat [B15])*.
  (a) Seksi 2 kartu konfigurasi model (marketing_blocks `cost_*`) dicabut dari landing, dipasang di
  /pricing di bawah 3 kartu BYOK; (b) 2 teks DIBUANG di DB (reversible, nilai lama tercatat sesi ini):
  baris head "Berdasarkan penggunaan nyata 8–12 Juli…" + kalimat footnote "Ditambah langganan per
  video… Rp 4.967" (disclaimer "Angka ilustrasi…" dipertahankan); (c) 2 kartu kini SAMA tinggi+lebar,
  di tengah (CSS `.cost-grid` grid stretch, maks 900px, responsif 1 kolom); (d) koherensi: 3 rujukan
  landing ("lihat ilustrasi biaya…") diarahkan ke halaman pricing + label admin /admin/pricing
  "(landing)" → "(/pricing, seksi BYOK)". Bukti: build lulus + replikasi query & predikat widget
  via kunci anon (seksi render ✓, head 0 baris ✓, teks terlarang hilang ✓). BE/FE-tenant TIDAK
  tersentuh (grep: marketing_blocks hanya dipakai landing/pricing/admin).
  (a) **[D1] /showcase TERNYATA SUDAH TERISI owner** (8 layar + 4 video aktif, live 200) — catatan
  "tabel kosong" = BASI; (b) **[B17]-F0 kurva belajar tampil di 3 lokasi** (/insights utama + channel
  setting + dashboard) — yang belum dari F1 hanya: `decision_reason` di Runs + email Laporan Kecerdasan
  Mingguan (grep kode = nol); (c) **[C2] label "menunggu volume data" DIGUGAT owner & terbukti basi**:
  196 video ber-analytics penuh sejak April — kalibrasi F3/F4 layak dinilai ulang kelayakannya, bukan
  ditunda otomatis; (d) [B15] pemicu berulang (3 video terhapus terdeteksi 13-Jul) → naik dari dorman
  ke layak-jadwal.

- **2026-07-13 (4) — 🔐 BUG SSO SIGNUP via WWW dipotong di gerbang server (nginx, izin owner).** Kesaksian owner (saksi mata test Rush-Q): daftar-dgn-Google → terlempar balik ke halaman signup; login ulang baru masuk. Bukti log nginx detik-per-detik: teman masuk via **www.**mesinviral.com → `doGoogle` membangun alamat-pulang ber-www → TIDAK terdaftar di allowlist Supabase → pengguna dibuang ke landing `/?code=...` (kode tak pernah ditukar; akun TERBUAT di Supabase 16:36:05, sesi browser tidak) → percobaan-2 dari non-www 16:36:26 sukses → /onboarding. **Fix akar:** kanonikalisasi domain di nginx — SEMUA kunjungan www (http+https) 301 → apex, path+query utuh (blok khusus `sites-enabled/www-canonical` + blok :80 diarahkan ke apex; backup `/root/mesinviral.nginx.bak-*`). Uji 7/7: www→301 apex (termasuk /auth/callback query utuh) · apex 200 semua · webhook Midtrans 200 · rantai penuh berakhir apex. Pelajaran uji menangkap edit gagal-match SEBELUM lapor (metode diganti file-terpisah). Klarifikasi keamanan owner: SSO daftar TANPA layar peringatan Google = NORMAL (izin dasar nama+email; layar verifikasi hanya utk scope YouTube saat connect channel). Sisa usulan UX (belum diketok): sapaan selamat-datang + 3 langkah di /onboarding.

- **2026-07-13 (3) — 🎯 AKAR SEJATI SAGA RETENSI-0 DIPOTONG (deploy `f554e38` 19:57, izin owner).** Penelusuran mendalam (mandat owner, nol asumsi) atas temuan audit "watch=0 total 12–13 Jul": akar = `self_learning.run_once` fetch analytics **SEKALI PER TENANT memakai koneksi channel PERTAMA** — padahal token OAuth terikat per-IDENTITAS channel (**koreksi keras owner: RAD & MVT = SATU akun Google `ryan.andrian.diputra@gmail.com`; RAD=channel utama, MVT=channel kedua → 2 KONEKSI, BUKAN 2 akun**). `channel==MINE` via koneksi MVT utk video RAD → Google balas SUKSES-TAPI-KOSONG tanpa error → 0 senyap. Menjelaskan SELURUH saga: sehat pra-25-Jun (1 koneksi) · mati sejak migrasi multi-koneksi · "sembuh" 11-Jul (backfill manual token benar) · mati lagi 12-Jul (loop harian tetap lama) — **fix scopes 11-Jul benar tapi separuh akar**. Fix: fetch per-CHANNEL + sapu `_get_videos_to_fetch` ter-scope channel_id (`self_learning.py` + `channel_analytics.py`; 212/212 video ber-channel_id, nol luput). Bukti diskriminatif 5/5: RAD hari-ini watch>0 muncul (baseline 0) · video pembanding `oGKw0Wq7FXo` 0→**357 mnt/85,8%/full=True** · MVT sehat + sapu scoped (2≤6) · run produksi pertama pasca-deploy = "fetch=2 channel" per-koneksi ✓. Data bolong 12–13 Jul terisi ulang alami via rotasi harian. Sampingan (→[B15] dorman): 3 video antrean ternyata sudah dihapus di YouTube.

- **2026-07-13 (2) — AUDIT STATUS vs CODEBASE (mandat owner: "curiga dokumen basi") — 5 permukaan, nol asumsi.** Hasil: (a) **[B16] header BASI** — badan sudah ✅ 11-Jul (migr 0149 + scopes 3/3 terisi + log 'full metrics siap') → header dikoreksi; (b) **[D1]-F0 LEBIH MAJU dari catatan**: 32/32 artikel docs **PUBLISHED** (bukan draft) + tombol Help (helpKey) terpasang di 12 halaman FE; (c) **[B17]-F0 SUDAH ✅** (tracker §5 PROGRAM_BUKTI_KECERDASAN: F0.1-F0.3 ✅ `3c1fd76` migr 0150, validasi identik 100%) — yang menunggu = F1 (gerbang G1); (d) terkonfirmasi MEMANG belum: B1 (system_secrets tak ada), B5 (fosil masih ada), B14/B15 (nol kode), B6 (nol provider t2v), D2 (hanya youtube_publisher), C2 (source_weights statis tanpa kalibrator). (e) **[A5] makin genting — bukti DB: 2 pembeli NYATA (kumala pro, effi starter) AKTIF ber-0 channel** = pelanggan bayar mandek pra-produksi. (f) 🔴 **TEMUAN MERAH BARU: `video_analytics` 12–13 Jul watch/subgain NOL TOTAL (92+113 baris)** padahal masa sehat Juni terisi same-day; diskriminatif: video sama `oGKw0Wq7FXo` 11-Jul watch=357 → 13-Jul watch=0 (views 550) → REGRESI PENULISAN METRIK (akar ≠ scopes; scopes OK). Kandidat: efek samping batch "otak belajar" 11-Jul. **Fix = menunggu ketok owner** (diagnosa akar dulu, jangan tambal buta).

- **2026-07-13** — **🎯 FINALISASI TIER PLAN (dokumen akar `finalisasi_tier_plan.md`, 5 tahap, mandat owner "tuntaskan terpadu, HARAM bug").** Audit pricing 5-permukaan → cetak biru 4-pilar (penegakan hak paket · rumus periode nilai-adil · harga checkout resmi · satu sumber tampilan). **DEPLOYED (VPS `75675cb`):** Tahap 1 (kuota channel ditegakkan server RLS 0155 + gate N-tertua · perpanjangan tak potong sisa hari · diskon admin NYATA · pagar lifecycle) · Tahap 2 (TAHUNAN end-to-end migr 0156 · drawer dinamis · display_name seragam · badge di-luar-kuota) · Tahap 3 (panel admin: editor narasi fitur + tuas paket + tambah entri harga + buang tab Schedule/USD mati + revenue/MRR agregat nyata RPC 0157) · **+fix insiden S3 NEO** (notif publish-gagal terjadwal + alarm storage janitor). **LOKAL selesai, menunggu ratifikasi redaksi + izin deploy:** Tahap 4 (kartu/matriks/ilustrasi-biaya marketing jadi DATA admin-editable migr 0158; toggle tahunan nyata; FAQ jujur; landing 2-komponen biaya) · Tahap 5 (fallback caps self-heal `tenant_config.py`; rekonsiliasi DESAIN §4/PAYMENT §changelog). Semua tahap ber-uji diskriminatif + nol residu; paritas marketing byte-identik (nol regresi tampilan). Commit: `fb04952`/`883836c`/`1b6b529`/`f9cd6aa`/`dc2394b`.
- **2026-07-11 (3)** — **fix upload showcase video >10MB (blocker F1 owner; izin eksplisit per-langkah):** "form-data tidak valid" utk file 12MB ternyata gerbang tersembunyi Next canary `proxyClientMaxBodySize` default 10MB (aktif krn middleware). Pembuktian berlapis: log nginx → parser mentah 79MB OK → probe ter-autentikasi (user diagnosa sekali-pakai, dihapus) ambang 8MB ok/10MB gagal → konstanta ditemukan di config-shared.js:260. Fix 1 knob → 100MB (selaras nginx; pagar per-jenis route tetap). Deploy `1c2597e` + probe pasca-deploy 12MB TEMBUS ke cek format ✓. Route showcase sendiri TERBUKTI bersih — bukan bug fitur.
- **2026-07-11 (2)** — **🧠 BATCH "OTAK BELAJAR DIBENAHI" TUNTAS+DEPLOYED+VERIFIED (izin eksplisit owner per-langkah):** pemicu = "Kisah Teladan Islami" palsu jadi top-niche (konten sudah dihapus owner krn visual melanggar aniconism). (1) **P5+P6** analyzer & viral-weight-optimizer: per-BARIS snapshot → snapshot TERBARU per-VIDEO (dedup 0056-style) + paginasi penuh (dulu limit 200 baris = ±3% sejarah RAD); (2) **migr 0148** dua RPC agregat (dashboard+/insights) = tertimbang volume, agg dinormalisasi 0..1 (kontrak % FE); (3) **P2** bersih 45 baris kontaminasi (backup penuh; videos 9 + analytics 21 + inventory 1 + insights 14; residu 0); (4) **P4a** DNA islami larangan MUTLAK figur. **Hasil verified:** top niche sejati RAD = universe_mysteries (otak lama salah: dark_history); MVT jujur insufficient; viral_weights n=135; log 0 error. Kebocoran antar-channel: NIHIL (isolasi verified semua jalur). Konsep kanonik owner terdokumentasi di memory self-learning. +[B14] QC wajah (dorman ber-pemicu) +[B15] sinkron video terhapus YT (dorman). Realtime kartu F2 [B13] ✅ terverifikasi live (jadwal auto-update).
- **2026-07-11** — **Sesi tutup-administrasi + arah funnel:** (1) header basi dirapikan: [B10] Fase 1-4 ✅ · [B11] Batch 1 ✅ (realisasi badan sudah lama ✅, judul tertinggal); (2) korroborasi stok sadar-jadwal LULUS live → item TUTUP (bukti di changelog 07-09); (3) [A4] checkpoint H+6: masih review privacy (normal) + audit mandiri halaman privacy vs regulasi Google LULUS semua butir — nol perubahan; (4) [D1] direvisi ke realita (infra funnel live, celah=KONTEN) + keputusan owner: F1 showcase=owner, F0 panduan lengkap+tombol Help=mandat Claude, F2/F3 ditangguhkan; (5) **notif Telegram video-menunggu-review (jalur terjadwal) + header circuit-break pakai nama channel ✅ DEPLOYED (`c6f3161`+`d42dd7a`, uji kirim nyata 2026-07-10 dini hari)** — di luar nomor backlog, mandat owner.
- **2026-07-10** — **3 perbaikan mandat owner (commit `f941579`, deployed+validated run nyata):** (1) **gerbang durasi pra-visual** — proyeksi audio+trailing vs window QC SEBELUM biaya gambar/render (rugi sistem ≠ rugi tenant); (2) **judul AKHIR video di Runs** (`run_metadata.video_title`, identik YouTube; fallback topik baris lama) — tutup insiden 1-video-2-nama; (3) **badge Perlu-Ditinjau menyebut tempat tinjau** (Studio/link · /review/link · kedaluwarsa-TTL). Detail = `QC_CONTENT_ARCHITECTURE` changelog 2026-07-10.
- **2026-07-09** — **Stok buffer SADAR-JADWAL (mandat owner, di luar nomor backlog):** target stok channel tidak lagi statis 2 — `buffer_depth` eksplisit menang (incl. 0, dulu bug jatuh ke 2); NULL → slot/hari × `app_config.buffer_target_days` (migr **0147**, admin-editable, clamp TTL); tanpa slot → 0. Dasar: stok > kebutuhan kena sapu TTL 72j (compute terbuang) + tenant model gratis kuota-harian (Groq/CF) terbakar eager-fill → circuit-break. FE admin System mencerminkan rumus sama. Commit `25c029b`; rumus diuji 5 kasus data nyata; deployed via skrip resmi. SPEC sinkron: `DESAIN_PRODUK_SAAS §12c`. **✅ KORROBORASI LIVE LULUS (2026-07-10 malam, DB+log VPS):** slot 19:00 MVT terbit (`3c-ePEy0zeY`) → stok 2→1 → NOL run pengisi-ulang 4,5 jam pasca-slot (target=1, defisit=0); pembanding diskriminatif: RAD (target 3) slot 21:00 LANGSUNG diisi ulang → diamnya MVT = keputusan rumus, bukan producer mati. Item TUTUP TOTAL.
- **2026-07-08** — tambah **[B11] Multi YouTube channel A-Z** (audit mendalam DB/BE/FE + OAuth; 5 gap kritis ber-bukti; desain pagar-3-lapis + picker galeri disetujui owner). Dokumen baru `MULTI_YOUTUBE_CHANNEL_ARCHITECTURE.md` = SPEC+tracker; `PER_CHANNEL_OAUTH_MIGRATION.md` gap §7 diserap ke [B11].
- **2026-07-05 (2)** — **Etalase niche terbuka + gerbang pesan custom (keputusan owner, di luar nomor backlog):** (1) Pustaka Niche kini menampilkan SEMUA niche publik aktif untuk semua tier (DNA terbuka penuh); di luar hak → badge 🔒 "Perlu upgrade" + tombol drawer "Upgrade paket"→/billing (gerbang PAKAI tetap server: RPC `set_channel_niche`, tak disentuh). (2) **Celah ditutup**: trial TERNYATA bisa mengajukan niche custom (RLS insert `niche_requests` hanya cek kepemilikan) → migr **0130** `plan_limits.can_request_custom_niche` (trial=false, berbayar=true, admin-tunable) + RLS insert diperketat; FE tombol "Pesan niche custom" trial = 🔒 → modal ajakan upgrade. Dwibahasa. Validated: RLS diuji live (trial DITOLAK/starter DITERIMA, nol residu) + login nyata akun trial via jalur browser = 4 niche (3 pakai + 1 lock) + build lokal PASS. Pemilih niche di Channel tetap hanya yang berhak (by design).
- **2026-07-04** — **Sesi poles marketing + admin (arahan owner, di luar nomor backlog; semua LIVE):** (1) `/demo` → **`/showcase`** (migr 0115: showcase_screens+showcase_videos + drop demo_tours; iframe login-trap dibuang; screenshot + galeri video contoh admin-managed via CMS; redirect 301). (2) Blog **feature image** (S3 `blog-cover/`, migr—; +fix ACL public-read laten upload-logo; nginx `client_max_body_size 100m`). (3) Marketing: footer Lumite · trial-days dari `app_config` (nilai live=3!) · kalkulator AI palsu → blok BYOK jujur "mulai Rp 0" · kontak kirim-server → `company_profile.email` (no-hardcode) · tab Status & badge footer → kondisi NYATA worker_heartbeats · fix nav highlight (hardcode `active=\"Fitur\"` sejak awal) · sub-judul rata tengah. (4) Admin: System Health dibersihkan dari fosil `pipeline_queue` → stok buffer per channel + query tahan >1000 · **Jadwal Rilis Bulanan DIHAPUS TUNTAS** (migr 0116 — penjadwal tanpa eksekutor=jebakan pending). (5) **Test Lab Fase 1 DIBANGUN ULANG** (migr 0117): uji-produksi niche admin **TANPA YouTube** (S3+TTL 3 hari, tonton di drawer Pustaka Niche), kunci via vault validate-early NYATA, pilihan provider/model/voice LENGKAP dari katalog DB, ConfirmDialog; sebelumnya rusak e2e (form buang kunci diam-diam + route baca kolom drop-0090). **Menyusul (disepakati): Fase 2 audit properti niche (fokus Music+Scoring, library 28 track) memakai alat ini · Fase 3 test niche utk tenant Business di Niche Studio (kredensial sendiri).** Acceptance Fase 1 = owner isi kunci AI di Test Lab → jalankan 1 test dari Pustaka Niche.
- **2026-07-03 (2)** — **[B8] TUNTAS ✅** (commit `3927c41`): notif Telegram admin utk masukan `/feedback` (baru dibangun, reuse notify_admin/vault) + atribusi `?ref=&source=` di email trial_lapse/trial_ending (sebelumnya link polos). LIVE-validated e2e (DB row + Telegram terkirim + log mv-webhook). Sisa pemblokir jualan tetap = **[A1]** (aksi owner).
- **2026-07-03** — **[B9] follow-up TUNTAS + arch docs CLOSED.** Tombol aksi-manual admin `/admin/tenants` (`6a5f798`) + Telegram admin via `company_profile.admin_telegram_chat_id` (`603640e`, migr 0114 — no-hardcode, editable owner). Bonus (permintaan owner): **menu Company Profile** `/admin/company-profile` (view/edit data perusahaan invoice + Telegram ID admin) + **fix badge Support** hardcode "4" → hitung tiket belum-selesai nyata (`1863239`). `LIFECYCLE_NURTURE` & `PAYMENT_AND_TENANT_GATE` **diverifikasi vs realita (2 verifikator read-only) → direkonsiliasi (5 discrepancy diperbaiki) → CLOSED.** Fokus tunggal tetap file ini; pemblokir jualan = **[A1] Midtrans produksi** (aksi owner).
- **2026-07-01** — dibuat dari audit menyeluruh (verified DB/BE/FE/git/VPS). Konsolidasi seluruh sisa-kerja + Plan-vs-Realisasi. Semua dokumen lain di-CLOSE jadi SPEC/arsip + ber-banner ke sini. Memory (`MEMORY.md`) arahkan sesi baru ke file ini.
- **2026-07-01** — tambah **[B8]** (halaman `/feedback` — perbaiki link MATI di email trial-lapse; keputusan owner Opsi B halaman-sendiri). Bug live customer-facing terverifikasi (`/feedback` → 404; email `email.py:92-101` mengarah ke sana). Urutan rekomendasi + Changelog disesuaikan.
- **2026-07-02** — **rantai kanonik billing & siklus-hidup dibereskan (anti miss-link)**: daftarkan `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` (SELESAI+deployed `04cf0a2`) + `LIFECYCLE_NURTURE_ARCHITECTURE.md` (rencana) ke peta dokumen; tambah item **[B9]** (mesin siklus-hidup/nurture); cross-link [A1]/[E1]→PAYMENT, [B8]/[B9]/[D1]→LIFECYCLE. Klarifikasi [A1]: switch = `MIDTRANS_ENV` `.env`+restart (bukan tombol admin=[B1]); pemblokir = kunci PRODUKSI approved.
