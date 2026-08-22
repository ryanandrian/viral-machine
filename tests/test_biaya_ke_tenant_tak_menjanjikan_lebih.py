"""Layar tenant HARAM menjanjikan biaya "nyata" saat angkanya perkiraan — dan haram membocorkan
kode internal mesin.

MASALAH YANG DIJAGA (arahan owner 2026-08-22: *"bagaimana caranya agar tidak terkesan bug
mesinviral.com di mata tenant"*)
Tiga tempat menjanjikan lebih dari yang bisa kita berikan:
  1. kolom Biaya AI (Runs)     : "Biaya AI BYOK **nyata** (konsumsi terukur × harga resmi provider)"
  2. sel biaya bila tak lengkap: ⚠️ + "model tanpa harga: `gemini-2.5-flash-preview-tts`"
     → tanda bahaya + KODE INTERNAL mentah di mata tenant; terbaca "aplikasinya rusak".
       Owner sudah pernah menyuruh mencabut nomor internal dari pesan tenant (12-Agu, `run_id`).
  3. kartu Biaya AI (Dashboard): "konsumsi terukur **nyata**" — dan menjumlahkan angka yang
     TIDAK lengkap TANPA satu penanda pun. Ini yang paling menyesatkan: diam-diam kurang.

Angka yang kurang sebagian itu WAJAR untuk sebuah PERKIRAAN, dan jadi BUG untuk sesuatu yang
mengaku "nyata". Jadi yang diperbaiki janjinya, bukan kekurangannya disembunyikan.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(AKAR, "apps/web/src/components/runs-table.tsx")
DASH = os.path.join(AKAR, "apps/web/src/app/(app)/dashboard/page.tsx")


def _baca(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi):
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))


class TestJanjiNyataDicabut(unittest.TestCase):

    def test_kolom_biaya_tak_lagi_mengaku_nyata(self):
        isi = _tanpa_komentar(_baca(RUNS))
        self.assertNotIn("BYOK nyata", isi, "kolom Biaya AI masih menjanjikan angka 'nyata'")
        self.assertNotIn("konsumsi terukur × harga resmi provider", isi,
                         "klaim 'konsumsi terukur' masih ada — itu janji yang tak selalu bisa dipenuhi")

    def test_kartu_dashboard_tak_lagi_mengaku_nyata(self):
        isi = _tanpa_komentar(_baca(DASH))
        self.assertNotIn("konsumsi terukur nyata", isi,
                         "kartu Biaya AI masih menjanjikan 'konsumsi terukur nyata'")

    def test_kata_perkiraan_dipakai_di_kedua_layar(self):
        for p in (RUNS, DASH):
            isi = _tanpa_komentar(_baca(p))
            self.assertRegex(isi, r"[Pp]erkiraan", f"{os.path.basename(p)}: tak menyebut ini perkiraan")


class TestKodeInternalTakBocorKeTenant(unittest.TestCase):

    def test_daftar_model_tak_ditempel_ke_layar_tenant(self):
        """`unpriced` = daftar kunci model internal. Boleh DIPAKAI sebagai penanda, haram DICETAK."""
        isi = _tanpa_komentar(_baca(RUNS))
        self.assertNotRegex(isi, r"unpriced\s*\.\s*join\(",
                            "kode internal model masih dicetak ke layar tenant")
        self.assertNotIn("model tanpa harga", isi,
                         "kalimat bernada galat internal masih tampil ke tenant")

    def test_penanda_tak_bernada_bahaya(self):
        isi = _tanpa_komentar(_baca(RUNS))
        i = isi.index("unpriced?.length")
        blok = isi[max(0, i - 700):i + 700]
        self.assertNotIn("⚠️", blok, "penanda masih bernada bahaya (⚠️) — terbaca sebagai bug kita")

    def test_kalimat_pengganti_menyebut_angka_bisa_lebih_tinggi(self):
        """Tenant perlu tahu ARAH ketidaklengkapannya, bukan cuma bahwa ia tak lengkap."""
        isi = _tanpa_komentar(_baca(RUNS))
        self.assertRegex(isi, r"lebih tinggi", "tak memberi tahu bahwa angka sebenarnya bisa lebih tinggi")


class TestDashboardTakDiamSaatAngkaKurang(unittest.TestCase):
    """Tempat paling menyesatkan hari ini: menjumlahkan angka kurang TANPA penanda."""

    def test_dashboard_menghitung_penanda_dari_data(self):
        """Penanda WAJIB dihitung dari `cost.unpriced` tiap run — bukan tebakan, bukan konstanta."""
        isi = _tanpa_komentar(_baca(DASH))
        self.assertRegex(isi, r"cost\?\.unpriced\?\.length\)\s*\w+\s*=\s*true",
                         "penanda ketaklengkapan tak dihitung dari data run")

    def test_penanda_benar_benar_MENENTUKAN_kalimatnya(self):
        """Versi pertama dua uji ini LOLOS saat syaratnya diganti `false ?` dan barisan
        penghitungnya dihapus — kalimatnya masih ada di berkas, jadi teks saja tak cukup.
        Yang diperiksa sekarang: kalimat itu dikendalikan oleh penanda dari data."""
        isi = _tanpa_komentar(_baca(DASH))
        self.assertRegex(isi, r"aiCost\.\w+\s*\?\s*\"perkiraan minimum",
                         "kalimat 'perkiraan minimum' tak dikendalikan penanda → kode mati")
        self.assertRegex(isi, r"aiCost\.\w+\s*\?\s*\"minimum estimate",
                         "kalimat Inggrisnya tak dikendalikan penanda → kode mati")


class TestDwibahasaTetap(unittest.TestCase):
    """§3.5 — teks layar wajib ID/EN. Perbaikan ini tak boleh menyisakan teks satu bahasa."""

    def test_kalimat_baru_punya_pasangan_inggris(self):
        """Jendela dipotong pada ELEMEN dwibahasanya (jangan jendela huruf sembarang: kalimat ID-nya
        panjang, jadi jendela sempit meleset dan jendela lebar bisa menangkap teks lain)."""
        isi = _baca(DASH)
        i = isi.index("perkiraan minimum")
        awal = isi.rindex("<Bi ", 0, i)
        akhir = isi.index("/>", i)
        elemen = isi[awal:akhir]
        self.assertIn("minimum estimate", elemen, "kalimat baru belum dwibahasa (ID ada, EN tidak)")


if __name__ == "__main__":
    unittest.main()
