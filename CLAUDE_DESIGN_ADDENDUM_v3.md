# Addendum v3 untuk Claude Design — MesinViral.com (Niche Model + Pricing Config-Driven)

> **Cara pakai:** Copy seluruh isi file ini, paste ke Claude Design SEBELUM minta Batch yang menyentuh Config (D18) atau Admin (E2.3, E5).
> Ini ADDENDUM ketiga — menumpuk di atas brief utama + addendum v1 & v2. Konten sebelumnya tetap valid KECUALI bagian yang secara eksplisit ditandai **SUPERSEDED** di bawah.

---

## 0. Apa yang Berubah di v3 (TL;DR)

Sejak addendum v2 disampaikan, ada keputusan produk baru soal **model niche** dan **pricing**. Brief utama (`CLAUDE_DESIGN_BRIEF.md`) sudah di-update. Ringkasan delta:

1. **D18 Config — Niches** → **DIREVISI TOTAL**. Spec D18 di addendum v2 **SUPERSEDED** oleh versi di file ini.
2. **E2.3 Admin Niche Library** → **DIPERLUAS** jadi drawer 6-tab + monthly release scheduler + exclusivity pipeline.
3. **E5 Admin Pricing Config** → **SCREEN BARU** (single source of truth semua harga).
4. **Prinsip baru lintas-screen:** semua nominal harga di-render dari `pricing_config` (DB), pakai placeholder `{{pricing.<key>}}` di mockup — **TIDAK ADA harga hardcode** di JSX.
5. **Screen inventory: 38 → 39.**

**Yang TIDAK berubah:** D1–D5, D6–D17, D19–D21, semua Auth/Onboarding/Marketing, design system Batch 1. Jangan di-redo.

---

## 1. Konteks Produk: Niche Model 3-Layer

Supaya desain D18 & E2.3 koheren, pahami model niche-nya:

- **Layer 1 — Broad Niche (Identity DNA):** 4 niche default aktif (Misteri Alam Semesta, Sejarah Kelam, Misteri Samudra, Fakta Menarik). Tiap niche punya "DNA": keywords, voice profile, visual style, mood priority, scoring criteria, default hashtags, **tag pool**.
- **Layer 2 — Sub-Tag (Granular):** 20-30 tag per niche (admin-curated). Dipakai untuk variety tracking + YouTube hashtag granular.
- **Layer 3 — Topic:** spesifik per video, di-generate AI. (Tidak ada UI khusus.)

**Cara catalog tumbuh:**
- **Monthly release** — admin rilis 1-2 niche baru/bulan, email blast ke tenant ("✨ Niche baru bulan ini").
- **On-demand custom** — tenant request niche custom, 2 tier (lihat D18).

---

## 2. ‼️ D18 Config — Niches — **VERSI BARU (SUPERSEDES addendum v2)**

`/config/niches` — Tenant browse catalog, aktifkan niche untuk channel, request custom.

**Layout:**

1. **Header:** "Niches" + counter "**3 dari 4 niche aktif** (Pro plan)".

2. **Active Niches section (top):** 4-col grid card:
   - Thumbnail moodboard (3-image collage)
   - Niche name (Bahasa Indonesia) + keyword preview chips (3-5)
   - Stats: "47 video produced, avg 2.3K views"
   - Active toggle (deactivate = freeup slot)
   - "Edit per-channel" link (kalau multi-channel)
   - Empty slot card kalau quota tersisa: dashed border "+ Add niche from catalog".

3. **Niche Catalog Browser:**
   - Filter tabs: All (4) / Active / Inactive / Premium (locked) / Custom (add-on)
   - Search bar
   - 3-col grid: thumbnail + name + 1-line desc + "▶ Sample" mini player
   - Button state: "Activate" (slot tersisa) / "Swap with..." dropdown (slot penuh) / "🔒 Premium" lock badge.

4. **🌟 "New This Month" Section** (monthly release showcase):
   - Featured horizontal scroll niche baru bulan ini (released by admin)
   - Each card: moodboard + name + "Released [tanggal]" + desc + "▶ Sample video" + "Activate" CTA
   - Subtle glow accent untuk yang very-new (< 7 hari).

5. **Custom Niche Request — DUAL OPTION** (large card, subtle violet gradient):
   - 🎨 Headline: "Tidak menemukan niche yang cocok?"
   - **Dua option card side-by-side:**

     **🌍 Public Niche** (Card 1)
     - Harga: `{{pricing.custom_niche_public_90d}}` *(render dari DB — placeholder, JANGAN tulis "Rp 299K" literal)*
     - "90 hari exclusive untuk channel-mu, lalu masuk public catalog"
     - "Affordable. Recommended untuk solo creator."
     - "Request Public Niche" button → modal form

     **🔒 Permanent Private** (Card 2)
     - Harga: `{{pricing.custom_niche_private}}` *(render dari DB)*
     - "Never public. Permanent exclusive untuk channel-mu."
     - "Premium positioning untuk agency."
     - "Request Private Niche" button → modal form

   - Modal form (sama untuk both): niche idea (textarea), target audience (chips), sample YT channel URLs, color palette + voice preferences, estimated viral angle, expected use case.
   - SLA badge: "3-5 hari delivery".

