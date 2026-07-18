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

## §2b SPESIFIKASI UI/UX FE TENANT — di mana muncul, seperti apa, skop apa

> **ATURAN KONSISTENSI UI (owner, MENGIKAT):** nol library/ikon baru — nuansa WAJIB seragam dgn aplikasi yang ada:
> - **Ikon = Lucide SAJA** (keluarga yang sama dgn menu utama & semua halaman). Emoji pada wireframe di bawah = notasi sketsa; implementasi memakai padanan Lucide: 📈→`TrendingUp`, 🧠→`Brain` (sudah dipakai InsightsView), 🧪→`FlaskConical`, 📬→`Mail`, 🟢↑→`ArrowUp` + warna `var(--success)`.
> - **Primitives eksisting SAJA:** kelas `card/card-title/badge/btn/progress/segmented` + token CSS (`var(--brand)`, `--success`, dst) + komponen `Bi` dwibahasa.
> - **Chart mengikuti pola chart internal yang sudah ada** (bar div `ins-chart` / SVG ringan ala Gauge dashboard) — DILARANG menambah chart library baru.
> - **DWIBAHASA ID/EN WAJIB di SEMUA permukaan program ini** (aturan kerja §3.5, ditegaskan owner 2026-07-11): setiap label/judul/subjudul/empty-state/tooltip/toggle FE via komponen `Bi` · **email Laporan Kecerdasan Mingguan dua bahasa penuh** (pola `_bi()` email.py yang sudah baku) · teks "🧠 Mengapa" dirakit dari **fragmen ber-kode → FE menerjemahkan** (BUKAN kalimat bebas LLM satu bahasa) · pesan error API kirim KODE, FE yang menerjemahkan. **Satu teks satu-bahasa lolos = cacat, item belum selesai.**
>
> **HUKUM DUA SKOP (owner):** setiap elemen menyatakan skopnya eksplisit. **Per-channel** = tab "Kinerja mesin" di `/channels/[id]` (sumber: data channel itu saja). **Seluruh channel (tot/avg tertimbang volume, aturan 0148)** = menu utama `/insights` + kartu dashboard. Komponen DIBUAT SEKALI dan dipakai di dua skop via prop `scopeLabel` (pola `InsightsView` yang sudah live — anti-selisih antar-halaman).

### F0 — Kartu "Kurva Belajar" (komponen bersama, 2 penempatan)

**Penempatan 1 (per-channel):** `/channels/[id]` → tab **Kinerja mesin**, kartu PALING ATAS (di atas InsightsView).
**Penempatan 2 (seluruh channel):** `/insights` → tepat di bawah hero "Mesin sudah belajar dari N video", sebelum kartu-kartu insight.

```
┌──────────────────────────────────────────────────────────────────┐
│ 📈 Kurva Belajar — channel ini                     [Views│Retensi]│   ← segmented toggle metrik
│ Video buatan tiap minggu, makin pintar makin tinggi                │
│                                                                    │
│  views/video                                            ▄▄         │
│      ▂▂       ▄▄        ▆▆       ▅▅        ██          ██         │
│  ────W1───────W2────────W3───────W4────────W5──────────W6────     │
│                                                                    │
│  Minggu ini: rata-rata 412 views/video   🟢 ↑ 12% vs minggu lalu   │
└──────────────────────────────────────────────────────────────────┘
```
- **Definisi batang (anti-tipu):** KOHORT minggu-PUBLISH — "video yang DIBUAT minggu itu" (snapshot terbaru per video), bukan kalender-views; sehingga kurva naik = *keputusan mesin membaik*, bukan video lama menabung views.
- Toggle metrik: Views/video ↔ Retensi rata-rata (config `learning_curve_metrics`).
- Skop seluruh-channel: batang = gabungan tertimbang volume; subjudul "semua channel-mu".
- **Empty state** (channel baru/<2 minggu): *"Kurva muncul setelah 2 minggu pertama — mesin sedang mengumpulkan pelajaran."* (Bi).
- **Dashboard** (skop seluruh-channel, SANGAT ringkas): kartu Self-Learning yang ada +1 baris chip: `🟢 ↑12% vs minggu lalu` (klik → /insights). Tidak ada kartu baru di dashboard.

### F1a — "🧠 Mengapa video ini" (per-VIDEO ⇒ skop per-channel by nature)

