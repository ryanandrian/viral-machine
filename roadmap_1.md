# ROADMAP MESIN VIRAL
> Checklist status semua item development — diupdate setiap item selesai.  
> Mulai: 4 April 2026 | Update terakhir: 8 April 2026

---

## STATUS PER ITEM

| # | Item | Status | Selesai |
|---|------|--------|---------|
| s81 | Telegram Notifikasi (success / QC fail / error) | ✅ DONE | 4 Apr 2026 |
| s82 | Regional Targeting Tier-1 di TrendRadar | ✅ DONE | 4 Apr 2026 |
| s83 | Loop Ending Video (xfade, disabled by default) | ✅ DONE | 4 Apr 2026 |
| s84a | Niche DB + Schedule Manager + Focus per Slot | ✅ DONE | 4 Apr 2026 |
| s84b | ChannelAnalytics — YouTube Analytics pull | ✅ DONE | 5 Apr 2026 |
| s84c | PerformanceAnalyzer + channel_insights | ✅ DONE | 5 Apr 2026 |
| s84d | Self-Learning NicheSelector feedback loop | ✅ DONE | 5 Apr 2026 |
| s85a | Niche visual_style + mood_priority config dari Supabase | ✅ DONE | 5 Apr 2026 |
| s85b | Music system config-driven (moods table, niche+mood query) | ✅ DONE | 5–6 Apr 2026 |
| s85c | LLM generate full cinematic visual prompts | ✅ DONE | 6 Apr 2026 |
| s86 | DALL-E 3 async fix (AsyncOpenAI context manager) + hapus visual_fallbacks dari retry | ✅ DONE | 7 Apr 2026 |
| s87 | Music fallback ordering fix — niche mood_priority sebelum keyword matches | ✅ DONE | 7 Apr 2026 |
| s88 | Fonts config-driven — fonts table Supabase + caption/hook title properties per tenant | ✅ DONE | 7 Apr 2026 |
| s89 | emotion_scoring_criteria config-driven — kolom baru di niches table, isi 4 niche | ✅ DONE | 7 Apr 2026 |
| s90 | Script quality: CLIMAX/CTA rewrite + niche-aware emotional_peak + retry feedback dengan skor | ✅ DONE | 7 Apr 2026 |
| s91 | Bug fixes: get_llm_provider Claude + CTR metric + video CTA terpotong + topic diversity inject | ✅ DONE | 8 Apr 2026 |
| 6 | BYO-CC Phase 1 — tenant_credentials table + enkripsi Fernet + mandatory validation | ⬜ TODO | — |
| 7 | BYO-CC Phase 2 — Dispatcher (ganti crontab hardcode per tenant) | ⬜ TODO | — |
| 8 | BYO-CC Phase 3 — Tenant Onboarding script (OAuth flow per tenant) | ⬜ TODO | — |
| 9 | **[URGENT]** Migrasi DALL-E 3 → gpt-image-1 (sebelum May 2026) | ⬜ TODO | — |
| 10 | Error Management Profesional — exceptions.py terpusat | ⬜ TODO | — |
| 11 | Analytics Isolation — youtube_channel_id per (tenant+channel) | ⬜ TODO | — |
| 12 | Multi-Channel per Tenant — channels table + dispatcher per channel | ⬜ TODO | — |

---

## CATATAN PER ITEM

### s86 — DALL-E 3 Async Fix + No Visual Fallbacks
- `ai_image.py` sekarang menggunakan `AsyncOpenAI` sebagai async context manager — fix `RuntimeError: Event loop is closed`
- Hapus `visual_fallbacks` dari retry attempt 3 — semua 3 attempt pakai DALL-E 3 dengan Claude rewrite
- Rejection feedback dari DALL-E 3 diakumulasi sebagai `rejection_history` → dikirim ke Claude per retry
- Jika 3 attempt gagal: scene di-skip, pipeline lanjut, Telegram notifikasi (via item s81)

### s87 — Music Fallback Fix
- Sebelumnya: keyword matches (dari script) diurut pertama → mood lintas niche bisa menang
- Sekarang: `niche_mood_priority` dari niches table diurut lebih dulu sebagai fallback, baru keyword matches
- Efek: universe_mysteries tidak akan mendapat musik `energetic` dari fun_facts

### s88 — Fonts Config-Driven
- Tabel `fonts` di Supabase: `font_name`, `r2_key`, `is_active`
- RLS policy ditambah di migration s88: anon key bisa SELECT fonts table
- `tenant_configs.caption_style` dan `hook_title_style` menyimpan font_name, size, color, bold, italic, border, alignment
- `video_renderer.py` download font dari R2, cache lokal di `logs/`