6. **Sub-Tag Pool per Active Niche** (collapsible per niche):
   - 20-30 tag chip dari `niches.tag_pool`
   - Tenant pilih default tag preference (favorite chips)
   - Tooltip: "Sub-tag dipakai untuk variety tracking + YouTube hashtag granular".

7. **Per-Channel Niche Override** (kalau multi-channel):
   - Table: Channel | Default niche | Override (dropdown) | "Apply override" per row.

**Empty state (Starter 1 slot):** "Pilih 1 niche utama untuk channel Anda" + onboarding-style guidance.

**⚠️ CRITICAL:** Semua nominal harga (Rp 299K, Rp 1.499K, dll.) **HARUS** pakai placeholder `{{pricing.<key>}}`, BUKAN string literal. Ini sinyal bahwa harga di-render dari `pricing_config` table via API. Backend: `src/utils/pricing.py::get_price(key)`.

---

## 3. ‼️ E2.3 Admin — Niche Library — **DIPERLUAS**

`/admin/niches` (tab) — System admin manage broad niche catalog + tag pool + monthly release + exclusivity.

1. **Header strip:** "Niche Library Management" + stats "Active (4) | Pending release (2) | Private exclusive (1) | Public coming from 90d (3)" + buttons "+ Create New Niche", "📅 Schedule Monthly Release".

2. **View tabs:** All | Active | Pending Release | Private Exclusive | Public-after-90d Pipeline | Archived.

3. **Data Table:** Niche key | Display name | Access type badge | Tenant count | Videos count | Avg performance | Released date | Exclusive until | Actions. Click row → drawer.

4. **Detail Drawer (slide-in right) — 6 tab:**
   - **Tab 1 Identity:** niche_key (read-only after create), display name (ID+EN), description, keywords multi-tag, thumbnail moodboard (3-image), target_emotion, is_active toggle.
   - **Tab 2 Voice DNA:** voice_profile JSON editor + preview play TTS + ElevenLabs voice picker.
   - **Tab 3 Visual DNA:** visual_style JSON editor + generate sample image preview + color palette swatches.
   - **Tab 4 Music + Scoring:** mood_priority drag-drop + emotion_scoring_criteria textarea + default_hashtags editor.
   - **Tab 5 🆕 Tag Pool:** 20-30 sub-tag chips (admin-curated), add/remove inline, usage count per tag, performance-per-tag chart (CTR avg), "Suggest new tags via AI" button.
   - **Tab 6 🆕 Access & Exclusivity:**
     - access_type radio: 🌍 Public / 📅 Release Pending / 🔒 Private Exclusive / ⏳ Public-after-90d
     - exclusive_tenant_id dropdown (kalau Private/Public-after-90d)
     - exclusive_until date picker
     - released_at (auto-set saat → public)
     - Audit trail access type changes.

5. **🆕 Monthly Release Scheduler Panel:** calendar view release per bulan, drag-to-reschedule, "Send release announcement email" toggle per release (semua tenant / filter tier), preview email template, bulk schedule wizard.

6. **🆕 Exclusivity Pipeline View** (table terpisah): Niche | Exclusive to tenant | Until date | Days remaining | "Transition to public" action. Auto-transition cron indicator + "Extend exclusivity" action.

7. **Activity log** (bottom): "Niche 'crypto_detective' released to public catalog by admin@... 2 jam lalu", dst.

**Empty state:** "Belum ada niche di catalog. Buat niche pertama atau seed dari template."
**Mobile:** table → card stack, drawer → full-screen modal.

---

## 4. ‼️ E5 Admin — Pricing Config — **SCREEN BARU (#39)**

`/admin/pricing` — Single source of truth SEMUA pricing nominal. Sysadmin adjust harga tanpa redeploy. Dibaca UI tenant + backend via API.

**Why:** Pricing tidak boleh hardcode. Subscription, add-on, one-time fee — semua editable di sini.

1. **Header:** "Pricing Configuration" + stats "Total entries (25) | Last change (2 jam lalu by admin@...) | Active (23) | Inactive (2)" + buttons "+ New Pricing Entry", "📥 Import CSV", "📤 Export current".

2. **Filter bar:** Category (All / Subscription / Add-on / One-time / Discount), Status (Active / Inactive / Scheduled / Expired), Search by key.

3. **Data Table** (sortable):
   - Columns: Key (`custom_niche_public_90d`) | Description | Category badge | Value IDR (inline edit) | Value USD cents (inline edit) | Effective from | Effective until | Active toggle | Last updated (who/when) | Actions (Edit / History / Duplicate / Archive)
   - Bulk: activate/deactivate, export selected.