**Penempatan 1:** `/runs/[id]` (detail run) — kartu penuh di bawah ringkasan:
```
┌──────────────────────────────────────────────────────────────────┐
│ 🧠 Mengapa mesin membuat video ini                                 │
│ Topik dipilih karena pola "pertanyaan-misteri" menahan penonton    │
│ rata-rata 74% di channel ini; hook meniru struktur 3 hook          │
│ terbaikmu; niche mengikuti bobot belajar terkini (Universe 39%).   │
└──────────────────────────────────────────────────────────────────┘
```
**Penempatan 2:** `/runs` (daftar) — ikon 🧠 kecil di ujung baris; hover/tap = tooltip kalimat pertama. TIDAK menambah kolom (tabel sudah padat; disiplin №3.6 — mobile aman).
- Sumber teks: `run_metadata.decision_reason` (disimpan pipeline dari insights_block yang MEMANG dipakai saat run itu — bukan karangan retrospektif). Run lama tanpa field → elemen tidak tampil (jujur, tanpa "N/A").
- Dwibahasa: disusun dari fragmen ber-kode → FE merangkai ID/EN (pola Bi standar, bukan teks LLM bebas 1 bahasa).

### F1b — "Laporan Kecerdasan Mingguan" (skop SELURUH channel, per-channel dirinci di dalamnya)

**Kanal:** email (mesin nurture yang sudah live). **Cermin in-app:** `/insights` kartu kecil "📬 Laporan minggu ini" (isi sama, agar yang tak baca email tetap melihat). **Toggle:** `/settings` → seksi baru "Notifikasi" (auto-save, pola dropdown/toggle standar §3.6) + kill-switch global admin.
```
Subjek: 📈 Channelmu makin pintar minggu ini — MesinViral
──────────────────────────────────────────────
Halo Riko,
Minggu ini mesin belajar dari 34 video di 2 channel-mu:
• RAD The Explorer  : 412 views/video (↑12%) · retensi 58% (↑4 poin)
  → Pelajaran: pola "pertanyaan-misteri" unggul — porsinya dinaikkan.
• Channel Kedua     : masih mengumpulkan data (minggu ke-1).
[Lihat kurva lengkap →]  (link /insights)
──────────────────────────────────────────────
```
- **Nada adaptif (pagar churn):** metrik turun ≥ ambang config → seksi channel itu memakai frasa "yang sedang dipelajari mesin dari penurunan ini", ATAU laporan ditahan (`learning_report_hold_on_decline`).

### F2 — jejak eksperimen yang TERLIHAT tenant (saat F2 aktif kelak)

- `/runs`: badge status tambahan `🧪 Eksperimen` (warna violet, Bi) pada run bertanda — jujur bahwa video itu uji sadar.
- `/runs/[id]`: kartu 🧠 menambah 1 kalimat: *"Video ini adalah eksperimen terkontrol: menguji [hipotesis]. Hasilnya menentukan arah belajar channel — dan TIDAK dihitung dalam rapor mingguanmu."*
- Kurva F0 & laporan F1b MENGECUALIKAN run eksperimen (tercantum di §2 arsitektur).

### Matriks penempatan (rangkuman satu layar)

| Elemen | `/channels/[id]` (per-channel) | `/insights` (seluruh channel) | Dashboard | `/runs` & detail | Email |
|---|---|---|---|---|---|
| Kurva Belajar | ✅ kartu penuh | ✅ kartu penuh (tertimbang) | chip delta 1-baris | — | angka ringkasnya |
| 🧠 Mengapa | — | — | — | ✅ tooltip + kartu | — |
| Laporan mingguan | — | cermin kartu kecil | — | — | ✅ utama |
| Badge 🧪 (F2) | — | — | — | ✅ | disebut dikecualikan |

## §2c UPDATE 2026-07-11 (2) — PENYEMPURNAAN F0 (poin owner: RAD sudah kaya konten; WAJIB dipahami sebelum eksekusi)

1. **Kurva TIDAK menunggu data baru** — RAD punya ±15 minggu sejarah (199 video sejak akhir Maret) → F0 menghasilkan 15 titik kohort SEJAK HARI PERTAMA dihitung.
2. **Garis penanda vertikal 11 Juli** ("mesin disehatkan") di kurva → eksperimen alami *sebelum vs sesudah*: sejarah = era mesin setengah-buta (bias snapshot + retensi mati sejak 24 Jun); bila self-learning sejati, minggu pasca-garis menanjak. Ini artefak bukti jualan terkuat.
3. **Anti bias-umur (metrik):** metrik UTAMA kurva = **retensi** (stabil terhadap umur video); views WAJIB **ber-jendela** ("views 7 hari pertama" per video, dihitung dari SEJARAH snapshot harian `video_analytics` yang tersedia ribuan baris — bukan views lifetime yang membuat kohort tua menang palsu). Kurva historis boleh datar/berisik = baseline "sebelum" yang sah, bukan kegagalan.
4. **Urutan eksekusi final (disepakati diskusi 2026-07-11 malam):** B17-**F0 = batch kecil PERTAMA** (1 RPC + 1 kartu dua-skop + garis penanda; sekali deploy) → lalu fokus penuh panduan tenant (2-3 mgg) → gerbang **G1 dievaluasi saat kurva PASCA-11-Jul ≥3 minggu** (bukan kurva total — sejarahnya sudah panjang; yang dinilai kesehatan tren era mesin-sehat).
5. Status ketok: **owner BELUM mengucapkan "mulai F0 program"** — jangan mulai kode tanpa itu.
6. **RITUAL ANTI-SALAH-PAHAM (WAJIB tiap fase, sebelum baris kode pertama):** setelah ketok fase & selesai bekal-baca §2d, eksekutor WAJIB menyerahkan **"PEMAHAMAN SAYA"** ke owner: (a) apa persisnya yang akan dibangun (bahasa bisnis), (b) file/tabel yang disentuh & yang TIDAK, (c) bentuk hasil akhirnya (rujuk wireframe §2b), (d) cara validasinya — lalu **TUNGGU konfirmasi owner**. Salah-paham tertangkap di sini = gratis; lolos ke kode = mahal. Menyerahkan proposal tanpa bagian "PEMAHAMAN SAYA" = belum memenuhi gerbang.

