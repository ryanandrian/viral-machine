# ⚖️ ATURAN KERJA — kontrak Claude ↔ owner (auto-dimuat tiap sesi)

> **Prinsip dokumen:** satu aturan = satu pasal (tidak ada duplikasi antar-pasal; pasal lain hanya boleh MERUJUK nomor, bukan mengulang isi). Setiap butir punya ukuran lulus/gagal yang jelas. Detail & "why" = file memory `[[...]]`; bila memory saling bertentangan → yang TERBARU menang.
> **Cara pakai:** sebelum menyentuh apa pun → §2. Sebelum bilang "selesai"/deploy → §3. Ada satu butir gagal → STOP: jangan lanjut / jangan sebut selesai.
> **⭐ STANDAR MUTU (berlaku LINTAS-PASAL, tanpa pengecualian):** SETIAP artefak yang saya hasilkan — kode ship, script sekali-pakai, query diagnosa, skrip analisis — DAN setiap langkah penalaran wajib **world-class best practice**: benar, tangguh terhadap kasus tepi, nol jalan-pintas malas, asumsi diverifikasi bukan ditebak. *Ukuran gagal:* "cukup jalan buat sekarang" · "toh cuma script buang" · lompatan nalar tanpa bukti = MELANGGAR (setara §3 gagal → STOP). Ini bukan gerbang pre-done saja; berlaku sejak baris pertama dipikirkan/ditulis. [[feedback_world_class_quality]] (owner tegaskan ulang 2026-07-12)

## §1 SUMBER KEBENARAN
1. **Daftar kerja = HANYA `SISA_KERJA_GO_LIVE.md`.** Marker `[ ]`/⬜ di dokumen mana pun selain itu = bukan daftar kerja.
2. **Fakta perilaku sistem = KODE + DB LIVE** (introspeksi langsung). Dokumen = peta awal yang bisa basi; anchor `file:baris` dari dokumen wajib di-grep ulang sebelum dipakai. [[feedback_master_docs_first]]
3. **Pasca-compaction:** summary + memory = valid; lanjutkan thread aktif. Dilarang re-investigasi hal yang sudah tercatat. [[feedback_post_compaction]]

## §2 GERBANG PRE-TOUCH (sebelum menyentuh apa pun)
1. **Paham dulu — HELICOPTER-VIEW, bukan kacamata kuda:** baca tuntas dokumen kanonik topik terkait, lalu petakan dampak di KELIMA permukaan **(DB · BE · FE-tenant · FE-admin · FE-marketing)** — sebutkan eksplisit mana yang tersentuh DAN mana yang TIDAK (dengan alasan; "tidak tersentuh" pun wajib hasil pengecekan, bukan asumsi). *Ukuran lulus:* bisa menyebut persis file/tabel/alur yang akan disentuh — tanpa menebak, tanpa "coba dulu". Tidak ada kategori "terlalu kecil untuk deep-dive". [[feedback_comprehend_before_work]]
2. **Lingkup utuh:** sebelum eksekusi 1 item, baca seluruh item/dokumen se-rantai + kolom DEPENDS-nya (anti-rework). [[feedback_review_whole_remediation_before_item]]
2b. **Cek realita data SEBELUM menulis kode/query:** wajib bisa menyebut volume nyata tabel terkait + batas limit/paginasi jalur akses + perilaku saat gagal — tidak bisa menyebut = belum boleh menulis. *(akar bug undercount 2026-07-11: query video_analytics ditulis tanpa cek isi 7.220 baris vs cap 1000)*
3. **Otorisasi — matriks tunggal (tidak ada wilayah abu-abu):** [[feedback_workflow]] [[feedback_owner_delegates_expert_decisions]] [[feedback_no_silent_ui_changes]]
   - (a) Ada mandat/approval owner → kerjakan PERSIS lingkup itu.
   - (b) Belum ada approval → susun proposal (temuan + opsi + rekomendasi) → TUNGGU jawaban.
   - (c) Di dalam mandat, pilihan teknis yang reversible → putuskan sendiri, sebutkan di laporan.
   - (d) **Selalu propose dulu** (mengalahkan a–c) bila menyentuh: elemen UI (tambah/ubah/hapus) · uang/biaya/infra · aksi irreversible pada data (hapus/drop/purge) · lingkup/arah produk.
   - (e) Temuan baru di tengah kerja → masuk daftar usulan; dilarang dikerjakan "sekalian".
   - (f) **Pesan owner masuk di tengah kerja = INTERRUPT**: berhenti, jawab dulu, baru lanjut. **Insiden/bug live TIDAK membatalkan (b)** — containment ≤ mengamankan state + diagnosa; fix kode tetap proposal→tunggu. Item rencana batch yang disetujui ≠ izin menariknya maju. [[feedback_owner_interrupt_stop]] *(pelanggaran berat 2026-07-08)*

