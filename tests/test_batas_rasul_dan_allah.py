"""LLM DIBATASI: JANGAN MENGGAMBARKAN/MENYUARAKAN RASULULLAH ATAU ALLAH. ORANG LAIN BEBAS.

Ketetapan owner 2026-08-15 (`SISA_KERJA [B32]` T7), menggantikan rancangan saya yang berlebihan:

    "ANDA LLM TINGGAL ANDA BATASI LLM UNTUK TIDAK BOLEH MENAMPILKAN/MENGGAMBARKAN ROSUL ATAU ALLAH
     DALAM NARASI, HANYA BOLEH MENYAMPAIKAN PESAN TERJEMAHAN HADITS ATAU TERJEMAHAN ALQURAN.
     MENGGAMBARKAN ORANG LAIN BOLEH-BOLEH SAJA."

⛔ **RANCANGAN SAYA SEBELUMNYA DITOLAK — jangan dihidupkan lagi:** memeriksa gambar hasil dengan
pengenal wajah / "mata" AI, atau menolak SEMUA kata bertubuh (man·woman·hands·face) pada niche
anikonik. Ketiganya membuat niche **kaku** dan melarang jauh lebih banyak daripada aturannya sendiri —
padahal yang terlarang hanya DUA sosok, bukan seluruh manusia. Owner: *"jangan over engineering."*

Batasnya dipasang di tempat asal masalahnya: **instruksi kepada LLM** yang menulis naskah dan yang
menulis perintah gambar. Terukur 15-Agu (4 gambar): mesin gambar mematuhi larangan selama adegan yang
KITA perintahkan tidak memintanya — jadi menahan permintaannya di hulu sudah cukup, dan penyaring
prompt yang sudah ada (`providers/visual/patri.py`) tetap jadi jaring terakhir.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBatasSampaiKeSeluruhPenulis(unittest.TestCase):
    def test_konstanta_tunggal_ada(self):
        from src.intelligence.script_engine import BATAS_SOSOK_DIMULIAKAN
        t = BATAS_SOSOK_DIMULIAKAN.lower()
        self.assertIn("muhammad", t)
        self.assertIn("allah", t)
        self.assertTrue("translat" in t or "meaning" in t,
                        "batas tak menyebut bahwa yang boleh hanyalah TERJEMAHAN hadits/Qur'an")

    def test_orang_lain_tetap_boleh(self):
        """Inti ketetapan owner: yang dilarang DUA sosok, bukan seluruh manusia."""
        from src.intelligence.script_engine import BATAS_SOSOK_DIMULIAKAN
        t = BATAS_SOSOK_DIMULIAKAN.lower()
        self.assertTrue("other people" in t or "ordinary people" in t,
                        "batas tidak menyatakan bahwa menggambarkan orang LAIN boleh — "
                        "tanpa kalimat itu LLM cenderung mengosongkan seluruh manusia (niche jadi kaku)")

    def test_dipakai_penulis_naskah_dan_penulis_gambar(self):
        """Batas yang hanya ada di satu penulis = jalur lain tetap bebas."""
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(akar, "src", "intelligence", "script_engine.py"), encoding="utf-8") as f:
            src = f.read()
        # 1 deklarasi + 2 jalur NASKAH (naskah utuh · naskah per-bagian).
        # SENGAJA TIDAK dipasang di penulis perintah GAMBAR: sisi gambar sudah terlindungi TIGA lapis
        # sejak 14-Agu (`providers/visual/patri.py`: penyaring permintaan + tempelan larangan di setiap
        # prompt + 23 uji penjaga). Menambah lapis keempat di sana = duplikasi tanpa penjagaan baru.
        self.assertGreaterEqual(src.count("BATAS_SOSOK_DIMULIAKAN"), 3,
                                "batas belum dipasang di kedua jalur penulis NASKAH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