## §2d BEKAL-BACA WAJIB PRA-EKSEKUSI (gerbang §2.1 versi konkret — sesi eksekutor WAJIB membaca INI dulu, bukan cuma dokumen ini)

> Dokumen ini memuat 100% KEPUTUSAN, tapi bukan 100% DETAIL kode. Sebelum menulis satu baris untuk fase mana pun, baca sumber di bawah SAMPAI paham (uji diri: bisa menyebut bentuk data & guard-nya tanpa membuka ulang). Melewati daftar ini = pelanggaran §2.1.

| Sebelum item | WAJIB baca (kode/skema live) | Yang harus dipahami |
|---|---|---|
| F0.1 (RPC kurva) | `migrations/0056` + `0148` (pola latest-per-video & tertimbang + guard channel-nyata) · skema `video_analytics` (kolom: analytics_date, collected_at, fetched_at, avg_view_pct, published_at; **snapshot HARIAN per video** — views-berjendela-7-hari dihitung dari sejarah snapshot) · `migrations/0057` (pola return table RPC) | kenapa dedup wajib; cara kohort minggu-publish; auth.uid() scoping |
| F0.2 (kartu kurva) | `components/insights-view.tsx` UTUH (pola scopeLabel, guard empty ala `topNiche &&`, bar `ins-chart`, render % baris 111-127) · `channels/[id]/page.tsx:480-500` & `insights/page.tsx:20-32` (cara 2 skop memanggil komponen bersama) | komponen sekali-tulis dua-skop; kontrak nilai 0..1 utk %; empty-state |
| F1.1 (decision_reason) | `niche_selector.py:399-427` (_build_insights_block — sumber teks alasan yang NYATA dipakai) · `pipeline.py` titik tulis `run_metadata` (pola `video_title` 07-10) · `runs/page.tsx` & `runs/[id]/page.tsx` (struktur tabel & kartu detail) | simpan yang DIPAKAI run itu, bukan rekonstruksi; fragmen ber-kode utk Bi |
| F1.2 (laporan mingguan) | `email.py` (`_bi`, `_trial_recap` pola fail-soft+paginasi, `notify_*`) · `renewal.py:150-200` (pola sweep + anti-dobel via kolom penanda) · `app_config` pola knob + CFG_META admin | dua bahasa penuh; anti-dobel kirim; kill-switch & nada adaptif config |
| F2/F3 | (saat gerbangnya tiba) `producer` alur pemilihan topik + `viral_weight_optimizer` (pasca-P6) + `topic_scores` di `videos` | jangan sentuh sebelum G2/G3 |
| SEMUA fase | memory `project_self_learning_remediation_2026_06_28` entri 🌟+⭐ (rantai 4-mata + 5 bug kelas baca-terpotong) + `CLAUDE.md` §2.2b/§3.4 | pola paginasi/first-seen WAJIB tiap query; validasi kelengkapan + per-WIDGET |

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
| F0.1 | RPC `get_channel_learning_curve` (kohort mingguan, pola 0056) | DB | G0 | ✅ | `3c1fd76` migr **0150** APPLIED (izin owner); retensi = bacaan-valid-terakhir ≤100 (pagar loop-Shorts 1261% & snapshot era-buta — cakupan 150→194/206); views ber-jendela `learning_curve_window_days`; diuji live sbg tenant (emulasi JWT): RAD 15 mgg · isolasi tenant-lain 0 baris · anon ditolak |
| F0.2 | Kurva di /insights tab channel (+ agregat tenant di menu utama) | FE | G0 | ✅ | `3c1fd76` deployed OK 2026-07-11 13:22 (situs 200, bundle live ber-"Kurva Belajar"); `LearningCurveCard` dua-skop (/channels/[id] tab Wawasan + /insights via `curveSlot`) + chip delta dashboard + 3 knob ber-label admin; dwibahasa penuh; garis penanda dari `learning_curve_marker_date` |
| F0.3 | Validasi: angka kurva vs hitung-manual independen 2 channel | — | G0 | ✅ | SQL vs ground-truth Python independen **IDENTIK 100%** (RAD 15 mgg · MVT 1 mgg→empty-state · gabungan tenant) + audit per-widget (bug tinggi-bar tertangkap pra-rilis & fixed) + tsc/build 0 err |
| F1.1 | `run_metadata.decision_reason` disimpan pipeline + kolom Runs (Bi) | BE+FE | G1 | 🔀 | **DILEBUR ke §6 Lapis 2** (ketok K5 18-Jul): kode-alasan = keputusan analis yang MEMANG dipakai run itu |
| F1.2 | Template email "Laporan Kecerdasan Mingguan" (nurture; toggle+kill-switch+nada adaptif) | BE | G1 | ⬜ | TETAP di sini (tidak dilebur) — menunggu G1 |
| F1.3 | Validasi: email uji data nyata + laporan channel-menurun tertahan sesuai ambang | — | G1 | ⬜ | TETAP di sini — menunggu G1 |
| F2.1 | Slot eksperimen ber-budget config + penanda + eksklusi rapor | BE | G2 | 🔀 | **DILEBUR ke §6 Lapis 2** (ketok K5): slot eksperimen = keputusan analis ber-tanda, tanpa video ekstra |
| F2.2 | Evaluator mingguan adopsi pemenang (via bobot eksisting) | BE | G2 | 🔀 | **DILEBUR ke §6 Lapis 2** — "bobot eksisting" viral_score_weights terbukti fitur-hampa (§6b); adopsi pemenang = hakim mekanik buku keputusan |
| F2.3 | Validasi: 1 siklus eksperimen nyata → keputusan adopsi terekam + reversible | — | G2 | 🔀 | **DILEBUR ke §6** fase A2 (vonis hakim vs ground-truth) |
| F3.1 | Agregator `platform_niche_priors` (anonim, per-niche) | BE+DB | G3 | 🔀 | **DILEBUR ke §6 Lapis 3** (ketok K6: boleh dari ≥1 channel niche katalog, label keyakinan-rendah; agregat = VONIS, bukan data mentah) |
| F3.2 | Selector pakai prior cold-start + peluruhan otomatis | BE | G3 | 🔀 | **DILEBUR ke §6 Lapis 3** (prior masuk dosir analis, memudar by videos_analyzed) |
| F3.3 | Review privasi + validasi cold-start channel uji | — | G3 | 🔀 | **DILEBUR ke §6** fase W1 (bukti-selesai memuat uji isolasi privasi) |

