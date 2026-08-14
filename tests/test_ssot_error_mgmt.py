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


# ── [12-Agu] TABEL §4 vs REGISTRY — DUA ARAH ────────────────────────────────────────────────────
#
# KENAPA BLOK INI LAHIR. Owner: *"bukankah hal ini sudah dijaga mesin???"* — penjaganya ADA, dan
# hijau, tapi **tabel §4 tak pernah masuk daftar periksanya.** Akibatnya dokumen bisa MENYATAKAN
# jatah gratis harian sebagai "kredit habis" sementara mesin menggolongkannya pulih-sendiri, dan
# tak satu pun alarm berbunyi. Lebih buruk: Claude membaca hijau itu lalu melapor "dokumen sudah
# sejalan dengan kode" — mempercayai alarm untuk sesuatu yang tidak diukurnya.
#
# Cacat bentuknya: penjaga versi lama memeriksa **satu arah** — "apa yang disebut dokumen memang
# ada?" — tapi tidak pernah sebaliknya: "apa yang ADA sudah disebut dokumen?" Karena itu segala
# yang BARU (penyedia baru, penjaga baru) bisa hilang dari dokumen tanpa jejak. Blok ini menjaga
# KEDUA arah, dan hanya mungkin sejak pemetaan menjadi DATA di satu tempat.

from src.providers import galat_registry as _reg  # noqa: E402


def _bagian_penyedia() -> str:
    """Isi §4 saja (tabel penyedia)."""
    return _bagian("## §4 REGISTRY", "## §5 ")


class TestTabelPenyediaSelarasRegistry(unittest.TestCase):

    def _rows(self) -> str:
        return _baris_tabel(_bagian_penyedia())

    def test_setiap_penyedia_registry_ada_di_tabel(self):
        rows = self._rows()
        hilang = [n for n, s in _reg.PENYEDIA.items()
                  if "alias" not in s and f"`{n}`" not in rows]
        self.assertFalse(
            hilang,
            f"penyedia sudah dipetakan di kode tapi TIDAK ADA di tabel §4: {hilang}. Dokumen jadi "
            f"peta yang bolong — pembacanya akan menyimpulkan penyedia itu belum tertangani.")

    def test_tak_ada_penyedia_hantu_di_tabel(self):
        rows = self._rows()
        disebut = set(re.findall(r"^\|\s*`([a-z0-9_]+)`", rows, re.M))
        hantu = sorted(disebut - set(_reg.PENYEDIA))
        self.assertFalse(hantu, f"tabel §4 menyebut penyedia yang TIDAK ADA di registry: {hantu}")

    def test_sumber_dan_tanggal_baca_cocok(self):
        """Aturan Emas §1 menuntut tiap pemetaan membawa tautan + tanggal. Kalau angkanya beda antara
        dokumen dan data, salah satunya bohong — dan pembaca tak tahu yang mana."""
        rows = self._rows()
        for nama, spek in _reg.PENYEDIA.items():
            if "alias" in spek:
                continue
            baris = [b for b in rows.split("\n") if f"`{nama}`" in b]
            self.assertTrue(baris, f"{nama}: barisnya tak ditemukan di §4")
            b = baris[0]
            with self.subTest(nama):
                self.assertIn(spek.get("dibaca", "—"), b,
                              f"{nama}: tanggal baca dokumen di §4 tak cocok dengan registry")
                if spek.get("sumber"):
                    self.assertIn(spek["sumber"], b,
                                  f"{nama}: tautan sumber di §4 tak cocok dengan registry")
                else:
                    self.assertIn("TIDAK ADA dokumen resmi", b,
                                  f"{nama}: tanpa dokumen resmi, tapi §4 tidak mengakuinya terang")

    def test_rincian_kode_tidak_disalin_ke_dokumen(self):
        """Salinan itulah yang melenceng. §4 wajib MENUNJUK registry, bukan menyalin pemetaannya."""
        bagian = _bagian_penyedia()
        self.assertIn("galat_registry.py", bagian,
                      "§4 tidak menunjuk sumber tunggalnya — pembaca akan menyalin ulang & melenceng lagi")


class TestPenjagaNyataDisebutDokumen(unittest.TestCase):
    """ARAH SEBALIKNYA. Penjaga versi lama hanya memastikan berkas yang DIRUJUK dokumen ada; penjaga
    yang BARU dibuat bisa tak pernah disebut. Nyata: tiga penjaga hidup, dokumen menyebut satu."""

    def test_semua_penjaga_topik_ini_disebut(self):
        t = _teks()
        akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        penanda = ("galat_registry", "classify_visual_error", "_classify_openai_compat_error",
                   "_classify_el_error", "classify_cloudflare_error")
        hilang = []
        for nama in sorted(os.listdir(os.path.join(akar, "tests"))):
            if not (nama.startswith("test_") and nama.endswith(".py")):
                continue
            isi = open(os.path.join(akar, "tests", nama), encoding="utf-8", errors="ignore").read()
            if any(k in isi for k in penanda) and f"tests/{nama}" not in t:
                hilang.append(f"tests/{nama}")
        self.assertFalse(
            hilang,
            f"penjaga HIDUP untuk topik ini tidak disebut dokumen: {hilang}.\nSesi berikutnya akan "
            f"menyangka topik ini kurang terjaga, lalu membangun penjaga kembar — atau lebih buruk, "
            f"menganggap dokumen sudah lengkap padahal bolong.")



