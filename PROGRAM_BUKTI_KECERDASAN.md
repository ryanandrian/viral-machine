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
