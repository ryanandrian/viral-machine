"""Saat channel berubah dari TERHENTI → BERJALAN, tenant wajib DIBERI TAHU.

LAHIR DARI KEJADIAN 6–11 SEP 2026 (kronologi owner, kata-katanya sendiri):
  1. ganti TTS ElevenLabs→OpenAI, lupa memilih karakter suara — **tapi bisa tetap di-save**
     ⇒ channel jatuh tak-lengkap, produksi berhenti 6 hari (ditutup B33: save kini menolak)
  2. owner memilih karakter suara lalu Save
  3. *"setelah saya save jeda otomatis terbuka dan producer langsung bekerja TANPA PENGETAHUAN SAYA"*
  4. *"di bagian atas channel masih ada tombol uji yang mana biasanya untuk melepas jeda harus lulus
     uji dulu"* ⇒ owner menekan uji
  5. uji mengantre di belakang 2 produksi yang owner tak tahu sedang berjalan ⇒ **12 menit**

AKAR — terbukti di kode, bukan teori: layar **SUDAH memegang** `rd.ready` (hasil `channel_readiness`,
disegarkan tiap `load()`), jadi ia TAHU channel berubah dari tak-siap → siap. Tapi yang ia katakan
sesudah menyimpan hanyalah satu kata: **"Tersimpan"** (`saveAiPart`). Tenant yang baru memperbaiki
channel mati 6 hari tidak diberi tahu apa yang terjadi berikutnya, lalu MENEBAK — dan tebakannya
wajar: tombol uji masih terpampang, berarti harus uji.

**Layar tahu, tapi tidak memberi tahu.** Itu akarnya — bukan rebutan slot (itu akibat, sudah ditutup
terpisah), bukan pula tombol uji yang salah tempat.

KENAPA PEMBERITAHUANNYA DI `load()`, BUKAN DI TIAP TOMBOL SIMPAN: kelengkapan bisa berubah lewat
BANYAK pintu (kartu Naskah · Suara · Visual · kartu Pengaturan channel · jadwal · koneksi YouTube).
Menaruhnya di tiap tombol = 6 salinan yang pasti melenceng. `load()` dipanggil sesudah SEMUA jalur
simpan ⇒ satu tempat, mustahil ada pintu yang terlewat. Nol kueri tambahan (rd memang sudah dimuat).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestPerubahanKeadaanDikomunikasikan(unittest.TestCase):
    def setUp(self):
        self.l = _tanpa_komentar(_isi(LAYAR))

    def test_layar_membandingkan_kesiapan_SEBELUM_dan_SESUDAH(self):
        """Tanpa membandingkan, layar tak bisa tahu bahwa keadaan BERUBAH — ia hanya tahu
        keadaan sekarang."""
        i = self.l.find('rpc("channel_readiness"')
        self.assertNotEqual(i, -1, "pembacaan kesiapan tak ditemukan di layar")
        blok = self.l[max(0, i - 300): i + 900]
        self.assertRegex(
            blok, r"(pulih|sebelumnya|prevReady|rdRef)",
            "layar memuat ulang kesiapan tapi tak pernah membandingkannya dengan keadaan "
            "sebelumnya ⇒ perubahan 'terhenti → berjalan' lewat tanpa satu kata pun.",
        )

    def test_tenant_diberi_tahu_produksi_berjalan_sendiri(self):
        """Inti: sesudah channel pulih, tenant harus tahu (a) channel sudah lengkap,
        (b) produksi jalan sendiri, (c) TIDAK perlu menjalankan uji."""
        # JANGKAR DIPERBAIKI: pembandingan keadaan ada di `load()`, tapi KALIMATNYA ada di bagian
        # tampilan (JSX) — dua tempat berbeda. Yang diikat di sini = tempat kalimatnya dirender.
        i = self.l.find("pulihMsg &&")
        self.assertNotEqual(i, -1, "kabar pemulihan tak pernah dirender ke layar")
        blok = self.l[i: i + 1600]
        self.assertRegex(
            blok, r"(otomatis|jalan sendiri)",
            "tenant tak diberi tahu bahwa produksi berjalan sendiri sesudah channel lengkap.",
        )
        # DIPERKUAT SESUDAH SABOTASE: versi pertama memakai `ID|EN` sehingga TETAP HIJAU saat
        # kalimat Indonesia dicabut — versi Inggris menutupinya. Tenant berbahasa Indonesia justru
        # yang paling butuh. Kedua bahasa kini diikat TERPISAH.
        self.assertIn(
            "tidak perlu menjalankan uji", blok,
            "kalimat Indonesia 'tidak perlu menjalankan uji' hilang — inilah yang membuat owner "
            "menekan uji lalu mengantre 12 menit.",
        )
        self.assertIn(
            "no test run needed", blok,
            "padanan Inggrisnya hilang — tenant berbahasa Inggris tetap salah-sangka.",
        )
        self.assertRegex(
            blok, r"<Bi\s+id=\"[^\"]+\"\s+en=\"[^\"]+\"|id:\s*\"[^\"]+\",\s*en:",
            "pemberitahuan tidak dwibahasa.",
        )

    def test_hanya_muncul_saat_BERUBAH_bukan_tiap_muat(self):
        """Kalau muncul tiap kali halaman dimuat, ia jadi kebisingan yang diabaikan —
        dan pesan yang diabaikan sama saja dengan tak ada pesan."""
        i = self.l.find('rpc("channel_readiness"')
        blok = self.l[max(0, i - 300): i + 1400]
        self.assertRegex(
            blok, r"===\s*false|!\s*\w+\.ready|\?\.ready\s*===\s*false",
            "pemberitahuan tak bersyarat 'sebelumnya TIDAK siap' ⇒ muncul tiap muat halaman.",
        )


class TestKonfirmasiUjiMenyebutKemungkinanAntre(unittest.TestCase):
    """Lapis kedua: bila tenant TETAP menekan uji, ia harus tahu konsekuensinya SEBELUM menekan —
    bukan sesudah, saat layar sudah berputar 'Menunggu giliran…'."""

    def test_pesan_konfirmasi_menyebut_antre_bila_mesin_sibuk(self):
        l = _tanpa_komentar(_isi(LAYAR))
        i = l.find("confirmMessage=")
        self.assertNotEqual(i, -1, "pesan konfirmasi uji tak ditemukan")
        blok = l[i: i + 900]
        self.assertRegex(
            blok, r"(antre|mengantre|queue)",
            "pesan konfirmasi uji tak menyebut kemungkinan mengantre — tenant menekan tanpa "
            "tahu mesin mungkin sedang sibuk (owner: menunggu 12 menit tanpa tahu sebabnya).",
        )


if __name__ == "__main__":
    unittest.main()
