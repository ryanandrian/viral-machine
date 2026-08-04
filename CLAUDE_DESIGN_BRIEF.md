# Claude Design Brief — MesinViral.com SaaS

> **Cara pakai:** Copy seluruh isi file ini, paste ke Claude Design / Anthropic Artifacts UI.
> Setiap section bisa di-request terpisah jika output terlalu besar untuk 1 generasi.
> Target framework: **Next.js 15 + shadcn/ui + Tailwind CSS + tremor.so charts**.

---

## 1. PROJECT OVERVIEW

**MesinViral.com** adalah SaaS multi-tenant yang auto-produksi video YouTube Shorts berkualitas viral, 5-24 video/hari per channel, dengan pipeline AI 7-step (trend scan → topic select → script generate via Claude → hook optimize → TTS via ElevenLabs → AI image via OpenAI → render → publish YouTube). Differensiasi utama: **self-learning dari real YouTube Analytics post-publish per channel** + **BYOK (tenant bawa API keys sendiri)** + **AI Slop Defense Engine** (diversity layer untuk compliance YouTube policy 2026).

**Target market:** Indonesia content creator yang scaling channel YouTube Shorts faceless (history/mystery/facts/science). Income range Rp 3-7jt/bulan. Tech-comfortable tapi BUKAN developer.

**Paket utama:** Starter Rp 149K · Pro Rp 349K · Business Rp 699K · Enterprise custom.

> ⚠️🔴 **DIKOREKSI 2026-08-05 — jangan pakai angka volume dari berkas ini.** Baris ini dulu menulis
> *"Starter (1 channel, **5 video/hari**), Pro (3 channel, **10/hari**), Scale (10 channel, **24/hari**)"*.
> Diverifikasi ke DB live: **`plan_limits.max_videos_per_day` = 1 · 1 · 3 · 5** (trial/starter/pro/business)
> — **3–5× lebih rendah** dari angka di atas, dan nama tier "Scale" sudah diganti **"Business"** (owner 14-Jun).
> **NILAI HIDUP = `plan_limits`**, admin-editable di `/admin/pricing` (migr 0073, nol hardcode). Angka apa pun
> yang disalin ke dokumen PASTI membusuk begitu owner menggeser kenopnya — karena itu di sini tidak disalin.
> Pernyataan yang TERVERIFIKASI cocok dengan DB: `CONTENT_CATEGORY_ARCHITECTURE.md` §"rumah gating tier"
> (1/1/3/5) dan `finalisasi_tier_plan.md` ("Max video/hari 50 landing = 5×10 channel").
> Status keputusan kuota = `SISA_KERJA_GO_LIVE.md` **[D6]**.

**Brand voice:** Profesional, calm, premium tapi tidak intimidating. Bahasa Indonesia (utama) + English (toggle). Terminology AI/tech tapi dijelaskan dalam bahasa awam.

---

## 2. DESIGN SYSTEM

### 2.1 Color Palette

**Dark mode (default):**
```
Background base    : #0A0A0B (zinc-950)
Surface 1 (cards)  : #18181B (zinc-900)
Surface 2 (hover)  : #27272A (zinc-800)
Border subtle      : #27272A
Border default     : #3F3F46 (zinc-700)
Text primary       : #FAFAFA (zinc-50)
Text secondary     : #A1A1AA (zinc-400)
Text muted         : #71717A (zinc-500)

Brand primary      : #6366F1 (indigo-500) — CTA, links, active states
Brand primary hover: #4F46E5 (indigo-600)
Brand accent       : #8B5CF6 (violet-500) — for AI features highlight

Success            : #10B981 (emerald-500) — completed runs, success metrics
Warning            : #F59E0B (amber-500) — quota near limit, suspended notice
Error              : #EF4444 (rose-500) — failed runs, errors
Info               : #3B82F6 (blue-500) — informational

Status pipeline    : 
  Pending          : #71717A (zinc-500)
  Running          : #3B82F6 (blue-500) with pulse animation
  Completed        : #10B981 (emerald-500)
  Failed           : #EF4444 (rose-500)
  Warning          : #F59E0B (amber-500)

YouTube brand      : #FF0000 (untuk channel-related accents)
Telegram brand     : #229ED9
ElevenLabs brand   : #6E2EF7 (untuk integration cards)
Anthropic brand    : #D97757 (untuk integration cards)
OpenAI brand       : #10A37F (untuk integration cards)
```

**Light mode (toggle):** Invert dengan zinc-50 base, zinc-900 text. Brand colors tetap.

### 2.2 Typography

```
Font UI            : Geist Sans (Google Fonts) — KEPUTUSAN FINAL (BUKAN Inter; Inter terlalu generik AI-slop). Bundle desain & implementasi pakai Geist.
Font monospace     : JetBrains Mono — untuk log viewer, code, API keys display
Font mono          : JetBrains Mono — log viewer/kode (Geist Sans = font SELURUH UI, bukan hanya hero)

Scale (rem):
xs    : 0.75rem  (12px) — labels, meta info
sm    : 0.875rem (14px) — body small, table cells
base  : 1rem     (16px) — body default
lg    : 1.125rem (18px) — emphasized body
xl    : 1.25rem  (20px) — section headers
2xl   : 1.5rem   (24px) — page subheaders
3xl   : 1.875rem (30px) — page headers
4xl   : 2.25rem  (36px) — dashboard KPI numbers
5xl   : 3rem     (48px) — landing hero
6xl   : 3.75rem  (60px) — landing hero XL

Font weight:
400 (regular) — body
500 (medium)  — labels, buttons
600 (semibold) — section headers, emphasis
700 (bold)    — page titles, KPI numbers
```

### 2.3 Spacing Scale (Tailwind default)

`0.25rem (1) | 0.5rem (2) | 0.75rem (3) | 1rem (4) | 1.5rem (6) | 2rem (8) | 3rem (12) | 4rem (16) | 6rem (24)`

**Layout grid:** 12 column, max-width 1440px untuk dashboard, 1280px untuk landing content.

### 2.4 Iconography

**Library:** Lucide React (consistent dengan shadcn/ui ecosystem). Stroke width 1.5px. Size: 16px (inline), 20px (button), 24px (header), 32px (feature card).

**Custom icons needed:**
- MesinViral logo (mark + wordmark)
- Pipeline step icons (Trend Radar, Topic Select, Script, Hook, TTS, Visual, Render, Publish)
- Brand integration icons (YouTube, Anthropic, OpenAI, ElevenLabs, Telegram)

### 2.5 Border Radius

```
sm  : 0.375rem (6px) — buttons, badges
md  : 0.5rem (8px)   — cards, inputs
lg  : 0.75rem (12px) — modal, drawer
xl  : 1rem (16px)    — feature cards, hero
2xl : 1.5rem (24px)  — landing main containers
full: 9999px         — pills, avatars
```

### 2.6 Shadow / Elevation (Dark Mode)

```
none   : no shadow (default surfaces)
sm     : 0 1px 2px rgba(0,0,0,0.5)  — slight lift untuk hover
md     : 0 4px 6px rgba(0,0,0,0.5)  — dropdown, popover
lg     : 0 10px 15px rgba(0,0,0,0.5) — modal
xl     : 0 20px 25px rgba(0,0,0,0.5) — major modals

Glow accent (for AI features):
  primary-glow : 0 0 30px rgba(99,102,241,0.3) — AI-related buttons saat hover
```

### 2.7 Animation Pattern

```
duration-150 : hover transitions (color, background)
duration-300 : drawer slide, modal fade
duration-500 : page transitions, large element movement

Easing       : ease-out (default), ease-in-out (transitions besar)

Special:
- Pulse animation untuk "Running" badge (animate-pulse)
- Skeleton loading dengan shimmer effect untuk semua data fetch
- Toast notifications: slide in from top-right, auto-dismiss 5s
- Live log tail: smooth scroll, new line fade-in
```

### 2.8 Core Components (shadcn/ui base)

Wajib ada (atomic + composite):

**Atomic:**
- Button (variants: default, secondary, ghost, destructive, outline; sizes: sm, md, lg, icon)
- Input (text, email, password, number, search; states: default, focus, error, disabled)
- Textarea
- Select (single + multi)
- Combobox (searchable dropdown)
- Checkbox, Radio Group
- Switch (toggle)
- Slider
- Label
- Badge (variants: default, success, warning, error, info, outline)
- Avatar (image, fallback initial)
- Tooltip
- Separator

**Layout:**
- Card (header, content, footer)
- Tabs (horizontal, vertical)
- Accordion
- Collapsible
- Sheet (slide-in drawer dari kanan/kiri/atas/bawah)
- Dialog (modal)
- Alert Dialog (destructive confirmation)
- Popover
- Dropdown Menu
- Command Menu (cmd+K palette)

**Data display:**
- Table (sortable, filterable, pagination)
- DataTable (advanced, dengan column visibility, row selection)
- Progress bar (linear + circular)
- Skeleton loaders
- Empty State illustration + CTA
- Alert (info/success/warning/error)
- Toast (sonner library style)

**Charts (tremor.so):**
- Area chart (analytics over time)
- Bar chart (top videos, niche distribution)
- Donut chart (niche split, status distribution)
- Spark chart (small inline trend in KPI cards)
- Tracker (compliance score visualization)

**SaaS-specific composite:**
- KPI Card (number + label + delta + icon + spark)
- Status Badge (color + dot + label, animated for running)
- Pipeline Timeline (vertical timeline dengan 7 step states)
- API Key Input (masked display, copy button, regenerate button, test connection)
- Plan Card (tier name + price + features + CTA + most-popular badge)
- Channel Card (logo + name + niche + stats + status indicator)
- Run Card (status + topic + niche + duration + view count + actions)
- Cost Breakdown Widget (mini bar showing AI cost components per video)
- Compliance Score Widget (circular gauge 0-100 + breakdown)
- Schedule Slot Card (time + niche + channel + content_type + active toggle)
- Wizard Step Indicator (horizontal progress dengan check + current + future)

### 2.9 Iconography Custom — Pipeline Steps

8 custom icons untuk pipeline step visualization (line-art style, indigo accent):

```
Step 1: Trend Radar     — radar/scan icon
Step 2: Topic Select    — bullseye/target dengan checkmark
Step 3: Script Generate — document dengan AI sparkles
Step 4: Hook Optimize   — magnet/lightbulb
Step 5: TTS Audio       — waveform dengan mic
Step 6: Visual Assemble — image stack
Step 7: Video Render    — film reel + cogs
Step 8: Publish YouTube — YouTube logo dengan upload arrow
```

---

## 3. DESIGN REFERENCES & MOOD BOARD

**Visual inspiration (the closer the better):**

