# 📖 Panduan Claude Code (Terminal CLI) — berlaku untuk SEMUA proyek

> **Tujuan:** Anda tahu persis cara menyuruh Claude agar hasil maksimal, kredit hemat, nol salah paham — di proyek mana pun.
> **Sumber valid:** dokumentasi resmi `code.claude.com/docs` + dokumen resmi Claude Design (Help Center, tutorial, pengumuman Anthropic — dipakai di Bagian 10 Fase 4) + verifikasi langsung di terminal (Claude Code v2.1.206, 2026-07-10). Bukan tebakan.
>
> **Struktur:** Bagian 1–6 = yang wajib dikuasai (dijelaskan tuntas + contoh). Bagian 7 = tips & tricks skenario nyata. Bagian 8 = daftar LENGKAP semua perintah (referensi, buka saat perlu). Bagian 9 = darurat. **Bagian 10 = panduan khusus PROYEK BESAR** (PRD ratusan halaman → SaaS jadi): stack standar, urutan kerja 14 langkah, Fase 0–5, koordinasi Claude Design, seni memberi prompt, template `CLAUDE.md` siap-pakai, kamus istilah.

---

## 1. Cara berpikir tentang Claude Code (1 menit, ini pondasi semuanya)

**Bayangkan Claude seperti karyawan ahli dengan MEJA KERJA terbatas.**

- **1 sesi = 1 percakapan = 1 meja kerja.** Semua yang Anda katakan dan semua file yang Claude baca "digelar di atas meja" itu. Selama sesi berjalan, Claude ingat semuanya.
- **Meja itu ada batasnya** (disebut *context*). Makin penuh meja, makin lambat dan makin mahal setiap langkah — karena setiap kali Anda kirim pesan, Claude "membaca ulang seisi meja" dulu sebelum menjawab.
- **`/clear` = membuang SEISI meja.** Claude lupa total. `/compact` = merapikan meja (meringkas), bukan membuang.
- **Ingatan permanen ada di LEMARI ARSIP**, bukan di meja — dan lemari ini **per-proyek** (per-folder): file `CLAUDE.md` (aturan proyek, otomatis terbaca tiap sesi baru) + memory otomatis Claude. Karena lemari ini ada, sesi baru bisa langsung nyambung tanpa Anda menjelaskan ulang dari nol.
- **Kredit terpakai untuk setiap baca & tulis.** Semua tips di panduan ini intinya satu: *kurangi baca-tulis yang tidak perlu.*

## 2. Membuat proyek APA PUN senyaman ini (kunci pindah-pindah proyek)

Perintah dan tombol di panduan ini sama persis di semua proyek. Yang membuat sebuah proyek terasa "Claude-nya sudah hafal" bukan fitur rahasia, melainkan **arsip proyek yang terawat**:

1. **Buka Claude Code di folder proyek itu** — meja kerja, izin, dan memory otomatis terpisah per-folder. Proyek A tidak bocor ke proyek B.
2. **Jalankan `/init` sekali di proyek baru** → Claude membaca proyek Anda dan membuat `CLAUDE.md` awal (peta proyek). *(Untuk proyek besar dari PRD: pakai Template siap-pakai di №10 sebagai gantinya.)*
3. **Isi `CLAUDE.md` dengan aturan main Anda** — cara Anda ingin Claude bekerja: *"selalu buat proposal dulu sebelum mengubah kode"*, *"deploy hanya lewat skrip X"*, *"jangan sentuh folder Y"*, *"laporan pakai bahasa bisnis"*. Edit kapan pun via `/memory`. Aturan ini otomatis terbaca setiap sesi — sekali tulis, berlaku selamanya.
4. **Biasakan menutup tugas besar dengan** *"catat progres & keputusan penting ke memory"* → sesi/hari berikutnya cukup *"lanjut kerja"*.

> Resep 4 langkah ini bisa diterapkan di proyek mana pun dalam 10 menit — dan untuk proyek besar menjadi WAJIB, dalam bentuk yang lebih ketat (№10).

## 3. Tombol keyboard — kendali fisik Anda

| Tombol | Fungsi | Penjelasan & kapan dipakai |
|---|---|---|
| `Esc` | **Rem darurat** | Menghentikan Claude SAAT ITU JUGA, di tengah kerja. Pakai begitu Anda melihat arah melenceng — jangan tunggu selesai, karena setiap detik Claude bekerja = kredit terbakar. Setelah berhenti, ketik koreksi Anda; Claude lanjut dari situ, tidak mulai dari nol. |
| `Esc` 2× cepat | Mundur ke pesan lama | Membuka daftar pesan Anda sebelumnya — pilih satu untuk "mundur ke titik itu" dan menulis ulang perintah dari sana. Berguna bila percakapan sudah melenceng beberapa langkah. |
| `Shift+Tab` | Ganti mode izin | Berputar antara mode Normal → Accept edits → Plan (lihat №4). Cek mode aktif di baris bawah layar SEBELUM memberi tugas. |
| `↑` / `↓` | Riwayat ketikan | Memanggil ulang pesan yang pernah Anda ketik — tak perlu mengetik ulang. |
| Tempel gambar | Bukti visual | Screenshot bisa langsung di-paste ke terminal (Ctrl+V). Claude bisa MELIHAT gambar — jauh lebih presisi daripada menceritakan isi layar. |

## 4. Mode izin — "seberapa longgar tali kekang"

Ini setelan paling penting yang sering terlewat. Ganti dengan `Shift+Tab`, atau ketik `/plan` untuk langsung masuk plan mode.

**Normal (bawaan)** — Claude bertanya dulu setiap mau mengubah file atau menjalankan perintah; Anda tekan ya/tidak.
*Kapan:* kerja harian. Anda melihat setiap perubahan sebelum terjadi. Kekurangannya: harus menunggui terminal untuk menekan izin.

**Accept edits** — izin edit file diberikan di muka; perubahan langsung terjadi tanpa klik Anda. (Perintah shell tetap minta izin.)
*Kapan:* HANYA bila mandat sudah sangat jelas batasnya dan Anda tak ingin menunggui. ⚠️ Bahaya umum: mode ini aktif tanpa disadari → edit masuk tanpa Anda lihat. Biasakan lirik baris bawah layar.

**Plan mode** — Claude dikunci HANYA BISA MEMBACA. Ia menyelidiki, lalu menyerahkan rencana tertulis; tidak satu file pun berubah sampai Anda menyetujui rencananya.
*Kapan:* ⭐ investigasi bug, audit, minta proposal, jelajah kode asing. Mode paling aman DAN paling hemat: tidak mungkin ada "kerja kebablasan" yang harus dibatalkan.

**Bypass permissions** — semua izin dilewati, Claude bebas total. *Hindari* — hanya masuk akal di lingkungan sekali-buang (container uji), bukan di proyek sungguhan.

## 5. Perintah harian — dijelaskan tuntas

### `/compact` — rapikan meja tanpa kehilangan benang merah
Meringkas percakapan panjang menjadi ringkasan padat; tugas yang sedang berjalan TETAP nyambung. Bisa diberi arahan: `/compact fokus ke rencana deploy` → yang dipertahankan detail soal itu.
**Kapan:** sesi sudah panjang (terasa lambat/mahal) tapi tugas belum selesai. **Ini yang seharusnya dipakai, bukan `/clear`.** Saat meja hampir penuh Claude melakukannya otomatis ("compacting…") — biarkan saja.

### `/clear` — mulai benar-benar dari nol
Membuang seluruh percakapan. Claude lupa semua yang belum tercatat di arsip (memory / `CLAUDE.md` / git).
**Kapan:** HANYA saat ganti topik total dan topik lama sudah tuntas + tercatat. **Jangan pernah di tengah tugas.** Kalau terlanjur: minta Claude membaca memory & git lalu melapor posisi terakhir — bisa, tapi ada biayanya.

### `/resume` dan `claude --continue` — kembali ke percakapan lama
- Dari dalam Claude Code: `/resume` → daftar semua sesi lama → pilih → percakapan hidup lagi lengkap dengan ingatannya.
- Dari terminal biasa: `claude --continue` (atau `claude -c`) langsung membuka sesi TERAKHIR; `claude --resume` membuka daftar pilihan.
**Kapan:** laptop mati, terminal tertutup, atau melanjutkan diskusi minggu lalu tanpa menjelaskan ulang.

