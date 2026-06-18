# Rencana Funnel Onboarding — "Pikat Dulu, Todong Belakangan"

> **Status:** USULAN MATANG (belum dieksekusi). Dibuat 2026-06-19. Berpijak pada audit FE/BE/DB nyata (3 penjelajah, kutip file/tabel/migrasi — bukan asumsi).
> **North-star:** di akhir trial, tenant **sudah terlanjur punya konten bermutu LIVE di YouTube mereka, hasil mesin ini** → sayang ditinggal → **bayar paket + beli kredit**. Sekaligus **hemat bakar uang** lewat batas trial yang masuk akal.
> ⚠️ Dokumen ini **merevisi** "trial = strict BYOK" (DESAIN §3) jadi **hybrid** & menutup kontradiksi §3↔§5 (lihat §7).

---

## 1. Prinsip (North-Star)

1. **Nilai sebelum kerja.** Tenant merasakan keajaiban **sebelum** diminta setup. Tidak ada todongan OAuth/API-key di langkah awal.
2. **Hook = endowment.** Bukan demo — tenant harus **memiliki** video bermutu di channel YouTube **mereka sendiri**. Channel mulai tumbuh → berhenti = rugi → lanjut bayar.
3. **Progressive disclosure.** Langkah berat (YouTube, BYOK) muncul **hanya saat termotivasi**, dibingkai sebagai hadiah/buka-kunci.
4. **Burn terkendali.** Platform "mentraktir" sedikit, sekali, engine murah, ber-cap & anti-abuse. Habis → BYOK / beli kredit.
5. **Jujur.** Tidak ada placeholder palsu (voice palsu, tombol mati). Belum siap = sembunyikan.

---

## 2. PETA KONDISI NYATA (hasil audit FE/BE/DB)

### 2.1 Backend produksi
| Kemampuan | Status | Bukti |
|---|---|---|
| Produksi on-demand (1 video sekarang) | ✅ ADA | `producer.run_direct()` drain `direct_jobs`; FE "Test sekarang" sudah insert |
| Produksi buffer + publish per-slot | ✅ ADA | `producer.produce_one()` → `content_inventory` → `publisher` slot tenant-tz |
| TTS gratis (tanpa key) | ✅ ADA | `providers/tts/edge_tts.py` (Edge TTS, default fallback) |
| Visual murah | ✅ ADA (perlu key) | `ai_image:gpt-image-1-mini` (butuh OpenAI key) — Pexels = fosil, jangan dihidupkan |
| **LLM murah/platform (tanpa key tenant)** | ❌ **HARUS DIBANGUN** | LLM **wajib BYOK**; tak ada jalur "Haiku via key platform" |
| Gate trial/billing | ✅ ADA | `billing/limits.py`: `can_produce()` {active,trial,grace}; `start_trial()` |
| Publish YouTube (upload+refresh+metadata) | ✅ ADA | `distribution/youtube_publisher.py` lengkap |
| **OAuth YouTube live** | ⚠️ **BLOCKER** | `webhook_app` (vault OAuth) **belum jalan di VPS** → connect gagal |

### 2.2 Database (Supabase v2, migrasi 0001–0055)
| Aspek | Status | Bukti |
|---|---|---|
| Provisioning trial otomatis saat signup | ✅ ADA | trigger `handle_new_tenant` (migr 0028): `subscription_status='trial'`, `plan_type='trial'`, `current_period_end=now+7d` |
| Caps trial | ✅ ADA | `plan_limits('trial',1,1)` (1 video/hari, 1 channel) + `app_config.trial_duration_days=7` |
| Katalog provider/model | ✅ ADA | `ai_providers`(anthropic/openai/replicate) · `ai_models`(Sonnet 4.6, Haiku 4.5, GPT-4o(-mini), gpt-image-1-mini) |
| Katalog niche (entitlement) | ✅ ADA | `niches`(is_base/access_type/exclusive_to/voice_profile) |
| Katalog bahasa | ✅ ADA | `content_languages` (6 locale, 2 official) |
| Katalog voice | ⚠️ **KOSONG** | `voice_catalog` 0 baris |
| **Saldo kredit / kuota video gratis** | ❌ **HARUS DIBANGUN** | tidak ada kolom/tabel credit/quota/free-video di mana pun |
| RPC config aman (whitelist) | ✅ ADA | `set_tenant_config` (7 arg), `set_tenant_content_config`, `set_channel_publish_slots` (validasi ≤ cap), `set_channel_niche` (entitlement), `approve/discard_inventory_item` |

