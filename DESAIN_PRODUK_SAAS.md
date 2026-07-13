# Desain Produk MesinViral.com — SaaS Multi-Tenancy

> **Tujuan dokumen:** menyamakan gambaran akhir produk antara user (Owner/Product) dan AI assistant (Dev) sebelum coding dimulai.
> **Status:** 🟢 v2.0 — DIVALIDASI dengan market research (Juni 2026)
> **Dibuat:** 2026-06-10 | **Update:** 2026-06-10 (market validation)
> **Format:** rekomendasi → alasan → data pendukung → pertanyaan terbuka (❓)

---

## 📊 EXECUTIVE SUMMARY — Hasil Market Validation

### Posisi MesinViral di Market 2026

**Market gap CONFIRMED:**
- ❌ **Tidak ada kompetitor BYOK** (AutoShorts, OpusClip, Klap, Submagic, Pictory semua locked-in markup)
- ❌ **Tidak ada self-learning real** dari YouTube Analytics post-publish (yang ada hanya pre-publish "virality prediction")
- ❌ **Tidak ada Indonesian-native player** dengan full auto-pilot capability
- ✅ **Volume ceiling kompetitor: 2 video/hari** (AutoShorts Hardcore). MesinViral target 5-24/hari = **3-12x lebih agresif**

**Market opportunity:**
- 📈 Asia-Pacific AI video market 2026: $540M → $6.48B (2034) — **CAGR 46%, tertinggi di dunia**
- 🎯 YouTube Shorts: 200B daily views, 2B MAU, 6.5M active creators globally
- 💰 Indonesia content creator income avg Rp 3.5-5.5jt/bln → sweet spot tool Rp 99-299K/bln

**Tiga Wedge Diferensiasi:**

```
  BYOK Transparency      Self-Learning Loop      Indonesia-First
  ─────────────────      ──────────────────      ───────────────
  • Tidak ada vendor      • Belajar dari real     • UI Bahasa ID
    lock-in              YT Analytics post-      • Midtrans native
  • Tenant kontrol         publish               • Niche curated
    biaya AI sendiri     • Adaptasi niche &       untuk audiens ID
  • 7.5x lebih murah       hook per channel      • Concierge setup
    per-video vs          • Moat 12-18 bulan      • Kompetitor lokal
    kompetitor                                     tidak ada
```

### 🚨 Risiko #1 yang HARUS Diselesaikan

**YouTube AI Slop Crackdown (Januari 2026):** YouTube CEO Neal Mohan explicit prioritize takedown AI slop. 16 channel dengan 35M subs total di-demonetize bulan ini. Mass-produced templated content tanpa human perspective = penalty.

**MesinViral 5-24 video/hari per channel otomatis = high-risk profile**. Tanpa mitigation, customer akan banned massal → mass churn → product death.

**Mitigation = Pillar Produk #1** (bukan opsional — survival). Detail di Section 9.

---

## 1. VISI & POSITIONING PRODUK

### Tagline
> **"Mesin produksi konten YouTube otomatis yang belajar dari channelmu sendiri."**

(Bukan "makin pintar setiap hari" yang generik — yang spesifik adalah belajar dari analytics tenant, yang **tidak ada kompetitor lain lakukan**.)

### Positioning Statement
**Untuk** content creator YouTube yang mau scale ke 5+ video/hari,
**MesinViral.com adalah** platform AI auto-production pertama yang
**memberikan** video viral-grade harian + adaptasi real-time dari analytics channel Anda,
**tidak seperti** AutoShorts/OpusClip/Pictory yang generic & locked-in API,
**produk ini** transparan biaya (BYOK), belajar dari data Anda, dan compliance-first.

### Prinsip Non-Negotiable
1. **Kualitas konten = segalanya** — lebih baik tidak produksi daripada produksi jelek
2. **No silent degradation** — kalau gagal, tenant tahu via Telegram + dashboard
3. **Diversity by design** — voice/niche/hook variation per tenant untuk YouTube compliance
4. **Self-learning** — feedback loop dari real channel analytics *(mekanika final 2026-07-11: metrik per-VIDEO snapshot-terbaru + sejarah penuh; agregat lintas-channel TERTIMBANG VOLUME — insight per-channel di tab channel, tot/avg di menu utama & dashboard; detail = memory self-learning + migr 0148)*
5. **Almost fully config-driven** — tenant override default
6. **Transparency** — BYOK + visible AI cost + auditable pipeline log

---

## 2. TARGET TENANT (Ideal Customer Profile)

### Persona Primer — "Faceless Channel Scaler" ⭐ FOKUS UTAMA
- 1-3 channel YouTube Shorts, niche faceless: history, mystery, facts, science, true-crime
- Sudah punya 1-10K subscribers, butuh scale konten dari 1-2/minggu → 5+/hari
- Tech-comfortable, BUKAN developer (bisa setup API key dengan tutorial)
- Income Rp 3.5-7jt/bln (dari salary atau channel current)
- **Pain:** bikin 1 video butuh 4-8 jam riset + script + voiceover + edit
- **Triggered by:** YouTube Shorts revenue share naik ke 18% (dari 4% di 2024) → urgensi scale

### Persona Sekunder — "Agency / Network"
- Manage 5-20 channel untuk klien
- Concern: scalability, cost control, white-label
- **Pain:** tim manual editor mahal (Rp 10-30jt/bulan), kualitas tidak konsisten

### Persona Tersier (deprioritized v1) — "Affiliate Marketer"
- Channel untuk affiliate sale (skincare, supplement, finance)
- Butuh konten persuasif + CTA jelas
- Skip dulu — fokus faceless edukatif yang Compliance lebih aman

### Bukan Target (Skip Eksplisit)
- ❌ Channel face-cam / vlog (butuh real person)
- ❌ News/breaking (butuh kecepatan & verifikasi sumber kredibel)
- ❌ Long-form deep-dive >15 menit (butuh editorial khusus)
- ❌ Channel tanpa monetization goals (hobi murni)
- ❌ Tenant tidak mau BYOK (mereka bukan ICP — pakai AutoShorts)

❓ **Q1 [TENTATIVE: setuju]:** Fokus persona primer "Faceless Channel Scaler" sebagai launch target. Confirm?

---