### `/rewind` — mesin waktu pembatal kesalahan
Mengembalikan percakapan DAN file kode ke titik sebelumnya. Bila Claude salah edit, tak perlu menyuruh "perbaiki balik" (makan kredit, bisa salah lagi) — cukup mundur ke sebelum kesalahan.
**Kapan:** hasil edit tak sesuai harapan; eksperimen yang ingin dibatalkan total. Alias: `/undo`.

### `/usage` — dompet Anda
Menampilkan pemakaian dan biaya. Alias: `/cost`, `/stats`.
**Kapan:** biasakan cek sesudah tugas besar, supaya punya rasa "tugas seperti ini biayanya sekian" — modal menilai pekerjaan mana yang layak biayanya.

### `/context` — seberapa penuh meja kerja
Peta visual isi "meja": berapa persen terpakai, apa yang memakan tempat.
**Kapan:** sesi terasa lambat/boros → cek ini → penuh? `/compact`.

### `/plan` — masuk mode rencana-dulu
Cara cepat masuk Plan mode (№4). Bisa langsung diisi: `/plan selidiki kenapa fitur X gagal`.
**Kapan:** setiap kali Anda ingin PROPOSAL, bukan eksekusi.

### `/btw` — pertanyaan sampingan yang tidak mengotori meja
Bertanya apa saja TANPA menambah beban percakapan utama — jawabannya tidak ikut "digelar di meja".
**Contoh:** di tengah tugas deploy, penasaran soal istilah → `/btw apa itu webhook?` → dijawab, tugas utama tak terbebani.
**Kapan:** pertanyaan pengetahuan umum / iseng di tengah tugas serius.

### `/rename` dan `/branch` — tata percakapan
- `/rename perbaikan-login` → sesi diberi nama, gampang dicari di `/resume`.
- `/branch coba-opsi-2` → menyalin percakapan jadi cabang baru; bereksperimen tanpa merusak jalur utama.
**Kapan:** `/rename` biasakan di awal tugas besar; `/branch` saat ragu antara dua pendekatan.

### `/memory` — buka lemari arsip
Mengedit `CLAUDE.md` dan file memory proyek — tempat aturan main & catatan permanen (lihat №2).
**Kapan:** menambah/mengubah aturan cara Claude bekerja di proyek itu.

### `/doctor` — Claude Code-nya sendiri bermasalah
Memeriksa & memperbaiki instalasi Claude Code (bukan proyek Anda).
**Kapan:** aplikasi terasa rusak, error aneh, perintah tak jalan. Alias: `/checkup`.

### `! perintah` dan `@file` — trik input
- `! ls` → menjalankan perintah shell dengan tangan Anda sendiri, dan HASILNYA terlihat oleh Claude. Berguna untuk login interaktif atau saat Claude minta Anda menjalankan sesuatu.
- `@src/index.ts` → menyebut file spesifik; Claude langsung tahu file mana yang Anda maksud (mengetik `@` memunculkan daftar).

## 6. Cara memberi perintah yang menghasilkan kerja terbaik

**① Satu pesan = satu mandat utuh: tujuan + batas + bukti yang diminta.**
- ❌ *"tolong benerin"* → Claude menebak apa, di mana, sampai mana.
- ✅ *"Perbaiki notifikasi yang headernya kode acak — ganti jadi nama channel. Jangan sentuh yang lain. Uji nyata, lapor dulu sebelum deploy."*
Semakin lengkap mandat di awal, semakin sedikit bolak-balik — dan bolak-balik itulah yang mahal.

**② Sebut sumber/konteksnya, jangan biarkan Claude mencari sendiri.**
*"lihat file TODO item 3"*, *"sesuai proposal tadi"*, `@src/pipeline.py`. Setiap tebakan yang tak perlu = file dibaca sia-sia = kredit.

**③ Tempel bukti mentah, jangan ceritakan ulang.**
Pesan error di-copy-paste utuh; tampilan aneh di-screenshot lalu paste. Bukti mentah presisi 100%; cerita ulang bisa kehilangan detail kunci.

**④ Jawaban pendek itu cukup — dan justru bagus.**
"setuju", "lanjut", "opsi 2", "jangan, batalkan". Claude memegang konteksnya; tak perlu mengulang latar belakang.

**⑤ Koreksi SEGERA, jangan tunggu selesai.**
Lihat arah melenceng → `Esc` → jelaskan. Menunggu selesai baru protes = kredit sudah terbakar + hasil harus dibongkar.

**⑥ Bedakan BERTANYA vs MENYURUH — Claude membacanya beda.**
*"Kenapa fitur X gagal?"* = permintaan diagnosa → Claude menjawab, tidak mengubah apa pun. *"Perbaiki"* = mandat kerja. Kalau ingin sekali jalan: *"selidiki X, kalau ketemu akarnya langsung perbaiki"* — itu mandat eksplisit. (Ingin Claude SELALU proposal dulu? Tulis aturannya di `CLAUDE.md` proyek — lihat №2.)

**⑦ Minta bukti, bukan janji.**
Claude bilang "selesai"? Minta bukti nyata: log berjalan, hasil di database, tampilan berubah — bukan sekadar "build lulus". Kalimat ampuh: *"mana bukti runtime-nya?"* (Jadikan aturan permanen di `CLAUDE.md` agar berlaku otomatis.)

## 7. Tips & tricks — skenario nyata

**💰 Hemat kredit**

1. **Gabungkan pertanyaan.** 3 pertanyaan dalam 1 pesan = Claude membaca meja 1×. Dikirim terpisah = membaca meja 3×. Jawaban sama, biaya beda jauh.
2. **Mulai tugas besar di sesi segar.** Meja kosong = tiap langkah murah. Topik lama selesai → pastikan tercatat → baru `/clear` → mandat baru.
3. **Ritme sehat sesi panjang:** kerja → terasa berat → `/context` (cek meja) → `/compact` (rapikan) → lanjut. Bukan: kerja → `/clear` → suruh ingat-ingat lagi (bayar dua kali).
4. **Plan mode untuk segala investigasi.** Diagnosa di Plan mode tak akan pernah jadi "kerja kebablasan yang harus di-revert". Revert = bayar dua kali.
5. **`/btw` untuk rasa penasaran.** Pertanyaan sampingan tidak membebani setiap langkah tugas utama sesudahnya.
6. **Workflow/subagent/`/batch` = artileri berat.** Puluhan agen sekaligus, token besar. Sebelum mengiyakan tawaran Claude, tanyakan: *"perkiraan biayanya?"* — dan pertimbangkan mewajibkan izin-dulu di `CLAUDE.md`.

**🛡️ Kendali & keamanan**

7. **Lirik baris bawah layar sebelum mandat besar** — di situ tertulis mode izin aktif. Salah mode (accept edits menyala) = edit terjadi tanpa Anda lihat.
8. **Salah arah kecil → `Esc` + koreksi. Salah hasil besar → `/rewind`.** Dua rem berbeda: satu menghentikan, satu membatalkan.
9. **Sebelum langkah berisiko (deploy/hapus/kirim), minta ringkasan dampak:** *"sebutkan apa yang berubah dan risikonya dulu"* — murah, sering menangkap yang terlewat.
10. **Akhir sesi kerja besar:** *"catat progres & keputusan ke memory"* — arsip permanen terisi, sehingga `/clear` atau sesi baru kapan pun tidak kehilangan apa-apa.

**🚀 Produktivitas**

11. **Buka hari cukup 2 kata:** *"lanjut kerja"* — Claude membaca arsip proyek (memory + `CLAUDE.md` + git) lalu melapor posisi. Syaratnya: arsip dirawat (tips nomor 10 di kelompok Kendali di atas).
12. **Beri nama sesi tugas besar** (`/rename audit-pembayaran`) — seminggu kemudian `/resume` tinggal pilih nama, seluruh konteks hidup lagi, nol biaya rekonstruksi.
13. **Ragu antara 2 pendekatan? `/branch`** — uji pendekatan B di cabang; gagal → kembali ke jalur utama yang masih bersih.
14. **Screenshot adalah bahasa tercepat Anda** untuk urusan tampilan/dashboard pihak ketiga — paste gambar >>> deskripsi teks. Arahan berbasis screenshot akurat; berbasis tebakan sering menyesatkan.
15. **`/export laporan.txt`** menyimpan percakapan jadi teks — arsip untuk keputusan penting.
16. **Jawaban terlalu teknis?** *"jelaskan dalam bahasa bisnis"* — dan tulis di `CLAUDE.md` agar jadi gaya default proyek itu.

## 8. Referensi LENGKAP semua perintah `/` (buka saat perlu)

