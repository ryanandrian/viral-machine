"""PEMBERITAHUAN WAJIB BISA DITINDAK — nol kode mesin, nol istilah teknis, nol pemotongan senyap.

KENAPA BERKAS INI ADA (ketok owner 2026-08-12, dari dua pesan yang ia terima sendiri)

  1. "🔥 Lead PANAS (trial-lapse) tenant c37d2ee3-… — layak outreach personal (nurture step 3)."
     Owner: *"isinya hanya anda dan Tuhan yang mengerti"*. Sebuah kode mesin + tiga istilah Inggris,
     tanpa nama, tanpa kontak, tanpa tautan. Padahal SEMUA bahannya ada di tangan pada titik itu.

  2. "✅ [RAD The Explorer] Video Published!" — hanya judul, niche, tautan, lalu satu kode mentah.
     Owner: *"mengapa pesan published tidak selengkap pesan video uji? dan di bawah url ada kode
     yang tidak dipahami siapapun."* Sebabnya bukan pilihan redaksi: pesan uji dikirim DI DALAM
     mesin produksi (angka masih di tangan), pesan terbit dikirim JAUH KEMUDIAN oleh penerbit yang
     dulu hanya diberi tautan/judul/niche — padahal angkanya sudah ada di metadata item itu.

  3. "⏰ Runtime: 0m 0s" pada video uji — SELALU nol. Bukan salah hitung, salah URUTAN: notifikasi
     membaca `result["elapsed_seconds"]` di pipeline baris ~689, sementara angka itu baru ditulis
     ±70 baris di bawah. Yang terbaca selalu nilai bawaan.

  4. Pesan ke OWNER dikirim sebagai HTML tanpa membersihkan nilai yang diselipkan. Bila teks galat
     memuat `<`/`>`/`&` — sangat mungkin pada galat penyimpanan yang balasannya XML — Telegram
     MENOLAK seluruh pesannya dan owner tidak menerima apa pun. Justru alarm terpenting (penyimpanan
     mati = semua channel berhenti) yang paling berisiko hilang. Jalur ke TENANT sudah bersih sejak
     lama; jalur ke OWNER belum. (Bahaya ini belum pernah terjadi — nol pesan ditolak sepanjang log.)
"""
import inspect
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.telegram_notifier import TelegramNotifier  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTIFIER = os.path.join(AKAR, "src", "utils", "telegram_notifier.py")

