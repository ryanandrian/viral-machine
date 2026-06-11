# Addendum untuk Claude Design — MesinViral.com (Post-Batch 1)

> ⚠️ **HISTORIS — Claude Design SUDAH SELESAI 100%.** Addendum ini (delta prompt) sudah terserap ke bundle desain + `CLAUDE_DESIGN_BRIEF.md`. Angka "38 screen" di sini **superseded → final 39**. JANGAN paste ke Claude Design lagi. Spec UI terkini = `CLAUDE_DESIGN_BRIEF.md`.

> **Cara pakai:** Copy seluruh isi file ini, paste ke Claude Design SEBELUM minta Batch berikutnya.
> Ini ADDENDUM atas brief yang sudah ada — bukan replace. Konten existing tetap valid.

---

## 1. Status Update

🎉 **Batch 1 selesai dengan baik.**

Yang sudah jadi (jangan di-redo):
- ✅ Design System foundation (tokens + component library)
- ✅ D1 Main Dashboard
- ✅ D5 Run Detail (kritis)
- ✅ D2 Channels List
- ✅ D3 Channel Detail (dengan 5 tab Overview/Runs/Analytics/Schedule/Settings)
- ✅ D4 Runs List dengan filter + drawer detail

Konsistensi shell + dark/light toggle + ID/EN toggle — semua confirmed bekerja. Mohon **lanjutkan pakai design system & component yang sama** untuk semua batch berikutnya.

---

## 2. Batch 2 Plan (yang Anda sebutkan) — APPROVED

**Lanjut sesuai rencana Anda:**
- **C1-C5** — Onboarding Wizard 5 step (Pilih Paket → Connect YouTube → API Keys → Niche & Voice → Schedule)
- **B1-B4** — Authentication (Sign Up, Sign In, Forgot Password, Email Verification)

Detail spesifik per screen sudah ada di brief original section 6 (SECTION B & C). **Tidak ada perubahan untuk Batch 2.**

**Catatan tambahan:**
- Pada C3 (Setup AI API Keys), pastikan ada **state "Skip & lakukan nanti"** karena di trial 7 hari user bisa pakai platform-managed credentials. Hanya wajib lengkap setelah trial habis.
- Pada B1 (Sign Up), pastikan testimonial card sebelah kanan benar-benar realistis (sebut nama channel Indonesia: "Misteri Samudra", "Jejak Kelam Sejarah", "Fakta Yang Bikin Mikir").

---

## 3. ‼️ ADDENDUM: 7 Screen Tambahan untuk Batch Berikutnya (Phase 5+)

Sebelum Anda mulai Batch dengan Config tabs, saya audit ulang brief dan menemukan **7 screen yang sebelumnya hanya disebut sebagai nama tab tanpa detail spec**. Berikut tambahannya:

### Screen Inventory Update

- Sebelumnya: 31 screens
- **Sekarang: 38 screens**
- Tambahan: D15 sampai D21 (7 screen baru di Section D — Tenant Dashboard)

### Phase 5 Deliverable Update

Phase 5 sekarang berisi:
1. D6 Analytics
2. D7 Schedule
3. D8 Config AI Engines
4. D9 Config API Keys
5. D10 Config Voice
6. D11 Config Visual
7. D12 Config Music *(detailed sebelumnya di v1.5 brief)*
8. **D15 Config Captions** ← NEW
9. **D16 Config Quality Gate** ← NEW (Pro+ only, dengan lock state untuk Starter)
10. **D17 Config Notifications Preferences** ← NEW
11. **D18 Config Niches** ← NEW
12. **D19 Config Hashtags** ← NEW
13. D13 Billing
14. D14 Settings

### Phase 5.5 (NEW — Standalone, RECOMMEND prioritized sebelum Billing/Settings):

15. **D20 Compliance Score Detail Page** ← NEW critical
16. **D21 Self-Learning Insights Page** ← NEW critical

