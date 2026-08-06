"""Pesan galat penyedia disimpan UTUH — tak ada pemotongan di jalan masuk.

MASALAH YANG DIJAGA (§8h AI_ERROR_MANAGEMENT — ditemukan owner 2026-08-06)
Penyedia AI mengirim keterangan yang bagian BERGUNANYA bisa ada di awal, tengah, ATAU ujung —
tergantung penyedianya (diukur dari 338 pesan nyata di worker.log VPS):

  • Groq batas jatah   → inti di UJUNG   ("Limit 100000, Used 97045 … try again in 34m37s")
  • OpenAI kuota habis → inti di AWAL    ("You exceeded your current quota …")
  • Gemini model tutup → inti di TENGAH  ("This model is not available …")
  • "User not found"   → inti = seluruhnya (14 huruf)
  • FFmpeg gagal       → inti terkubur di balik ribuan huruf konfigurasi build

⇒ **Tidak ada aturan pemotongan yang bisa benar untuk semua penyedia.** Aturan apa pun = tebakan
tentang bagian mana yang penting, dan tebakan itu PASTI salah untuk sebagian penyedia — termasuk
penyedia yang belum dipakai hari ini. Persis begitulah angka 220 lahir (diketik 9-Jul, tanpa dasar).

DIUKUR: 140 dari 338 pesan nyata (41%) terpotong; potongannya jatuh tepat di bagian berguna.
BIAYA memotong = NOL yang bisa diukur: seluruh riwayat galat sejak proyek lahir = 12,6 KB, dan tabel
lain di database yang SAMA sudah menyimpan 1.855 huruf. Tak ada yang memaksanya.

ATURAN YANG DIJAGA DI SINI:
  A. Jalur pesan galat penyedia → **NOL pemotongan** sampai tersimpan.
  B. Peringkasan hanya untuk MENAMPILKAN, dan hanya bila permukaannya punya batas NYATA
     (Telegram menolak >4.096 huruf — batas milik Telegram, bukan angka kita).
  C. Setiap peringkasan tampilan WAJIB DIUMUMKAN: bukan sekadar "…", tapi menyebut berapa huruf
     disembunyikan. Potongan yang tak diumumkan terbaca sama persis seperti pesan utuh — itulah
     yang menipu owner, tenant, DAN Claude sendiri selama berbulan-bulan.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Berkas + nama variabel/ekspresi yang membawa pesan galat penyedia ke PENYIMPANAN.
# (Baris log/jejak internal TIDAK didaftarkan — ia tak pernah sampai ke tenant maupun ke DB.)
JALUR_SIMPAN = {
    "src/intelligence/script_engine.py": ["last_error"],
    "src/intelligence/niche_selector.py": ["last_error"],
    "src/orchestrator/pipeline.py": ["No topics selected", "Script generation failed"],
    "src/providers/visual/ai_image.py": ["VisualError(str(e)"],
    "src/orchestrator/inventory.py": ['"error": reason'],
    "src/utils/supabase_writer.py": ["qc_reason", "str(error)"],
    "src/intelligence/channel_analyst.py": ["reject = f"],
    "src/intelligence/script_analyzer.py": ["sebab=f"],
}
RX_POTONG = re.compile(r"\[:\s*\d+\s*\]")


def _teks(rel: str) -> str:
    return open(os.path.join(AKAR, rel), encoding="utf-8", errors="ignore").read()


class TestPemindaiBenar(unittest.TestCase):
    """Pagar-untuk-pagar: alat ukur yang salah lebih berbahaya daripada tak mengukur."""

    def test_semua_berkas_ada(self):
        for rel in JALUR_SIMPAN:
            self.assertTrue(os.path.exists(os.path.join(AKAR, rel)), f"berkas hilang: {rel}")

    def test_pola_potong_memang_menangkap(self):
        self.assertTrue(RX_POTONG.search("str(e)[:220]"), "regex pemotong tak menangkap bentuk nyata")
        self.assertFalse(RX_POTONG.search("daftar[i]"), "regex salah menangkap indeks biasa")


class TestNolPemotonganDiJalurSimpan(unittest.TestCase):

    def test_baris_pembawa_pesan_penyedia_tak_memotong(self):
        langgar = []
        for rel, penanda in JALUR_SIMPAN.items():
            for i, baris in enumerate(_teks(rel).split("\n"), 1):
                if baris.lstrip().startswith("#"):
                    continue                       # komentar boleh menyebut angka lama (sejarah)
                if any(p in baris for p in penanda) and RX_POTONG.search(baris):
                    langgar.append(f"{rel}:{i} → {baris.strip()[:100]}")
        self.assertFalse(
            langgar,
            "Pesan galat penyedia MASIH dipotong sebelum disimpan:\n  " + "\n  ".join(langgar)
            + "\nTak ada aturan potong yang benar untuk semua penyedia (inti pesan bisa di awal, "
              "tengah, atau ujung). Simpan apa adanya — biayanya nol, dan tak ada yang memaksanya.")

    def test_alasan_rem_channel_tak_dibatasi_angka_karangan(self):
        """`production_paused_reason` memuat pesan penyedia. Batas 500 di sini memotongnya lagi."""
        t = _teks("src/orchestrator/producer.py")
        m = re.search(r"def _potong_rapi\([^)]*batas[^)]*=\s*(\d+)", t)
        self.assertIsNone(
            m, f"`_potong_rapi` masih memasang batas bawaan ({m.group(1) if m else ''}) pada alasan "
               f"rem channel — pesan penyedia terpotong lagi di lapis ini.")


class TestPeringkasanTampilanDIUMUMKAN(unittest.TestCase):
    """Peringkasan tampilan boleh — TAPI hanya bila diumumkan. Potongan senyap = penipuan yang
    sama, hanya pindah tempat."""

    def test_batas_telegram_dari_telegram_bukan_karangan(self):
        t = _teks("src/utils/telegram_notifier.py")
        self.assertRegex(t, r"BATAS_TELEGRAM\s*=\s*4096",
                         "batas Telegram tak dinyatakan sebagai tetapan bernama — angka tersebar lagi")

    def test_peringkas_ada_dan_mengumumkan(self):
        from src.utils.telegram_notifier import BATAS_TELEGRAM, ringkas_diumumkan
        pendek = "kunci ditolak penyedia"
        self.assertEqual(ringkas_diumumkan(pendek, 500), pendek,
                         "teks yang MUAT tidak boleh disentuh sama sekali")
        panjang = "x" * 5000
        hasil = ringkas_diumumkan(panjang, 300)
        self.assertLessEqual(len(hasil), 300, "hasil peringkasan melebihi ruang yang diberikan")
        self.assertRegex(hasil, r"dipotong\s+\d+",
                         "potongan tidak diumumkan — pembaca akan mengira ini pesan utuh (persis "
                         "cacat yang sedang diperbaiki)")
        self.assertIn("4096", str(BATAS_TELEGRAM), "batas Telegram berubah dari 4096")

    def test_peringkas_tahan_kasus_tepi(self):
        from src.utils.telegram_notifier import ringkas_diumumkan
        self.assertEqual(ringkas_diumumkan("", 100), "", "teks kosong tak boleh jadi aneh")
        self.assertEqual(ringkas_diumumkan(None, 100), "", "None tak boleh melempar galat")
        sempit = ringkas_diumumkan("y" * 900, 20)   # ruang lebih kecil dari penandanya sendiri
        self.assertLessEqual(len(sempit), 20, "ruang sempit → hasil tetap wajib muat")

    def test_notifikasi_gagal_upload_memakai_peringkas(self):
        t = _teks("src/utils/telegram_notifier.py")
        # Batas blok = sampai `def` berikutnya, BUKAN jumlah karakter tetap. Versi pertama memakai
        # jendela 2600 karakter dan berhenti sebelum badan fungsinya — merah palsu lagi.
        _i = t.index("def notify_publish_fail")
        _j = t.index("\n    def ", _i + 10)
        blok = t[_i:_j]
        # Komentar DIBUANG dulu: catatan sejarah di sana memang mengutip kode lama
        # (`str(error)[:200]`) untuk menjelaskan apa yang diperbaiki. Versi pertama uji ini membaca
        # kutipan itu sebagai kode dan merah palsu — alat ukur yang salah, bukan kodenya.
        kode = "\n".join(b for b in blok.split("\n") if not b.lstrip().startswith("#"))
        self.assertNotRegex(kode, r"str\(error\)\[:\s*\d+\s*\]",
                            "notifikasi masih memotong diam-diam dengan angka karangan")
        self.assertIn("ringkas_diumumkan", kode,
                      "notifikasi tak memakai peringkas ber-pengumuman")


class TestPesanNYATATersimpanUtuh(unittest.TestCase):
    """Bahan uji = pesan NYATA dari worker.log produksi (bukan karangan — aturan proyek: sampel
    harus dari produksi)."""

    GROQ = ("Error code: 429 - {'error': {'message': 'Rate limit reached for model "
            "`llama-3.3-70b-versatile` in organization `org_01ky4j1q1serys5h988mx3r1fr` service tier "
            "`on_demand` on tokens per day (TPD): Limit 100000, Used 97045, Requested 5359. Please "
            "try again in 34m37.056s. Need more tokens? Upgrade to Dev Tier today at "
            "https://console.groq.com/settings/billing', 'type': 'tokens', 'code': "
            "'rate_limit_exceeded'}}")

    def test_bagian_yang_selama_ini_hilang_ada_di_sampel(self):
        """Kalau sampelnya sendiri tak memuat bagian itu, ujian di bawah jadi hijau-palsu."""
        for wajib in ("try again in 34m37", "Limit 100000", "Used 97045", "console.groq.com"):
            self.assertIn(wajib, self.GROQ, f"sampel uji tak memuat {wajib!r}")

    def test_sampel_nyata_melewati_batas_lama(self):
        self.assertGreater(len(self.GROQ), 220,
                           "sampel tak melewati 220 — ia takkan membuktikan apa pun")

    def test_peringkas_telegram_tak_menghilangkan_sampel_nyata(self):
        from src.utils.telegram_notifier import BATAS_TELEGRAM, ringkas_diumumkan
        self.assertEqual(ringkas_diumumkan(self.GROQ, BATAS_TELEGRAM), self.GROQ,
                         "pesan penyedia NYATA (434 huruf) ikut dipangkas padahal jauh di bawah "
                         "batas Telegram — peringkasnya terlalu galak")


if __name__ == "__main__":
    unittest.main(verbosity=2)