- **Linear** (linear.app) — sidebar nav style, command menu, dark mode aesthetic, sleek table
- **Vercel Dashboard** — analytics chart treatment, project card design, deployment timeline
- **Stripe Dashboard** — payment table, financial data density, clarity in complexity
- **Supabase Dashboard** — database explorer, real-time data tail, table editor
- **Resend Dashboard** — email-focused, status visualization, clean log viewer
- **Cursor / Claude.ai** — AI-themed gradients, sparkle accents, premium feel
- **OpenAI Platform** — API key management UX, usage charts

**Anti-patterns (HINDARI):**
- ❌ Bootstrap-style chunky buttons (we want refined, modern)
- ❌ Over-decorated gradients everywhere (subtle only, for AI features)
- ❌ Flashy animations (we serve professional creators, not gaming)
- ❌ Overwhelming density without hierarchy (Stripe-style balance)
- ❌ "AI bro" aesthetic with neon greens (sophisticated indigo/violet instead)

**Style descriptor:**
> "Linear's clean information architecture × Stripe's data density × Vercel's deployment timeline aesthetic × subtle AI-feature glow accents. Dark mode primary, light mode optional. Indonesian content creator audience — premium feel tanpa intimidating."

---

## 4. USER PERSONAS

### Persona 1 — "Riko, Faceless Channel Scaler" (Primary, 80% UX)
- 28 tahun, Jakarta, ex-marketing
- 1 channel YouTube Shorts niche "ocean_mysteries", 8K subs
- Sudah produksi 2 video/minggu manual, ingin scale ke 5/hari
- Income Rp 6jt/bln (campuran salary + early YT revenue)
- Tech: comfortable dengan Notion, Canva, Google Workspace. **BUKAN coder**. Pernah pakai ChatGPT untuk script.
- Wakteu pemakaian: 15-30 menit/hari untuk monitor & adjust

### Persona 2 — "Sarah, Agency Manager" (Secondary, 15% UX)
- 35 tahun, Surabaya, founder agensi konten 5 orang
- Manage 8 channel klien (mix faceless + edukatif)
- Income: agency revenue Rp 50jt/bln
- Tech: punya tim Operations, butuh dashboard terpusat + reporting

### Persona 3 — "Admin Internal" (Tertiary, 5% UX)
- Staff support MesinViral
- Need: tenant overview, suspend/refund, support tickets, system health

---

## 5. SCREEN INVENTORY

**Total: 39 screens unik + states**, dipecah jadi 5 section.

> **Catatan (2026-06-11):** Screen/config tambahan untuk epic **Multi-Format Short Studio** (format config, duration preset, soft-sell/brand+link panel, distribution panel tier-gated, admin `format_profiles`) **TIDAK ada di bundle Claude Design** — dibangun langsung saat implementasi frontend (Hybrid). Spec: `MULTI_FORMAT_STUDIO.md`.

