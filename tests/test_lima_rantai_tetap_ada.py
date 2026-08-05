"""Aturan LIMA RANTAI (`CLAUDE.md` §0.7) tak boleh hilang atau melunak.

KENAPA UJI INI ADA
Aturan ini lahir 2026-08-05 dari kegagalan perilaku yang owner sebut *"biang kerok seluruh kerusakan
sistem"*: dalam SATU penyelidikan panel tenant — tepat setelah owner menegaskan "pahami 100%" — Claude
mengusulkan perbaikan **dua kali** dan **menggugurkan keduanya sendiri**. Usulan-1 hanya menelusuri
mata 1-2; usulan-2 melewatkan mata 3 & 5, padahal di mata 3 letak sebabnya (Test Channel TIDAK PERNAH
membuat baris `content_inventory`) dan di mata 5 letak cakupannya (8 run, bukan 2). Bila owner menjawab
"ya", perbaikan dibangun di atas model yang SALAH — persis cara ranjau lahir.

KENAPA DIJAGA MESIN, BUKAN DIPERCAYAKAN PADA INGATAN
Presedennya sudah terbukti pahit: **18 rujukan memory di `SISA_KERJA` §0 menunjuk berkas yang dibuang
15-Jul dan bertahan 3 minggu** tanpa ada yang sadar. Aturan yang tak dijaga akan membusuk atau dilunakkan
diam-diam — termasuk oleh Claude sendiri di sesi berikutnya, saat aturan ini terasa merepotkan.

Owner: *"buktikan janji ini SEUMUR HIDUP, bukan hanya untuk saat ini."* Uji inilah bentuk "seumur hidup"
yang bisa ditegakkan: bukan janji, tapi merah bila aturannya dicabut.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATURAN = os.path.join(AKAR, "CLAUDE.md")


def _teks() -> str:
    return open(ATURAN, encoding="utf-8").read()


class TestLimaRantaiUtuh(unittest.TestCase):

    def test_aturan_ada_di_pasal_disiplin_inti(self):
        """WAJIB di §0 (disiplin inti) — bukan di pasal lain, bukan di dokumen lain. §0 dibaca lebih
        dulu, dan `CLAUDE.md` satu-satunya berkas yang OTOMATIS masuk ke hadapan Claude tiap sesi
        (termasuk pasca-compaction). Memory tidak — 8 berkas memory terbukti diabaikan."""
        t = _teks()
        m = re.search(r"## §0 DISIPLIN INTI(.*?)## §1", t, re.S)
        self.assertIsNotNone(m, "§0 DISIPLIN INTI hilang dari CLAUDE.md")
        self.assertIn("LIMA RANTAI", m.group(1),
                      "aturan LIMA RANTAI tak lagi ada di §0 — sesi baru takkan pernah melihatnya")

    def test_kelima_mata_disebut_lengkap(self):
        """Empat mata tak cukup: kegagalan 05-Agu justru terjadi karena mata 3 & 5 dilewati."""
        t = _teks()
        for kunci, kenapa in (
            ("BACA DARI MANA", "mata 1 — sumber data layar"),
            ("PREDIKAT", "mata 2 — aturan klasifikasi"),
            ("SIAPA MEMBUAT", "mata 3 — DI SINI letak sebab kegagalan 05-Agu"),
            ("APA YANG MENUTUP", "mata 4 — mekanisme pengakhir"),
            ("JALUR SAUDARA", "mata 5 — DI SINI letak cakupan sebenarnya (8 vs 2)"),
        ):
            self.assertIn(kunci, t, f"mata rantai hilang: {kunci} ({kenapa})")

    def test_tetap_berstatus_WAJIB_bukan_anjuran(self):
        """Aturan yang melunak jadi 'sebaiknya' = aturan yang mati. Bukti: 'verifikasi dengan teliti'
        berbentuk anjuran dilanggar berulang, sementara aturan berbentuk FORMAT dipatuhi."""
        t = _teks()
        blok = t[t.index("LIMA RANTAI"):t.index("LIMA RANTAI") + 1800]
        self.assertIn("TIDAK SAH", blok,
                      "sanksi 'TIDAK SAH' dicabut — aturan berubah jadi anjuran, dan anjuran diabaikan")
        self.assertRegex(blok, r"FORMAT WAJIB",
                         "penegasan 'FORMAT WAJIB' hilang — ia akan dibaca sebagai nasihat")

    def test_mata_yang_belum_diperiksa_wajib_ditulis(self):
        """Inti pencegahannya. Kegagalan 05-Agu terjadi karena Claude TIDAK TAHU apa yang belum ia
        periksa — ia mengira sudah lengkap. Memaksa menulis 'BELUM DIPERIKSA' mengubah titik buta
        menjadi terlihat, dan membuat pelanggarannya tampak di pesan itu juga."""
        t = _teks()
        self.assertIn("BELUM DIPERIKSA", t,
                      "kewajiban menulis mata yang belum diperiksa telah dicabut — titik buta kembali "
                      "tersembunyi, dan owner harus membongkar lagi untuk menemukannya")
        self.assertRegex(t, r"dilarang dikosongkan diam-diam|dilarang.*ditebak",
                         "larangan mengosongkan/menebak mata rantai hilang")

    def test_hak_owner_menolak_seketika_masih_tertulis(self):
        """Penegak sebenarnya bukan mesin, tapi owner — dengan biaya 5 detik (blok ada/tidak),
        BUKAN dengan membongkar kode. Bila hak itu dicabut dari aturan, beban kembali ke owner."""
        t = _teks()
        self.assertRegex(t, r"[Oo]wner menolak seketika",
                         "hak owner menolak-seketika hilang dari aturan — penegaknya lenyap")

    def test_insiden_pemicunya_tetap_tercatat(self):
        """Konvensi CLAUDE.md: konteks insiden dalam kurung = SEBAB aturan lahir. Tanpa itu, sesi
        berikutnya menganggap aturan ini birokrasi lalu melunakkannya."""
        t = _teks()
        self.assertRegex(t, r"DUA KALI|dua kali",
                         "insiden pemicu (dua usulan yang digugurkan sendiri) hilang dari aturan")
        self.assertIn("biang kerok", t,
                      "kalimat owner 'ini biang kerok seluruh kerusakan sistem' hilang — bobot aturan "
                      "ini akan diremehkan sesi berikutnya")


if __name__ == "__main__":
    unittest.main(verbosity=2)
