"""Setiap rute API WAJIB terjaga — atau publik dengan ALASAN TERTULIS.

MASALAH YANG DIJAGA (2026-08-04)
Sapuan manual malam ini SALAH DUA KALI: pola grep-nya tidak memuat `requireSuperAdmin`, lalu tidak
memuat `requireReseller` — sehingga melaporkan **22 rute "tanpa penjaga"** yang sebenarnya terjaga.
Owner: *"gila, alat ukur saja salah."* Itu keluhan yang paling dalam malam ini, dan benar: **alat ukur
yang salah lebih berbahaya daripada tidak mengukur**, karena ia melahirkan "temuan" palsu yang memicu
perubahan tanpa sebab — mesin rantai bug-fix tanpa ujung.

AKAR KESALAHANNYA: daftar nama penjaga DIHAFAL penulis pemeriksa. Penjaga baru = pemeriksa buta.
**MAKA: uji ini MENEMUKAN daftar penjaga dari kode** (`apps/web/src/lib/**/guard.ts`), tidak menghafalnya.
Menambah `lib/xxx/guard.ts` baru otomatis ikut terhitung — kelas kesalahan itu dihapus, bukan ditambal.

KEADAAN TERUKUR saat uji ini lahir: 81 rute · 71 terjaga sesi/peran · 10 publik-secara-desain
(masing-masing diperiksa satu per satu, lihat `PUBLIK_SENGAJA`). **Nol celah.**
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(AKAR, "apps", "web", "src", "app", "api")
LIB = os.path.join(AKAR, "apps", "web", "src", "lib")

# Rute yang SENGAJA publik + alasannya + mekanisme penggantinya.
# Tiap baris = hasil pemeriksaan satu per satu pada 2026-08-04 (bukan daftar agar uji hijau).
PUBLIK_SENGAJA = {
    "auth/signup/route.ts":              "pendaftaran akun — mustahil butuh sesi",
    "auth/forgot-password/route.ts":     "lupa sandi — pengguna justru tak bisa masuk",
    "feedback/route.ts":                 "formulir masukan publik (anonim, ditulis ke tabel ber-RLS)",
    "contact/route.ts":                  "formulir kontak halaman pemasaran",
    "version/route.ts":                  "info versi build — nol data tenant",
    "public/company/route.ts":           "profil perusahaan untuk halaman pemasaran (data publik)",
    "public/status/route.ts":            "status layanan untuk halaman pemasaran (nol data tenant)",
    "partner/check/route.ts":            "validasi kode rujukan SAAT MENDAFTAR — pemanggil belum punya akun",
    "partner/reseller-register/route.ts": "pendaftaran reseller; AGEN yang menyetujui (SPEC AGENT §2.4), status lahir 'pending'",
    "lifecycle/reactivate/route.ts":     "tautan 1-klik dari email; OTENTIKASI = token HMAC diverifikasi server (verify_state) — tenant belum tentu login",
}


def _penjaga_dari_kode() -> set[str]:
    """TEMUKAN nama fungsi penjaga dari berkas guard di lib/ — jangan dihafal.

    Inilah perbaikan atas kesalahan alat ukur 04-Agu: penjaga baru ikut terhitung otomatis."""
    nama: set[str] = set()
    for p in glob.glob(os.path.join(LIB, "**", "*guard*"), recursive=True):
        teks = open(p, encoding="utf-8", errors="ignore").read()
        nama |= set(re.findall(r"export\s+(?:async\s+)?function\s+(\w+)", teks))
    return nama


def _pola_penjaga() -> re.Pattern:
    """Penjaga = fungsi guard yang ditemukan + mekanisme setara yang dipakai kode ini:
    sesi Supabase langsung (`auth.getUser`) dan rahasia internal antar-layanan."""
    bagian = sorted(_penjaga_dari_kode()) + [r"auth\.getUser", "X-Internal-Secret", "MV_INTERNAL_SECRET"]
    return re.compile("|".join(bagian))


def _rute() -> list[str]:
    return sorted(os.path.relpath(p, API) for p in
                  glob.glob(os.path.join(API, "**", "route.ts"), recursive=True))


class TestPenjagaDitemukanBukanDihafal(unittest.TestCase):

    def test_penjaga_ditemukan_dari_kode(self):
        """Pagar untuk pagar #1: bila penemuan gagal, uji utama menjadi hijau-palsu."""
        nama = _penjaga_dari_kode()
        self.assertGreaterEqual(len(nama), 3,
                                f"hanya {len(nama)} fungsi penjaga ditemukan ({sorted(nama)}) — "
                                f"berkas guard dipindah/berubah nama? Pemeriksa ini jadi buta.")

    def test_ada_rute_untuk_diperiksa(self):
        """Pagar untuk pagar #2."""
        self.assertGreaterEqual(len(_rute()), 50, "pemindai rute API rusak")


class TestSetiapRuteTerjagaAtauBeralasan(unittest.TestCase):

    def test_tak_ada_rute_terbuka_tanpa_alasan(self):
        pola = _pola_penjaga()
        telanjang = []
        for r in _rute():
            teks = open(os.path.join(API, r), encoding="utf-8", errors="ignore").read()
            if pola.search(teks):
                continue
            if r.replace(os.sep, "/") in PUBLIK_SENGAJA:
                continue
            telanjang.append(r)
        self.assertFalse(
            telanjang,
            "Rute API tanpa penjaga DAN tanpa alasan publik tertulis:\n  "
            + "\n  ".join(telanjang)
            + "\nTambahkan penjaga (requireSuperAdmin / requireAgent / requireReseller / auth.getUser), "
              "ATAU daftarkan di PUBLIK_SENGAJA beserta ALASAN + mekanisme penggantinya.")

    def test_daftar_publik_tidak_menyimpan_rute_hantu(self):
        """Rute yang sudah dihapus tapi masih terdaftar publik = daftar yang membusuk; pembaca
        berikutnya menganggap daftar ini terpelihara padahal tidak."""
        ada = {r.replace(os.sep, "/") for r in _rute()}
        hantu = sorted(set(PUBLIK_SENGAJA) - ada)
        self.assertFalse(hantu, f"PUBLIK_SENGAJA memuat rute yang tak ada lagi: {hantu}")

    def test_setiap_alasan_publik_bisa_dibaca_manusia(self):
        for r, alasan in PUBLIK_SENGAJA.items():
            self.assertTrue(alasan and len(alasan.strip()) >= 20,
                            f"PUBLIK_SENGAJA['{r}'] tanpa alasan memadai — 'lupa' yang menyamar 'sengaja'")

    def test_rute_yang_sudah_terjaga_tidak_ikut_didaftar_publik(self):
        """Rute terjaga yang IKUT didaftar publik = niat bertentangan; kalau kelak penjaganya
        terlepas, daftar publik ini akan menutupi kebocorannya dari uji di atas."""
        pola = _pola_penjaga()
        salah = []
        for r in PUBLIK_SENGAJA:
            p = os.path.join(API, r)
            if os.path.exists(p) and pola.search(open(p, encoding="utf-8", errors="ignore").read()):
                salah.append(r)
        self.assertFalse(salah, f"rute ini TERJAGA tapi didaftar publik — cabut dari PUBLIK_SENGAJA: {salah}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
