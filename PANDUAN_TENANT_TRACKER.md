# 📖 F0 — PANDUAN TENANT LENGKAP (/docs) — TRACKER LINTAS-SESI

> **Mandat owner 2026-07-11:** lengkapi SELURUH panduan yang dibutuhkan calon tenant & tenant (baru/lama) di CMS `/docs` — selengkap & semudah mungkin dipahami, urutan jelas, profesional, **nol asumsi liar** (setiap klaim diverifikasi ke FE/DB live). Setelah 100%: **tombol Help di panel tenant** (buka `/docs` tab baru).
> **Status hidup item ini:** `SISA_KERJA_GO_LIVE.md` [D1] menunjuk ke file INI. Sesi baru: baca §Aturan → lanjut artikel ⬜ pertama dari atas.

## Aturan penulisan (WAJIB, tiap artikel)
1. **Verifikasi dulu, tulis kemudian:** buka halaman FE terkait (kode live) — nama tombol/menu/istilah di artikel = persis yang tenant lihat. Nol fitur karangan.
2. **Nol angka volatil dipatri** (harga/kuota/hari) — rujuk halaman live (Pricing/Billing) atau tulis "sesuai paket Anda".
2b. **Katalog AI = HIDUP, jangan dipatok (owner 2026-07-11):** provider & model terus bertambah (katalog admin, tanpa deploy). Dilarang kalimat yang menyiratkan daftar tertutup ("mendukung N penyedia", "modelnya adalah X/Y/Z"). Sumber kebenaran daftar = layar /integrations & pemilih model channel; artikel per-vendor dibingkai "salah satu penyedia yang didukung — daftar lengkap & terbaru selalu di aplikasi, bertambah seiring waktu"; artikel konsep mengajarkan CARA MEMBACA katalog (tier/Gratis/harga) agar tetap benar berapa pun isinya kelak.
3. **Dwibahasa penuh**: `body` (ID) + `body_en` (EN) — FE merender keduanya.
4. Bahasa awam; langkah bernomor; satu artikel = satu tujuan; screenshot opsional menyusul (owner).
5. Tulis via CMS `docs_articles` sebagai **draft** → lapor batch ke owner → **publish setelah owner cek**.
6. Update tabel di bawah + `PROGRESS` kolom tiap artikel selesai (status + tanggal + bukti singkat).

## Mekanisme teknis
- Tabel: `docs_articles` (slug PK, grp, grp_en, title, title_en, body, body_en, sort_order, status draft/published). FE `/docs` render published saja, urut `sort_order`, sidebar per-grup, cari, feedback ya/tidak.
- Tulis via Supabase REST service-role (`.env`). Slug baru = INSERT; draft lama = UPDATE body.
- **⚖️ ATURAN URUTAN (owner 2026-07-11): daftar & sort_order WAJIB mengikuti ALUR PROSES BISNIS tenant** (kenal→daftar→siapkan kunci→bangun channel→running harian→evaluasi→akun/bantuan) — bukan pengelompokan tematik. 6 grup = tahap perjalanan. `sort_order`: T1=10-19 · T2=20-29 · T3=40-49 · T4=50-59 · T5=60-69 · T6=70-79 (artikel lama di-renumber + grp disesuaikan saat batch-nya digarap).
- **⚖️ STRUKTUR BAKU ISI (disepakati 2026-07-11):** tiap artikel = ① tujuan-1-kalimat ② prasyarat+link ③ lokasi layar (nama menu/tombol PERSIS) ④ langkah bernomor + TANDA-BERHASIL per langkah (varian: tutorial/konsep/referensi-layar/penolong) ⑤ kamus istilah layar ⑥ jebakan umum dari insiden nyata ⑦ bila-gagal → link troubleshooting ⑧ link artikel selanjutnya. Ukuran lulus = tenant awam bisa MELAKSANAKAN sampai berhasil tanpa bertanya.

## Daftar artikel (31) — URUT ALUR PROSES BISNIS (owner 2026-07-11) — status: ⬜ belum · 🟡 draft (nunggu cek owner) · ✅ published

