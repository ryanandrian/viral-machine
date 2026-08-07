"""Adegan gambar yang GAGAL tidak boleh disamarkan jadi masalah durasi.

RANTAI KERUSAKAN YANG DIJAGA (dipetakan ujung-ke-ujung 2026-08-07/08)

    penyedia menolak/kehabisan kredit
      → penangkap adegan MEMBUANG sebabnya, mencoba tulis-ulang 3× (sia-sia bila kredit habis)
      → adegan dilewati, perakit tetap melapor "✅ berhasil"
      → perender menyusun durasi dari JUMLAH klip, bukan isinya
      → video 22,7 dtk lebih pendek dari narasi — cerita tenant TERPOTONG DI TENGAH
      → QC menamainya "Durasi kependekan" ⇒ tenant menyalahkan MesinViral
      → masuk gudang sebagai stok ⇒ menyumbat slot 72 jam ⇒ channel diam 3 hari

TERUKUR DI PRODUKSI: 23 adegan dilewati · 5 run rusak sejak 27-Jul · 12 dari 180 render kehilangan
gambar (yang terparah 34,4 dtk) · run 3-Agu RETRO REWIND: berkas jadi 36,7 dtk sementara narasinya
58,3 dtk ⇒ ±21 detik cerita tidak ikut.

KENAPA INI BUKAN MASALAH DURASI: pada run itu SELURUH rantai durasi benar — naskah 167 kata (resep
133-163) · gerbang hulu lolos (proyeksi 60,8s) · audio nyata 55,8s · gerbang pra-visual lolos ·
perender menghitung 58,3s. Yang hilang GAMBARNYA. Label "durasi" itulah yang membuat belasan kali
perbaikan durasi tak pernah menuntaskan apa pun — diperbaiki di rantai yang tidak bersalah.

EMPAT ATURAN YANG DIJAGA BERKAS INI:
  A. Sebab kegagalan adegan WAJIB tersimpan (dulu dibuang satu baris setelah dibuat).
  B. Klip kurang dari jumlah bagian naskah = GAGAL JUJUR — bukan video pendek yang tetap dikirim.
  C. Sebab yang MUSTAHIL sembuh dengan diulang (kredit/tagihan/kunci/model) tidak diulang 3×;
     mengulang hanya membakar sisa jatah tenant.
  D. Produksi yang klipnya LENGKAP tidak boleh ikut terpengaruh (anti-regresi — 168 dari 180 render
     sehat wajib tetap jalan).
"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTOR = os.path.join(AKAR, "src", "providers", "visual", "ai_image.py")

# Sampel VERBATIM dari worker.log produksi (aturan proyek: sampel dari produksi, bukan karangan).
SAMPEL_BILLING = ("Error code: 400 - {'error': {'message': 'Billing hard limit has been reached.', "
                  "'type': 'billing_limit_user_error', 'code': 'billing_hard_limit_reached'}}")
SAMPEL_CF_429 = 'Cloudflare image HTTP 429: {"errors":[{"code":10000,"message":"Rate limit"}]}'


def _teks(p):
    return open(p, encoding="utf-8", errors="ignore").read()


class TestPemindaiBenar(unittest.TestCase):
    """Pagar-untuk-pagar: alat ukur yang salah lebih berbahaya daripada tak mengukur."""

    def test_berkas_ada(self):
        self.assertTrue(os.path.exists(ADAPTOR), f"adaptor gambar tak ditemukan: {ADAPTOR}")

    def test_sampel_memang_sampel_produksi(self):
        self.assertIn("billing_hard_limit_reached", SAMPEL_BILLING)
        self.assertIn("429", SAMPEL_CF_429)


class TestA_SebabAdeganGagalTersimpan(unittest.TestCase):
    """Sebab kegagalan dibuat lengkap oleh adaptor, lalu DIBUANG satu baris kemudian — sama persis
    dengan cacat yang ditutup 06-Agu di jalur pesan penyedia."""

    def test_ada_penampung_sebab_adegan_gagal(self):
        from src.providers.visual.ai_image import AIImageProvider
        self.assertTrue(
            hasattr(AIImageProvider, "scene_errors") or "scene_errors" in _teks(ADAPTOR),
            "tak ada penampung sebab adegan yang gagal — sebabnya tetap hilang, dan tenant tetap "
            "membaca 'durasi kependekan' untuk kegagalan yang sebenarnya milik penyedianya")

    def test_sebab_tidak_dibuang_di_penangkap_adegan(self):
        """Penangkap adegan wajib MENYIMPAN sebabnya, bukan hanya memakainya untuk tulis-ulang."""
        t = _teks(ADAPTOR)
        m = re.search(r"GAGAL setelah 3 attempt.{0,400}", t, re.S)
        self.assertIsNotNone(m, "cabang 'adegan dilewati' tak ditemukan")
        self.assertRegex(
            m.group(0), r"scene_errors",
            "saat adegan akhirnya dilewati, sebabnya tidak disimpan ke mana pun — persis cacat "
            "yang membuat kita buta selama 8 minggu")


class TestC_TakMengulangYangMustahilSembuh(unittest.TestCase):
    """Kredit habis tidak sembuh dengan menulis ulang prompt. Mengulang 3× hanya membakar sisa
    jatah tenant — dan jalur penulis naskah SUDAH memakai aturan ini (hanya mengulang untuk
    batas-laju / gangguan sesaat / tak-dikenal)."""

    def test_kelas_mustahil_sembuh_tidak_diulang(self):
        t = _teks(ADAPTOR)
        self.assertRegex(
            t, r"FAST_FAIL",
            "penangkap adegan tak mengenal kelas yang mustahil sembuh — untuk kredit habis ia akan "
            "tetap menulis ulang prompt 3×, membakar sisa jatah tenant tanpa peluang berhasil")


class TestD_BalasanPenyediaTidakDipotongDiAdaptor(unittest.TestCase):
    """Balasan penyedia memuat angka, jam pulih, dan tautan perbaikan. Memotongnya di sumber =
    membuang bukti yang justru sedang kita kumpulkan (pelajaran 06-Agu, 13 pemotongan dicabut)."""

    def test_tak_ada_pemotongan_pada_balasan_penyedia(self):
        langgar = []
        for i, baris in enumerate(_teks(ADAPTOR).split("\n"), 1):
            if baris.lstrip().startswith("#"):
                continue
            if re.search(r"(r|s|res|v)\.text\[:\s*\d+\s*\]|str\((sub|data)\)\[:\s*\d+\s*\]", baris):
                langgar.append(f"baris {i}: {baris.strip()[:96]}")
        self.assertFalse(
            langgar,
            "Balasan penyedia masih dipotong di adaptor:\n  " + "\n  ".join(langgar)
            + "\nBagian yang terbuang justru yang berguna: berapa jatah terpakai, kapan boleh dicoba "
              "lagi, dan tautan tempat memperbaikinya.")


class TestB_KlipKurangGagalJujur(unittest.TestCase):
    """Inti perbaikannya. Pemeriksaan dipisah jadi fungsi sendiri supaya bisa diuji langsung —
    pola sama dengan `_pesan_gagal_visual` yang sudah ada."""

    def _pipeline(self):
        from src.orchestrator.pipeline import Pipeline
        return Pipeline.__new__(Pipeline)

    def test_fungsi_pemeriksa_ada(self):
        self.assertTrue(hasattr(self._pipeline(), "_periksa_kelengkapan_klip"),
                        "tak ada pemeriksa kelengkapan klip — video pendek tetap lolos ke tenant")

    def test_klip_lengkap_TIDAK_diganggu(self):
        """ANTI-REGRESI: 168 dari 180 render sehat wajib tetap jalan."""
        p = self._pipeline()
        script = {"beat_durations": [2.4, 17.0, 14.1, 12.8, 9.4]}   # 5 bagian
        self.assertIsNone(p._periksa_kelengkapan_klip(["a", "b", "c", "d", "e"], script, None),
                          "produksi dengan klip LENGKAP ikut digagalkan — itu bug baru")

    def test_klip_kurang_menghasilkan_sebab(self):
        """Kasus NYATA 3-Agu: 5 bagian naskah, hanya 4 klip jadi."""
        p = self._pipeline()
        script = {"beat_durations": [2.4, 17.0, 14.1, 12.8, 9.4]}
        pesan = p._periksa_kelengkapan_klip(["a", "b", "c", "d"], script, SAMPEL_BILLING)
        self.assertIsNotNone(pesan, "klip kurang tapi produksi tetap dilanjutkan — video akan "
                                    "terbit dengan cerita terpotong, seperti 3-Agu")
        self.assertIn("Billing hard limit", pesan,
                      "sebab dari penyedia tidak ikut — tenant akan menyalahkan MesinViral")

    def test_tanpa_bagian_naskah_tidak_mengarang(self):
        """Naskah tanpa `beat_durations` (jalur lama) tidak boleh digagalkan atas dasar tebakan."""
        p = self._pipeline()
        self.assertIsNone(p._periksa_kelengkapan_klip(["a"], {}, None),
                          "tanpa jumlah bagian yang pasti, pemeriksa harus DIAM, bukan menebak")

    def test_tanpa_sebab_tetap_gagal_tapi_jujur(self):
        """Sebab tak terekam (mis. penyedia belum dikenali) → tetap gagal, tanpa mengarang sebab."""
        p = self._pipeline()
        script = {"beat_durations": [1, 2, 3, 4, 5]}
        pesan = p._periksa_kelengkapan_klip(["a", "b"], script, None)
        self.assertIsNotNone(pesan)
        self.assertNotIn("None", pesan, "jangan bocorkan 'None' ke mata tenant")


if __name__ == "__main__":
    unittest.main(verbosity=2)
