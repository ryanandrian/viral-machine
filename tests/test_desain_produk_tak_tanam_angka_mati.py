"""`DESAIN_PRODUK_SAAS.md` tak boleh menanam ANGKA MATI untuk nilai yang hidup di DB.

MASALAH YANG DIJAGA (temuan 2026-08-04)
Dokumen pondasi produk menulis kuota **5 / 10 / 24** video/hari/channel sebagai angka mati, sementara
nilai yang BENAR-BENAR ditegakkan ada di `plan_limits.max_videos_per_day` — **admin-editable** di
`/admin/pricing` (migr 0073, nol hardcode). Nilai hidup saat diperiksa: **1 / 1 / 3 / 5**
(trial/starter/pro/business) = **3–5× lebih rendah**.

BAHAYA NYATA yang nyaris terjadi: menyelaraskan kenop ke angka dokumen = menaikkan beban render **5×**.
Puncak produksi yang PERNAH tercapai = 34 video/hari (16-Jun); Business versi angka-mati menuntut
240/hari. Owner sendiri yang menahannya: *"bisa jadi dokumen banyak yang basi... jika ini dijadikan
acuan satu-satunya tanpa melihat sejarahnya, bisa berantakan semuanya."* Kekhawatiran itu TERBUKTI.

STRATEGINYA: **hapus KEMUNGKINAN drift, bukan cuma deteksi.** Dua sumber angka yang harus disinkronkan
manual akan selalu melenceng lagi. Karena itu dokumen WAJIB menunjuk ke kenopnya, dan uji ini menolak
kembalinya matriks angka mati.

CATATAN: uji ini HERMETIK (hanya membaca dokumen, nol DB) supaya deterministik dan tak menyentuh
produksi. Ia menjaga BENTUK (menunjuk kenop, bukan angka mati) — nilai kuotanya sendiri keputusan owner.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOK = os.path.join(AKAR, "DESAIN_PRODUK_SAAS.md")


def _teks() -> str:
    return open(DOK, encoding="utf-8").read()


class TestKuotaMenunjukKenopBukanAngkaMati(unittest.TestCase):

    def test_baris_kuota_tidak_menanam_angka_mati_lagi(self):
        """Baris matriks 'Max Video/hari/channel' dilarang memuat angka per-tier.

        Bentuk lama yang dilarang:  | **Max Video/hari/channel** | 5 | 10 | 24 | Custom |
        Angka apa pun di sel tier = benih drift berikutnya (kenop bergeser, dokumen diam)."""
        for baris in _teks().splitlines():
            if "Max Video/hari" not in baris and "Total Video/bulan" not in baris:
                continue
            sel = [s.strip() for s in baris.strip().strip("|").split("|")]
            for isi in sel[1:]:                       # sel[0] = label baris
                bersih = isi.replace("*", "").replace("~", "").replace(",", "").replace(".", "").strip()
                self.assertFalse(
                    re.fullmatch(r"\d+", bersih),
                    f"baris kuota menanam angka mati '{isi}' — nilai hidup ada di "
                    f"plan_limits.max_videos_per_day (admin-editable). Tunjuk kenopnya, jangan "
                    f"menyalin angkanya.\n  baris: {baris.strip()[:120]}")

    def test_dokumen_menunjuk_sumber_kenop_yang_benar(self):
        """Pembaca harus tahu KE MANA melihat nilai sebenarnya — kalau tidak, ia akan memakai
        angka apa pun yang ia temukan di dokumen."""
        t = _teks()
        self.assertIn("plan_limits.max_videos_per_day", t,
                      "dokumen tak menyebut sumber kenop kuota — pembaca akan menebak")
        self.assertIn("/admin/pricing", t,
                      "dokumen tak menyebut TEMPAT owner mengubahnya")

    def test_peringatan_bahaya_menaikkan_kuota_masih_ada(self):
        """Pagar paling penting: menuruti angka dokumen = beban render 5×. Kalau peringatan ini
        hilang, sesi berikutnya bisa 'menyelaraskan' kenop ke angka lama dan menumbangkan produksi."""
        t = _teks()
        self.assertIn("34 video/hari", t,
                      "puncak kapasitas terukur (34/hari) hilang — pembanding realistis lenyap")
        self.assertRegex(t, r"beban render \*\*5×\*\*|beban render 5×",
                         "peringatan beban render 5× hilang dari dokumen")

    def test_klaim_pemasaran_yang_basi_ditandai(self):
        """Klaim '7,5× lebih murah' dihitung dari 150 video/bulan yang tidak berlaku pada kenop hidup.
        Klaim ini boleh TETAP tertulis (sejarah), tapi WAJIB bertanda jangan-dipakai — angka jualan
        yang tak didukung sistem = janji yang tak bisa ditepati."""
        t = _teks()
        if "7.5×" in t or "7,5×" in t:
            self.assertRegex(
                t, r"[Jj]angan pakai angka 7[.,]5×",
                "klaim '7,5× lebih murah' masih ada TANPA penanda jangan-dipakai; pada kenop hidup "
                "angkanya ~3,7× — memakainya di materi jualan = janji yang tak didukung sistem")

    def test_keputusan_trial_vs_starter_tercatat(self):
        """Temuan bisnis terpenting 04-Agu: pada kenop hidup, Trial & Starter IDENTIK (1 video/hari,
        1 channel) ⇒ tenant membayar Rp 149K tanpa tambahan produksi. Ini keputusan OWNER (harga/produk);
        catatannya tak boleh hilang, kalau tidak temuan ini akan ditemukan-ulang tiap beberapa bulan."""
        t = _teks()
        self.assertRegex(t, r"Trial dan Starter identik|Trial & Starter identik",
                         "temuan Trial=Starter hilang dari dokumen")
        self.assertRegex(t, r"BELUM DIKETOK|belum diketok",
                         "status 'belum diketok owner' hilang — bisa disalahpahami sebagai sudah diputuskan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