### TAHAP 1 — MULAI DI SINI: kenal → putuskan → masuk (grp "Mulai di Sini" / "Getting Started")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 1 | `memulai-dengan-mesinviral` ✏️ada | Memulai dengan MesinViral | landing, DESAIN_PRODUK §pipeline | ✅ published (terverifikasi DB 2026-07-11 — status sudah published; tak disentuh seeding) |
| 2 | `apa-itu-byok` ✏️published | Apa itu BYOK? (review-selaraskan) | /integrations | ✅ published 2026-07-11 |
| 3 | `paket-dan-trial` 🆕 | Paket, Trial & Batasan | /pricing live, plan_limits DB | ✅ published 2026-07-11 |
| 4 | `onboarding` ✏️ada | Panduan Onboarding | /onboarding (2 langkah, indikator hijau) | ✅ published 2026-07-11 |

### TAHAP 2 — SIAPKAN KREDENSIAL: bekal sebelum mesin bisa jalan (grp "Siapkan Kredensial" / "Set Up Credentials") — halaman /integrations
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 5 | `api-keys` ✏️ada | Kredensial AI: konsep & cara pakai | /integrations (pool, Simpan & Uji, Dipakai oleh) | ✅ published 2026-07-11 |
| 6 | `kunci-gratis-groq` 🆕 | Bikin kunci Groq GRATIS | console.groq.com + free_tier_note DB | ✅ published 2026-07-11 |
| 7 | `kunci-gratis-cloudflare` 🆕 | Bikin kunci Cloudflare GRATIS | dash.cloudflare.com + format ACCOUNT_ID:API_TOKEN (vault) | ✅ published 2026-07-11 |
| 8 | `kunci-gemini` 🆕 | Kunci Google Gemini (gratis harian) | aistudio.google.com + free_tier_note (catatan privasi) | ✅ published 2026-07-11 |
| 9 | `kunci-openai` 🆕 | Kunci OpenAI (berbayar) | platform.openai.com | ✅ published 2026-07-11 |
| 10 | `kunci-anthropic` 🆕 | Kunci Anthropic (berbayar) | console.anthropic.com | ✅ published 2026-07-11 |
| 11 | `kunci-elevenlabs` 🆕 | Kunci ElevenLabs (suara premium) + Edge TTS gratis | elevenlabs.io (scoped key!) + vault | ✅ published 2026-07-11 |
| 12 | `connect-youtube` ✏️ada | Hubungkan channel YouTube | /integrations (Hubungkan dengan Google, multi-koneksi) + syarat verifikasi telepon (thumbnail) | ✅ published 2026-07-11 |
| 13 | `notifikasi-telegram` 🆕 | Notifikasi Telegram | /integrations (chat ID) + jenis notif (per-run, review-pending, circuit-break) | ✅ published 2026-07-11 |

### TAHAP 3 — BANGUN CHANNEL: dari niche sampai aktif (grp "Bangun Channel" / "Build Your Channel")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 14 | `niches` ✏️ada | Memahami Niche | /niches (pustaka, 🔒 upgrade, pesan custom + Evaluasi) | ✅ published 2026-07-11 |
| 15 | `membuat-channel` 🆕 | Membuat & Mengaktifkan Channel | /channels/new + prasyarat + Uji channel + jeda/lanjut | ✅ published 2026-07-11 |
| 16 | `pengaturan-channel` 🆕 | Pengaturan Channel A–Z | /channels/[id] per-seksi (Pengaturan · Durasi & segmentasi · Caption · Hashtag · Branded · Operasional & mutu) | ✅ published 2026-07-11 |
| 17 | `ai-engines` ✏️ada | Mesin AI per-Channel | picker model channel (tier/Gratis/harga Rp) | ✅ published 2026-07-11 |
| 18 | `schedule` ✏️ada | Jadwal Publish | /schedule + timezone + stok mengikuti jadwal | ✅ published 2026-07-11 |