### 2.3 Frontend (Next.js 16, App Router, RLS)
| Layar/route | Status | Catatan |
|---|---|---|
| `/onboarding` | ◐ HYBRID | wizard 5-langkah; **data hardcode** (PLANS/NICHES/VOICES/jadwal); `finish()` persist nyata (RPC + keys/set + channels.insert) |
| `/dashboard` | ✅ NYATA | KPI dari `production_runs`; **grid2 bisa disisipi kartu buka-kunci** |
| `/channels/[id]` | ✅ NYATA | tab niche (RPC+entitlement), duration-preset (`PresetTables`), **"Test sekarang"→`direct_jobs`** |
| `/schedule` | ✅ NYATA | tulis `channels.publish_slots` via RPC (validasi cap) |
| `/runs`, `/runs/[id]` | ✅ NYATA | list + live-tail log; retry→`direct_jobs` |
| `/review` | ✅ NYATA | approve/discard `ready_with_issues` + preview S3 |
| `/settings` > Integrations | ✅ NYATA | YouTube connect/status/disconnect via `/api/youtube/*` |
| `/config` > AI Engines | ◐ HYBRID | input key→vault; **selector LLM baru 2 opsi hardcode**, belum dari `ai_models` |
| Komponen reusable | ✅ | `AppShell`, `PresetTables`, `Bi`(i18n id/en), token kartu/badge/tombol |

**Kesimpulan:** mesin & DB **80% siap**; yang kurang spesifik = **(1) jalur LLM platform-murah, (2) ledger kredit/kuota gratis, (3) deploy webhook_app, (4) onboarding data-driven & ramping, (5) isi/atau-sembunyikan voice.**

---

## 3. WORKFLOW TENANT BARU (TRIAL) — langkah-demi-langkah

> Tiap langkah dipetakan ke route/fungsi/tabel nyata + tanda **[ADA]** / **[BUILD]**.

| # | Tahap | Aksi tenant | FE | BE / DB | Status |
|---|---|---|---|---|---|
| 0 | **Daftar** | Google/email signup | `/auth` | trigger `handle_new_tenant` → trial 7hr | **[ADA]** |
| 1 | **Cicipi (onboarding ramping)** | Pilih **niche → bahasa → voice** | `/onboarding` (rebuild 3-langkah) | baca `niches`(entitled)+`content_languages`(+`voice_catalog`/default) | **[BUILD]** wiring katalog |
| 2 | **Lihat contoh** | Tonton galeri contoh niche-nya | `/onboarding` akhir / `/dashboard` | manifest video pre-render (S3) | **[BUILD]** galeri |
| 3 | **Masuk dashboard** | Lihat channel + checklist buka-kunci | `/dashboard` (kartu baru) | `channels` (dibuat di finish), `production_runs` | **[BUILD]** kartu; `finish()` **[ADA]** |
| 4 | **Video pertama (HOOK, gratis)** | Klik "Buat video pertama gratis" | kartu dashboard → modal | insert `direct_jobs`(free flag) → `run_direct` pakai **engine platform murah** | **[BUILD]** jalur LLM platform + gate kredit |
| 5 | **Pantau produksi** | Lihat progres pipeline | `/runs`, `/runs/[id]` (live-tail) | `production_runs`+`pipeline_run_logs` | **[ADA]** |
| 6 | **Tayang ke channel** | "Video siap! Hubungkan YouTube" | kartu dashboard → `/settings` Integrations | `/api/youtube/connect`→`webhook_app`→`tenant_credentials` | **[ADA kode]** · **[BUILD]** deploy webhook_app |
| 7 | **Otomatiskan** | Atur slot + aktifkan scheduler | `/schedule` | RPC `set_channel_publish_slots` | **[ADA]** |
| 8 | **Trial run (ber-cap)** | Mesin produksi beberapa lagi | otomatis | producer loop + gate kredit (free habis→BYOK) | **[BUILD]** gate kredit |
| 9 | **BYOK saat kredit habis** | Masukkan key vendor pilihan + model | `/config` AI Engines | `/api/keys/set` (Fernet) + `set_tenant_config(llm_library)` | **[ADA]** · **[BUILD]** picker vendor+model dari `ai_models` |
| 10 | **Konversi** | "Channel Anda X video/Y views — lanjutkan" | banner `/dashboard` + email | nudge hari 5–7 | **[BUILD]** nudge |

---

## 4. DRAFT UI/UX (wireframe)

