"""Tabel yang bisa DITULIS langsung dari browser tak boleh bertambah diam-diam.

SSOT: `PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md` (§7 pintu keluar nilai) —
  *"Tabel yang bisa ditulis browser (RLS non-SELECT) = 6: `channels`(insert/update) · `direct_jobs`(insert)
    · `niche_requests` · `support_messages` · `support_tickets`. Hanya `direct_jobs` yang memicu produksi."*
dan *"3 lapis pagar WAJIB, masing-masing menjaga jalur berbeda; tidak saling menggantikan"* — RLS menjaga
jalur **browser → DB LANGSUNG**, yang TIDAK lewat rute API sama sekali (jadi `test_rute_api_terjaga.py`
tak bisa menutupnya).

KENAPA INI PALING BERBAHAYA BILA BERTAMBAH: pintu 5 di §7 (tombol "Jalankan ulang") dulu menyuntik
`direct_jobs` LANGSUNG dari browser tanpa satu pun pemeriksaan status — sumber salah satu dari 11 celah
yang ditutup [B24]. Setiap tabel baru yang bisa ditulis browser = pintu baru dengan sifat yang sama.

DIVERIFIKASI 2026-08-04 (migrasi + DB live):
  policy tulis ditemukan di 7 tabel; **2 di antaranya HANTU** — `production_schedules` &
  `tenant_api_accounts` sudah TIDAK ADA di DB live (policy ikut terhapus bersama tabelnya).
  ⇒ kenyataan = **5 tabel**, PERSIS seperti klaim dokumen. Dokumen BENAR.

CATATAN ALAT UKUR (pelajaran mahal 04-Agu): versi pertama pemindai ini SALAH — ia memproses semua
`CREATE POLICY` lebih dulu lalu semua `DROP POLICY`, padahal di migr 0191 urutannya DROP-lalu-CREATE,
sehingga policy `direct_jobs` yang BARU justru terhapus dari hitungan. Yang menangkapnya adalah
**DOKUMEN** — ia menyebut `direct_jobs`, alat bilang tidak, jadi selisihnya diselidiki alih-alih
dipercaya. Karena itu pemindai di bawah memproses pernyataan MENURUT URUTAN KEMUNCULAN.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOK = os.path.join(AKAR, "PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md")

# Tabel yang BOLEH ditulis browser + kenapa. Diverifikasi satu per satu ke DB live 2026-08-04.
DIIZINKAN = {
    "channels":         "tenant mengelola channelnya sendiri (insert/update); RLS memfilter tenant_id",
    "direct_jobs":      "SATU-SATUNYA pemicu produksi; RLS-nya memuat gerbang uji (migr 0191/0194)",
    "niche_requests":   "tenant memesan niche kustom; tak memicu produksi",
    "support_messages": "tenant membalas tiket dukungannya sendiri",
    "support_tickets":  "tenant membuka tiket dukungan",
}

# Policy yang tabelnya SUDAH DIHAPUS dari DB live → hantu, bukan pintu.
HANTU_TABEL_SUDAH_DIDROP = {
    "production_schedules": "tabel tak ada di DB live (diperiksa 2026-08-04)",
    "tenant_api_accounts":  "tabel tak ada di DB live (diperiksa 2026-08-04)",
}


def _tabel_bisa_ditulis() -> dict[str, set[str]]:
    """Policy tulis per tabel, memproses CREATE/DROP MENURUT URUTAN KEMUNCULAN.

    Urutan itu WAJIB: dalam satu berkas migrasi, pola bakunya adalah
    `DROP POLICY IF EXISTS x` lalu `CREATE POLICY x` (mengganti policy lama). Memproses semua CREATE
    lebih dulu lalu semua DROP akan MENGHAPUS policy yang justru baru dibuat — bug alat ukur 04-Agu."""
    aktif: dict[tuple[str, str], str] = {}
    for berkas in sorted(glob.glob(os.path.join(AKAR, "migrations", "*.sql"))):
        teks = open(berkas, encoding="utf-8", errors="ignore").read()
        kejadian = []
        for m in re.finditer(r"create\s+policy\s+\"?([^\"\s]+)\"?\s+on\s+(?:public\.)?(\w+)"
                             r"(.{0,120}?)\bfor\s+(insert|update|delete|all)\b", teks, re.I | re.S):
            kejadian.append((m.start(), "C", m.group(2).lower(), m.group(1), m.group(4).lower()))
        for m in re.finditer(r"drop\s+policy\s+(?:if\s+exists\s+)?\"?([^\"\s;]+)\"?\s+on\s+(?:public\.)?(\w+)",
                             teks, re.I):
            kejadian.append((m.start(), "D", m.group(2).lower(), m.group(1), None))
        for _, jenis, tabel, nama, aksi in sorted(kejadian, key=lambda x: x[0]):
            if jenis == "C":
                aktif[(tabel, nama)] = aksi
            else:
                aktif.pop((tabel, nama), None)
    keluar: dict[str, set[str]] = {}
    for (tabel, _), aksi in aktif.items():
        keluar.setdefault(tabel, set()).add(aksi)
    return keluar


class TestPemindaiSendiriBenar(unittest.TestCase):
    """Pagar-untuk-pagar. Alat ukur yang salah lebih berbahaya daripada tidak mengukur."""

    def test_menemukan_direct_jobs(self):
        """Kasus yang MEMBUKTIKAN bug urutan: `direct_jobs` di-DROP lalu di-CREATE di migr 0191.
        Bila pemindai kembali memproses CREATE-dulu-DROP-belakangan, tabel paling berbahaya
        (satu-satunya pemicu produksi) akan HILANG dari pengawasan tanpa satu pun uji merah."""
        t = _tabel_bisa_ditulis()
        self.assertIn("direct_jobs", t,
                      "pemindai kehilangan direct_jobs — bug urutan CREATE/DROP kembali")
        self.assertIn("insert", t["direct_jobs"])

    def test_menemukan_cukup_banyak_policy(self):
        t = _tabel_bisa_ditulis()
        self.assertGreaterEqual(len(t), 5, f"pemindai hanya menemukan {len(t)} tabel — polanya rusak")


class TestTakAdaPintuTulisBaru(unittest.TestCase):

    def test_setiap_tabel_bisa_ditulis_sudah_diizinkan(self):
        ditemukan = set(_tabel_bisa_ditulis())
        baru = sorted(ditemukan - set(DIIZINKAN) - set(HANTU_TABEL_SUDAH_DIDROP))
        self.assertFalse(
            baru,
            "TABEL BARU yang bisa ditulis LANGSUNG dari browser: " + str(baru) + "\n"
            "Ini pintu baru yang TIDAK lewat rute API (jadi penjaga rute tak menutupnya) — sifatnya "
            "sama dengan pintu 5 [B24] yang dulu menyuntik direct_jobs tanpa pemeriksaan status.\n"
            "Wajib: pastikan RLS-nya memuat pemeriksaan yang benar, lalu daftarkan di DIIZINKAN "
            "beserta alasannya. JANGAN sekadar didaftarkan agar uji hijau.")

    def test_alasan_izin_bisa_dibaca_manusia(self):
        for tabel, alasan in {**DIIZINKAN, **HANTU_TABEL_SUDAH_DIDROP}.items():
            self.assertTrue(alasan and len(alasan.strip()) >= 20,
                            f"alasan untuk '{tabel}' terlalu pendek — 'lupa' menyamar 'sengaja'")

    def test_direct_jobs_tetap_satu_satunya_pemicu_produksi(self):
        """Klaim dokumen yang paling menentukan. Bila tabel pemicu produksi bertambah tanpa disadari,
        seluruh gerbang uji [B24] bisa dilewati lewat pintu baru."""
        t = open(DOK, encoding="utf-8").read()
        self.assertRegex(t, r"[Hh]anya `direct_jobs` yang memicu produksi",
                         "klaim 'hanya direct_jobs yang memicu produksi' hilang dari SSOT — "
                         "pagar paling menentukan lenyap dari dokumen")


class TestDokumenSelarasDenganKenyataan(unittest.TestCase):

    def test_dokumen_menyebut_kelima_tabel_yang_diizinkan(self):
        """DOKUMEN ↔ KENYATAAN. Dokumen inilah yang menangkap bug alat ukur 04-Agu — ia harus tetap
        memuat daftarnya agar bisa menjadi pembanding independen di masa depan."""
        t = open(DOK, encoding="utf-8").read()
        for tabel in DIIZINKAN:
            self.assertIn(f"`{tabel}`", t,
                          f"`{tabel}` bisa ditulis browser tapi TIDAK tercantum di SSOT — "
                          f"dokumen berhenti bisa dipakai sebagai pembanding independen")


if __name__ == "__main__":
    unittest.main(verbosity=2)
