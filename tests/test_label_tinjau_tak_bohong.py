"""Kata "Perlu Ditinjau" hanya boleh dipakai untuk ANTREAN NYATA, bukan untuk buku-besar riwayat.

MASALAH YANG DIJAGA (dilaporkan owner 2026-08-05)
Di menu **Produksi → tab Perlu Ditinjau** muncul 2 item, tetapi di **menu Perlu Ditinjau** kosong.
Sebabnya bukan data hilang — **dua layar itu membaca tabel yang berbeda**:
  • daftar Runs & KPI channel  → `production_runs` (BUKU-BESAR riwayat, status terminal)
  • menu/halaman Perlu Ditinjau → `content_inventory.status='ready_with_issues'` (ANTREAN LIVE)

`QC_CONTENT_ARCHITECTURE.md` baris 496 sudah menetapkan aturannya jauh sebelum bug ini dilaporkan:

    "Perlu ditinjau" (aksi) = content_inventory.ready_with_issues (antrean LIVE), BUKAN
    production_runs.qc_failed (ledger historis — itu sebab "/review kosong tapi sinyal nyala").

Layar melanggarnya: ia memakai buku-besar sebagai LAMPU TUGAS. Akibat nyata yang terukur di DB live
05-Agu: **8 run uji** (5 tenant, terlama 4 minggu) memakai lencana "Perlu Ditinjau" untuk pekerjaan yang
TIDAK PERNAH ADA di aplikasi kita — videonya sudah terunggah privat ke YouTube Studio tenant, dan
keputusannya (publikkan / hapus) terjadi di YouTube, di luar kendali kita. Tak ada yang menunggu di sini.

PERBAIKANNYA = MENJUJURKAN LABEL, bukan menambah tombol.
  • buku-besar  → "Ada catatan QC" (fakta historis; barisnya sudah menyebut TEMPAT tinjau)
  • antrean     → "Perlu Ditinjau" (menu + halaman /review; di situ ADA tombol Pakai/Buang)

DUA ARAH DIJAGA — dan arah kedua sama pentingnya:
  (a) buku-besar tak boleh memakai nama antrean TANPA BUKTI    → lampu tugas palsu tak lahir lagi
      (boleh menyebutnya HANYA di dalam cabang yang sudah memeriksa penanda item-hidup —
       di situ barisnya memang ada, jadi janjinya benar)
  (b) antrean nyata WAJIB tetap bernama "Perlu Ditinjau"       → cegah perbaikan ini dilebihkan
      sampai menghapus nama antrean yang sah (over-correction = bug baru)
  (c) SUMBER ANGKA buku-besar WAJIB tetap `production_runs`    → rincian "dibuat = sukses + gagal +
      catatan" harus tetap berjumlah benar. Sesi berikutnya mungkin tergoda "menyelaraskan" angka ini
      ke antrean; itu memecah aritmetikanya. Uji ini menahan godaan itu.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FE = os.path.join(AKAR, "apps", "web", "src")

TABEL_RUNS = os.path.join(FE, "components", "runs-table.tsx")
DETAIL_RUN = os.path.join(FE, "app", "(app)", "runs", "[id]", "page.tsx")
BERANDA = os.path.join(FE, "app", "(app)", "dashboard", "page.tsx")
CHANNEL = os.path.join(FE, "app", "(app)", "channels", "[id]", "page.tsx")
ANTREAN = os.path.join(FE, "app", "(app)", "review", "page.tsx")
NAVIGASI = os.path.join(FE, "components", "app-shell.tsx")

# Berkas yang menampilkan BUKU-BESAR (production_runs) → haram memakai nama antrean tanpa bukti.
BUKU_BESAR = {"runs-table.tsx": TABEL_RUNS, "runs/[id]/page.tsx": DETAIL_RUN,
              "dashboard/page.tsx": BERANDA, "channels/[id]/page.tsx": CHANNEL}

# Penanda "run ini PUNYA baris di antrean live". Satu-satunya izin menyebut nama antrean.
PENJAGA_ITEM_HIDUP = "punyaItemTinjau"


def _teks(p: str) -> str:
    return open(p, encoding="utf-8", errors="ignore").read()


def _tanpa_komentar(s: str) -> str:
    """Buang komentar // dan /* */ — komentar BOLEH menyebut istilah lama saat menjelaskan sejarah;
    yang dijaga adalah teks yang MATA TENANT lihat.

    `(?<!:)` WAJIB: versi pertama memakai `//.*$` dan **melahap `https://…`** — separuh baris JSX
    yang memuat tautan ikut hilang, jadi pemindai buta pada baris-baris itu. Ditangkap oleh
    `test_pembuang_komentar_tidak_membuang_jsx` sebelum dipercaya. (Kelima kalinya dalam pekerjaan ini
    alat ukur saya sendiri yang cacat — karena itu setiap pemindai punya pagar-untuk-pagar.)
    """
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(re.sub(r"(?<!:)//.*$", "", b) for b in s.split("\n"))


class TestPemindaiBenar(unittest.TestCase):
    """Pagar-untuk-pagar: alat ukur yang salah lebih berbahaya daripada tak mengukur."""

    def test_semua_berkas_ada(self):
        for nama, p in {**BUKU_BESAR, "review/page.tsx": ANTREAN, "app-shell.tsx": NAVIGASI}.items():
            self.assertTrue(os.path.exists(p), f"berkas layar tak ditemukan: {nama} → {p}")

    def test_pembuang_komentar_tidak_membuang_jsx(self):
        """Regex // bisa melahap URL (https://…). Bila itu terjadi, pemindai jadi buta."""
        contoh = 'const a = "x"; // catatan\nconst b = <a href="https://y.com" />;'
        keluar = _tanpa_komentar(contoh)
        self.assertIn("https://y.com", keluar, "pembuang komentar melahap URL — pemindai tak bisa dipercaya")
        self.assertNotIn("catatan", keluar)


