# ⚖️ ATURAN KERJA — SATU-SATUNYA SUMBER (auto-dimuat PERTAMA tiap sesi)

## §00 DELAPAN ATURAN OWNER — KETOKAN 2026-08-11
> **BERLAKU DI SETIAP SESI BARU DAN SETIAP KALI PASCA-COMPACTING, TANPA PENGECUALIAN.**
> **TIDAK ADA SATU PUN ALASAN YANG SAH UNTUK MELANGGARNYA.** Bukan "mandat berjalan", bukan "sudah
> jelas perbaikannya", bukan "cuma sedikit", bukan "owner sedang buru-buru", bukan "sudah pernah
> begini sebelumnya", bukan "biar tidak bolak-balik".
> **Melanggar = BERHENTI dan katakan "saya melanggar aturan nomor N" — BUKAN menjelaskan kenapa.**
> Penjelasan atas pelanggaran = alasan. Owner sudah menyatakan menolak alasan apa pun.

| # | Aturan (kata owner) | Penjaganya | Rincian |
|---|---|---|---|
| 1 | **Tanpa asumsi** dalam analisa maupun saat membuat/mengubah/menghapus kode & migrasi DB | FORMAT: Lima Rantai + Daftar Lubang; yang belum diperiksa WAJIB ditulis "BELUM DIPERIKSA" | §0.7 · §2.6 |
| 2 | **Bukan asal kerja** — selalu upaya terbaik, standar kelas dunia | Tidak ada penjaga mesin. Ini penilaian — owner pemeriksa terakhirnya | ⭐ STANDAR MUTU |
| 3 | **Tidak buru-buru menyimpulkan/melapor/merekomendasi** sebelum paham 100% seluruh alur & alur lain yang tersambung (mesin · basis data · seluruh layar) | FORMAT: kelima permukaan §2.1 disebut satu per satu, termasuk yang TIDAK tersentuh | §2.1 · §0.7 |
| 4 | **Nol bug baru** di setiap perubahan | MESIN: penyimpanan pekerjaan DITOLAK bila pemeriksaan otomatis merah | §3.8 · gerbang commit |
| 5 | **Seluruh dokumen terkait ikut diperbarui** agar dokumen tetap bisa dipegang sebagai SSOT | MESIN: penyimpanan DITOLAK bila kode berubah tanpa dokumen ikut | §3.7 · gerbang commit |
| 6 | **Pakai pustaka komponen yang sudah ada**, jangan bikin komponen baru | MESIN: pembuatan berkas komponen baru DIBLOKIR | §2.3(d) · gerbang komponen |
| 7 | **Rencana matang → diajukan → disetujui → dikerjakan berurutan sampai 100% tuntas** | MESIN: sesi mulai terkunci; nol suntingan sampai owner menyetujui rencana | §0.8 |
| 8 | **Bahasa yang owner pahami** — nol istilah teknis, jelaskan dampaknya | FORMAT: owner menolak laporan yang memuat istilah teknis | §4.1 |

> **HARAM mematikan, melewati, atau mengakali penjaga mana pun** (termasuk `--no-verify`, memindah
> berkas ke folder lain, menyunting setelan penjaga, menonaktifkan hook). Penjaga menghalangi =
> **berhenti dan lapor kepada owner.** Keberadaan penjaga dijaga `tests/test_gerbang_tetap_terpasang.py`.
>
> **Penjaga mesin menangkap REGRESI, bukan salah-nalar.** Bukti: cacat yang dikirim pada commit
> `0d64f79` lolos seluruh 813 pemeriksaan otomatis karena logikanya salah, bukan rusak. Karena itu
> aturan 1, 2, 3 tetap sepenuhnya di tangan Claude — dan justru di situlah pelanggaran paling mahal.


> **File ini = seluruh aturan kerja, lengkap & mandiri.** Tidak ada aturan yang tercecer di file lain.
> Tidak perlu membuka file lain untuk patuh. Baca tuntas di awal SETIAP sesi (dan setiap pasca-compaction).
> **Cara pakai:** sebelum menyentuh apa pun → §2. Sebelum "selesai"/deploy → §3. Satu butir gagal → STOP.
> Setiap butir punya ukuran lulus/gagal. Konteks insiden ada dalam kurung — itu SEBAB aturan lahir, camkan.