# UUID = bentuk kode mesin yang paling sering bocor ke mata manusia.
_RX_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _teks(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def _tangkap(fn, *a, **kw) -> str:
    """Jalankan pembuat pesan, tangkap TEKS yang akan dikirim (tanpa menyentuh jaringan)."""
    ditangkap = {}

    def _stub(_self, chat_id, text):
        ditangkap["text"] = text
        return True

    with patch.object(TelegramNotifier, "_send", _stub):
        fn(*a, **kw)
    return ditangkap.get("text", "")


# ── 1. Pesan ke TENANT: nol kode mesin ──────────────────────────────────────────────────────────

class TestNolKodeMesinKeTenant(unittest.TestCase):

    def test_pesan_video_terbit_tak_memuat_kode_mesin(self):
        n = TelegramNotifier()
        with patch.object(TelegramNotifier, "_chat_id_for_tenant", lambda *_: "123"):
            teks = _tangkap(n.notify_published, tenant_id="a410251c-cb09-492f-8342-0d829cd7de60",
                            url="https://youtube.com/shorts/x", title="Judul", niche="fun_facts",
                            channel_name="RAD The Explorer", duration_secs=54.5, size_mb=24.7,
                            clips=5, hook_score=79.8, words=147)
        self.assertFalse(_RX_UUID.search(teks),
                         f"kode mesin bocor ke mata tenant:\n{teks}")
        self.assertNotIn("_1785670573", teks, "nomor run mentah masih dicetak")

    def test_pesan_video_terbit_SELENGKAP_pesan_uji(self):
        """Inti keluhan owner. Angka-angka ini SUDAH ADA di metadata item — hanya belum diserahkan."""
        n = TelegramNotifier()
        with patch.object(TelegramNotifier, "_chat_id_for_tenant", lambda *_: "123"):
            teks = _tangkap(n.notify_published, tenant_id="t", url="https://x",
                            title="Judul", niche="fun_facts", channel_name="RAD",
                            duration_secs=54.5, size_mb=24.7, clips=5, hook_score=79.8, words=147)
        for wajib, apa in (("0:54", "durasi"), ("24.7", "ukuran berkas"), ("5 adegan", "jumlah adegan"),
                           ("147 kata", "jumlah kata"), ("80/100", "skor daya-tarik")):
            self.assertIn(wajib, teks, f"{apa} tidak muncul di pesan video terbit:\n{teks}")

    def test_angka_yang_TIDAK_ADA_tak_memaksa_baris_kosong(self):
        """Baris lama (metadata tak lengkap) tetap aman — tak ada '⏱ Durasi: None'."""
        n = TelegramNotifier()
        with patch.object(TelegramNotifier, "_chat_id_for_tenant", lambda *_: "123"):
            teks = _tangkap(n.notify_published, tenant_id="t", url="https://x", title="Judul")
        self.assertNotIn("None", teks, f"nilai kosong bocor sebagai 'None':\n{teks}")
        self.assertIn("Video terbit", teks)


# ── 2. Nol istilah teknis pada teks yang dibaca manusia ─────────────────────────────────────────

class TestNolIstilahTeknis(unittest.TestCase):
    """§4.1 — owner & tenant non-teknis. Istilah ini pernah nyata muncul di pesan mereka."""

    TERLARANG = ("Hook score", "Video Published", "Runtime:", "Pipeline GAGAL",
                 "trial-lapse", "outreach", "nurture step")

    def test_tak_ada_istilah_terlarang_di_teks_pesan(self):
        """Diperiksa lewat POHON SINTAKS, bukan pencarian teks per baris.

        Alat ukur versi pertama memakai pencarian per baris dan langsung salah menuduh: ia menandai
        KUTIPAN pesan lama yang sengaja ditulis di dalam dokumentasi fungsi sebagai pelanggaran.
        Padahal kutipan sejarah itu justru yang membuat perbaikan bisa dipahami sesi berikutnya.
        Pelajaran yang sama seperti di berkas-berkas penjaga lain: pola yang terlalu kasar =
        penjaga yang menuduh, dan penjaga yang menuduh akhirnya dimatikan orang.
        """
        import ast
        langgar = []
        for path in (NOTIFIER, os.path.join(AKAR, "src", "billing", "renewal.py")):
            pohon = ast.parse(_teks(path))
            # Kumpulkan simpul dokumentasi (docstring) supaya TIDAK ikut diperiksa.
            doc_ids = set()
            for n in ast.walk(pohon):
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    d = n.body[0] if n.body else None
                    if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant) \
                            and isinstance(d.value.value, str):
                        doc_ids.add(id(d.value))
            for n in ast.walk(pohon):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids:
                    for t in self.TERLARANG:
                        if t in n.value:
                            langgar.append(f"{os.path.basename(path)}:{n.lineno}: {t!r} → "
                                           f"{n.value[:70]}")
        self.assertFalse(langgar, "istilah teknis muncul di teks yang dibaca manusia:\n  "
                         + "\n  ".join(langgar))


# ── 3. Runtime tak boleh nol: angka diisi SEBELUM dikirim ───────────────────────────────────────

class TestLamaProduksiTerisi(unittest.TestCase):

    def test_elapsed_diisi_sebelum_notifikasi_dikirim(self):
        """Urutan-lah yang dulu salah, bukan hitungannya. Dijaga sebagai URUTAN, bukan sebagai nilai."""
        src = _teks(os.path.join(AKAR, "src", "orchestrator", "pipeline.py"))
        i_isi = src.find('result["elapsed_seconds"] = round(time.time() - start_time, 1)')
        i_kirim = src.find("self.telegram.notify_success(result")
        self.assertGreater(i_isi, -1, "pengisian lama-produksi sebelum notifikasi HILANG")
        self.assertGreater(i_kirim, -1, "pemanggilan notifikasi sukses tak ditemukan")
        self.assertLess(i_isi, i_kirim,
                        "lama produksi diisi SETELAH notifikasi dikirim → pesan kembali '0m 0s'")

    def test_format_waktu_nol_tetap_jujur(self):
        """Bila memang nol (mustahil kini), jangan mengarang angka."""
        self.assertIn("0", TelegramNotifier._fmt_elapsed(0))


# ── 4. Pesan ke OWNER: nilai wajib dibersihkan ──────────────────────────────────────────────────

class TestNilaiPesanOwnerDibersihkan(unittest.TestCase):

    def test_helper_membersihkan_tanda_html(self):
        h = TelegramNotifier.aman('<Error><Code>AccessDenied</Code> & habis')
        for mentah in ("<Error>", "<Code>"):
            self.assertNotIn(mentah, h, "tanda HTML mentah lolos — Telegram akan MENOLAK pesannya "
                                        "dan owner tidak menerima apa pun")
        self.assertIn("&lt;", h)

    def test_alarm_penyimpanan_membersihkan_galatnya(self):
        src = _teks(os.path.join(AKAR, "src", "orchestrator", "buffer_janitor.py"))
        self.assertIn("TelegramNotifier.aman(e)", src,
                      "alarm penyimpanan menyelipkan teks galat mentah — balasan S3 berbentuk XML, "
                      "jadi alarm TERPENTING justru yang paling mungkin hilang")

    def test_alarm_komisi_membersihkan_galatnya(self):
        src = _teks(os.path.join(AKAR, "src", "billing", "midtrans.py"))
        self.assertGreaterEqual(src.count("TelegramNotifier.aman("), 4,
                                "alarm komisi (menyangkut UANG) masih menyelipkan nilai mentah")


