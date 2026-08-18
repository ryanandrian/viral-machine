# 🗺️ PETA MESINVIRAL — satu halaman untuk owner

> Dibuat 2026-08-19 atas permintaan owner: *"tidak ada satupun pegangan."*
> **Bukan dokumen teknis.** Ini peta untuk mengarahkan, dibaca tiga menit.
> Isinya hanya yang **sudah diukur** — bukan rencana, bukan harapan.

---

## 1. Apa yang mesin ini kerjakan

Lima langkah, otomatis, untuk tiap video:

1. **Mengintip tren** — mengumpulkan sinyal apa yang sedang ramai di niche channel itu.
2. **Memilih topik** — mesin AI memilih 5 kandidat terbaik, lalu dinilai & diurutkan.
3. **Menulis naskah** — hook, isi, penutup, sesuai DNA niche (gaya bicara, pantangan, emosi).
4. **Membuat suara & gambar** — suara dari katalog, gambar per babak cerita, lalu dirender jadi video.
5. **Menerbitkan** — unggah ke channel YouTube tenant sesuai jadwalnya.

Di antara langkah itu ada penjaga: gerbang durasi (menolak naskah yang panjangnya meleset),
QC (menolak video cacat), dan rem otomatis (menghentikan channel yang gagal berulang, supaya
kredit tenant tidak terbakar).

## 2. Yang terbukti jalan

- **12 channel** terdaftar; **5 aktif dan tidak dijeda** hari ini.
- **5 video jadi** dalam 24 jam terakhir. RAD The Explorer: 3 dari 3 percobaan.
- **1.151 penjaga uji** hijau. Bagian yang dijaga penjaga tidak pernah rusak dua kali.
- Pembayaran, jadwal, penerbitan YouTube, notifikasi, dan penagihan biaya AI: berjalan.
- Mesin **benar-benar mengukur** performa: 239 video RAD sudah dianalisa.

## 3. Yang rusak sekarang — NOL

Tidak ada kerusakan **terukur** yang belum ditangani. *(Ukuran "rusak" di peta ini = ada angka yang
bisa diukur ulang siapa pun — lihat §4b. Yang tinggal pendapat masuk daftar improvement §4c.)*

**Sudah diperbaiki 19-Agu, menunggu izin pasang:** jawaban AI terpotong lalu diulang 3× sia-sia
(uang tenant terbakar tanpa peluang berhasil) · tombol mutu gambar yang tak berpengaruh di 9 dari
12 channel — kini hanya muncul pada model yang benar-benar menerimanya, dan tenant diberi tahu
bahwa mutu mengikuti model yang ia pilih.

## 4. Yang dijanjikan tapi belum dibangun — 2 hal, dan ini yang terbesar

1. **Belajar di dalam satu niche.** Setelah tenant fokus ke satu niche, mesin seharusnya makin
   pintar di dalam niche itu — sudut mana, tema mana yang menahan penonton. Dirancang 11 Juni
   (lapis "sub-tag"), **tidak pernah dibangun**. Ini janji utama yang dijual.
2. **Bobot penilaian dikalibrasi dari hasil nyata.** Mesin sudah menghitungnya. Hasil hitungnya:
   lima ukuran yang dipakai memilih topik **hampir tidak berhubungan** dengan hasil nyata
   (kaitannya −0,13 sampai +0,08 — praktis nol). Artinya mesin memutuskan memakai ukuran yang
   terbukti tidak meramalkan apa pun. Angka ini sudah ada di database dan belum pernah ditindak.

## 4c. Improvement — bekerja sesuai rancangan, rancangannya bisa lebih baik

**Ini BUKAN kerusakan.** Mesin menuruti kontraknya dengan benar; yang dipertanyakan rancangannya.
Keputusannya milik owner.

1. **Jumlah gambar mengikuti babak cerita, bukan panjang tayangan.** Kontraknya tertulis: preset
   15 dtk = 2 gambar · 30 = 3 · 60 = 5 · 90 = 7, dan mesin menurutinya dengan benar. Akibatnya satu
   gambar bisa menemani sampai 19 detik narasi, dan owner menilai hasilnya kurang nyambung.
   Perbaikannya **sudah dirancang sejak Juni** (mekanisme slot per-babak) dan dokumennya sendiri
   menulis *"JANGAN ubah tanpa keputusan owner"*. **Menunggu ketokan.**
   *(⚠️ 19-Agu Claude sempat menaruh butir ini di daftar "rusak" — pelanggaran pertama aturan §4b,
   terjadi di dokumen yang dibuat untuk mencegahnya, ditemukan owner lewat satu pertanyaan:
   "itu bug atau improvement?")*