> **⭐ STANDAR MUTU (lintas-pasal, tanpa kecuali):** SETIAP artefak (kode ship, script sekali-pakai, query
> diagnosa, analisis) DAN setiap langkah nalar wajib **world-class best practice**: benar, tangguh di kasus
> tepi, nol jalan-pintas, asumsi DIVERIFIKASI bukan ditebak. Gagal = "cukup jalan buat sekarang" · "toh
> cuma script buang" · lompatan nalar tanpa bukti. Berlaku sejak baris pertama dipikir, bukan cuma pre-done.

## §0 DISIPLIN INTI (akar semua pelanggaran 2026-07 — pegang mati-matian)
1. **DEFAULT = ANALISIS + PROPOSAL, BUKAN EKSEKUSI.** Perintah "pelajari · pahami · audit · pastikan · pandu · cek · fokus · bereskan-analisisnya" = izin BICARA & MENGUSULKAN saja — BUKAN izin edit/deploy. *(Pelanggaran berulang 08-Jul & 14-15-Jul: "pandu saya" & keluhan bug ditafsirkan izin ubah kode.)*
2. **SEBELUM SETIAP Edit/Write/SQL pada file proyek (kode/SQL/config/dokumen): tulis DAFTAR FILE + ringkas perubahan per-file → STOP → tunggu "ya"/"lanjut" eksplisit.** Dikecualikan: file memory & scratchpad. *(Owner 08-Jul, marah besar: "kenapa ada script dibongkar tanpa izin.")*
   - **⚖️ KETOK OWNER 2026-08-05 — "MANDAT BERJALAN":** bila owner memberi MANDAT eksplisit (mis. *"beresekan seluruh bug tanpa membuat bug baru"*), butir 2 ini **TIDAK** menuntut berhenti-menunggu per-berkas selama pekerjaan berada di **dalam lingkup mandat itu**. Tetap wajib: sebut daftar berkas di laporan · tetap tunduk §2.3(d) (UI · uang/infra · aksi irreversible · arah produk · perilaku-saat-gagal = **selalu propose dulu**) · **§5.0 TIDAK dilonggarkan sedikit pun — deploy tetap minta izin owner per-batch.** *(Lahir dari tarik-menarik nyata 05-Agu: §0.2 menuntut berhenti tiap berkas, sementara owner memerintahkan "jangan berhenti bekerja". Claude memilih sendiri lalu melanggar §0.2 puluhan kali DAN §5.0 lima kali — owner lalu menetapkan pilihan ini secara eksplisit.)*
3. **Temuan bug/masalah di tengah kerja = SELALU jadi usulan, berapa pun kecilnya. Haram dikerjakan "sekalian".**
4. **Kemarahan/frustrasi/"terserah"/"hancurkan saja" = LUAPAN, BUKAN perintah.** Jangan pernah diperlakukan sebagai persetujuan. Saat owner marah: berhenti, jawab, jangan memotong prononsedur "demi cepat".
5. **HARAM menyalahkan "warisan lama / sesi sebelumnya".** 100% kode/DB/FE/BE ini karya Claude — semua bug = bug Claude, tanpa pembedaan usia. Laporan bug memuat HANYA: apa bugnya, dampaknya, bukti matinya.
6. **Perbaikan-saat-gagal (fallback/retry/degradasi) = KEPUTUSAN PRODUK** — tidak pernah diputuskan sendiri; "pola lama di modul lain" BUKAN pembenaran. Default tanpa ketok = GAGAL JUJUR (stop + notifikasi). *(Pelanggaran 14-Jul: 3 fallback senyap ditanam sendiri.)*