# ── 5. Pesan calon pelanggan: bisa langsung dipakai menghubungi ─────────────────────────────────

class TestPesanCalonPelanggan(unittest.TestCase):

    def _kirim(self):
        from src.billing import renewal
        ditangkap = {}

        class _Q:
            def select(self, *_a, **_k): return self
            def eq(self, *_a, **_k): return self
            def limit(self, *_a, **_k): return self
            def execute(self): return type("R", (), {"data": [{"channel_name": "BJ Yusroon"}]})()

        class _SB:
            def table(self, _n): return _Q()

        with patch("src.utils.email.tenant_email", lambda *_a, **_k: "m.yusroon@gmail.com"), \
             patch.object(TelegramNotifier, "notify_admin",
                          lambda _self, text: ditangkap.setdefault("t", text) or True):
            renewal._kabari_owner_lead_panas(
                _SB(), "c37d2ee3-42e8-49bf-aa62-be4b52ad57ef",
                {"display_handle": "m.yusroon"}, 3, 9)
        return ditangkap.get("t", "")

    def test_memuat_yang_dibutuhkan_untuk_menghubungi(self):
        teks = self._kirim()
        for wajib, apa in (("m.yusroon", "nama"), ("m.yusroon@gmail.com", "email"),
                           ("BJ Yusroon", "nama channel"), ("9 hari", "umur sejak masa coba habis"),
                           ("memproduksi video", "alasan kenapa panas"),
                           ("admin/tenants", "tautan tindak lanjut")):
            self.assertIn(wajib, teks, f"{apa} tidak ada di pesan:\n{teks}")

    def test_TIDAK_memuat_kode_mesin(self):
        teks = self._kirim()
        self.assertFalse(_RX_UUID.search(teks),
                         f"kode tenant mentah masih dikirim ke owner:\n{teks}")


# ── 6. Nol pemotongan senyap ────────────────────────────────────────────────────────────────────

class TestNolPemotonganSenyap(unittest.TestCase):
    """Ketokan owner 06-Agu: jangan pasang batas panjang pesan; bila memang harus dipendekkan,
    UMUMKAN potongannya. `notify_failure` masih memotong senyap di 250 huruf sampai 12-Agu."""

    def test_tak_ada_potong_senyap_di_notifier(self):
        langgar = []
        for i, baris in enumerate(_teks(NOTIFIER).split("\n"), 1):
            s = baris.strip()
            if s.startswith("#"):
                continue
            if re.search(r"str\((?:error|e|_pe)\)\[:\s*\d+\s*\]", s):
                langgar.append(f"baris {i}: {s[:80]}")
        self.assertFalse(langgar, "pemotongan senyap kembali:\n  " + "\n  ".join(langgar))

    def test_dua_jalur_kegagalan_memakai_pemendek_yang_mengumumkan(self):
        src = _teks(NOTIFIER)
        self.assertGreaterEqual(src.count("ringkas_diumumkan("), 3,
                                "jalur kegagalan tak semuanya memakai pemendek yang mengumumkan")


# ── 6. Kegagalan TERBIT: tenant dapat MAKNA, kami dapat KODE ────────────────────────────────────
#
# KENAPA BLOK INI LAHIR (13-Agu 2026, pesan yang owner terima sendiri pukul 06:00):
#   "❌ [RAD The Explorer] Publish gagal, akan diulang: download gagal
#    (a410251c-.../410d4538-.../a410251c-..._1786489240.mp4): An error occurred (403) when calling
#    the HeadObject operation: Forbidden"
# Owner: *"pesan errornya tidak jelas hanya kode saja. ANEH"*.
# Tiga cacat sekaligus, dan yang ketiga paling berat: sebabnya adalah **akun penyimpanan KAMI yang
# diblokir karena tagihan belum dibayar** — 100% milik kita — tapi pesannya membiarkan tenant
# mengira dirinyalah yang bermasalah. Jalur kegagalan AI sudah lewat mesin penggolong sejak 11-Agu;
# jalur TERBIT satu-satunya yang belum ikut, dan ini menutupnya.

