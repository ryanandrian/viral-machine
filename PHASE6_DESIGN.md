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
| Cadence harian | ✅ v2 (LIVE 2026-06-28) | `self_learning` loop di `worker_decoupled` (24j; fetch + compute insights + viral_score_weights). Cron v1 `compute_insights.sh` **DIHAPUS** 2026-06-28. |

## 1. GAP yang Phase 6 bangun
- **6.1 Self-learning LOOP di v2** ✅ LIVE — `fetch_and_store` + `compute_and_store` (+ `ViralWeightOptimizer`) di **`worker_decoupled`** (loop 24j + post-publish 24-72h per §8), **channel-scoped** (`channel_id`; insight bleed se-tenant DIPERBAIKI 2026-06-28 commit `3bd32ee`). Cron v1 DIHAPUS. Detail [[project_self_learning_remediation_2026_06_28]].
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
## ✅ STATUS 6.2 — increment #1 DONE (2026-06-14)
Anchor: **DESAIN §9.1** (Diversity Layer). Migrasi `0018` (videos += voice_id/hook_pattern/music_mood/visual_seed + `diversity_config` single-row) + `src/intelligence/diversity.py` (`DiversityEngine` LRU per-channel, config-driven, fail-soft) + integrasi:
- ✅ **Hook-pattern rotation** — `producer` set `preferred_hook_pattern` (LRU pool) → `hook_optimizer._select_winner` re-pilih winner ke arah itu **HANYA bila skor dalam `HOOK_DIVERSITY_TOLERANCE` (default 8)** → quality-first (tak korbankan hook unggul). Unit-test 6/6.
- ✅ **Visual-seed rotation** — `producer.pick_seed` → `visual_seed` thread ke `ai_image` (Replicate `input.seed`; OpenAI tak punya param = fail-soft abaikan). Frame fingerprint unik §9.1.
- ✅ **Tutup gap Phase-5 decoupled** — `publisher._publish_from_buffer` kini **menulis row `videos`** (sebelumnya tak ada di mode decoupled → niche-guard & diversity tak punya histori) + rekam 4 dimensi → loop lookback berikutnya terisi.
- ✅ **Niche rotation** = sudah ada (`schedule_manager._apply_diversity_guard`, tak diubah).
- 🟡 **Voice rotation = DEFERRED (jujur, bukan skip diam):** `DiversityEngine` siap dimensi 'voice', TAPI belum di-wire di produce — channel kini hanya 1 voice (TenantRunConfig/niche-map), butuh **voice-pool catalog** (nyambung TTS catalog-wiring) + surfacing voice_id terpakai. Aktif saat voice-catalog ada. `voice_id` di `videos` = null s/d itu.
- ✅ **Music-mood rotation = DONE** (koreksi 2026-06-14, owner benar — saya sempat salah baca): `music_selector` v1 **TIDAK** pakai `background_music_mood` LLM; mood = keyword-detect (tabel `moods`) + fallback `niches.mood_priority` → mood **niche-anchored**. Maka rotasi LRU per-channel atas `niches.mood_priority` = **quality-safe** (semua mood di pool sudah niche-appropriate, admin-kurasi) — persis §9.1. Producer hitung `preferred_music_mood` (LRU) → thread `tenant_config→video_renderer._mix_music→select_and_download(preferred_mood)` (skip keyword-detect bila diset). **Perekaman diperbaiki:** `videos.music_mood` = mood AKTUAL yang di-inject (bukan proxy LLM); null bila niche tanpa mood_priority. Track-level `random.choice` tetap menambah variasi.

**Validasi murah (tanpa render/API):** py_compile 9 file ✅ · import 9 modul ✅ · DiversityEngine LRU (rotasi tak ulang ≤N, seed hindari recent, graceful) ✅ · `_select_winner` 6/6 (rotate dalam-toleransi / keep quality / resolve-formula) ✅ · `channel_id` threaded + write_video dims ✅. Applied v2 migr 0018 idempotent.

### Changelog
- 2026-06-14 — dibuat. Kondisi-nyata (sebagian besar EXISTS) + gap (6.1-6.4) + sub-phase. Menunggu nod owner sebelum implementasi.
- 2026-06-14 — **6.2 increment #1 DONE** (hook + visual-seed + tutup gap write_video; voice/music deferred dgn alasan). Anchor DESAIN §9.1. Validasi murah hijau.
- 2026-06-14 — **music-mood rotation DONE** (koreksi: mood v1 = keyword+niche.mood_priority, BUKAN LLM → rotasi LRU mood_priority = quality-safe) + perekaman mood AKTUAL diperbaiki. Tinggal **voice rotation** yang deferred (butuh voice-pool catalog + EL aktif).