### TAHAP 4 — OPERASIONAL HARIAN: running (grp "Operasional Harian" / "Daily Operations")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 19 | `dashboard` 🆕 | Membaca Dashboard | /dashboard (KPI, Jadwal, Runs, Compliance, Biaya AI, chip Kurva) | ✅ published 2026-07-11 |
| 20 | `runs-produksi` 🆕 | Memantau Produksi (Runs) | /runs + /runs/[id] live-tail + judul video | ✅ published 2026-07-11 |
| 21 | `review-video` 🆕 | Meninjau Video "Perlu Ditinjau" | /review (Pakai/Buang, TTL) vs YT Studio private | ✅ published 2026-07-11 |
| 22 | `biaya-ai` 🆕 | Memahami Biaya AI (BYOK) | kartu Biaya AI + kolom Runs + label "bukan biaya kami" | ✅ published 2026-07-11 |

### TAHAP 5 — EVALUASI & BERKEMBANG: makin pintar (grp "Evaluasi & Berkembang" / "Evaluate & Grow")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 23 | `analytics` ✏️ada | Analytics | /analytics vs tab kinerja-mesin per-channel + YT Studio | ✅ published 2026-07-11 |
| 24 | `self-learning` ✏️ada | Self-Learning (+ Kurva Belajar) | /insights + Kurva Belajar (B17-F0 live) + mekanisme bobot per-channel | ✅ published 2026-07-11 |
| 25 | `ai-slop-defense` ✏️ada | AI Slop Defense & Compliance | /compliance | ✅ published 2026-07-11 |

### TAHAP 6 — TAGIHAN, AKUN & BANTUAN (grp "Akun & Bantuan" / "Account & Help")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 26 | `billing` ✏️ada | Billing & Upgrade | /billing (GoPay+VA, Lanjutkan pembayaran, periode) | ✅ published 2026-07-11 |
| 27 | `kelola-akun` 🆕 | Pengaturan Akun | /settings (Profil, timezone, Bahasa & tema, Password) | ✅ published 2026-07-11 |
| 28 | `siklus-akun` 🆕 | Saat Trial/Langganan Berakhir | LIFECYCLE_NURTURE (banner→grace→suspended 30h→blocked→hapus + reaktivasi 1-klik + hak hapus data) | ✅ published 2026-07-11 |
| 29 | `bantuan` 🆕 | Bantuan & Masukan | /support + /feedback | ✅ published 2026-07-11 |
| 30 | `troubleshooting` ✏️ada | Troubleshooting | kasus nyata: kunci invalid, YT disconnect, QC gagal, circuit-break, thumbnail 403 | ✅ published 2026-07-11 |
| 31 | `faq` ✏️ada | FAQ | rangkum pertanyaan lintas-artikel (ditulis TERAKHIR) | ✅ published 2026-07-11 |