### 4.1 Onboarding ramping — Langkah 1/3: Niche (data dari `niches`)
```
┌─────────────────────────────────────────────────────────────┐
│  MesinViral            ●─────○─────○   Niche · Bahasa · Suara │
├─────────────────────────────────────────────────────────────┤
│  Channel Anda tentang apa?                                    │
│  Pilih satu (bisa tambah nanti). Mesin yang produksi.         │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 🌌       │  │ 🏛️       │  │ 🌊       │  │ 🤯       │       │
│  │ Misteri  │  │ Sejarah  │  │ Misteri  │  │ Fakta    │       │
│  │ Semesta  │  │ Kelam    │  │ Samudra  │  │ Menakjub.│       │
│  │  ✓ (sel) │  │          │  │          │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  (kartu di-generate dari niches WHERE is_base/entitled)       │
│                                            [ Lanjut → ]       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Onboarding akhir — Galeri contoh (the "wow")
```
┌─────────────────────────────────────────────────────────────┐
│  Beginilah yang akan diproduksi channel Anda 👇              │
│  (contoh nyata niche "Misteri Semesta", bahasa Indonesia)     │
│                                                               │
│   ┌────────┐  ┌────────┐  ┌────────┐    ► tap untuk putar     │
│   │ ▶ 0:42 │  │ ▶ 0:58 │  │ ▶ 0:51 │    (video pre-render,    │
│   │ [thumb]│  │ [thumb]│  │ [thumb]│     biaya per-tenant ≈0) │
│   └────────┘  └────────┘  └────────┘                          │
│                                                               │
│   "Otomatis. Tiap hari. Tanpa Anda mengedit apa pun."         │
│                               [ Masuk ke Dashboard → ]        │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Dashboard — kartu buka-kunci (progressive disclosure)
```
┌─────────────────────────────────────────────────────────────┐
│  Halo, Riko 👋        Trial: 7 hari tersisa · 1 video gratis  │
├─────────────────────────────────────────────────────────────┤
│  🚀 3 langkah ke channel otomatis Anda:                       │
│  ┌─────────────────────────┐ ┌─────────────────────────┐     │
│  │ ① 🎬 Buat video pertama │ │ ② ▶ Hubungkan YouTube   │     │
│  │   GRATIS — ditraktir     │ │   (untuk tayang otomatis)│     │
│  │   [ Buat sekarang ]      │ │   [ Hubungkan ] (locked  │     │
│  │                          │ │     sampai video jadi)   │     │
│  └─────────────────────────┘ └─────────────────────────┘     │
│  ┌─────────────────────────┐                                  │
│  │ ③ ⏰ Atur jadwal tayang  │   (terbuka setelah ②)            │
│  └─────────────────────────┘                                  │
├─────────────────────────────────────────────────────────────┤
│  Recent Runs (kosong) · Success — · Compliance —              │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Buat video pertama — modal → progres
```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│ 🎬 Video pertama Anda — gratis│     │  Sedang dibuat… (≈3–5 menit)  │
│ Niche : Misteri Semesta       │ ──► │  ✓ Skrip   ✓ Suara            │
│ Durasi: 60 dtk (ideal)        │     │  ◐ Gambar  ○ Render  ○ QC     │
│ Engine: hemat (ditraktir)     │     │  [ Lihat progres di /runs ]   │
│        [ Buat Video ]         │     │  Hasil = privat (preview dulu)│
└──────────────────────────────┘     └──────────────────────────────┘
  insert direct_jobs(job_type='free_trial',          run_direct → engine platform murah
  publish_privacy='private', is_free=true)            (Haiku + gpt-image-mini + Edge TTS)
```

### 4.5 Video jadi → dorong publish (hook tertanam)
```
┌─────────────────────────────────────────────────────────────┐
│  ✅ Video pertama Anda siap! [ ▶ Preview ]                    │
│                                                               │
│  Mau tayang di channel YouTube Anda?                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ▶ Hubungkan YouTube  →  video langsung tayang            │ │
│  │   [ Hubungkan channel ]                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│  (B1: wizard BYO-CC terpandu  |  B2: "Authorize" 1-klik)      │
└─────────────────────────────────────────────────────────────┘
```

### 4.6 Banner konversi (hari 5–7)
```
┌─────────────────────────────────────────────────────────────┐
│ ⏳ Trial habis 2 hari lagi. Channel Anda sudah 4 video,       │
│    1.2rb views. Jangan biarkan berhenti.                      │
│    [ Pilih paket + masukkan API key Anda ]   [ nanti ]        │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Kendali Biaya & Batas Trial (anti bakar uang)

Model: **trial = saldo kredit kecil + cap keras + anti-abuse.** Hanya video "ditraktir" yang membebani; sisanya BYOK.

