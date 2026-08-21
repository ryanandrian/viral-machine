"""HASIL UJI YANG MEMBUKTIKAN MODEL MATI WAJIB MENYAMPAI KE KATALOG.

Pemicu (22-Agu): `gemini-2.5-flash` diuji atas perintah owner. Google menjawab
*"This model models/gemini-2.5-flash is **no longer available to new users**"* — frasa itu PERSIS
kata-global B1 yang dipakai karantina (`KATA_GLOBAL`). Tapi karantina TIDAK menyala, karena ia hanya
disambungkan ke jalur PRODUKSI (`producer._record_production_run`). Jalur UJI berhenti di
`cost_hint.audit`, dan modelnya tetap `is_active=true` sampai admin mematikannya sendiri.

⇒ Dua pintu lagi, seperti kelas cacat 17-Agu (§9b): bukti yang sama, satu pintu bersuara ke katalog,
satu pintu diam. Owner: *"sambungkan jalur uji ke karantina."*

HARAM: mengarantina SETIAP kegagalan uji. Uji bisa gagal karena kunci salah, kuota habis, atau
jaringan — itu bukan bukti model mati. Penilaian tetap lewat `nilai_bukti` yang sudah ada
(A: `dasar` = kode/teks-vendor · B1 kata global | B2 ≥2 tenant | B3 hilang dari umpan harga).

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

SRC = "src/config/model_tester.py"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _tanpa_komentar(rel: str) -> str:
    src = _baca(rel)
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))


class TestJalurUjiMenyambungKeKatalog(unittest.TestCase):

    def test_jalur_uji_memanggil_penilai_karantina(self):
        """Diurai lewat AST: `pass  # karantina(...)` lolos dari pencocokan teks — cacat itu sudah
        tertangkap sekali di producer, jangan diulang."""
        import ast
        pohon = ast.parse(_baca(SRC))
        panggil = [n for n in ast.walk(pohon)
                   if isinstance(n, ast.Call)
                   and getattr(n.func, "id", getattr(n.func, "attr", "")) == "karantina"]
        self.assertTrue(
            panggil,
            "Hasil uji yang MEMBUKTIKAN model mati tidak pernah sampai ke katalog. Bukti terkuat "
            "yang bisa didapat sistem (jawaban vendor atas panggilan nyata) berhenti di stempel "
            "audit, dan modelnya tetap ditawarkan ke tenant berikutnya.")

    def test_yang_dinilai_pesan_VENDOR_bukan_pesan_kita(self):
        """B1 mencari kata Inggris milik vendor. Memberi karantina pesan kita sendiri membuatnya
        mustahil menyala — kelas cacat yang sudah dikunci di producer."""
        import ast
        pohon = ast.parse(_baca(SRC))
        panggil = [n for n in ast.walk(pohon)
                   if isinstance(n, ast.Call)
                   and getattr(n.func, "id", getattr(n.func, "attr", "")) == "karantina"]
        self.assertTrue(panggil)
        arg = ast.unparse(panggil[0].args[3]) if len(panggil[0].args) > 3 else ""
        self.assertTrue(
            re.search(r"\be\b|str\(e\)|pesan", arg),
            f"Karantina dinilai dari `{arg}` — bukan galat vendor apa adanya. Kata seperti "
            "'no longer available' hanya ada di jawaban vendor.")
        for milik_kita in ("note", "result", "audit"):
            self.assertNotIn(
                milik_kita, arg,
                f"Karantina dinilai dari `{milik_kita}` — itu teks yang KAMI rakit; kata vendor "
                "hilang di situ dan B1 tak akan pernah menyala.")

    def test_dasar_diambil_dari_exception_bukan_DIKARANG(self):
        """`dasar` menentukan boleh-tidaknya mengarantina. Mengarangnya = mengarantina dari bukti
        yang tak pernah diperiksa."""
        kode = _tanpa_komentar(SRC)
        self.assertTrue(
            re.search(r'getattr\(\s*e\s*,\s*["\']dasar["\']', kode),
            "`dasar` tidak diambil dari galat yang sesungguhnya ⇒ karantina memakai bukti karangan.")
        self.assertNotIn(
            'dasar="kode/teks-vendor"', kode,
            "`dasar` DIPATOK ke nilai terkuat ⇒ kegagalan uji karena kunci salah/kuota habis akan "
            "dinilai seolah vendor menyebut modelnya sendiri.")

    def test_kegagalan_karantina_HARAM_menggagalkan_uji(self):
        """Karantina adalah pembelajaran katalog, bukan jalur kerja. Kegagalannya haram membuat
        admin melihat 'uji gagal' padahal ujinya sendiri sudah menjawab."""
        kode = _tanpa_komentar(SRC)
        i = kode.find("karantina(")
        self.assertGreater(i, 0)
        blok = kode[max(0, i - 400):i + 500]
        self.assertTrue(re.search(r"try\s*:", blok), "panggilan karantina tak dibungkus try")
        self.assertTrue(re.search(r"except\s+Exception", blok),
                        "kegagalan karantina tidak fail-soft ⇒ ia bisa menelan hasil uji")

    def test_HANYA_saat_uji_GAGAL(self):
        """Uji LULUS haram menyentuh karantina — itu bukti model HIDUP."""
        kode = _tanpa_komentar(SRC)
        i = kode.find("karantina(")
        self.assertGreater(i, 0)
        atas = kode[:i]
        self.assertTrue(
            re.search(r"except\s+Exception[^\n]*:", atas.split("def test_model")[-1]),
            "panggilan karantina tidak berada di dalam cabang KEGAGALAN")

    def test_penilaian_tetap_lewat_nilai_bukti_yang_SUDAH_ADA(self):
        """Jangan membangun penilai kedua: ambang A+(B1|B2|B3) sudah ada dan sudah dijaga uji.
        Penilai kedua = dua sumber kebenaran untuk 'apakah model ini mati'."""
        kode = _tanpa_komentar(SRC)
        self.assertTrue(
            re.search(r"from\s+src\.orchestrator\.karantina_model\s+import", kode),
            "modul karantina yang sudah ada tidak dipakai ⇒ ada penilai kedua di tempat lain")
        for dilarang in ("KATA_GLOBAL", "no longer available", "decommission"):
            self.assertNotIn(
                dilarang, kode,
                f"`{dilarang}` disalin ke sini ⇒ ambang bukti jadi DUA sumber kebenaran; kalau satu "
                "diperbaiki dan yang lain lupa, katalog dan produksi menilai berbeda.")


if __name__ == "__main__":
    unittest.main()