*(Perubahan urutan vs daftar tematik lama, keputusan owner "urut proses bisnis": BYOK maju ke #2 · Paket & Trial sebelum Onboarding · Biaya AI masuk Operasional Harian · Compliance masuk Evaluasi.)*

## Penutup (setelah 31 artikel ✅)
| Langkah | Detail | Status |
|---|---|---|
| Tombol **Help** di panel tenant | app-shell (ikon ? di topbar) → buka `/docs` **tab baru** + **help KONTEKSTUAL per-halaman** (ikon ? di samping judul → `/docs?a=<slug>`; mandat owner "pairing lokasi sesuai") | ✅ LIVE `3e6edaa` · ⬆️ di-upgrade SOFTCODE `5307e9b` 2026-07-12 (pemetaan di DB `help_links` + admin Content→"Tombol Help"; seed=diff nol; LIVE `eb4937c` 2026-07-12 00:24, bundle terverifikasi) |
| Artikel #32 `niche-studio` | hasil inventarisasi owner: satu-satunya halaman tenant tanpa panduan → ditulis + published (sort 45, T3) | ✅ seeded 2026-07-11 |
| Sapu silang | tiap halaman FE yang punya panduan → pastikan istilahnya konsisten dgn artikel | ✅ 2026-07-16 — korpus 1.504 label FE (Bi + non-Bi diverifikasi manual) × 31 artikel; **5 kelas mismatch nyata DIPERBAIKI di CMS** ("Kirim/New ticket"→**Tiket baru** · "Uji/Test channel"→**Uji produksi channel / Test now (private)** · EN billing **Continue payment**/**Choose & pay** · **Use in a channel** · **Skip for now, finish later**); sisanya = alarm-palsu (judul-bagian baku/analogi/rujukan-judul-artikel). ⚠️ TEMUAN-SAMPINGAN (usulan, BELUM dikerjakan): halaman `/support` tampak SATU-BAHASA (tombol "Tiket baru", header "Bantuan" tanpa `Bi`) — pelanggaran dwibahasa §3.5 di FE, butuh ketok owner. |
| Update [D1] SISA_KERJA + PROGRESS journal | tutup administrasi | ✅ |

## PROGRESS (entri terbaru di atas)
- **2026-07-16** — ✅ SAPU-SILANG ISTILAH TUNTAS (lihat baris tabel Penutup; 5 kelas fix di CMS langsung-live [artikel published], nol sentuh FE). [D1]-panduan kini TUNTAS SELURUHNYA kecuali koreksi-isi owner bila ada + usulan dwibahasa /support (menunggu ketok).
- **2026-07-11 (5)** — ✅ **SELURUH 31 ARTIKEL PUBLISHED** (perintah eksplisit owner "publish seluruh dokumen, agar dapat saya preview di marketing site"). Verifikasi per-widget: query PERSIS FE /docs dijalankan sbg ANON → 31 artikel tampil, 6 grup, urutan proses-bisnis benar; situs /docs HTTP 200. Owner mem-preview langsung di https://mesinviral.com/docs — koreksi kapan pun (edit via admin Content / minta Claude revisi). Sisa [D1]: koreksi owner (bila ada) + tombol Help (FE, mandat terpisah) + sapu silang istilah.
- **2026-07-11 (4)** — 🏁 **SELURUH 30 ARTIKEL DITULIS & DI-SEED ke CMS sebagai draft** (mandat owner "tuntaskan seluruh panduan, koreksi setelah selesai; hanya seeding DB, nol BE/FE"). Proses: harvest label UI persis dari kode FE live (integrations/onboarding/niches/schedule/review/billing/settings/analytics/channels/runs/docs-renderer) + fakta katalog dari DB (`ai_providers.free_tier_note`) → 30 artikel struktur-baku 8-bagian, dwibahasa penuh, urut proses bisnis (sort 10-75, 6 grup), markdown sesuai kemampuan renderer (nol tabel md). Verifikasi DB pasca-seed: 31 baris = 6 grup benar, 30 draft + 1 published (#1 ternyata SUDAH published di DB — tak disentuh), semua body ID+EN >800 chars. Catatan: `apa-itu-byok` (published lama 482c satu-bahasa) kini draft ber-isi baru → sementara hilang dari /docs sampai owner publish. **MENUNGGU: koreksi owner atas 30 draft → publish → lalu tombol Help (perlu sentuh FE = mandat terpisah).**
- **2026-07-11 (3)** — Mandat owner "tuntaskan panduan tenant" + 2 aturan dipatri: (a) daftar URUT ALUR PROSES BISNIS (tabel di atas disusun ulang: 6 tahap kenal→kunci→bangun→running→evaluasi→akun); (b) STRUKTUR BAKU ISI 8-bagian per artikel (lihat §Mekanisme) — ukuran lulus = tenant awam bisa melaksanakan sampai berhasil tanpa bertanya. Siap mulai Tahap 1 (#2-#4) begitu urutan dikonfirmasi owner.
- **2026-07-11 (2)** — Artikel #1 `memulai-dengan-mesinviral` DRAFT di CMS (ID 1.814 + EN 1.822 chars, nol angka volatil) — menunggu cek owner. **Urutan disepakati malam ini: B17-F0 (batch kecil kurva) DULUAN → baru batch A panduan penuh.** Daftar 31 artikel: owner belum ketok eksplisit — konfirmasi sekali lagi saat mulai batch A. Konteks penulisan artikel niche/insight WAJIB selaras arsitektur baru (memory self-learning ⭐ 07-11).
- **2026-07-11** — Tracker dibuat; daftar 31 artikel diajukan ke owner (revisi dari 29: E dipecah). Menunggu ketok daftar → mulai batch A.