## §3 GERBANG PRE-DONE (sebelum bilang "selesai" / deploy / tandai ✅)
1. **Anti-human-error:** input kritis tidak BISA diisi salah (dropdown/validasi/tombol-uji di titik input) — "gagal-aman belakangan" saja = gagal butir ini. [[feedback_world_class_gate]]
2. **Koheren per-sistem:** rantai DB→BE→FE-tenant→FE-admin konsisten satu logika; nol fosil & nol duplikat tersisa dari pekerjaan ini. [[feedback_world_class_quality]]
3. **Config-driven:** nilai bisnis/AI/pricing dibaca dari DB/config, nol literal di kode; kegagalan komponen = stop + notifikasi, dilarang fallback senyap. [[feedback_no_hardcode]]
4. **Bukti runtime:** klaim "jalan" hanya setelah dieksekusi dengan data/perilaku nyata; build/tsc lulus BELUM memenuhi butir ini. Bukti wajib membuktikan **KELENGKAPAN data** (dibandingkan ground-truth independen) — "angkanya tampak wajar" = BUKAN bukti. **Audit tampilan = per-WIDGET:** replikasi predikat persis yang menentukan apa yang MATA USER lihat (filter/guard/format komponen), bukan hanya kontrak sumber data — data valid ≠ tampilan valid. *(insiden "0 Content types" 2026-07-11)* [[feedback_analysis_discipline]]
5. **Bila menyentuh teks UI/email:** dwibahasa ID/EN via mekanisme `Bi` (API kirim KODE error, FE yang menerjemahkan). Teks satu bahasa = cacat. [[feedback_bilingual_mandatory]]
6. **Bila menyentuh UI:** layak tenant awam — status + tombol proses dalam SATU panel; tombol disabled + label progres selama proses; pilihan dropdown/toggle auto-save (bukan tombol Simpan terpisah). [[feedback_uiux_design_for_lay_tenants]]
7. **Tutup administrasi:** isi kolom REALISASI (status + commit + bukti) di `SISA_KERJA_GO_LIVE.md` + sinkronkan dokumen SPEC terkait.
8. **🚫 NOL REGRESI — HARAM memunculkan bug:** setiap penambahan/perubahan/perbaikan wajib **100% valid, nol bug baru** — bukan hanya di permukaan yang disentuh, tapi di SETIAP permukaan yang dipetakan §2.1 (DB·BE·FE-tenant·FE-admin·FE-marketing). *Ukuran gagal:* satu bug/regresi lahir dari kerja ini = pelanggaran berat (kacamata kuda), STOP. Buktikan tiap permukaan terdampak masih jalan (uji nyata per §3.4), bukan berasumsi "yang lain tak kena". [[feedback_comprehend_before_work]] [[feedback_world_class_quality]]

## §4 PELAPORAN (setiap komunikasi ke owner)
1. **Bahasa dampak-bisnis, nol jargon** — owner non-teknis; status berbentuk checklist sederhana. [[feedback_plain_language]]
2. **Jujur & presisi:** pisahkan tegas SELESAI / poles-opsional / risiko tersisa; dilarang over-claim; menjelaskan sesuatu ≠ menjadikannya tugas baru. [[feedback_define_done_no_scope_creep]]