## 3. CUSTOMER JOURNEY

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. DISCOVERY                                                              │
│     Landing mesinviral.com → demo video 2 menit → testimoni → "Mulai Free"│
│                                ▼                                           │
│  2. SIGN-UP (self-serve, < 60 detik)                                       │
│     Email + password (Supabase Auth) → email verification                  │
│                                ▼                                           │
│  3. ONBOARDING WIZARD (5 step, ~10-15 menit)                               │
│     a. Pilih paket + start 7-day trial (no credit card required)          │
│     b. Connect channel YouTube (OAuth — wajib tenant's GCP project)       │
│     c. Input API keys (Anthropic + OpenAI + ElevenLabs) — auto-validate   │
│        ↳ Tutorial video 5 menit per service dengan screen recording       │
│        ↳ Skip option: "Lakukan nanti" (terbatas trial paid AI)            │
│     d. Pilih niche utama + voice style + brand color                      │
│     e. Setup publish schedule (default 3 slot/hari, optimal time)         │
│                                ▼                                           │
│  4. FIRST PRODUCTION (otomatis 1-2 jam setelah wizard, atau "Run Now")    │
│     Tenant lihat live progress di dashboard (7 step pipeline real-time)   │
│     Notif Telegram + email: "✅ Video live"                                │
│                                ▼                                           │
│  5. DAILY VALUE (otomatis, set-and-forget) — Week 1                       │
│     - Pipeline jalan sesuai jadwal                                         │
│     - Dashboard show: views/CTR/retention per video                       │
│     - Trigger upgrade: "Trial habis dalam 3 hari, upgrade untuk continue" │
│                                ▼                                           │
│  6. SELF-LEARNING KICK-IN — Week 2-4                                      │
│     - Setelah 20+ videos, mesin pull analytics → adapt niche weight       │
│     - Notif: "Hook style 'gap question' perform 2.3x lebih baik —         │
│        mesin akan prioritaskan style ini"                                  │
│     - INI MOMEN AHA: tenant rasakan self-learning real                    │
│                                ▼                                           │
│  7. EXPANSION (upsell trigger)                                            │
│     - Tenant butuh tambah channel → upgrade ke Pro/Business                  │
│     - Agency case → contact sales untuk Enterprise                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### Trial Strategy (Validated)

**7 hari free trial, no credit card required, full feature, limit 5 video total.**

> 🔄 **UPDATE 2026-06-14 (owner, SUPERSEDE detail di bawah + §5 platform-managed trial):** Trial = **BYOK** (tenant pakai key AI sendiri sejak trial — bukan platform-managed). Alasan: insentif abuse runtuh (abuser bayar AI sendiri), infra simpel (tak ada platform-key), trial = produk asli kualitas penuh, filter ICP. Trial jadi **tier `'trial'`** di `plan_limits` (caps **1 channel, 1 video/hari**, admin-editable) + **durasi 7 hari** di `app_config` (admin-editable). Lapse tanpa upgrade → status **`trial_expired`** (non-producing) = **lead marketing** (kontak + usage utk follow-up/feedback; retensi data dalam grace). Tetap **bukan free-tier permanen**. Implementasi: migr 0023/0024, `src/billing/{limits,renewal}.py`, `src/config/app_config.py`.

**Alasan:**
- 5 video cukup untuk merasakan: 1 setup result + 4 next-day publish + dashboard analytics
- No CC required = lower friction (acquisition>>conversion at low ARPU)
- Limit 5 video = control loss (max ~$2 cost per trial user)
- Conversion path: day 5 email "trial habis dalam 2 hari, kamu sudah generate X views!" → upgrade button

**Alternatif yang ditolak:**
- ❌ 14 hari unlimited — abuse risk, biaya AI bisa $20/trial user
- ❌ Credit card upfront — friction terlalu tinggi untuk Indonesia market

❓ **Q2:** Confirm 7-hari/5-video/no-CC trial?

❓ **Q3 [TENTATIVE: skip required]:** Wizard step 3 (API keys) bisa di-skip dengan tenant pakai trial credit dari platform. Setelah trial, wajib lengkapi. OK?

---

## 4. BUSINESS MODEL — PRICING VALIDATED

> 🔄 **UPDATE 2026-06-14 (owner):** tangga tier V2 = **Trial → Starter → Pro → Business** (tier tertinggi = **Business**; nama lama "Scale"/"agency" disatukan ke **Business** di FE+DB+pricing+caps). **Enterprise = ditunda ke V3** (kolom Enterprise di tabel = referensi masa depan, BUKAN self-serve V2). **Caps per-tier (channel + video/hari) = ADMIN-EDITABLE via `plan_limits` (DB), no-hardcode** — disesuaikan kondisi pasar tanpa redeploy. Trial = BYOK time-boxed (lihat §3 update).

### Struktur Paket (REVISI berdasarkan market data Juni 2026)

| | **Starter** | **Pro** | **Business** | **Enterprise** |
|---|---|---|---|---|
| **Harga IDR** | **Rp 149K** | **Rp 349K** | **Rp 699K** | Custom |
| **Harga USD** | ~$9 | ~$22 | ~$44 | – |
| **Max Channel** | 1 | 3 | 10 | Unlimited |
| **Max Video/hari/channel** | 5 | 10 | 24 | Custom |
| **Total Video/bulan (max)** | ~150 | ~900 | ~7,200 | Custom |
| **AI Providers** | BYOK wajib (post-trial) | BYOK wajib | BYOK wajib | BYOK + setup support |
| **Music Library** | Standard (~100 track) | Premium (~500 track) | Premium + upload custom | Custom curate |
| **Analytics depth** | 7 hari | 90 hari | Unlimited | Unlimited + export |
| **Self-Learning Engine** | ✅ (1 channel) | ✅ (3 channel separately) | ✅ + cross-channel insights | ✅ + custom ML |
| **Diversity Engine** | ✅ basic (5 voice, 4 niche) | ✅ extended (15 voice, custom) | ✅ unlimited | ✅ |
| **Manual Trigger ("Run Now")** | 3/bulan | 20/bulan | Unlimited | Unlimited |
| **Support** | Email (48h) | Email (24h) + chat | Priority email (12h) + WA | Slack + monthly call + SLA |
| **API access** | ❌ | ❌ | ✅ (read-only) | ✅ (full) |
| **White label** | ❌ | ❌ | ❌ | ✅ |
| **Branding tenant** | YouTube only | YT + dashboard logo | Full | Custom domain |

### Validasi Pricing vs Market

| Tool | Plan | Harga | Video/bulan | $/video |
|---|---|---|---|---|
| AutoShorts.ai | Hardcore | $69 (Rp 1.1M) | 60 | $1.15 |
| Submagic | Business+API | $69 (Rp 1.1M) | 100 | $0.69 |
| OpusClip | Pro | $29 (Rp 460K) | 300 (credits) | $0.10 |
| **MesinViral** | **Starter** | **$9 (Rp 149K)** | **150** | **$0.06** |
| **MesinViral** | **Pro** | **$22 (Rp 349K)** | **900** | **$0.024** |
| **MesinViral** | **Business** | **$44 (Rp 699K)** | **7,200** | **$0.006** |

**MesinViral Starter = 7.5× lebih murah per video** dari AutoShorts Hardcore (kompetitor terdekat).

### Affordability vs Daya Beli Indonesia

| Tier | Harga/bulan | % income avg creator (Rp 4.5jt) |
|---|---|---|
| Starter | Rp 149K | **3.3%** — sweet spot |
| Pro | Rp 349K | **7.8%** — manageable |
| Scale | Rp 699K | **15.5%** — investment level (untuk channel monetized atau agency) |

### Add-on & Upsell Potential

> ⚠️ **PRINSIP:** Semua pricing add-on (dan subscription) **TIDAK hardcode** — disimpan di tabel `pricing_config` (Supabase) dan editable via admin panel (screen E5). Nilai di bawah = default initial seed. Lihat [[feedback_no_hardcode]] memory rule.

| Add-on | Pricing Default | Karakteristik |
|---|---|---|
| 🌍 **Custom Niche — Public** | Rp 299K one-time | 90 hari exclusive → masuk public catalog. Fair use, mass market. |
| 🔒 **Custom Niche — Private** | Rp 1.499K one-time | Permanent exclusive, never public. Premium positioning untuk agency. |
| 🎤 **Voice Pack Premium** | Rp 99K | ElevenLabs voice exclusive license |
| 🛠️ **Concierge Setup** | Rp 399K one-time | Tim kami setup semua API keys + GCP project untuk tenant |
| ⚡ **Priority Queue** | Rp 99K/bulan | Video tenant ini dijadwalkan duluan saat congestion |
| 📊 **Channel Audit** | Rp 499K one-time | Analisis channel existing + custom niche recommendation |

**Niche custom logic detail (lihat juga [[decisions_niche_model]]):**
- Public-after-90d: tenant requester exclusive 90 hari, lalu otomatis masuk public catalog (semua tenant akses)
- Permanent Private: never public, kunci permanent untuk requester
- Plus monthly release cycle: admin curate 1-2 niche baru tiap bulan ke public catalog (free akses semua tenant) — marketing engine retention

### Free Tier? — **NO**, hanya trial 7 hari

**Alasan tolak free tier:**
- BYOK requirement = tenant non-serious tidak akan setup → trial user infinitif tanpa convert
- Biaya AI di trial sudah cukup acquisition cost
- Kompetitor banyak yang free tier dengan watermark → kita differentiate dengan quality, bukan price

### Payment Strategy

**Primary: Midtrans** (Indonesia-native) — ✅ **akun owner SUDAH tersedia** (2026-06-11), jadi provider final (menggantikan rencana Xendit/Stripe).
- ✅ Recurring/Subscription API (auto-renew)
- ✅ E-wallet (GoPay, ShopeePay, dll) + QRIS
- ✅ Kartu kredit (Visa/Mastercard/JCB)
- ✅ Virtual Account (semua bank)
- ✅ Direct debit / paylater (Akulaku, Kredivo)
- ✅ Webhook notification untuk auto-suspend

**Secondary (opsional, nanti):** Stripe untuk export market (USD international) — belum prioritas.

### Billing Mechanics

> 🔄 **UPDATE 2026-07-13 (realita implementasi, ratifikasi owner — finalisasi_tier_plan Tahap 5.2):**
> **Perpanjangan = BAYAR MANUAL per periode (BUKAN auto-debit)**, via link Snap + email pengingat
> (H-3 sebelum habis). Alasan: metode utama pasar ID (GoPay/VA/QRIS) tidak mendukung recurring
> charge; kartu kredit bisa recurring tapi minoritas → recurring API TIDAK dipakai (dihindari
> kompleksitas + gagal-debit senyap). Masa tenggang (`billing_grace_days`, default 7h) menjaga mesin
> tetap jalan sambil menunggu bayar. **Prorate/tahunan/diskon = SUDAH nyata di mesin** (rumus
> nilai-adil `compute_new_period` + `compute_checkout_amount`, lihat PAYMENT doc §3.4). Refund =
> proses MANUAL via dashboard Midtrans (bukan self-service). Butir di bawah = rencana awal (sebagian
> di-supersede baris ini).

- **Cycle:** ~~monthly auto-renew~~ → **bulanan/tahunan, bayar MANUAL tiap periode** (jangkar tanggal
  dipertahankan via prorate nilai-adil saat perpanjang paket sama)
- **Failed payment:** tak ada auto-retry debit; tenant bayar ulang via link kapan saja dalam grace →
  lewat grace → suspend (siklus lifecycle di PAYMENT/LIFECYCLE doc)
- **Suspend:** scheduler stop, dashboard read-only, data + history tetap aman
- **Grace period:** 30 hari setelah suspend baru data dihapus (vs original 14 — kasih ruang re-engage)
- **Refund:** ~~prorate otomatis~~ → **manual via Midtrans** (hubungi tim ≤7 hari pembayaran pertama)
- **Annual prepay discount:** ✅ **LIVE** — knob `annual_discount_pct` (default 20%), admin-editable

❓ **Q4 [TENTATIVE: setuju]:** Confirm 3 paket Rp 149/349/699 + Enterprise custom?

❓ **Q5 [TENTATIVE: setuju]:** Annual prepay 20% off?

---

## 5. BYOK STRATEGY — Curated Catalog (Validated)

### Decision: **Strict BYOK + Curated Catalog**

**Curated Catalog artinya:**

```
Engine "Script LLM" (locked di 2 family)
├─ Anthropic Claude
│  ├─ claude-sonnet-4-6 (default — quality tinggi)
│  └─ claude-haiku-4-5 (cepat & murah)
└─ OpenAI GPT
   ├─ gpt-4o (default OpenAI — quality tinggi)
   └─ gpt-4o-mini (cepat & murah)

Engine "TTS" (locked di 2 provider)
├─ ElevenLabs (premium — multilingual v2 / flash / turbo)
└─ Edge TTS (gratis fallback)

Engine "Visual AI" (locked di OpenAI image)
├─ gpt-image-1-mini (default — cheap & good)
├─ gpt-image-1 (premium quality)
└─ dall-e-3 (high-quality legacy; ⚠️ deadline discontinue ~May 2026 SUDAH LEWAT per 2026-06-12 — status perlu dikonfirmasi, lihat open-decision)

Engine "Music" (platform-managed, BUKAN BYOK)
└─ Library R2 curated
```

**Mengapa Curated bukan Free Pick:**
1. **Quality control** — kita test setiap model, pastikan output viral-grade
2. **Prompt engineering** — prompt kita di-tune per model
3. **Cost predictability** — tenant tahu range biaya
4. **Support burden** — kita hanya support model yang kita test
5. **AI Slop compliance** — kita curate untuk hasil quality, bukan flooding

**Tenant choice flexibility:**
- Personal/Starter: default only (kita pilih optimal)
- Pro+: bisa pilih dari catalog per engine
- Enterprise: bisa request model baru ditambahkan (review process)

### Mandatory Keys per Paket

| Engine | Trial (7 hari) | Starter+ |
|---|---|---|
| **Script LLM** | Platform-managed (Haiku only) | BYOK Anthropic ATAU OpenAI |
| **TTS** | Platform-managed (Edge TTS) | BYOK ElevenLabs (Edge TTS fallback OK) |
| **Visual AI** | Platform-managed (gpt-image-1-mini, limited) | BYOK OpenAI |
| **YouTube** | Wajib BYO (Google OAuth + GCP project) | Wajib BYO |
| **Music** | Platform (R2) | Platform (R2) |

❓ **Q6 [TENTATIVE: setuju]:** Curated catalog (locked engine, choose model dari list) — bukan free pick. Confirm?

---

## 6. FLEKSIBILITAS KONFIGURASI TENANT (3 Lapis)

| Lapis | Siapa | Apa yang Bisa Diatur |
|---|---|---|
| **L1 — Default Smart** | Semua tenant baseline | Sistem otomatis: niche optimal (self-learn), publish time optimal, model AI per paket |
| **L2 — Tenant Override** | Tenant aktif (semua tier) | Pilih niche, publish time, voice ElevenLabs, brand color, font caption, music mood |
| **L3 — Power User** | Pro & Scale | Custom prompt templates (limited), viral score threshold, retry logic, model AI specific, niche custom |

### Konfigurasi Tab-by-Tab di UI

| Tab | Field | Tier Restrictions |
|---|---|---|
| **Channels** | List channel YT, branding per channel, default niche | All — limit jumlah per paket |
| **AI Engines** | Per engine: pilih model dari catalog | L1 default Starter; L2+ choose Pro |
| **API Keys** | Input + "Test Connection" button | All — wajib lengkap untuk paid |
| **Voice** | Pilih voice ElevenLabs + preview audio | All |
| **Visual** | Style preset (Cinematic Dark, Vibrant, Minimalist) atau custom prefix prompt | L2 preset; L3 custom |
| **Music** | Toggle on/off, volume, mood priority per niche | All |
| **Captions** | Font, size, color, position, karaoke style | All — preset di Starter |
| **Schedule** | Slot publish WIB, days of week, content_type | All |
| **Quality Gate** | Min viral score (default 75), max retry, action on fail | L3 only (Pro & Scale) |
| **Notifications** | Telegram, email, what events | All |
| **Hashtags** | Default hashtag pool per niche | All |
| **Niches** | Pilih 1-N niche dari catalog (N = paket limit) | All — request custom = L3 |

### Yang LOCKED (untuk konsistensi quality & compliance)

- Pipeline architecture (7 step)
- Scoring viral 6 dimensi (algoritma)
- Schema script 8 section
- Auto-cleanup policy
- Diversity Engine rules (untuk AI slop defense)
- Source data trend (5 source)

❓ **Q7:** Apakah ada field tertentu yang Anda mau **buka tutup** dari rekomendasi di atas?

---

## 7. UI/UX KONSEP

### Tech Stack Frontend (Recommended)

- **Framework:** Next.js 15 (App Router) — SSR, fast, React
- **UI:** shadcn/ui + Tailwind — modern, professional, customizable
- **Auth:** Supabase Auth (sudah ready di backend)
- **Realtime:** Supabase Realtime (live log streaming)
- **Charts:** tremor.so (dashboard-friendly) atau Recharts
- **State:** TanStack Query (server state) + Zustand (UI state)
- **i18n:** next-intl (Indonesia + English)
- **Deploy:** ~~Vercel~~ → **SELF-HOST VPS** (2026-06-17, owner: hemat biaya+tanpa akun) — `mv-web` Next.js + nginx + Let's Encrypt.
- **Domain:** `mesinviral.com` (landing+dashboard+admin, **path-based**, → VPS) + `api.mesinviral.com` (webhook, → VPS). *(bukan subdomain app./admin. terpisah)*

### Information Architecture

```
mesinviral.com (Public)
  ├─ / (landing — hero + demo video + pricing + testimoni)
  ├─ /pricing
  ├─ /docs (knowledge base)
  ├─ /blog (SEO content marketing)
  ├─ /case-studies (case study channel customers)
  ├─ /login, /signup, /forgot-password

app.mesinviral.com (Tenant — auth required)
  ├─ /onboarding (5-step wizard untuk new tenant)
  ├─ /dashboard (live overview)
  ├─ /channels
  │   └─ /channels/[id] (per-channel: niches, schedule, analytics, runs)
  ├─ /runs (list semua pipeline run, filterable)
  │   └─ /runs/[id] (live timeline + log)
  ├─ /analytics (charts: views, CTR, retention, top videos)
  ├─ /config (tabbed)
  ├─ /schedule (calendar view)
  ├─ /billing (plan, invoice, usage)
  ├─ /team (multi-user — Enterprise)
  ├─ /settings (profile, security, integrations, Telegram)

admin.mesinviral.com (Internal — super-admin only; login terpisah /admin/login; bypass RLS via service_role)
  ├─ /admin/tenants (list, suspend/unsuspend, kirim email→worker, trial-leads) [E1]
  ├─ /admin/pricing (inline-edit pricing_config + plan_limits + app_config + audit/rollback) [E5]
  ├─ /admin/niches (niche + is_base + eksklusivitas/monthly-release + Test niche) [E2.3]
  ├─ /admin/catalog (AI models/providers, music, voice_catalog, languages, tts) [E2.x]
  ├─ /admin/system (queue/error real + worker_heartbeats + Direct Jobs panel) [E3]
  ├─ /admin/support (tiket: inbox/reply/resolve) [E4]
  ├─ /admin/content (CMS: kelola Blog/Docs/Demo — markdown, draft/publish)   ← konten landing/marketing
  ├─ /admin/test-lab (kredensial channel internal + "Test semua kredensial" NYATA)
  └─ /admin/account (ganti password admin)
```
> **STATUS v2 (2026-06-15): admin panel SELESAI + tervalidasi.** Super-admin = `app_metadata.role='super_admin'` (akun terpisah, BUKAN tenant). Semua data lintas-tenant via **service_role server-route ber-gate** (`/api/admin/*`), bukan anon+RLS. Detail: `PHASE10_ADMIN_WIRING.md`.

### Visual Style

- **Mood:** professional, calm, focused (bukan flashy)
- **Color:** indigo-600 primary, dark mode default (content creator audience)
- **Typography:** Geist Sans (UI — KEPUTUSAN FINAL, bukan Inter), JetBrains Mono (logs)
- **Layout:** sidebar nav + main + slide-in drawer untuk detail

(Mockup ASCII tetap sama dengan v1 — lihat backup atau implementasi.)

❓ **Q8:** Dark mode default? Bilingual ID + EN dari awal atau Indonesia dulu?

---

## 8. NILAI JUAL & DIFERENSIASI (VALIDATED)

### 5 Killer Features (Re-Ranked Berdasarkan Moat)

#### 🥇 1. Self-Learning Loop dari Real YouTube Analytics — **MOAT UTAMA**
- Mesin pull analytics tenant 24-72 jam post-publish → score CTR/retention/AVD per video
- Adapt niche weight, hook pattern, **topik** **per channel** tenant *(koreksi 2026-06-28: self-learning TIDAK mengadaptasi visual style — variasi visual = `visual_seed` DiversityEngine, bukan hasil-belajar; klaim landing diluruskan commit `61a7fd7`)*
- Pakai Claude Haiku untuk meta-learning (cheap), Sonnet untuk strategy adjustment weekly
- **Unique value:** Tidak ada kompetitor lakukan ini. Pictory/AutoShorts/OpusClip cuma punya "virality prediction" pre-publish, bukan post-publish learning loop.
- **Moat duration:** 12-18 bulan sampai kompetitor catch up

#### 🥈 2. BYO-Everything Transparency
- Tenant pegang semua API keys + GCP project
- Dashboard show breakdown cost AI per video (real-time)
- Export semua data anytime
- No vendor lock-in
- **Unique value:** 0 kompetitor BYOK. Trust signal untuk power user creator yang sudah literate AI.

#### 🥉 3. AI Slop Defense / Compliance Engine
- Voice rotation pool, niche diversity, hook variation otomatis
- AI Disclosure tag automation (YouTube self-identification)
- Optional human review queue (Pro+)
- **Unique value:** Setelah Jan 2026 crackdown, ini SURVIVAL untuk customer mereka. Kompetitor mass-produce tanpa diversity = banned.

#### 4. Volume Ceiling 3-12× Kompetitor
- 5-24 video/hari per channel vs kompetitor ceiling 2/hari
- Plus multi-channel parallel
- **Value:** Untuk scaling creator/agency, ini fundamental

#### 5. Indonesia-First
- UI Bahasa Indonesia + EN
- Midtrans native payment
- Niche library curated untuk audiens ASEAN
- Support Bahasa Indonesia
- Indonesia content creator income-friendly pricing
- **Value:** Tidak ada kompetitor lokal. Differensiasi pasti.

### Tabel Komparasi Verified (Juni 2026)

| Fitur | MesinViral | AutoShorts | OpusClip | Submagic | Pictory |
|---|---|---|---|---|---|
| Auto-publish YT 24/7 | ✅ | ✅ | ⚠️ scheduler | ⚠️ scheduler | ❌ |
| **Self-learning per channel analytics** | **✅ UNIQUE** | ❌ | ❌ | ❌ | ❌ |
| **BYOK** | **✅ UNIQUE** | ❌ | ❌ | ❌ | ❌ |
| **Diversity engine (AI slop compliance)** | **✅ UNIQUE** | ❌ | ❌ | ❌ | ❌ |
| Multi-channel | ✅ (1-10+) | ❌ | ⚠️ Business | ⚠️ | ⚠️ Team |
| Max video/hari | **5-24** | **2** | – | – | – |
| Custom voice (ElevenLabs) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Indonesia payment & UI** | **✅** | ❌ | ❌ | ❌ | ❌ |
| Quality gate (skip if bad) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Price ($/video Hardcore tier) | $0.024-0.06 | $1.15 | ~$0.10 | $0.69 | – |

### Landing Page Pitch (REVISI)

> "**Setiap content creator YouTube punya impian sama:** 1 channel viral, 100K subscribers, monetisasi.
>
> Tapi realita: bikin 1 video Shorts butuh 4-8 jam. Untuk scale ke 5 video/hari, butuh tim Rp 10jt/bulan.
>
> **AutoShorts.ai max 2 video/hari. OpusClip cuma potong klip dari video panjang.**
> **Tidak ada satu pun yang belajar dari channel-mu sendiri.**
>
> **MesinViral.com mengubah persamaan ini.**
>
> Mesin AI yang auto-produksi 5-24 video Shorts/hari per channel, dengan kualitas viral-grade,
> yang **belajar dari analytics channel Anda** dan **menjaga monetisasi Anda aman** dari penalty AI slop YouTube.
>
> Anda pegang API keys sendiri. Bayar AI cost langsung. **7.5× lebih murah per video** dibanding kompetitor.
>
> Mulai gratis 7 hari, 5 video, tanpa kartu kredit. →"

❓ **Q9:** Apakah pitch ini menangkap voice brand Anda?

---

## 9. ⭐ YOUTUBE AI SLOP DEFENSE STRATEGY (Pillar Produk Baru)

### Konteks Risiko

**Januari 2026: YouTube CEO Neal Mohan announce crackdown AI slop.**
- 16 channel dengan total 35M subs di-demonetize bulan ini
- 4.7B total view × $9.8M revenue removed
- Policy basis: "mass-produced templated content lacking human perspective"
- **MesinViral 5-24 video/hari otomatis = profile risk tinggi tanpa mitigation**

### MesinViral Defense Engine (Built-in dari Day 1)

#### 9.1 Diversity Layer — Otomatis per Channel

| Aspek | Mekanisme | Lapis Personalisasi |
|---|---|---|
| **Voice rotation** | Pool 5-15 voice ElevenLabs (sesuai paket), rotated per video dengan algorithmic shuffle | Per channel |
| **Niche rotation** | Anti-dominasi: max 40% slot dalam 6 produksi terakhir (sudah ada di kode) | Per channel |
| **Hook style variation** | 6 pattern hook (gap question, surprise stat, contrarian claim, story bait, time pressure, identity hook) — round-robin | Per channel |
| **Music mood rotation** | Mood priority dari niche → 3-5 mood per niche di-rotate | Per channel |
| **Visual style seed** | Style preset + random seed per video → frame fingerprint unik | Per channel |
| **Script structural variation** | 8-section schema fixed, tapi opening/closing language varied via LLM prompt seed | Per channel |

#### 9.2 Compliance Touches

- **AI Disclosure auto-tag** — YouTube "made with AI" self-identification per video metadata
- **Niche fact-check pass** (opsional, Pro+) — second LLM verify claim/numbers di script sebelum produce
- **Human Review Queue** (Pro+) — toggle ke "review before publish", 24-48 jam window
- **Copyright/trademark filter** (built-in, semua tier) — keyword block list updated otomatis

#### 9.3 Transparency Layer untuk Tenant

- **Compliance Score per channel** (dashboard widget): 0-100
  - Voice diversity %
  - Niche distribution
  - Hook style spread
  - Days since last duplicate slug
  - YouTube AI disclosure compliance status
- **Alert** kalau channel approach risk threshold (Compliance Score < 60)

#### 9.4 Onboarding Education

- Trial wizard step 4 (niche): edukasi 1 menit video "Bagaimana mesinviral menjaga channelmu aman"
- Dashboard onboarding tooltip: penjelasan Compliance Score saat first hover

#### 9.5 Insurance / SLA (Future, Enterprise)

- Enterprise tier: kalau channel kena strike YouTube karena algoritma platform (bukan content violation), kita kasih credit 1 bulan gratis + audit channel
- Bukan jaminan, tapi signal serius kita pegang compliance

❓ **Q10:** Apakah pillar AI Slop Defense ini make sense sebagai #1 product priority bareng Self-Learning? Setuju masuk ke roadmap awal?

---

## 10. ⭐ UNIT ECONOMICS & MARGIN ANALYSIS

### Cost Real per Video Shorts 60 Detik (Juni 2026)

#### Pipeline Cost Breakdown

| Engine | Calculation | Cost (USD) |
|---|---|---|
| **Claude Sonnet 4.6** (script gen, 3000 in + 2500 out tokens) | $3/M in + $15/M out | $0.0465 |
| **Claude Haiku 4.5** (4 utility calls — niche/hook/scoring/rewrite, 1500 in + 800 out each) | $1/M in + $5/M out × 4 | $0.022 |
| **ElevenLabs Multilingual v2** (~825 chars script) | $0.00022/char | $0.181 |
| *Alternative: ElevenLabs Flash* | $0.00011/char | $0.091 |
| **gpt-image-1-mini medium** (6 images per video) | $0.015/image × 6 | $0.090 |
| *Alternative: gpt-image-1-mini low* | $0.005/image × 6 | $0.030 |
| **YouTube API + Pexels + R2** | quota free + storage | $0.001 |
| **Total Premium** | – | **$0.34** |
| **Total Cost-Optimized** | – | **$0.19** |

**Konversi IDR (kurs Rp 16K/USD):** Rp 3.040 – Rp 5.440 per video.

#### Volume Cost Implication (per tenant per bulan)

| Tier | Video/bulan max | AI cost premium | AI cost optimized |
|---|---|---|---|
| Starter | 150 | $51 (Rp 816K) | $28 (Rp 448K) |
| Pro | 900 | $306 (Rp 4.9M) | $171 (Rp 2.7M) |
| Scale | 7,200 | $2,448 (Rp 39M) | $1,368 (Rp 22M) |

**KRITIS:** Karena BYOK, **tenant yang bayar langsung ke Anthropic/OpenAI/ElevenLabs**. MesinViral hanya jual orchestration layer.

### MesinViral Infra Cost per Tenant per Bulan

| Komponen | Cost (USD) |
|---|---|
| Compute (worker render — **~7-21 mnt/video**, lihat §12c; $/video tetap kecil krn compute murah/menit) | ~$0.02/video × 150-7200 = $3-144 |
| Supabase DB (rows + storage) | $0.5-3 |
| Cloudflare R2 (music streaming + storage) | $0.2-1 |
| Egress (video file passing through) | $0.1-2 |
| Telegram + email | $0.1 |
| **Total per tenant Starter** | **~$4** |
| **Total per tenant Pro** | **~$10** |
| **Total per tenant Scale** | **~$25** |

### Margin Analysis

| Tier | Revenue (USD) | Infra Cost | Gross Margin | Margin % |
|---|---|---|---|---|
| Starter ($9) | $9 | $4 | $5 | **55%** |
| Pro ($22) | $22 | $10 | $12 | **54%** |
| Scale ($44) | $44 | $25 | $19 | **43%** |

Note: Scale margin lebih rendah karena volume render hit compute lebih keras. Mitigation: optimasi FFmpeg + GPU acceleration (Phase 7+).

### Break-Even Math

**Fixed cost MesinViral (asumsi solo dev, post-launch):**
- VPS + Supabase + R2 + domain + monitoring: **~$80/bulan**
- Payment gateway fee (~2-3% Midtrans): variable, ~5% of revenue blended

**Break-even tenant count:** 
- 80 / (avg margin $8 dari blended tier) = **~10 tenant Starter** atau 7 Pro

**Aggressive growth target Year 1:**
- 100 tenant blended → $2,000-3,000 MRR → $24-36K ARR
- Bisa di-reach jika launch beta 4 bulan + content marketing 3 bulan

❓ **Q11:** Margin 43-55% acceptable? Atau target higher (e.g., raise Scale ke Rp 999K untuk 50%+)?

---

## 11. ⭐ RED FLAGS & RISK REGISTER

### 🚨 Risk #1 (CRITICAL): YouTube AI Slop Policy
**Likelihood:** Sangat tinggi (sudah aktif Jan 2026)
**Impact:** Customer channel banned/demonetized → mass churn → death
**Mitigation:** Section 9 Defense Engine (built-in dari day 1, BUKAN opsional)
**Owner:** Product (architecture choice)

### 🚨 Risk #2 (HIGH): BYOK Onboarding Friction
**Likelihood:** Tinggi (40-50% trial signup mungkin abandoned)
**Impact:** Acquisition cost naik 2x untuk hit conversion target
**Mitigation:**
- Wizard step-by-step dengan tutorial video 3-5 menit per API
- "Skip & lakukan nanti" opsi (trial pakai platform-managed)
- Concierge Setup add-on (Rp 399K) — kita setup keys + GCP untuk tenant
- Email follow-up day 1 day 3 untuk yang abandoned wizard
**Owner:** UX (wizard design)

### 🚨 Risk #3 (HIGH): YouTube OAuth Quota Limit
**Likelihood:** Tinggi untuk Scale tier
**Impact:** Tenant Scale hit upload limit → service degraded
**Mitigation:**
- Wizard step 2 (OAuth): tenant wajib BYO GCP project
- Tutorial untuk request quota increase ke Google (1-2 minggu lead)
- Pre-flight check: dashboard show daily quota remaining
- Auto throttle saat near limit
**Owner:** Engineering (quota monitoring)

### 🟠 Risk #4 (MEDIUM): RPM Shorts Rendah
**Data:** $0.01-0.07/1K views; tenant butuh 1M+ views/bulan untuk make money
**Impact:** Tenant tidak puas dengan ROI → churn cepat (3-6 bulan)
**Mitigation:**
- Self-learning engine wajib deliver views uplift visible dalam 30 hari
- Onboarding edukasi: realistic expectation setting
- Case study channel customer dengan view trajectory
- Niche selection guidance: niche dengan RPM tinggi (finance, business) di-promote
**Owner:** Product + Marketing

### 🟠 Risk #5 (MEDIUM): ElevenLabs ToS — Creator Plan B2B Restriction
**Data:** ElevenLabs Creator ($22) tidak boleh untuk redistribusi commercial B2B
**Impact:** Kalau MesinViral pakai 1 account ElevenLabs untuk all tenants → violation
**Mitigation:**
- **BYOK fundamental: tenant pakai akun ElevenLabs sendiri** — no platform sharing
- Trial period pakai Edge TTS (free, no ToS issue)
**Owner:** Legal review

### 🟠 Risk #6 (MEDIUM): Anthropic/OpenAI API Cost Volatility
**Data:** Model pricing bisa berubah (mis. DALL-E discontinue ~May 2026 — deadline sudah lewat, konfirmasi status)
**Impact:** Catalog model harus update, communication ke tenant
**Mitigation:**
- Catalog di Supabase (Phase 1.3) — flag deprecated models
- Auto-migration prompt ke tenant 30 hari sebelum deprecation
- Notif email kalau model pilihan tenant akan deprecated
**Owner:** Engineering (catalog management)

### 🟡 Risk #7 (LOW): Kompetitor Catch-up
**Data:** OpusClip 16M creators, AutoShorts sudah punya nama
**Impact:** Slow adoption MesinViral
**Mitigation:**
- Moat lewat self-learning (12-18 bulan technical advantage)
- Indonesia-first defensible (legal/payment lokalisasi sulit di-copy fast)
- Content marketing fokus value prop unik

### 🟡 Risk #8 (LOW): Indonesian Recession / Daya Beli Volatile
**Mitigation:**
- Pricing tier Starter Rp 149K = manageable
- Annual prepay discount untuk lock cash flow
- Add export market gradually (USD pricing)

❓ **Q12:** Risk register comprehensive? Ada risk lain yang Anda concerned?

---

## 12. TECH STACK IMPLICATION (Updated)

### Backend (sudah sebagian ada)
- ✅ Python pipeline (orchestrator, intelligence, providers)
- ✅ Supabase Postgres + Auth + RLS + Realtime
- ✅ Cloudflare R2 (music + fonts)
- ✅ Worker + Dispatcher (perlu fix timezone bug — Phase 1.6)
- ⏳ Tenant Credentials (Fernet) — **Phase 4**
- ⏳ Multi-channel propagation — **Phase 5**
- ⏳ **Konten Multi-Bahasa (per-channel)** — `content_language` di channel + catalog `content_languages` config-driven (id-ID/en-US official, SEA experimental); inject bahasa ke script LLM + voice filter + caption font. Backend nyangkut **Phase 1.x (prompt) + Phase 5 (channel field)**. Selling point landing page. Lihat memory `decisions_content_language`.
- ⏳ **Self-Learning Feedback Engine** — **Phase 6 (NEW PRIORITY)** — pull YT Analytics 24-72h post-publish, adapt config
- ⏳ **Diversity Engine** — **Phase 6 (NEW PRIORITY)** — voice/hook/niche rotation algorithm
- ⏳ **Compliance Score calculator** — **Phase 7**
- ❌ Payment integration (**Midtrans** webhook handler — akun owner sudah ada) — **Phase 8**
- ❌ Email service (Resend) — **Phase 8**
- ❌ Onboarding wizard backend (state machine) — **Phase 9**

### Frontend (belum ada sama sekali)
- ❌ Next.js app (landing + dashboard + admin) — **Phase 9-10**
- ❌ Onboarding wizard UI
- ❌ Dashboard with live tail
- ❌ Config tabbed pages
- ❌ Analytics charts
- ❌ Billing portal

### Infrastructure
- ✅ VPS Ubuntu (worker `mv-worker` + frontend `mv-web` + nginx) — 2026-06-16/17
- ✅ Supabase project (v2)
- ✅ ~~Vercel project~~ → **N/A: frontend SELF-HOST di VPS** (2026-06-17, tanpa Vercel)
- ✅ Domain + SSL: **`https://mesinviral.com` LIVE** (Let's Encrypt di VPS, auto-renew) · `api.` (webhook) belum
- ❌ Monitoring (Sentry + BetterStack)
- ❌ CDN (Cloudflare untuk landing)

### Updated Phase Roadmap

> **Status LIVE per-phase = `PROGRESS.md` (master status).** Tabel di bawah = roadmap KONSEP; jangan catat status di sini (hindari drift 3-tempat).

| Phase | Scope | Estimasi Solo Dev | Catatan |
|---|---|---|---|
| **0** | Audit ✅ DONE | – | – |
| **1** | SOFTCODE AI Config (6 sub) | 4-6 jam | Backend foundation |
| **2** | Error Mgmt Terpusat | 2 jam | – |
| **3** | Pipeline Run Logs DB | 2 jam | UI-ready logging |
| **4** | BYO-CC Phase 1 (auth + credentials) | 1 minggu | – |
| **5** | Multi-Channel | 1 minggu | – |
| **6** | **NEW: Self-Learning Feedback Engine + Diversity Engine** | **2 minggu** | **CORE MOAT** |
| **7** | **NEW: Compliance Score + AI Slop Defense polish** | 1 minggu | **SURVIVAL** |
| **8** | Payment integration (**Midtrans** — akun ready) + tier-gating | 2 minggu | – |
| **9** | UI Foundation (Next.js + landing + dashboard) | 4-6 minggu | – |
| **10** | UI Polish (onboarding wizard + admin) | 2-3 minggu | – |
| **11** | Beta launch + 10 hand-picked tenants | 1 bulan | Feedback iteration |
| **12** | Public launch | – | Marketing kick-off |

**Total to MVP launch:** ~5-6 bulan full-time. Bisa beta launch **bulan 4**.

---

## 12b. EPIC — Multi-Format Short Studio (perluasan kategori creator)

> **Konsep induk di sini; spec teknis + validasi lengkap di `MULTI_FORMAT_STUDIO.md`; status di `PROGRESS.md`. Sudah divalidasi terhadap kode + API (2026-06-11) — jangan analisa ulang.**

**Positioning:** dari "tool creator viral faceless" → **studio short-video faceless multi-format** yang menampung **sebanyak mungkin kategori creator**: mystery/facts (existing), **edukasi soft-sell** (brand promosi halus), **motivational/quote**, **educator**. Memperluas TAM ke segmen **brand/advertiser** bernilai tinggi sambil menjaga filosofi **anti-hard-sell** (soft-sell terkontrol).

**Pilar fitur (ringkas):**
- **Duration presets** 8/15/30/45/60/75/90s + **Format profiles** (section = fungsi Format×Durasi); WPS per-format; QC window relatif.
- **Render mode** `image_sequence` (existing) + **`ai_video`** (text-to-video, **BYOK**, untuk 8s motivasi) — tetap masuk karena provider sudah support (Kling/Runway/Luma/Veo/Sora).
- **Branded Content:** logo overlay di video + soft-sell CTA ("hidup sehat bersama [brand]") + link landing di deskripsi (atas/bawah). *(Auto-pin komentar YouTube = mustahil via API → pakai link deskripsi.)*
- **Multi-platform tier-gated:** Starter=YouTube · Pro=+Reels · Scale=+TikTok (ke-3). **Catatan onboarding:** Reels butuh akun Business+Page+App Review (2–4 mgg); TikTok butuh audit (2–4 mgg) untuk post publik.
- **Katalog AI extensible (BYOK granular):** tenant pilih model (quality/cost), developer bisa tambah model (config) / provider (adapter) kapan saja.

**Feasibility (tervalidasi):** cheap wins (logo, QC relatif, link, soft-sell, durasi 30–75s) → **Phase 1.x**; ai_video + multi-platform → fase berat tersendiri (nyambung BYO-CC Phase 4 + tier Phase 8 Midtrans). Detail per item + bukti file:line di `MULTI_FORMAT_STUDIO.md §0`.

---

## 12c. PONDASI — Arsitektur Produksi: Decoupling (Producer / Buffer / Publisher)

> **Pondasi kritikal.** Angka & keputusan tervalidasi dari VPS nyata di memory `decisions_production_scaling`. **Jangan benchmark/analisa ulang.**

### Masalah (kenapa wajib)
Pipeline lama: **produksi + publish dalam satu tarikan, DI WAKTU SLOT**. Produksi 1 video = **35 menit terukur** (render ~21 mnt dominan). Kalau banyak tenant berbagi slot publish (mis. 14:00), semua produksi berat meledak bersamaan → **server down** (terbukti live: VPS 2-core/swap-0 OOM-mati di bawah render konkuren).

### Solusi: pisah 2 mesin + buffer (analogi pabrik-gudang)
- **PRODUCER** (pabrik) — jalan KONTINU 24/7, di-smooth. Tugas: jaga setiap channel punya **stok video siap-tayang** di buffer. Dibatasi **concurrency = jumlah core** (tak pernah overload).
- **BUFFER** (gudang) — aset video di **Biznet Gio S3** (co-located, ~50MB/file) + status di tabel **`content_inventory`** (source of truth).
- **PUBLISHER** (pengirim) — jalan saat slot tiba. Tugas: ambil 1 video ready dari buffer → publish (RINGAN, ~5 dtk I/O). "Jadwal" tenant = jadwal **publish**, bukan produksi.

### Pseudo-code (acuan, agar tidak salah paham)

```
# ===== PRODUCER (mesin produksi) — loop terus 24/7 =====
# Jaga stok buffer tiap channel. Tidak terikat jam slot.
loop selamanya:
    for channel in urutkan_prioritas(channel_aktif):       # buffer paling tipis / slot terdekat dulu
        target = channel.buffer_depth                       # config per-niche: tren=1, evergreen=3-5
        # ⭐ UPDATE 2026-07-09 (LIVE, `producer.target_stock`): buffer_depth NULL → target SADAR-JADWAL
        #    = slot/hari × `app_config.buffer_target_days` (clamp TTL); tanpa slot → 0.
        #    Dasar owner: anti stok basi kena TTL 72j + anti kuota-harian model gratis terbakar eager-fill.
        stok   = hitung_status_ready(channel)               # dari content_inventory
        if stok < target:
            if render_berjalan() < MAX_CONCURRENT_RENDER:   # = jumlah core (anti-overload!)
                produksi_satu_video(channel)                # ~13 mnt (pasca-optimasi)
        # stok cukup -> skip (jangan over-produksi, jaga freshness)
    tunggu(30 detik)

fungsi produksi_satu_video(channel):
    catat_inventory(channel, status="producing")
    video, meta = jalankan_pipeline_AI(channel)             # script->TTS->image->RENDER
    s3_key = upload_biznet_S3(video)                        # aset berat ke object storage
    update_inventory(channel, s3_key, meta, status="ready",
                     expires_at = now + masa_segar)          # freshness guard

# ===== PUBLISHER (mesin submit) — dispatcher tiap menit =====
loop tiap menit:
    for slot in slot_jatuh_tempo(now, timezone_tenant):    # hormati timezone tenant
        video = ambil_ready_tertua(slot.channel)           # dari content_inventory
        if video kosong:
            telegram(slot.channel, "⚠️ Buffer kosong, slot dilewati")   # no silent degradation
            naikkan_prioritas_produksi(slot.channel)
            continue
        update_inventory(video, status="publishing")
        hasil = publish(video, slot.channel.platforms)     # YouTube/Reels/TikTok ~5 dtk
        if hasil.sukses:
            update_inventory(video, status="published")
            hapus_S3(video.s3_key)                          # buang file berat, simpan record
            telegram(slot.channel, "✅ Published " + hasil.url)
        else:
            update_inventory(video, status="ready")        # kembalikan ke buffer
            retry_backoff(video); telegram(slot.channel, "❌ Gagal, akan diulang")
```

### Kenapa ini mencegah down
- Produksi **dibatasi `MAX_CONCURRENT_RENDER` = jumlah core** + tersebar sepanjang hari → CPU tak pernah lewat kapasitas.
- Publish di slot cuma **upload** (no CPU) → 50 channel berbagi 14:00 = 50 upload ringan, BUKAN 50 render.

### Scaling (orkestrator multi-node)
`MAX_CONCURRENT_RENDER` itu **per-node**. Saat tenant tumbuh, **orkestrator** sebar `produksi_satu_video` ke **beberapa node** (concurrency/node = core/node). Lebih banyak proses di core yang sama TIDAK menambah throughput (CPU-bound, terbukti).

### Trigger & interval loop (KEPUTUSAN — bukan cron, 2026-06-12)
**Producer di-trigger oleh SCRIPT LOOPING persisten, BUKAN cron.** Alasan: rem concurrency (`MAX_RENDER = jumlah core`) **wajib dipegang satu proses yang hidup terus**; cron men-spawn proses **buta** (tak tahu berapa render jalan) → tak ada rem → **OOM/down** (terbukti live). Konsisten dgn worker sekarang yang **sudah loop** (sudah ganti crontab, commit `ff139ba`). **Antrian & state tetap di Supabase** (`production_queue`, `content_inventory`); koordinasi multi-node via `SELECT … FOR UPDATE SKIP LOCKED` (anti rebut/dobel). Prinsip: **Supabase = papan antrian/otak koordinasi; loop persisten = tangan yang bekerja & pegang rem.**

| Komponen | Trigger | Interval loop (default, **config-driven/tunable**) | Dasar (terukur, bukan asumsi) |
|---|---|---|---|
| **Planner** (cek defisit buffer → enqueue) | loop / Supabase pg_cron | **60 detik** | Buffer berubah paling cepat ~13–35 mnt (1 produksi selesai) atau per-slot (jam) → lag 60s diabaikan |
| **Producer** (klaim job + render) | **loop persisten** (pegang semaphore=core) | **10 detik** saat idle; **saat render selesai LANGSUNG klaim berikutnya** (tanpa tunggu) | Idle ≤10s vs render 13–35 mnt = <1,5% waste; isi slot core secepatnya |
| **Publisher** (cek slot jatuh tempo → upload) | loop / cron | **30 detik** | Slot granularity menit; 30s pasti tangkap slot ≤30s; upload ringan (~5 dtk) |

Interval = **default beralasan, config-driven** (ubah tanpa deploy), diturunkan dari **waktu produksi terukur** (13–35 mnt). Divalidasi/tuning di produksi — bukan angka karang.

### Angka pondasi (tervalidasi)
- 1 video: **35 mnt sekarang → ~13 mnt** (optimasi render 2,87× terukur + paralel image).
- Capacity: **~50 tenant → 4 core · ~100 → 8 core/16GB · 1000 → ~72 core (multi-node)**. RAM ~2GB/core + swap.
- **Optimasi render = prioritas #1** (lever terbesar, murah, prasyarat scale).

Detail lengkap + bukti file:line: memory `decisions_production_scaling` · status/roadmap: `PROGRESS.md`.

---

## 12d. FITUR v2 TERBANGUN (2026-06-15) — admin, direct-produce, CMS, landing

> Ringkasan fitur yang sudah dibangun + tervalidasi (branch `v2-backend`, migrasi 0001-0043). Detail teknis: `PHASE10_ADMIN_WIRING.md` + `progress_journal`.

**A. Direct / On-demand Produce ("1 mesin, 2 mode") — pengganti "Run Now" ambigu.** Satu MESIN pipeline, dua MODE: (1) **Scheduled** (producer jaga buffer → publisher slot, §12c) + (2) **Direct** (`direct_jobs` di-drain producer SEBELUM stok-buffer, **semaphore core SAMA → anti-OOM utuh**). 3 pemicu kontekstual: **tenant** "Test sekarang (private)" (Channel Detail — preview config sebelum jadwal) · **tenant** "Jalankan ulang" (Run Detail gagal — mis. setelah top-up kredit AI) · **admin** "Test niche" (uji niche baru di channel internal `admin-test`). Progress live di `/runs/[id]` (D5, live-tail run_id), status Antre/Berjalan di Runs + panel admin System Health. Diproses worker v2 saat cutover.

**B. Admin Panel penuh** (lihat §7 IA): Tenants/Pricing/Niches/Catalog/System/Support/Content/Test-Lab/Account — semua wired ke DB (service_role gated). Caps/harga/niche/katalog/kredensial-test admin-editable.

**C. CMS — landing/marketing content admin-editable.** Halaman **Blog, Docs, Demo** kini DB-backed (`blog_posts`/`docs_articles`/`demo_tours`), dikelola admin via `/admin/content` (editor markdown, draft/publish). Publik baca yang published (RLS sembunyikan draft). **Harga landing/pricing (A1/A2) = dari `pricing_config`** (no-hardcode terpenuhi). Halaman statik lain (About/Contact) = mailto nyata. **Catatan:** admin tak perlu ngoding/deploy untuk update konten.

**D. Validasi kredensial NYATA.** Onboarding "Test koneksi" + admin Test Lab benar-benar memanggil API provider (OpenAI/Anthropic/ElevenLabs) → ok/gagal (bukan simulasi).

**E. Keamanan kredensial tenant (2026-06-15) — nilai jual.** Owner: "seluruh kredensial tenant AMAN".
- **YouTube OAuth BYO-CC = TERBANGUN** (Opsi A, owner-approved): tenant bawa Google OAuth app sendiri (client_id+secret) → consent → refresh_token. **SELURUH enkripsi (Fernet) + tukar-token + tulis `tenant_credentials` terjadi di server Python (`webhook_app`)**; Next hanya proxy authed (sesi Supabase→tenant_id) → master key (`ENCRYPTION_KEY`) **TAK pernah ke frontend/Vercel**. State HMAC anti-CSRF. Entry: onboarding + Settings→Integrasi (connect/disconnect/status). Sisa = deploy `webhook_app` ke VPS + 1× uji consent dgn GCP-app nyata.
- **SEMUA API key AI terenkripsi at-rest** (migr 0044): `llm/visual/tts/youtube_api_key` plaintext → kolom `*_enc` (Fernet). Tulis via vault `/api/keys/set` (server pemegang-kunci); `set_tenant_config` RPC **tak bisa lagi** tulis key plaintext (param key dibuang). Worker dekripsi saat baca (`tenant_config._eff_key`). Plaintext lama dimigrasi + di-null.

**F. QC-fail = Review-in-Domain + Approve (OPSI C, owner 2026-06-17 — MENGGANTIKAN "publish PRIVATE" Opsi A 2026-06-16).** Video yang gagal QC (mis. durasi di luar toleransi preset) **tidak dihapus & TIDAK auto-upload ke YouTube** → **tetap di buffer S3** (status `ready_with_issues`) + tenant terima **advisory** (alasan + rekomendasi, via Telegram) → tenant **tinjau dari dashboard (preview dari S3)** → **putuskan: Pakai (kita publish, kuota−1) / Buang (hapus) / abaikan (TTL auto-buang).** **Integrasi §12c = Opsi C:** Producer **HANYA stok** (tak pernah publish); `ready`+`ready_with_issues` **dihitung stok → rem alami** (buffer penuh ⇒ producer berhenti); Publisher **hanya auto-publish `ready`** saat slot (kuota+laporan di publish); video bermasalah ditinjau **di domain kita** (YouTube tak pernah menerima tanpa persetujuan ber-kuota → tutup cheat flip-Studio + off-schedule di sumber); hard-fail beruntun → **circuit-breaker** (pause + alarm seketika). **Mengganti Opsi A** yang membuat producer upload-privat ke YouTube → biang **INSIDEN RUNAWAY 2026-06-17** (loop tanpa rem + upload off-schedule). Opsi C **otomatis menyetop runaway**. Detail desain: `QC_CONTENT_ARCHITECTURE.md §3/§6.2`; checklist status: `PROGRESS.md §PERBAIKAN ARSITEKTUR PRODUKSI v2 (OPSI C)`.
- **Isolasi:** `tenant_credentials` = RLS service_role-only; `tenant_configs` = RLS per-tenant; key tak pernah di-log/ditampilkan ulang. **Landing** punya section "Keamanan kredensial" (klaim hanya yang benar).

**Prinsip ditegakkan owner (2026-06-15):** nol komponen FE fake/non-functional (yang tanpa backend ditandai jujur "segera"/disembunyikan) · no-hardcode · service_role hanya server-route admin · semua keputusan via expert + validasi runtime.

❓ **Q13:** Setuju prioritas: Phase 6 (Self-Learning + Diversity) di-prioritaskan SETELAH foundation backend (Phase 1-5) — sebelum payment & UI?

---

## 13. RINGKASAN — Keputusan yang Perlu Disepakati

| # | Keputusan | Recommend | Status |
|---|---|---|---|
| Q1 | Target persona "Faceless Channel Scaler" | Setuju | ✅ TENTATIVE |
| Q2 | Trial 7 hari / 5 video / no CC | Setuju | ✅ TENTATIVE |
| Q3 | Wizard step 3 (API keys) bisa di-skip dengan trial credit | Setuju | ✅ TENTATIVE |
| Q4 | Pricing Rp 149/349/699 + Enterprise custom | Setuju | ✅ TENTATIVE |
| Q5 | Annual prepay 20% off | Setuju | ✅ TENTATIVE |
| Q6 | Curated catalog (locked engine, choose model) | Setuju | ✅ TENTATIVE |
| Q7 | Konfigurasi 3 lapis (Default/Override/Power) | Setuju (need user input untuk field tutup) | ⏳ |
| Q8 | Dark mode default + bilingual ID+EN | Indonesia dulu, dark mode | ⏳ |
| Q9 | Landing page pitch v2 | Setuju | ⏳ |
| Q10 | AI Slop Defense Engine pillar #1 | Setuju (NEW) | ⏳ |
| Q11 | Margin 43-55% acceptable | Setuju | ⏳ |
| Q12 | Risk register comprehensive | Setuju | ⏳ |
| Q13 | Phase 6 (Self-Learn + Diversity) priority sebelum Payment & UI | Setuju | ⏳ |

---

## 14. NEXT STEP

Setelah Anda review & approve dokumen ini (atau koreksi):

1. **Update dokumen ini** dengan keputusan final (status ⏳ → ✅)
2. **Sync ke memory** (`~/.claude/.../memory/`) — buat memory file baru `product_spec_v2.md`
3. **Update `PROGRESS.md`** master plan untuk align dengan keputusan (terutama Phase 6 priority)
4. **Update `~/.claude/plans/expressive-waddling-moler.md`** kalau perlu
5. **Mulai Phase 1.1** SOFTCODE LLM (sudah di-plan detail)

Saya tidak akan koding sebelum minimal **Q1, Q4, Q6, Q10, Q13** (business critical) disepakati explicit.

---

## 📚 SOURCES (Market Research Juni 2026)

### Competitor Pricing
- [OpusClip Pricing](https://www.opus.pro/pricing)
- [Klap Pricing](https://klap.app/pricing)
- [Submagic Pricing](https://www.submagic.co/pricing)
- [Pictory Pricing](https://pictory.ai/pricing)
- [Vidnoz Pricing](https://www.vidnoz.com/pricing.html)
- [Synthesia Pricing](https://www.synthesia.io/pricing)
- [AutoShorts.ai Review 2026](https://www.argil.ai/blog/autoshorts-ai-review-2026-features-pricing-and-better-alternatives)

### Market Data
- [YouTube Shorts Statistics 2026](https://autofaceless.ai/blog/youtube-shorts-statistics-2026)
- [Asia-Pacific AI Video Generator Market](https://www.intelmarketresearch.com/asia-pacific-ai-video-generator-software-market-market-41251)
- [vidIQ Shorts Monetization 2026](https://vidiq.com/blog/post/youtube-shorts-monetization/)

### AI API Pricing
- [Anthropic Pricing 2026 (Finout)](https://www.finout.io/blog/anthropic-api-pricing)
- [Anthropic Pricing 2026 (Benchlm)](https://benchlm.ai/blog/posts/claude-api-pricing)
- [ElevenLabs Pricing 2026](https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs)
- [OpenAI Image API Pricing 2026](https://www.aifreeapi.com/en/posts/openai-image-generation-api-pricing)
- [gpt-image-1 Cost Detail](https://costgoat.com/pricing/openai-images)

### YouTube AI Slop Crackdown
- [YouTube AI Slop Crackdown 2026](https://outlierkit.com/resources/youtube-ai-slop-crackdown-2026/)
- [ScaleLab YouTube AI Crackdown](https://scalelab.com/en/why-youtube-is-cracking-down-on-ai-generated-content-in-2026)
- [YouTube Monetization w/ AI](https://miraflow.ai/blog/youtube-monetization-ai-content-2026-allowed-demonetized)

### BYOK Strategy Validation
- [n8n Pricing 2026](https://instapods.com/blog/n8n-pricing/)
- [n8n Cloud Pricing](https://openhosst.com/blog/n8n-cloud-pricing)
- [IronCore Labs BYOK Pitfalls](https://ironcorelabs.com/blog/2024/five-things-saas-mess-up-with-byok/)

### Indonesia Market
- [Jobstreet Content Creator Salary ID](https://id.jobstreet.com/career-advice/role/content-creator/salary)
- [Midtrans Docs](https://docs.midtrans.com/) (payment gateway — akun owner sudah ada)
- [Midtrans Recurring / Subscription](https://docs.midtrans.com/docs/snap-recurring-transaction)
- *(Xendit/Stripe = opsi historis, tidak dipakai — Midtrans final)*

### Competitor Auto-Pilot Tools
- [inReels Auto-Upload Guide](https://www.inreels.ai/blog/create-ai-youtube-shorts-auto-upload)
- [Mirra YouTube Shorts Automation](https://www.mirra.my/en/blog/youtube-shorts-ai-automation-guide)
- [ytZolo Per-Channel AI Tools](https://ytzolo.com/blog/ai-youtube-tools-2026/)
- [Creativism.id ID Workflow](https://creativism.id/auto-generate/)

---

**END OF DOCUMENT v2.0 — siap di-review.**
