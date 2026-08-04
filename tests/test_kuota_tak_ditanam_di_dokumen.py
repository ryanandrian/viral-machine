"""Angka kuota video TIDAK BOLEH ditanam di dokumen mana pun — hanya menunjuk kenop hidup.

MASALAH YANG DIJAGA (disisir 2026-08-05, atas perintah owner "pastikan mana yang valid di antara yang
tumpang tindih")
**Tujuh dokumen menyatakan angka BERBEDA untuk hal yang SAMA.** Diverifikasi ke DB live —
`plan_limits.max_videos_per_day` = **1 · 1 · 3 · 5** (trial/starter/pro/business), admin-editable di
`/admin/pricing` (migr 0073):

| Pernyataan | Vonis |
|---|---|
| `CONTENT_CATEGORY_ARCHITECTURE` "max_videos_per_day 1/1/3/5" | ✅ VALID (cocok persis DB) |
| `finalisasi_tier_plan` "Max video/hari 50 landing = 5×10ch" | ✅ VALID (aritmetika benar: business 5×10=50) |
| `ONBOARDING_FUNNEL_PLAN` & `PAYMENT_AND_TENANT_GATE` "trial 1/hari" | ✅ VALID |
| halaman pemasaran "Hingga 50 video/hari" | ✅ VALID (Business 5×10 channel) |
| `CLAUDE_DESIGN_BRIEF` "Starter 5/hari, Pro 10/hari, Scale 24/hari" | ❌ BASI (3–5× lebih tinggi; "Scale" pun nama lama) |
| `DESAIN_PRODUK_SAAS` 6 baris naratif "5-24 video/hari" | ❌ BASI (klaim turunan "3-12× lebih agresif" ikut gugur) |
| `RISET_NICHE_TRENDING` "5–24 video/hari/channel" | ❌ BASI (kesimpulan "pool habis berminggu" pakai laju 5× terlalu cepat) |

**SEBAB STRUKTURALNYA, dan itu yang dijaga uji ini:** angka yang DISALIN ke dokumen pasti membusuk begitu
owner menggeser kenopnya. Satu-satunya bentuk yang tak bisa basi = **menunjuk kenopnya**, bukan menyalin
nilainya. Sama seperti pelajaran `test_desain_produk_tak_tanam_angka_mati.py`.

CATATAN JUJUR SOAL ALAT UKUR: pemeriksaan otomatis "berapa persen artefak dokumen masih ada" yang saya
coba lebih dulu **GAGAL TOTAL** — 5 dari 5 artefak yang ia sebut "sudah tidak ada" ternyata ADA
(`channels.niche_pool`, `MEMORY.md`, `youtube_publisher`) atau sudah terdokumentasi sebagai koreksi
(`tests/test_errmgmt.py`) atau memang baris RENCANA berlabel NEW (`reels_publisher.py`). Angkanya dibuang;
resolusi di atas dikerjakan dengan MEMBACA dan MEMBANDINGKAN, bukan memola.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pola angka kuota yang PERNAH ditanam & terbukti membusuk. Ditulis sebagai pola, bukan daftar berkas,
# supaya dokumen BARU pun ikut terjaga.
POLA_TERLARANG = [
    (r"\b5\s*[-–]\s*24\s*video", "rentang '5-24 video' = angka rancangan yang tak pernah terpasang"),
    (r"Starter[^.\n]{0,40}\b5\s*video\s*/\s*hari", "Starter 5 video/hari (kenop hidup: 1)"),
    (r"Pro[^.\n]{0,40}\b10\s*/\s*hari", "Pro 10/hari (kenop hidup: 3)"),
    (r"Scale[^.\n]{0,40}\b24\s*/\s*hari", "Scale 24/hari (kenop hidup: business 5; 'Scale' nama lama)"),
]

# Berkas yang BOLEH memuat pola itu KARENA sedang mengoreksinya (spanduk/catatan koreksi) atau
# karena ia justru uji ini sendiri. Diperiksa satu per satu 2026-08-05.
BOLEH_MENYEBUT = {
    "DESAIN_PRODUK_SAAS.md":                "memuat blok koreksi yang MENYATAKAN angka itu basi",
    "CLAUDE_DESIGN_BRIEF.md":               "memuat spanduk koreksi 05-Agu di baris paket",
    "RISET_NICHE_TRENDING_2026-07-05.md":   "memuat spanduk koreksi 05-Agu di kepala berkas",
    "finalisasi_tier_plan.md":              "mencatat salah-paham lama yang DICABUT (jejak keputusan)",
}


def _dokumen() -> list[str]:
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(AKAR, "*.md")))


class TestAngkaKuotaTidakDitanamLagi(unittest.TestCase):

    def test_ada_dokumen_untuk_diperiksa(self):
        """Pagar untuk pagar: bila glob rusak, uji di bawah hijau-palsu selamanya."""
        self.assertGreaterEqual(len(_dokumen()), 30, "pemindai dokumen rusak")

    def test_tak_ada_dokumen_baru_menanam_angka_kuota(self):
        pelanggar = []
        for nama in _dokumen():
            if nama in BOLEH_MENYEBUT:
                continue
            teks = open(os.path.join(AKAR, nama), encoding="utf-8", errors="ignore").read()
            for pola, alasan in POLA_TERLARANG:
                if re.search(pola, teks, re.I):
                    pelanggar.append(f"{nama}: {alasan}")
        self.assertFalse(
            pelanggar,
            "Dokumen menanam ANGKA KUOTA (pasti membusuk saat owner menggeser kenop):\n  "
            + "\n  ".join(pelanggar)
            + "\nTunjuk `plan_limits.max_videos_per_day` (admin-editable /admin/pricing), JANGAN salin "
              "nilainya. Bila baris itu memang catatan koreksi/sejarah, daftarkan di BOLEH_MENYEBUT "
              "beserta alasannya.")

    def test_pengecualian_benar_benar_memuat_koreksinya(self):
        """Daftar pengecualian tak boleh jadi tempat sembunyi: berkas yang didaftarkan WAJIB benar-benar
        memuat koreksi/penandanya. Kalau tidak, pengecualian itu justru melegalkan dokumen basi."""
        for nama, alasan in BOLEH_MENYEBUT.items():
            p = os.path.join(AKAR, nama)
            self.assertTrue(os.path.exists(p), f"BOLEH_MENYEBUT memuat berkas hantu: {nama}")
            teks = open(p, encoding="utf-8", errors="ignore").read()
            self.assertRegex(
                teks, r"BASI|dikoreksi|DIKOREKSI|DICABUT|kenop hidup",
                f"{nama} didaftarkan sebagai 'memuat koreksi' tapi tak ada penanda koreksinya — "
                f"pengecualian ini melegalkan dokumen basi. Alasan terdaftar: {alasan}")

    def test_sumber_kenop_disebut_di_dokumen_yang_mengoreksi(self):
        """Koreksi tanpa menunjuk sumber hidup = pembaca tetap tak tahu angka benarnya."""
        for nama in BOLEH_MENYEBUT:
            teks = open(os.path.join(AKAR, nama), encoding="utf-8", errors="ignore").read()
            self.assertIn("plan_limits", teks,
                          f"{nama} mengoreksi angka tapi tak menyebut sumber hidupnya (`plan_limits`)")


class TestPernyataanValidTidakIkutHilang(unittest.TestCase):
    """Arah sebaliknya. Dua dokumen memuat pernyataan yang TERVERIFIKASI cocok DB — keduanya adalah
    rujukan bila kelak ada yang bertanya "berapa angka benarnya". Bila hilang, resolusi konflik ini
    lenyap dan tumpang-tindihnya akan lahir lagi."""

    def test_content_category_masih_menyebut_angka_terverifikasi(self):
        t = open(os.path.join(AKAR, "CONTENT_CATEGORY_ARCHITECTURE.md"), encoding="utf-8").read()
        self.assertRegex(t, r"max_videos_per_day.{0,12}1/1/3/5",
                         "pernyataan terverifikasi '1/1/3/5' hilang dari CONTENT_CATEGORY — "
                         "rujukan angka benar lenyap")

    def test_finalisasi_tier_masih_menjelaskan_aritmetika_50(self):
        t = open(os.path.join(AKAR, "finalisasi_tier_plan.md"), encoding="utf-8").read()
        self.assertRegex(t, r"50[^.\n]{0,40}5\s*[×x]\s*10",
                         "penjelasan '50/hari = 5×10 channel' hilang — klaim halaman pemasaran jadi "
                         "tak bisa dipertanggungjawabkan lagi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
