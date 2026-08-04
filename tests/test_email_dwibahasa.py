"""Email ke tenant WAJIB dwibahasa — badan DAN subjek.

SSOT: `CLAUDE.md` §3.5 — *"Teks UI/email = dwibahasa ID/EN via mekanisme `Bi`. Satu bahasa = cacat."*

MASALAH YANG DIJAGA (diukur 2026-08-04)
Keadaan BERSIH: **12 dari 12** fungsi `notify_*` memakai `_bi()` (badan Inggris di atas, Indonesia di
bawah, dipisah garis) dan **12 dari 12 subjek dwibahasa** (pola inline `"EN / ID — MesinViral"`).
Tapi — seperti setiap temuan malam ini — kebersihan itu hasil DISIPLIN, bukan penjagaan: **nol uji**
memeriksanya. Email ke-13 bisa lahir satu bahasa, dan yang menemukannya adalah tenant yang menerima
surat dalam bahasa yang tak ia pahami — pada momen paling sensitif (tagihan gagal, akun diblokir,
data akan dihapus).

CATATAN ALAT UKUR (pelajaran 04-Agu, ketiga kalinya alat saya salah malam itu): pemeriksaan pertama
menghitung `_bi(` per fungsi dan curiga karena hanya 1 panggilan untuk 29 baris teks. Ternyata itu
BENAR — `_bi(en_block, id_block)` membawa DUA BLOK UTUH sekaligus. Dan kolom "subject via _bi" pertama
melaporkan "-" untuk semua, padahal subjeknya dwibahasa INLINE. **Hitungan mentah tanpa membaca kode
menghasilkan dua kesimpulan salah berturut-turut** — karena itu uji ini memeriksa POLA YANG NYATA
dipakai kode, bukan pola yang diasumsikan.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL = os.path.join(AKAR, "src", "utils", "email.py")


def _fungsi_notify() -> list[tuple[str, str]]:
    s = open(EMAIL, encoding="utf-8").read()
    return re.findall(r"\ndef (notify_\w+)\((.*?)(?=\ndef |\Z)", s, re.S)


class TestMekanismeDwibahasaEmailUtuh(unittest.TestCase):

    def test_fungsi_bi_masih_menggabung_dua_bahasa(self):
        """Kalau `_bi` sendiri berubah jadi satu bahasa, SELURUH 12 email ikut cacat tanpa satu pun
        uji lain merah. Ini pemeriksaan paling menentukan di berkas ini."""
        s = open(EMAIL, encoding="utf-8").read()
        m = re.search(r"def _bi\(([^)]*)\)[^:]*:(.*?)(?=\n\n|\ndef )", s, re.S)
        self.assertIsNotNone(m, "fungsi _bi() hilang dari email.py — mekanisme dwibahasa lenyap")
        params, badan = m.group(1), m.group(2)
        self.assertIn("en", params, "_bi tak lagi menerima blok Inggris")
        self.assertIn("id_", params, "_bi tak lagi menerima blok Indonesia")
        self.assertIn("{en}", badan, "_bi tak lagi memasang blok Inggris ke hasil")
        self.assertIn("{id_}", badan, "_bi tak lagi memasang blok Indonesia ke hasil")

    def test_ada_cukup_fungsi_email_untuk_diperiksa(self):
        """Pagar untuk pagar: bila pemindai rusak, uji di bawah hijau-palsu."""
        n = len(_fungsi_notify())
        self.assertGreaterEqual(n, 10, f"hanya {n} fungsi notify_* ditemukan — pemindai rusak")


class TestSetiapEmailDwibahasa(unittest.TestCase):

    def test_badan_setiap_email_memakai_bi(self):
        tanpa = [n for n, badan in _fungsi_notify() if "_bi(" not in badan]
        self.assertFalse(tanpa,
                         "Email dengan badan SATU BAHASA (CLAUDE.md §3.5): " + str(tanpa)
                         + "\nTenant menerima surat dalam bahasa yang mungkin tak ia pahami — dan ini "
                           "terjadi pada momen paling sensitif (tagihan gagal, akun diblokir, data dihapus).")

    def test_subjek_setiap_email_dwibahasa(self):
        """Pola nyata: `"Payment received / Pembayaran diterima — MesinViral"` (dua bahasa dipisah '/').
        Subjek satu bahasa = tenant tak paham surat apa ini SEBELUM membukanya."""
        kurang = []
        for nama, badan in _fungsi_notify():
            m = re.search(r"send_email\(\s*\n?\s*to,\s*\n?\s*(f?[\"'][^\"']+[\"'])", badan, re.S)
            subj = m.group(1) if m else ""
            if not subj:
                m2 = re.search(r"subject\s*=\s*(f?[\"'][^\"']+[\"'])", badan)
                subj = m2.group(1) if m2 else ""
            if not subj:
                kurang.append(f"{nama} (subjek tak terbaca — bentuk panggilan berubah?)")
                continue
            # dwibahasa bila ada pemisah '/' antar-frasa, ATAU dirakit dari dua variabel bahasa.
            dua = ("/" in subj) or re.search(r"\{en_?\w*\}.*\{id_?\w*\}", subj)
            if not dua:
                kurang.append(f"{nama}: {subj[:70]}")
        self.assertFalse(kurang, "Subjek email SATU BAHASA (CLAUDE.md §3.5):\n  " + "\n  ".join(kurang))

    def test_kedua_blok_bahasa_benar_benar_berisi(self):
        """`_bi("", "")` lolos uji 'memakai _bi' tapi mengirim email kosong satu sisi.

        CATATAN ALAT UKUR: versi pertama uji ini SALAH — ia mencari koma "pemisah argumen" pada
        kedalaman kurung 0, padahal teks emailnya sendiri memuat koma (`f"Hi,\\n\\nYour payment..."`)
        ⇒ argumen pertama terpotong jadi `f"Hi` dan 11 dari 12 email dilaporkan cacat PALSU.
        Uji yang berbohong = bug baru yang ditanam, jadi pendekatannya diganti: periksa PENANDA
        BAHASA yang nyata, tak bergantung pada penguraian koma sama sekali.
        """
        PENANDA_EN = ("Hi,", "Your ", "your ", "payment", "plan", "account", "trial", "data")
        PENANDA_ID = ("Halo", "Anda", "Pembayaran", "paket", "Langganan", "Trial Anda", "Data Anda")
        cacat = []
        for nama, badan in _fungsi_notify():
            i = badan.find("_bi(")
            if i < 0:
                continue                      # sudah ditangkap uji lain di kelas ini
            wilayah = badan[i:i + 1600]       # cukup memuat kedua blok pada email terpanjang
            n_teks = len(re.findall(r"[\"'][^\"']{15,}[\"']", wilayah))
            if n_teks < 2:
                cacat.append(f"{nama}: _bi() hanya membawa {n_teks} blok teks (butuh ≥2, satu per bahasa)")
                continue
            if not any(p in wilayah for p in PENANDA_EN):
                cacat.append(f"{nama}: blok INGGRIS tak ditemukan")
            if not any(p in wilayah for p in PENANDA_ID):
                cacat.append(f"{nama}: blok INDONESIA tak ditemukan")
        self.assertFalse(cacat, "Blok bahasa tak berisi:\n  " + "\n  ".join(cacat))


if __name__ == "__main__":
    unittest.main(verbosity=2)