| Kontrol | Usulan | Alasan |
|---|---|---|
| Galeri contoh | pre-render sekali (amortized) | tour bebas, ~0 biaya per-tenant |
| **Kuota gratis** | **1 video** penuh-platform (agresif: ≤3) | hook cukup 1; tunggu data konversi |
| Engine trial | Haiku + Edge TTS + gpt-image-1-mini | termurah; konsisten katalog |
| Batas teknis | durasi preset pendek, resolusi standar | tekan biaya/video |
| Setelah kuota habis | **wajib BYOK / beli kredit** | burn berhenti; tenant serius lanjut biaya sendiri |
| Caps tier `trial` | 1 channel · 1 video/hari · 7 hari | sudah ada di `plan_limits`/`app_config` |
| **Estimasi burn** | 1 gratis ≈ **Rp 6rb** · 3 ≈ **Rp 18rb** | jauh di bawah ambang $2/user (DESAIN) |

**Anti-abuse:** 1 trial per akun terverifikasi (email+Google); **video gratis cair hanya setelah YouTube tersambung** (filter abuser sekali-pakai); heuristik device/IP; saldo tak auto-refill; **tanpa watermark** (justru ingin mereka pamer konten bermutu).

---

## 6. BACKLOG YANG HARUS DIBANGUN (konkret, dari audit)

**DB (migrasi baru):**
- `tenant_configs.trial_credit_balance` (int, satuan cents) **+** `free_video_used`/`free_video_limit` (int) — ATAU tabel `trial_credits` (ledger audit). *(belum ada sama sekali)*
- `app_config`: `trial_free_videos` (default 1).
- (opsi voice) isi `voice_catalog` per locale/provider **atau** pakai `niches.voice_profile`.

**BE (Python):**
- Jalur **LLM platform-murah** (Haiku via key platform) aktif **hanya** saat `plan_type='trial'` + saldo kredit > 0; deduksi kredit pasca-produksi.
- Gate `can_produce()` cek saldo kredit + `free_video_used < limit`; habis → wajib BYOK.
- Flag `direct_jobs`/`content_inventory.metadata.is_free_trial` + hitung pemakaian.
- **Deploy `webhook_app`** (vault OAuth) ke VPS (blocker publish).

**FE (Next.js):**
- Rebuild `/onboarding` jadi **3-langkah data-driven** (niche/bahasa/voice dari katalog; buang plan/youtube/keys dari alur wajib; buang copy "kredensial platform" basi).
- Galeri contoh (komponen + manifest).
- Dashboard **kartu buka-kunci** (grid2) + state progres.
- Modal "Buat video pertama" → `direct_jobs(free)`.
- Picker **vendor+model LLM** dari `ai_models` di `/config` AI Engines (ganti 2-opsi hardcode).
- Banner konversi.
- Perbaiki **mismatch niche** (key FE `fun_facts` vs DB) → pakai `niche_id` nyata.

---

## 7. Menutup Kontradiksi Dokumen (§3 vs §5)

DESAIN saat ini bertabrakan: **§3** trial=strict-BYOK vs **§5 tabel** trial=platform-managed. **Resolusi (jika A1 disetujui): Trial = HYBRID** — kuota kecil ditraktir platform (engine murah, ber-cap+verifikasi) untuk hook, lalu **BYOK wajib** untuk lanjut. Menyatukan anti-abuse (§3) + aha (§5). Setelah diketok, §3/§5 di-update.

---

## 8. Roadmap Implementasi (bertahap; tiap fase: validasi lokal → deploy → update PROGRESS)
1. **F0** Onboarding 3-langkah data-driven (niche/bahasa/voice) + buang copy basi + fix mismatch niche.
2. **F1** Galeri contoh pre-render.
3. **F2** Ledger kredit trial + gate produce + jalur LLM platform-murah.
4. **F3** Dashboard kartu buka-kunci + modal "video pertama gratis".
5. **F4** Deploy `webhook_app`; jalur publish (B1 terpandu / B2 1-klik).
6. **F5** Picker vendor+model BYOK; gating "kredit habis → BYOK".
7. **F6** Banner + email konversi (hari 5–7).

---

## 9. Keputusan yang Ditunggu dari Owner
- [ ] **A** — A1 (traktir 1–3 video, **rekomendasi**) atau A2 (strict-BYOK + galeri saja)?
- [ ] Jika A1: kuota gratis = **1** atau **3** video?
- [ ] **B** — B1 (BYO-CC terpandu, interim cepat) atau investasi **B2** (OAuth YouTube 1-klik, buka funnel sesungguhnya)?
- [ ] **Voice:** isi `voice_catalog` sekarang, atau interim default per-niche (`niches.voice_profile`) + sembunyikan picker?
- [ ] Watermark video trial: ya / **tidak** (rekomendasi tidak)?
- [ ] Setuju update DESAIN §3/§5 jadi model hybrid setelah A diketok?
