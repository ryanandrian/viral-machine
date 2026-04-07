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
- [ ] Test live: pastikan script yang dihasilkan mencerminkan pola top_hooks historis

### S1-C: HookOptimizer Baca `top_hooks` ✅
- [x] Load `channel_insights` di awal `HookOptimizer.optimize()`
- [x] Tambah "formula ke-6": variasi dari hook historis CTR tertinggi channel
- [x] Guard: jika tidak ada insights → tetap pakai 5 formula existing (no degradation)
- [ ] Test live: pastikan hook historis masuk sebagai kandidat dan bersaing fair

---

## Stage 2 — Smart Default (Selaras DESIGN.md 8.D)

### S2-A: Smart Niche Selection (user tidak set niche)
- [ ] Jika `niche_id = NULL` di schedule → baca `niche_weights` dari `channel_insights`
- [ ] Pilih niche dengan weight tertinggi yang belum dipakai berlebihan (diversity guard tetap aktif)
- [ ] Fallback ke rotasi round-robin jika grade `insufficient_data`
- [ ] Test: channel dengan data insights memilih niche berdasarkan performa, bukan urutan

### S2-B: Smart Focus Selection (user tidak set focus)
- [ ] Jika `niche_focus = NULL` → gabungkan `top_topics` dari insights + sinyal TrendRadar
- [ ] Hindari fokus yang sudah diproduksi dalam lookback window (dedup tetap jalan)
- [ ] Output: focus string yang diinjek ke NicheSelector sebagai soft constraint
- [ ] Test: focus yang dipilih mesin relevan dengan tren + historis channel

### S2-C: User Override Tetap Dihormati
- [ ] Verifikasi: jika user set niche eksplisit → S1-B & S1-C tetap berjalan di balik layar
- [ ] Verifikasi: jika user set focus eksplisit → insights tetap diinjek ke ScriptEngine
- [ ] Verifikasi: tidak ada degradasi kualitas di mode custom vs mode auto
- [ ] Test end-to-end: 3 skenario (full-auto, niche-only, niche+focus)

---

## Stage 3 — Learning Evolution (Jangka Menengah)

### S3-A: Viral Score Weight Adaptif
- [ ] Desain schema: `viral_score_weights` di `tenant_configs` (per-channel override)
- [ ] Script bulanan: bandingkan predicted `viral_score` vs actual performance (views, CTR, subs)
- [ ] Algoritma penyesuaian weight: regression sederhana atau korelasi per dimensi
- [ ] Simpan weight baru ke DB, pipeline otomatis pakai weight terbaru
- [ ] Test: weight berubah setelah ada data cukup; default weight tetap untuk channel baru

### S3-B: Performance Attribution
- [ ] Tag setiap video di `videos` table: `insights_grade` saat produksi
- [ ] Query: bandingkan avg performa video pre-insights vs post-insights per channel
- [ ] Siapkan data untuk ditampilkan di Dashboard tenant (DESIGN.md 8.B — TBD)
- [ ] Test: angka attribution masuk akal dan tidak menyesatkan

---

## Catatan Penting

- **Prinsip utama:** setiap improvement tidak boleh menurunkan kualitas untuk kondisi apapun (no degradation)
- **Guard wajib:** semua inject insights harus ada fallback jika data belum tersedia (grade `insufficient_data`)
- **User control:** insights adalah default smart behavior — user tetap bisa override via schedule config
- **No breaking changes:** interface `NicheSelector.select()` dan `ScriptEngine.generate()` tidak berubah dari luar

---

*Last updated: 2026-04-07*
*Status Stage 1: 🔄 In Progress (S1-A ✅ S1-B ✅ S1-C ✅ — test live pending)*
*Status Stage 2: ⏳ Belum dimulai*
*Status Stage 3: ⏳ Belum dimulai*