---

## §6 🧠 PROPOSAL EVOLUSI ARSITEKTUR — "MESIN CERDAS 3-LAPIS" (dibuat 2026-07-18)

> **STATUS: ✅ DIKETOK OWNER 2026-07-18 — K1–K6 SEMUA disetujui sesuai usulan** (K1 arsitektur+urutan fase ✓ · K2 dua-sinyal completion+loop_factor ✓ · K3 LLM analis=BYOK tenant ✓ · K4 mode bayangan 2 minggu ✓ · K5 rekonsiliasi dokumen ✓ [dieksekusi di commit ini] · K6 warisan boleh dari 1 channel utk niche katalog ber-label keyakinan-rendah ✓). Mandat pengiring owner: haram asumsi liar setitik pun · haram ranjau/bug baru · tuntas sampai akar · world-class.
> Bagian ini MENYERAP F1.1/F2/F3 tracker §5 (ditandai 🔀), MENGOREKSI premis B11-2.2, dan MEMATRIKAN keputusan Audisi Niche. **Eksekusi per-fase tetap lewat ritual §2c.6: bekal-baca → "PEMAHAMAN SAYA" → konfirmasi owner → kode. Fase berikutnya = M1.** Sesi pasca-compaction: baca §6 ini SEBELUM menyentuh apa pun terkait kecerdasan.

### §6a KEPUTUSAN OWNER TEREKAM 18-Jul (ini SUDAH keputusan, bukan proposal)
1. **Target tenant = MONETISASI YouTube** (subscriber + akumulasi tontonan), bukan sekadar view.
2. **Dua tipe channel, mesin wajib melayani keduanya:** (a) **fixed** — 1 channel 1 niche pamungkas sejak awal (kecerdasan bekerja DI DALAM niche); (b) **multi-niche random** — pool niche.
3. **Lifecycle AUDISI utk tipe (b):** acak rata HANYA di fase awal (eksplorasi, data belum ada) → data matang: produksi MENGERUCUT ke pemenang → mesin MEREKOMENDASIKAN fokus; **TENANT yang mencabut niche kalah** (aksi milik tenant, reversible; mesin tak pernah auto-cabut).