## 4b. Cara membedakan mana yang benar — permintaan owner 19-Agu

Owner: *"setiap sesi anda meyakinkan menyatakan bug, lalu sesi berikutnya anda hina rancangan
sendiri. Saya tidak punya pegangan mana yang benar."* **Sebabnya: dua hal dicampur.**

### DEFINISI OWNER — 19-Agu 2026, ini yang berlaku (bukan tafsiran Claude)

> **BUG** = sesuatu yang **rusak, atau berpotensi merusak.** Termasuk: **fosil** · **objek di layar
> yang tidak berfungsi / tidak terhubung** · **data yang dikumpulkan tapi tidak dipakai** · dan
> sejenisnya.
>
> **IMPROVEMENT** = sesuatu yang **saat ini berjalan dengan baik** tapi **mutunya belum tercapai /
> belum memuaskan** dan berpotensi ditingkatkan. Termasuk **mutu konten** (narasi · suara · gambar ·
> video · durasi) dan segala yang terkait **self-learning & self-improvement.**

**Ujian mekanis untuk memisahkannya** (supaya penilaian Claude tidak masuk hitungan):

| | **BUG** | **IMPROVEMENT** |
|---|---|---|
| Bisa ditulis uji yang **MERAH** di kode sekarang? | **Ya** | Tidak |
| Contoh nyata 19-Agu | tombol mutu gambar tak terhubung di 9 dari 12 channel · suara aktif pada mesin yang mati · jawaban terpotong diulang 3× sia-sia · data belajar dikumpulkan lalu diberi label karangan | jumlah gambar per panjang cerita · seberapa percaya pada sinyal belajar yang lemah |
| Dijaga apa? | **penjaga uji** — sesi berikutnya yang membaliknya ditolak mesin | **keputusan owner bertanggal** |

**Ukuran untuk owner:** kalau Claude menyebut sesuatu bug, tanya *"apa angkanya, dan bagaimana saya
mengukurnya sendiri?"* **Tak bisa menjawab ⇒ itu pendapat, bukan bug.**

**Jangan timbang keyakinan Claude.** Terbukti 19-Agu: dalam satu sesi ia mengoreksi diri **12 kali**.

**⛔ UNTUK SESI BERIKUTNYA:** keputusan owner yang tercatat bertanggal **HARAM disebut bug**. Mau
mengubahnya? Datang ke owner dengan ANGKA, bukan dengan keyakinan.

*Contoh nyata 19-Agu:* Claude menyebut "mesin percaya 100% pada korelasi lemah" sebagai **bug**,
lalu **menariknya sendiri** setelah ditegur — yang terukur hanyalah *0 dari 5 korelasi mencapai
ambang layak-percaya (±0,171 pada 132 video; terkuat 0,081)*. Apakah mesin **seharusnya** menakar
keyakinan dari kekuatan sinyal = **KEPUTUSAN OWNER, belum diketok.**

## 5. Yang tidak boleh dikerjakan tanpa ketokan owner

Memasang ke server · mengubah setelan milik tenant · mengubah perilaku-saat-gagal (rem, retry) ·
menyentuh v1 · mematikan penjaga uji mana pun.

## 6. Cara owner memeriksa hasil kerja tanpa perlu memercayai laporan

Satu ukuran saja: **apakah video tetap jadi.** Lihat jumlah video sukses di layar Runs
sebelum dan sesudah pemasangan. Kalau turun, perbaikannya salah dan bisa dibatalkan
dalam hitungan menit.

Dan satu pertanyaan yang menangkap kesalahan paling sering: **"diuji dengan jalur produksi
asli, atau tiruan?"**

---

> **Peta ini wajib diperbarui setiap kali nomor 3 atau 4 berubah.** Peta yang basi = owner
> kehilangan pegangan lagi.