**Rationale prioritization:** D20 dan D21 adalah **pillar utama produk** (Self-Learning = moat #1, AI Slop Defense = product survival). Mereka deserved dedicated page, bukan hanya widget di D1.

---

## 4. Detailed Specs untuk 7 Screen Baru

### D15. Config — Captions (`/config/captions`)

**Purpose:** Tenant atur visual style karaoke caption (subtitle ASS) yang muncul di video output.

**Layout:**

1. **Header:** "Captions Style" + tier badge

2. **Live Preview area (top, sticky on scroll):**
   - Mock video frame 9:16 aspect ratio Shorts dengan dummy clip background gelap
   - Caption sample text scrolling karaoke style — text contoh: **"Suara aneh di kedalaman Mariana Trench"**
   - **Real-time update** saat ubah setting di bawah

3. **3 Tab Config:**
   - **Tab Style:**
     - Font picker dropdown dengan thumbnail per font: Anton (default, bold display), Inter, Bebas Neue, Plus Jakarta Sans, Geist
     - Font size slider 60-150px (default 119)
     - Bold/Italic toggle
     - Color picker text (default #FFFFFF), active word color (default #FFD700 yellow)
     - Border color + width slider 0-8px
     - Background opacity slider 0-100%
   - **Tab Position:**
     - Position preset: Top / Center / Bottom (default Bottom)
     - Margin vertical slider 0-400px (default 326)
     - Alignment: Left / Center / Right
     - Max line 1-3 (default 2)
   - **Tab Animation:**
     - Karaoke style: **Word highlight** (default) / Line fade / Pop / None
     - Animation speed (slow/medium/fast)
     - Words per line slider 2-6 (default 3)

4. **Preset Templates strip** (4 card horizontal):
   - 🎬 "Cinematic" — Anton, big bottom center, yellow active (DEFAULT)
   - ✨ "Subtle" — Inter, medium, white active
   - 🔥 "Bold Statement" — Bebas Neue, XL, red active
   - 🎨 "Custom" — current tenant config

5. **Sticky Action Bar bottom:**
   - "💾 Save & Apply" primary
   - "🎬 Test on sample video" (modal preview 10s clip)
   - "↺ Reset to default"

6. **Tier restriction Starter:** preset only, advanced custom dengan blur overlay + "Upgrade ke Pro untuk full kustomisasi"

**Mobile:** preview area collapse top, tabs jadi accordion vertical.

---

### D16. Config — Quality Gate (`/config/quality`)

**Purpose:** Tenant Pro+ atur threshold viral score + retry logic + action on fail.

**Layout:**

1. **Header:** "Quality Gate" + 🔒 badge "Pro+ feature"

2. **Lock State for Starter:**
   - Gray overlay dengan blur background
   - Shield icon + "Quality Gate kustomisasi hanya untuk paket Pro+"
   - "Lihat default settings" link (read-only)
   - "Upgrade ke Pro" primary CTA

3. **Main settings (Pro+ unlocked):**

   - **Minimum Viral Score card:**
     - Slider 50-90 (default 75)
     - Live histogram: distribusi score channel 30 hari terakhir + threshold line bergerak real-time
     - Caption dynamic: "Dengan threshold 75, **87% video Anda lewat** (152 dari 175 minggu lalu)"

   - **Max Retry card:**
     - Stepper 1-5 (default 3)
     - Cost note: "💰 Setiap retry ~$0.07 LLM cost. 3 retry = max $0.21 per failed attempt"

   - **Action on Fail radio card:**
     - 🛑 **"Skip publish + Telegram notif"** (DEFAULT — kualitas first)
     - ⚠️ "Publish anyway dengan tag warning"
     - ⏸️ "Pause channel sampai admin review"

   - **Per-Dimension Thresholds (collapsible advanced):**
     - 6 slider untuk: Hook Power (80), Curiosity Gap (80), Retention Arc (80), Emotional Peak (80), Information Density (75), CTA Strength (70)
     - Each slider dengan tooltip explain dimensi
     - "Reset all to default" link

4. **Quality History Stats:**
   - "Last 30 hari: **85% pass rate**"
   - Bar chart per-dimension avg score actual
   - "Failed runs breakdown" donut: 60% rendah Emotional Peak, 25% rendah Hook Power, dll.

5. **AI Recommendation card** (insight-style, subtle violet glow border):
   - 💡 "Hook Power di channel Anda avg 76 — naikkan threshold ke 80 untuk hasil lebih konsisten?"
   - Apply button inline

**Empty state (insufficient data):** "Butuh min 5 video untuk menampilkan stats."

---

### D17. Config — Notifications Preferences (`/config/notifications`)

**Purpose:** Tenant pilih event apa yang notifikasi via channel apa.

**Layout:**

1. **Header:** "Notifications Preferences"

2. **Channel Setup section** (3 expand card):

   - **📱 Telegram:**
     - Status indicator: 🟢 Connected / 🟡 Not configured / 🔴 Error
     - Bot token read-only: `@MesinViralBot`
     - Chat ID input + "Test Telegram" button
     - Tutorial link "📖 Cara setup Telegram bot chat ID" (modal step-by-step)

   - **📧 Email:**
     - Email tujuan (default account email, override allowed)
     - "Send test email" button
     - Email format preview thumbnail

   - **🔗 Webhook** (Enterprise badge):
     - URL input + HMAC secret
     - "Test webhook" button + last delivery status
     - JSON payload sample preview

3. **Event Matrix Table** (sticky header):
   - **Rows = events (dengan icon):**
     - ✅ Video Published
     - ❌ Run Failed
     - ⚠️ Quality Gate Failed
     - 🚫 Channel Suspended
     - 🛡️ Compliance Score Low (< 70)
     - ⏰ Trial Ending (3 hari & 1 hari sebelum end)
     - 💳 Payment Failed
     - 💡 Self-Learning Insight (baru ditemukan)
     - 📊 Weekly Digest (Senin pagi)
   - **Columns:** Telegram | Email | Webhook | In-app
   - **Cells:** checkbox toggle each combo
   - Header row: "Toggle all" link per kolom

4. **Notification Preview cards** (2-col):
   - Sample Telegram notif format — chat bubble mockup
   - Sample email template thumbnail dengan brand header

5. **Quiet Hours section** (Pro+ collapsible):
   - Toggle "Aktifkan quiet hours"
   - Time range picker (default 22:00 - 07:00 WIB)
   - "Notif di-queue, batch send saat morning"

---

### D18. Config — Niches (`/config/niches`)

**Purpose:** Tenant browse catalog niche, pilih yang aktif untuk channel, request custom niche.

**Layout:**

1. **Header:** "Niches" + counter "**3 dari 4 niche aktif** (Pro plan)"

2. **Active Niches section:**
   - 4-col grid card:
     - Thumbnail moodboard (3-image collage)
     - Niche name (Bahasa Indonesia)
     - Keyword preview chips
     - Stats: "47 video produced, avg 2.3K views"
     - Active toggle (deactivate = freeup slot)
     - "Edit per-channel" link (multi-channel)
   - Empty slot card: dashed border + "+ Add niche from catalog"

3. **Niche Catalog Browser:**
   - Filter tabs: All / Active / Inactive / Premium (locked) / Custom (add-on)
   - Search bar
   - 3-col grid card semua niche:
     - Thumbnail moodboard + name + 1-line description + "▶ Sample" mini player
     - Button state: "Activate" / "Swap with..." dropdown / "🔒 Premium"

4. **Custom Niche Request CTA card** (large, subtle violet gradient):
   - 🎨 "Tidak menemukan niche yang cocok?"
   - "Request custom niche — **Rp 299K per niche**, 3-5 hari delivery"
   - "📝 Request Form" CTA → modal:
     - Niche idea description (textarea)
     - Target audience (chips)
     - Sample existing YouTube channel URLs
     - Color palette + voice preferences

5. **Per-Channel Niche Override section** (kalau multi-channel):
   - Table: Channel | Default niche | Override (dropdown)
   - "Apply override" button per row

---

### D19. Config — Hashtags (`/config/hashtags`)

**Purpose:** Tenant edit pool hashtag per niche untuk YouTube metadata.

**Layout:**

1. **Header:** "Hashtags Pool"

2. **Tab per niche aktif** (horizontal scroll): Universe Mysteries | Dark History | Ocean Mysteries | Fun Facts | + Add niche

3. **Per Niche Content:**
   - **Default Pool** (read-only, abu-abu):
     - List 20-30 hashtag chip default
     - Caption: "Default oleh mesinviral.com. Dipakai jika custom kosong."

   - **Custom Hashtags** (editable):
     - Tag input dengan autocomplete (suggest dari trending hashtag YouTube)
     - Chip list dengan X button
     - Counter: "8/15 custom (Pro plan)"
     - Drag-to-reorder priority

   - **Blacklist section:**
     - Tag input + chip list
     - Use case: avoid demonetized atau off-brand tags

   - **Live Preview card:**
     - "Sample video metadata akan include:"
     - List 15 hashtag final
     - Format: `#cosmic #mystery #fun #space #...`
     - Character count: "97/100 (limit YT)"

   - **AI Optimize button** (Pro+):
     - "✨ Optimize via AI" — re-generate optimal hashtags berdasarkan top performing video
     - Modal: before/after comparison + apply/reject

**Tier:** Starter pakai default only (custom locked).

---

### D20. Compliance Score Detail (`/compliance` atau `/channels/[id]/compliance`)

**⚠️ CRITICAL screen — pillar product survival (AI Slop Defense).**

**Purpose:** Deep dive AI Slop Defense status per channel.

**Layout:**

1. **Header:**
   - "Compliance Score — Misteri Samudra"
   - Last updated: "2 jam lalu"
   - Channel selector dropdown

2. **Hero Metric (large, prominent):**
   - Circular gauge **87/100** + label "**Healthy**" (color: 🟢 > 80, 🟡 60-80, 🔴 < 60)
   - Sub-text: "Channel Anda aman dari risiko AI policy 2026"

3. **Breakdown Spider Chart (5 axis):**
   - Voice diversity: 95%
   - Niche distribution: 85%
   - Hook style variation: 90%
   - Days since duplicate slug: 95%
   - YouTube AI disclosure: 100%
   - Overlay current vs ideal target

4. **Per-Dimension Detail Cards (2-col grid):**

   - **🎤 Voice Diversity:**
     - Chart distribusi voice usage 30 days (donut)
     - Stats: "7 voice rotated (target: ≥5)"
     - "✅ Sangat baik. Optional: tambah 2 voice female untuk balance gender"

   - **📂 Niche Distribution:**
     - Donut chart distribusi niche
     - "🟡 Niche 'dark_history' over-produced (45% last 7 days) — diversity guard akan rotate"

   - **🎣 Hook Style Variation:**
     - Bar chart 6 hook pattern (gap_question, surprise_stat, contrarian, story_bait, time_pressure, identity)
     - "Tambah variety di pattern 'time_pressure' (hanya 5%)"

   - **🔄 Duplicate Detection:**
     - "Last duplicate slug: 27 hari lalu"
     - List 10 recent topic dengan similarity score
     - "Slug 'kapal-hilang-bermuda' similar to 'kapal-misterius-bermuda' (78%)"

   - **🤖 AI Disclosure:**
     - Toggle status: "AI Disclosure tag = ON di semua video"
     - Audit log YouTube self-identification

5. **90-Day Trend Chart** — Compliance Score over time area chart dengan annotation events

6. **Action Items Panel** (jika score < 80):
   - 🟡 "Voice rotation di-dominasi 'Adam' (45% of videos) — recommend tambah voice female"
   - 🟡 "Niche 'dark_history' over-produced (60% last 7 days) — adjust schedule"
   - Each action: inline "Apply fix" + "Snooze" + "Dismiss"

7. **Educational Panel:**
   - "📚 Why this matters" — embed video 2 menit explain YouTube AI policy crackdown 2026
   - FAQ: "Apa yang terjadi kalau score < 60?"

**Empty state (< 10 videos):** "Compliance Score muncul setelah 10 video produksi"

---

### D21. Self-Learning Insights (`/insights` atau `/channels/[id]/insights`)

**⚠️ CRITICAL screen — pillar moat #1 product (Self-Learning).**

**Purpose:** Tenant lihat detail apa yang mesin pelajari dari channel mereka.

**Layout:**

1. **Header:**
   - "Self-Learning Insights — Misteri Samudra"
   - Channel selector
   - Performance grade badge: **"Optimizing"** (chip: insufficient_data / learning / optimizing / peak)

2. **Summary Hero Card** (subtle violet gradient untuk AI feature treatment):
   - "🧠 Mesin sudah belajar dari **87 video** di channel ini"
   - "Last analytics pull: 2 jam lalu"
   - "Next adaptation: weekly Senin 07:00 WIB"
   - Mini stat strip: Niche weight adjustments 3 | Hook adaptations 5 | Topic clusters discovered 12

3. **Insights Timeline** (vertical, recent first):
   - Each insight card (violet accent left border):
     - Date + insight type icon
     - Title: "**Hook style 'gap question' perform 2.3x lebih baik** dari avg"
     - Mini chart support claim (bar comparison)
     - Adaptation: "✨ Mesin akan prioritaskan 'gap question' di 60% video baru (sebelumnya 25%)"
     - Confidence: "Based on 23 videos data, p=0.97"
     - Actions row: ✅ Accept (default) | ❌ Reject (dropdown reason) | 💬 Comment | ⏰ Snooze 7 days
     - Status badge: **Auto-applied** / Pending review / Rejected (user)

4. **Insight Categories Filter:**
   - All | Niche Performance | Hook Patterns | Topic Clusters | Publish Time | Music Mood | Voice Style

5. **History of Adaptations** (audit log table):
   - Columns: Date | Insight | Adaptation Applied | Status | Performance Impact (after 14d)
   - Sortable, filterable

6. **Manual Override Panel:**
   - "Manually adjust learnings" — power users
   - Override niche weight slider
   - Hook preference manual ranking
   - "Reset all learning" destructive button (dengan confirmation)

7. **Education Panel:**
   - "📚 Bagaimana Self-Learning bekerja?"
   - FAQ: "Apakah mesin belajar antar-channel?" (TIDAK — per-channel isolation)

**Empty state (grade=insufficient_data, < 5 videos):**
- 🌱 Illustration
- "Mesin sedang mengumpulkan data. Insights pertama muncul setelah ~5 video published."
- Progress: "3/5 video"

---

## 5. Konsistensi Critical untuk Semua Screen Baru

Pakai elemen design system yang Anda sudah establish di Batch 1:

- ✅ Sidebar nav style + collapsible
- ✅ Card surface (zinc-900) dengan border (zinc-800)
- ✅ Indigo-500 untuk primary CTA + active state
- ✅ Violet-500 untuk **AI feature treatment** (D20 hero gauge, D21 hero card, AI Recommendation cards di D16)
- ✅ Status badges (Pending/Running/Completed/Failed) dengan color+icon+label
- ✅ Skeleton loader pattern saat data fetch
- ✅ Empty state pattern (illustration + headline + CTA)
- ✅ Dark mode default + working light toggle
- ✅ ID default + working EN toggle
- ✅ Desktop 1440px + Mobile 375px untuk SEMUA new screens

**Special visual treatment untuk AI features:**
- D20 hero gauge: prominent dengan glow indigo
- D21 hero card: subtle violet gradient background (#8B5CF6 dengan 15% opacity)
- D21 insight cards: violet left border (4px)
- D16 AI Recommendation card: violet outline + sparkle icon

**Indonesian content examples** — pakai data konkret:
- Channel name: "Misteri Samudra"
- Niche names: Misteri Alam Semesta, Sejarah Kelam, Misteri Samudra, Fakta Menarik
- Sample insight: "Hook 'gap question' perform 2.3x", "Niche 'dark_history' over-produced"
- Sample topic: "Suara aneh di kedalaman Mariana Trench", "Kapal Hilang di Segitiga Bermuda"
- Dates: "10 Juni 2026, 14:00 WIB", "2 jam lalu", "Senin 07:00 WIB"
- Pricing reference: Rp 299K untuk custom niche, Rp 199K voice pack

---

## 6. Roadmap Updated

Berikut sequence batch yang saya rekomendasikan:

| Batch | Scope | Status |
|---|---|---|
| **Batch 1** | Design System + D1 + D5 + D2 + D3 + D4 | ✅ DONE |
| **Batch 2** | C1-C5 Onboarding + B1-B4 Auth (9 screen) | ⏭️ NEXT |
| **Batch 3** | A1 Landing + A2 Pricing + A3 Demo (3 screen) | ⏸️ |
| **Batch 4** | D6 Analytics + D7 Schedule (2 screen) | ⏸️ |
| **Batch 5** | D8-D12 + **D15-D19** Config tabs (10 screen) | ⏸️ Use updated specs di addendum ini |
| **Batch 6** | **D20 Compliance + D21 Self-Learning Insights** (2 screen) | ⏸️ **Critical priority** |
| **Batch 7** | D13 Billing + D14 Settings (2 screen) | ⏸️ |
| **Batch 8** | A4-A8 Marketing rest (5 screen) | ⏸️ |
| **Batch 9** | E1-E4 Admin Internal + Music Library Management (4 screen) | ⏸️ |
| **Batch 10** | F1-F6 States patterns (6 patterns) | ⏸️ |

**Total: 38 screens + 6 state patterns** = production-ready design system untuk dev implementation.

---

## 7. Tidak Perlu Re-do Apapun dari Batch 1

Batch 1 output (D1, D2, D3, D4, D5 + Design System) sudah baik. **Mohon tetap konsisten dengan style yang sudah established di sana**:
- Component library yang sama
- Layout shell yang sama
- Typography (Geist Sans) konsisten
- Color palette identik
- Indonesian content level yang sama

---

**END OF ADDENDUM.**

> Lanjut sesuai roadmap. Batch 2 (Onboarding + Auth) tidak terdampak oleh addendum ini — silakan jalankan dulu. Addendum ini hanya relevan untuk Batch 5+ dan Batch 6.