### §6b FONDASI BUKTI 18-Jul (semua terverifikasi kode+DB live+probe API — JANGAN re-audit)
- **`viral_score_weights` = fitur HAMPA (premis B11-2.2 GUGUR):** korelasi 5 dimensi `topic_scores` (tebakan LLM, sd 2,4–5,7, mean 70–90) vs hasil nyata |r|≤0,24 pada n=130 RAD; dalam-1-niche (n=39) pun nol; hasil (Y) justru bervariasi besar (views 5–929, retensi sd 23,6) → bukan Y datar, bukan pencampuran niche: **fiturnya sendiri tanpa informasi**. Bobot live = rata 0,2 (semua korelasi ≤ lantai 0,05). Per-channel-isasi item ini = sia-sia; jalan perbaikan = GANTI fitur dgn atribut nyata (Lapis 1).
- **`niche_weights` BENAR tapi TAK DIPAKAI:** formula subs-first (`performance_analyzer.py:221`) selaras monetisasi; teruji bebas-perancu (semua 211 snapshot-terbaru segar 17–18 Jul; kohort bulan-publish 4/4: dark_history KALAH konsisten 0,09/0,20/0,62/0,26 subs/video; universe [.393] vs fun_facts [.307] BELUM terpisah statistik — konvergensi memang harus bertahap). Konsumen produksi = NOL (picker mode-random acak rata + hindari 1–2 terakhir, `producer.py:103`; bobot live universe .393/fun .307/ocean .190/dark .110 = persis proporsi subs 64/50/31/18).
- **Loop Shorts >100%:** 24 video RAD (maks 1261%); cap-100 (`performance_analyzer.py:355`) TIDAK membalik urutan juara hari ini (monoton) — kerugian nyata = resolusi hilang di atas 100 + tampilan tak konsisten (`top_hooks` menyimpan & menampilkan MENTAH 102,5%). Probe kurva membuktikan watchRatio>1 = tonton-ulang nyata. `top_hooks` diurut CTR→fallback VIEWS (bukan retensi) → tak terdistorsi loop. `avoid_patterns` kosong = jujur (tak ada jenis konten <40%).
- **⭐ KURVA RETENSI PER-MOMEN = TERSEDIA & TERBUKTI (probe 18-Jul, jalur kode kita):** YouTube Analytics API laporan Audience Retention — 100 titik/video (`elapsedVideoTimeRatio`), metrik `audienceWatchRatio` + `relativeRetentionPerformance` (pembanding vs video YouTube sedurasi — gratis) + `startedWatching/stoppedWatching`; syarat 1 request = 1 video; scope `yt-analytics.readonly` **SUDAH ada di kedua koneksi ryan** (tanpa consent ulang). Probe: `MYNPEh1cRYk` (1911v, avg 42,4%) → hook hebat (watchRatio 1,24 di awal) tapi kabur massal t=0,05→0,25 (1,17→0,45) = pelajaran craft yang rata-rata tak pernah ajarkan; `mkY_T6aUsc8` (102,5%) → watchRatio>1 sepanjang paruh awal = loop nyata; video muda 33v (2 hari) → 0 titik (kurva butuh umur/views → ambil ≥3 hari, ambang teruji saat implementasi).
- **Rantai insight→prompt→ranking per-channel = SEHAT** (satu-satunya jalur belajar yang bekerja; JANGAN dirombak — 3 lapis di bawah = ADDITIVE).

### §6c HUKUM DESAIN (mengikat semua lapis)
1. **Fakta & penalaran dipisah mati:** mekanik MENGUKUR → LLM MEMUTUSKAN → mekanik MENGADILI. LLM tak pernah menilai dirinya sendiri (LLM pandai berdongeng dari derau).
2. **Additive total:** rantai 4-mata terverifikasi TIDAK dirombak; semua = tabel/blok baru menempel.
3. Config-driven penuh (kenop lahir lengkap ber-label admin, CLAUDE.md §3.3) · gagal-jujur tanpa fallback senyap · dwibahasa via fragmen ber-kode · per-channel sejak lahir.
4. **Hakim tertinggi = Kurva F0** (bukan klaim LLM, bukan klaim Claude).
5. Unit belajar = **pasangan KEPUTUSAN–HASIL** (bukan data mentah): mesin belajar dari keputusannya sendiri.