class TestBukuBesarTakMemakaiNamaAntrean(unittest.TestCase):

    def test_nama_antrean_hanya_dipakai_saat_barisnya_TERBUKTI_ada(self):
        """Aturannya bukan "kata itu haram", tapi **haram dipakai tanpa bukti**.

        Menyebut "Perlu Ditinjau" SAH bila layar sudah membuktikan barisnya memang ada di antrean —
        yaitu di dalam cabang yang memeriksa penanda item-hidup. Di luar cabang itu (lencana status,
        nama tab, label KPI, kalimat tetap) kata tersebut menjanjikan pekerjaan yang tak ada.

        Konteks 260 karakter ke ATAS diperiksa karena penjaganya adalah syarat ternary yang biasanya
        berada di baris sebelumnya (`{punyaItemTinjau\\n  ? <>…Perlu Ditinjau…`)."""
        langgar = []
        for nama, p in BUKU_BESAR.items():
            t = _tanpa_komentar(_teks(p))
            for m in re.finditer(r"Perlu Ditinjau|Perlu tinjau|perlu ditinjau|Needs Review", t):
                if PENJAGA_ITEM_HIDUP in t[max(0, m.start() - 260):m.start()]:
                    continue                    # sudah dibuktikan ADA barisnya → penyebutan sah
                baris = t[:m.start()].count("\n") + 1
                langgar.append(f"{nama}:{baris} → …{t[max(0, m.start() - 70):m.start() + 45]}…")
        self.assertFalse(
            langgar,
            "Nama antrean 'Perlu Ditinjau' dipakai TANPA membuktikan barisnya ada:\n  "
            + "\n  ".join(langgar)
            + "\nIni melahirkan lampu tugas palsu: tenant mengira ada pekerjaan di aplikasi, padahal "
              "keputusannya di YouTube Studio. Untuk buku-besar pakai 'Ada catatan QC'; nama antrean "
              f"hanya boleh di dalam cabang ber-`{PENJAGA_ITEM_HIDUP}`.")

    def test_label_pengganti_ada_dan_dwibahasa(self):
        """§3.5 CLAUDE.md: satu bahasa = cacat. Label baru wajib punya pasangan ID/EN.
        Pencocokan TAK peka huruf besar-kecil: di tengah kalimat ejaannya 'ada catatan QC'
        (Beranda), sebagai label berdiri sendiri 'Ada catatan QC' — keduanya benar."""
        for nama, p in BUKU_BESAR.items():
            t = _teks(p)
            self.assertRegex(t, r"(?i)ada catatan QC",
                             f"{nama}: label pengganti 'Ada catatan QC' tak ditemukan — status QC "
                             f"kehilangan namanya sama sekali")
            self.assertRegex(t, r'data-en|\ben=\{?"',
                             f"{nama}: tak ada penanda bahasa Inggris di dekat label — §3.5 dilanggar")


class TestAntreanNyataTetapBernamaBenar(unittest.TestCase):
    """Arah kebalikan. Perbaikan yang DILEBIHKAN sampai menghapus nama antrean = bug baru."""

    def test_menu_navigasi_masih_perlu_ditinjau(self):
        t = _teks(NAVIGASI)
        self.assertIn("Perlu Ditinjau", t,
                      "menu navigasi kehilangan nama 'Perlu Ditinjau' — tenant tak lagi punya pintu ke "
                      "antrean yang BENAR-BENAR menunggu keputusannya (tombol Pakai/Buang ada di situ)")

    def test_halaman_antrean_masih_perlu_ditinjau(self):
        t = _teks(ANTREAN)
        self.assertIn("Perlu Ditinjau", t, "halaman /review kehilangan judulnya")
        self.assertIn("ready_with_issues", t,
                      "halaman /review tak lagi membaca antrean live `ready_with_issues` — sumbernya salah")


