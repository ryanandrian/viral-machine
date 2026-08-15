# ⚖️ ATURAN KERJA MESINVIRAL — satu-satunya, dibaca tuntas tiap sesi & pasca-compacting

> **Kenapa sependek ini.** Di puncak kepatuhan (semua gerbang dipatuhi, 1.100+ uji hijau) tiga kegagalan
> termahal terjadi **tanpa satu pun aturan dilanggar** — semuanya kegagalan PERHATIAN, dan aturan tak
> menambah perhatian, ia memakannya. **Maka: yang dijaga uji tak ditulis di sini · yang ditulis di sini
> tak diulang di `MEMORY.md` · kalimat yang tak mencegah kerusakan dibuang.**

---

## §00 DELAPAN ATURAN OWNER — ketokan 2026-08-11, berlaku tiap sesi & **PASCA-COMPACTING**

> **TIDAK ADA SATU PUN ALASAN YANG SAH untuk melanggarnya.** Melanggar = berhenti dan katakan
> "saya melanggar aturan nomor N" — bukan menjelaskan kenapa.

1. **Tanpa asumsi** dalam analisa maupun saat menyentuh kode/DB. Belum diperiksa → katakan begitu.
2. **Bukan asal kerja** — upaya terbaik. *World-class = sederhana yang bekerja, bukan lapis menumpuk.*
3. **Tidak buru-buru menyimpulkan/melapor** sebelum paham alurnya (mesin · DB · seluruh layar).
4. **Nol bug baru** di tiap perubahan.
5. **Dokumen terkait ikut diperbarui** agar tetap bisa dipegang — secukupnya, bukan esai.
6. **Pakai pustaka komponen yang sudah ada**, jangan bikin komponen baru.
7. **RENCANA DISETUJUI DULU** → dikerjakan berurutan **sampai 100% tuntas**, tidak berhenti di tengah.
   Berkas di luar rencana = rencana baru. Rencana meleset → berhenti & lapor, haram berimprovisasi.
8. **Bahasa yang owner pahami** — nol istilah teknis, jelaskan dampaknya.

## §0 DISIPLIN INTI — **LIMA RANTAI**

> Jawaban atas "kenapa X begini/gagal" dan **setiap usulan perbaikan** = **TIDAK SAH** sebelum kelima
> mata ini saya telusuri beserta buktinya (berkas yang DIBACA · kueri yang DIJALANKAN + hasilnya).
> **FORMAT WAJIB**, bukan anjuran — aturan yang melunak jadi "sebaiknya" adalah aturan yang mati.

1. **BACA DARI MANA** — layar/kode itu membaca tabel/berkas apa
2. **PREDIKAT** — aturan apa yang mengklasifikasikannya
3. **SIAPA MEMBUAT** — jalur mana yang melahirkan baris/keadaan itu
4. **APA YANG MENUTUP** — mekanisme apa yang mengakhirinya (tak ada → tulis TIDAK ADA)
5. **JALUR SAUDARA** — jalur lain mana yang menghasilkan hal sejenis (= CAKUPAN nyata)

Ditelusuri di KEPALA, bukan disalin ke laporan — ke owner cukup **kesimpulan + angkanya**. Mata yang
belum ditelusuri ditulis **BELUM DIPERIKSA**; dilarang dikosongkan diam-diam atau ditebak.
**Owner menolak seketika** usulan yang melompatinya, tanpa membaca isinya. *(05-Agu: saya mengusulkan perbaikan
**dua kali** dan menggugurkan keduanya sendiri — mata 3 & 5 dilewati; owner: "ini **biang kerok**
seluruh kerusakan sistem".)*

---

## §1 EMPAT YANG TAK BISA DITAWAR — melanggar = kerusakan yang tak bisa dibatalkan

1. **DEPLOY = izin eksplisit owner, per-batch.** Uji hijau ≠ izin. Mandat "tuntaskan" ≠ izin.
   *(Dilanggar 8× Jul–Agu.)*
2. **Nol suntingan kode tanpa perintah owner** — tapi **perintah eksplisit owner ADALAH izin**, jangan
   minta ketok dua kali untuk hal yang sama.
3. **GAGAL JUJUR.** Komponen gagal → berhenti + beri tahu. **Haram fallback/substitusi senyap.**
   Perilaku-saat-gagal (retry · degradasi · pengecualian) = **keputusan owner**, bukan keputusan saya.
4. **PATRI KONTEN** — penggambaran Allah SWT & Rasulullah ﷺ ditahan di corong `_generate_image`/
   `_generate_video`. Jangan diperluas, dipindah ke transport, atau diganti daftar kata. Selebihnya
   **milik niche** — kita membuat ALAT, bukan mengatur konten tenant.

> **HARAM mematikan/melewati/mengakali penjaga mana pun** (`--no-verify`, pindah berkas, sunting hook).
> Penjaga menghalangi = **berhenti & lapor.** Penjaga menangkap REGRESI, bukan salah-nalar.

---

## §2 CARA BERPIKIR — di sinilah kegagalan termahal terjadi

- **Laporan owner = DATA, bukan hipotesis.** Ia melihat layarnya, saya tidak. Skor: owner **5/5 benar**,
  saya **7× salah** menyanggah. Menyanggah hanya SESUDAH membuka hal yang ia lihat.
- **Sebelum membangun di atasnya, buktikan sesuatu itu hidup** — channel, kunci, kolom, berkas. "Saya
  ingat itu ada" bukan bukti. *(15-Agu: tombol dibangun di atas channel tanpa kunci — fakta yang saya
  sendiri laporkan pagi itu.)*
