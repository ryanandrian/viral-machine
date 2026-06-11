# Addendum v4 untuk Claude Design — MesinViral.com (Konten Multi-Bahasa)

> **Cara pakai:** Copy seluruh isi file ini, paste ke Claude Design SEBELUM minta Batch yang menyentuh Landing (A1), Onboarding (C4), Channel Detail (D3), Config Voice (D10), Config Captions (D15), atau Admin Catalog (E2).
> Ini ADDENDUM keempat — menumpuk di atas brief utama + addendum v1, v2, v3. Konten sebelumnya tetap valid KECUALI bagian yang ditandai **REVISI** di bawah.

---

## 0. Apa yang Berubah di v4 (TL;DR)

Keputusan produk baru: **tenant bisa memilih bahasa konten** (narasi TTS + caption + script) yang diproduksi — **bukan hanya Indonesia/English, tapi multi-bahasa** (Malaysia, Filipina, Thailand, Vietnam, dst.). Brief utama (`CLAUDE_DESIGN_BRIEF.md`) sudah di-update. Ringkasan delta:

1. **Level setting = PER-CHANNEL** (1 channel = 1 bahasa). BUKAN per-video. Override per-konten = future, JANGAN didesain sekarang.
2. **A1 Landing Page** → tambah **Konten Multi-Bahasa sebagai killer feature** (selling point ke calon tenant) + row di comparison table + 1 FAQ. **(INI PENTING — fitur ini harus tampil sebagai nilai jual di halaman marketing, bukan cuma config internal.)**
3. **C4 Onboarding (Pilih Niche & Voice)** → tambah dropdown **"Bahasa Konten"**, ditempatkan **SEBELUM** voice selection (voice difilter oleh bahasa).
4. **D3 Channel Detail → tab Settings** → tambah field bahasa konten + peringatan non-retroaktif.
5. **D10 Config Voice** → "filter by language" sekarang **terikat** ke bahasa channel.
6. **D15 Config Captions** → caption mengikuti bahasa konten; tambah catatan font non-Latin.
7. **E2.5 Admin Content Languages** → **TAB BARU** di Catalog Management (catalog bahasa config-driven, admin-managed).
8. Daftar bahasa **TIDAK hardcode** — render dari catalog DB (pola sama dgn pricing/niche). Di mockup pakai data contoh, tapi struktur = list dari DB.

**Yang TIDAK berubah:** semua screen lain, design system, pricing/niche dari v3. Jangan di-redo. **Bahasa UI app (toggle ID/EN via next-intl) BEDA dari bahasa konten — jangan dicampur.**

---

## 1. Konsep: Bahasa Konten vs Bahasa UI (WAJIB dibedakan)

- **Bahasa UI** = bahasa antarmuka aplikasi (tombol, label, menu). Toggle ID/EN, sudah ada. TIDAK berubah.
- **Bahasa Konten** = bahasa video yang DIPRODUKSI mesin: narasi (TTS), caption/subtitle, dan script. Ini fitur BARU. Di-set **per channel**.

Contoh nyata: seorang tenant Indonesia bisa punya channel "Misteri Samudra" (Bahasa Indonesia) DAN channel "Ocean Mysteries" (English) DAN channel "Misteri Lautan" (Bahasa Malaysia) — masing-masing channel satu bahasa, dikelola dari satu dashboard.

**Kenapa per-channel, bukan per-video:** algoritma YouTube memihak channel mono-bahasa (audiens konsisten); voice TTS bahasa-spesifik; tren & keyword niche bersifat region/bahasa. Jadi bahasa = properti channel.

---

## 2. ⭐ A1 Landing Page — Konten Multi-Bahasa sebagai SELLING POINT

Ini permintaan eksplisit: fitur multi-bahasa **harus dikomunikasikan ke calon tenant** di landing page, bukan disembunyikan di config.

**Killer Features section** (sekarang **6 card**, bukan 5) — tambah card:

> **🌐 Konten Multi-Bahasa**
> "Produksi narasi + caption dalam Bahasa Indonesia, English, dan bahasa Asia Tenggara (Malaysia, Filipina, Thailand, Vietnam). Pilih bahasa per channel — jangkau audiens lintas negara dari satu platform."

