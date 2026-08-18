"""DAFTAR "YANG RUSAK" DI PETA OWNER WAJIB BERBUKTI UJI — bukan pendapat berselubung fakta.

LAHIR DARI PELANGGARAN SAYA SENDIRI, 19-Agu, dalam SATU sesi:
saya menulis §4b (tabel pemisah TERUKUR vs PENDAPAT) di `PETA_MESINVIRAL.md`, lalu **beberapa menit
kemudian** menaruh butir "jumlah gambar mengikuti babak cerita" di daftar **"Yang rusak"** — padahal
itu kontrak rancangan yang mesin turuti dengan BENAR, jadi pendapat, bukan kerusakan. Owner
menemukannya dengan satu pertanyaan: *"itu bug atau improvement?"*

Owner: *"sampai kapan anda akan terus bertingkah liar tidak terkendali?"* — jawaban yang jujur:
aturan yang bersandar pada disiplin saya GAGAL DALAM HITUNGAN MENIT; yang bertahan hanya yang
ditolak mesin. Maka aturan §4b diubah jadi penjaga.

KONTRAK YANG DIJAGA — sesederhana mungkin supaya tak bisa diakali:
setiap butir di daftar "Yang rusak sekarang" WAJIB menyebut berkas `tests/…` yang membuktikannya.
Alasannya tepat definisi kita sendiri: **kerusakan = ada yang bisa dibuat MERAH.** Tak ada ujinya ⇒
tak terbukti rusak ⇒ tempatnya di daftar improvement (§4c), bukan di daftar rusak.

BATAS UJI INI (jujur, agar tak dibaca lebih kuat dari isinya): ia menjaga BENTUK — bahwa klaim
"rusak" menunjuk bukti yang ADA. Ia tidak bisa menilai apakah uji itu bermutu.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PETA = os.path.join(AKAR, "PETA_MESINVIRAL.md")


def _bagian_rusak(teks: str) -> str:
    m = re.search(r"## 3\. Yang rusak sekarang(.*?)\n## ", teks, re.S)
    return m.group(1) if m else ""


class TestPetaJujur(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(PETA, encoding="utf-8") as f:
            cls.teks = f.read()

    def test_bagian_rusak_masih_ada(self):
        """Kalau judulnya diubah, penjaga ini jadi buta — itu cara termudah mengakalinya."""
        self.assertTrue(_bagian_rusak(self.teks),
                        "Bagian '## 3. Yang rusak sekarang' tak ditemukan di peta — penjaga ini "
                        "buta. Judul bagian itu bagian dari kontrak, jangan diubah diam-diam.")

    def test_setiap_klaim_rusak_menunjuk_uji_yang_ADA(self):
        blok = _bagian_rusak(self.teks)
        butir = [b.strip() for b in re.findall(r"^\s*\d+\.\s+(.*?)(?=^\s*\d+\.\s|\Z)",
                                               blok, re.S | re.M)]
        tanpa_bukti, uji_hantu = [], []
        for b in butir:
            berkas = re.findall(r"tests/([A-Za-z0-9_\-]+\.py)", b)
            if not berkas:
                tanpa_bukti.append(b.splitlines()[0][:70])
                continue
            for f in berkas:
                if not os.path.exists(os.path.join(AKAR, "tests", f)):
                    uji_hantu.append(f)
        self.assertEqual(
            tanpa_bukti, [],
            f"Butir di daftar RUSAK tanpa menyebut uji yang membuktikannya: {tanpa_bukti}. "
            "Kerusakan = ada yang bisa dibuat MERAH. Tanpa uji, itu PENDAPAT — tempatnya di daftar "
            "improvement (§4c). Inilah pelanggaran yang owner tangkap 19-Agu.")
        self.assertEqual(uji_hantu, [],
                         f"Uji yang disebut tak ada di repo: {uji_hantu}.")

    def test_pemisah_terukur_vs_pendapat_tak_boleh_hilang(self):
        self.assertIn("## 4b.", self.teks,
                      "Tabel pemisah TERUKUR vs PENDAPAT (§4b) hilang dari peta — tanpa itu owner "
                      "kehilangan satu-satunya ukuran untuk menilai klaim Claude.")
        self.assertIn("## 4c.", self.teks,
                      "Daftar improvement (§4c) hilang — butir pendapat akan kembali menyusup ke "
                      "daftar rusak, persis pelanggaran 19-Agu.")


if __name__ == "__main__":
    unittest.main()