### §6d DESAIN 3 LAPIS
**LAPIS 1 — MATA (kurva retensi per-momen; fondasi semua lapis):**
- DB: tabel baru `video_retention_curves` — video_id/channel_id/tenant_id, 100 titik (JSONB), `relative_retention_performance`, + fitur turunan MEKANIK: `hook_hold` (daya tahan awal), `mid_exit` (titik kabur massal), `loop_factor` (porsi tonton-ulang), `end_ratio`.
- BE: kolektor di cadence self_learning — hanya video umur ≥ `retention_curve_min_age_days` (config, usul 3) yang belum ber-kurva; 1 req/video; idempoten; fail-soft; pola paginasi baku. Backfill sejarah RAD sekali jalan (bahan Lapis 3 + validasi).
- Termasuk: eksekusi VONIS LOOP (K2) — usulan: DUA SINYAL terpisah `completion` (cap 100) + `loop_factor`; sekalian konsistenkan tampilan 102,5%.
- TIDAK disentuh: pipeline produksi/publisher/QC/analyzer eksisting. FE: tidak ada (ukur dulu, pamerkan belakangan).

**LAPIS 2 — OTAK ANALIS + BUKU KEPUTUSAN (jantung):**
- Siklus per channel (config, usul mingguan): DOSIR fakta mekanik (kohort mingguan · subs/niche bebas-perancu · fitur kurva per jenis-konten/pola-hook · riwayat keputusan lalu + VONISNYA) → LLM ANALIS → **KEPUTUSAN TERSTRUKTUR menu-tertutup ber-batas**: arah topik (maks 3) · target pola hook ber-budget · geser campuran jenis konten (maks ±20%) · campuran niche (HANYA channel random-mode, dalam aturan audisi §6a.3) · slot eksperimen sadar · rekomendasi fokus (HANYA saran ke tenant) — semua WAJIB + PREDIKSI terukur.
- Eksekusi: arahan aktif masuk prompt (blok baru sejajar insights_block) + campuran produksi digeser TERBATAS. **HAKIM MEKANIK** siklus berikutnya: prediksi vs angka nyata → vonis MENANG/KALAH/BELUM-JELAS → tabel `channel_decisions` (keputusan + kode-alasan dwibahasa + prediksi + vonis + angka).
- Pagar: **MODE BAYANGAN dulu** (analis mencatat, TIDAK mengubah produksi; owner review mutu → baru ketok LIVE) · kill-switch global + toggle per-channel · menu tertutup.
- MELEBUR (tidak dibangun 2×): **F2** (slot eksperimen = keputusan ber-tanda, dikecualikan rapor) · **F1a** (kode-alasan = "mengapa video ini") · **audisi konvergensi/fokus** (analis merekomendasikan, mekanik membatasi, tenant memutuskan) · **pensiun formula fitur-hampa** (koreksi B11-2.2).
- Biaya: ±1 panggilan LLM/channel/minggu (kecil). Sumber kunci = K3.

**LAPIS 3 — WARISAN (channel baru tak lahir buta):**
- Agregator merangkum **VONIS** (bukan data mentah/topik — aman privasi) lintas-channel per niche katalog → `platform_niche_priors`. Channel baru (`videos_analyzed < N` config): dosir memuat seksi "warisan platform" berlabel jujur, memudar otomatis seiring data sendiri. Benih hari-1 = korpus RAD (200+ video + kurva backfill M1) utk universe/dark/fun/ocean.

