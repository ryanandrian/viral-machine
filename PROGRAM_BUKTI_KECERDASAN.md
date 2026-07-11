# 🧠📈 PROGRAM BUKTI KECERDASAN — real self-learning yang TERUKUR, TERASA, lalu TERJUAL

> **STATUS: PLAN (disetujui owner utk dilaksanakan; eksekusi per-fase tetap lewat gerbang kontrak: proposal rinci → ketok → validasi → izin deploy).**
> **Daftar kerja hidup = `SISA_KERJA_GO_LIVE.md` [B17]** (file ini = SPEC + tracker Plan-vs-Realisasi).
> **Bintang utara (owner, 2026-07-11):** *"MesinViral harus benar-benar smart — real self-learning & self-improvement, bukan fake. Channel semakin pintar tiap minggu → konten ber-view tinggi karena kecerdasan mesin. Ini yang dijanjikan dan dijual."*
> Dibuat 2026-07-11, di atas fondasi yang BARU diverifikasi malam itu (lihat §2).

---

## §0 ALASAN — kenapa rencana ini, kenapa urutan ini

**Masalah yang dijawab:** janji "semakin pintar tiap minggu" hari ini punya MESIN yang nyata (baru disehatkan total 2026-07-11) tapi belum punya BUKTI yang bisa ditunjuk. Tanpa pengukur, klaim kita setara klaim kompetitor palsu; dengan pengukur, klaim kita menjadi satu-satunya yang bisa dibuktikan pelanggan pada channel-nya sendiri.

**Kalibrasi jujur yang mendasari urutan (hasil analisa 2026-07-11):**
- Kepuasan tenant pada akhirnya hanya dibeli oleh **views yang naik** — bukan oleh dashboard.
- Dari 4 ide awal: *laporan mingguan* & *"mengapa" per-video* = **JENDELA** (membuat kecerdasan terasa; TIDAK menambah kecerdasan) · *eksperimen aktif* & *warisan platform* = **OTAK** (menambah kecerdasan; punya ongkos & syarat skala).
- **Kesalahan yang dilarang rencana ini:** memasang jendela saat pemandangan belum terbukti bagus (laporan mingguan pada channel yang menurun = mempertontonkan kegagalan tiap minggu = churn), dan menyebut jendela sebagai kecerdasan (= "fake smart" yang owner haramkan).
- Maka hukum urutannya: **UKUR dulu (internal) → BUKTIKAN kurva naik → baru PAMERKAN (jendela) → lalu PERCEPAT (otak aktif) → skala-kan (warisan platform).**

**Tingkat keyakinan (jujur, per fase):** F0 = 100% (tanpa syarat: murah, tak berisiko, prasyarat segalanya). F1 = yakin BILA gerbang G1 lulus. F2/F3 = yakin BILA syarat volumenya terpenuhi — keyakinan tanpa syarat pada fase bersyarat adalah over-claim.

---

## §1 HASIL YANG DIDAPAT SETELAH TEREALISASI (per fase, bahasa bisnis)

| Fase | Hasil untuk TENANT | Hasil untuk BISNIS (jualan) |
|---|---|---|
| **F0 Pengukur** | (belum terlihat tenant — internal) | Kita TAHU dengan angka apakah janji inti benar; bahan keputusan semua fase lain; deteksi dini bila loop melenceng |
| **F1 Jendela** | Merasakan mesin belajar tiap minggu (laporan) + melihat alasan tiap video (Runs) → percaya, betah, memamerkan | Diferensiasi demo brutal ("lihat cara mesin berpikir") + marketing organik dari screenshot laporan + churn turun |
| **F2 Eksperimen aktif** | Channel bervolume membaik LEBIH CEPAT dan pasti (sebab-akibat, bukan kebetulan) | Klaim "semakin pintar tiap minggu" jadi kepastian mekanis; parit yang tak bisa ditiru kompetitor template |
| **F3 Warisan platform** | Channel BARU pintar sejak lahir (tanpa masa buta) | Senjata konversi trial→bayar: "channelmu mewarisi kecerdasan seluruh platform"; makin banyak tenant = makin pintar = network moat |

