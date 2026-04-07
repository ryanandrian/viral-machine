# Self-Learning & Self-Improvement — Progress Checklist

> Pegangan bersama untuk memastikan mesinviral.com benar-benar smart, viral, dan terus berkembang.
> Update status setiap item seiring progress. Jangan mulai stage berikutnya sebelum stage sebelumnya ✅.

---

## Stage 1 — Tutup Feedback Loop (Kritikal)

### S1-A: Otomasi Data Pipeline
- [x] Cron harian: `fetch_analytics.sh` → `ChannelAnalytics.fetch_and_store()` (06:00 UTC)
- [x] Cron mingguan: `compute_insights.sh` → `PerformanceAnalyzer.compute_and_store()` (Senin 07:00 UTC)

### S1-B: ScriptEngine Baca Insights ✅
- [x] Load `channel_insights` terbaru di awal `ScriptEngine.generate()`
- [x] Inject `top_hooks` (CTR-ranked) ke prompt ScriptEngine (Claude & GPT)
- [x] Inject `content_type_perf` (retention-ranked) ke prompt
- [x] Inject `avoid_patterns` ke prompt (patterns dengan retention rendah)
- [x] Guard: jika grade `insufficient_data` → generate normal tanpa injection (no degradation)
- [x] Test live: ✅ 2026-04-07 — insights injected, smart focus aktif, pipeline SUCCESS

### S1-C: HookOptimizer Baca `top_hooks` ✅
- [x] Load `channel_insights` di awal `HookOptimizer.optimize()`
- [x] Tambah "formula ke-6": variasi dari hook historis CTR tertinggi channel
- [x] Guard: jika tidak ada insights → tetap pakai 5 formula existing (no degradation)
- [x] Test live: ✅ 2026-04-07 — hook optimizer berjalan (pipeline SUCCESS end-to-end)

---

## Stage 2 — Smart Default (Selaras DESIGN.md 8.D)

### S2-A: Smart Niche Selection (user tidak set niche) ✅
- [x] Jika insights tersedia (grade >= learning) → pilih niche dengan `niche_weight` tertinggi dari rotation list user
- [x] Diversity guard tetap aktif (dari Stage 1) — niche dominan tetap diblokir
- [x] Fallback ke round-robin jika grade `insufficient_data`
- [x] Test live: ✅ 2026-04-07 — `ocean_mysteries` weight=0.810 dipilih, diversity guard aktif, redirect ke `dark_history`

### S2-B: Smart Focus Selection (user tidak set focus) ✅
- [x] Jika focus kosong dan grade >= `optimizing` → derive smart focus dari `content_type_perf` + `top_topics`
- [x] Smart focus pakai bahasa "PREFERRED DIRECTION" (soft) — AI boleh deviate jika trending lebih kuat
- [x] User focus (eksplisit) tetap pakai bahasa "FOCUS CONSTRAINT" (hard)
- [x] Dedup tetap jalan untuk mencegah topik serupa diproduksi ulang
- [x] Test live: ✅ 2026-04-07 — smart focus derived: "Prioritize 'dark_history' content format (proven 100% avg retention)"

### S2-C: User Override Tetap Dihormati ✅
- [x] User set niche → S1-B & S1-C (script + hook learning) tetap jalan di balik layar
- [x] User set focus → insights tetap diinjek ke ScriptEngine, focus user dihormati sebagai hard constraint
- [x] Grade `insufficient_data` → semua berjalan normal, zero degradation
- [x] Test end-to-end: ✅ 2026-04-07 — full-auto pipeline SUCCESS, video published

---

## Stage 3 — Learning Evolution (Jangka Menengah)

### S3-A: Viral Score Weight Adaptif ✅
- [x] Migration s87: `videos.topic_scores` + `videos.insights_grade` + `tenant_configs.viral_score_weights`
- [x] ScriptEngine: embed `topic_scores` (5 dimensi) + `insights_grade` ke script output
- [x] SupabaseWriter + Pipeline: simpan field baru saat publish
- [x] `compute_viral_weights.py`: Pearson correlation 5 dimensi vs performance_score
      (avg_view_pct×0.30 + CTR×0.25 + subs_norm×0.25 + views_norm×0.15 + like_rate×0.05)
- [x] Gradual blending: n<20 → default, n=20–50 → blend, n≥50 → fully computed
- [x] NicheSelector `_get_blended_weights()` + `_calculate_viral_score(tenant_id)`
- [ ] Tambah cron bulanan untuk `compute_viral_weights.py` (di server produksi rad4vm)
- [ ] Test live: verifikasi weights berubah setelah n≥20 video dengan analytics

### S3-B: Performance Attribution ✅
- [x] `videos.insights_grade`: tag grade saat produksi
- [x] `compute_viral_weights.py`: attribution report pre vs post insights (avg performance score)
- [ ] Data siap untuk Dashboard tenant (DESIGN.md 8.B — roadmap berikutnya)

---

## Catatan Penting

- **Prinsip utama:** setiap improvement tidak boleh menurunkan kualitas untuk kondisi apapun (no degradation)
- **Guard wajib:** semua inject insights harus ada fallback jika data belum tersedia (grade `insufficient_data`)
- **User control:** insights adalah default smart behavior — user tetap bisa override via schedule config
- **No breaking changes:** interface `NicheSelector.select()` dan `ScriptEngine.generate()` tidak berubah dari luar

---

*Last updated: 2026-04-07*
*Status Stage 1: ✅ Done + Test Live PASSED (2026-04-07)*
*Status Stage 2: ✅ Done + Test Live PASSED (2026-04-07)*
*Status Stage 3: ✅ Done (cron bulanan perlu ditambah di server rad4vm)*
