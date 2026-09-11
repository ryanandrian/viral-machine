"""Uji tenant yang SUDAH menunggu tak boleh diserobot pengisi stok.

LAHIR DARI KEJADIAN 10–11 SEP 2026 (owner). Jejak `worker.log` — bukan teori:
    00:39:13  owner menekan "Uji sekarang" → job `pending` lahir
    00:39:21  produksi STOK #1 mulai
    00:45:58  produksi stok #1 SELESAI  ⇒ slot bebas
    00:46:06  produksi STOK #2 MEREBUT slot (8 detik kemudian)
    00:52:39  uji owner baru dapat giliran — menunggu 13,4 menit, kalah 2×

AKAR — jendela balapan di dalam `plan_and_submit`, terbukti dari urutan waktu:
  1. putaran dimulai ~00:45:5x → `drain_direct` gagal `sem.acquire` (stok #1 masih jalan) ⇒ uji dilewati
  2. `plan_and_submit` mulai memutari 9 channel × ±7 kueri (`gate_for_channel` · `channel_readiness` ·
     `buffer_depth` ×3 · streak · latest_failure) — butuh DETIK-AN
  3. di TENGAH pengumpulan itu stok #1 selesai (00:45:58,8) ⇒ slot bebas
  4. `plan_and_submit` baru sampai ke `sem.acquire()` pada 00:46:06 ⇒ BERHASIL, slot direbut

Jadi pengisi stok mengambil slot berdasarkan keadaan LAMA (saat putaran dimulai) tanpa memeriksa
lagi tepat sebelum mengambil. Urutan `drain_direct` sebelum `plan_and_submit` TIDAK cukup —
keadaan bisa berubah di tengah putaran.

B34 (jeda stok 10 dtk → 5 menit) hanya MENGECILKAN peluangnya, tidak menutupnya. Owner:
*"mengecilkan masalah bukan membereskan masalah"* — dan celah yang jarang terjadi justru lebih
berbahaya: ketika terjadi, tak ada yang menyangka.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCER = "src/orchestrator/producer.py"
JANITOR = "src/orchestrator/buffer_janitor.py"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("#"))


def _fungsi(isi: str, nama: str) -> str:
    i = isi.find(f"def {nama}(")
    assert i != -1, f"fungsi {nama} tak ditemukan"
    sisa = isi[i + 10:]
    j = re.search(r"\ndef \w+\(", sisa)
    return isi[i: i + 10 + (j.start() if j else len(sisa))]


class TestStokMengalahPadaUjiYangMenunggu(unittest.TestCase):
    def setUp(self):
        self.p = _tanpa_komentar(_isi(PRODUCER))
        self.plan = _fungsi(self.p, "plan_and_submit")

    def test_stok_memeriksa_antrean_uji_SEBELUM_mengambil_slot(self):
        """Inti perbaikan: pemeriksaan harus dilakukan DI DEKAT `sem.acquire`, bukan hanya di awal
        putaran — sebab slot bisa bebas di tengah pengumpulan defisit."""
        self.assertRegex(
            self.plan, r"direct_jobs",
            "plan_and_submit tak pernah menanyakan antrean uji ⇒ ia bisa merebut slot yang baru "
            "bebas padahal uji tenant sudah menunggu sejak beberapa menit lalu.",
        )
        m = re.search(r"sem\.acquire\(", self.plan)
        self.assertIsNotNone(m, "sem.acquire tak ditemukan di plan_and_submit")
        sebelum = self.plan[:m.start()]
        self.assertIn(
            "direct_jobs", sebelum,
            "pemeriksaan antrean uji ada, tapi TIDAK sebelum `sem.acquire` — jendela balapan "
            "tetap terbuka.",
        )

    def test_stok_benar_benar_mengalah_bukan_hanya_mencatat(self):
        """Jangkar perilaku: hasil pemeriksaan wajib MENGHENTIKAN pengambilan slot."""
        # JANGKAR DIPERBAIKI SESUDAH SABOTASE: versi pertama mencari `return|break` dalam 700
        # huruf sesudah "direct_jobs" — dan TETAP HIJAU saat `return 0` dicabut, sebab ia
        # menangkap `break` milik loop `for _, ch in deficits` di bawahnya. Yang diikat sekarang:
        # tindakan mengalah harus berada ANTARA pemeriksaan antrean dan `sem.acquire`.
        m = re.search(r"direct_jobs", self.plan)
        a = re.search(r"sem\.acquire\(", self.plan)
        self.assertIsNotNone(a, "sem.acquire tak ditemukan")
        antara = self.plan[m.start(): a.start()]
        self.assertRegex(
            antara, r"\breturn\b",
            "antrean uji diperiksa tapi hasilnya tak MENGHENTIKAN pengambilan slot sebelum "
            "`sem.acquire` — pengisi stok tetap menyerobot uji yang sudah menunggu.",
        )

    def test_pemeriksaan_fail_soft(self):
        """DB gagal dibaca ⇒ produksi stok JANGAN berhenti total (itu lebih buruk).
        Fail-soft: anggap tak ada uji menunggu, lanjutkan seperti perilaku lama."""
        m = re.search(r"direct_jobs", self.plan)
        blok = self.plan[max(0, m.start() - 500): m.start() + 700]
        self.assertRegex(
            blok, r"except\s+Exception",
            "pembacaan antrean uji tanpa penjaga — sekali DB tersendat, seluruh produksi stok "
            "bisa berhenti.",
        )

    def test_urutan_drain_sebelum_plan_tetap_dijaga(self):
        """Lapis pertama yang SUDAH benar — perbaikan ini melengkapinya, bukan menggantinya."""
        loop = _fungsi(self.p, "run_forever")
        i_drain = loop.find("drain_direct(")
        i_plan = loop.find("plan_and_submit(")
        self.assertNotEqual(i_drain, -1, "drain_direct hilang dari loop")
        self.assertNotEqual(i_plan, -1, "plan_and_submit hilang dari loop")
        self.assertLess(
            i_drain, i_plan,
            "drain_direct tak lagi dipanggil sebelum plan_and_submit — lapis pertama jebol.",
        )


class TestAntreanUjiTakMenggantungSelamanya(unittest.TestCase):
    """Lubang kedua: penyapu hanya mengenal job `producing` yang macet, BUKAN `pending` yang tak
    pernah dapat giliran. Layar tenant berputar "Menunggu giliran…" tanpa akhir, tanpa pernah
    gagal — tenant menyimpulkan tombolnya rusak."""

    def setUp(self):
        self.j = _tanpa_komentar(_isi(JANITOR))

    def test_penyapu_mengenal_job_pending_yang_terlalu_lama(self):
        self.assertIn(
            "reap_stuck_direct_jobs", self.j, "penyapu job direct tak ditemukan")
        fn = _fungsi(self.j, "reap_stuck_direct_jobs")
        self.assertRegex(
            fn, r"\"pending\"|'pending'",
            "penyapu hanya mengenal status 'producing' — job 'pending' yang tak pernah dapat "
            "giliran menggantung selamanya dan layar tenant berputar tanpa akhir.",
        )

    def test_batas_pending_lebih_longgar_daripada_producing(self):
        """Menunggu antrean itu WAJAR (produksi lain 8–15 menit). Batasnya tak boleh seketat
        batas job yang sudah berjalan lalu macet — kalau terlalu ketat, uji sah ikut digagalkan."""
        fn = _fungsi(self.j, "reap_stuck_direct_jobs")
        angka = [int(x) for x in re.findall(r"\"(\d+)\"", fn)]
        self.assertTrue(angka, "tak ada batas waktu ber-angka di penyapu")
        self.assertGreaterEqual(
            max(angka), 60,
            "batas job 'pending' terlalu ketat — uji yang sedang mengantre wajar bisa ikut "
            f"digagalkan: {angka}",
        )

    def test_alasan_gagal_menyebut_sebabnya_kepada_tenant(self):
        fn = _fungsi(self.j, "reap_stuck_direct_jobs")
        self.assertRegex(
            fn, r"(antre|antrean|menunggu|sibuk)",
            "job pending digagalkan tanpa menyebut sebabnya — tenant tak tahu bahwa mesin "
            "sedang sibuk, bukan tombolnya rusak.",
        )


if __name__ == "__main__":
    unittest.main()