---

## §2 ARSITEKTUR — hasil deep-dive 2026-07-11 (fondasi TERVERIFIKASI) + titik pasang tiap fase

**Rantai belajar 4-mata yang sudah hidup & teruji end-to-end (JANGAN diaudit ulang; bukti = memory self-learning entri ⭐ 07-11 + [B16]):**
```
[1 UKUR]   channel_analytics (kolektor) ──▶ video_analytics (snapshot harian per-video; retensi/watch/subs
           HIDUP kembali sejak fix scopes 0149 + rotasi ee9bc01; 205 video, 150 ber-retensi)
[2 HITUNG] performance_analyzer (per-VIDEO snapshot-terbaru, sejarah penuh) ──▶ channel_insights (per-channel)
           viral_weight_optimizer ──▶ tenant_configs.viral_score_weights (korelasi skor-topik ↔ performa nyata)
           RPC agregat 0148 (tertimbang volume) ──▶ dashboard & /insights (tot/avg); tab channel = per-channel
[3 PAKAI]  niche_selector (insights_block per-channel → prompt pemilihan topik) + script_engine (gaya naskah)
[4 ADAPT]  loop harian self_learning (mv-worker) mengulang 1-3 otomatis
```

**Titik pasang per fase (semua ADDITIVE — tidak mengubah rantai yang sudah diverifikasi):**

- **F0 Pengukur:** DB — RPC baru `get_channel_learning_curve(channel_id)`: agregasi MINGGUAN per-channel dari `video_analytics` snapshot-terbaru-per-video (pola 0056/0148 yang terbukti) di-bucket per minggu-publish video: `views/video, retensi rata2, subs-gain/video, n video`. NOL tabel baru (turunan murni). FE — kurva di `/insights` tab channel & admin (fase awal boleh admin-only). ⚠️ pagar: bandingkan KOHORT minggu-publish (bukan kalender-view) agar video lama yang terus menabung views tidak menipu kurva.
- **F1 Jendela:** (a) *alasan per-video* — `run_metadata.decision_reason`: pipeline MENYIMPAN 1 kalimat dari insights_block yang SUDAH dipakai selector (data ada, selama ini dibuang pasca-pakai) → kolom di Runs (FE) — dwibahasa; (b) *laporan mingguan* — 1 template baru di mesin email nurture yang SUDAH live (renewal sweep + `email.py`), isi dari RPC F0; toggle per-tenant + kill-switch `app_config.learning_report_enabled`. ⚠️ pagar anti-churn: bila kurva channel MENURUN ≥ ambang config → laporan memakai nada "yang sedang dipelajari mesin" (bukan rapor merah), atau tahan (config).
- **F2 Eksperimen aktif:** producer — slot eksperimen ber-BUDGET config (`experiment_ratio`, default 0; aktif per-channel HANYA bila `video/hari ≥ app_config.experiment_min_daily`); hipotesis dari `avoid_patterns`/bobot rendah (uji-ulang sadar) atau variasi hook-pattern; penanda `run_metadata.experiment` → dikecualikan dari rapor F1 & kurva utama F0 (jujur: ongkos belajar bukan kegagalan); evaluator mingguan mengadopsi pemenang via mekanisme bobot yang SUDAH ada (viral_score_weights / niche_weights). 
- **F3 Warisan platform:** agregator level-platform (service) merangkum POLA anonim per-niche lintas-tenant (nol data mentah tenant; hanya distribusi pola: hook-pattern × retensi) → tabel `platform_niche_priors` → `niche_selector` memakai prior HANYA saat channel `videos_analyzed < N` (cold-start), memudar otomatis seiring data channel sendiri. Isolasi per-channel/tenant yang diverifikasi 07-11 TIDAK disentuh — prior = READ tambahan, bukan kebocoran.

**Kepatuhan kontrak di semua fase:** nilai bisnis via `app_config` (nol hardcode) · dwibahasa Bi · fail-soft tanpa fallback senyap · setiap query tabel besar WAJIB pola paginasi/first-seen teruji (pelajaran 5 bug 2026-07-11) · validasi = ground-truth independen + per-WIDGET.

