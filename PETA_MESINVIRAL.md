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

## 3. Yang rusak sekarang — 1 hal

1. **Gambar terlalu sedikit untuk panjang cerita.** Satu gambar bisa menemani sampai 19 detik
   narasi, jadi terasa tidak nyambung. Jumlah gambar diikat ke jumlah babak cerita, bukan ke
   panjang tayangan. *(Perbaikannya sudah dirancang sejak Juni — **menunggu ketokan owner**, dan
   dokumennya melarang mengubahnya tanpa itu.)*

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
