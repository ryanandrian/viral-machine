# 📖 F0 — PANDUAN TENANT LENGKAP (/docs) — TRACKER LINTAS-SESI

> **Mandat owner 2026-07-11:** lengkapi SELURUH panduan yang dibutuhkan calon tenant & tenant (baru/lama) di CMS `/docs` — selengkap & semudah mungkin dipahami, urutan jelas, profesional, **nol asumsi liar** (setiap klaim diverifikasi ke FE/DB live). Setelah 100%: **tombol Help di panel tenant** (buka `/docs` tab baru).
> **Status hidup item ini:** `SISA_KERJA_GO_LIVE.md` [D1] menunjuk ke file INI. Sesi baru: baca §Aturan → lanjut artikel ⬜ pertama dari atas.

## Aturan penulisan (WAJIB, tiap artikel)
1. **Verifikasi dulu, tulis kemudian:** buka halaman FE terkait (kode live) — nama tombol/menu/istilah di artikel = persis yang tenant lihat. Nol fitur karangan.
2. **Nol angka volatil dipatri** (harga/kuota/hari) — rujuk halaman live (Pricing/Billing) atau tulis "sesuai paket Anda".
3. **Dwibahasa penuh**: `body` (ID) + `body_en` (EN) — FE merender keduanya.
4. Bahasa awam; langkah bernomor; satu artikel = satu tujuan; screenshot opsional menyusul (owner).
5. Tulis via CMS `docs_articles` sebagai **draft** → lapor batch ke owner → **publish setelah owner cek**.
6. Update tabel di bawah + `PROGRESS` kolom tiap artikel selesai (status + tanggal + bukti singkat).

## Mekanisme teknis
- Tabel: `docs_articles` (slug PK, grp, grp_en, title, title_en, body, body_en, sort_order, status draft/published). FE `/docs` render published saja, urut `sort_order`, sidebar per-grup, cari, feedback ya/tidak.
- Tulis via Supabase REST service-role (`.env`). Slug baru = INSERT; draft lama = UPDATE body.
- `sort_order`: kelompok A=10-19, B=20-39, C=40-49, D=50-59, E=60-69 (artikel lama di-renumber saat batch-nya digarap).

## Daftar artikel (29) — status: ⬜ belum · 🟡 draft ditulis (nunggu cek owner) · ✅ published

### A. MULAI DI SINI (grp "Mulai di Sini" / "Getting Started")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 1 | `memulai-dengan-mesinviral` ✏️ada | Memulai dengan MesinViral | landing, DESAIN_PRODUK §pipeline | 🟡 draft 2026-07-11 (ID 1.814 + EN 1.822 chars, nol angka volatil) |
| 2 | `apa-itu-byok` ✏️published | Apa itu BYOK? (review-selaraskan) | /integrations | ⬜ |
| 3 | `onboarding` ✏️ada | Panduan Onboarding | /onboarding (2 langkah, indikator hijau) | ⬜ |
| 4 | `paket-dan-trial` 🆕 | Paket, Trial & Batasan | /pricing live, plan_limits DB | ⬜ |

### B. KREDENSIAL (grp "Kredensial" / "Credentials") — halaman /integrations
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 5 | `api-keys` ✏️ada | Kredensial AI: konsep & cara pakai | /integrations (pool, Simpan & Uji, Dipakai oleh) | ⬜ |
| 6 | `kunci-gratis-groq` 🆕 | Bikin kunci Groq GRATIS | console.groq.com + free_tier_note DB | ⬜ |
| 7 | `kunci-gratis-cloudflare` 🆕 | Bikin kunci Cloudflare GRATIS | dash.cloudflare.com + format ACCOUNT_ID:API_TOKEN (vault) | ⬜ |
| 8 | `kunci-gemini` 🆕 | Kunci Google Gemini (gratis harian) | aistudio.google.com + free_tier_note (catatan privasi) | ⬜ |
| 9 | `kunci-openai` 🆕 | Kunci OpenAI (berbayar) | platform.openai.com | ⬜ |
| 10 | `kunci-anthropic` 🆕 | Kunci Anthropic (berbayar) | console.anthropic.com | ⬜ |
| 11 | `kunci-elevenlabs` 🆕 | Kunci ElevenLabs (suara premium) + Edge TTS gratis | elevenlabs.io (scoped key!) + vault | ⬜ |
| 12 | `connect-youtube` ✏️ada | Hubungkan channel YouTube | /integrations (Hubungkan dengan Google, multi-koneksi) + syarat verifikasi telepon (thumbnail) | ⬜ |
| 13 | `notifikasi-telegram` 🆕 | Notifikasi Telegram | /integrations (chat ID) + jenis notif (per-run, review-pending, circuit-break) | ⬜ |

