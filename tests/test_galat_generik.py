"""SATU JALUR UNTUK SELURUH GALAT AI — dan vendor baru tak bisa masuk tanpa dipetakan.

KENAPA BERKAS INI ADA (ketok owner 2026-08-12)
  • *"Pastikan tidak ada jalur lain yang menghandle AI error management kecuali melalui perbaikan
    yang akan anda lakukan."*
  • *"Pastikan setiap penambahan AI vendor / model baru akan menerapkan metode yang sama, konsep
    harus generik untuk seluruh AI error management."*
  • *"Ingat fal.ai itu agregator dan mungkin kedepan akan ada agregator lain seperti blackbox.ai."*

APA YANG DIJAGA — dan kenapa tiap butirnya lahir dari kerusakan NYATA:
  A. NOL jalur kedua. Dulu ada EMPAT penilai tersebar; gejala IDENTIK (jatah gratis harian tenant
     habis) ditangani berbeda-beda: jalur naskah benar, jalur gambar menyuruh tenant "isi ulang
     saldo" untuk jatah yang pulih sendiri tengah malam.
  B. SETIAP penyedia di katalog DB punya barisnya. Vendor yang belum dipetakan = seluruh galatnya
     tak bernama → diulang walau kunci salah, dan tenant tak diberi tahu apa pun yang bisa dikerjakan.
     Terukur: Anthropic & OpenAI TTS NOL penggolongan, Edge TTS (6 channel aktif) hampir nol.
  C. Tiap baris membawa SUMBER + TANGGAL dibaca (§1 Aturan Emas). Vendor tanpa dokumen resmi wajib
     mengaku terang, bukan dikarang.
  D. Gejala BERKALA (jatah harian/periodik) → SELALU pulih-sendiri, penyedia apa pun. Ini invarian
     yang pelanggarannya baru saja dibayar: layar & Telegram sama-sama berkata "TIDAK akan pulih
     sendiri, isi ulang saldo" untuk jatah gratis harian Cloudflare.
  E. Jaring HTTP generik TIDAK boleh menghentikan channel. Vendor yang belum dipetakan harus
     berperilaku waras, bukan berbahaya.
  F. Agregator meneruskan galat vendor di baliknya — dan itu ikut terbaca.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass, FAST_FAIL, SELF_HEALING  # noqa: E402
from src.providers import galat_registry as reg  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(AKAR, "src")

# Berkas yang MEMANG boleh memuat pemetaan penanda→golongan. Hanya satu, plus taksonomi intinya.
_BOLEH_MEMETAKAN = {
    os.path.join(SRC, "providers", "galat_registry.py"),
    os.path.join(SRC, "exceptions.py"),
}
# Pola pemetaan: penanda (string/angka) → ErrorClass. Kebalikannya (`ErrorClass.X: "kalimat"`) = tabel
# ANJURAN per-golongan, dan itu SAH di mana pun karena kalimatnya khas komponen.
_RX_PEMETAAN = re.compile(r"""["']?[\w\- ]+["']?\s*:\s*ErrorClass\.""")


def _py_files():
    for akar, _, berkas in os.walk(SRC):
        for b in berkas:
            if b.endswith(".py"):
                yield os.path.join(akar, b)


# ── A. Nol jalur kedua ──────────────────────────────────────────────────────────────────────────

class TestA_HanyaSatuJalur(unittest.TestCase):

    def test_tak_ada_tabel_pemetaan_di_luar_registry(self):
        langgar = []
        for path in _py_files():
            if path in _BOLEH_MEMETAKAN:
                continue
            for i, baris in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
                s = baris.strip()
                if s.startswith("#") or "ErrorClass." not in s:
                    continue
                # `ErrorClass.X: "..."` = tabel anjuran (sah). `"tok": ErrorClass.X` = pemetaan (haram).
                if s.startswith("ErrorClass."):
                    continue
                if _RX_PEMETAAN.search(s):
                    langgar.append(f"{os.path.relpath(path, AKAR)}:{i}: {s[:88]}")
        self.assertFalse(
            langgar,
            "PEMETAAN GALAT DI LUAR `galat_registry.py` — jalur kedua lahir kembali:\n  "
            + "\n  ".join(langgar)
            + "\n\nAkibat yang sudah terbukti: gejala yang SAMA ditangani berbeda tergantung vendor & "
              "komponen; tenant di satu penyedia dibohongi sementara di penyedia lain tidak. "
              "Pindahkan barisnya ke registry.")

    def test_tabel_lama_tak_dihidupkan_lagi(self):
        for nama in ("_OPENAI_COMPAT_ERROR_MAP", "_EL_ERROR_MAP", "_VISUAL_ERROR_MAP",
                     "_CF_ERROR_MAP", "_GEMINI_ERROR_MAP"):
            for path in _py_files():
                if path in _BOLEH_MEMETAKAN:
                    continue
                isi = open(path, encoding="utf-8", errors="ignore").read()
                self.assertNotRegex(
                    isi, rf"^{nama}\s*[:=]", f"tabel lama '{nama}' hidup lagi di "
                    f"{os.path.relpath(path, AKAR)} — pemetaan wajib satu tempat")


# ── B & C. Katalog penuh + sumber tercatat ──────────────────────────────────────────────────────

class TestB_SetiapPenyediaDipetakan(unittest.TestCase):
    """Diperiksa terhadap katalog DB yang NYATA, bukan daftar hafalan di kode uji."""

    def test_semua_penyedia_katalog_punya_baris(self):
        try:
            import os as _os
            from dotenv import load_dotenv
            load_dotenv(os.path.join(AKAR, ".env"))
            from supabase import create_client
            sb = create_client(_os.getenv("SUPABASE_URL"),
                               _os.getenv("SUPABASE_SERVICE_ROLE_KEY") or _os.getenv("SUPABASE_KEY"))
            baris = sb.table("ai_providers").select("provider_key,is_active").execute().data
        except Exception as e:                                   # noqa: BLE001
            self.skipTest(f"katalog DB tak terbaca di lingkungan ini ({type(e).__name__}) — "
                          f"pemeriksaan ini menuntut DB live")
        aktif = [str(x.get("provider_key")).strip().lower() for x in baris if x.get("is_active")]
        self.assertTrue(aktif, "katalog ai_providers kosong — mustahil, periksa kueri")
        belum = sorted(set(aktif) - reg.penyedia_terpetakan())
        self.assertFalse(
            belum,
            f"PENYEDIA AKTIF DI KATALOG TAPI BELUM DIPETAKAN: {belum}.\n"
            f"Tenant bisa memilihnya dari layar, dan begitu dipilih SELURUH kegagalannya tak bernama: "
            f"diulang walau kunci salah, dan tenant tak diberi tahu apa pun yang bisa dikerjakan. "
            f"Wajib: baca dokumen galat RESMI vendornya, tambahkan barisnya di `galat_registry.PENYEDIA` "
            f"beserta tautan + tanggal (AI_ERROR_MANAGEMENT §1 Aturan Emas + §5 langkah 1).")

    def test_tiap_baris_membawa_sumber_dan_tanggal(self):
        for nama, spek in reg.PENYEDIA.items():
            if "alias" in spek:
                continue
            self.assertIn("dibaca", spek, f"{nama}: tanggal baca dokumen tak dicatat")
            self.assertIn("sumber", spek, f"{nama}: sumber dokumen tak dicatat")
            if not spek["sumber"]:
                # Sah HANYA bila keterbatasannya diakui terang — bukan dikarang.
                self.assertIn("catatan", spek, f"{nama}: tanpa sumber & tanpa catatan = pemetaan karangan")
                self.assertRegex(spek["catatan"], r"TIDAK ADA dokumen|tidak ada dokumen",
                                 f"{nama}: tak ada dokumen resmi, tapi tidak diakui terang di catatan")

    def test_alias_menunjuk_penyedia_yang_ada(self):
        for nama, spek in reg.PENYEDIA.items():
            if "alias" in spek:
                self.assertIn(spek["alias"], reg.PENYEDIA, f"{nama}: alias menunjuk penyedia hantu")


# ── D. Invarian jatah BERKALA ───────────────────────────────────────────────────────────────────

class TestD_JatahBerkalaSelaluPulihSendiri(unittest.TestCase):
    """⛔ INVARIAN YANG PELANGGARANNYA BARU DIBAYAR. Untuk gejala 'jatah berkala habis', layar dan
    Telegram sama-sama berkata "TIDAK akan pulih sendiri · isi ulang saldo" bila golongannya bukan
    pulih-sendiri — padahal jatahnya kembali saat hari berganti dan tak ada yang perlu diisi."""

    KASUS = (
        ("cloudflare · jatah harian 10.000 neuron", "cloudflare", 3036, ""),
        ("gemini · jatah harian", "gemini", "quota_exceeded", ""),
        ("openai · batas pemakaian organisasi", "openai", "organization_usage_limit_exceeded", ""),
        ("groq · tokens per day (sampel nyata ×8)", "groq", None,
         "Rate limit reached ... on tokens per day (TPD): Limit 100000, Used 99988."),
    )

    def test_semua_jatah_berkala_pulih_sendiri(self):
        for judul, penyedia, kode, teks in self.KASUS:
            with self.subTest(judul):
                p = reg.golongkan(penyedia, kode=kode, teks=teks)
                self.assertIn(p.kelas, SELF_HEALING,
                              f"{judul}: golongan {p.kelas.value} membuat tenant dibilangi 'tidak akan "
                              f"pulih sendiri' — padahal pulih saat jatah berganti")
                self.assertNotIn(p.kelas, FAST_FAIL,
                                 f"{judul}: golongan FAST_FAIL disajikan sebagai 'ada yang harus Anda "
                                 f"kerjakan'. Untuk jatah berkala TIDAK ADA yang perlu dikerjakan.")

    def test_saldo_berbayar_TETAP_menuntut_tindakan(self):
        """Pembanding wajib: kalau semuanya dijadikan 'pulih sendiri', tenant yang saldonya benar-benar
        habis akan menunggu selamanya."""
        for penyedia, kode in (("openai", "credit_balance_exhausted"),
                               ("elevenlabs", "insufficient_credits"),
                               ("anthropic", "billing_error")):
            with self.subTest(f"{penyedia}·{kode}"):
                p = reg.golongkan(penyedia, kode=kode)
                self.assertIn(p.kelas, FAST_FAIL,
                              f"{penyedia} {kode}: saldo/tagihan bermasalah WAJIB menuntut tindakan")
                self.assertNotIn(p.kelas, SELF_HEALING)


# ── E. Jaring generik tidak boleh berbahaya ─────────────────────────────────────────────────────

class TestE_JaringGenerikAman(unittest.TestCase):
    """Vendor yang BELUM dipetakan tetap akan bertemu tenant. Jaringnya harus waras, bukan berbahaya."""

    def test_status_http_generik_tak_pernah_merem_cepat(self):
        for status in sorted(reg._STATUS_UMUM):
            kelas = reg._STATUS_UMUM[status]
            if status in (401, 402, 403, 404):
                continue          # memang menuntut tindakan tenant & tak terbantah lintas vendor
            with self.subTest(status):
                self.assertNotIn(kelas, FAST_FAIL,
                                 f"status {status} menghentikan channel hanya dari angka HTTP — "
                                 f"itu menebak, dan salah-rem menghentikan produksi tenant keliru")

    def test_429_vendor_tak_dikenal_boleh_diulang(self):
        p = reg.golongkan("vendor_yang_belum_ada", status=429, teks="429 Too Many Requests")
        self.assertEqual(p.kelas, ErrorClass.RATE_LIMIT)
        self.assertIn(p.kelas, SELF_HEALING)

    def test_5xx_vendor_tak_dikenal_tetap_UNKNOWN(self):
        """Keputusan owner yang berlaku: yang RAGU tetap UNKNOWN. Vendor yang dokumennya MENYEBUT
        arti 5xx tetap tertangani lewat tabelnya sendiri."""
        p = reg.golongkan("vendor_yang_belum_ada", status=500, teks="internal server error")
        self.assertEqual(p.kelas, ErrorClass.UNKNOWN)

    def test_vendor_tak_dikenal_tak_pernah_dituduhkan_ke_tenant(self):
        p = reg.golongkan("vendor_yang_belum_ada", teks="sesuatu yang asing sama sekali")
        self.assertEqual(p.kelas, ErrorClass.UNKNOWN)
        self.assertFalse(p.milik_kita, "galat asing tak boleh otomatis disebut salah kita")

    def test_permintaan_kita_kebesaran_ditandai_milik_kita(self):
        self.assertTrue(reg.golongkan("anthropic", status=413).milik_kita)


# ── F. Agregator ────────────────────────────────────────────────────────────────────────────────

class TestF_Agregator(unittest.TestCase):
    """fal.ai hari ini; blackbox.ai dsb. ke depan. Agregator meneruskan galat vendor di baliknya —
    kalau hanya lapis agregatornya dipetakan, 'saldo OpenAI habis' yang lewat agregator salah golong."""

    def test_galat_milik_agregator_sendiri(self):
        p = reg.golongkan("fal", kode="content_policy_violation", teks="")
        self.assertEqual(p.kelas, ErrorClass.UNKNOWN,
                         "isi prompt ditolak penyaring = bukan salah akun tenant & bukan salah kita; "
                         "dibiarkan boleh-diulang supaya jalur tulis-ulang prompt yang menanganinya")
        self.assertFalse(p.milik_kita)

    def test_saldo_agregator_habis_dari_sampel_nyata(self):
        p = reg.golongkan("fal", teks="User is locked. Reason: Exhausted balance. Top up your balance")
        self.assertEqual(p.kelas, ErrorClass.QUOTA_EXHAUSTED)
        self.assertIn(p.kelas, FAST_FAIL)

    def test_galat_TERUSAN_vendor_di_baliknya_ikut_terbaca(self):
        p = reg.golongkan(
            "fal", kode="downstream_service_error",
            teks="downstream_service_error: upstream said {'code': 'credit_balance_exhausted'}")
        self.assertEqual(p.kelas, ErrorClass.QUOTA_EXHAUSTED,
                         "galat yang DITERUSKAN dari vendor di balik agregator tidak terbaca — "
                         "saldo tenant habis akan tampak sebagai gangguan biasa")
        self.assertTrue(p.dasar.startswith("terusan-agregator"), p.dasar)

    def test_penanda_agregator_ada_dan_bisa_ditambah(self):
        agr = [n for n, s in reg.PENYEDIA.items() if s.get("agregator")]
        self.assertIn("fal", agr, "fal.ai wajib ditandai agregator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