- Visual treatment: ikon globe 🌐 + deretan flag/locale chip kecil (🇮🇩 🇬🇧 🇲🇾 🇵🇭 🇹🇭 🇻🇳) sebagai aksen.
- Tone tetap premium, calm (jangan norak). Sub-glow violet seperti AI-feature card lain.

**Comparison table** — tambah row **"Multi-language content"**: MesinViral ✅, kompetitor mayoritas ❌ (ini diferensiasi).

**FAQ** — tambah 1 accordion:
> Q: "Bisa bikin konten dalam bahasa selain Indonesia (English, Malaysia, Thailand)?"
> A: "Bisa. Pilih bahasa konten per channel saat setup. Mesin produksi narasi, caption, dan script dalam bahasa itu. Bahasa official: Indonesia & English; bahasa Asia Tenggara lain tersedia bertahap."

(Opsional, kalau pas) sebut juga di hero sub-headline atau How-It-Works sebagai bukti jangkauan global.

---

## 3. C4 Onboarding — Step "Pilih Niche & Voice"

Urutan field jadi: **Niche → Bahasa Konten → Voice → Brand color.**

Tambah dropdown **"Bahasa Konten"** di antara niche grid dan voice selection:
- Default ter-pilih: **Bahasa Indonesia (id-ID)**.
- Item dropdown: nama bahasa + flag + badge tier. Official (Indonesia, English) tanpa badge; bahasa SEA dengan badge kecil **"Eksperimental"**.
- Helper text: "Menentukan bahasa narasi, caption & script untuk semua video channel ini."
- ⚠️ Microcopy: "Mengubah bahasa akan mengubah pilihan voice yang tersedia."
- **Voice dropdown di bawahnya hanya menampilkan voice yang mendukung bahasa terpilih** (filtered).

---

## 4. D3 Channel Detail — Tab Settings

Tab Settings sekarang: **bahasa konten**, niche, voice, brand.
- Field "Bahasa Konten" (dropdown sama seperti C4).
- Saat diubah → tampilkan **callout peringatan**: "Bahasa baru hanya berlaku untuk video yang diproduksi setelah ini (tidak retroaktif). Voice akan di-reset/filter sesuai bahasa baru."

---

## 5. D10 Config Voice & D15 Config Captions

**D10 Voice:** "Filter by language" defaultnya = bahasa konten channel. Voice grid hanya tampilkan voice yang support bahasa itu. Filter lain (gender, style, age) tetap.

**D15 Captions:** caption otomatis ikut bahasa konten (dari TTS) — tenant TIDAK set bahasa caption di sini, hanya style. Tambah callout:
> ⚠️ "Untuk bahasa skrip non-Latin (mis. Thailand), pilih font yang mendukung karakter bahasa tersebut. Font tanpa dukungan akan tampil sebagai kotak." — font picker auto-filter sesuai bahasa channel.

---

## 6. E2.5 Admin — Tab Content Languages (TAB BARU di Catalog Management)

Tab kelima di E2 Catalog Management (setelah AI Models, Music, Niche, Voice Templates).

**Purpose:** sysadmin kelola catalog bahasa konten yang tersedia untuk tenant. Config-driven — sama pola dengan pricing & niche, BUKAN hardcode di kode.

**Layout:** data table, kolom per bahasa:
- `locale` (BCP-47: id-ID, en-US, ms-MY, fil-PH, th-TH, vi-VN, …)
- `display_name`
- `tts_providers_supported` (badge: ElevenLabs / OpenAI TTS / Edge)
- `quality_tier` (official / experimental)
- `caption_font` (font default dengan glyph coverage bahasa itu)
- `is_active` (toggle → langsung mempengaruhi dropdown di C4 + D3)

**Row actions:** edit, toggle active, preview voice sample.
**Seed contoh untuk mockup:** id-ID + en-US = official aktif; ms-MY, fil-PH, th-TH, vi-VN = experimental.

---

## 7. Catatan untuk Konsistensi Mockup

- Pakai data contoh nyata di dropdown (Indonesia, English, Malaysia, Filipina, Thailand, Vietnam) — tapi secara konseptual ini list dari DB, bukan literal hardcode.
- Flag/locale chip boleh dipakai sebagai aksen visual, tapi jaga estetika tetap premium & calm (bukan "language switcher" norak).
- JANGAN desain UI override bahasa per-video — itu future scope.
- Screen inventory: E2.5 = tab baru di E2 (bukan screen top-level baru), jadi hitungan screen utama tetap.
