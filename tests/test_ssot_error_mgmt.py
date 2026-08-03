"""
PENJAGA ANTI-DRIFT — `AI_ERROR_MANAGEMENT_ARCHITECTURE.md` vs KODE.

Jalankan:  python -m unittest tests.test_ssot_error_mgmt

KENAPA ADA
Audit 2026-08-03 menemukan dokumen SSOT itu menyimpang dari kode di EMPAT tempat sekaligus:
  1. kelas `MODEL_UNAVAILABLE` ada di kode tapi HILANG dari tabel taksonomi §1
  2. §1 menyatakan FAST_FAIL berisi 3 kelas — kode punya 4 (perilaku rem yang salah didokumentasikan)
  3. §7 menyandarkan bukti pada `tests/test_errmgmt.py` yang TIDAK ADA di repo
  4. seluruh anchor `file:baris` sudah basi dan menyesatkan pembacanya

Dokumen yang salah lebih berbahaya daripada tidak ada dokumen: orang mengambil keputusan dari situ.
Janji "akan dijaga" sudah terbukti tidak cukup — maka dijaga MESIN. Bila kode dan dokumen bergeser
tanpa satu sama lain, berkas ini MERAH sebelum ada yang tersesat.

Uji ini sengaja membaca dokumen sebagai TEKS: ia menjaga apa yang MANUSIA baca, bukan apa yang
kebetulan benar di kode.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import FAST_FAIL, ErrorClass  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOK = os.path.join(AKAR, "AI_ERROR_MANAGEMENT_ARCHITECTURE.md")


def _teks() -> str:
    with open(DOK, encoding="utf-8") as f:
        return f.read()


def _bagian(nama_awal: str, nama_akhir: str | None = None) -> str:
    """Potong satu bagian dokumen berdasar judul '## §n …'."""
    t = _teks()
    i = t.index(nama_awal)
    j = t.index(nama_akhir, i) if nama_akhir else len(t)
    return t[i:j]


def _baris_tabel(bagian: str) -> str:
    """HANYA baris tabel Markdown.

    Penting, dan pernah membuat penjaga ini bocor: memeriksa 'disebut di mana pun dalam bagian'
    TIDAK cukup. Saat `MODEL_UNAVAILABLE` dihapus dari tabel §1, namanya masih muncul di baris
    `FAST_FAIL = {...}` pada bagian yang sama → uji tetap hijau padahal tabelnya sudah bolong.
    Yang dijaga adalah BARIS TABEL — di situlah manusia membaca daftar kelasnya.
    """
    return "\n".join(b for b in bagian.splitlines() if b.strip().startswith("|"))


class TestTaksonomiSelarasKode(unittest.TestCase):
    """Setiap kelas di kode WAJIB punya barisnya di tabel §1 — dan sebaliknya."""

    def test_setiap_kelas_kode_ada_di_dokumen(self):
        tabel = _baris_tabel(_bagian("## §1", "## §2"))
        for kelas in ErrorClass:
            self.assertIn(
                f"`{kelas.name}`", tabel,
                f"Kelas {kelas.name} ada di src/exceptions.py tapi TIDAK ada di tabel §1 — "
                f"pembaca dokumen akan mengira kelas itu tak ada.")

    def test_tak_ada_kelas_hantu_di_dokumen(self):
        sec = _baris_tabel(_bagian("## §1", "## §2"))
        nyata = {k.name for k in ErrorClass}
        # Nama kelas ditulis dalam backtick HURUF BESAR di tabel §1.
        disebut = set(re.findall(r"`([A-Z][A-Z_]{4,})`", sec)) - {"FAST_FAIL"}
        hantu = disebut - nyata
        self.assertFalse(hantu, f"Dokumen §1 menyebut kelas yang TIDAK ADA di kode: {sorted(hantu)}")

    def test_jumlah_kelas_disebut_benar(self):
        sec = _bagian("## §1", "## §2")
        m = re.search(r"\*\*(\w+) kelas\*\*", sec)
        self.assertIsNotNone(m, "§1 tak lagi menyebut jumlah kelas — kalimatnya berubah?")
        ejaan = {3: "TIGA", 4: "EMPAT", 5: "LIMA", 6: "ENAM", 7: "TUJUH", 8: "DELAPAN", 9: "SEMBILAN"}
        self.assertEqual(m.group(1).upper(), ejaan.get(len(ErrorClass)),
                         f"§1 menyebut '{m.group(1)} kelas' padahal kode punya {len(ErrorClass)}")


class TestFastFailSelarasKode(unittest.TestCase):
    """Daftar FAST_FAIL = klaim PERILAKU REM. Salah di sini = salah menjelaskan mesin."""

    def test_daftar_fast_fail_sama_persis(self):
        sec = _bagian("## §1", "## §2")
        m = re.search(r"`FAST_FAIL = \{([^}]*)\}`", sec)
        self.assertIsNotNone(m, "Baris FAST_FAIL tak ditemukan di §1 — formatnya berubah?")
        di_dok = {x.strip() for x in m.group(1).split(",") if x.strip()}
        di_kode = {k.name for k in FAST_FAIL}
        self.assertEqual(di_dok, di_kode,
                         f"FAST_FAIL menyimpang.\n  dokumen: {sorted(di_dok)}\n  kode   : {sorted(di_kode)}")


class TestBuktiUjiBenarBenarAda(unittest.TestCase):
    """§7 tak boleh menyandarkan bukti pada berkas yang tidak eksis (kesalahan lama)."""

    def test_berkas_uji_yang_dirujuk_ada_semua(self):
        # HANYA baris TABEL yang diperiksa — di situlah berkas DIKLAIM sebagai bukti. Prosa di
        # sekitarnya justru perlu bebas menyebut berkas yang hilang (itu catatan koreksinya).
        hilang = [b for b in set(re.findall(r"tests/(test_[a-z0-9_]+)\.py",
                                            _baris_tabel(_bagian("## §7", "## §8"))))
                  if not os.path.isfile(os.path.join(AKAR, "tests", f"{b}.py"))]
        self.assertFalse(hilang, f"§7 mengklaim bukti dari berkas uji yang TIDAK ADA: {sorted(hilang)}")

    def test_berkas_ini_sendiri_terdaftar(self):
        self.assertIn("test_ssot_error_mgmt", _bagian("## §7", "## §8"),
                      "Penjaga anti-drift tak terdaftar di §7 — pembaca tak tahu ia dijaga mesin.")


class TestKontrakTampilanLengkap(unittest.TestCase):
    """Kelas tanpa kontrak tampilan = tenant melihat pesan kosong saat kelas itu muncul."""

    def test_setiap_kelas_punya_anjuran(self):
        tabel = _baris_tabel(_bagian("## §9", "## §10"))
        for kelas in ErrorClass:
            self.assertIn(f"`{kelas.name}`", tabel,
                          f"Kelas {kelas.name} tak punya baris kontrak tampilan di §9 — "
                          f"saat kelas ini terjadi, tenant tak tahu harus berbuat apa.")

    def test_larangan_menyebut_penyedia_ditegaskan(self):
        sec = _bagian("## §9", "## §10")
        self.assertIn("TIDAK PERNAH per nama penyedia", sec,
                      "Aturan general (arahan owner) hilang dari §9.")


class TestTakAdaAnchorBarisBasi(unittest.TestCase):
    """Nomor baris selalu basi. Aturan §3: rujuk nama simbol, bukan baris."""

    def test_tak_ada_anchor_file_baris(self):
        """Dua bentuk anchor, keduanya basi: `berkas.py:123` DAN `` `:123` `` telanjang.

        Bentuk kedua sempat lolos dari penjaga versi pertama — §3 menulis "scheduled `:206`"
        tanpa nama berkas, jadi pola yang menuntut `.py:` tidak mencocokkannya. Angkanya
        memang sudah basi (nyata 137/397/491). Pelajaran yang sama, kedua kalinya di berkas
        ini: pola yang terlalu sempit = penjaga yang tidur.
        """
        t = _teks()
        t = re.sub(r"> ⚠️ \*\*Anchor baris SENGAJA DIHAPUS.*?\n\n", "", t, flags=re.S)
        t = re.sub(r"## §11 CHANGELOG.*", "", t, flags=re.S)   # changelog = catatan sejarah, boleh
        sisa = re.findall(r"[\w/]+\.py:~?\d+", t) + re.findall(r"`:~?\d+`", t)
        self.assertFalse(sisa, f"Anchor baris muncul lagi (selalu basi, menyesatkan): {sisa}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
