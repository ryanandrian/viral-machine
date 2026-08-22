"""Run gagal yang SUDAH diulang wajib mengatakan hasil ulangannya — bukan diam sebagai "Gagal".

MASALAH YANG DIJAGA (dilaporkan owner 2026-08-22)
Tombol "Jalankan ulang" menulis baris antrean ber-`source_run_id` = run asal. Terukur: kolom itu
punya **NOL pembaca** di seluruh aplikasi (satu-satunya penyebutnya = baris yang MENULISnya).
Akibatnya, sesudah ulangan BERHASIL:
  • baris run asal tetap berlencana "Gagal" tanpa keterangan apa pun  → *"terkesan produksi ulangnya gagal"*
  • tombol "Jalankan ulang" tetap hidup                              → sekali tekan = produksi baru
    lagi + kredit AI tenant terbakar untuk video yang sudah jadi (terjadi 22-Agu: 1 produksi 6m37s)

YANG DIJAGA (perilaku, bukan letak kode):
  1. kedua layar (daftar Runs & halaman run) MEMBACA `source_run_id` — kolomnya berhenti jadi kolom mati
  2. keterangannya INFORMATIF: menyebut SUKSES/GAGAL + NOMOR run hasil (owner: "sudah diulang" saja
     masih terkesan gagal) — dan nomornya dari data, bukan dirakit dari potongan teks
  3. tombol "Jalankan ulang" DIMATIKAN saat ulangan masih jalan / sudah berhasil; tetap HIDUP bila
     ulangannya juga gagal (kunci wajib punya jalur buka — §PAYMENT §10e-2)
  4. baris run gagal TIDAK dihapus dari daftar — itu riwayat nyata (buku-besar tak boleh dipalsukan)
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABEL = os.path.join(AKAR, "apps/web/src/components/runs-table.tsx")
DETAIL = os.path.join(AKAR, "apps/web/src/app/(app)/runs/[id]/page.tsx")


def _baca(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """Komentar pernah MENYELAMATKAN uji palsu (kata yang dijaga dikutip di komentar sebelahnya)."""
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))


class TestKolomTautanUlanganDibaca(unittest.TestCase):

    def test_daftar_runs_membaca_source_run_id(self):
        """MENGAMBIL kolomnya, bukan cuma menyebutnya."""
        isi = _tanpa_komentar(_baca(TABEL))
        self.assertRegex(isi, r'select\("[^"]*source_run_id',
                         "daftar Runs tak MENGAMBIL tautan ulangan → baris gagal tetap membisu")
        self.assertIn('"retry"', isi, "daftar Runs tak menyaring pekerjaan jenis ulangan")

    def test_halaman_run_membaca_source_run_id(self):
        """WAJIB berupa penyaring bacaan — bukan baris yang MENULIS tautan itu (tombol ulang).
        Versi pertama uji ini hijau tanpa perbaikan apa pun karena mencocoki baris penulisnya."""
        isi = _tanpa_komentar(_baca(DETAIL))
        self.assertRegex(isi, r'eq\("source_run_id"',
                         "halaman run tak MENYARING tautan ulangan → tombol tetap menawarkan ulangan")


class TestKeteranganInformatif(unittest.TestCase):
    """Owner 22-Agu: *"kalau cuma 'sudah diulang', kesannya masih gagal"* → wajib sebut hasil + nomor."""

    def test_kedua_layar_menyebut_sukses(self):
        for p in (TABEL, DETAIL):
            isi = _tanpa_komentar(_baca(p))
            self.assertRegex(isi, r"diulang dan sukses",
                             f"{os.path.basename(p)}: keterangan ulangan tak menyebut SUKSES")

    def test_kedua_layar_menyebut_nomor_run_hasil(self):
        """Nomor diambil dari baris run hasil (bukan dirakit dari potongan `run_id`)."""
        for p in (TABEL, DETAIL):
            isi = _tanpa_komentar(_baca(p))
            self.assertRegex(isi, r"RUN #\$\{", f"{os.path.basename(p)}: nomor run hasil tak ditampilkan")
            self.assertRegex(isi, r"/runs/\$\{", f"{os.path.basename(p)}: nomor run hasil tak bisa dibuka")

    def test_nomor_tak_dirakit_dari_potongan_teks(self):
        """`direct-<8 huruf pertama>` = perakitan rapuh; nomor wajib dari baris production_runs."""
        for p in (TABEL, DETAIL):
            isi = _tanpa_komentar(_baca(p))
            self.assertNotRegex(isi, r'"direct-"\s*\+', f"{os.path.basename(p)}: nomor run dirakit dari teks")
            self.assertNotRegex(isi, r"`direct-\$\{", f"{os.path.basename(p)}: nomor run dirakit dari teks")


class TestTombolUlangTakBisaBakarKredit(unittest.TestCase):

    def _blok_tombol(self) -> str:
        isi = _tanpa_komentar(_baca(DETAIL))
        i = isi.index("onClick={retry}")
        awal = isi.rindex("<button", 0, i)
        return isi[awal:isi.index("</button>", i)]

    def test_tombol_dimatikan_oleh_keadaan_ulangan(self):
        blok = self._blok_tombol()
        self.assertRegex(blok, r"disabled=\{[^}]*ulangan",
                         f"tombol Jalankan ulang tak melihat keadaan ulangan: {blok[:200]}")

    def test_keadaan_ulangan_benar_benar_menutup_tombol(self):
        """Penjaga tak boleh jadi KODE MATI. Versi pertama uji ini lolos saat aturannya diganti
        `const ulanganMenutup = false;` — karena kata yang dicarinya masih ada di tempat lain di
        berkas yang sama. Kini yang diperiksa = ISI aturannya, dipotong sampai titik-koma."""
        isi = _tanpa_komentar(_baca(DETAIL))
        m = re.search(r"const\s+(ulanganMenutup|tutupUlang|ulangan\w*Selesai)\s*=(.*?);", isi, re.S)
        self.assertIsNotNone(m, "tak ada aturan yang menghitung kapan tombol ditutup")
        aturan = m.group(2)
        self.assertRegex(aturan, r"ulangan\s*\.\s*jobStatus",
                         f"aturan tutup tak membaca keadaan pekerjaan ulangan: {aturan.strip()[:160]}")
        self.assertIn("producing", aturan, "keadaan 'sedang diulang' tak diperhitungkan")
        self.assertRegex(aturan, r"ulangan\s*\.\s*runStatus",
                         "aturan tutup tak melihat hasil run ulangan")
        self.assertRegex(aturan, r'"failed"',
                         "aturan tutup tak membiarkan ulangan-yang-juga-gagal diulang → jalur buka hilang")


class TestRiwayatTakDipalsukan(unittest.TestCase):

    def test_baris_gagal_tak_disaring_keluar_dari_daftar(self):
        """Perbaikan ini menambah KETERANGAN; menyembunyikan barisnya = memalsukan buku-besar."""
        isi = _tanpa_komentar(_baca(TABEL))
        self.assertNotRegex(isi, r"filter\([^)]*ulangan[^)]*\)",
                            "baris run gagal disaring keluar dari daftar — buku-besar dipalsukan")


class TestKalimatDaftarRunsTakMenjanjikanProgress(unittest.TestCase):
    """P3 — kalimat lama menjanjikan progress yang layar itu tak pernah tampilkan."""

    def test_janji_progress_dicabut(self):
        """Komentar dibuang dulu: yang dijaga = teks yang DILIHAT tenant, bukan catatan kode."""
        isi = _tanpa_komentar(_baca(TABEL))
        self.assertNotIn("progress muncul di sini", isi,
                         "kalimat yang menjanjikan progress masih ada padahal tak ditampilkan")
        self.assertNotIn("progress appears here", isi)

    def test_kalimat_pengganti_dwibahasa(self):
        """Jangkar = JSX-nya (`data-id>Produksi langsung`), bukan kemunculan kata pertama — versi
        pertama uji ini jatuh ke KOMENTAR di atas kueri, jendelanya tak pernah mencapai panelnya."""
        isi = _baca(TABEL)
        i = isi.index("data-id>Produksi langsung")
        blok = isi[i:i + 1800]
        self.assertRegex(blok, r"data-id>[^<]*setelah selesai", "kalimat pengganti (ID) tak ada")
        self.assertRegex(blok, r"data-en>[^<]*(finish|complete)", "kalimat pengganti (EN) tak ada")


if __name__ == "__main__":
    unittest.main()