> Perintah harian sudah dijelaskan tuntas di №5. Tabel ini melengkapi sampai 100% — sebagian besar jarang diperlukan.

### 8a. Sesi & percakapan
| Perintah | Fungsi |
|---|---|
| `/clear [nama]` | Percakapan baru, konteks kosong (lihat №5) |
| `/compact [instruksi]` | Ringkas percakapan (lihat №5) |
| `/resume [sesi]` | Lanjut percakapan lama (lihat №5) |
| `/rewind` | Mundur percakapan + kode (lihat №5) |
| `/branch [nama]` | Cabang percakapan untuk eksperimen |
| `/btw <pertanyaan>` | Pertanyaan sampingan tanpa membebani sesi |
| `/rename [nama]` | Beri nama sesi |
| `/recap` | Ringkasan satu-baris sesi berjalan |
| `/export [file]` | Simpan percakapan sebagai teks |
| `/copy [N]` | Salin jawaban Claude ke clipboard |
| `/focus` | Tampilan ringkas (prompt terakhir + jawaban akhir saja) |
| `/exit` | Keluar (alias `/quit`) |

### 8b. Kredit, konteks & model
| Perintah | Fungsi |
|---|---|
| `/usage` | Pemakaian & biaya (alias `/cost`, `/stats`) |
| `/context [all]` | Peta isi "meja kerja" |
| `/model [model]` | Ganti model AI (beda kecerdasan & harga) |
| `/effort [level]` | Tingkat usaha berpikir: low → max (makin tinggi makin teliti & mahal) |
| `/fast [on\|off]` | Mode keluaran cepat (khusus model Opus) |
| `/advisor [model\|off]` | Model kedua sebagai penasihat pendamping |

### 8c. Kendali kerja Claude
| Perintah | Fungsi |
|---|---|
| `/plan [deskripsi]` | Masuk plan mode (lihat №4–5) |
| `/goal [kondisi\|clear]` | Claude terus bekerja sampai kondisi tercapai (mis. "sampai semua test lulus") |
| `/background [prompt]` | Lepas sesi jadi agen latar belakang — jalan sendiri tanpa ditunggui (alias `/bg`) |
| `/tasks` | Daftar tugas latar belakang yang sedang jalan |
| `/workflow [nama]` | Orkestrasi multi-agen (⚠️ mahal) |
| `/agents` | Kelola konfigurasi subagent |
| `/schedule [deskripsi]` | Tugas terjadwal berulang di cloud (alias `/routines`) |
| `/autofix-pr [prompt]` | Sesi cloud otomatis memperbaiki PR GitHub saat CI gagal |

### 8d. Setelan & izin
| Perintah | Fungsi |
|---|---|
| `/config [key=value]` | Setelan umum (alias `/settings`) |
| `/permissions` | Aturan izin tool: allow / ask / deny |
| `/memory` | Edit `CLAUDE.md` / file memory (lihat №5) |
| `/skills` · `/reload-skills` | Daftar skill · muat ulang skill baru |
| `/hooks` | Otomasi saat event tool (lanjutan) |
| `/mcp` | Kelola koneksi MCP server (integrasi eksternal) |
| `/plugin` · `/reload-plugins` | Kelola plugin |
| `/keybindings` · `/statusline` · `/color` · `/scroll-speed` | Kustomisasi tampilan & shortcut |
| `/add-dir <path>` · `/cd <path>` | Tambah folder kerja · pindah folder kerja |
| `/trust <path>` | Beri akses file tanpa dialog izin |
| `/sandbox` | Mode sandbox (isolasi; platform tertentu) |
| `/privacy-settings` | Setelan privasi |

### 8e. Akun, diagnosa, integrasi & lainnya
| Perintah | Fungsi |
|---|---|
| `/help` | Bantuan & daftar perintah |
| `/status` | Versi, akun, koneksi |
| `/doctor` | Periksa & perbaiki instalasi (lihat №5; alias `/checkup`) |
| `/login` · `/logout` | Masuk/keluar akun Anthropic |
| `/upgrade` · `/passes` | Upgrade paket · bagikan minggu gratis |
| `/feedback [laporan]` | Lapor bug ke Anthropic (alias `/bug`, `/share`) |
| `/debug [deskripsi]` | Logging debug untuk troubleshoot |
| `/release-notes` | Catatan perubahan versi |
| `/insights` | Laporan analisis pemakaian sesi-sesi Anda |
| `/powerup` | Belajar fitur via pelajaran interaktif |
| `/init` | Buat `CLAUDE.md` awal proyek (lihat №2) |
| `/diff` | Lihat perubahan kode yang belum di-commit |
| `/review [PR]` | Review PR GitHub |
| `/security-review` | Analisis keamanan perubahan kode |
| `/ide` · `/desktop` · `/web` · `/mobile` · `/teleport` · `/remote-control` · `/remote-env` · `/chrome` | Integrasi: IDE / app Desktop / web claude.ai / HP / tarik sesi web ke terminal / kendali jarak jauh / environment cloud / Chrome |
| `/install-github-app` · `/install-slack-app` | Pasang app GitHub / Slack |
| `/setup-bedrock` · `/setup-vertex` | Autentikasi AWS / Google Cloud |
| `/design-login` · `/design-sync` | Akses & sinkron design-system |
| `/heapdump` | Snapshot memori aplikasi (diagnosa teknis dalam) |
| `/radio` · `/stickers` | Radio lo-fi · pesan stiker (hiburan) |

### 8f. Skill bawaan (perintah pintar)
| Perintah | Fungsi |
|---|---|
| `/code-review [level] [--fix]` | Review kode: cari bug + usul perapian; `--fix` sekalian menerapkan |
| `/simplify [target]` | Sederhanakan/rapikan kode yang baru berubah |
| `/verify` | Buktikan perubahan benar-benar jalan lewat uji nyata (bukan cuma build) |
| `/run` | Jalankan aplikasi proyek untuk melihat hasil langsung |
| `/deep-research <pertanyaan>` | Riset web mendalam multi-sumber, laporan bercatatan kaki (⚠️ agak mahal) |
| `/dataviz [permintaan]` | Panduan desain grafik/dashboard |
| `/loop [interval] [prompt]` | Jalankan prompt berulang otomatis (mis. pantau tiap 5 menit) |
| `/batch <instruksi>` | Perubahan besar paralel lintas-kode (⚠️ mahal) |
| `/claude-api` | Referensi API Claude (untuk ngoding pakai API) |
| `/fewer-permission-prompts` | Kurangi dialog izin yang sering muncul |
| `/run-skill-generator` | Ajari `/run` & `/verify` cara menjalankan proyek Anda |

### 8g. Alias (nama lain, fungsi sama)
`/new`, `/reset` → `/clear` · `/continue` → `/resume` · `/cost`, `/stats` → `/usage` · `/settings` → `/config` · `/undo` → `/rewind` · `/quit` → `/exit` · `/bug`, `/share` → `/feedback` · `/checkup` → `/doctor` · `/bg` → `/background` · `/app` → `/desktop` · `/rc` → `/remote-control` · `/routines` → `/schedule` · `/proactive` → `/loop`

### 8h. Dari terminal biasa (sebelum masuk Claude Code)
| Perintah | Fungsi |
|---|---|
| `claude` | Mulai sesi baru di folder saat ini |
| `claude --continue` / `claude -c` | Langsung lanjut percakapan TERAKHIR proyek itu |
| `claude --resume` / `claude -r` | Buka daftar percakapan lama, pilih salah satu |

## 9. Kalau terjadi sesuatu (darurat)

| Kejadian | Yang Anda lakukan | Kenapa ini benar |
|---|---|---|
| Terminal tertutup / laptop mati | Buka terminal di folder proyek → `claude --continue` | Percakapan tersimpan di disk; tidak ada yang hilang |
| Terlanjur `/clear` di tengah tugas | *"baca memory & git, lapor posisi terakhir"* | Arsip permanen tetap ada; Claude merekonstruksi darinya |
| Claude salah edit / hasil tak diinginkan | `/rewind` → pilih titik sebelum kesalahan | Membatalkan percakapan + file sekaligus, tanpa "perbaikan di atas kesalahan" |
| Claude klaim selesai tapi Anda ragu | *"mana bukti runtime-nya?"* | Bukti nyata (log/DB/tampilan live) > "build lulus" |
| Claude mengerjakan yang tidak diminta | `Esc` → *"itu di luar mandat, kembali ke X"* | Temuan baru sebaiknya jadi usulan, bukan dikerjakan "sekalian" |
| Muncul "context low / compacting" | Biarkan | Normal — Claude merapikan mejanya sendiri lalu lanjut |
| Claude Code terasa rusak/aneh | `/doctor` | Diagnosa & perbaikan otomatis instalasi |