---

## §3 GERBANG ANTAR-FASE (hukum, bukan saran)

| Gerbang | Syarat lolos | Alasan |
|---|---|---|
| **G0 → mulai F0** | ketok owner fase F0 | — |
| **G1 → F1** | kurva F0 terisi **≥3 minggu** DAN tren sehat (naik/stabil) pada channel rujukan; owner melihat kurvanya sendiri | jendela hanya dipasang bila pemandangan terbukti; juga memberi waktu retensi pasca-fix 07-11 mengendap |
| **G2 → F2** | ada channel produksi `≥ experiment_min_daily` (config; usul awal 5/hari) + owner ketok budget eksperimen | eksplorasi butuh volume; channel kecil tak boleh membayar ongkos belajar |
| **G3 → F3** | ≥ N tenant aktif ber-analytics lintas niche (config; usul awal 5 tenant) | prior dari 1-2 channel = bias berbahaya, bukan kecerdasan |

---

## §4 RISIKO & MITIGASI (jujur di muka)

| Risiko | Mitigasi (di desain, bukan janji) |
|---|---|
| Kurva F0 ternyata DATAR/turun | Justru itulah gunanya F0 — ketahuan internal SEBELUM dijual; jadi umpan investigasi mesin, bukan aib publik |
| Laporan mingguan menyoroti channel yang jelek | Nada adaptif + ambang tahan-kirim (config) + toggle per-tenant |
| Video eksperimen kalah → tenant kecewa | Budget kecil ber-config, ditandai & dikecualikan dari rapor, hanya channel bervolume |
| Prior platform salah kaprah antar-audiens | Prior hanya cold-start + memudar otomatis + per-niche + gerbang G3 |
| Kebocoran data antar-tenant di F3 | Hanya agregat pola anonim; review khusus privasi sebelum ketok F3 |
| Kelas-bug "baca terpotong" kambuh | Pola paginasi/first-seen kini baku (CLAUDE.md §2.2b/§3.4); audit per-WIDGET wajib |

---

## §5 PLAN vs REALISASI (living tracker — isi SETIAP fase selesai+tervalidasi)

| # | Item | Lapisan | Gerbang | Status | REALISASI (commit + bukti) |
|---|---|---|---|---|---|
| F0.1 | RPC `get_channel_learning_curve` (kohort mingguan, pola 0056) | DB | G0 | ⬜ | |
| F0.2 | Kurva di /insights tab channel (+ agregat tenant di menu utama) | FE | G0 | ⬜ | |
| F0.3 | Validasi: angka kurva vs hitung-manual independen 2 channel | — | G0 | ⬜ | |
| F1.1 | `run_metadata.decision_reason` disimpan pipeline + kolom Runs (Bi) | BE+FE | G1 | ⬜ | |
| F1.2 | Template email "Laporan Kecerdasan Mingguan" (nurture; toggle+kill-switch+nada adaptif) | BE | G1 | ⬜ | |
| F1.3 | Validasi: email uji data nyata + laporan channel-menurun tertahan sesuai ambang | — | G1 | ⬜ | |
| F2.1 | Slot eksperimen ber-budget config + penanda + eksklusi rapor | BE | G2 | ⬜ | |
| F2.2 | Evaluator mingguan adopsi pemenang (via bobot eksisting) | BE | G2 | ⬜ | |
| F2.3 | Validasi: 1 siklus eksperimen nyata → keputusan adopsi terekam + reversible | — | G2 | ⬜ | |
| F3.1 | Agregator `platform_niche_priors` (anonim, per-niche) | BE+DB | G3 | ⬜ | |
| F3.2 | Selector pakai prior cold-start + peluruhan otomatis | BE | G3 | ⬜ | |
| F3.3 | Review privasi + validasi cold-start channel uji | — | G3 | ⬜ | |

### Changelog
- **2026-07-11** — dokumen dibuat (mandat owner "buatkan rencana 1 dokumen khusus plan-vs-realisasi"); fondasi = deep-dive & pembenahan total rantai belajar 2026-07-11 ([B16] + memory self-learning ⭐). Eksekusi F0 menunggu ketok.
