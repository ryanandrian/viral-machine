# PHASE 6 — Self-Learning + Diversity Engine (🥇 CORE MOAT) — Rencana Desain

> Status: 📋 DESIGN (propose-first). Pondasi: `DESAIN_PRODUK_SAAS.md §8` (#1 moat: belajar dari YT Analytics post-publish) + `§9` (AI Slop Defense). Cadence: [[decisions_production_scaling]]. Tag: [[decisions_niche_model]]. Status LIVE = `PROGRESS.md`.
>
> **Temuan kunci:** sebagian besar self-learning **SUDAH ADA & jalan** (di v1). Phase 6 = **wire ke v2 + lengkapi diversity engine + AI disclosure** — bukan bangun dari nol. Lebih kecil dari estimasi.

## 0. Kondisi nyata — SUDAH ADA (jangan rebuild, verified 2026-06-14)
| Komponen | Status | Bukti |
|---|---|---|
| Pull YT Analytics → `video_analytics` | ✅ | `channel_analytics.py::fetch_and_store` (YT Data v3 + Analytics v2: views/watch_time/avg_view_pct/ctr/subscriber_gain). 3182 row v2. |
| Compute insights → `channel_insights` | ✅ | `performance_analyzer.py::compute_and_store` (niche_weights/top_hooks[by CTR]/content_type_perf/avoid_patterns). Grade: insufficient(<5)/learning(5-20)/peak(50+). 15 row. |
| Inject insights ke generasi | ✅ | ScriptEngine (`_build_insights_block`), NicheSelector (smart-focus), HookOptimizer (historical hooks). |
| Diversity guard NICHE | ✅ parsial | `schedule_manager._apply_diversity_guard` (anti-dominasi niche, max N/6 terakhir). |
| Cadence harian | ✅ v1 | `scripts/compute_insights.sh` (cron v1). **v2 worker belum wire.** |

## 1. GAP yang Phase 6 bangun
- **6.1 Self-learning LOOP di v2** — jadwalkan `fetch_and_store` + `compute_and_store` di **`worker_decoupled`** (loop/cadence harian + post-publish 24-72h per §8), **channel-scoped** (`channel_id`, kini per-tenant). Ganti cron v1.
- **6.2 Diversity Engine PENUH (AI Slop Defense §9.1)** — selain niche (ada), tambah rotasi algoritmik per-channel: **voice** (pool per-paket), **hook style** (6 pattern round-robin), **music mood**, **visual seed/fingerprint**. Anti "output seragam" → hindari demonetisasi YouTube AI-policy 2026.
- **6.3 AI Disclosure tag (§9.2)** — `youtube_publisher` set flag "altered/synthetic content" + metadata "made with AI". (Catatan: verifikasi field API YouTube terkini.)
- **6.4 Insights lebih dalam** — visual_style adaptation; **per-tag performance** (`videos.topic_tags`, [[decisions_niche_model]]); insights **per-channel** (bukan per-tenant) untuk multi-channel.

## 2. Sub-phase + validation gate (urutan)
| Sub | Scope | Validation (nyata, hemat) |
|---|---|---|
| **6.1** | Wire fetch+compute loop ke worker_decoupled (channel-scoped, cadence config-driven) | run loop lokal vs v2 → `channel_insights` ter-update per channel; idempotent |
| **6.2** | Diversity Engine: voice/hook/music/visual rotation (modul `diversity.py`) + integrasi ke pipeline/selector | unit: rotasi tak ulang ≤N terakhir; integrasi: 3 produksi beruntun → voice/hook beda |
| **6.3** | AI disclosure tag di publish | publish (private test) → cek metadata disclosure via API |
| **6.4** | Insights: per-tag + visual-style + channel-scope | compute → channel_insights punya per-tag; inject ke generasi |

## 3. Catatan arsitektur
- Compute = LLM **config tenant** (Haiku/utility untuk meta-learning — cost-aware, §8). Nol hardcode provider.
- **Feeds Phase 7 (Compliance Score):** metrik diversity (voice/niche/hook spread, anti-duplikat, disclosure) = persis 5 dimensi Compliance radar. Jadi 6.2 = sumber data 7.
- **channel-scoping**: insights/diversity per-channel (selaras multi-channel Phase 5). `channel_insights.channel_id` sudah ada.
- Non-breaking: tenant tanpa cukup data → grade insufficient → estimasi AI (perilaku sekarang).

## 4. Pertanyaan terbuka (owner)
1. Cadence loop self-learning: harian (compute) + per berapa jam fetch analytics? (default config: fetch tiap 24j, compute tiap 24j — tunable).
2. Diversity Engine: rotasi voice butuh **pool voice per paket** (Starter 5 / Pro 15 — DESAIN §9) → perlu katalog voice (nyambung TTS catalog-wiring follow-up). Bangun katalog voice di 6.2 atau pakai voice yang ada dulu?
3. AI disclosure: wajib semua video atau toggle tenant?

---
### Changelog
- 2026-06-14 — dibuat. Kondisi-nyata (sebagian besar EXISTS) + gap (6.1-6.4) + sub-phase. Menunggu nod owner sebelum implementasi.