## 10. 🏗️ Tips & tricks khusus PROYEK BESAR — dari PRD ratusan halaman sampai SaaS jadi, 100% vibe coding

> **Masalah intinya:** PRD 200 halaman TIDAK muat "digelar di meja" setiap sesi (№1) — dan Anda tidak membaca kode, jadi kualitas tidak bisa dijaga oleh mata Anda. Solusinya dua: **distilasi dokumen** + **gerbang kualitas otomatis yang disiplin**. Semua fase di bawah memakai perintah yang sudah dijelaskan di panduan ini.

### 🧱 STACK STANDAR (ketetapan owner — seluruh dokumen ini sejalan dengannya)

| Lapisan | Standar | Peran awam |
|---|---|---|
| Database + Auth | **Supabase** (PostgreSQL) | Lemari data + sistem login; pemisahan data antar-tenant pakai RLS bawaannya |
| Backend | **Node.js** | Dapur aplikasi |
| Frontend | **React + Next.js + Tailwind (+ shadcn/ui)** | Ruang tamu aplikasi — dipilih agar hasil Claude Design (React) DIPAKAI LANGSUNG tanpa konversi; jalan di Node.js, konsisten dengan BE |
| Kode & riwayat | **Git + GitHub** | Kotak proyek + save point + kerja tim |
| Lingkungan pengembangan | **WSL Ubuntu 22.04** (lokal) | Dapur latihan di laptop Anda |
| Lingkungan produksi | **VPS Ubuntu 22.04** (BiznetGio) | Dapur sungguhan yang diakses publik — OS sama dengan lokal = seragam, minim kejutan |
| Penyimpanan file/gambar | **S3-compatible** (BiznetGio) | SEMUA aset upload ke sini — bukan di disk server aplikasi, bukan di DB |

- **Penyimpangan dari stack ini = keputusan owner** lewat proposal + trade-off; bukan pilihan bebas Claude.
- ✅ **FE = React sengaja dipilih selaras standar baku Claude Design** (output React, `/design-sync` berbasis React — keputusan owner 2026-07-10, delegasi ke Claude): komponen prototype DIPAKAI LANGSUNG, Claude Code fokus **wiring** (data Supabase, auth, state, i18n, test) — bukan membangun ulang FE. Detail alur di Fase 4.
- 📊 **Tabel data kompleks (daftar ber-sort/filter/pagination/pilih-baris) WAJIB TanStack Table** — mesin tabel standar de-facto React (headless), tampilannya dibalut komponen shadcn/ui agar senada prototype. Dilarang membangun logika tabel manual & dilarang menambah pustaka tabel lain tanpa proposal → ketok owner (keputusan owner 2026-07-10).

### ✅ URUTAN KERJA DARI NOL — ikuti dari atas ke bawah, jangan loncat

> Ini peta jalannya. Detail CARA mengerjakan tiap langkah ada di Fase 0–5 di bawahnya. Prinsip di setiap langkah sama: **Claude mengusulkan → Anda ketok → baru dikerjakan.**

**TAHAP PERSIAPAN (sekali saja, ± minggu pertama):**

| # | Langkah | Yang Anda lakukan / ketik | Selesai bila |
|---|---|---|---|
| 1 | Siapkan "rumah" proyek | Buka terminal di folder baru → `claude` → *"siapkan folder proyek + git, lalu berhenti"* | Folder & git ada, belum ada kode |
| 2 | Masukkan PRD | Salin file PRD ke `docs/PRD/` (atau minta Claude memindahkannya) | PRD ada di dalam repo |
| 3 | **Distilasi PRD** → detail di **Fase 0** | `/plan` lalu perintah distilasi (teks lengkapnya ada di Fase 0) | 5 dokumen turunan (a–e, termasuk Matriks Cakupan 100%) jadi & **Anda sudah membacanya + ketok** |
| 4 | **Pondasi & aturan main** → detail di **Fase 1** | Sesi baru: copy-paste **Template `CLAUDE.md`** (bagian 📋 bawah — stack standar sudah terisi di §7) → minta proposal struktur folder + konvensi → Claude lengkapi sisa §7 | `CLAUDE.md` terpasang berisi SOP + stack standar + §7 lengkap, Anda ketok |
| 5 | **Rancang database** → detail di **Fase 2** | Sesi baru, `/plan`: skema DB penuh dari model domain | Skema Anda ketok, migrasi pertama jalan |
| 6 | **Rancang tampilan** → detail di **Fase 4** | Di Claude Design (claude.ai): sistem desain dulu, lalu prototype alur-alur inti | Design system + alur inti diketok — sebelum ini dilarang ngoding FE. (Alur sisanya boleh menyusul, asal selalu SELANGKAH di depan pembangunan — lihat Fase 4) |

> #### ⚖️ Kenapa urutannya CETAK BIRU → DB → baru DESAIN FE? (jangan dibalik)
> **CETAK BIRU ≠ PRD Anda.** Cetak biru = HASIL DISTILASI (Fase 0): 5 dokumen kerja yang dibuat Claude Code DARI PRD Anda, lalu Anda ketok. Analogi rumah: PRD = daftar keinginan pemilik · distilasi = gambar arsitek (inilah cetak biru) · **DB = pondasi & rangka** · desain FE = interior & tampak muka · pembangunan modul = ruangan satu per satu. Anda tidak memilih warna interior sebelum gambar arsitek ada — dan tidak menunda pondasi demi gambar interior.
> 1. **DB paling mahal diubah belakangan.** Ubah tampilan = mengecat ulang; ubah struktur data setelah aplikasi berjalan = membongkar pondasi rumah yang sudah dihuni.
> 2. **DB memaksa kejujuran.** Desain tampilan bisa "menggambar apa saja" (indah tapi bohong); skema DB tidak bisa bohong — layar yang didesain SETELAH DB ada hanya menampilkan data yang sungguh bisa disediakan sistem.
> 3. **Prompt ke Claude Design jadi presisi.** Claude Code menulis draft prompt per-alur berbekal skema NYATA ("layar ini menampilkan kolom A/B/C + kondisi kosong/error") — bukan karangan.
> 4. **Arah balik tetap hidup & murah:** kalau saat mendesain ketahuan ada data kurang → cukup 1 migrasi kecil, karena ketahuan SEBELUM ada kode yang bergantung padanya.
>
> 💡 **Bonus paralel:** langkah 6 adalah pekerjaan ANDA (iterasi visual di Claude Design, bisa berhari-hari). Sementara itu Claude Code tidak menganggur — kerangka backend inti (login, pemisahan tenant, config) dibangun paralel karena tidak bergantung tampilan. Dua jalur bertemu di tahap pembangunan.

**TAHAP PEMBANGUNAN (berulang untuk SETIAP modul, urut sesuai backlog):**

| # | Langkah | Yang Anda lakukan / ketik | Selesai bila |
|---|---|---|---|
| 7 | Buka modul | Sesi baru → *"baca spec modul X, lalu `/plan` usulkan cara membangunnya"* | Proposal jelas, Anda ketok |
| 8 | Bangun iris vertikal | Claude kerjakan DB→BE→FE modul itu (FE mengikuti prototype langkah 6) | Fitur jalan nyata (bukan cuma build) |
| 9 | Gerbang kualitas | Test lulus + bukti runtime + `/code-review` (+`/security-review` bila menyentuh login/uang/data pribadi) | Nol temuan penting tersisa |
| 10 | Tutup buku modul | *"commit, centang backlog, tulis entri PROGRESS.md"* → `/clear` | Backlog tercentang + entri PROGRESS tertulis (format di bawah), meja bersih |
| 11 | Tiap 3–5 modul: AUDIT | Sesi khusus `/plan`: perintah audit (teks lengkap di Fase 5) | Temuan dibereskan sebagai 1 batch |

**TAHAP MENJELANG RILIS:**

| # | Langkah | Yang Anda lakukan / ketik | Selesai bila |
|---|---|---|---|
| 12 | Audit total | Audit menyeluruh (Fase 5) + `/security-review` seluruh aplikasi | Daftar temuan = nol yang berbahaya |
| 13 | Uji sebagai orang awam | Anda sendiri klik-klik seluruh alur dari daftar-akun sampai bayar — bukan Claude yang menguji | Anda tidak tersesat di aplikasi sendiri |
| 14 | Rilis | Minta Claude siapkan skrip deploy resmi → deploy → cek kesehatan situs | Situs hidup + alur inti jalan di produksi |

