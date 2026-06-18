# Branded Content — Arsitektur Lengkap (CTA · Logo · Link Landing)

> **Sumber kebenaran status & arsitektur** untuk fitur branding per-channel. Dirujuk dari `PROGRESS.md`.
> Spec konsep: `MULTI_FORMAT_STUDIO.md §6 "Branded Content layer"`. Dokumen ini = detail teknis + status NYATA (hasil audit kode/DB 2026-06-19, kutip file:line — bukan asumsi).
> **Aturan anti-ambigu:** status branded content **hanya** di sini (dan ringkasan checklist di PROGRESS yang menaut ke sini). Bila ada dokumen lain menyebut status berbeda → **dokumen ini menang**.

---

## 1. Tujuan & Ruang Lingkup

Tiga kemampuan branding yang bisa diatur **per-channel** oleh tenant:

1. **Custom CTA / soft-sell** — izinkan SATU sebutan brand halus dalam narasi (anti hard-sell tetap berlaku).
2. **Logo overlay** — tempel logo tenant pada video di posisi, ukuran, dan opacity tertentu.
3. **Link landing di deskripsi** — sisipkan URL landing page tenant di awal/akhir deskripsi YouTube.

**Prinsip:** semua **opsional & nullable** (default = tanpa branding) → non-breaking; channel lama tetap jalan tanpa perubahan.

---

## 2. Status Ringkas (matriks)

| Fitur | DB | BE (mesin) | FE (UI tenant) | Storage |
|---|---|---|---|---|
| Custom CTA / soft-sell | ✅ | ✅ | ❌ | — |
| Logo overlay (posisi/ukuran/opacity) | ✅ | ✅ | ❌ | ❌ (bucket logo belum ada) |
| Link landing di deskripsi | ✅ | ✅ | ❌ | — |

**Inti:** mesin & DB **sudah jadi & tervalidasi**; tenant **belum punya UI** untuk mengaturnya → saat ini nilai = default (tanpa logo, tanpa link, CTA implicit). Edit hanya mungkin via DB langsung.

---

## 3. Data Layer (DB)

**Migrasi:** `migrations/0015_branded_content.sql` — menambah kolom ke tabel `channels`:

| Kolom | Tipe | Default | Fungsi |
|---|---|---|---|
| `cta_mode` | text | `'implicit'` | `implicit` (tanpa brand) \| `soft_sell` (izinkan 1 sebutan brand) |
| `brand_name` | text | NULL | nama brand untuk soft-sell |
| `brand_cta_text` | text | NULL | override teks CTA soft-sell (opsional) |
| `brand_logo` | text | NULL | path lokal **atau** URL http(s) logo untuk overlay |
| `logo_position` | text | `'top-right'` | posisi overlay (top-left/top-right/bottom-left/bottom-right) |
| `logo_size` | numeric | `0.12` | fraksi lebar video (0–1) |
| `logo_opacity` | numeric | `0.85` | 0–1 |
| `landing_link` | text | NULL | URL landing page di deskripsi |
| `link_position` | text | `'bottom'` | `top` \| `bottom` (posisi di deskripsi) |

Terkait: `format_profiles.default_cta_mode` (migr `0012`) — default cta_mode per format-profile (bisa di-override channel).

**Penulisan (rencana FE):** kolom `channels` ini "config bersih" → boleh ditulis via **RLS UPDATE** langsung (pola sama tab Settings channel) atau RPC bila ingin validasi ketat. **TIDAK** menyentuh kolom billing.

---

## 4. Backend — Bagaimana Diterapkan (semua SUDAH JADI)

### 4.0 Plumbing config
`src/intelligence/config.py:27–63` — `TenantConfig` memuat semua field branding, dan `from_channel_row()` mem-*thread* dari row `channels` (default aman bila NULL). Dipakai pipeline saat produksi.

### 4.1 Custom CTA / soft-sell
- `src/intelligence/script_engine.py:285` — parameter `cta_mode`, `brand_name`, `brand_cta_text`.
- `:355–356` — bila `cta_mode == 'soft_sell'` **dan** `brand_name` ada → suntik `soft_sell_block` ke prompt: izinkan **SATU** sebutan brand halus (mis. "…bersama [brand]"). Hard-sell tetap dilarang oleh guard anti-promo.
- Bila `implicit` (default) → tidak ada sebutan brand.