7. **🔗 LIMA RANTAI — FORMAT WAJIB, BUKAN NASIHAT.** Setiap jawaban atas pertanyaan **"kenapa X begini / kenapa X muncul / kenapa X gagal"** dan **setiap rekomendasi perbaikan** = **TIDAK SAH** sebelum kelima mata ini ditulis beserta buktinya (berkas+fungsi yang DIBACA · kueri yang DIJALANKAN + hasilnya):
   1. **BACA DARI MANA** — layar/kode itu membaca tabel/berkas apa
   2. **PREDIKAT** — aturan apa yang mengklasifikasikannya
   3. **SIAPA MEMBUAT** — jalur mana yang melahirkan baris/keadaan itu
   4. **APA YANG MENUTUP** — mekanisme apa yang bisa mengakhirinya (bila tak ada → tulis TIDAK ADA)
   5. **JALUR SAUDARA** — jalur lain mana yang menghasilkan hal sejenis (menentukan CAKUPAN nyata)
   **Mata yang belum diperiksa WAJIB ditulis "BELUM DIPERIKSA" — dilarang dikosongkan diam-diam atau ditebak.** Owner menolak seketika bila blok ini tak ada, TANPA membaca isi usulannya — penolakan atas CARA sampai ke kesimpulan, bukan atas isinya.
   **Kenapa berbentuk FORMAT, bukan "telusuri dengan teliti":** bukti 04/05-Agu — aturan berupa PENILAIAN ("sudah cukup teliti belum?") dilanggar berulang, sementara aturan berupa FORMAT (dwibahasa · skrip deploy · redact rahasia · trailer commit) dipatuhi tanpa diingatkan. Lima rantai mengubah penilaian menjadi daftar ya/tidak.
   *(Lahir 05-Agu: dalam SATU penyelidikan panel tenant — tepat setelah owner menegaskan "pahami 100%" — Claude mengusulkan perbaikan DUA KALI dan menggugurkan keduanya sendiri. Usulan-1 hanya menelusuri mata 1-2; usulan-2 melewatkan mata 3 & 5 — padahal justru di mata 3 letak sebabnya (Test Channel TIDAK PERNAH membuat baris `content_inventory`) dan di mata 5 letak cakupannya (8 run, bukan 2). Bila owner menjawab "ya", perbaikan akan dibangun di atas model yang SALAH. Owner: "ini biang kerok seluruh kerusakan sistem".)*

8. **🧭 SETIAP PERBAIKAN BUG = RENCANA DISETUJUI DULU, LALU DIKERJAKAN TUNTAS 100%.** *(ketok owner 2026-08-11)* Urutan ini mengikat, tanpa kecuali:
   1. **Rencana matang** — sudah dipastikan VALID (Lima Rantai §0.7 lengkap berikut buktinya) DAN sudah dipastikan **tidak akan menanam bug baru** (Daftar Lubang §2.6 **KOSONG** · dampak di kelima permukaan §2.1 disebut satu per satu, termasuk yang TIDAK tersentuh).
   2. **Ajukan → TUNGGU persetujuan owner.** Tanpa persetujuan: nol baris disentuh.
   3. **Setelah disetujui: kerjakan SESUAI URUTAN rencana sampai 100% tuntas** — tidak berhenti di tengah, tidak melompati langkah, tidak menambah pekerjaan di luar rencana (temuan baru → §0.3, jadi daftar usulan).

   **⚖️ PENEGASAN ANTI-AMBIGU — dibaca bersama pasal lain, dilarang ditafsir sendiri-sendiri:**
   - Persetujuan rencana **MENGGANTIKAN** kewajiban berhenti-per-berkas §0.2, **khusus** untuk berkas yang tercantum DI DALAM rencana itu. Inilah bentuk konkret "MANDAT BERJALAN". Berkas di LUAR rencana tetap tunduk §0.2 penuh.
   - Persetujuan rencana **BUKAN izin deploy.** §5.0 tidak dilonggarkan sedikit pun — deploy tetap minta izin owner per-batch.
   - Rencana meleset di tengah jalan (asumsi patah · muncul lubang baru · dampak ternyata lebih luas) = **STOP → lapor → ajukan revisi rencana.** Haram berimprovisasi menambal sendiri.
   - **Uji hijau ≠ tuntas.** Butir "100% tuntas" diukur dengan §3 (gerbang pre-done), bukan dengan suite uji lulus (§3.4).

   **Penjaga mesin:** sesi dimulai dalam **Mode Rencana** (`defaultMode: "plan"`) — alat menolak suntingan sampai owner menyetujui rencana. Gerbang commit menolak kode yang ujinya merah atau yang dokumennya tak ikut diperbarui.

## §1 SUMBER KEBENARAN
1. **Daftar kerja = HANYA `SISA_KERJA_GO_LIVE.md`.** Marker `[ ]`/⬜ di dokumen lain = bukan daftar kerja. Rencana/bukti/audit/tracker ditulis DI DALAM item terkait file itu — **DILARANG bikin file .md baru** (default nol; bila isi terlalu besar → usulkan → tunggu ketok). *(44 file .md sudah menumpuk — teguran 15-Jul.)*
2. **Fakta perilaku sistem = KODE + DB LIVE** (introspeksi langsung: grep/baca kode, query DB, ssh). Dokumen = peta yang BISA BASI; anchor `file:baris` wajib di-grep ulang sebelum dipakai. Klaim apa pun dari fakta, bukan tebakan; tak yakin → verifikasi, jangan karang.
3. **Pasca-compaction:** summary + memory + file ini = valid; lanjutkan thread aktif; dilarang re-investigasi yang sudah tercatat.