### s89 — Emotion Scoring Criteria Config-Driven
- Kolom `emotion_scoring_criteria` (TEXT) ditambah ke tabel `niches`
- Diisi 4 niche aktif: universe_mysteries (EXISTENTIAL AWE), dark_history (MORAL WEIGHT), ocean_mysteries (PRIMAL FEAR), fun_facts (IRRESISTIBLE URGE TO SHARE)
- `script_analyzer.py` pakai 3-tier priority: explicit criteria → derive dari voice_profile → default generic

### s90 — Script Quality Improvement
- `script_engine.py`: CLIMAX instruks "CAUSE emotion, don't describe" + 3 teknik konkrit + quality bar
- `script_engine.py`: CTA instruksi dirombak total — tidak ada CTA eksplisit, chemistry via resonance
- `script_engine.py`: FORBIDDEN list ditambah: "Follow", "Subscribe", "Like", "Hit the bell"
- `script_engine.py`: retry feedback menyertakan skor aktual + teknik konkrit per dimensi (bukan hanya nama dimensi)
- `script_analyzer.py`: scoring criteria semua 6 dimensi diperketat dengan threshold 80+ yang eksplisit

### s91 — Bug Fixes Bundle

**4 fix dalam 1 item, semua perubahan minimal dan terisolasi:**

1. **`get_llm_provider()` Claude support** — `tenant_config.py:228`
   - Tambah `from src.providers.llm.claude import ClaudeProvider`
   - Tambah `"claude": ClaudeProvider` ke dict `providers`
   - Tidak ada perubahan lain — ScriptEngine sudah handle Claude sendiri

2. **CTR metric fix** — `channel_analytics.py:321`
   - Ganti `cardClickRate` → `impressionClickThroughRate` di query metric Analytics API
   - `impressionClickThroughRate` sudah dalam decimal, `×100` tetap valid
   - Data langsung mengalir ke `top_hooks` dengan nilai real setelah 48 jam video publish

3. **Video CTA terpotong** — `video_renderer.py:570`
   - Ganti `audio_duration` → `total_duration` di pemanggilan `_create_clip_list()`
   - Clip list target: 89.8s → setelah xfade -2.0s → video 87.8s = matching audio
   - 0 perubahan di fungsi `_create_clip_list()` itu sendiri

4. **Topic diversity AI prompt** — `niche_selector.py`
   - Di `select()`: fetch `recent_topics` via `get_recent_topics()` SEBELUM AI call
   - Pass ke `_analyze_with_ai()` sebagai parameter baru `recent_topics`
   - Inject ke prompt sebagai blok "AVOID THESE ANGLES (recently covered)"
   - `_filter_duplicates()` TIDAK diubah — tetap jalan sebagai hard filter post-generation

### Item 9 — URGENT: gpt-image-1 Migration
- DALL-E 3 discontinue ~May 2026
- Langkah: research API spec → test kualitas → update `AI_IMAGE_MODELS` di `ai_image.py` → set default baru
- `ai_image.py` prompts sudah model-agnostic (tidak ada "DALL-E 3" hardcode di prompt)

### Item 6–8 — BYO-CC (Bring Your Own Cloud Console)
- Prerequisite: kesepakatan infrastruktur v1 sudah selesai (6 Apr 2026)
- LLM wajib: `anthropic_api_key` ATAU `openai_api_key`
- TTS wajib: `elevenlabs_api_key` ATAU `openai_api_key`
- Visual AI wajib: `openai_api_key` (DALL-E 3 / gpt-image-1)
- YouTube wajib: Google OAuth (GCP project milik tenant)
- Musik: platform-managed, tidak perlu API key tenant

---

## PRINSIP TIDAK BOLEH DILANGGAR

1. **Pipeline tidak pernah crash** — setiap fitur baru wajib wrapped try-except dengan fallback
2. **Config-driven** — tidak ada hardcode niche, threshold, font, atau API behavior di kode
3. **Backward compatible** — kode baru tidak merusak pipeline yang sudah jalan
4. **Supabase DDL** — selalu `ADD COLUMN IF NOT EXISTS` + `DEFAULT` yang aman
5. **Test lokal dulu** — validasi sebelum push ke VPS
6. **Commit per item** — 1 item = 1 commit + deploy + monitor 1 run produksi