class TestAritmetikaBukuBesarTerjaga(unittest.TestCase):
    """`dibuat = sukses + gagal + catatan` harus tetap berjumlah benar.

    Godaan sesi berikutnya: "selaraskan angka ini dengan menu Perlu Ditinjau". Kalau satu bagian
    dihitung dari tabel ANTREAN sementara sisanya dari BUKU-BESAR, jumlahnya pecah — dan itu bug baru
    yang lahir dari perbaikan bug lama."""

    def test_hitungan_beranda_tetap_dari_production_runs(self):
        t = _teks(BERANDA)
        m = re.search(r'\.in\("status",\s*\[\s*"qc_failed"', t)
        self.assertIsNotNone(
            m, "hitungan 'ada catatan QC' di Beranda tak lagi membaca production_runs.qc_failed — "
               "rincian Success Rate tak akan berjumlah benar lagi (dibuat ≠ sukses+gagal+catatan)")

    def test_kpi_channel_tetap_dari_production_runs(self):
        t = _teks(CHANNEL)
        self.assertRegex(
            t, r'cntRun\(\[\s*"qc_failed"',
            "KPI channel tak lagi menghitung dari buku-besar run — 'Total run' tak akan cocok dengan "
            "rinciannya")


class TestJalanBuntuKeHalamanKosongTertutup(unittest.TestCase):
    """Cacat terukur: halaman detail run menampilkan tombol 'Tinjau' → /review TANPA SYARAT.
    Untuk 8 dari 9 run ber-catatan QC, halaman itu KOSONG ⇒ tenant menabrak dinding."""

    PENJAGA = PENJAGA_ITEM_HIDUP

    def test_setiap_tautan_ke_review_dijaga_penanda_item_hidup(self):
        t = _tanpa_komentar(_teks(DETAIL_RUN))
        self.assertIn(self.PENJAGA, t,
                      f"penanda '{self.PENJAGA}' tak ada — halaman detail run tak bisa membedakan run "
                      f"yang PUNYA baris antrean live dari yang tidak, jadi tautannya pasti menyesatkan "
                      f"salah satu pihak")
        telanjang = []
        for m in re.finditer(r'href="/review"', t):
            konteks = t[max(0, m.start() - 600):m.start()]
            if self.PENJAGA not in konteks:
                telanjang.append(t[max(0, m.start() - 90):m.start() + 40].replace("\n", " ")[-120:])
        self.assertFalse(
            telanjang,
            "Tautan ke /review yang TIDAK dijaga penanda item-hidup:\n  " + "\n  ".join(telanjang)
            + f"\nSetiap tautan ke /review wajib berada di dalam cabang yang memeriksa "
              f"`{self.PENJAGA}`; tanpa itu tenant dikirim ke halaman kosong.")

    def test_halaman_detail_membaca_antrean_live(self):
        t = _teks(DETAIL_RUN)
        self.assertIn("ready_with_issues", t,
                      "halaman detail run tak membaca antrean live — mustahil ia tahu apakah /review "
                      "punya barisnya; keputusannya akan jadi tebakan")


class TestCatatanQCTidakDisembunyikan(unittest.TestCase):
    """Laci run dulu menampilkan diagram 8 langkah dan MENYEMBUNYIKAN catatan QC-nya — padahal justru
    catatan itu satu-satunya informasi yang tenant butuhkan ("Durasi 35.2s di luar ±15% target 60s").
    Datanya SUDAH ada di DB; hanya tak ditampilkan."""

    def test_laci_menampilkan_catatan_qc_untuk_status_review(self):
        t = _tanpa_komentar(_teks(TABEL_RUNS))
        self.assertIn("Catatan QC", t,
                      "laci run tak punya bagian 'Catatan QC' — alasan sebenarnya tetap tersembunyi "
                      "di balik diagram pipeline")
        # error_message harus dipakai untuk DUA keadaan: failed (sudah ada) + review (baru).
        self.assertGreaterEqual(
            len(re.findall(r"error_message", t)), 2,
            "`error_message` hanya dipakai sekali — status 'ada catatan QC' masih tak menampilkan "
            "sebabnya")


if __name__ == "__main__":
    unittest.main(verbosity=2)