4. **Detail Drawer / Edit Modal — 4 tab:**
   - **Tab 1 Pricing:** Key (read-only after create), description, category dropdown, Value IDR, Value USD cents, auto-conversion suggestion ("Kurs 16000 IDR/USD: Rp 299.000 ≈ $18.69") + "Use auto conversion" button.
   - **Tab 2 Schedule:** effective from/until datetime picker, active toggle, "Schedule for next month" quick action.
   - **Tab 3 Audit Log:** timeline of changes (who/when/before→after) + "Rollback to version X".
   - **Tab 4 Where Used:** list screens/components yang reference key ini + "Test in preview" (iframe tenant UI dengan pricing applied).

5. **Common Categories — quick-edit cards:**
   - **Subscription Tiers:** 3 row Starter/Pro/Scale, inline IDR+USD, "Save all".
   - **Add-ons:** Custom niche public-90d, Custom niche private, Voice pack, Niche audit, Concierge setup, ~~Priority queue~~.
     > ⛔ **"Priority queue" DICABUT 2026-08-13 (ketok owner)** — tak pernah ada barangnya; sudah dihapus
     > dari halaman jual bersama Webhook & akses API. Butir 8 "API Documentation Panel" di bawah ikut
     > gugur. Rujukan hidup: `DESAIN_PRODUK_SAAS.md` §4. **Jangan dibangun.**
   - **Discounts:** Annual prepay % off, First-month promo, Referral discount.

6. **🆕 Promo/Seasonal Scheduler** (timeline): calendar upcoming pricing changes (Black Friday, Anniversary), drag-to-reschedule, "Create campaign" wizard (discount % + duration + applicable plans).

7. **Audit & Compliance Log** (bottom): full chronological changes, export CSV (accounting), weekly email digest.

8. **API Documentation Panel** (right rail collapsible): "GET /api/pricing" + sample response JSON + cache info ("Cached 5 menit, invalidate on update") + "Generate webhook signature".

**Critical UX:**
- ✏️ Inline edit auto-save (debounced 1s)
- 🚨 Confirmation modal sebelum activate change yang affect production tenants
- 📊 Impact preview: "Perubahan ini akan affect 47 active tenants"
- 🔄 Cache invalidation indicator: "Pricing cache flushed at 14:23"

**Empty state:** "Belum ada pricing config. Seed dari default values?" + import button.
**Permission:** RBAC — hanya Super Admin yang bisa edit; audit log visible untuk all admin.

---

## 5. Prinsip Lintas-Screen: Harga = Config-Driven

Berlaku untuk **SEMUA screen yang menampilkan harga**, bukan hanya D18/E5:

- **A2 Pricing (marketing):** harga plan pakai `{{pricing.plan_starter}}`, `{{pricing.plan_pro}}`, `{{pricing.plan_scale}}`.
- **C1 Onboarding (pilih paket):** sama, placeholder.
- **D13 Billing:** harga current plan + add-on pakai placeholder.
- **D18 Niches:** custom niche pricing pakai placeholder.

**Aturan untuk mockup:** di mana pun ada angka harga, render sebagai `{{pricing.<key>}}` (mis. `{{pricing.plan_pro}}`) dan boleh tampilkan contoh nilai di samping sebagai komentar visual kecil/caption, TAPI value utama harus jelas terlihat "dynamic". Ini menandai ke developer bahwa value datang dari DB, bukan literal.

**Key registry (untuk referensi mockup):**
`plan_starter`, `plan_pro`, `plan_scale`, `custom_niche_public_90d`, `custom_niche_private`, `voice_pack`, `niche_audit`, `concierge_setup`, `priority_queue`.

---

## 6. Konsistensi (sama seperti Batch 1)

- Sidebar shell + collapsible nav
- Card surface zinc-900 + border zinc-800
- Indigo-500 primary CTA + active state
- **Violet-500 untuk AI/premium treatment** (custom niche gradient card di D18, AI-suggest di E2.3 Tab Pool)
- Status badges + skeleton loaders + empty states pattern
- Dark default + working light toggle, ID default + working EN toggle
- Desktop 1440px + Mobile 375px untuk semua screen baru
- Typography Geist Sans, content Indonesia konkret ("Misteri Samudra", dst.)

---

## 7. Dampak ke Roadmap Batch

| Batch | Scope | Catatan v3 |
|---|---|---|
| Batch 5 | D8-D12 + D15-D19 Config tabs | **Pakai D18 versi v3** (bagian 2), bukan D18 di addendum v2 |
| Batch 9 | E1-E4 Admin + Music Library | **Tambah E2.3 versi diperluas** (bagian 3) **+ E5 NEW** (bagian 4) |

Screen inventory total: **39 screens + 6 state patterns.**

---

**END OF ADDENDUM v3.**

> Batch 1-4 tidak terdampak. Addendum ini relevan untuk Batch 5 (D18) dan Batch 9 (E2.3 + E5). Prinsip pricing config-driven (bagian 5) berlaku juga saat Batch 3 (A2 Pricing) dan Batch 7 (D13 Billing) — pakai placeholder `{{pricing.key}}`.