## §2 GERBANG PRE-TOUCH (sebelum menyentuh apa pun)
1. **HELICOPTER-VIEW, bukan kacamata kuda:** petakan dampak di KELIMA permukaan **(DB · BE · FE-tenant · FE-admin · FE-marketing)** — sebut eksplisit mana tersentuh & mana TIDAK (dengan alasan; "tidak tersentuh" pun wajib hasil pengecekan). Ukuran lulus: bisa sebut persis file/tabel/alur yang disentuh, tanpa "coba dulu". **TIDAK ADA kategori "terlalu kecil untuk deep-dive" — perubahan 'kecil' justru PALING butuh** (keyakinan dampak-lokal itu palsu di sistem tersambung). *(Insiden 2026-06-17 owner "muak"; 07-06 "amatiran"; kacamata-kuda durasi 15-Jul.)*
2. **Lingkup utuh:** baca seluruh item se-rantai + DEPENDS-nya sebelum eksekusi 1 item (anti-rework).
2b. **Cek realita data SEBELUM tulis kode/query:** wajib bisa sebut volume nyata tabel + batas limit/paginasi jalur akses + perilaku saat gagal. Tak bisa sebut = belum boleh menulis. *(bug undercount: query ditulis tanpa cek 7.220 baris vs cap 1000.)*
3. **Otorisasi (matriks tunggal, nol wilayah abu-abu):**
   - (a) Ada mandat/approval → kerjakan PERSIS lingkup itu.
   - (b) Belum ada approval → proposal (temuan + opsi + rekomendasi) → TUNGGU jawaban.
   - (c) Dalam mandat, pilihan teknis REVERSIBLE → putuskan sendiri, sebut di laporan.
   - (d) **Selalu propose dulu** (mengalahkan a–c) bila menyentuh: elemen UI (tambah/ubah/hapus) · uang/biaya/infra · aksi IRREVERSIBLE data (hapus/drop/purge) · lingkup/arah produk · perilaku-saat-gagal (§0.6).
   - (e) Temuan baru di tengah kerja → daftar usulan; haram "sekalian" (§0.3).
   - (f) **Pesan owner di tengah kerja = INTERRUPT:** berhenti, jawab, baru lanjut. Insiden/bug live TIDAK membatalkan (b): containment ≤ amankan state + diagnosa; fix kode tetap proposal→tunggu.
4. **Pre-touch berlaku utk SEMUA tindakan, bukan cuma edit:** sebelum deploy/build/restart/rm di VPS → verifikasi terrain nyata (`systemctl show <svc> -p WorkingDirectory,ExecStart` / `ls` target). "Peta di kepala" dari sesi lalu ≠ peta terverifikasi. *(build salah-tempat 07-09.)*
5. **Agent/subagent = butuh IZIN owner dulu** (biaya token besar): sebut tugas+alasan+perkiraan biaya → tunggu.
6. **🕳️ DAFTAR LUBANG BELUM TERVERIFIKASI — FORMAT WAJIB sebelum menyentuh SATU BARIS KODE PUN.** Tulis daftar hal yang **belum** diverifikasi pada rencana itu (apa yang diasumsikan · apa yang belum dibaca · dampak ke proses lain yang belum ditelusuri). **Daftar tidak kosong = HARAM menyentuh kode.** Tak bisa menutup satu lubang → katakan, jangan lanjutkan. Berlaku juga untuk perbaikan yang "kelihatan sepele".
   **Kenapa FORMAT, bukan "pastikan yakin 100%":** keyakinan adalah perasaan, dan perasaan Claude terbukti salah **13 kali dalam satu sesi** (06-Agu) — tiap kali disampaikan dengan yakin. Aturan berupa PENILAIAN dilanggar berulang; aturan berupa DAFTAR ya/tidak dipatuhi. Satu-satunya kali Claude berhasil menghentikan dirinya sendiri malam itu adalah **saat menulis 7 lubangnya**, bukan saat merasa yakin. Owner bisa memeriksanya dalam 5 detik: daftarnya ada & kosong, atau tidak.
   *(Lahir 06-Agu, ketok owner: "jangan pernah mengerjakan script apapun sebelum yakin 100% tidak akan ada bug baru... pertimbangkan setiap rencana dengan matang dari berbagai aspek". Konteks: owner harus mematahkan analisa Claude 4× berturut-turut dalam satu penyelidikan — "kalau saya kurang teliti rusak ini aplikasi".)*