| Section | Jumlah | URL Pattern |
|---|---|---|
| A. Public Marketing | 8 | mesinviral.com/* |
| B. Authentication | 4 | mesinviral.com/auth/* |
| C. Onboarding Wizard | 5 (1 per step) | app.mesinviral.com/onboarding/* |
| D. Tenant Dashboard | 21 | app.mesinviral.com/* |
| E. Admin Internal | 5 | admin.mesinviral.com/* |
| F. States (modal/empty/error) | 6 patterns | Various |

> ⚠️ **Cara hitung (anti-bingung):** kolom Jumlah = rentang penomoran (mis. D1-D21), BUKAN jumlah screen fisik — Config (D8-D19) = 1 screen multi-tab, E2.1-E2.5 = subtab E2. **Total screen logis kanonik = 39.** Bundle Claude Design = **32 file HTML ≈ 30 screen prototype + mobile/states**; screen epic Multi-Format belum di bundle (dibangun saat implementasi).

---

## 6. SCREEN SPECIFICATIONS — DETAILED

### SECTION A — Public Marketing Site

---

#### A1. Landing Page (`mesinviral.com/`)

**Purpose:** Convert visitor → free trial signup.

**Layout (top to bottom):**

1. **Navigation bar** (sticky)
   - Logo kiri | Menu tengah (Fitur, Harga, Demo, Dokumentasi, Blog) | "Masuk" + "Mulai Gratis" kanan
   - Background blur on scroll

2. **Hero section**
   - Headline (5xl): "Mesin produksi video YouTube otomatis yang **belajar dari channelmu sendiri**."
   - Subheadline (xl, zinc-400): "5-24 video Shorts per hari, dengan kualitas viral-grade. Tools lain bikin video. MesinViral belajar dari analytics channelmu."
   - Dual CTA: "Mulai Gratis 7 Hari →" (primary, large) + "Tonton Demo (2 menit)" (ghost, dengan play icon)
   - Hero visual: dashboard mockup (3D tilt) showing live pipeline + analytics chart
   - Sub-row: "Tanpa kartu kredit. 5 video gratis di trial. Cancel anytime."
   - Trust badges: "Powered by Claude · ElevenLabs · OpenAI"

3. **Stats banner** (3 KPI strip)
   - "10x Volume" — "Vs kompetitor 2 video/hari, kami 24/hari/channel"
   - "7.5× Lebih Murah" — "Rp 75/video vs Rp 18,000/video di AutoShorts.ai"
   - "100% BYOK" — "Tenant pegang API keys, transparan biaya"

4. **Problem section** ("Masalah yang Kamu Hadapi")
   - 3 column dengan icon + headline + body
     - "Bikin 1 video butuh 4-8 jam" — riset + script + voiceover + edit
     - "Tools auto-pilot lain max 2 video/hari" — dengan harga $69/bulan
     - "Tidak ada yang belajar dari channelmu" — generic AI, output sama untuk semua orang

5. **Solution section** ("Bagaimana MesinViral Mengubah Ini")
   - Animated pipeline diagram horizontal: 7 step dengan icon + label, scroll-triggered animation
   - Caption per step (hover): explanation singkat

6. **Killer Features section** (6 feature cards, 2-col grid pada desktop)
   - **🥇 Self-Learning Engine** — "Belajar dari real YouTube Analytics channelmu. Adapt niche, hook, visual style otomatis."
   - **🔓 BYOK Transparency** — "Kamu pegang API keys Anthropic/OpenAI/ElevenLabs. Lihat biaya AI real-time."
   - **🛡️ AI Slop Defense** — "Diversity engine otomatis lindungi channel dari YouTube AI policy 2026."
   - **🚀 5-24 Video/hari** — "Multi-channel parallel. Scale tanpa hire tim."
   - **🌐 Konten Multi-Bahasa** — "Produksi narasi + caption dalam Bahasa Indonesia, English, dan bahasa Asia Tenggara (Malaysia, Filipina, Thailand, Vietnam). Pilih bahasa per channel — jangkau audiens lintas negara dari satu platform."
   - **🇮🇩 Indonesia-First** — "UI Bahasa Indonesia, Midtrans payment, support lokal." *(bundle desain masih tulis "Xendit" → swap ke Midtrans saat implementasi)*

7. **Comparison table** ("MesinViral vs Kompetitor")
   - Sticky header table dengan 5 kolom (MesinViral, AutoShorts, OpusClip, Submagic, Pictory)
   - Rows: Auto-publish, Self-learning, BYOK, Diversity engine, Multi-channel, **Multi-language content**, Max video/hari, Custom voice, Indonesia payment, Price/video
   - MesinViral column highlighted dengan border indigo + light glow

8. **How It Works** (3 step process)
   - 1. Daftar & Connect Channel (1 menit)
   - 2. Input API Keys (5 menit, dengan tutorial)
   - 3. Mesin Jalan 24/7

9. **Testimonials carousel** (3-5 quote cards)
   - Avatar + nama + channel + quote + stat (e.g., "2.3x growth in 60 days")
   - Auto-scroll dengan pause on hover

10. **Pricing preview** (3 card row, kompak)
    - Starter Rp 149K | Pro Rp 349K (most popular) | Scale Rp 699K
    - Each: 5 key features + CTA "Pilih Paket"
    - Link "Lihat semua paket & fitur →" ke /pricing

11. **FAQ accordion** (10-12 Q&A)
    - "Apa itu BYOK?"
    - "Apakah aman dari penalty YouTube AI policy?"
    - "Berapa biaya total termasuk API?"
    - "Bisa cancel kapan saja?"
    - "Apakah ada free tier?"
    - "Channel saya 0 subs, bisa pakai?"
    - "Bisa bikin konten dalam bahasa selain Indonesia (English, Malaysia, Thailand)?"
    - dll.

12. **CTA strip final**
    - "Siap scale channelmu ke 5+ video per hari?"
    - "Mulai Gratis 7 Hari" button XL center
    - "Tanpa kartu kredit"

13. **Footer**
    - Logo + tagline kecil
    - Kolom: Produk (Fitur, Harga, Demo, Roadmap), Resources (Dokumentasi, Blog, Case Studies, API), Company (About, Contact, Karir), Legal (Privacy, Terms, GDPR)
    - Social: YouTube, Twitter/X, Instagram, LinkedIn
    - Sub-footer: copyright, language toggle (ID/EN), status page link

**Mobile (<768px):** Hero stacked, comparison table horizontal scroll, pricing 1-col vertical.

---

#### A2. Pricing Page (`/pricing`)

**Layout:**

1. Header: "Pilih paket yang cocok untuk channelmu" + monthly/annual toggle (annual 20% off badge)

2. **3-tier comparison cards** prominently (Starter / Pro / Scale)
   - Each card: tier name + price + price/year strikethrough (kalau annual) + tagline + "Yang Anda Dapatkan" bullet list + CTA
   - "Most Popular" badge di Pro (indigo glow border)

3. **Enterprise card** terpisah di bawah, lebar full
   - "Butuh lebih? Mari bicara" + form contact

4. **Comparison table lengkap** (semua field config dari Tab Config)
   - 30+ row features, 4 column (incl Enterprise)
   - Checkmark / X icon / numeric value

5. **AI Cost Calculator** widget interaktif
   - Slider: "Berapa video per hari?" (1-24)
   - Auto-calculate: estimated AI cost/bulan ke Anthropic, ElevenLabs, OpenAI
   - Total IDR equivalent
   - Disclaimer: "Biaya AI dibayar langsung ke provider sesuai BYOK"

6. **Add-ons section**
   - Niche Pack, Voice Pack, Concierge Setup, Priority Queue, Channel Audit
   - Card with price + one-line description

7. **FAQ pricing-specific**
   - "Bisa upgrade/downgrade kapan saja?"
   - "Refund policy?"
   - "Bagaimana biaya AI dihitung?"

---

#### A3. Demo Page (`/demo`)

**Layout:**

1. Header: "Lihat MesinViral dalam aksi"

2. **Video embed** (YouTube/Vimeo) — 2 menit walk-through

3. **Interactive product tour** (Storylane/Navattic style atau tabbed)
   - Tab: Dashboard | Pipeline live | Self-learning | Compliance
   - Each tab: screenshot atau interactive replay dengan annotation

4. **CTA section** "Coba sekarang gratis"

---

#### A4. Documentation/Knowledge Base (`/docs`)

**Layout:**

1. **Sidebar nav** (collapsible, 250px)
   - Search bar
   - Tree: Getting Started, Onboarding, API Keys Setup, Niches, AI Engines, Schedule, Analytics, Self-Learning, AI Slop Defense, Billing, Troubleshooting, FAQ

2. **Main content** (max-width 720px)
   - Breadcrumb
   - Article header dengan last updated + reading time
   - Article body: markdown rendered (h2/h3, code blocks, callouts, images, video embed)
   - "Was this helpful?" feedback bottom
   - "Next/Previous article" navigation
   - "Edit on GitHub" link (if docs open-source)

3. **Right rail (TOC)** untuk article > 3 sections (sticky)

**Empty state search:** "Tidak menemukan jawaban? Hubungi support" + CTA

---

#### A5. Blog (`/blog` + `/blog/[slug]`)

- **List:** card grid 3-col, masing-masing: cover image + category + title + excerpt + author + date + reading time
- **Filter:** by category (Tips Growth, AI Updates, Case Studies, Product News)
- **Article:** sama struktur dengan docs, tapi ada hero image + author bio bottom + related articles

---

#### A6. Case Studies (`/case-studies` + `/case-studies/[slug]`)

- **List:** card dengan channel name + subs growth + main metric ("3.2x views in 90 days") + thumbnail
- **Detail:** hero metric + customer story format (Challenge → Solution → Result) + screenshots + quote pull + CTA "Mulai trial sepertinya"

---

#### A7. About / Contact / Status / Legal pages

- **About:** simple page, mission + team (optional), values
- **Contact:** form + email + alamat + WA support
- **Status:** simple uptime page (atau embed dari BetterStack)
- **Legal:** Privacy Policy, Terms of Service, Refund Policy, GDPR — semua text-heavy, clean typography

---

#### A8. 404 / Maintenance / Error Pages

- **404:** illustration + "Halaman tidak ditemukan" + link kembali home
- **Maintenance:** clock illustration + ETA + status link
- **Error 500:** "Ada error di sisi kami" + contact support

---

### SECTION B — Authentication

---

#### B1. Sign Up (`/signup`)

**Layout:** split-screen, kiri form + kanan branding/visual.

**Kiri (form, 50% width desktop, 100% mobile):**
- Logo top
- "Mulai gratis 7 hari" headline
- Subheadline: "5 video gratis, tanpa kartu kredit"
- Form: Email + Password (with show/hide) + Confirm Password
- "Daftar dengan Google" OAuth button (atas form, prominently)
- Terms acceptance checkbox
- Submit button "Buat Akun"
- "Sudah punya akun? Masuk" link bottom

**Kanan (50% width desktop):**
- Background gradient indigo → violet subtle
- Testimonial quote card overlay: "MesinViral menambah views channel saya 2.3x dalam 2 bulan. Set & forget." — Riko, Ocean Mysteries Channel
- Stat ticker: "Bergabung dengan 500+ creators yang sudah produksi 1M+ video"

---

#### B2. Sign In (`/login`)

Sama dengan B1 tapi simpler:
- Email + Password
- "Lupa password?" link
- OAuth Google
- "Belum punya akun? Daftar gratis" link

---

#### B3. Forgot Password (`/forgot-password`)

- Single field email
- "Kirim link reset" button
- Setelah submit: success message "Cek email Anda"

---

#### B4. Email Verification (`/verify-email`)

- State 1: "Cek email Anda untuk verifikasi" + resend button
- State 2: "Email berhasil diverifikasi!" + auto redirect to onboarding

---

### SECTION C — Onboarding Wizard (5 Steps)

**Common layout untuk semua step:**

- Top: progress indicator horizontal (5 dot/step, dengan check ✓ pada selesai, current dengan ring indigo)
- Left rail: list step dengan label, current highlighted, future grayed
- Center: main content (max 720px)
- Bottom: "← Kembali" + "Lanjut →" buttons
- "Skip semua, lakukan nanti" link bottom (mengarahkan ke dashboard dengan trial mode)
- Help button (?) right top — tooltip "Butuh bantuan? Chat dengan kami"

---

#### C1. Step 1 — Pilih Paket

**Content:**
- Headline: "Pilih paket untuk memulai trial 7 hari"
- 3 card paket (Starter/Pro/Scale) — Compact version
- Each card: price + 3 main features + radio button select
- Default selected: Starter
- Catatan box: "Trial 7 hari semua paket gratis. Cancel kapan saja sebelum trial selesai tanpa biaya."

---

#### C2. Step 2 — Connect YouTube Channel

**Content:**
- Headline: "Hubungkan channel YouTube Anda"
- Sub: "Anda akan diminta untuk membuat Google Cloud Project. Ikuti tutorial ini."
- **Tutorial video embed** (3-5 menit, screen recording)
- Steps checklist:
  1. ☐ Buka Google Cloud Console (link button)
  2. ☐ Buat project baru bernama "mesinviral-yourname"
  3. ☐ Enable YouTube Data API v3
  4. ☐ Buat OAuth 2.0 credentials
  5. ☐ Copy Client ID + Client Secret
- Form fields:
  - Google Client ID input
  - Google Client Secret input
  - YouTube Channel ID input (with "How to find?" tooltip)
- Button "Connect & Verify" — saat submit, redirect ke Google OAuth consent, balik dengan success state
- Success state: green check + channel name + thumbnail + subs count detected

---

#### C3. Step 3 — Setup AI API Keys

**Content:**
- Headline: "Tambahkan API keys untuk power mesin"
- Sub: "BYOK = Bring Your Own Keys. Anda yang kontrol biaya, transparan."
- Trust note: "Keys di-enkripsi dengan Fernet AES-128, never logged"

- **3 expandable card untuk masing-masing service:**

  **Anthropic Claude (LLM)**
  - Status badge: Required | Optional
  - Embed video tutorial 2 menit
  - Steps: Create account → Add billing → Generate API key
  - Input: API key (masked) + Test Connection button
  - On success: green check + "Connected · $0.00 spent so far" + last test timestamp

  **OpenAI (Visual AI + LLM alternative)**
  - Same structure

  **ElevenLabs (TTS)**
  - Same structure
  - Bonus: setelah connected, button "Browse voices" yang preview ke step 4

- "Skip untuk sekarang" link → trial mode dengan platform-managed (limited features) notice

---

#### C4. Step 4 — Pilih Niche & Voice

**Content:**

- Headline: "Pilih niche & style channel"

- **Niche grid** (2x2 atau 2x3 cards)
  - Universe Mysteries (with thumbnail moodboard)
  - Dark History
  - Ocean Mysteries
  - Fun Facts
  - "Niche custom (Rp 299K)" — pop-up form
- Each niche card: thumbnail + description + sample video link + checkbox

- **Bahasa Konten** dropdown (render dari catalog `content_languages` — config-driven, BUKAN hardcode)
  - Default: Bahasa Indonesia (id-ID)
  - Official: Indonesia, English; tier SEA (Malaysia, Filipina, Thailand, Vietnam) dengan badge "Eksperimental"
  - **Menentukan bahasa narasi (TTS) + caption + script untuk SEMUA video channel ini**
  - ⚠️ Mengubah bahasa = daftar voice ikut berubah (voice difilter per bahasa)
  - Ditempatkan SEBELUM voice selection karena daftar voice difilter oleh bahasa ini

- **Voice selection** dropdown dengan preview
  - Default voice per niche pre-selected
  - "Custom voice" — pilih dari ElevenLabs library
  - Each option: preview play button + name + style descriptor

- **Brand color picker** (untuk thumbnail accent)

---

#### C5. Step 5 — Setup Schedule

**Content:**
- Headline: "Tentukan jadwal publikasi"

- **Visual schedule editor** (calendar week view)
  - Default suggestion: 3 slot/hari optimal (10:00, 14:00, 19:00 WIB)
  - Drag-to-edit slot
  - Per slot: time picker + niche assigned (atau "auto rotation") + content_type (short/long)

- Suggestion box: "Berdasarkan data, slot 10:00, 14:00, 19:00 WIB punya engagement tertinggi. Mau pakai default?"

- "Aktifkan scheduler sekarang" toggle

- Final CTA: "Selesai Setup! Lihat Dashboard" button XL

---

### SECTION D — Tenant Dashboard

**Common layout:**

- Top bar: logo + tenant name dropdown (multi-tenant switcher kalau agency) + search (cmd+K) + notifications bell + avatar dropdown
- Left sidebar (collapsible, 240px → 64px):
  - Dashboard
  - Channels
  - Runs
  - Analytics
  - Schedule
  - Config (expandable submenu: AI Engines, API Keys, Voice, Visual, Music, Captions, Quality Gate, Notifications, Niches, Hashtags)
  - Billing
  - Team (Enterprise only)
  - Settings
  - Help (bottom)
- Main content area dengan breadcrumb top + page title + actions
- Optional right rail (drawer slide-in) untuk detail view

---

#### D1. Main Dashboard (`/dashboard`)

**Layout:**

1. **Greeting bar**
   - "Selamat pagi, Riko" (dynamic by time of day)
   - Date + worker status badge (🟢 Worker Live)
   - Quick action: "+ Run Now" button (Pro+)

2. **KPI cards row (4 cards)**
   - "Video Hari Ini" — 2/3 (with spark chart 7 days)
   - "Success Rate" — 95% (delta +2% from yesterday, with mini bar)
   - "Total Views Hari Ini" — 1.2K (across all channels)
   - "Subs Today" — +47 (with delta)

3. **2-column grid:**

   **Kolom kiri (60% width)**
   - **Upcoming Schedule** card
     - Today's slots dalam row layout, status badge (Pending / Running / Done)
     - Time | Niche | Channel | Status | Action (Cancel / View)
     - Bottom: "View full schedule →"
   - **Recent Runs** card
     - Last 5 runs dengan: status icon + time + topic + niche + duration + view count + YouTube link icon
     - Failed runs highlighted dengan red border-left
     - "View all runs →"

   **Kolom kanan (40% width)**
   - **Compliance Score Widget** (circular gauge 0-100)
     - Per channel score
     - Breakdown: voice diversity %, niche distribution %, hook spread %, days since duplicate
     - Color: green > 80, amber 60-80, red < 60
     - Link "Lihat detail compliance →"
   - **Cost Tracker** card
     - "AI Cost Hari Ini" — $4.20 (Rp 67K)
     - Breakdown bar: Anthropic 30% | ElevenLabs 25% | OpenAI 45%
     - "Bulan ini: $112 / Budget: $500" + progress bar
   - **Self-Learning Status** card
     - "Last analytics pull: 2 jam lalu"
     - Insight: "Hook 'gap question' perform 2.3x lebih baik — di-prioritaskan"
     - "Lihat semua insights →"

4. **Activity feed** (bottom, expandable)
   - Real-time stream: "Run #97 just started", "Run #96 published to YouTube", etc.

**Empty state (new tenant):**
- "Belum ada video. Setup channel pertama Anda?" + button ke onboarding

---

#### D2. Channels List (`/channels`)

**Layout:**

1. **Header:** "Channels" + "+ Tambah Channel" button (disabled jika hit paket limit)

2. **Filter bar:** All / Active / Suspended / Setup Incomplete

3. **Channel grid** (3-col desktop, 1-col mobile)
   - Each card:
     - Channel logo (round) + Channel name
     - Niche badges (max 4)
     - Status badge (Active / Setup Incomplete / Suspended)
     - Stats row: Total videos | Total views | Avg CTR | Subs
     - Mini chart: views last 30 days
     - Footer: "Manage →" button + 3-dot menu (Pause, Edit, Delete)

4. **Quota indicator:** "3 dari 3 channel terpakai (Pro plan)" + upgrade CTA

---

#### D3. Channel Detail (`/channels/[id]`)

**Layout:**

1. **Channel header**
   - Logo + name + YouTube URL (link out)
   - KPI strip: Total Videos | Subs | This Month Views | Avg Engagement

2. **Tabs:**
   - Overview (default)
   - Runs (filtered by this channel)
   - Analytics (charts)
   - Schedule (per-channel slots)
   - Settings (per-channel **bahasa konten**, niche, voice, brand) — ganti bahasa konten = peringatan non-retroaktif (hanya berlaku video baru) + voice ikut ter-reset/filter

3. **Overview tab content:**
   - Performance chart (area, 90 days, multi-metric overlay)
   - Top performing videos table (last 30 days, sortable)
   - Niche distribution donut + recommended adjustment text
   - Hook style performance bar chart

---

#### D4. Runs List (`/runs`)

**Layout:**

1. **Header + filters:** Status (All/Completed/Failed/Running/Queued) | Channel | Date range | Niche

2. **Data table:** Run ID | Channel | Niche | Topic (truncated) | Status badge | Duration | Views (post-publish) | Started At | Actions
   - Sortable columns
   - Row click → drawer slide-in dengan run detail
   - Bulk actions: Re-run | Export CSV

3. **Pagination + "Showing X of Y"**

4. **Quick stats top right:** "12 successful runs today, 1 failed"

---

#### D5. Run Detail (`/runs/[id]`) — KRITIS untuk product

**Layout: full page atau drawer (pilihan UX, recommend full page untuk detail).**

1. **Header**
   - "← Back to runs" link
   - Run number + topic + channel + niche
   - Status badge (large) + duration
   - Actions: "Re-run", "Download log", "Open YouTube" (if published)

2. **3-column layout**

   **Kolom kiri (40% width) — Pipeline Timeline (vertical)**
   - 7 step (atau 8 with publish), masing-masing:
     - Step icon + label
     - Status indicator (pending/running pulse/completed check/failed X/warning ⚠)
     - Duration ("12s" / "running 1m 30s")
     - Sub-info (e.g., "Provider: Claude Haiku 4.5", "6 clips generated")
     - Click step → highlight log section yang related
   - Vertical line connector dengan animation untuk running

   **Kolom tengah (35% width) — Live Log Tail**
   - Monospace font
   - Color-coded: INFO white, WARN amber, ERROR rose
   - Auto-scroll to bottom (toggle pause)
   - Search/filter bar
   - "Download full log" button

   **Kolom kanan (25% width) — Metadata + Cost**
   - **Output card**
     - Thumbnail (kalau sudah ada hook_frame)
     - YouTube link (kalau published) + view count + watch time
     - File size, duration, resolution
     - Script preview (expandable)
   - **Cost breakdown card**
     - $0.34 total = $0.07 Claude + $0.18 ElevenLabs + $0.09 OpenAI
     - Bar visual
   - **AI providers used card**
     - Claude Sonnet 4.6 (script)
     - Claude Haiku 4.5 (utility)
     - ElevenLabs Multilingual v2
     - gpt-image-1-mini

3. **Bottom: Telegram notif preview** (kalau notif fired)

---

#### D6. Analytics (`/analytics`)

**Layout:**

1. **Filter:** Date range picker | Channel filter (multi) | Niche filter

2. **Top KPI strip (6 cards):**
   - Total Videos Published
   - Total Views
   - Avg CTR
   - Avg Retention
   - Subs Gained
   - Total AI Cost

3. **Chart grid:**
   - Views over time (area chart, multi-channel overlay)
   - CTR distribution (histogram)
   - Top performing niches (bar)
   - Hook style performance (bar)
   - Music mood × performance (heatmap)
   - Publish time × engagement (heatmap)

4. **Top videos table** dengan thumbnail, sortable

5. **Self-learning insights panel** — auto-generated insights:
   - "Niche 'ocean_mysteries' perform 1.5x lebih baik dari 'dark_history' — mesin menambah weight"
   - "Hook 'time pressure' under-perform — mesin men-deprioritize"
   - Action: tenant approve/reject insight

6. **Export button:** CSV, PDF report

---

#### D7. Schedule (`/schedule`)

**Layout:**

1. **View toggle:** Week calendar | Month overview | List

2. **Week view:**
   - 7-day grid horizontal
   - Slot cards (drag-and-drop to reorder time)
   - Each slot: time + niche + channel + content_type + active/paused toggle
   - "+" button per day untuk add slot

3. **Quick action:** "Bulk edit", "Pause all", "Apply template"

4. **Suggested optimization banner:**
   - "Mesin deteksi slot 14:00 punya engagement 30% lebih tinggi. Tambah slot di jam ini?"

---

#### D8. Config — AI Engines (`/config/ai-engines`)

**Layout:** seperti di v2 doc Section 8 mockup
- 3 expandable card (Script LLM, TTS, Visual AI)
- Per card: provider radio + model selector per task + API key input + test connection + usage stat
- Save button bottom (sticky on scroll)

---

#### D9. Config — API Keys (`/config/api-keys`)

**Layout:**
- Table dengan: Service | Status (Connected/Failed/Not Set) | Last Test | Last Used | Actions (Test, Update, Remove)
- Bulk test all button
- Audit log: "API key Anthropic diperbarui 2 hari lalu"

---

#### D10. Config — Voice (`/config/voice`)

- ElevenLabs voice library browser
- **Filter by language defaultnya = bahasa konten channel** (di-set di onboarding C4 / Channel Settings); voice yang ditampilkan hanya yang mendukung bahasa tsb
- Filter tambahan: gender, style, age
- Card grid: voice name + preview play + sample text + "Use this voice" button
- Per niche assignment: default voice per niche

---

#### D11. Config — Visual (`/config/visual`)

- Style preset cards: Cinematic Dark, Vibrant, Minimalist, Mysterious
- Custom prompt prefix editor (Pro+)
- Color palette per niche (optional override)

---

#### D12. Config — Music (`/config/music`)

**Purpose:** Tenant control music selection behavior untuk channel-nya (TIDAK edit library — library di-manage oleh System Admin di E2.2).

**Layout:**

1. **Header**
   - "Music Config" — channel selector dropdown (kalau multi-channel)
   - Global toggle: **"Background music aktif"** (Switch, default ON)

2. **Tabs:** Settings | Library Browser (read-only) | Usage Stats

3. **Tab Settings:**
   - **Volume slider** (0-100%, default 30%) — with mini speaker icon + live preview button "▶ Test mix"
   - **Ducking dB slider** (-10 to -25dB, default -18dB) — **Pro+ only**, tooltip explain "Ducking otomatis turunkan musik saat ada suara TTS"
   - **Auto fade in/out toggle** + duration slider (0.5-3s)
   - **Mood Priority per Niche** — 4 card (1 per niche aktif), each card berisi:
     - Niche name + thumbnail
     - Draggable list of 5-15 moods (drag to re-order priority)
     - "Reset to default" link (default dari niches.mood_priority backend config)
     - Tooltip: "Mood pertama yang match script akan dipilih"
   - **Use my custom uploads** toggle (**Premium+ & Enterprise only**) — surface tracks tenant upload sendiri (kalau pakai add-on Voice/Niche Pack)

4. **Tab Library Browser (read-only untuk tenant):**
   - Filter bar: Mood (multi-select) | Niche compat | BPM range slider | Duration range
   - Search bar
   - Data table:
     - Columns: ▶ Play | Waveform thumb | Track name | Mood badges | Niche compat | BPM | Duration | Used by me (count) | ⭐ Favorite | 🚫 Blacklist
     - Hover row: full waveform mini-preview
     - Click row → drawer dengan track detail (full waveform, license info read-only, why available untuk paket ini)
   - Footer: "Menampilkan 87 dari 100 tracks (Standard tier). Upgrade untuk akses 500 tracks Premium →"
   - Empty filter result: "Tidak ada track sesuai filter. Reset filter atau request niche custom."

5. **Tab Usage Stats:**
   - Top 10 tracks dipakai tenant 30 hari terakhir (bar chart + table)
   - Performance correlation: "Track ini avg CTR 1.4x dari channel rata-rata"
   - Auto-recommendation card:
     - 🟢 "Track 'Cosmic Dread' perform 1.8x — pertahankan di rotasi"
     - 🟡 "Track 'Tense Buildup' CTR 30% lebih rendah dari avg — blacklist?"
   - Diversity metric: "Anda pakai 12 track berbeda dari 100 tersedia (12%) — tambah variasi untuk hindari similarity"

**Empty state (music disabled):** "Background music dimatikan. Aktifkan untuk video lebih engaging" + toggle inline + sample video link.

**Mobile:** Tabs jadi bottom tab, table jadi card stack.

---

#### D13. Billing (`/billing`)

**Layout:**

1. **Current plan card**
   - Plan name + price + renewal date
   - "Upgrade Plan" / "Downgrade Plan" buttons
   - Usage indicators: Channel usage (1/3), Video this month (45/900)

2. **Payment method**
   - Current method (Midtrans logo + masked detail) *(bundle desain masih "Xendit" → swap ke Midtrans saat implementasi)*
   - "Update payment method" button

3. **Invoice history table**
   - Date | Amount | Status | Action (Download PDF)
   - Last 12 months

4. **Add-ons section**
   - Active add-ons listed
   - "+ Add new add-on" button → drawer dengan add-on catalog

5. **AI Cost Tracker** (read-only — mengingatkan BYOK terpisah)
   - "Biaya AI (BYOK)" — dengan disclaimer
   - Breakdown chart per provider this month

---

#### D14. Settings (`/settings`)

**Tabs:**
- Profile (name, email, avatar, phone)
- Security (password change, 2FA setup, sessions)
- Integrations (Telegram bot setup, webhook URL, Slack untuk Enterprise)
- Notifications preferences (link ke D17 untuk full preferences)
- Language (ID / EN)
- Danger zone (export data, delete account)

---

#### D15. Config — Captions (`/config/captions`)

**Purpose:** Tenant atur visual style karaoke caption (ASS subtitle) yang muncul di video output. Caption otomatis mengikuti **bahasa konten channel** (dari narasi TTS) — tenant tidak set bahasa caption di sini, hanya style.

⚠️ **Catatan font non-Latin:** untuk bahasa dengan skrip non-Latin (mis. Thailand), font ASS yang dipilih WAJIB punya glyph coverage bahasa itu — font tanpa coverage akan render kotak. `fonts` table tandai `script_support` per font; font picker auto-filter sesuai bahasa konten channel.

**Layout:**

1. **Header:** "Captions Style" + tier badge

2. **Live Preview area (top, sticky on scroll)**
   - Mock video frame 9:16 (aspect ratio Shorts) dengan dummy clip background
   - Caption sample text scrolling karaoke style — text contoh: "Suara aneh di kedalaman Mariana Trench"
   - **Real-time update** saat ubah setting di bawah (semua perubahan langsung visible)

3. **3-tab Config:**
   - **Tab Style:**
     - Font picker dropdown (dari `fonts` table Supabase): Anton (default), Inter, Bebas Neue, Plus Jakarta Sans, Geist + thumbnail preview per font
     - Font size slider (60-150px, default 119px)
     - Bold/Italic toggle
     - Color picker (text color, default #FFFFFF)
     - Active word color picker (karaoke highlight, default #FFD700 yellow)
     - Border color + border width slider (0-8px)
     - Background opacity slider (0-100%)
   - **Tab Position:**
     - Position preset: Top / Center / Bottom (default Bottom)
     - Margin vertical slider (0-400px, default 326)
     - Alignment: Left / Center / Right
     - Max line (1-3, default 2)
     - Max chars per line (auto-calculated based on font size, override allowed)
   - **Tab Animation:**
     - Karaoke style: **Word highlight** (default) / Line fade / Pop / None
     - Animation speed (slow/medium/fast)
     - Words per line slider (2-6, default 3)
     - Pre-roll fade-in toggle

4. **Preset Templates strip** (4 card horizontal scroll):
   - 🎬 **"Cinematic"** (Anton, big bottom center, yellow active) — DEFAULT
   - ✨ **"Subtle"** (Inter, medium bottom, white active)
   - 🔥 **"Bold Statement"** (Bebas Neue, XL center, red active)
   - 🎨 **"Custom"** (current tenant config)
   - Click → apply preset to all settings

5. **Action Bar (sticky bottom):**
   - "💾 Save & Apply" primary button
   - "🎬 Test on sample video" — render 10s preview clip in modal
   - "↺ Reset to default" link

6. **Tier Restriction (Starter):**
   - Preset only, advanced custom locked dengan blur overlay + "Upgrade ke Pro untuk full kustomisasi"

**Mobile:** preview area collapse jadi top section, config tabs jadi accordion.

---

#### D16. Config — Quality Gate (`/config/quality`)

**Purpose:** Tenant Pro+ atur threshold viral score + retry logic + action on fail.

**Layout:**

1. **Header:** "Quality Gate" + 🔒 badge "Pro+ feature"

2. **Lock State for Starter:**
   - Gray overlay dengan blur background
   - Icon shield + "Quality Gate kustomisasi hanya untuk paket Pro+"
   - "Lihat default settings" link (read-only view)
   - "Upgrade ke Pro" CTA primary

3. **Main settings (Pro+ unlocked):**

   - **Minimum Viral Score** card:
     - Slider 50-90, default 75
     - Live histogram: distribusi score channel 30 hari terakhir + threshold line bergerak
     - Caption dynamic: "Dengan threshold 75, **87% video Anda lewat** (152 dari 175 minggu lalu)"
     - Pakai data real dari tenant
   
   - **Max Retry** card:
     - Stepper input (1-5, default 3)
     - Cost implication note: "💰 Setiap retry ~$0.07 LLM cost. 3 retry = max $0.21 per failed attempt"
   
   - **Action on Fail** radio card:
     - 🛑 **"Skip publish + Telegram notif"** (default — kualitas first, sesuai prinsip [[project_vision]])
     - ⚠️ "Publish anyway dengan tag warning"
     - ⏸️ "Pause channel sampai admin review"
   
   - **Per-Dimension Thresholds** (collapsible advanced section):
     - 6 individual slider untuk setiap dimensi viral scoring:
       - Hook Power (default 80)
       - Curiosity Gap (default 80)
       - Retention Arc (default 80)
       - Emotional Peak (default 80)
       - Information Density (default 75)
       - CTA Strength (default 70)
     - Each slider dengan tooltip explain dimensi
     - "Reset all to default" link

4. **Quality History Stats:**
   - "Last 30 hari: 85% pass rate"
   - Bar chart per-dimension avg score actual
   - "Failed runs breakdown" — donut: 60% rendah di Emotional Peak, 25% rendah di Hook Power, dll.

5. **AI Recommendation card** (insight-style, violet glow):
   - 💡 "Hook Power di channel Anda avg 76 — naikkan threshold ke 80 untuk hasil lebih konsisten?"
   - Apply button inline

**Empty state (insufficient data):** "Butuh min 5 video untuk menampilkan stats. Lanjutkan produksi atau pakai default config."

---

#### D17. Config — Notifications Preferences (`/config/notifications`)

**Purpose:** Tenant pilih event apa yang notifikasi via channel apa.

**Layout:**

1. **Header:** "Notifications Preferences"

2. **Channel Setup section** (3 expand card):

   - **📱 Telegram** card:
     - Status indicator: 🟢 Connected / 🟡 Not configured / 🔴 Error
     - Bot token field (read-only, platform-managed): `@MesinViralBot`
     - Chat ID input + "Test Telegram" button (kirim test notif)
     - Tutorial link: "📖 Cara setup Telegram bot chat ID" (modal step-by-step + video)

   - **📧 Email** card:
     - Email tujuan default: tenant's account email (override allowed)
     - "Send test email" button
     - Email format preview thumbnail

   - **🔗 Webhook** card (Enterprise badge):
     - URL input + HMAC secret (untuk verification)
     - "Test webhook" button + last delivery status indicator
     - Format: JSON payload sample preview

3. **Event Matrix Table** (kompak):
   - Rows = events (dengan icon):
     - ✅ Video Published (sukses upload YT)
     - ❌ Run Failed (pipeline error)
     - ⚠️ Quality Gate Failed (script tidak lewat threshold)
     - 🚫 Channel Suspended
     - 🛡️ Compliance Score Low (< 70)
     - ⏰ Trial Ending (3 hari + 1 hari sebelum end)
     - 💳 Payment Failed
     - 💡 Self-Learning Insight (insight baru ditemukan)
     - 📊 Weekly Digest (Senin pagi)
   - Columns = channels: Telegram | Email | Webhook | In-app
   - Cells = checkbox untuk toggle each event × channel combo
   - Header row: "Toggle all in column" link per kolom
   - Sticky header on scroll

4. **Notification Preview cards** (2-col):
   - Sample Telegram notif format (chat bubble mockup)
   - Sample email template thumbnail dengan brand header

5. **Quiet Hours section** (Pro+ collapsible):
   - Toggle "Aktifkan quiet hours"
   - Time range picker (default 22:00 - 07:00 WIB)
   - Caption: "Notif di-queue, batch send saat morning"

**Empty/error state:** Telegram bot not connected → highlighted card dengan setup CTA.

---

#### D18. Config — Niches (`/config/niches`)

**Purpose:** Tenant browse catalog niche, pilih yang aktif untuk channel-nya, request custom niche (add-on).

**Layout:**

1. **Header:** "Niches" + counter "**3 dari 4 niche aktif** (Pro plan)"

2. **Active Niches section (top):**
   - 4-col grid card niche aktif:
     - Thumbnail moodboard (3-image collage)
     - Niche name (bahasa Indonesia)
     - Keyword preview (3-5 tags)
     - Stats: "47 video produced, avg 2.3K views"
     - Active toggle (deactivate = freeup slot)
     - "Edit per-channel" link (kalau multi-channel)
   - Empty slot card kalau ada quota tersisa: dashed border + "+ Add niche from catalog"

3. **Niche Catalog Browser:**
   - Filter tabs: All (4) / Active / Inactive / Premium (locked) / Custom (add-on)
   - Search bar
   - 3-col grid semua niche tersedia di catalog:
     - Each card: thumbnail (moodboard) + name + 1-line description + sample video link + "▶ Sample" mini player
     - Button state:
       - "Activate" (kalau slot tersisa)
       - "Swap with..." dropdown (kalau slot penuh, pilih yang di-deactivate)
       - "🔒 Premium" lock badge untuk niche locked at tier

4. **🌟 "New This Month" Section** (monthly release showcase):
   - Featured horizontal scroll niche baru bulan ini (released by admin)
   - Each card: thumbnail moodboard + name + "Released [date]" + description + "▶ Sample video" + "Activate" CTA
   - Animation: subtle glow accent untuk yang very-new (< 7 hari released)

5. **Custom Niche Request — DUAL OPTION** (large card, subtle violet gradient):
   - 🎨 Headline: "Tidak menemukan niche yang cocok?"
   - **Two side-by-side option cards:**

     **🌍 Public Niche** — Card 1
     - Price displayed dynamically: `{{pricing.custom_niche_public_90d}}` *(rendered dari `pricing_config` table — TIDAK hardcode)*
     - "90 hari exclusive untuk channel-mu, lalu masuk public catalog"
     - "Affordable. Recommended untuk solo creator."
     - "Request Public Niche" button → modal form

     **🔒 Permanent Private** — Card 2
     - Price displayed dynamically: `{{pricing.custom_niche_private}}` *(rendered dari DB)*
     - "Never public. Permanent exclusive untuk channel-mu."
     - "Premium positioning untuk agency."
     - "Request Private Niche" button → modal form

   - Form modal (sama untuk both): niche idea description (textarea), target audience (chips), sample existing YT channel URLs, color palette + voice preferences, estimated viral angle, expected ROI/use case
   - SLA badge: "3-5 hari delivery"

6. **Sub-Tag Pool per Active Niche** (collapsible section per niche):
   - 20-30 tag chip dari `niches.tag_pool` admin-curated
   - Tenant pilih default tag preference per niche (favorite chips)
   - Tooltip: "Sub-tag dipakai untuk variety tracking + YouTube hashtag granular"

7. **Per-Channel Niche Override section** (kalau multi-channel):
   - Table: Channel name | Default niche (dari config global) | Override (dropdown ke niche lain dari yang active)
   - "Apply override" button per row

**Empty state (Starter 1 slot only):** "Pilih 1 niche utama untuk channel Anda" + onboarding-style guidance.

**⚠️ CRITICAL DESIGN NOTE:** Semua nominal harga di screen ini (Rp 299K, Rp 1.499K, dll.) HARUS render dari API call ke `pricing_config` table, BUKAN string literal di HTML/JSX. Pakai placeholder `{{pricing.<key>}}` di mockup untuk signal ini. Backend ada helper `src/utils/pricing.py::get_price(key)`.

---

#### D19. Config — Hashtags (`/config/hashtags`)

**Purpose:** Tenant edit pool hashtag per niche untuk YouTube metadata.

**Layout:**

1. **Header:** "Hashtags Pool"

2. **Tab per niche aktif** (horizontal scroll kalau banyak):
   - Universe Mysteries | Dark History | Ocean Mysteries | Fun Facts | + Add niche tab

3. **Per Niche Content (saat tab dipilih):**

   - **Default Pool section** (read-only):
     - Card abu-abu dengan list 20-30 hashtag chip default dari platform
     - Caption: "Default oleh mesinviral.com. Dipakai jika custom kosong."

   - **Custom Hashtags section** (editable):
     - Tag input dengan autocomplete (suggest dari trending hashtag YouTube terkini)
     - Chip list dengan X button per chip
     - Counter: "8/15 custom (Pro plan)" — paket limit
     - Drag-to-reorder priority

   - **Blacklist section** (tenant block specific tags dari muncul di video manapun):
     - Tag input + chip list
     - Use case: avoid tag yang demonetized atau off-brand

   - **Live Preview card:**
     - "Sample video metadata akan include:"
     - List 15 hashtag final (mix custom + default, di-blacklist removed)
     - Format: `#cosmic #mystery #fun #space #...`
     - Character count: "97/100 (limit YT)"

   - **AI Optimize button** (Pro+):
     - "✨ Optimize via AI" — re-generate optimal hashtags berdasarkan top performing video di niche
     - Modal show before/after comparison + apply/reject

**Tier restriction:** Starter pakai default only (custom locked).

---

#### D20. Compliance Score Detail (`/compliance` atau `/channels/[id]/compliance`)

**Purpose:** Deep dive AI Slop Defense status per channel — pillar product survival.

**Layout:**

1. **Header:**
   - "Compliance Score — Misteri Samudra" (channel name)
   - Last updated: "2 jam lalu"
   - Channel selector dropdown

2. **Hero Metric (large):**
   - Circular gauge **87/100** + label "**Healthy**" (color: 🟢 > 80, 🟡 60-80, 🔴 < 60)
   - Sub-text: "Channel Anda aman dari risiko AI policy 2026"

3. **Breakdown Spider Chart (5 axis):**
   - Voice diversity: 95%
   - Niche distribution: 85%
   - Hook style variation: 90%
   - Days since duplicate slug: 95%
   - YouTube AI disclosure: 100%
   - Overlay current vs ideal (target lines)

4. **Per-Dimension Detail Cards (5 cards, 2-col grid):**

   - **🎤 Voice Diversity** card:
     - Chart distribusi voice usage last 30 days (donut)
     - Stats: "7 voice rotated (target: ≥5)"
     - Recommendation: "✅ Sangat baik. Optional: tambah 2 voice female untuk balance gender"

   - **📂 Niche Distribution** card:
     - Donut chart distribusi niche
     - "🟡 Niche 'dark_history' over-produced (45% last 7 days) — diversity guard akan rotate"

   - **🎣 Hook Style Variation** card:
     - Bar chart 6 hook pattern (gap_question, surprise_stat, contrarian, story_bait, time_pressure, identity)
     - Action: "Tambah variety di pattern 'time_pressure' (hanya 5%)"

   - **🔄 Duplicate Detection** card:
     - Stats: "Last duplicate slug: 27 hari lalu"
     - List 10 recent topic dengan similarity score
     - "Slug 'kapal-hilang-bermuda' similar to 'kapal-misterius-bermuda' (78%)"

   - **🤖 AI Disclosure Compliance** card:
     - Toggle status: "AI Disclosure tag = ON di semua video"
     - Audit log YouTube self-identification (last 30 video)
     - Educational link

5. **90-Day Trend Chart:**
   - Compliance Score over time area chart
   - Annotation events: "Aug 5: Added voice Sarah", "Aug 12: Diversity guard activated"

6. **Action Items Panel** (priority alerts, kalau score < 80):
   - 🟡 "Voice rotation di-dominasi 'Adam' (45% of videos) — recommend tambah voice female"
   - 🟡 "Niche 'dark_history' over-produced (60% last 7 days) — adjust schedule"
   - Each action: inline "Apply fix" button + "Snooze" + "Dismiss"

7. **Educational Panel (bottom):**
   - "📚 Why this matters" — embed video 2 menit explain YouTube AI policy crackdown 2026
   - FAQ: "Apa yang terjadi kalau score < 60?"

**Empty state (insufficient data, < 10 videos):** "Compliance Score muncul setelah 10 video produksi"

---

#### D21. Self-Learning Insights (`/insights` atau `/channels/[id]/insights`)

**Purpose:** Tenant lihat detail apa yang mesin pelajari dari channel mereka — moat utama produk.

**Layout:**

1. **Header:**
   - "Self-Learning Insights — Misteri Samudra"
   - Channel selector
   - Performance grade badge: **"Optimizing"** (chip: insufficient_data / learning / optimizing / peak)

2. **Summary Hero card** (violet gradient subtle):
   - "🧠 Mesin sudah belajar dari **87 video** di channel ini"
   - "Last analytics pull: 2 jam lalu"
   - "Next adaptation: weekly Senin 07:00 WIB"
   - Mini stat strip: Niche weight adjustments 3 | Hook adaptations 5 | Topic clusters discovered 12

3. **Insights Timeline (vertical, recent first):**
   - Each insight card (violet accent border):
     - Date + insight type icon
     - Title: "**Hook style 'gap question' perform 2.3x lebih baik** dari avg"
     - Mini chart support: bar comparison
     - Adaptation: "✨ Mesin akan prioritaskan 'gap question' di 60% video baru (sebelumnya 25%)"
     - Confidence: "Based on 23 videos data, p=0.97"
     - Actions row: ✅ Accept (default) | ❌ Reject (dropdown reason) | 💬 Comment | ⏰ Snooze 7 days
     - Status badge: Auto-applied / Pending review / Rejected (user)

4. **Insight Categories Filter:**
   - All | Niche Performance | Hook Patterns | Topic Clusters | Publish Time | Music Mood | Voice Style

5. **History of Adaptations (audit log table):**
   - Columns: Date | Insight | Adaptation Applied | Status | Performance Impact (after 14d)
   - Sortable, filterable

6. **Manual Override Panel:**
   - "Manually adjust learnings" — for power users
   - Override niche weight slider
   - Hook preference manual ranking
   - "Reset all learning" destructive button (dengan confirmation)

7. **Education Panel (bottom):**
   - "📚 Bagaimana Self-Learning bekerja?" — embed explainer
   - FAQ: "Apakah mesin belajar antar-channel?" (TIDAK — per-channel isolation)

**Empty state (grade=insufficient_data, < 5 videos):**
- 🌱 Illustration
- "Mesin sedang mengumpulkan data. Insights pertama muncul setelah ~5 video published."
- Progress: "3/5 video"

---

### SECTION E — Admin Internal (admin.mesinviral.com)

---

#### E1. Tenants Management (`/admin/tenants`)

- Data table: Tenant ID | Email | Plan | Status (Active/Trial/Suspended) | MRR | Joined | Last activity
- Filter + search
- Row click → drawer dengan tenant detail: plan, channels, recent runs, billing history, support tickets
- Actions: Suspend, Refund, Add credit, Send email, Impersonate (login as tenant)

---

#### E2. Catalog Management (`/admin/catalog`)

**Tabs:** AI Models | **Music Library (lihat E2.2 detail)** | Niche Library | Voice Templates | **Content Languages (E2.5)**

##### E2.1 — Tab AI Models
- Data table: model_key | platform (openai/anthropic/replicate) | model_id | description | size/cost class | is_active | actions
- Add/Edit/Disable model (form modal)
- Sync indicator dengan provider catalog (mis. flag deprecated models)
- Bulk operations: enable/disable

---

##### E2.2 — Tab Music Library (PRIMARY ADMIN SCREEN — DETAILED)

**Purpose:** System Administrator full CRUD untuk music library yang dipakai semua tenant. Manage upload, tagging, kualitas, license, dan usage analytics across R2 bucket + Supabase `music_library` table.

**Layout:**

1. **Header Strip**
   - "Music Library Management" + breadcrumb
   - **Stats strip (5 KPI mini-card):**
     - Total tracks: 487
     - Active: 412 (yang tersedia untuk tenant)
     - Pending review: 8 (baru upload, belum approved)
     - Disabled: 67 (manual disable atau quality issues)
     - R2 storage: 4.2 GB / 50 GB plan
   - Actions: **"+ Upload Track"** (single) + **"+ Bulk Upload"** + **"Run R2 Integrity Check"** (3-dot menu)

2. **Filter Bar (sticky):**
   - **Status:** All / Active / Pending / Disabled / Rejected
   - **Mood:** multi-select dari 15 mood (dramatic, mysterious, epic, dst.)
   - **Niche compat:** multi-select (universe_mysteries, dark_history, ocean_mysteries, fun_facts)
   - **BPM range slider** (60-180 BPM)
   - **Duration range** (15-300 detik)
   - **License type:** Royalty-free / Licensed / Original / CC0 / Unknown
   - **Quality issues only** toggle
   - **Search:** name, tag, filename, R2 path
   - **Sort dropdown:** Recently added | Most used | Best performance | A-Z | File size

3. **Main Data Table (full-width)**
   - Selectable rows (checkbox column) untuk bulk operations
   - Columns:
     - ▶ Play (inline mini player, click → play/pause)
     - 🌊 Waveform thumb (60×30px static visualization)
     - Track name (editable inline, click to edit)
     - Mood tags (multi badge, click → edit drawer)
     - Niche compat (multi badge)
     - BPM
     - Duration
     - File size
     - Bitrate (kbps)
     - LUFS (loudness, integrated)
     - **Used by N tenants** (sortable)
     - **Used in M videos** (sortable)
     - **Avg performance** (CTR uplift indicator, 🟢 +1.4x / 🟡 baseline / 🔴 -0.7x)
     - Status badge (Active / Pending / Disabled / Rejected)
     - Quality issues icon (⚠️ kalau ada, hover → list issues)
     - Actions menu: ✏️ Edit | 🚫 Disable/Enable | 🗑️ Delete | 👁️ View Usage Detail

4. **Bulk Operations Panel** (muncul saat ≥1 row selected, sticky bottom)
   - "N tracks selected"
   - Buttons: Bulk Tag (mood + niche) | Bulk Activate | Bulk Disable | Bulk Reject (dengan reason) | Bulk Export CSV | Bulk Delete (confirmation modal destructive)

5. **Detail Drawer** (slide-in right, ESC to close — saat klik row atau Edit)
   - Tab navigation: **Metadata** | **File** | **License** | **Usage** | **Quality**
   
   **Tab Metadata:**
   - Track name input
   - Description textarea
   - Mood multi-select (drag to reorder priority)
   - Niche compat multi-select
   - BPM (manual override + "Auto-detect" button)
   - Key (manual + auto-detect: e.g., "F# minor")
   - Energy level slider 1-10
   - Tempo descriptor (Slow / Mid / Fast / Variable)
   - Custom tags (free-text chips)
   - Save / Cancel

   **Tab File:**
   - R2 path: `music/{niche}/{mood}/{filename}.mp3` (copy button)
   - File size + format (MP3 / WAV / FLAC)
   - Bitrate + sample rate
   - LUFS analysis: Integrated -14 LUFS (target -14 to -16 untuk Shorts), True peak -1.2 dBFS
   - **Full waveform visualization** (interactive, click to seek, zoom in/out)
   - Audio player full-control (play/pause/seek/volume)
   - "Re-process file" button (re-detect BPM, LUFS, key)
   - "Download original" button
   - "Replace file" (upload new version, archive old)

   **Tab License:**
   - License type dropdown
   - Source URL (link out)
   - Attribution text (required toggle + textarea)
   - Original purchase receipt: upload file
   - Expiry date (optional, untuk licensed tracks)
   - Notes textarea

   **Tab Usage:**
   - **Chart usage trend 90 hari** (area chart, total plays per day)
   - **Top tenants using this track** (table: tenant_id | channel | count used | avg CTR videos with this track)
   - **Performance per niche** (when paired with niche X, CTR =Y)
   - Heatmap: usage by day-of-week × hour-of-day

   **Tab Quality:**
   - Auto-detected issues list:
     - ⚠️ "Clipping detected at 0:23-0:25"
     - ⚠️ "Silence > 2s at 1:14"
     - ⚠️ "LUFS -22 (too quiet, normalize?)"
     - ⚠️ "Abrupt cut at end (no fade out)"
   - Per issue: severity (info/warning/error) + "Fix suggestion" (e.g., "Apply -2dB compression")
   - "Mark as resolved" / "Reject track" buttons

6. **Upload Single Track Modal**
   - **Step 1: File Drop**
     - Dropzone (drag-drop atau click to browse)
     - Accepted: MP3, WAV, FLAC. Max 20MB.
     - Validation: format check, size check, audio integrity
   - **Step 2: Auto-Process (loading screen ~10-30s)**
     - Live progress: Duration ✓ → BPM detection ✓ → LUFS measurement ✓ → Key detection ✓ → Waveform generation ✓
     - Pakai librosa / Essentia di backend
   - **Step 3: Review Auto-Detected**
     - Preview waveform
     - Auto-detected: duration 58s, BPM 92, key F# minor, LUFS -15
     - Override any value
   - **Step 4: Tag Form**
     - Mood (multi-select, required)
     - Niche compat (multi-select, required)
     - License type + source + attribution
     - Description (optional)
   - **Step 5: Upload to R2 + DB**
     - Progress bar
     - On success: redirect to track detail drawer

7. **Bulk Upload Modal**
   - **Step 1: Files Drop** (multi-file or folder drag)
   - **Step 2: CSV Metadata Import** (optional)
     - Download template button: `bulk_music_template.csv` (columns: filename, name, mood, niche, license_type, source_url, attribution)
     - Upload filled CSV
     - Match files dengan CSV rows (by filename)
   - **Step 3: Processing Queue**
     - Table: filename | status (queued/processing/done/error) | progress | BPM detected | actions (cancel)
     - Background processing dengan WebSocket update
   - **Step 4: Review Batch**
     - All processed tracks listed
     - Per-row: review tags, accept / reject
   - **Step 5: Bulk Activate**
     - Final confirm → semua "Pending" → "Active"

8. **R2 Integrity Check Panel** (modal atau drawer)
   - "Last sync: 2 jam lalu"
   - Comparison:
     - DB tracks: 487
     - R2 files: 489
     - **Mismatch detected:** 2 files
   - Issues list:
     - 🔴 "Orphan R2 file: `music/ocean_mysteries/mysterious/abandoned_track.mp3`" (no DB row) + "Delete from R2" / "Create DB row" actions
     - 🔴 "Orphan DB row: ID 234 'Lost Track'" (file missing in R2) + "Re-upload" / "Delete DB row" actions
   - "Run check now" button → background job

9. **Quality Issues Dashboard** (separate panel)
   - List semua track dengan auto-detected issues (sortable by severity)
   - Click → drawer Quality tab pre-opened
   - Filter: severity, issue type

10. **Activity Log** (sidebar atau bottom)
    - Real-time stream activity admin:
      - "30 tracks bulk uploaded by admin@mesinviral.com — 2 jam lalu"
      - "Track 'Cosmic Dread' tagged mood=mysterious by admin@... — 4 jam lalu"
      - "Track 'Old Track' disabled (quality issue) — 1 hari lalu"
    - Filter by admin user, action type, date range
    - Export CSV

**Empty state (library kosong):**
- Centered illustration musical note
- "Belum ada track. Upload track pertama untuk mulai isi library."
- "+ Upload Track" primary CTA

**Empty state (no search result):**
- "Tidak ada track sesuai filter."
- "Reset filter" + "Upload new track" CTA

**Mobile:** table jadi card stack, drawer jadi full-screen modal. Admin tools terutama desktop-first — mobile limited untuk approve/reject pending tracks only.

---

##### E2.3 — Tab Niche Library (DETAILED)

**Purpose:** System admin manage broad niche catalog + tag pool + monthly release scheduler + exclusivity manager.

**Layout:**

1. **Header strip:**
   - "Niche Library Management"
   - Stats: Active (4) | Pending release (2) | Private exclusive (1) | Public coming from 90d (3)
   - "+ Create New Niche" + "📅 Schedule Monthly Release" buttons

2. **View tabs:** All | Active | Pending Release | Private Exclusive | Public-after-90d Pipeline | Archived

3. **Data Table:**
   - Columns: Niche key | Display name | Access type badge | Tenant count using | Videos count | Avg performance | Released date | Exclusive until | Actions
   - Click row → drawer dengan full edit

4. **Detail Drawer (slide-in right) — 6 tab:**

   **Tab 1: Identity**
   - niche_key (slug, lowercase_underscore, read-only after create)
   - Display name (Indonesian + English)
   - Description (textarea)
   - Keywords multi-tag (untuk trend scanning)
   - Thumbnail moodboard (3-image upload)
   - target_emotion text
   - is_active toggle

   **Tab 2: Voice DNA**
   - voice_profile JSON editor (style, tone, emotion_arc, language_register)
   - Preview play sample TTS dengan voice config
   - Default voice ElevenLabs picker

   **Tab 3: Visual DNA**
   - visual_style JSON editor (base_style, color_palette, atmosphere)
   - Generate sample image via gpt-image-1-mini untuk preview
   - Color palette swatches

   **Tab 4: Music + Scoring**
   - mood_priority drag-drop list dari moods catalog
   - emotion_scoring_criteria textarea (untuk ScriptAnalyzer niche-aware)
   - default_hashtags multi-tag editor

   **Tab 5: 🆕 Tag Pool**
   - 20-30 sub-tag chips (admin-curated)
   - Add/remove tag dengan inline edit
   - Each tag: usage count across all videos
   - Performance per tag chart (CTR avg)
   - "Suggest new tags via AI" button (analyze recent videos di niche untuk auto-suggest)

   **Tab 6: 🆕 Access & Exclusivity**
   - access_type radio:
     - 🌍 Public (default catalog, semua tenant)
     - 📅 Release Pending (admin curate, belum publish ke catalog)
     - 🔒 Private Exclusive (specific tenant only, permanent)
     - ⏳ Public-after-90d (specific tenant exclusive sampai date, lalu public)
   - exclusive_tenant_id dropdown (kalau Private atau Public-after-90d)
   - exclusive_until date picker
   - released_at date (auto-set saat status → public)
   - Audit trail: history access type changes

5. **🆕 Monthly Release Scheduler Panel** (dedicated section atau modal):
   - Calendar view: niche release scheduled per month
   - Drag-to-reschedule
   - "Send release announcement email" toggle per release (semua tenant atau filter tier)
   - Preview email template
   - Bulk schedule wizard

6. **🆕 Exclusivity Pipeline View** (table separate):
   - List niche dengan exclusive_until in future
   - Columns: Niche | Exclusive to tenant | Until date | Days remaining | "Transition to public" action
   - Auto-transition cron job indicator
   - Action button: "Extend exclusivity" (negotiate dengan tenant)

7. **Activity log** (bottom):
   - "Niche 'crypto_detective' released to public catalog by admin@... 2 jam lalu"
   - "Niche 'wayang_history' exclusive extended to 2026-12-01 (tenant ID: agency_wayang)"

**Empty state:** "Belum ada niche di catalog. Buat niche pertama atau seed dari template."

**Mobile:** table jadi card stack, drawer jadi full-screen modal.

---

##### E2.4 — Tab Voice Templates
- Assign default voice per niche (dropdown dari ElevenLabs library)
- Voice metadata: language, gender, style, age range
- Preview play per voice

##### E2.5 — Tab Content Languages (🆕 catalog config-driven)
- CRUD catalog bahasa konten yang tersedia untuk tenant (pola sama dgn pricing/niche — admin-managed, BUKAN hardcode di kode/UI)
- Kolom per row: `locale` (BCP-47, mis. id-ID / en-US / ms-MY / th-TH), `display_name`, `tts_providers_supported` (ElevenLabs/OpenAI/Edge), `quality_tier` (official/experimental), `caption_font` (font default dgn glyph coverage), `is_active`
- Toggle active/inactive per bahasa → langsung mempengaruhi dropdown "Bahasa Konten" di onboarding C4 + D3 Channel Settings
- Seed saat launch: **id-ID + en-US (official)**; ms-MY, fil-PH, th-TH, vi-VN (experimental — aktifkan setelah QA voice + font glyph)

---

#### E5. Admin Pricing Config (`/admin/pricing`) — 🆕 NEW

**Purpose:** Single source of truth untuk SEMUA pricing nominal di sistem. Sysadmin adjust pricing tanpa redeploy. Read by UI tenant + backend logic via API.

**Why:** Pricing tidak boleh hardcode (per [[feedback_no_hardcode]] scope extended). Subscription, add-on, one-time fee — semua editable di sini.

**Layout:**

1. **Header:**
   - "Pricing Configuration"
   - Stats: Total pricing entries (25) | Last change (2 jam lalu by admin@...) | Active (23) | Inactive (2)
   - "+ New Pricing Entry" button + "📥 Import from CSV" + "📤 Export current"

2. **Filter bar:**
   - Category: All / Subscription / Add-on / One-time / Discount
   - Status: Active / Inactive / Scheduled (effective_from di future) / Expired (effective_until lewat)
   - Search by key

3. **Data Table** (sortable):
   - Columns:
     - Key (mis. `custom_niche_public_90d`)
     - Description (e.g. "Custom niche public after 90 hari")
     - Category badge (subscription/add-on/one-time)
     - Value IDR (editable inline)
     - Value USD cents (editable inline)
     - Effective from (date picker)
     - Effective until (date picker, optional untuk seasonal/promo)
     - Active toggle
     - Last updated (by who, when)
     - Actions: Edit | History (audit log) | Duplicate | Archive
   - Bulk operations: bulk activate/deactivate, export selected

4. **Detail Drawer / Edit Modal:**
   - **Tab 1: Pricing**
     - Key (read-only after create)
     - Description
     - Category dropdown
     - Value IDR input
     - Value USD cents input
     - Auto-conversion suggestion: "Berdasarkan kurs 16000 IDR/USD: Rp 299.000 ≈ $18.69"
     - "Use auto conversion" button
   - **Tab 2: Schedule**
     - Effective from datetime picker
     - Effective until datetime picker (optional)
     - Active toggle
     - "Schedule for next month" quick action
   - **Tab 3: Audit Log**
     - Timeline of changes: who, when, before → after value
     - "Rollback to version X" button
   - **Tab 4: Where Used**
     - List screens/components yang reference this pricing key
     - "Test in preview" button → opens tenant UI in iframe dengan this pricing applied

5. **Common Categories Section** (quick-edit cards):
   - **Subscription Tiers card:**
     - 3 input row: Starter | Pro | Scale
     - Inline edit IDR + USD
     - "Save all" button
   - **Add-ons card:**
     - Custom niche public-90d, Custom niche private, Voice pack, Niche audit, Concierge setup, Priority queue
   - **Discounts card:**
     - Annual prepay % off
     - First-month promo
     - Referral discount

6. **🆕 Promo/Seasonal Scheduler** (timeline view):
   - Calendar view upcoming pricing changes (Black Friday discount, Anniversary promo, dll.)
   - Drag-to-reschedule
   - "Create campaign" wizard (set discount % + duration + applicable plans)

7. **Audit & Compliance Log** (bottom strip):
   - "All pricing changes log" (full chronological)
   - Export CSV untuk accounting
   - Email digest weekly summary to admin

8. **API Documentation Panel** (right rail collapsible):
   - "Pricing API endpoint: GET /api/pricing"
   - Sample response JSON
   - Cache info: "Cached 5 menit, invalidate on update"
   - "Generate webhook signature" untuk integrasi external

**Critical UX patterns:**
- ✏️ Inline editing dengan auto-save (debounced 1s)
- 🚨 Confirmation modal sebelum activate pricing change yang affect production tenants
- 📊 Impact preview: "Perubahan ini akan affect 47 active tenants"
- 🔄 Cache invalidation indicator: "Pricing cache flushed at 14:23"

**Empty state:** "Belum ada pricing config. Seed dari default values?" + import button.

**Permission:** RBAC — hanya Super Admin yang bisa edit. Audit log tetap visible untuk all admin.

---

#### E3. System Health (`/admin/system`)

- Worker status grid (multi-worker future): up/down, last heartbeat, current job
- Queue depth chart (last 24h)
- Error rate chart
- Pipeline failure breakdown by error type
- Database health (Supabase stats embed)

---

#### E4. Support Tickets (`/admin/support`)

- Inbox-style: ticket list left + conversation right
- Status filter (Open/Pending/Resolved/Closed)
- Tag system
- Quick replies template
- Tenant context sidebar (current plan, recent runs, billing)

---

### SECTION F — States & Edge Cases

---

#### F1. Empty States

Untuk setiap list/dashboard yang bisa kosong:
- Centered illustration (line-art, indigo accent)
- Headline: "Belum ada [item]"
- Subheadline: friendly explanation
- Primary CTA button

Variants:
- No channels yet → "+ Connect first channel"
- No runs yet → "Schedule akan trigger run pertama hari ini"
- No analytics yet → "Data muncul setelah 24 jam dari publish pertama"
- Search no results → "Coba kata kunci lain"

---

#### F2. Loading States

- Skeleton loaders untuk semua data fetch (matching component shape)
- Shimmer animation
- Top progress bar untuk page transitions (nprogress style)

---

#### F3. Error States

- Inline error (form field) — red text + icon below input
- Toast notifications untuk action errors (5s auto-dismiss)
- Full-page error untuk crash:
  - "Ada masalah. Tim kami sudah diberitahu."
  - Error ID untuk reference
  - Retry button + "Kembali ke dashboard" button

---

#### F4. Trial / Suspension States

- **Trial banner** (top of dashboard, sticky):
  - "Trial Anda berakhir dalam 3 hari. 2/5 video gratis terpakai."
  - "Upgrade sekarang →" CTA
  - Dismissable

- **Suspended state** (full takeover):
  - "Akun Anda di-suspend karena gagal pembayaran"
  - "Update payment method" button
  - "Hubungi support" link
  - Data tetap visible (read-only)

---

#### F5. Modal Patterns

- **Confirm:** "Hapus channel X?" + alert dialog (destructive)
- **Form modal:** "Tambah channel baru" + 3-step form
- **Detail drawer:** slide-in dari kanan, ESC to close
- **Command menu (cmd+K):** global search + quick actions

---

#### F6. Notification Patterns

- **Toast:** sonner style, top-right, color-coded
- **Bell dropdown:** list notifications dengan unread indicator
- **Notif detail:** click → relevant page (e.g., notif "Run completed" → run detail)

---

## 7. RESPONSIVE BREAKPOINTS

```
Mobile S    : 320px — minimal width support (iPhone SE)
Mobile      : 375px — default mobile
Mobile L    : 425px
Tablet      : 768px — sidebar collapse, single column
Laptop      : 1024px — sidebar permanent expanded
Desktop     : 1280px — comfortable layout
Desktop XL  : 1440px — max content width
4K          : 1920px — content max-width caps, increase padding
```

**Mobile-specific behavior:**
- Sidebar → bottom tab bar (5 main: Dashboard, Channels, Runs, Analytics, More)
- Tables → cards stack
- Multi-column layout → vertical stack
- Drawers → bottom sheet
- Cmd+K → search button in top bar

---

## 8. DELIVERABLES YANG DIHARAPKAN DARI CLAUDE DESIGN

### Phase 1 — Design System (1 batch)
1. Color palette (light + dark mode swatches)
2. Typography scale visualization
3. Spacing scale
4. Component library showcase (all components 2.8 di-visualize)
5. Iconography (custom pipeline icons + branded service icons)

### Phase 2 — Landing & Marketing (1 batch)
1. A1 Landing page (full scroll)
2. A2 Pricing page
3. A3 Demo page
4. A4 Docs structure (sidebar + article)

### Phase 3 — Authentication & Onboarding (1 batch)
1. B1-B4 Auth screens
2. C1-C5 Onboarding wizard 5 steps

### Phase 4 — Tenant Dashboard Core (1 batch)
1. D1 Main Dashboard
2. D2 Channels List
3. D3 Channel Detail
4. D4 Runs List
5. D5 Run Detail (KRITIS)

### Phase 5 — Tenant Dashboard Config & Settings (1 batch)
1. D6 Analytics
2. D7 Schedule
3. D8-D12 Config tabs (AI Engines, API Keys, Voice, Visual, **Music**)
4. **D15-D19 Config tabs (Captions, Quality Gate, Notifications, Niches, Hashtags)** ← NEW
5. **D20 Compliance Score Detail** ← NEW (pillar AI Slop Defense)
6. **D21 Self-Learning Insights** ← NEW (pillar moat #1 product)
7. D13 Billing
8. D14 Settings

### Phase 6 — Admin & Edge Cases (1 batch)
1. E1-E4 Admin pages (Tenants, Catalog dengan E2.1-E2.4 sub, System Health, Support)
2. **E5 NEW: Admin Pricing Config** ← single source of truth all pricing, editable + audit log
3. F1-F6 States & patterns

### Format Output yang Diharapkan

**Untuk setiap screen:**
- Desktop view (1440px) + Mobile view (375px)
- High-fidelity, production-ready visual
- Use real Indonesian content examples (channel name "Misteri Samudra", topic "Kapal Hilang di Segitiga Bermuda", niche names dalam ID)
- Include realistic data (view counts 1.2K-58K, dates 2026-MM-DD WIB format)
- Annotation untuk interaction (e.g., "Hover state shows tooltip")

**Untuk design system:**
- Exportable as Tailwind config / shadcn/ui theme
- Color values in hex + Tailwind class name
- Component variants visualized

---

## 9. TECHNICAL NOTES untuk Implementasi

Setelah design selesai, frontend akan dibangun dengan:
- **Next.js 15** (App Router, RSC)
- **shadcn/ui** — copy-paste components
- **Tailwind CSS** — utility-first styling
- **tremor.so** — chart components (built on Tremor)
- **Recharts** atau **visx** — custom charts kalau tremor terbatas
- **Framer Motion** — animations
- **next-intl** — i18n (ID + EN)
- **Supabase Client** — auth + realtime
- **TanStack Query** — server state
- **Zustand** — UI state
- **Sonner** — toast notifications
- **Lucide React** — icons
- **next-themes** — dark/light mode toggle

**Design harus memperhatikan:**
- Component reusability (atomic design principles)
- Tailwind utility class naming convention
- Real-time data display (Supabase Realtime subscription)
- Accessibility (WCAG AA, keyboard nav, screen reader)
- Performance (no heavy animation on mobile, lazy load images)
- SEO untuk public pages (semantic HTML, meta tags)

---

## 10. CONSTRAINTS & TONE

**DO:**
- Use indigo/violet untuk accent AI features (subtle glow)
- Show real-time elements prominently (pulse animation untuk live, smooth transitions)
- Make data feel approachable (good hierarchy, white space)
- Indonesian content examples throughout
- Status indicators clear (icon + color + label)
- Empty states warm and helpful

**DON'T:**
- Use neon "AI bro" colors (no electric green, no bright cyan)
- Overcrowd dashboard with too many widgets
- Show technical jargon without tooltip explanation
- Use stock photo people (use illustration atau abstract)
- Make CTA buttons too aggressive (no full-red urgency, prefer indigo invitations)

**Voice & Microcopy examples:**
- ✅ "Mesin sedang belajar dari channel Anda" (warm, narrative)
- ❌ "AI model training in progress" (cold, technical)
- ✅ "Trial Anda berakhir 3 hari lagi" (clear, no panic)
- ❌ "ACTION REQUIRED: Trial expiring soon" (alarming)

---

**END OF BRIEF.**

> Catatan untuk Claude Design: prioritaskan **Phase 1-2 dulu** (design system + landing) supaya foundation kuat sebelum lanjut ke dashboard yang kompleks. Setiap phase akan di-review user sebelum lanjut.