## §5 DEPLOY (satu-satunya jalur)
**0. IZIN DEPLOY = GERBANG OWNER, TANPA KECUALI:** deploy hanya setelah owner membaca laporan validasi dan mengucapkan izin EKSPLISIT di batch itu. Validasi lulus ≠ izin. Fix atas bug buatan sendiri ≠ izin. Mandat "tuntaskan" ≠ izin deploy. *(pelanggaran 2×, 2026-07-11 dini hari)*
**LOKAL (edit + lulus §3.4) → commit → push → VPS WAJIB via skrip resmi (mandat owner 2026-07-09; manual `git pull`+restart tangan = DILARANG):**
- **FE:** `ssh vps '~/viral-machine-v2/scripts/deploy_fe.sh start'` → poll `... deploy_fe.sh status` sampai `OK`/`FAIL`.
- **BE:** `ssh vps '~/viral-machine-v2/scripts/deploy_be.sh start'` → poll `... deploy_be.sh status` sampai `OK`/`FAIL`; pagar render-aktif menunda otomatis — `start --force` hanya sadar-risiko.
*Ukuran lulus:* status skrip `OK` (service active + situs 200 / `/health` 200) — bukan sekadar "perintah sudah dijalankan".
Turunan pasal ini (tidak diulang di tempat lain): dilarang mengedit kode langsung di VPS · deploy per-BATCH 1× di akhir task (bukan per-langkah) · perintah VPS lama lainnya = detached + poll (SSH foreground diputus → error 255; kedua skrip sudah menerapkannya) · VPS hanya berisi runtime (tanpa `.md`/`apps/`). [[feedback_local_test_batch_deploy]] [[feedback_vps_clean]] [[feedback_vps_ssh_long_commands]] *(skrip lahir dari insiden build salah-tempat 2026-07-09)*

## §6 LARANGAN SPESIFIK (fakta lapangan; tidak diturunkan dari pasal lain)
1. v1 = pensiun/arsip — jangan disentuh.
2. `channels.niche_pool` + `channels.niche_mode` = AKTIF — jangan di-drop.
3. Password/secret dilarang tampil di chat — redact (mis. `sed -E 's/Rad@[0-9]*/***/g'`).
4. Dashboard Midtrans: Notification URL milik aiwa — jangan diubah; kita menitip notifikasi per-transaksi via `X-Override-Notification`.
5. Google Cloud Console: selama review verifikasi berjalan, jangan ubah publish status / user type / scope (perubahan = antre ulang).
6. Test-job produksi wajib private / di luar kuota publish live.
7. Semua aset/media disimpan HANYA di S3 `mesinviral-assets`; Supabase = database saja. [[feedback_all_assets_on_s3]]

## §7 KOMPAS (pemecah kebuntuan saat ada pilihan)
1. **Prioritas:** tanya *"apakah ini memblok tenant berbayar pertama?"* — TIDAK → usulkan defer (tujuan owner = segera jualan; dilarang rabbit-hole penyempurnaan internal).
2. **Desain data/fitur:** asumsikan tenant multi-channel; atribusi data per-video/per-run — ryan (1 channel) = kasus uji, bukan patokan. [[feedback_design_for_multichannel_scale]]
3. **Durasi video = hulu pipeline:** perubahan apa pun yang menyentuhnya wajib membuktikan durasi output tetap presisi. [[feedback_f4_locked_gate]]
4. **Output kita gagal (email/API/file):** dump byte/header/payload yang KITA kirim + bandingkan dengan jalur pembanding yang sukses + uji lokal — SEBELUM menyalahkan DNS/relay/pihak-ketiga. [[feedback_inspect_our_output_before_blaming_infra]]
5. **Konflik "cukup" vs "benar":** pilih benar; bila itu memperluas kerja → kembali ke §2.3 (jangan diam-diam kerjakan, jangan diam-diam lewati).
6. **Aturan baru dari owner:** langsung diterapkan pada objek temuannya di sesi yang sama — dicatat saja = belum selesai.

> Indeks 22 aturan + urutan baca kanonik = `MEMORY.md` · peta sistem/akses/visi = `SISA_KERJA_GO_LIVE.md §0`.
