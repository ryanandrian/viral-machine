"""Dokumen tak boleh menunjuk berkas/memory yang SUDAH TIDAK ADA.

MASALAH YANG DIJAGA (ditemukan 2026-08-05 saat membaca `SISA_KERJA_GO_LIVE.md` BARIS DEMI BARIS atas
perintah owner: *"jangan asal baca, teliti setiap baris dari awal hingga akhir"*)

`SISA_KERJA_GO_LIVE.md` §0 — berkas yang **setiap sesi baru baca PERTAMA** — memuat blok berjudul
*"ATURAN KERJA LENGKAP — 18 memory (WAJIB patuh)"* lalu mendaftar 18 rujukan `[[feedback_*]]`.
Diperiksa satu per satu: **18 dari 18 TIDAK ADA.** Ke-24 berkas `feedback_*` dipusatkan ke `CLAUDE.md`
lalu dibuang **2026-07-15** atas perintah owner ("pusatkan 1 lokasi, buang fosil") — dan blok itu
**tak pernah ikut diperbarui**, bertahan **3 minggu**.

Akibatnya sesi baru diperintahkan mematuhi aturan yang tak bisa ia buka ⇒ ia **menebak**. Inilah bentuk
"dokumen basi tapi terkesan hidup" yang owner sebut paling merusak: bukan salah tulis, tapi **perintah
yang menunjuk ke ruang kosong**.

Uji ini menjaga DUA arah rujukan yang bisa diverifikasi tanpa tafsir:
  • `[[nama_memory]]` → berkas `memory/nama_memory.md` harus ada
  • `` `path/berkas.ext` `` → berkas harus ada di repo
Rujukan yang berada di dalam blok koreksi/peta-silang DIKECUALIKAN (justru sedang menjelaskan bahwa
berkasnya tiada) — dikenali dari penanda di baris yang sama.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = "/home/rad/.claude/projects/-home-rad-viral-machine/memory"

# Dokumen yang WAJIB bersih dari rujukan hantu: yang dibaca sesi baru sebagai perintah.
# (Dokumen arsip/histori boleh menyebut berkas lama — itu memang catatan sejarah.)
WAJIB_BERSIH = ["SISA_KERJA_GO_LIVE.md", "CLAUDE.md"]

# Penanda bahwa baris itu sedang MENJELASKAN berkasnya tiada (bukan memerintahkan membacanya).
PENANDA_KOREKSI = re.compile(
    r"SUDAH TIDAK ADA|TIDAK ADA|TIADA|HILANG|dibuang|DICABUT|peta-silang|RANJAU|"
    r"tak pernah|BASI|dihapus", re.I)

# Baris RENCANA menyebut berkas yang memang BELUM dibangun — itu sah, bukan rujukan hantu.
# (Diverifikasi 05-Agu: `src/config/system_secrets.py` di item S2 dan `reels_publisher.py`/
#  `tiktok_publisher.py`/`base_publisher.py` di item multi-platform — semuanya baris PLAN.)
# Tanpa pengecualian ini, uji akan menuntut penghapusan rencana yang sah = merusak dokumen.
PENANDA_RENCANA = re.compile(r"\bPLAN\b|RENCANA|akan dibangun|\bNEW\b|belum dibangun|setelah diputuskan",
                             re.I)


def _baris(dok: str):
    p = os.path.join(AKAR, dok)
    return open(p, encoding="utf-8", errors="ignore").read().split("\n")


class TestPemindaiBenar(unittest.TestCase):
    """Pagar-untuk-pagar: alat ukur yang salah lebih berbahaya daripada tak mengukur
    (terbukti 6× dalam satu sesi 04/05-Agu)."""

    def test_dokumen_wajib_bersih_memang_ada(self):
        for d in WAJIB_BERSIH:
            self.assertTrue(os.path.exists(os.path.join(AKAR, d)), f"{d} tak ditemukan")

    def test_folder_memory_terbaca(self):
        self.assertTrue(os.path.isdir(MEM), f"folder memory tak terbaca: {MEM}")
        self.assertGreaterEqual(len(glob.glob(os.path.join(MEM, "*.md"))), 5,
                                "folder memory nyaris kosong — pemindai jadi hijau-palsu")


class TestTakAdaRujukanHantu(unittest.TestCase):

    def test_rujukan_memory_masih_ada(self):
        hantu = []
        for dok in WAJIB_BERSIH:
            for i, baris in enumerate(_baris(dok), 1):
                # Penanda koreksi diperiksa pada baris TANPA rujukannya sendiri. Tanpa ini, sebuah
                # rujukan bisa MEMBERI PENGECUALIAN PADA DIRINYA SENDIRI — terbukti 05-Agu: rujukan
                # palsu `[[feedback_yang_sudah_dibuang]]` LOLOS karena namanya memuat kata "dibuang"
                # yang ada di daftar penanda. Celah itu membuat penjaga ini buta pada kelas nama
                # tertentu; ditutup dengan membuang teks rujukan sebelum mencocokkan penanda.
                tanpa_rujukan = re.sub(r"\[\[[a-z0-9_]+\]\]", "", baris)
                if PENANDA_KOREKSI.search(tanpa_rujukan):
                    continue                      # baris ini sedang MENJELASKAN, bukan memerintah
                for nama in re.findall(r"\[\[([a-z0-9_]+)\]\]", baris):
                    if not os.path.exists(os.path.join(MEM, f"{nama}.md")):
                        hantu.append(f"{dok}:{i} → [[{nama}]]")
        self.assertFalse(
            hantu,
            "Dokumen memerintahkan membaca memory yang TIDAK ADA:\n  " + "\n  ".join(hantu[:15])
            + "\nSesi baru akan mencarinya, tak menemukan, lalu MENEBAK — itu akar 'dokumen basi tapi "
              "terkesan hidup'. Perbaiki rujukannya, ATAU beri penanda bahwa berkasnya sudah tiada.")

    def test_rujukan_berkas_repo_masih_ada(self):
        hantu = []
        for dok in WAJIB_BERSIH:
            baris_semua = _baris(dok)
            for i, baris in enumerate(baris_semua, 1):
                # Blok RENCANA sering multi-baris: penanda "**PLAN:**" di baris induk, berkasnya di
                # sub-butir di bawahnya (mis. [B1] S1-S4). Karena itu konteks 6 baris ke ATAS ikut
                # diperiksa — versi pertama uji ini hanya melihat satu baris dan salah menuduh
                # `src/config/system_secrets.py` (baris 258) sebagai hantu, padahal ia sub-butir PLAN
                # dari item [B1] yang statusnya ⬜ belum dikerjakan.
                konteks = "\n".join(baris_semua[max(0, i - 7):i])
                if PENANDA_KOREKSI.search(baris) or PENANDA_RENCANA.search(konteks):
                    continue                      # koreksi ATAU rencana (berkas belum dibangun) = sah
                for jalur in re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|ts|tsx|sql|sh|md))`", baris):
                    j = jalur.lstrip("./")
                    if os.path.exists(os.path.join(AKAR, j)):
                        continue
                    if glob.glob(os.path.join(AKAR, "**", os.path.basename(j)), recursive=True):
                        continue                  # disebut tanpa jalur penuh — masih ada di repo
                    if os.path.exists(os.path.join(MEM, os.path.basename(j))):
                        continue                  # berkas memory
                    hantu.append(f"{dok}:{i} → {jalur}")
        self.assertFalse(
            hantu,
            "Dokumen menunjuk BERKAS yang tidak ada di repo:\n  " + "\n  ".join(hantu[:15])
            + "\nBila berkasnya memang sudah dibuang, tulis penandanya di baris itu (mis. 'SUDAH TIDAK "
              "ADA'/'dibuang') supaya pembaca tak mengejar ruang kosong.")


class TestBlokAturanMenunjukSumberYangHidup(unittest.TestCase):
    """Blok §0 SISA_KERJA pernah memerintahkan 18 memory yang tiada selama 3 minggu.
    Sekarang ia WAJIB menunjuk `CLAUDE.md`. Bila penunjuk itu hilang lagi, sesi baru kembali buta."""

    def test_blok_aturan_menunjuk_claude_md(self):
        t = "\n".join(_baris("SISA_KERJA_GO_LIVE.md"))
        m = re.search(r"### 📏 ATURAN KERJA LENGKAP(.{0,1200})", t, re.S)
        self.assertIsNotNone(m, "blok 'ATURAN KERJA LENGKAP' hilang dari SISA_KERJA §0")
        blok = m.group(1)
        self.assertIn("CLAUDE.md", blok,
                      "blok aturan tak lagi menunjuk CLAUDE.md — sesi baru kembali mengejar memory yang tiada")
        self.assertRegex(blok, r"18 dari 18|SUDAH TIDAK ADA",
                         "peringatan bahwa 18 memory itu tiada telah dicabut — ranjau lahir kembali")


if __name__ == "__main__":
    unittest.main(verbosity=2)