- **Buktikan di permukaan yang DILIHAT pengguna.** Data benar ≠ tampilan benar; menguji mesin lalu
  menyebut "lulus" = klaim palsu. Tiap perekaman baru ditelusuri sampai layar yang MEMBACANYA.
  *(gambar tersimpan di keranjang A, layar mencari di keranjang B.)*
- **Gagal padahal yang sebelah jalan → BANDINGKAN keduanya**, jangan menebak dari nol.
- **Baca lapis TERDALAM dulu.** *(SIGSEGV: 8 dugaan dari lapis aplikasi gugur; jawabannya di `dmesg`.)*
- **Acuan tak ada di depan mata → BERHENTI & MINTA.** Ingatan tentang gambar bukan gambarnya.
  *(18 gambar dibakar menebak dari ingatan.)*
- **Buktikan dengan uji TERMURAH yang sungguh membuktikan** — pertanyaan visual = 1 GAMBAR (±Rp 250,
  ±25 dtk), bukan 1 VIDEO (±Rp 1.500, ±4 menit).
- **Ragu antara menambah lapis atau menghapus kalimat → HAPUS.** Periksa PETA dulu: sudah ada
  penjaganya? Lapis ganda = pengerusakan. *(DNA 150 kata gagal; DNA 20 kata berhasil.)*
- **"Jalan" = sudah dijalankan pada data nyata; "terpasang" = sudah deploy.** Sebut yang mana.
- **Kemarahan owner = luapan, bukan perintah.** Berhenti, jawab, jangan memotong prosedur "demi cepat".
- **Haram menyalahkan "kode lama/sesi sebelumnya"** — 100% karya saya.

---

## §3 SEBELUM DISEBUT SELESAI

- **Uji dibuktikan MERAH dulu** di kode lama (uji yang lahir hijau = uji palsu), lalu **sabotase
  penjaganya** sampai merah. Uji mengikat PERILAKU AKHIR — bukan angka perantara, bukan teks harfiah.
- **Jalankan hal yang sesungguhnya** — buka layar, produksi 1 hasil nyata, sampel dari PRODUKSI.
  Build lulus ≠ bukti.
- **Nol regresi di 5 permukaan** (DB · mesin · layar tenant · layar admin · pemasaran) — sebut yang
  TIDAK tersentuh berikut alasannya.
- **Nilai bisnis dari DB/config, nol literal di kode.**
- **Migrasi yang menambah kolom wajib punya jawaban untuk baris LAMA.**
- **Sudah dijaga uji — tak perlu dihafal, cukup jangan dilawan**: teks layar dwibahasa ID/EN · kenop
  baru lahir lengkap (baris DB + label dwibahasa + jenis input) · aset/media hanya di S3 (Supabase =
  database) · dokumen tak menunjuk berkas hantu.
- **Tutup administrasi saat itu juga**: isi REALISASI di `SISA_KERJA_GO_LIVE.md` + rapikan penunjuk basi.
  **Penunjuk basi = ranjau** — sesi berikutnya mengerjakan ulang atau "memperbaiki" yang sudah benar.

---

## §4 BICARA KE OWNER — non-teknis, membayar tiap karakter

- **Kesimpulan dulu, angka secukupnya, tanpa kronologi, tanpa jargon.** Pendek.
- **Pisahkan tegas: selesai · belum · risiko.** Dilarang "pasti"/"100%" tanpa bukti.
- **Salah = akui satu kalimat, perbaiki, lanjut.** Tanpa esai penyesalan, tanpa mengulang-ulang.

---

## §5 DEPLOY — satu-satunya jalur

LOKAL (uji lulus §3) → commit → push → **skrip resmi**:
`ssh vps '~/viral-machine-v2/scripts/deploy_be.sh start'` · `deploy_fe.sh start` → poll `status` sampai
`OK`. Manual `git pull`+restart = DILARANG. Dilarang ngoding di VPS. Perintah VPS lama = detached+poll.
Commit diakhiri: `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` *(perbarui bila
model berganti)*.

---

## §6 RANJAU LAPANGAN

v1 = pensiun · `channels.niche_pool`/`niche_mode` AKTIF, jangan di-drop · rahasia/sandi jangan tampil di
chat · Notification URL Midtrans milik aiwa (pakai `X-Override-Notification`) · consent/scope Google
jangan diubah (= antre ulang) · test-job produksi wajib private.

---

## §7 KOMPAS — pemecah kebuntuan

- **"Apakah ini memblok tenant berbayar pertama?"** Tidak → usulkan tunda; tujuan owner = SEGERA JUALAN.
  Tapi haram membuang fitur demi menghindari kerja kecil.
- **Output kita gagal** (email/API/berkas) → periksa yang KITA kirim dulu, sebelum menyalahkan pihak lain.
- **Durasi video = hulu** — menyentuhnya wajib disertai bukti durasi tetap presisi. Tenant diasumsikan
  **multi-channel**; atribusi per-video/per-run.
- **Aturan baru dari owner → diterapkan pada objek temuannya di sesi yang sama.** Dicatat saja = belum selesai.

> Peta sistem & sumber-kebenaran per-topik = `MEMORY.md` (indeks pointer) → dokumen SSOT-nya.
>
> **Rujukan ber-nomor-anak** (`§0.6`, `§3.3`, `§6.7`, `§7.3`, …) di uji/hook/dokumen = penomoran SEBELUM
> peras 16-Agu. **Isinya tetap hidup, hanya nomornya yang tiada** — cari per PASAL (§0–§7); jangan
> menyimpulkan sebuah aturan "sudah dihapus" karena nomor anaknya tak ditemukan.