### §6e FASE, BIAYA, GERBANG, BUKTI-SELESAI
| Fase | Isi | Biaya | Gerbang | Bukti-selesai |
|---|---|---|---|---|
| M1 | Lapis 1 kolektor + fitur turunan + backfill RAD | ±1 sesi | Ketok K1 | **✅ TUNTAS 2026-07-18 — cakupan 100,0% (205/205 video eligible RAD: 161 ok + 44 empty-tercatat, kering 6 putaran)** · fitur 3 video spot-check IDENTIK vs hitung manual independen · kurva byte-cocok probe pagi · 2 error transien Google-500 ter-retry otomatis · uji permanen `tests/test_retention_curves.py` **12/12** + regresi auth-invalid 10/10 + py_compile/import + tsc/next-build FE lulus · migr **0171** APPLIED (RLS tertutup 0-policy; 4 kenop + kartu admin "Mata Mesin — Kurva Retensi"). Wawasan perdana mata-baru: hook RAD rata2 DITONTON ULANG (hook_hold 1,38; 159/161 video ber-loop) — kebocoran di BADAN video (end_ratio 0,38). **✅ DEPLOYED PRODUKSI 2026-07-18 (izin owner "deploy batch M1"): BE OK 16:36 (mv-worker/webhook active, health=200) + FE OK 16:53 (situs=200), commit `5a6c463`; kolektor terbukti hidup di log produksi 16:37 (idempoten: eligible=0/final=153 — cocok persis kondisi akhir backfill); 0 error ber-timestamp pasca-deploy; nol run produksi di jendela deploy** |
| M2 | Vonis loop (dua-sinyal) + konsistensi tampilan | ±½ sesi | Vonis K2 | **✅ TUNTAS LOKAL 2026-07-18:** completion (cap 100) dipatri di SUMBER (`_compute_top_hooks`/`_compute_top_topics`); loop_factor terpisah = M1. Uji permanen `tests/test_analyzer_completion_cap.py` **3/3** (cap + ranking hooks by-views & topik by-composite TAK berubah + avoid_patterns utuh) + regresi 22/22 · recompute RAD via kode produksi: **0 nilai >100 tersisa** di JSON; `niche_weights` identik (nol regresi) · FE tak disentuh (sudah ber-cap defensif — dugaan awal salah, dikoreksi jujur di §6e2). **⛔ Sisa: izin DEPLOY BE** (tanpa deploy, loop harian worker menulis mentah lagi) |
| A1 | `channel_decisions` + dosir + analis MODE BAYANGAN | ±1–1,5 sesi | M1 done | Dosir valid vs data live · keputusan lolos skema · NOL efek produksi |
| A2 | Review owner bayangan → wiring LIVE + hakim mekanik | ±1 sesi | Ketok pasca-review (K4) | Arahan terbukti di prompt run nyata · vonis hakim benar vs ground-truth |
| W1 | Warisan: agregator + cold-start + benih RAD | ±1 sesi | ≥X vonis (config) + K6 | Channel-uji baru menerima prior berlabel · isolasi privasi teruji |
Administrasi tiap fase: rekonsiliasi dokumen ini + `SISA_KERJA` + memory DI COMMIT YANG SAMA (§3.7). TIDAK disentuh: pipeline inti, program durasi, error-mgmt, partner, DNA niche, FE tenant (sampai jendela pasca-G1).

### §6e2 🦴 DAFTAR SAPU FOSIL TERIKAT-FASE (perintah owner 18-Jul: "jangan meninggalkan fosil setitikpun BE/DB/FE") — WAJIB dieksekusi di fase tercantum, bukan "nanti"
| Fosil | Lokasi (terverifikasi 18-Jul) | Disapu di fase |
|---|---|---|
| Nilai retensi mentah >100 bocor dari sumber | **✅ DISAPU M2 18-Jul (koreksi lokasi setelah bekal-baca: FE TERNYATA sudah cap `Math.min(100)` — kebocoran nyata = JSON tersimpan → prompt LLM `_build_insights_block` "1261% watched").** Fix di SUMBER: `_compute_top_hooks`+`_compute_top_topics` simpan completion (cap 100) → prompt & FE konsisten otomatis; `avoid_patterns` SENGAJA tak diubah (mengubah perilaku belajar = di luar lingkup) | **M2 ✅** |
| Penulis formula fitur-hampa | `src/analytics/viral_weight_optimizer.py` + panggilan `self_learning.py` (blok VIRAL-WEIGHTS) | **A2** (saat otak analis LIVE menggantikan) |
| Pembaca bobot di produksi | `niche_selector._get_blended_weights` + `_calculate_viral_score` (sumber bobot diganti/disederhanakan) | **A2** |
| FE-tenant 3 titik pembaca `viral_score_weights` | kartu "Formula yang dipelajari mesin" `insights-view.tsx` · fetch di `channels/[id]/page.tsx` · breakdown `runs/[id]/page.tsx` | **A2** (ganti ke sumber baru/buku keputusan — bukan dihapus diam-diam, diganti yang jujur) |
| Kolom DB `tenant_configs.viral_score_weights` | tenant_configs | **Pasca-A2**, drop = IREVERSIBEL → **ketok owner terpisah** (§2.3d) |
| Aturan no-hardcode M1 | Semua nilai kebijakan (umur ambil/refresh/limit/menyerah) = `app_config` ber-kartu admin; definisi matematis fitur (mis. jendela hook) = konstanta ber-nama + ber-uji di modul, BUKAN nilai bisnis | M1 |

### §6f RISIKO JUJUR
| Risiko | Mitigasi ter-desain |
|---|---|
| LLM berdongeng dari derau | Menu tertutup + prediksi wajib + hakim mekanik + mode bayangan |
| Kurva tak tersedia video muda/sepi | Kebijakan umur-ambil config + horizon vonis realistis |
| Keputusan analis memburukkan channel | Batas geser kecil + kill-switch + Kurva F0 sbg alarm |
| Tak menaikkan view secepat harapan | Prediksi-vs-vonis = laju belajar TERUKUR & jujur (tak ada jaminan viral — yang dijual: laju belajar terbukti) |