# ── [14-Agu] TIGA PENJAGA BARU — menutup apa yang lolos pada insiden 13/14-Agu ──────────────────
#
# Penjaga di atas semuanya HIJAU sementara dokumen ini menyatakan perilaku yang TIDAK ADA di mesin:
# §1 & §3 berjanji "toleransi normal → rem menyala di kegagalan ke-3", padahal sejak 12-Agu dua kelas
# dikecualikan dari hitungan sehingga rem TIDAK PERNAH menyala. Dua tenant dibanjiri 53 kabar gagal.
#
# Yang tak terjaga, dan sekarang dijaga:
#   (a) kolom "Sikap" §1 — kalimat PERILAKU, tak pernah dibandingkan dengan perilaku sebenarnya
#   (b) struktur tabel — blok catatan disisipkan di antara baris judul & pemisah §9a, tabelnya rusak
#   (c) angka bukti §7 — tertulis 12 & 9, nyatanya 35 & 14; "rate_limit 3×", nyatanya 53×


def _kolom_tabel(baris: str) -> list[str]:
    """Pecah satu baris tabel Markdown menjadi kolom-kolomnya."""
    return [k.strip() for k in baris.strip().strip("|").split("|")]


class _GudangUji:
    """Buku besar run palsu — sekecil mungkin, hanya untuk mengukur PERILAKU hitungan."""

    def __init__(self, kelas, n=3):
        self.runs = [{"status": "failed", "error_class": kelas, "error_message": "x",
                      "created_at": f"2026-08-14T12:0{i}:00+00:00"} for i in range(n)]

    def table(self, _n):
        gudang = self

        class Q:
            def select(self, *_a, **_k):
                return self

            def eq(self, *_a):
                return self

            def gt(self, *_a):
                return self

            def order(self, *_a, **_k):
                return self

            def limit(self, _n2):
                return self

            def execute(self):
                class R:
                    data = gudang.runs
                    count = None
                return R()
        return Q()


def _streak_untuk(kelas: str) -> int:
    from unittest.mock import patch as _patch
    from src.orchestrator import inventory
    with _patch("src.orchestrator.inventory._sb", return_value=_GudangUji(kelas)):
        return inventory.recent_nonready_streak("CH")


class TestSikapDokumenAdalahPerilakuNyata(unittest.TestCase):
    """⛔ Kolom "Sikap" §1 adalah JANJI PERILAKU. Uji ini membandingkannya dengan mesin.

    Inilah penjaga yang absen 12–14 Agu. Dokumen berkata dua kelas mendapat "toleransi normal"
    (= rem menyala setelah 3 kegagalan) sementara mesin tidak menghitungnya sama sekali. Tak satu
    pun dari 880 uji membandingkan kalimat itu dengan kenyataan.
    """

    def _baris_kelas(self) -> dict[str, list[str]]:
        hasil = {}
        for b in _baris_tabel(_bagian("## §1", "## §2")).splitlines():
            kol = _kolom_tabel(b)
            if len(kol) >= 3:
                m = re.match(r"`([A-Z][A-Z_]+)`", kol[0])
                if m:
                    hasil[m.group(1)] = kol
        return hasil

    def test_semua_kelas_terbaca_dari_tabel(self):
        self.assertEqual(set(self._baris_kelas()), {k.name for k in ErrorClass},
                         "format tabel §1 berubah sehingga kolom Sikap tak lagi bisa dibaca mesin — "
                         "penjaga ini jadi tidur tanpa memberi tahu siapa pun")

    def test_kelas_bersikap_REM_SEGERA_memang_fast_fail(self):
        for nama, kol in self._baris_kelas().items():
            sikap = kol[2]
            with self.subTest(nama):
                if "REM SEGERA" in sikap.upper():
                    self.assertIn(ErrorClass[nama], FAST_FAIL,
                                  f"§1 menjanjikan REM SEGERA untuk {nama}, tapi kode tidak")
                else:
                    self.assertNotIn(ErrorClass[nama], FAST_FAIL,
                                     f"kode merem SEGERA untuk {nama}, tapi §1 tidak mengatakannya")

    def test_kelas_bertoleransi_normal_BENAR_BENAR_dihitung(self):
        """Uji PERILAKU, bukan pembacaan teks.

        "toleransi normal" hanya bermakna bila kegagalannya memang menambah hitungan. Bila ada yang
        mengecualikan sebuah kelas lagi (percobaan 12-Agu), uji ini merah — dan pesannya menyebut
        harga yang sudah dibayar.
        """
        acuan = _streak_untuk(ErrorClass.AUTH_INVALID.value)
        self.assertEqual(acuan, 3, "acuan hitungan sendiri sudah tidak benar")
        for nama, kol in self._baris_kelas().items():
            if "toleransi normal" not in kol[2].lower():
                continue
            with self.subTest(nama):
                self.assertEqual(
                    _streak_untuk(ErrorClass[nama].value), acuan,
                    f"§1 menjanjikan '{nama}: toleransi normal' (rem menyala di kegagalan ke-3), "
                    f"tapi mesin tidak menghitungnya ⇒ rem TIDAK PERNAH menyala untuk sebab ini. "
                    f"Itu kerusakan 13/14-Agu: 30 & 23 kegagalan beruntun, ±257 kabar gagal/jam, "
                    f"dua tenant mematikan channelnya sendiri.")

    def test_sikap_di_alur_bagian3_masih_menyebut_ambangnya(self):
        """§3 butir 6 menuliskan ambang rem sebagai angka. Bila kode & dokumen berbeda, salah satu
        berbohong kepada pembacanya."""
        sec = _bagian("## §3", "## §4")
        m = re.search(r"PRODUCER_FAIL_STREAK_STOP`?\((\d+)\)", sec)
        self.assertIsNotNone(m, "§3 tak lagi menyebut ambang rem — pembaca kehilangan angkanya")
        bawaan = int(os.getenv("PRODUCER_FAIL_STREAK_STOP", "3"))
        self.assertEqual(int(m.group(1)), bawaan,
                         f"§3 menyebut ambang {m.group(1)}, bawaan kode {bawaan}")