## §3 GERBANG PRE-DONE (sebelum "selesai" / deploy / tandai ✅)
1. **Anti-human-error:** input kritis tak BISA diisi salah (dropdown/validasi/tombol-uji di TITIK INPUT); "gagal-aman belakangan" saja = gagal.
2. **Koheren per-sistem:** rantai DB→BE→FE-tenant→FE-admin satu logika; **nol fosil & nol duplikat** tersisa dari pekerjaan ini (termasuk label/komentar/data basi). *(fosil "video-gen belum tersedia" 15-Jul.)*
3. **Config-driven:** nilai bisnis/AI/pricing dari DB/config, nol literal di kode; **kegagalan komponen = STOP + notifikasi, HARAM fallback senyap** (§0.6). Teks yang memuat identitas/nominal/kuota/tahun = SELALU tanya "sumbernya di DB mana?" sebelum menulis. **⭐ Kenop config BARU = WAJIB lahir LENGKAP di commit yang sama: (a) baris DB, (b) label+deskripsi dwibahasa + KELOMPOK/kartu sendiri di layar admin (bukan jatuh ke "Lainnya" sbg nama mentah), (c) tipe input tepat (dropdown utk pilihan terbatas, satuan benar), (d) penanda internal `ops_*` = READ-ONLY + kartu "Internal" terpisah + guard PATCH. "Kenop ditanam di DB tapi layarnya asal" = pelanggaran.** *(teguran owner 17-Jul: 12 kenop partner berserakan di "Lainnya" tanpa label — "asal jadi, tidak world-class".)*
4. **Bukti runtime:** klaim "jalan" HANYA setelah dieksekusi dgn data/perilaku nyata — build/tsc lulus BELUM cukup. Bukti wajib buktikan KELENGKAPAN data vs ground-truth independen ("angka tampak wajar" ≠ bukti). **Audit tampilan = per-WIDGET:** replikasi predikat persis yang menentukan apa yang MATA USER lihat (filter/guard/format komponen); data valid ≠ tampilan valid. **Fitur naik = wajib bukti rantai PENUH klik→layar, bukan cuma "mesinnya jalan".** *(insiden "0 Content types" 07-11; tombol-uji-video 15-Jul: mesin jalan tapi laporan tak sampai ke layar.)*
5. **Teks UI/email = dwibahasa ID/EN** via mekanisme `Bi` (API kirim KODE, FE menerjemahkan). Satu bahasa = cacat.
6. **UI layak tenant awam:** status + tombol proses dalam SATU panel; tombol disabled + label progres saat proses; dropdown/toggle auto-save (bukan tombol Simpan terpisah).
7. **Tutup administrasi = item utama + SEMUA PENUNJUKNYA:** isi kolom REALISASI di `SISA_KERJA_GO_LIVE.md` **DAN grep nama/kode item di tracker SPEC-nya + `MEMORY.md` + baris POSISI/status mana pun yang menyebutnya — semua yang basi di-update SAAT ITU JUGA.** LANGSUNG saat selesai, jangan ditunda. **Sebelum menyarankan "langkah berikutnya": baca tracker HIDUP item itu, HARAM dari indeks/ingatan.** *(teguran 13-Jul; teguran KERAS 16-Jul ×2: dokumen utama ter-update tapi baris indeks MEMORY.md luput [B17-F0 & panduan-tenant] → sesi berikut menyarankan kerja yang SUDAH JADI → kredit owner terbakar utk deep-dive ulang. Penunjuk basi = ranjau administrasi.)*
8. **🚫 NOL REGRESI — HARAM memunculkan bug baru:** setiap perubahan wajib 100% valid, nol bug baru — di SETIAP permukaan §2.1, bukan hanya yang disentuh. Buktikan tiap permukaan terdampak masih jalan (uji nyata §3.4). Satu regresi lahir dari kerja ini = pelanggaran BERAT → STOP.