class TestPesanGagalTerbit(unittest.TestCase):

    PUBLISHER = os.path.join(AKAR, "src", "orchestrator", "publisher.py")

    def test_galat_mentah_tak_pernah_masuk_pesan_tenant(self):
        """Dijaga lewat POHON SINTAKS: cari panggilan `_notify(...)` yang menyisipkan objek galat
        (`{e}`) ke dalam teksnya. Itu bentuk persis cacat 06:00 — dan satu-satunya cara ia lahir
        kembali."""
        import ast
        langgar = []
        pohon = ast.parse(_teks(self.PUBLISHER))
        for n in ast.walk(pohon):
            if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_notify"):
                continue
            for arg in n.args:
                if not isinstance(arg, ast.JoinedStr):
                    continue
                for bagian in arg.values:
                    if isinstance(bagian, ast.FormattedValue) and \
                            getattr(bagian.value, "id", "") in ("e", "error", "exc", "_e"):
                        langgar.append(f"publisher.py:{n.lineno}: galat mentah disisipkan ke pesan tenant")
        self.assertFalse(
            langgar,
            "GALAT MENTAH KEMBALI KE PESAN TENANT:\n  " + "\n  ".join(langgar)
            + "\n\nYang tenant terima jadi seperti 13-Agu 06:00: kode HTTP + nama berkas internal, "
              "untuk kegagalan yang sebenarnya MILIK KITA. Golongkan dulu lewat `galat_registry`.")

    def test_kegagalan_penyimpanan_MENGAKU_milik_kita(self):
        """Kalimat untuk tenant wajib menyebut ini di sisi MesinViral — bukan menggantung."""
        from src.providers.galat_registry import golongkan_penyimpanan
        from botocore.exceptions import ClientError
        p = golongkan_penyimpanan(ClientError({"Error": {"Code": "403", "Message": "Forbidden"}},
                                              "HeadObject"))
        self.assertIsNotNone(p, "galat penyimpanan tak dikenali → jatuh ke jalur galat mentah lagi")
        self.assertTrue(p.milik_kita, "kegagalan penyimpanan KAMI ditandai bukan milik kita")
        self.assertIn("MesinViral", p.pesan_tenant,
                      "pesan tidak mengaku ini di sisi kami — tenant akan menyalahkan dirinya")

    def test_pesan_tenant_nol_kode_dan_nol_nama_berkas(self):
        from src.providers.galat_registry import golongkan_penyimpanan
        from botocore.exceptions import ClientError
        from src.utils.s3_buffer import BufferError
        try:
            try:
                raise ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject")
            except Exception as dalam:
                raise BufferError("download gagal (a410251c-cb09-492f-8342/410d4538/x_1786489240.mp4): "
                                  f"{dalam}") from dalam
        except Exception as e:
            pesan = golongkan_penyimpanan(e).pesan_tenant
        for terlarang in ("403", "HeadObject", "Forbidden", "An error occurred", ".mp4",
                          "download gagal"):
            self.assertNotIn(terlarang, pesan, f"pesan tenant masih memuat {terlarang!r}")
        self.assertFalse(_RX_UUID.search(pesan), "nama berkas/UUID internal bocor ke tenant")

    def test_kode_asli_TETAP_tercatat_untuk_kami(self):
        """Membersihkan pesan tenant TIDAK boleh berarti membuang buktinya. Kode aslinya wajib tetap
        ada di catatan server — di situlah kami mendiagnosa."""
        src = _teks(self.PUBLISHER)
        i = src.find("golongkan_penyimpanan")
        self.assertGreater(i, 0, "penggolong penyimpanan tak dipakai di jalur terbit")
        cuplik = src[max(0, i - 600):i + 900]
        self.assertRegex(cuplik, r"logger\.error\(.*\{e\}|logger\.error\(.*_pen\.kode",
                         "kode galat asli tak lagi tercatat di catatan server")

    def test_berkas_hilang_TIDAK_dijanjikan_terbit_otomatis(self):
        """Berkasnya benar-benar tidak ada ⇒ mengulang dijamin gagal. Menjanjikan 'akan terbit
        otomatis' di keadaan itu = berbohong kepada tenant."""
        from src.providers.galat_registry import golongkan_penyimpanan
        from botocore.exceptions import ClientError
        p = golongkan_penyimpanan(ClientError({"Error": {"Code": "NoSuchKey", "Message": "x"}},
                                              "GetObject"))
        self.assertTrue(p.berkas_hilang)
        self.assertNotIn("akan terbit otomatis", p.pesan_tenant)
        self.assertIn("MesinViral", p.pesan_tenant)


if __name__ == "__main__":
    unittest.main(verbosity=2)