### Fase 0 — Distilasi PRD *(= langkah 2–3 checklist)*

1. Simpan PRD di dalam repo, mis. `docs/PRD/`.
2. Sesi khusus **Plan mode**: *"Baca seluruh PRD, lalu hasilkan: (a) peta arsitektur sistem, (b) model data/domain lengkap, (c) pecahan per-MODUL — tiap modul jadi file spec sendiri 2–5 halaman, (d) BACKLOG tunggal berurutan dengan kolom dependensi & status, (e) MATRIKS CAKUPAN."*
3. **Matriks Cakupan = jaminan "tak ada setitik pun terlewat"** (standar industri: *Requirements Traceability Matrix*). Prosesnya 3 lintasan: (1) setiap butir kebutuhan di PRD diberi nomor unik R-001, R-002, … — didaftar SEMUA, bukan diringkas; (2) setiap nomor dipetakan ke spec modul + item backlog; (3) PRD disisir ulang bab-per-bab — setiap butir wajib berstatus **terpetakan** atau **pertanyaan terbuka untuk owner**, tidak ada status ketiga. *Distilasi DILARANG diketok sebelum matriks 100%.* Anda bisa spot-check kapan pun: "R-117 dipetakan ke mana?" — jawabannya harus selalu ada.
4. **Anda review & ketok hasil distilasi itu** — ini pengganti Anda membaca 200 halaman berulang-ulang.
5. Mulai sekarang: sesi kerja hanya membaca **spec modul yang relevan**, bukan PRD utuh. Hemat besar + presisi naik.

> ⚠️ PRD adalah sumber kebenaran BISNIS; hasil distilasi adalah sumber kebenaran KERJA. Kalau keduanya bertentangan → perbaiki distilasinya, catat keputusannya.

### Sistem 3 dokumen hidup — jantung proyek (dibuat di Fase 0–1, diupdate SETIAP titik progres)

Inilah yang membuat proyek berbulan-bulan tidak pernah tersesat, tahan `/clear`, tahan ganti sesi, dan bisa diaudit kapan pun. Tiga file, tiga peran — jangan dicampur:

| File | Peran | Kapan diupdate |
|---|---|---|
| `BACKLOG.md` | **Apa yang harus dikerjakan** — daftar kerja tunggal: item + dependensi + status + kolom REALISASI (commit + bukti) | Setiap item selesai / temuan baru masuk |
| `PROGRESS.md` | **Apa yang sudah terjadi** — jurnal kronologis, entri terbaru di ATAS | Setiap tutup batch (langkah 10) — TANPA KECUALI |
| `docs/spec/` | **Bagaimana seharusnya** — spec per-modul hasil distilasi | Hanya bila keputusan mengubah rencana |

**Format entri `PROGRESS.md`** (suruh Claude patuhi ini, tulis aturannya di `CLAUDE.md`):
```
## 2026-08-15 — Modul pembayaran (Batch 12) SELESAI
Dikerjakan: ... (2-4 baris, bahasa bisnis)
Bukti: test 14/14 lulus + transaksi uji masuk DB + commit a1b2c3d
Keputusan penting: ... (bila ada — beserta alasannya)
Berikutnya: modul notifikasi (backlog #13)
```

**Aturan mainnya:**
- **Batch tanpa entri PROGRESS = batch BELUM selesai.** Titik. Ini yang menjamin "setiap titik progres tercatat".
- Sesi baru kapan pun cukup: *"baca PROGRESS.md entri teratas + BACKLOG.md, lapor posisi, lanjut"* — nol biaya rekonstruksi, nol cerita ulang dari Anda.
- Kolom REALISASI di backlog wajib berisi **bukti** (commit + hasil uji), bukan sekadar centang — supaya "selesai" selalu bisa dibuktikan, bukan diingat-ingat.
- Keputusan penting (ganti arah, tolak fitur, pilih vendor) dicatat DI HARI ITU — keputusan yang tak tercatat akan didebat ulang 2 bulan kemudian (mahal).

### Fase 1 — Pondasi *(= langkah 4 checklist; paling menentukan — jangan tergoda langsung ngoding fitur)*