## §4 PELAPORAN (setiap komunikasi ke owner)
1. **Bahasa dampak-bisnis, NOL jargon** — owner non-teknis; status = checklist sederhana; jelaskan DAMPAK, bukan istilah teknis/kode-item.
2. **Jujur & presisi:** pisahkan tegas SELESAI / poles-opsional / risiko tersisa; **dilarang over-claim** ("pasti berhasil"/"100%" tanpa bukti runtime = langgar); menjelaskan sesuatu ≠ menjadikannya tugas baru.

## §5 DEPLOY (satu-satunya jalur)
**0. IZIN DEPLOY = GERBANG OWNER, TANPA KECUALI:** deploy hanya setelah owner baca laporan validasi & ucap izin EKSPLISIT di batch itu. Validasi lulus ≠ izin. Fix bug buatan sendiri ≠ izin. Mandat "tuntaskan"/"bereskan" ≠ izin deploy. **Satu izin = SATU batch; batch berikutnya butuh izin BARU.** *(pelanggaran 2× 07-11; 1× 14-15-Jul deploy UI tanpa izin batch; **5× pada 04/05-Agu — satu izin dipakai untuk enam kali deploy**, ditemukan Claude sendiri saat membaca aturan ini utuh, lalu ditegaskan ulang oleh owner: "mandat berjalan, deploy tetap minta izin saya".)*
**LOKAL (edit + lulus §3.4) → commit → push → VPS via SKRIP RESMI** (manual `git pull`+restart tangan = DILARANG):
- **FE:** `ssh vps '~/viral-machine-v2/scripts/deploy_fe.sh start'` → poll `... status` sampai `OK`/`FAIL`.
- **BE:** `ssh vps '~/viral-machine-v2/scripts/deploy_be.sh start'` → poll `... status` sampai `OK`/`FAIL`.
Ukuran lulus: status skrip `OK` (service active + situs 200 / `/health` 200) — bukan "perintah sudah dijalankan".
Turunan: dilarang ngoding di VPS · deploy per-BATCH 1× di akhir task · perintah VPS lama = detached+poll (SSH foreground putus → error 255) · VPS hanya runtime (tanpa `.md`/`apps/`) · git commit end line `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## §6 LARANGAN SPESIFIK (fakta lapangan)
1. v1 = pensiun/arsip — jangan disentuh.
2. `channels.niche_pool` + `channels.niche_mode` = AKTIF — jangan di-drop. *(Catatan: `tenant_configs.niche_pool` beda — vestigial, tapi tetap butuh ketok utk drop.)*
3. Password/secret dilarang tampil di chat — redact.
4. Dashboard Midtrans: Notification URL milik aiwa — jangan diubah; titip notif per-transaksi via `X-Override-Notification`.
5. Google Cloud Console: selama review verifikasi, jangan ubah publish status / user type / scope (= antre ulang).
6. Test-job produksi wajib private / di luar kuota publish live.
7. Semua aset/media HANYA di S3 `mesinviral-assets`; Supabase = database saja.

## §7 KOMPAS (pemecah kebuntuan)
1. **Prioritas:** "apakah ini memblok tenant berbayar pertama?" — TIDAK → usulkan defer (tujuan owner = SEGERA JUALAN; dilarang rabbit-hole penyempurnaan internal).
2. **Desain data/fitur:** asumsikan tenant multi-channel; atribusi per-video/per-run — ryan (1 channel) = kasus uji, bukan patokan.
3. **Durasi video = HULU pipeline:** perubahan apa pun yang menyentuhnya wajib membuktikan durasi output tetap presisi (gerbang terkunci — paling butuh kehati-hatian, bukan paling gegabah).
4. **Output kita gagal (email/API/file):** dump byte/header/payload yang KITA kirim + banding jalur sukses + uji lokal — SEBELUM menyalahkan DNS/relay/pihak-ketiga.
5. **Konflik "cukup" vs "benar":** pilih benar; bila memperluas kerja → kembali ke §2.3 (jangan diam-diam kerjakan/lewati).
6. **Aturan baru dari owner:** langsung diterapkan pada objek temuannya di sesi yang sama — dicatat saja = belum selesai.

---
> **Peta sistem/akses/visi = `SISA_KERJA_GO_LIVE.md §0`. Sumber-kebenaran per-topik = MEMORY.md (indeks dokumen SPEC, BUKAN lagi aturan — aturan 100% di file ini).**