### C. CHANNEL & KONTEN (grp "Channel & Konten" / "Channels & Content")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 14 | `niches` ✏️ada | Memahami Niche | /niches (pustaka, 🔒 upgrade, pesan custom + Evaluasi) | ⬜ |
| 15 | `membuat-channel` 🆕 | Membuat & Mengaktifkan Channel | /channels/new + prasyarat + Uji channel + jeda/lanjut | ⬜ |
| 16 | `pengaturan-channel` 🆕 | Pengaturan Channel A–Z | /channels/[id] per-seksi (Pengaturan · Durasi & segmentasi · Caption · Hashtag · Branded · Operasional & mutu) | ⬜ |
| 17 | `schedule` ✏️ada | Jadwal Publish | /schedule + timezone + stok mengikuti jadwal | ⬜ |
| 18 | `ai-engines` ✏️ada | Mesin AI per-Channel | picker model channel (tier/Gratis/harga Rp) | ⬜ |

### D. OPERASIONAL HARIAN (grp "Operasional" / "Daily Operations")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 19 | `dashboard` 🆕 | Membaca Dashboard | /dashboard (KPI, Jadwal, Runs, Compliance, Biaya AI) | ⬜ |
| 20 | `runs-produksi` 🆕 | Memantau Produksi (Runs) | /runs + /runs/[id] live-tail + judul video | ⬜ |
| 21 | `review-video` 🆕 | Meninjau Video "Perlu Ditinjau" | /review (Pakai/Buang, TTL) vs YT Studio private | ⬜ |
| 22 | `analytics` ✏️ada | Analytics | /analytics vs tab kinerja-mesin per-channel + YT Studio | ⬜ |
| 23 | `self-learning` ✏️ada | Self-Learning | /insights + mekanisme bobot per-channel | ⬜ |
| 24 | `ai-slop-defense` ✏️ada | AI Slop Defense & Compliance | /compliance | ⬜ |
| 25 | `biaya-ai` 🆕 | Memahami Biaya AI (BYOK) | kartu Biaya AI + kolom Runs + label "bukan biaya kami" | ⬜ |

### E. TAGIHAN, AKUN & BANTUAN (grp "Akun & Bantuan" / "Account & Help")
| # | slug | Judul | Sumber verifikasi | Status |
|---|---|---|---|---|
| 26 | `billing` ✏️ada | Billing & Upgrade | /billing (GoPay+VA, Lanjutkan pembayaran, periode) | ⬜ |
| 27 | `kelola-akun` 🆕 | Pengaturan Akun | /settings (Profil, timezone, Bahasa & tema, Password) | ⬜ |
| 28 | `siklus-akun` 🆕 | Saat Trial/Langganan Berakhir | LIFECYCLE_NURTURE (banner→grace→suspended 30h→blocked→hapus + reaktivasi 1-klik + hak hapus data) | ⬜ |
| 29 | `bantuan` 🆕 | Bantuan & Masukan | /support + /feedback | ⬜ |
| 30 | `troubleshooting` ✏️ada | Troubleshooting | kasus nyata: kunci invalid, YT disconnect, QC gagal, circuit-break, thumbnail 403 | ⬜ |
| 31 | `faq` ✏️ada | FAQ | rangkum pertanyaan lintas-artikel | ⬜ |

*(31 baris karena artikel 29 lama dipecah: bantuan/troubleshooting/faq terpisah.)*

## Penutup (setelah 31 artikel ✅)
| Langkah | Detail | Status |
|---|---|---|
| Tombol **Help** di panel tenant | app-shell (ikon ? di topbar) → buka `/docs` **tab baru** (`target="_blank" rel="noopener"`), dwibahasa tooltip | ⬜ |
| Sapu silang | tiap halaman FE yang punya panduan → pastikan istilahnya konsisten dgn artikel | ⬜ |
| Update [D1] SISA_KERJA + PROGRESS journal | tutup administrasi | ⬜ |

## PROGRESS (entri terbaru di atas)
- **2026-07-11 (2)** — Artikel #1 `memulai-dengan-mesinviral` DRAFT di CMS (ID 1.814 + EN 1.822 chars, nol angka volatil) — menunggu cek owner. **Urutan disepakati malam ini: B17-F0 (batch kecil kurva) DULUAN → baru batch A panduan penuh.** Daftar 31 artikel: owner belum ketok eksplisit — konfirmasi sekali lagi saat mulai batch A. Konteks penulisan artikel niche/insight WAJIB selaras arsitektur baru (memory self-learning ⭐ 07-11).
- **2026-07-11** — Tracker dibuat; daftar 31 artikel diajukan ke owner (revisi dari 29: E dipecah). Menunggu ketok daftar → mulai batch A.