class TestStrukturTabelDokumenUtuh(unittest.TestCase):
    """⛔ Tabel yang terbelah tidak ter-render sebagai tabel — isinya hilang dari mata pembaca.

    Nyata: catatan 12-Agu disisipkan tepat antara baris JUDUL tabel §9a dan baris pemisahnya,
    sehingga seluruh tabel jalur pemulihan berhenti tampil sebagai tabel. Lolos dari semua penjaga
    karena tak satu pun memeriksa BENTUK dokumen — hanya isinya.
    """

    @staticmethod
    def _pemisah(b: str) -> bool:
        return bool(re.match(r"^\|[\s:\-|]+\|?\s*$", b))

    def test_setiap_tabel_punya_baris_pemisah_tepat_di_bawah_judulnya(self):
        baris = _teks().split("\n")
        rusak = []
        for i, b in enumerate(baris):
            if not b.startswith("|") or self._pemisah(b):
                continue
            sebelum = baris[i - 1] if i else ""
            if sebelum.startswith("|"):
                continue                      # bukan baris judul
            sesudah = baris[i + 1] if i + 1 < len(baris) else ""
            if not self._pemisah(sesudah):
                rusak.append(f"baris {i + 1}: {b[:60]}")
        self.assertFalse(
            rusak,
            "tabel Markdown terbelah — judulnya tak langsung diikuti baris pemisah, jadi tabelnya "
            f"tidak ter-render:\n  " + "\n  ".join(rusak))


class TestAngkaBuktiUjiTidakBasi(unittest.TestCase):
    """⛔ Angka bukti yang basi = dokumen yang meyakinkan tapi salah.

    §7 menulis jumlah uji per berkas. Angka itu tak pernah dijaga: tertulis 12 & 9 sementara nyatanya
    35 & 14. Pembaca (termasuk sesi Claude berikutnya) memakainya untuk menilai seberapa terjaga
    sebuah topik — dan menilai terlalu rendah sama menyesatkannya dengan terlalu tinggi.
    """

    @staticmethod
    def _jumlah_nyata(modul: str) -> int:
        return unittest.TestLoader().loadTestsFromName(f"tests.{modul}").countTestCases()

    def test_angka_di_tabel_bagian7_sama_dengan_jumlah_nyata(self):
        salah = []
        for b in _baris_tabel(_bagian("## §7", "## §8")).splitlines():
            kol = _kolom_tabel(b)
            if len(kol) < 2:
                continue
            berkas = re.findall(r"tests/(test_[a-z0-9_]+)\.py", kol[0])
            angka = re.fullmatch(r"\**(\d+)\**", kol[1].strip())
            if len(berkas) != 1 or not angka:
                continue                     # baris tanpa angka ("—") atau baris gabungan → dilewati
            nyata = self._jumlah_nyata(berkas[0])
            if int(angka.group(1)) != nyata:
                salah.append(f"{berkas[0]}: dokumen {angka.group(1)}, nyata {nyata}")
        self.assertFalse(salah, "angka bukti §7 sudah basi:\n  " + "\n  ".join(salah))


if __name__ == "__main__":
    unittest.main(verbosity=2)
