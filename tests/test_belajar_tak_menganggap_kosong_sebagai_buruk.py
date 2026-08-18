"""MESIN TIDAK BOLEH MEMPERLAKUKAN "DATA TIDAK ADA" SEBAGAI "PERFORMA SEBURUK MUNGKIN".

FAKTA TERUKUR (19-Agu, bukan pendapat — siapa pun bisa mengukurnya ulang):
`_compute_performance_scores` menulis `avg_view_pct = r.get("avg_view_pct") or 0.0`. Retensi yang
BELUM TERAMBIL jadi **0,0**, lalu dibobot 0,30 dalam skor performa. Akibatnya video yang datanya
belum turun dinilai **gagal total**.

Bahwa itu label PALSU bisa dibuktikan tanpa berdebat: video dengan `views > 0` MUSTAHIL punya
retensi 0% — kalau ada yang menonton, ada durasi yang tertonton. Jadi 0 di sana bukan angka
performa, melainkan **ketiadaan data**.

BESARNYA — disebut apa adanya, tidak dibesar-besarkan:
  hari ini  : 2 dari 132 video yang dipakai belajar (1%) ⇒ hampir tak menggeser hasil
  historis  : cakupan retensi per bulan **4% · 0% · 51% · 49% · 92%** (Apr–Agu, paginasi penuh)
              ⇒ pada bulan Mei, fit akan memakai label yang HAMPIR SELURUHNYA palsu.
Jadi bahayanya bukan hari ini, melainkan setiap kali pengambilan analitik tersendat lagi — dan itu
sudah pernah terjadi dua kali.

YANG BUKAN URUSAN UJI INI (dinyatakan supaya tak ada yang mengira lebih): seberapa besar mesin
boleh percaya pada korelasi lemah adalah **KEPUTUSAN RANCANGAN, bukan bug** — pendapat saya sudah
saya tarik 19-Agu setelah owner menegur bahwa saya menghina rancangan saya sendiri. Uji ini hanya
menjaga KEJUJURAN LABEL.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.viral_weight_optimizer import _compute_performance_scores  # noqa: E402


def _baris(views, retensi, likes=0, subs=0, ctr=0.0):
    return {"views": views, "avg_view_pct": retensi, "likes": likes,
            "subscriber_gain": subs, "ctr": ctr}


class TestKejujuranLabel(unittest.TestCase):

    def test_nol_ber_penonton_diperlakukan_sebagai_data_tak_ada(self):
        """KOREKSI ATAS UJI PERTAMA SAYA (19-Agu): premis awalnya MUSTAHIL. Saya menulis
        "retensi 0% dengan 1.000 penonton = sungguh-sungguh nol" — padahal itu tak bisa terjadi:
        kalau ada yang menonton, ada durasi yang tertonton. Maka 0-ber-penonton WAJIB diperlakukan
        sama dengan kosong, dan uji ini yang dibetulkan — bukan kodenya yang dilonggarkan."""
        kosong, nol_mustahil = _compute_performance_scores([
            _baris(1000, None),
            _baris(1000, 0.0),
        ])
        self.assertEqual(round(kosong, 6), round(nol_mustahil, 6),
                         "0% ber-penonton tidak diperlakukan sebagai data tak ada — padahal angka "
                         "itu mustahil, jadi memakainya = belajar dari label karangan.")

    def test_retensi_jelek_yang_MUNGKIN_tetap_dibedakan_dari_kosong(self):
        """Yang benar-benar jelek tapi MUNGKIN (mis. 1%) harus tetap menurunkan skor — kalau tidak,
        perbaikan ini justru menghapus kemampuan mesin mengenali video gagal."""
        kosong, jelek = _compute_performance_scores([
            _baris(1000, None),
            _baris(1000, 1.0),
        ])
        self.assertGreater(kosong, jelek,
                           "video yang datanya belum ada tak boleh dinilai lebih baik/sama dengan "
                           "video yang retensinya sungguh 1%")

    def test_kosong_tak_menarik_skor_ke_bawah(self):
        """Video ber-penonton banyak yang retensinya belum terambil tidak boleh dihukum: ia harus
        dinilai dari sinyal yang MEMANG ada (views/likes/subscriber), bukan diberi 0% retensi."""
        tanpa = _compute_performance_scores([_baris(5000, None, likes=200, subs=10),
                                            _baris(10, None)])[0]
        rendah = _compute_performance_scores([_baris(5000, 5.0, likes=200, subs=10),
                                             _baris(10, 5.0)])[0]
        self.assertGreater(
            tanpa, rendah,
            "Video populer yang datanya belum turun dinilai LEBIH BURUK daripada video populer yang "
            "retensinya sungguh 5% — itu menghukum ketiadaan data.")

    def test_retensi_nyata_tetap_dipakai_apa_adanya(self):
        """REGRESI: video yang datanya ADA tak boleh berubah penilaiannya."""
        a, b = _compute_performance_scores([_baris(1000, 80.0), _baris(1000, 20.0)])
        self.assertGreater(a, b, "retensi nyata berhenti membedakan — itu regresi")

    def test_nol_yang_sungguhan_tetap_dihitung_nol(self):
        """Video TANPA penonton memang boleh bernilai 0 — di sana 0 adalah data, bukan ketiadaan."""
        skor = _compute_performance_scores([_baris(0, None), _baris(1000, 90.0)])
        self.assertLess(skor[0], skor[1])


if __name__ == "__main__":
    unittest.main()