### §6g ⭐ DAFTAR KETOK — ✅ SEMUA DIKETOK OWNER 2026-07-18 ("ketok K1-K6 semua sesuai usulan anda")
- **K1 ✅** — Arsitektur 3-lapis + urutan fase §6e: DISETUJUI.
- **K2 ✅** — Vonis loop: **(A) dua-sinyal `completion` (cap 100) + `loop_factor`** — DIKETOK.
- **K3 ✅** — Kunci LLM analis: **(A) BYOK tenant** — DIKETOK.
- **K4 ✅** — Mode bayangan: **2 minggu** — DIKETOK.
- **K5 ✅** — Rekonsiliasi dokumen: DIKETOK & DIEKSEKUSI (tracker §5 ditandai 🔀; B11-2.2 dikoreksi di `MULTI_YOUTUBE_CHANNEL_ARCHITECTURE.md` + `SISA_KERJA`; audisi terpatri §6a).
- **K6 ✅** — Warisan boleh lahir dari **≥1 channel utk niche katalog, ber-label keyakinan-rendah** (gerbang G3 lama direvisi) — DIKETOK.

### Changelog
- **2026-07-18 (5)** — **M2 (dua-sinyal K2) DIBANGUN + TERVALIDASI LOKAL; ⛔ BELUM DEPLOY (§5.0: "tuntaskan" ≠ izin deploy — menunggu izin eksplisit batch).** Completion cap-100 dipatri di SUMBER analyzer; kebocoran nyata = prompt LLM (dugaan FE salah → dikoreksi §6e2); uji 3/3 + regresi 22/22; recompute RAD 0 nilai >100; niche_weights identik. Tanpa deploy BE, loop harian menulis mentah lagi (recompute lokal akan tertimpa) — deploy = penuntas.
- **2026-07-18 (4)** — **M1 ✅ DEPLOYED PRODUKSI** (izin owner): BE OK 16:36 + FE OK 16:53 (`5a6c463`); kolektor hidup di log produksi (idempoten); 0 error baru; kenop global-platform dikonfirmasi ke owner (by-design: kebijakan operasional + kuota API per-project kita). Berikutnya: ritual §2c.6 utk M2 (dua-sinyal loop, sentuh FE tenant) & A1 (analis bayangan).
- **2026-07-18 (3)** — **M1 (Lapis 1 MATA) DIBANGUN + BACKFILL RAD TUNTAS + TERVALIDASI 100%** (mandat "lanjutkan M1, kerjakan tuntas, backfill RAD sekalian"). Kolektor `retention_curves.py` (per-channel, per-identitas koneksi) + migr 0171 APPLIED + 4 kenop ber-kartu admin + uji 12/12 + cakupan 205/205 + fitur identik-manual. ⛔ BELUM DEPLOY BE (menunggu izin owner). Detail = §6e baris M1.
- **2026-07-18 (2)** — **§6 DIKETOK PENUH (K1–K6 sesuai usulan) + rekonsiliasi K5 dieksekusi** (tracker §5 F1.1/F2/F3 → 🔀; B11-2.2 & SISA_KERJA dikoreksi). Mandat pengiring: nol asumsi, nol ranjau baru, tuntas ke akar, world-class. Berikutnya: ritual §2c.6 utk fase M1 (bekal-baca → PEMAHAMAN SAYA → konfirmasi → kode).
- **2026-07-18** — **§6 PROPOSAL "Mesin Cerdas 3-Lapis" dituangkan LENGKAP (menunggu ketok K1–K6)** + §6a keputusan owner (monetisasi, 2 tipe channel, audisi 3-fase) + §6b fondasi bukti (formula fitur-hampa; niche_weights benar-tapi-tak-dipakai; probe kurva retensi SUKSES — scope sudah ada). Pemicu: teguran owner "proposal detail tapi tak dituangkan ke dokumen = hilang saat compaction".
- **2026-07-11 (2)** — **F0 TUNTAS+DEPLOYED** (ketok owner "mulai F0 program" → ritual PEMAHAMAN SAYA → izin "terapkan migrasi 0150 & deploy"). Kurva 15 minggu RAD LIVE hari pertama; garis penanda 11-Jul tampil (minggu pasca-garis = era belajar penuh, belum berkohort). 2 keputusan metrik dari realita data (dicatat jujur): retensi = bacaan-valid-terakhir (snapshot era-buta ≠ retensi 0) + pagar ≤100% (Shorts loop s/d 1261%). **Berikutnya: fokus panduan tenant; G1 dievaluasi saat kurva pasca-11-Jul ≥3 minggu.**
- **2026-07-11** — dokumen dibuat (mandat owner "buatkan rencana 1 dokumen khusus plan-vs-realisasi"); fondasi = deep-dive & pembenahan total rantai belajar 2026-07-11 ([B16] + memory self-learning ⭐). Eksekusi F0 menunggu ketok.
