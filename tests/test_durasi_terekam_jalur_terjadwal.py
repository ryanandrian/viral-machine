"""Durasi video WAJIB terekam di JALUR UTAMA (terjadwal) — bukan hanya jalur uji.

SSOT: `CLAUDE.md` §7.3 — *"Durasi video = HULU pipeline: perubahan apa pun yang menyentuhnya wajib
membuktikan durasi output tetap presisi (gerbang terkunci — paling butuh kehati-hatian)."*
Acuan mutu durasi: `QC_CONTENT_ARCHITECTURE.md` §2c.

MASALAH YANG DIJAGA (diukur ke DB live 2026-08-05)
`publisher.write_video(...)` meneruskan `file_size_mb` tapi **TIDAK** `duration_secs` — padahal:
  • producer SUDAH menyimpan `duration_secs` di metadata stok (`produce_one` dan `run_direct`),
  • `SupabaseWriter.write_video` SUDAH punya parameternya.
Hanya satu baris yang hilang. Akibat terukur:

| Jendela | Video | Durasi tercatat | KOSONG |
|---|---|---|---|
| 14 hari | 75 | 20 | **55 (73%)** |
| 30 hari | 156 | 35 | 121 |
| 60 hari | 244 | 80 | 164 |

Yang tercatat hanya video dari jalur UJI LANGSUNG (di situ `pipeline` menulis row `videos` sendiri).
Pola waktunya membuktikannya: video terbit pada jam terjadwal (07:00/12:00/14:00/23:00) berdurasi
KOSONG; yang terbit di jam tak beraturan (mis. 11:27 = uji langsung) TERCATAT.

**Kenapa ini penting padahal QC tetap jalan:** QC masih menahan video di luar rentang SEBELUM publish —
jadi ini bukan kebocoran mutu. Yang hilang adalah **JEJAKNYA**. Tanpa jejak, pergeseran presisi durasi
hanya terlihat saat tenant mengeluh, bukan saat terjadi — dan itu persis pola yang membuat masalah di
proyek ini selalu ditemukan terlambat. Ia juga membuat audit "durasi tetap presisi" (§7.3) MUSTAHIL
dilakukan untuk produksi terjadwal, yaitu 73% produksi.

CATATAN pengukuran (disiplin 04-Agu): perbandingan pertama memakai `channels.duration_preset` SEKARANG
terhadap video berbulan-bulan lalu → tampak selisih +15,9s di RAD The Explorer. Itu MENYESATKAN: preset
bisa berubah dan tak ada catatan preset per-video. Kesimpulan hanya diambil setelah dipersempit ke
jendela di mana presetnya pasti. **Selisih durasi historis TIDAK diklaim sebagai bug** — dan tak akan
bisa diklaim sampai target per-video ikut terekam (lihat kelas uji terakhir).
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISHER = os.path.join(AKAR, "src", "orchestrator", "publisher.py")
PRODUCER = os.path.join(AKAR, "src", "orchestrator", "producer.py")
WRITER = os.path.join(AKAR, "src", "utils", "supabase_writer.py")


def _panggilan_write_video() -> str:
    """Blok argumen `write_video(...)` di publisher (jalur terjadwal)."""
    s = open(PUBLISHER, encoding="utf-8").read()
    i = s.find("write_video(")
    assert i > 0, "panggilan write_video hilang dari publisher"
    return s[i:i + 2600]


class TestRantaiDurasiUtuh(unittest.TestCase):
    """Tiga mata rantai: producer menyimpan → publisher meneruskan → penulis menerima.
    Satu mata putus = jejak durasi hilang untuk 73% produksi, tanpa satu pun uji lain merah."""

    def test_producer_menyimpan_durasi_di_metadata_stok(self):
        s = open(PRODUCER, encoding="utf-8").read()
        self.assertGreaterEqual(
            len(re.findall(r'"duration_secs":\s*_?qc\.get\("duration"\)', s)), 2,
            "producer tak lagi menyimpan duration_secs di metadata stok — publisher takkan punya "
            "sumbernya (jalur terjadwal DAN uji langsung sama-sama harus menyimpannya)")

    def test_penulis_masih_menerima_parameter_durasi(self):
        s = open(WRITER, encoding="utf-8").read()
        self.assertRegex(s, r"duration_secs:\s*Optional\[float\]",
                         "write_video tak lagi menerima duration_secs — kolomnya jadi mustahil terisi")
        self.assertIn('"duration_secs"', s, "write_video tak lagi menulis kolom duration_secs")

    def test_publisher_MENERUSKAN_durasi(self):
        """Inti perbaikan 05-Agu. Baris inilah yang hilang selama ini."""
        blok = _panggilan_write_video()
        self.assertRegex(
            blok, r"duration_secs\s*=\s*meta\.get\(\s*[\"']duration_secs[\"']\s*\)",
            "publisher TIDAK meneruskan duration_secs ke write_video.\n"
            "Akibat terukur (DB live 05-Agu): 55 dari 75 video dalam 14 hari berkolom durasi KOSONG "
            "(73%) — hanya jalur uji langsung yang tercatat.\n"
            "Presisi durasi = gerbang PALING TERKUNCI (CLAUDE.md §7.3) jadi tak bisa diaudit untuk "
            "produksi terjadwal. QC tetap menjaga sebelum publish; yang hilang adalah JEJAKNYA.")

    def test_ukuran_berkas_tetap_diteruskan(self):
        """Regresi: jangan sampai menambah durasi malah menggeser argumen lain."""
        self.assertIn("file_size_mb", _panggilan_write_video(),
                      "file_size_mb hilang dari panggilan — regresi akibat suntingan durasi")


class TestTargetDurasiPerVideoBelumTerekam(unittest.TestCase):
    """CELAH YANG MASIH TERBUKA — didokumentasikan, sengaja BELUM diperbaiki.

    `videos.duration_secs` merekam durasi AKTUAL, tapi tak ada satu pun kolom/metadata yang merekam
    **TARGET** (preset) yang dituju video itu. `run_metadata` hanya memuat
    {ai_usage, cost, mode, scheduled, video_title} — diperiksa langsung ke DB live 05-Agu.

    Akibatnya presisi durasi tetap **tak bisa diaudit secara historis**: `channels.duration_preset`
    adalah nilai SEKARANG, dan bila owner menggesernya, seluruh video lama seolah menyimpang.
    Itu sudah nyaris membuat saya salah lapor (selisih +15,9s di RAD The Explorer yang ternyata
    artefak perbandingan, bukan cacat produksi).

    Menambah kolom/metadata baru = menyentuh skema & jalur produksi ⇒ butuh ketok owner (§2.3d).
    Uji ini menjaga agar celahnya tetap TERCATAT, bukan menuntutnya ditutup sekarang."""

    def test_celah_target_durasi_terdokumentasi(self):
        s = open(os.path.join(AKAR, "SISA_KERJA_GO_LIVE.md"), encoding="utf-8").read()
        self.assertIn("TARGET durasi per-video", s,
                      "celah 'target durasi per-video belum terekam' hilang dari backlog — "
                      "audit presisi durasi historis akan terus mustahil tanpa ada yang tahu sebabnya")


if __name__ == "__main__":
    unittest.main(verbosity=2)
