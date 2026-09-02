"""Saklar "Judul pembuka" dilarang menjanjikan sesuatu yang tidak dilakukan mesin.

LAHIR DARI KELUHAN TENANT 2026-09-02 ("sudah saya matikan, kontennya masih ada judul pembuka").
Mesin TERBUKTI benar — saklar sampai ke renderer sebagai False dan judul tidak digambar. Yang
salah adalah JANJI DI LAYAR.

Ada DUA hal berbeda yang sama-sama bernama "hook", keduanya lahir dari `script["hook"]` yang SAMA
(`video_renderer.py:911`):
  • TULISAN judul di layar — digambar FFmpeg drawtext; INI yang dimatikan saklar tsb;
  • KALIMAT pembuka — tetap diucapkan narator dan tetap muncul sebagai subtitle.

Layar dulu berbunyi "matikan = video langsung mulai". Videonya TIDAK langsung mulai: kalimat
pembukanya tetap terdengar. Janji itulah yang melahirkan keluhan — tenant menilai mesin bohong,
padahal layarnya yang bohong.

Uji ini mengunci: kalimat palsu itu tak boleh kembali, dan penggantinya WAJIB menyebut bahwa
kalimat pembuka tetap ada — dalam DUA bahasa.
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


def _blok_kartu_hook(isi: str) -> str:
    i = isi.find("Judul pembuka (hook)")
    assert i != -1, "kartu Judul pembuka tak ditemukan — struktur layar berubah"
    j = isi.find("Caption (subtitle video)", i)
    return isi[i : j if j != -1 else i + 6000]


class TestJanjiPalsuTakBolehKembali(unittest.TestCase):
    def setUp(self):
        self.blok = _blok_kartu_hook(_isi(LAYAR))

    def test_kalimat_video_langsung_mulai_sudah_tiada(self):
        """Janji yang dibantah mesin: kalimat pembuka TETAP diucapkan saat saklar mati."""
        for palsu in ("video langsung mulai", "starts straight away"):
            with self.subTest(kalimat=palsu):
                self.assertNotIn(
                    palsu, self.blok,
                    f'layar masih menjanjikan "{palsu}" — padahal kalimat pembuka tetap terdengar.',
                )

    def test_penjelasan_saklar_menyebut_kalimat_pembuka_tetap_ada(self):
        """Dwibahasa — tenant ID dan EN sama-sama berhak tahu apa yang SEBENARNYA dimatikan."""
        i = self.blok.find("Tampilkan judul")
        self.assertNotEqual(i, -1, 'baris saklar "Tampilkan judul" tak ditemukan')
        sub = self.blok[i : i + 700]
        self.assertRegex(
            sub, r"(diucapkan|terdengar|suara)",
            "penjelasan Indonesia tidak menyebut bahwa kalimat pembuka tetap diucapkan.",
        )
        self.assertRegex(
            sub, r"(spoken|voice|narrat)",
            "penjelasan Inggris tidak menyebut bahwa kalimat pembuka tetap diucapkan.",
        )

    def test_pratinjau_saat_mati_tidak_mengesankan_pembuka_hilang_total(self):
        """Kotak pratinjau adalah tempat kedua tenant menyimpulkan 'tidak ada apa-apa lagi'."""
        i = self.blok.find("dimatikan")
        self.assertNotEqual(i, -1, "teks pratinjau saat saklar mati tak ditemukan")
        sekitar = self.blok[max(0, i - 260) : i + 400]
        self.assertRegex(
            sekitar, r"(diucapkan|terdengar|subtitle)",
            "pratinjau saat mati tak menjelaskan kalimat pembuka tetap ada — "
            "tenant menyimpulkan pembukanya hilang total.",
        )


if __name__ == "__main__":
    unittest.main()
