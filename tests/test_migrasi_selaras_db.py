"""Migrasi ↔ DB: kolom yang migrasi janjikan harus benar-benar ada.

MASALAH YANG DIJAGA
Proyek ini **tidak punya tabel pencatat migrasi** (diperiksa 2026-08-04: `schema_migrations`,
`_migrations`, `migrations`, `supabase_migrations` — tak satu pun ada). Migrasi diterapkan manual, dan
satu-satunya catatan "sudah terpasang" adalah CATATAN DI DOKUMEN (blok POSISI di `SISA_KERJA_GO_LIVE.md`).
Catatan dokumen bisa membusuk — malam ini sudah terbukti tiga kali di dokumen lain. Maka satu-satunya
kebenaran = **EFEK migrasi di DB**.

DIVERIFIKASI 2026-08-04 terhadap DB live:
  • 111 kolom ditambahkan migrasi & belum dibuang → **111 ADA**, nol terlewat.
  • Efek 7 migrasi terakhir (0190–0197) yang diklaim blok POSISI: **semua terbukti terpasang**
    (kenop gerbang · `tenant_test_gate` · `tenant_produce_allowed` · `tenant_resume_channels` ·
    `trial_self_extends` · `production_paused_class` · `production_resumed_at`).

CATATAN ALAT UKUR (keempat kalinya alat saya salah pada 04-Agu): sapuan pertama melaporkan
`tts_pace_calibration.constraint` HILANG — padahal itu `ALTER TABLE … ADD CONSTRAINT …`, bukan kolom.
Regex menangkap kata kunci SQL sebagai nama kolom. **Satu alarm palsu dari 111 = 100% temuan palsu**,
dan kalau dipercaya, saya akan "memperbaiki" DB yang sehat. Karena itu pemindai di bawah membuang
kata-kunci SQL secara eksplisit, dan uji `test_pemindai_tak_menangkap_kata_kunci_sql` menjaganya.

LINGKUP: uji ini MENYENTUH DB (read-only, `select … limit 1`). Bila kredensial tak tersedia (mis. CI
tanpa `.env`), ia SKIP — jangan pernah membuat suite merah karena lingkungan, itu melatih orang
mengabaikan merah.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Kata kunci SQL yang muncul sesudah `ADD` tapi BUKAN nama kolom (sumber alarm palsu 04-Agu).
BUKAN_KOLOM = {"constraint", "primary", "unique", "foreign", "check", "exclude", "column", "if", "not"}


def _kolom_dijanjikan_migrasi() -> dict[tuple[str, str], str]:
    """(tabel, kolom) → berkas migrasi. Memperhitungkan DROP COLUMN & DROP TABLE."""
    tambah: dict[tuple[str, str], str] = {}
    buang_kolom: set[tuple[str, str]] = set()
    buang_tabel: set[str] = set()
    for f in sorted(glob.glob(os.path.join(AKAR, "migrations", "*.sql"))):
        s = open(f, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)\s+add\s+"
                             r"(?:column\s+)?(?:if\s+not\s+exists\s+)?(\w+)", s, re.I):
            tabel, kolom = m.group(1).lower(), m.group(2).lower()
            if kolom in BUKAN_KOLOM:
                continue                       # `ADD CONSTRAINT …` dst — bukan kolom
            tambah[(tabel, kolom)] = os.path.basename(f)
        for m in re.finditer(r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)\s+drop\s+"
                             r"(?:column\s+)?(?:if\s+exists\s+)?(\w+)", s, re.I):
            buang_kolom.add((m.group(1).lower(), m.group(2).lower()))
        for m in re.finditer(r"drop\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)", s, re.I):
            buang_tabel.add(m.group(1).lower())
    return {k: v for k, v in tambah.items()
            if k not in buang_kolom and k[0] not in buang_tabel}


def _sb():
    """Klien DB read-only; None bila lingkungan tak menyediakan kredensial."""
    try:
        from dotenv import load_dotenv
        from supabase import create_client
        load_dotenv(os.path.join(AKAR, ".env"))
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
        return create_client(url, key) if url and key else None
    except Exception:
        return None


class TestPemindaiMigrasiBenar(unittest.TestCase):
    """Pagar-untuk-pagar. Alat ukur yang salah lebih berbahaya daripada tidak mengukur."""

    def test_menemukan_banyak_kolom(self):
        n = len(_kolom_dijanjikan_migrasi())
        self.assertGreaterEqual(n, 80, f"pemindai hanya menemukan {n} kolom — polanya rusak")

    def test_pemindai_tak_menangkap_kata_kunci_sql(self):
        """Sumber alarm palsu 04-Agu: `ADD CONSTRAINT` dibaca sebagai kolom bernama 'constraint'."""
        kolom = {k for _, k in _kolom_dijanjikan_migrasi()}
        keliru = sorted(kolom & BUKAN_KOLOM)
        self.assertFalse(keliru, f"pemindai kembali menangkap kata kunci SQL sebagai kolom: {keliru}")

    def test_migrasi_terakhir_ikut_terbaca(self):
        """Migrasi [B24]/[B25] adalah yang paling berbahaya bila luput dari pengawasan."""
        pasangan = _kolom_dijanjikan_migrasi()
        for perlu in (("channels", "production_paused_class"), ("channels", "production_resumed_at"),
                      ("tenant_configs", "trial_self_extends")):
            self.assertIn(perlu, pasangan, f"{perlu} tak terbaca dari migrasi — pemindai buta")


class TestKolomJanjiMigrasiAdaDiDB(unittest.TestCase):

    def test_tak_ada_kolom_yang_terlewat(self):
        sb = _sb()
        if sb is None:
            self.skipTest("kredensial DB tak tersedia di lingkungan ini")
        # [DIPERBAIKI 2026-08-05] Versi pertama uji ini menganggap **error apa pun** sebagai "kolom
        # hilang". Akibatnya, saat 111 permintaan beruntun kena gangguan/pembatasan laju, ia melaporkan
        # BELASAN kolom hilang — padahal diverifikasi satu-per-satu SEMUANYA ADA (`app_config.value_text`,
        # `ai_providers.key_group`, `agents.telegram_chat_id`, …). **Alarm palsu dari penjaga sendiri**
        # adalah ranjau: sesi berikutnya akan "memperbaiki" DB yang sehat.
        # Sekarang dibedakan TIGA keadaan, dan "tak bisa memverifikasi" TIDAK PERNAH dilaporkan sebagai
        # "hilang" (kode PostgreSQL: 42703 = kolom tak ada · 42P01/PGRST205 = tabel tak ada).
        hilang, tabel_hilang, tak_terverifikasi = [], set(), []
        for (t, k), berkas in sorted(_kolom_dijanjikan_migrasi().items()):
            galat = None
            for _ in range(3):                     # ulang 2× pada gangguan sesaat
                try:
                    sb.table(t).select(k).limit(1).execute()
                    galat = None
                    break
                except Exception as e:
                    galat = str(e)
                    if "42703" in galat or "does not exist" in galat or "find the table" in galat:
                        break                      # vonis pasti — tak perlu diulang
            if galat is None:
                continue
            if "42703" in galat or ("column" in galat and "does not exist" in galat):
                hilang.append(f"{t}.{k} (migrasi {berkas})")
            elif "find the table" in galat or "42P01" in galat or "PGRST205" in galat:
                tabel_hilang.add(t)
            else:
                tak_terverifikasi.append(f"{t}.{k} → {galat[:90]}")
        self.assertFalse(
            tak_terverifikasi,
            "TAK BISA MEMVERIFIKASI ke DB (bukan berarti kolomnya hilang — jangan 'perbaiki' apa pun "
            "atas dasar ini):\n  " + "\n  ".join(tak_terverifikasi[:8])
            + "\nPeriksa koneksi/pembatasan laju, lalu jalankan ulang.")
        self.assertFalse(
            hilang,
            "Kolom yang DIJANJIKAN migrasi tapi TIDAK ADA di DB live:\n  " + "\n  ".join(hilang)
            + "\nArtinya migrasi belum diterapkan (atau kolomnya dihapus tangan). Kode yang memakainya "
              "akan gagal saat dijalankan. Tak ada tabel pencatat migrasi di proyek ini, jadi uji ini "
              "adalah satu-satunya pengawas otomatis keselarasan migrasi↔DB.")
        self.assertFalse(
            tabel_hilang,
            f"Tabel yang migrasi janjikan tapi tak ada di DB: {sorted(tabel_hilang)} — "
            f"bila memang sudah di-drop, tambahkan DROP TABLE-nya di migrasi agar tercatat.")


class TestTriggerJanjiMigrasiHidupDiDB(unittest.TestCase):
    """[14-Agu] Migrasi yang menjanjikan TRIGGER wajib punya triggernya HIDUP di DB.

    Kenapa perlu penjaga sendiri: proyek ini tak punya tabel pencatat migrasi, dan kolom bisa
    diperiksa lewat REST — **trigger tidak bisa**. Jadi trigger adalah bagian migrasi yang paling
    mudah hilang tanpa jejak (mis. saat DB dipulihkan dari cadangan) dan paling sulit disadari:
    tak ada galat, hanya perilaku yang diam-diam kembali salah.

    Yang dijaga 0198: menyalakan channel WAJIB menutup periode hitungan kegagalan. Bila triggernya
    hilang, dua channel tenant akan direm seketika saat dinyalakan — tanpa satu percobaan produksi.

    SKIP bila kredensial DB langsung tak tersedia (berkas koneksi tidak ikut ke repo). Lingkungan
    tak boleh membuat suite merah — itu melatih orang mengabaikan merah.
    """

    WAJIB = {
        "channels_activation_gate":   "gerbang aktivasi (channel tak lengkap tak bisa dinyalakan)",
        "channels_rem_readonly":      "kolom rem read-only bagi tenant (0195)",
        "channels_catat_pengaktifan": "menyalakan channel menutup periode kegagalan (0198, §8k)",
    }

    @staticmethod
    def _trigger_hidup():
        """Nama trigger channels yang hidup — None bila lingkungan tak punya sambungan langsung."""
        berkas = os.path.join(AKAR, "SUPABASE-CONNECTION.md")
        if not os.path.isfile(berkas):
            return None
        try:
            import psycopg2
        except Exception:
            return None
        # Berkas memuat DUA proyek: v1 (PENSIUN — HARAM disentuh, CLAUDE.md §6.1) dan v2. Baris v2
        # dipilih dengan memeriksa nama proyeknya, dan dipecah dari KANAN karena kata sandi memuat '@'.
        for baris in open(berkas, encoding="utf-8"):
            b = baris.strip()
            if not b.startswith("postgresql://") or "atliatnjhysdibmfypul" not in b:
                continue
            kredensial, _, alamat = b[len("postgresql://"):].rpartition("@")
            user, _, pw = kredensial.partition(":")
            hostport, _, db = alamat.partition("/")
            host, _, port = hostport.partition(":")
            if "ap-southeast" not in host:      # pagar kedua: region v2
                return None
            try:
                conn = psycopg2.connect(host=host, port=int(port or 5432), dbname=db or "postgres",
                                        user=user, password=pw, connect_timeout=15)
            except Exception:
                return None
            try:
                cur = conn.cursor()
                cur.execute("""select t.tgname from pg_trigger t
                               join pg_class c on c.oid = t.tgrelid
                               where c.relname = 'channels' and not t.tgisinternal""")
                return {r[0] for r in cur.fetchall()}
            finally:
                conn.rollback()
                conn.close()
        return None

    def test_trigger_channels_lengkap(self):
        hidup = self._trigger_hidup()
        if hidup is None:
            self.skipTest("sambungan DB langsung tak tersedia di lingkungan ini")
        hilang = {n: k for n, k in self.WAJIB.items() if n not in hidup}
        self.assertFalse(
            hilang,
            "TRIGGER yang dijanjikan migrasi TIDAK HIDUP di DB:\n  "
            + "\n  ".join(f"{n} — {k}" for n, k in hilang.items())
            + "\nTak ada galat yang akan muncul; perilakunya hanya kembali salah diam-diam.")

    def test_urutan_trigger_masih_seperti_dirancang(self):
        """Urutan trigger PostgreSQL = alfabetis, dan 0198 bergantung padanya.

        `channels_catat_pengaktifan` harus berjalan SESUDAH gerbang aktivasi (supaya channel yang
        ditolak tak sempat menutup periode) dan SEBELUM penjaga rem (supaya hasilnya diperiksa
        penjaga itu). Mengganti nama trigger tanpa memperhatikan ini akan mengubah urutannya.
        """
        hidup = self._trigger_hidup()
        if hidup is None:
            self.skipTest("sambungan DB langsung tak tersedia di lingkungan ini")
        urut = sorted(n for n in hidup if n in self.WAJIB)
        self.assertEqual(
            urut, ["channels_activation_gate", "channels_catat_pengaktifan", "channels_rem_readonly"],
            "urutan eksekusi trigger channels berubah — 0198 dirancang di antara keduanya")


if __name__ == "__main__":
    unittest.main(verbosity=2)