1. **`CLAUDE.md` ditulis SEBELUM baris kode pertama** — pakai Template 📋 di bawah (stack standar sudah terisi di §7), lalu Claude melengkapi sisanya: struktur folder + konvensi penamaan & pola kode (diputuskan sekali lewat proposal, bukan berubah di tengah jalan).
2. **Git sejak hari pertama** (1 commit rapi per-batch, selaras aturan emas #3) — ini jaring pengaman `/rewind`-nya proyek besar.

### Fase 2 — DB dulu, dan diketok *(= langkah 5 checklist)*

1. Dari model domain (Fase 0), minta **skema database penuh** sebagai file migrasi bernomor sejak awal — bukan "tabel ditambah sambil jalan".
2. Untuk SaaS: keputusan **multi-tenant** (pemisahan data antar-pelanggan) diambil DI SINI, sejak desain — menempelkannya belakangan = bongkar semua.
3. Review skema di Plan mode, Anda ketok, baru migrasi dijalankan. **DB adalah bagian paling mahal untuk diubah belakangan** — investasi waktu di sini terbayar berlipat.

### Fase 3 — Bangun per IRIS VERTIKAL *(= langkah 7–11 checklist; resep anti-tambal-sulam)*

1 batch = **1 fitur tembus penuh DB → BE → FE**, bukan "seluruh backend dulu baru frontend". Fitur pertama yang tembus penuh membuktikan seluruh arsitektur nyambung — kesalahan pondasi ketahuan di minggu pertama, bukan bulan ketiga.

Ritual per-batch (hafalkan, ini jantungnya):
```
sesi baru → baca spec modul → /plan (proposal) → Anda ketok
→ kerjakan → test + bukti runtime (/verify) → /code-review
→ commit → centang BACKLOG + entri PROGRESS.md → /clear → modul berikutnya
```
- **Sesi segar per modul** (meja bersih = murah & fokus), sah karena arsip (backlog + memory + spec) dirawat.
- Temuan di luar mandat batch → masuk backlog sebagai usulan, **jangan dikerjakan "sekalian"** — itu awal dari berantakan.

### Fase 4 — FE lewat Claude Design *(= langkah 6 checklist + implementasinya di langkah 8; prototype dulu, kode belakangan)*

> **Seluruh bagian ini berpijak pada dokumen RESMI Anthropic** (Help Center "Get started with Claude Design", tutorial resmi "Using Claude Design for prototypes and UX", pengumuman resmi Anthropic Labs). Butir berlabel *(rekomendasi)* = kesimpulan penerapan, bukan kutipan resmi.

**Fakta resmi yang jadi fondasi:**
- Alur resmi 4 langkah: **Input → Generate → Iterate → Handoff ke Claude Code** ("closed loop": eksplorasi → prototype → kode produksi).
- Urutan resmi memulai proyek: buat proyek → **lampirkan design system** → tambahkan konteks (dokumen, screenshot, codebase) → BARU deskripsikan yang mau dibangun.
- **Semua contoh prompt resmi berbentuk per-halaman / per-alur** — *"Design a new settings page…"*, *"Map out the flow for a user who wants to upgrade…"* — tidak ada contoh "buatkan seluruh aplikasi sekaligus".
- Iterasi resmi 3 cara: **chat** (perubahan struktural besar) · **komentar inline** (penyesuaian tertarget) · **edit langsung**; bisa juga menyimpan versi & minta pendekatan alternatif.
- Handoff resmi membundel: file desain + riwayat chat + README — satu instruksi ke Claude Code.
- Batasan resmi yang paling penting: **kualitas output bergantung pada kelengkapan design system sumber**.
- Bila codebase dihubungkan, prototype memakai **komponen nyata** dari kode Anda; rekomendasi resmi: tautkan direktori spesifik, bukan seluruh repo. `/design-sync` (perintah resmi CLI) = jalur sinkron design-system repo ↔ Claude Design — **berbasis React**.
- **Standar baku output Claude Design = HTML/CSS/JS atau komponen React** — dan stack standar kita (FE React) SENGAJA diselaraskan dengannya: komponen handoff **dipakai langsung**, pekerjaan Claude Code = **wiring** (data Supabase, auth, kondisi loading/error, i18n, test) — bukan menulis ulang tampilan. Realistis: reuse ±90–95%; sisa 5–10% adalah wiring yang memang bukan bagian desain.

**Jawaban pertanyaan kunci — prompt bertahap atau langsung seluruh proyek?**
Dokumen resmi tidak menjawab hitam-putih, tapi polanya tegas: **KONTEKS dipasang sekali di level proyek — PROMPT diberikan bertahap per-alur/per-halaman.** Jadi bukan memilih salah satu:
- **Utuh di depan:** dokumen konteks (ringkasan produk + pengguna + inventori layar — hasil distilasi Fase 0) + design system → dilampirkan SEKALI saat proyek dibuat. Inilah yang menjaga layar ke-30 tetap senada dengan layar ke-1.
- **Bertahap saat generate:** satu prompt per alur/halaman, mengikuti bentuk contoh-contoh resmi, disempurnakan lewat iterasi — koreksi selera Anda di alur awal menular ke alur berikutnya.
- *(rekomendasi)* **Claude Code yang menuliskan draft prompt-prompt itu** dari spec modul — tutorial resmi menempatkan "PM menulis prompt fitur"; dalam vibe coding, pemegang spec paling lengkap adalah Claude Code, dan Anda tetap pengetoknya.

**Urutan kerja lengkap:**

| # | Langkah | Siapa | Dasar |
|---|---|---|---|
| 1 | Siapkan bahan: dokumen konteks produk (dari distilasi Fase 0) + arahan visual + daftar semua layar + **STANDAR TEKNIS FE** (wajib tertulis di dokumen konteks: React + Tailwind + shadcn/ui; semua tabel data kompleks memakai pola **TanStack Table** — sort/filter/pagination/seleksi didesain sesuai kemampuan nyata pola itu); minta Claude Code drafkan juga prompt per-alur — **draft prompt layar ber-tabel wajib menyebut TanStack Table eksplisit** | Claude Code + Anda ketok | resmi (konteks proyek) + rekomendasi (Claude Code sbg penulis draft) |
| 2 | Buat proyek di Claude Design → lampirkan design system (bila belum ada: jadikan pembuatan design system pekerjaan pertama) → lampirkan dokumen konteks | Anda | resmi |
| 3 | ⛔ **GERBANG look & feel:** kunci design system + 2–3 layar kunci dulu; iterasi (chat/komentar/edit) sampai Anda PUAS; dilarang lanjut sebelum lewat — ingat batasan resmi: kualitas semua output bergantung kelengkapan design system | Claude Design + Anda | resmi (batasan) + rekomendasi (dijadikan gerbang) |
| 4 | Generate bertahap per-alur/per-halaman memakai draft prompt langkah 1; tiap alur: generate → iterasi → ketok; ragu antara 2 gaya → minta versi alternatif (fitur resmi) | Claude Design + Anda | resmi |
| 5 | Bila sebagian kode sudah ada: hubungkan direktori spesifik (bukan seluruh repo) agar prototype memakai komponen nyata | Anda | resmi |
| 6 | **"Handoff to Claude Code"** — bundel resmi (file desain + riwayat chat + README) masuk ke repo | Claude Design → Claude Code | resmi |
| 7 | Implementasi: baca README bundel → port pondasi style dulu → buktikan dengan 1 layar terkompleks → sisanya ikut urutan backlog (iris vertikal Fase 3) | Claude Code | rekomendasi |
| 8 | Setelah handoff, kebenaran visual = KODE di repo; fitur besar baru kelak → `/design-login` + `/design-sync` → desain lagi di Claude Design dengan design-system terkini | Anda putuskan | resmi (mekanisme sync) + rekomendasi (satu sumber kebenaran) |

**Sinkronisasi dengan jadwal pembangunan (Fase 3)** *(rekomendasi)*: desain minimal **selangkah di depan** pembangunan — layar modul X diketok SEBELUM batch FE modul X dimulai. Mengubah prototype murah; mengubah kode jadi mahal.

> Sumber resmi: `support.claude.com` → "Get started with Claude Design" · `claude.com/resources/tutorials` → "Using Claude Design for prototypes and UX" · `anthropic.com/news/claude-design-anthropic-labs`. Produk masih berkembang cepat — cek Help Center untuk fitur terbaru.

### Fase 5 — Gerbang kualitas berkala *(= langkah 9, 11, 12 checklist; pengganti mata Anda)*

Karena Anda tidak membaca kode, **gerbang otomatis inilah reviewer Anda**:
- **Tiap batch:** test suite lulus + `/code-review` (level tinggi untuk modul kritis: pembayaran, auth, data pelanggan).
- **Tiap selesai modul penting:** `/security-review` — apalagi yang menyentuh login, uang, dan data pribadi.
- **Tiap 3–5 modul: sesi AUDIT khusus di Plan mode:** *"Sisir seluruh kode: cari duplikasi, hardcode, kode mati, inkonsistensi pola, fallback senyap, TODO terbengkalai. Laporkan sebagai daftar temuan berperingkat."* → temuan diperbaiki sebagai batch sebelum lanjut.
- **Larangan keras: "nanti dirapikan".** Hutang teknis yang ditunda = definisi bom waktu. Rapikan sebelum modul berikutnya, selagi murah.

### Seni memberi prompt — membuat Claude PATUH aturan & SELALU kinerja terbaik

> №6 mengajarkan anatomi satu perintah. Bagian ini selevel di atasnya: cara MENGELOLA Claude selama proyek berbulan-bulan — agar aturan tidak luntur dan kualitas tidak menurun. Semua teknik di sini berpijak pada mekanisme resmi Claude Code (`CLAUDE.md` auto-dimuat tiap sesi · konteks/"meja kerja" · memory) — bukan mantra.

**① Aturan di chat itu MENGUAP; aturan di `CLAUDE.md` itu PERMANEN.**
Aturan yang Anda ucapkan di percakapan bisa pudar saat sesi diringkas/diganti. Maka setiap kali Anda menemukan aturan yang penting, saat itu juga perintahkan:
> *"Jadikan aturan permanen — tulis ke `CLAUDE.md`: [aturannya]. Lalu terapkan sekarang juga pada pekerjaan yang sedang berjalan."*

Bagian kedua itu penting: aturan yang hanya dicatat tapi tidak langsung diterapkan = belum ada.

**② Aturan harus punya UKURAN lulus/gagal — bukan himbauan.**
Claude mematuhi aturan yang bisa diperiksa, bukan nasihat moral:
- ❌ *"kerjanya yang teliti ya"* — tak terukur, tak mengubah apa pun.
- ✅ *"dilarang bilang selesai sebelum menunjukkan bukti runtime"* — bisa diperiksa, pasti dipatuhi.
- ✅ *"setiap nilai bisnis wajib dari config; satu saja hardcode = pekerjaan ditolak"*.

**③ Ritual pembuka tugas besar: kunci pemahaman SEBELUM sentuh apa pun.**
> *"Sebelum mulai: ulangi mandat ini dengan kata-katamu sendiri, sebutkan persis file/tabel yang akan kamu sentuh dan yang TIDAK boleh disentuh, lalu tunggu konfirmasi saya."*

Salah paham yang tertangkap di sini biayanya nol. Salah paham yang tertangkap setelah kerja = bayar dua kali. Ini pasangan sempurna Plan mode.

**④ Kata-kata yang BENAR-BENAR mengubah kualitas** (bukan mantra — ini instruksi kerja yang bisa dieksekusi):
- *"Jangan berasumsi — verifikasi langsung ke kode/DB sebelum menjawab"* → memaksa pengecekan nyata.
- *"Deep dive sampai akar, jangan berhenti di gejala"* → melarang tambal-di-permukaan.
- *"Sertakan bukti untuk setiap klaim"* → mengubah laporan janji jadi laporan fakta.
- *"Kalau tidak yakin, bilang tidak yakin — jangan mengarang"* → membuka pintu kejujuran.
- *"Petakan dulu semua yang terdampak sebelum menyentuh satu file pun"* → mencegah efek domino.

**⑤ Minta DIBANTAH — penawar sifat mengiyakan.**
Claude punya kecenderungan menyetujui ide Anda. Untuk keputusan penting, netralkan:
> *"Apa kelemahan pendekatan ini? Apa yang bisa salah 3 bulan lagi? Kalau usulanku buruk, bantah dengan alasan."*
> *"Beri 2–3 opsi + kelebihan-kekurangan + rekomendasimu + alasannya."*

Keputusan yang selamat dari bantahan = keputusan yang kuat.

**⑥ Saat Claude melanggar aturan / kerja asal: koreksi PRESISI, lalu patenkan.**
Kemarahan panjang tidak memperbaiki apa pun; koreksi presisi memperbaiki selamanya:
1. Hentikan (`Esc`), sebutkan persis apa yang dilanggar.
2. > *"Catat pelanggaran ini di `CLAUDE.md`/memory sebagai aturan yang diperkuat — lengkap dengan KENAPA-nya — dan terapkan sekarang pada objek temuannya."*
3. Sesi berikutnya, uji: *"sebutkan aturan kerja yang relevan untuk tugas ini sebelum mulai"* — kalau tidak bisa menyebut, jangan beri mandat.

Beginilah aturan proyek tumbuh dari pengalaman nyata, bukan dari daftar teoretis di hari pertama.

**⑦ Jaga "kondisi kerja" Claude — kepatuhan juga soal konteks.**
- **Mandat besar selalu di sesi segar** — meja penuh membuat perhatian terhadap aturan ikut terdesak.
- **Satu mandat eksekusi dalam satu waktu.** Menumpuk 5 tugas dalam satu perintah = kualitas terbagi 5. (Menggabung 5 *pertanyaan* justru bagus — bedakan bertanya vs menyuruh, №6-⑥.)
- **Akhiri tiap batch dengan pencatatan** (PROGRESS.md) — Claude yang "membaca sejarahnya sendiri" di sesi baru bekerja jauh lebih patuh daripada yang mulai dari nol.

### Anti bom-waktu yang paling sering terlewat (masing-masing pernah menghancurkan proyek orang)

1. **Rahasia (API key, password) HANYA di file `.env`** — tidak pernah di dalam kode, tidak pernah masuk git, tidak pernah tampil di chat. Minta Claude pasang pagarnya sejak Fase 1 (`.gitignore` + contoh `.env.example`). Kunci yang pernah bocor = anggap sudah dicuri → ganti.
2. **Dilarang mengedit kode langsung di server.** Alur satu-satunya: kerjakan LOKAL → validasi → commit → deploy via skrip resmi (buat skripnya sekali di langkah 14, lengkap dengan cek kesehatan otomatis). Edit tangan di server = perubahan tak tercatat = tak bisa diulang = bom waktu.
3. **Backup database SEBELUM setiap migrasi produksi.** Migrasi salah tanpa backup = data pelanggan hilang permanen. Jadikan bagian skrip deploy, bukan ingatan manusia.
4. **Resep TEPAT WAKTU = disiplin lingkup, bukan kerja lembur.** Setiap item backlog diuji satu pertanyaan: *"apakah ini memblok rilis / pengguna berbayar pertama?"* TIDAK → turunkan ke bawah backlog (fase pasca-rilis). Musuh jadwal proyek besar bukan kelambatan — melainkan perfeksionisme pada hal yang tidak memblok rilis.

### Aturan emas proyek besar (rangkuman satu layar)

1. **Distilasi sekali, baca per-modul selamanya** — jangan pernah menelan PRD utuh tiap sesi.
2. **Pondasi & DB diketok sebelum fitur pertama** — bagian termahal untuk diubah belakangan.
3. **Iris vertikal**: 1 batch = 1 fitur tembus DB→BE→FE = 1 commit.
4. **Desain disetujui sebelum diimplementasi** (Claude Design dulu, kode belakangan).
5. **"Selesai" = test lulus + bukti runtime** — bukan "build sukses".
6. **Backlog tunggal** = satu-satunya daftar kerja; temuan baru masuk backlog, bukan dikerjakan sekalian.
7. **Gerbang otomatis = mata Anda**: `/code-review` + `/security-review` + audit berkala — 100% vibe coding hanya aman bila gerbang ini tidak pernah dilewati.
8. **Batch tanpa entri `PROGRESS.md` = batch belum selesai** — 3 dokumen hidup adalah ingatan permanen proyek; merawatnya bukan administrasi, melainkan syarat kelangsungan.
9. **Tepat waktu = disiplin lingkup:** yang tidak memblok rilis → turun ke bawah backlog.
10. **Ekspektasi realistis:** proyek 200 halaman = berbulan-bulan kerja per-batch + biaya token besar — pantau `/usage` per batch, dan nikmati kemajuan yang terukur, bukan sprint buta.

### 📋 Template `CLAUDE.md` siap COPY-PASTE untuk proyek besar Anda

> **Cara pakai (langkah 4 checklist):** salin seluruh blok di bawah → simpan sebagai `CLAUDE.md` di folder akar proyek baru → suruh Claude mengisi bagian §7 saat Fase 1.
> ⚠️ **Yang ditaruh di akar proyek HANYA `CLAUDE.md` ini** — file panduan lengkap (dokumen yang sedang Anda baca) adalah buku pegangan OWNER, bukan SOP mesin: jangan jadikan dua sumber kebenaran. Bila ingin ikut di repo, simpan sebagai referensi di `docs/` — Claude hanya terikat pada `CLAUDE.md`. Template ini adalah SOP panduan ini dalam bentuk PASAL MENGIKAT — otomatis termuat & wajib dipatuhi Claude di setiap sesi. Setiap pasal punya ukuran lulus/gagal (aturan terukur = aturan yang dipatuhi, lihat "Seni memberi prompt" ②). Aturan baru yang lahir selama proyek dipatenkan ke file ini juga (teknik ① & ⑥).

````markdown
# ⚖️ ATURAN KERJA — kontrak Claude ↔ owner (auto-dimuat tiap sesi)

> Satu aturan = satu pasal, dengan ukuran lulus/gagal. **Ada satu butir gagal → STOP: jangan lanjut / jangan sebut selesai.**
> Owner non-teknis dan TIDAK membaca kode — kualitas dijaga oleh GERBANG di dokumen ini, bukan oleh review manusia.
> Sebelum menyentuh apa pun → §2. Sebelum bilang "selesai" → §3.

## §1 SUMBER KEBENARAN
1. Daftar kerja = HANYA `BACKLOG.md` (item + dependensi + status + kolom REALISASI berisi commit + bukti).
2. Sejarah & posisi terakhir = `PROGRESS.md` (jurnal kronologis, entri terbaru di ATAS).
3. Rencana per-modul = `docs/spec/`. Kebenaran bisnis = `docs/PRD/` — bila bertentangan dengan spec → perbaiki spec + catat keputusannya di PROGRESS.md.
4. Fakta perilaku sistem = KODE + DB LIVE (introspeksi langsung) — bukan ingatan atau dokumen yang bisa basi.
5. Awal SETIAP sesi: baca `PROGRESS.md` entri teratas + `BACKLOG.md` → lapor posisi → tunggu arahan.

## §2 GERBANG PRE-TOUCH (sebelum menyentuh apa pun)
1. **Paham dulu:** baca spec modul terkait + petakan SEMUA permukaan terdampak (DB, BE, FE). *Lulus bila:* bisa menyebut persis file/tabel/alur yang akan disentuh — tanpa menebak, tanpa "coba dulu".
2. **Otorisasi:** belum ada persetujuan owner → susun proposal (temuan + opsi + trade-off + rekomendasi) → TUNGGU jawaban. Ada mandat → kerjakan PERSIS lingkup itu. Pilihan teknis kecil yang reversible di dalam mandat → putuskan sendiri, sebutkan di laporan.
3. **Temuan baru di tengah kerja → masuk `BACKLOG.md` sebagai usulan.** DILARANG dikerjakan "sekalian".
4. **Pesan owner masuk di tengah kerja = INTERRUPT:** berhenti, jawab dulu, baru lanjut.
5. **Urutan fase proyek WAJIB:** distilasi PRD → pondasi → DB → desain (Claude Design) → pembangunan per modul (iris vertikal DB→BE→FE). DILARANG mengerjakan fase apa pun sebelum gerbang fase sebelumnya diketok owner. FE hanya boleh dibangun mengikuti prototype yang sudah diketok.

## §3 GERBANG PRE-DONE (sebelum bilang "selesai" / commit / deploy)
1. **Bukti runtime:** klaim "jalan" hanya setelah dieksekusi dengan data/perilaku NYATA (log, isi DB, tampilan berubah). Build/kompilasi lulus BELUM memenuhi butir ini.
2. **Test:** fitur baru wajib test otomatis; seluruh test suite lulus.
3. **Config-driven:** nilai bisnis (harga, batas, kuota, model AI) dibaca dari config/DB — nol hardcode di kode. Kegagalan komponen = berhenti + bersuara; DILARANG fallback senyap.
4. **Koheren per-sistem:** rantai DB→BE→FE satu logika; nol duplikat, nol kode mati tersisa dari pekerjaan ini.
5. **UI:** dilarang menambah/mengubah/menghapus elemen UI di luar prototype/mandat tanpa izin owner.
6. **Tutup administrasi:** centang item `BACKLOG.md` + isi REALISASI (commit + bukti) + tulis entri `PROGRESS.md` dengan format:
   `## [tanggal] — [modul] (Batch N) SELESAI` · Dikerjakan: … · Bukti: test X/X + [bukti runtime] + commit [hash] · Keputusan: … · Berikutnya: …
   **Batch tanpa entri PROGRESS = batch BELUM selesai.**

## §4 PELAPORAN (setiap komunikasi ke owner)
1. Bahasa dampak-bisnis, nol jargon; jargon teknis yang tak terhindarkan dijelaskan sekali dalam bahasa awam.
2. Pisahkan tegas: SELESAI / opsional / risiko tersisa. Dilarang over-claim. Tidak yakin → katakan tidak yakin.
3. Untuk keputusan penting: sajikan 2–3 opsi + kelebihan-kekurangan + rekomendasi beralasan; sebutkan juga kelemahan usulan owner bila ada.

## §5 KEAMANAN & DEPLOY
1. Rahasia (API key, password) HANYA di `.env` (terdaftar di `.gitignore`; sediakan `.env.example`). Dilarang muncul di kode, di git, dan di chat (redact).
2. Alur deploy SATU-SATUNYA: LOKAL (WSL) → validasi lulus §3 → commit → push GitHub → deploy ke VPS via skrip resmi dengan cek kesehatan otomatis. DILARANG mengedit kode langsung di server.
3. Backup database SEBELUM setiap migrasi produksi — bagian dari skrip deploy, bukan ingatan.
4. SEMUA file/aset upload disimpan HANYA di storage S3-compatible — dilarang di disk server aplikasi, dilarang di DB.

## §6 KOMPAS (pemecah kebuntuan)
1. Prioritas: *"apakah ini memblok rilis / pengguna berbayar pertama?"* — TIDAK → usulkan turunkan ke bawah backlog.
2. Konflik "cukup" vs "benar": pilih benar; bila memperluas kerja → kembali ke §2.2 (proposal, bukan diam-diam).
3. Aturan baru dari owner → langsung diterapkan pada objek temuannya + dipatenkan ke file ini DI SESI YANG SAMA (dicatat saja = belum selesai).

## §7 FAKTA PROYEK (stack = STANDAR owner; sisanya diisi Claude saat Fase 1, dirawat sepanjang proyek)
- Nama proyek & tujuan bisnis: [ISI]
- **Stack STANDAR (ketetapan owner — penyimpangan apa pun wajib proposal → ketok owner):**
  DB + Auth = Supabase (PostgreSQL, multi-tenant via RLS) · BE = Node.js · FE = React + Next.js + Tailwind (+ shadcn/ui) ·
  Git = GitHub · Dev = WSL Ubuntu 22.04 · Prod = VPS Ubuntu 22.04 (BiznetGio) · Aset = S3-compatible (BiznetGio)
- Catatan FE: komponen prototype Claude Design (React) DIPAKAI LANGSUNG — kerja FE = wiring (data/auth/state/i18n/test), DILARANG menulis ulang tampilan yang sudah diketok.
- Tabel data kompleks (sort/filter/pagination/seleksi) WAJIB **TanStack Table** + balutan shadcn/ui. DILARANG logika tabel manual atau pustaka tabel lain tanpa proposal → ketok owner.
- Dokumen konteks & SEMUA draft prompt untuk Claude Design wajib mencantumkan standar teknis FE di atas; draft prompt layar ber-tabel wajib menyebut TanStack Table eksplisit — agar desain lahir sesuai kemampuan nyata komponennya.
- Struktur folder: [ISI]
- Perintah: build [ISI] · test [ISI] · jalankan lokal [ISI]
- Cara deploy resmi: [ISI setelah skrip deploy dibuat]
- Keputusan arsitektur penting: [tambah seiring proyek, satu baris per keputusan + tanggal]
````

> ⚠️ **Kejujuran tentang "taat 100%":** `CLAUDE.md` menjamin aturan SELALU terbaca di setiap sesi — itu fondasinya. Ketaatan maksimal dicapai saat dipadukan dengan peran Anda sebagai pengetok: ritual pembuka tugas besar (teknik ③), minta bukti (teknik ④), dan koreksi-lalu-patenkan saat ada pelanggaran (teknik ⑥). Kontrak + pengawasan gerbang = sistem yang membuat pelanggaran sulit lolos.

### 📕 Kamus istilah (untuk orang awam)

| Istilah | Artinya secara sederhana |
|---|---|
| **Repo** | "Kotak proyek" — folder berisi seluruh kode + riwayat perubahannya (git) |
| **Commit** | Titik simpan permanen, seperti *save point* di game — bisa kembali ke sini kapan pun |
| **Stack** | Paket pilihan teknologi proyek (bahasa, framework, database) — diputuskan sekali di awal |
| **DB / database** | Lemari data aplikasi: data pelanggan, transaksi, konten |
| **Migrasi (DB)** | "Berita acara" resmi setiap perubahan bentuk lemari data — bernomor urut, bisa dilacak & diulang |
| **BE / backend** | Dapur aplikasi — logika & mesin yang tidak terlihat pengguna |
| **FE / frontend** | Ruang tamu aplikasi — semua yang dilihat & diklik pengguna |
| **Multi-tenant** | Satu aplikasi dipakai banyak pelanggan, data mereka TERPISAH rapat — wajib untuk SaaS, dirancang sejak awal |
| **Iris vertikal** | Membangun 1 fitur tembus dapur-sampai-ruang-tamu, bukan menyelesaikan seluruh dapur dulu |
| **Backlog** | Daftar kerja tunggal ber-status — satu-satunya sumber "apa selanjutnya" |
| **Spec (modul)** | Ringkasan 2–5 halaman: apa yang harus dibangun untuk satu bagian aplikasi |
| **Test / test suite** | Pemeriksa otomatis — sekali ditulis, selamanya menjaga fitur tidak diam-diam rusak |
| **Bukti runtime** | Bukti fitur JALAN sungguhan (log, data masuk DB, tampilan berubah) — bukan sekadar "tidak error saat dibangun" |
| **Design system** | Kesepakatan visual: warna, huruf, bentuk tombol — supaya semua halaman senada |
| **Prototype** | Contoh tampilan yang bisa dilihat & disetujui SEBELUM dikodekan |
| **Deploy** | Menerbitkan aplikasi ke server supaya bisa diakses publik |
| **Hardcode** | Nilai penting "dipatri mati" di dalam kode (harga, batas kuota) — bom waktu; harusnya di config/DB |
| **Fallback senyap** | Sistem gagal tapi diam-diam "pura-pura jalan" pakai jalur cadangan — bom waktu paling berbahaya |
| **Vibe coding** | Membangun aplikasi sepenuhnya lewat percakapan dengan AI, tanpa menulis kode sendiri — aman HANYA dengan gerbang kualitas №10 |
| **PRD** | *Product Requirements Document* — dokumen lengkap berisi semua kebutuhan & aturan bisnis produk |
| **RLS** | *Row Level Security* (fitur Supabase/PostgreSQL) — penjaga di pintu lemari data: setiap tenant hanya bisa melihat barisnya sendiri |
| **Next.js** | Kerangka kerja React untuk membangun aplikasi web utuh (halaman, routing, rendering) — jalan di Node.js |
| **Tailwind + shadcn/ui** | Bahasa styling + kumpulan komponen siap-pakai yang kodenya jadi MILIK repo Anda — bahan yang sama dengan output Claude Design |
| **TanStack Table** | Mesin tabel data standar React (sort/filter/pagination) — wajib untuk semua tabel kompleks (lihat Stack Standar) |

---
*Bagian 1–9 universal — berlaku di proyek mana pun. Bagian 10 mengikat ke STACK STANDAR ketetapan owner (Supabase · Node.js · React + Next.js + Tailwind · GitHub · WSL/VPS Ubuntu 22.04 · S3-compatible). Aturan main tiap proyek hidup di `CLAUDE.md`-nya (lihat №2; untuk proyek besar pakai Template 📋 di №10 yang stack-nya sudah terisi).*