### 4.2 Logo overlay
- `src/production/video_renderer.py:937–941` — pass terpisah `_overlay_logo()`, **fail-soft** (kalau gagal, video tetap jadi tanpa logo), hanya jalan bila `brand_logo` ada.
- `_resolve_logo()` `:1051–1063` — resolve `brand_logo`: path lokal → langsung; URL http(s) → unduh ke `brand_logo_dl.png`.
- Overlay via FFmpeg menggunakan `logo_position`, `logo_size` (fraksi lebar), `logo_opacity`.
- Berlaku untuk `render_mode` **image_sequence** & **ai_video** (MULTI_FORMAT §6).
- Catatan: `drawtext` hook-title (`:170,805`) terpisah dari logo overlay.

### 4.3 Link landing di deskripsi
- `src/distribution/youtube_publisher.py:128` — bangun deskripsi (CTA + hashtag dijamin masuk).
- `:153–155` — sisipkan `landing_link` di **atas** atau **bawah** deskripsi sesuai `link_position`. (Pinned-comment mustahil via API → pakai link deskripsi.)
- Bila `landing_link` NULL → deskripsi normal tanpa link.

---

## 5. Frontend — Rencana Panel "Branded" (BELUM dibangun)

**Lokasi:** tab **"Branded"** di `/channels/[id]` (atau langkah opsional onboarding/`config`). Komponen reusable: pola posisi mengikuti `config/visual/caption` (pemilih posisi), `Bi` (i18n id/en), token kartu/slider.

**Isi panel:**
- **CTA:** radio `implicit | soft_sell`; bila `soft_sell` → input `brand_name` (+ opsional `brand_cta_text`).
- **Logo:** upload file → simpan ke storage → URL ke `brand_logo`; **pemilih posisi** (grid 4 sudut); slider `logo_size` & `logo_opacity`; **preview** overlay di mockup 9:16.
- **Link landing:** input `landing_link` + toggle posisi `top|bottom`.

**Tulis ke DB:** RLS UPDATE pada `channels` (kolom config) — pola sama tab Settings channel.

**Ukuran logo (bounds platform):** rencana `logo_size` dibatasi rentang platform (mis. via katalog `branding_config`) supaya logo tak menutupi konten; posisi & ukuran tetap pilihan tenant dalam bounds tsb. *(branding_config = item katalog yang belum dibuat; sampai ada, pakai default `0.12` + validasi FE sederhana.)*

---

## 6. Storage Logo (BELUM ada)

- Saat ini storage hanya untuk **buffer video** (Biznet S3, `S3_BUCKET`, dipakai `/api/review/preview`). **Belum ada** bucket khusus logo.
- `MULTI_FORMAT_STUDIO.md §6:117` mencatat perlu **storage bucket `brand_logo`**.
- BE `_resolve_logo` sudah menerima **URL http(s)** → cukup: FE upload logo ke bucket (Supabase Storage **atau** path Biznet S3) → dapat URL publik/presigned → simpan ke `channels.brand_logo`. Tidak perlu ubah BE.

---

## 7. Backlog (yang HARUS dibangun)

- [ ] **FE** — panel "Branded" di `/channels/[id]`: CTA (radio + brand_name) · upload logo + pemilih posisi + slider ukuran/opacity + preview · landing_link + posisi. Tulis via RLS UPDATE `channels`.
- [ ] **Storage** — bucket/lokasi upload logo + route upload → simpan URL ke `brand_logo`.
- [ ] *(opsional)* katalog `branding_config` untuk bounds ukuran/posisi platform.

**Sudah jadi (jangan diulang):** DB (migr 0015) ✅ · BE soft-sell CTA ✅ · BE logo overlay ✅ · BE link deskripsi ✅.

---

## 8. Referensi File
- DB: `migrations/0015_branded_content.sql`, `migrations/0012_multiformat_presets.sql` (`default_cta_mode`)
- BE: `src/intelligence/config.py:27–63` · `src/intelligence/script_engine.py:285,355` · `src/production/video_renderer.py:937,1051` · `src/distribution/youtube_publisher.py:128,153`
- Spec: `MULTI_FORMAT_STUDIO.md §6` (baris 100–103, 116–117)
- Status di PROGRESS: cari "Branded Content" (checklist menaut ke dokumen ini)
