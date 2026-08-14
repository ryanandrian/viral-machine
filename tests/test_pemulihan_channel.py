"""
Uji regresi PERMANEN — REM DARURAT: simpan sebabnya & katakan apa artinya [B25].
SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8a (celah yang ditutup) + §9 (kontrak tampilan per-kelas).

Jalankan:  python -m unittest tests.test_pemulihan_channel

MASALAH YANG DIJAGA AGAR TAK KEMBALI
Saat rem darurat menyala, sistem SUDAH tahu kelas errornya — ia membacanya justru untuk memutuskan
mengerem cepat — lalu MEMBUANGNYA. Yang tersimpan hanya "3x produksi beruntun gagal/bermasalah",
sehingga layar & Telegram cuma bisa menganjurkan tebakan. Tenant tak pernah tahu pertanyaan yang
paling menentukan: APAKAH INI PULIH SENDIRI? Satu channel tenant BERBAYAR karena itu mati ±44 jam
menunggu sesuatu yang sudah pulih sendiri keesokan harinya.

Yang dijaga:
  A. `_pause_channel` menyimpan `production_paused_class` — untuk KEDUA cabang (rem-cepat & 3-gagal).
  B. Alasan yang tersimpan memuat pesan manusiawi dari kegagalan terakhir, bukan kalimat generik saja.
  C. Telegram memberi anjuran BERBEDA untuk kelas yang pulih-sendiri vs yang butuh tindakan.
  D. ANTI-DRIFT: `SELF_HEALING` (kode) ↔ kolom "Pulih sendiri?" (dokumen) ↔ resep layar (FE).
     Tiga tempat, satu kebenaran — kalau salah satu bergeser, uji ini merah.
"""
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import FAST_FAIL, SELF_HEALING, ErrorClass  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOK = os.path.join(AKAR, "AI_ERROR_MANAGEMENT_ARCHITECTURE.md")
FE_PANEL = os.path.join(AKAR, "apps", "web", "src", "components", "pemulihan-channel.tsx")
# Cermin KEEMPAT — layar admin punya salinan SELF_HEALING sendiri. Sempat luput dari penjagaan:
# uji ini bahkan mengklaim "lintas 3 tempat" padahal ada 4. Kelas baru yang tak diperbarui di sini
# membuat layar admin salah menyatakan "pulih sendiri" tanpa ada yang menangkapnya.
FE_ADMIN = os.path.join(AKAR, "apps", "web", "src", "app", "admin", "(panel)", "system", "page.tsx")


def _baca(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Stub Supabase minimal: cukup untuk menangkap payload update ke `channels` ────────────────────
class _Tabel:
    def __init__(self, sink):
        self._sink = sink
        self._upd = None

    def update(self, payload):
        self._upd = payload
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        if self._upd is not None:
            self._sink.append(self._upd)
        class R:  # noqa: N801
            data = []
        return R()


class FakeSB:
    def __init__(self):
        self.tulisan = []

    def table(self, _nama):
        return _Tabel(self.tulisan)


class TestRemMenyimpanSebabnya(unittest.TestCase):
    """A — kelas error berhenti dibuang."""

    def _pause(self, kelas):
        from src.orchestrator import producer
        sb = FakeSB()
        producer._pause_channel(sb, {"id": "C1"}, "alasan apa pun", error_class=kelas)
        return sb.tulisan[0]

    def test_kelas_tersimpan(self):
        for kelas in ErrorClass:
            with self.subTest(kelas=kelas.value):
                self.assertEqual(self._pause(kelas.value)["production_paused_class"], kelas.value)

    def test_kelas_kosong_jadi_null_bukan_string_kosong(self):
        # String kosong di kolom teks = nilai yang tampak ada tapi tak bermakna; layar akan
        # memperlakukannya sebagai kelas tak dikenal alih-alih "tidak diketahui".
        self.assertIsNone(self._pause("")["production_paused_class"])
        from src.orchestrator import producer
        sb = FakeSB()
        producer._pause_channel(sb, {"id": "C1"}, "x")   # tanpa argumen sama sekali
        self.assertIsNone(sb.tulisan[0]["production_paused_class"])

    def test_kolom_rem_lama_tetap_ditulis(self):
        # REGRESI: menambah kolom baru tak boleh menghilangkan yang lama.
        p = self._pause("rate_limit")
        for k in ("production_paused", "production_paused_at", "production_paused_reason"):
            self.assertIn(k, p)
        self.assertTrue(p["production_paused"])


class TestAlasanMemuatPenyebabNyata(unittest.TestCase):
    """B — cabang 3-kegagalan dulu hanya menulis kalimat generik."""

    def test_kedua_cabang_menyertakan_pesan_terakhir(self):
        # Jendela dibatasi SEMANTIK (dari "REM DARURAT" sampai notifikasinya), bukan jumlah karakter:
        # potongan sepanjang-N pecah begitu ada komentar baru menggeser barisnya keluar.
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "producer.py"))
        i = src.index("REM DARURAT")
        j = src.index("notify_circuit_break", i)
        blok = src[i:j]
        self.assertIn("Penyebab terakhir:", blok,
                      "cabang 3-kegagalan tak lagi menyertakan penyebab — tenant kembali buta")
        self.assertIn("error_class=_kelas", blok, "kelas tak diteruskan ke penyimpan rem")


class TestTelegramBedakanPulihSendiri(unittest.TestCase):
    """C — satu bit terpenting: perlu bertindak atau tidak."""

    def _kirim(self, kelas):
        from src.utils.telegram_notifier import TelegramNotifier
        n = TelegramNotifier()
        with patch.object(n, "_chat_id_for_tenant", return_value="123"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            n.notify_circuit_break("T1", "C1", "sebab apa pun", "Channel X", error_class=kelas)
        return kirim.call_args[0][1]

    def test_kelas_pulih_sendiri_menyuruh_menunggu(self):
        for kelas in SELF_HEALING:
            with self.subTest(kelas=kelas.value):
                t = self._kirim(kelas.value)
                self.assertIn("pulih sendiri", t)
                self.assertNotIn("perlu Anda kerjakan", t)

    def test_kelas_butuh_tindakan_menyuruh_bertindak(self):
        for kelas in FAST_FAIL:
            with self.subTest(kelas=kelas.value):
                t = self._kirim(kelas.value)
                self.assertIn("TIDAK pulih sendiri", t)

    def test_kelas_tak_diketahui_tidak_mengarang(self):
        for nilai in ("", "kelas_ngawur"):
            t = self._kirim(nilai)
            self.assertNotIn("pulih sendiri", t,
                             "tanpa kelas, sistem TIDAK boleh menjanjikan apa pun soal pemulihan")

    def test_mengantar_ke_layar_bila_alamat_diketahui(self):
        # Alamat aplikasi datang dari lingkungan (kosong di mesin uji, terisi di produksi) —
        # keduanya wajib diuji: ada alamat → tautan; tak ada → pesan tetap utuh tanpa tautan bolong.
        with patch.dict(os.environ, {"APP_BASE_URL": "https://mesinviral.com"}):
            self.assertIn("https://mesinviral.com/channels/C1", self._kirim("rate_limit"))
        with patch.dict(os.environ, {"APP_BASE_URL": ""}):
            t = self._kirim("rate_limit")
            self.assertNotIn("/channels/", t)
            self.assertIn("Pulihkan produksi", t, "tanpa alamat, anjurannya tetap harus utuh")


class TestNotifUnggahGagalIkutMenjawabPulihSendiri(unittest.TestCase):
    """§8b — notifikasi kegagalan UNGGAH dulu satu-satunya yang tak bisa menjawab
    "perlu bertindak atau cukup ditunggu?", padahal `publish()` SUDAH mengembalikan `error_class`
    (dibuang di pemanggil). Akibatnya jatah unggah yang pulih sendiri terlihat sama gentingnya
    dengan koneksi YouTube yang putus permanen.

    SAMPEL DI SINI VERBATIM DARI worker.log PRODUKSI (bukan karangan — pelajaran §11 04-Agu):
      • `invalid_grant: Token has been expired or revoked.`  (4 kejadian)
      • `unauthorized_client: Unauthorized`                  (2 kejadian)
    """

    SAMPEL_INVALID_GRANT = ("('invalid_grant: Token has been expired or revoked.', "
                            "{'error': 'invalid_grant', 'error_description': "
                            "'Token has been expired or revoked.'})")
    SAMPEL_UNAUTH_CLIENT = ("('unauthorized_client: Unauthorized', "
                            "{'error': 'unauthorized_client', 'error_description': 'Unauthorized'})")

    def _kirim(self, kelas, pesan="apa pun"):
        from src.utils.telegram_notifier import TelegramNotifier
        n = TelegramNotifier()
        with patch.object(n, "_get_chat_id", return_value="123"), \
             patch.object(n, "_channel_name", return_value="Channel X"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            n.notify_publish_fail(run_id="R1", tenant_id="T1", error=pesan, error_class=kelas)
        return kirim.call_args[0][1]

    def test_token_dicabut_menyuruh_periksa_koneksi_youtube(self):
        """Sampel nyata paling sering: token dicabut/kedaluwarsa = AUTH_INVALID, mustahil sembuh
        dengan menunggu. Tenant harus disuruh menyambungkan ulang, bukan dibiarkan menunggu."""
        t = self._kirim(ErrorClass.AUTH_INVALID.value, self.SAMPEL_INVALID_GRANT)
        self.assertIn("TIDAK pulih sendiri", t)
        self.assertIn("Koneksi YouTube", t)
        self.assertIn("invalid_grant", t, "sebab nyata harus tetap terbaca untuk diagnosa")

    def test_kelas_pulih_sendiri_menyuruh_menunggu(self):
        for kelas in SELF_HEALING:
            with self.subTest(kelas=kelas.value):
                t = self._kirim(kelas.value)
                self.assertIn("pulih sendiri", t)
                self.assertNotIn("perlu Anda kerjakan", t)

    def test_semua_kelas_butuh_tindakan_konsisten(self):
        for kelas in FAST_FAIL:
            with self.subTest(kelas=kelas.value):
                self.assertIn("TIDAK pulih sendiri", self._kirim(kelas.value))

    def test_tanpa_kelas_atau_kelas_asing_tidak_mengarang(self):
        """`unauthorized_client` BELUM terpetakan (§4) — sengaja: memetakannya ke AUTH_INVALID akan
        MENANDAI koneksi YouTube tenant tidak sah = perilaku mesin, keputusan produk (§0.6).
        Sampai diketok, notifikasinya harus netral, bukan menjanjikan pemulihan."""
        for nilai in ("", "kelas_ngawur"):
            with self.subTest(kelas=nilai):
                t = self._kirim(nilai, self.SAMPEL_UNAUTH_CLIENT)
                self.assertNotIn("pulih sendiri", t)
                self.assertIn("dicoba ulang otomatis", t)

    def test_tetap_jalan_tanpa_argumen_kelas(self):
        """Argumen baru tidak boleh memaksa pemanggil lama — nol regresi."""
        from src.utils.telegram_notifier import TelegramNotifier
        n = TelegramNotifier()
        with patch.object(n, "_get_chat_id", return_value="123"), \
             patch.object(n, "_channel_name", return_value="Channel X"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            n.notify_publish_fail(run_id="R1", tenant_id="T1", error="x")
        self.assertIn("dicoba ulang otomatis", kirim.call_args[0][1])


class _QRuns:
    """Stub rantai kueri production_runs yang MENDUKUNG `.gt()` — inti perbaikan 0197."""

    def __init__(self, rows):
        self._rows = rows
        self._sejak = None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gt(self, kolom, nilai):
        assert kolom == "created_at", f"filter tak terduga: {kolom}"
        self._sejak = nilai
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = [r for r in self._rows if not self._sejak or r["created_at"] > self._sejak]
        rows = sorted(rows, key=lambda r: r["created_at"], reverse=True)
        class R:  # noqa: N801
            data = rows
        return R()


class TestPemulihanMemutusHitungan(unittest.TestCase):
    """
    [0197] BUG yang dilaporkan owner: BISIK NUSANTARA "dihentikan mesin" berulang meski sudah
    dipulihkan. Log membuktikan rem menyala 2× dalam sehari TANPA satu pun percobaan produksi baru —
    kegagalan HARI SEBELUMNYA masih terhitung, jadi siklus penjadwal berikutnya langsung mengerem lagi.

    Lahir dari jalur buka yang ditambahkan [B24]: dulu rem hanya dilepas oleh produksi SUKSES, dan
    sukses itu sendiri memutus hitungan. Menambah cara melepas rem tanpa ikut memutus hitungannya =
    menambah pintu tanpa memasang lantainya.
    """

    RUNS = [
        {"created_at": "2026-08-02T11:50:00+00:00", "status": "failed",
         "error_class": "rate_limit", "error_message": "jatah harian habis"},
        {"created_at": "2026-08-02T11:49:00+00:00", "status": "failed",
         "error_class": "rate_limit", "error_message": "jatah harian habis"},
        {"created_at": "2026-08-02T11:36:00+00:00", "status": "failed",
         "error_class": "unknown", "error_message": "naskah tak layak"},
        {"created_at": "2026-08-02T11:27:00+00:00", "status": "success",
         "error_class": None, "error_message": None},
    ]

    def _stub(self):
        class SB:
            def table(_self, _n):
                return _QRuns(TestPemulihanMemutusHitungan.RUNS)
        return SB()

    def test_tanpa_titik_pemulihan_streak_penuh(self):
        """Perilaku lama — inilah yang mengerem berulang.

        [14-Agu] Angka ini sempat diubah 3 → 1 oleh percobaan 12-Agu (kelas pulih-sendiri dibuat
        netral). Percobaan itu DICABUT karena melahirkan banjir 53 kabar gagal ke dua tenant, jadi
        angkanya kembali 3: contoh data ini 3 kegagalan, dan KETIGANYA dihitung."""
        with patch("src.orchestrator.inventory._sb", return_value=self._stub()):
            from src.orchestrator import inventory
            self.assertEqual(inventory.recent_nonready_streak("C1"), 3)

    def test_sesudah_pemulihan_hitungan_nol(self):
        with patch("src.orchestrator.inventory._sb", return_value=self._stub()):
            from src.orchestrator import inventory
            self.assertEqual(
                inventory.recent_nonready_streak("C1", sejak="2026-08-03T00:00:00+00:00"), 0,
                "kegagalan sebelum pemulihan masih dihitung → channel direm ulang seketika")

    def test_kegagalan_BARU_tetap_dihitung(self):
        # Rem tidak boleh lumpuh: periode yang belum ditutup tetap dihukum. KETIGA kegagalan
        # dihitung — termasuk yang pulih sendiri (lihat pencabutan 14-Agu di docstring inventory).
        with patch("src.orchestrator.inventory._sb", return_value=self._stub()):
            from src.orchestrator import inventory
            self.assertEqual(
                inventory.recent_nonready_streak("C1", sejak="2026-08-01T00:00:00+00:00"), 3)

    def test_rem_cepat_membaca_periode_yang_sama(self):
        # Dua pengambil keputusan tak boleh membaca dunia yang berbeda.
        with patch("src.orchestrator.inventory._sb", return_value=self._stub()):
            from src.orchestrator import inventory
            self.assertIsNone(inventory.latest_failure("C1", sejak="2026-08-03T00:00:00+00:00"))
            lf = inventory.latest_failure("C1", sejak="2026-08-01T00:00:00+00:00")
            self.assertEqual(lf["error_class"], "rate_limit")

    def test_penjadwal_meneruskan_titik_pemulihan(self):
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "producer.py"))
        self.assertIn('_sejak = ch.get("production_resumed_at")', src,
                      "penjadwal tak membaca titik pemulihan → bug 0197 kembali")
        self.assertIn("recent_nonready_streak(cid, sejak=_sejak)", src)
        self.assertIn("latest_failure(cid, sejak=_sejak)", src)

    def test_semua_jalur_pelepas_rem_mencatat_titiknya(self):
        # Melepas rem tanpa mencatat titiknya = pemulihan yang hanya bertahan sampai siklus berikutnya.
        self.assertIn("production_resumed_at", _baca(os.path.join(AKAR, "src", "orchestrator", "producer.py")))
        sql = _baca(os.path.join(AKAR, "migrations", "0197_pemulihan_memutus_hitungan_kegagalan.sql"))
        self.assertIn("production_resumed_at = now()", sql)
        self.assertIn("production_paused_class = null", sql,
                      "kelas lama wajib ikut dibersihkan — kalau tidak, layar menampilkan sebab basi")


class TestJalurPemulihanYangBenarDidahulukan(unittest.TestCase):
    """
    PELAJARAN MAHAL 2026-08-03 — tenant komplain, dan penyebabnya keputusan UI, bukan logika.

    Tombol "Pulihkan produksi" sempat ditawarkan kepada SEMUA orang. Ia hanya melepas rem: tak
    memproduksi apa pun, tak membuktikan apa pun. Tenant wajar menekan tombol yang paling menonjol —
    log produksi mencatat ia menekannya pukul 11:01:19 dan 11:08:08, dan mesin mengerem lagi
    11 detik & 1 detik kemudian. Bagi tenant: aplikasinya rusak.

    Jalur lama ("Jalankan uji & pulihkan") tak pernah punya masalah itu justru karena ia MENUNTUT
    BUKTI: satu produksi berhasil, dan keberhasilan itulah yang memutus hitungan kegagalan.

    Aturan lama yang dikunci di sini: *"selama uji masih boleh dijalankan, ITU jalur yang ditawarkan."*

    ⚠️ DIPERSEMPIT 2026-08-06 — aturan itu terlalu luas, dan keluasannya melahirkan jebakan sendiri.
    Ditemukan owner: rem menyala karena jatah HARIAN penyedia habis (Groq "tokens per day"), lalu
    panel menyembunyikan tombol pemulih dan menyuruh menguji. Padahal uji = satu produksi NYATA yang
    memanggil penyedia yang jatahnya SEDANG habis ⇒ dijamin gagal, sambil membakar sisa jatah hari
    itu. Terukur: channel tenant BERBAYAR berhenti 1-Agu s/d 6-Agu tanpa jalan keluar yang berfungsi.

    KENAPA MEMPERSEMPITNYA AMAN — akar insiden 3-Agu SUDAH ditutup di MESIN, bukan di layar:
    migrasi **0197** membuat pelepasan rem menyetel `production_resumed_at` DALAM SATU PERNYATAAN,
    dan hitungan kegagalan beruntun hanya menghitung kegagalan SESUDAH titik itu. Rem-menyala-lagi-
    11-detik-kemudian (yang dulu terjadi karena kegagalan HARI SEBELUMNYA masih terhitung) kini
    mustahil secara struktur. Aturan UI di atas ternyata tambalan penyeimbang untuk bug yang sudah
    diperbaiki — dan tambalan itu sendiri menjadi jebakan.

    ATURAN BARU yang dikunci: jalur ditentukan oleh **SEBAB**, bukan oleh "boleh menguji atau tidak".
      • sebab BUTUH TINDAKAN TENANT → uji tetap didahulukan (uji MEMBUKTIKAN perbaikannya berhasil)
      • sebab PULIH SENDIRI / TAK DIKETAHUI → tombol pemulih + peringatan jujur
    Jebakannya sendiri dijaga terpisah di `tests/test_pemulihan_tak_menjebak.py`.
    """

    FE = os.path.join(AKAR, "apps", "web", "src", "components", "pemulihan-channel.tsx")
    HAL = os.path.join(AKAR, "apps", "web", "src", "app", "(app)", "channels", "[id]", "page.tsx")

    def test_tombol_pintas_tak_pernah_mendahului_jalur_uji(self):
        fe = _baca(self.FE)
        self.assertIn("bisaUji", fe, "panel tak lagi membedakan tenant yang masih bisa menguji")
        self.assertIn("ujiJalurYangBenar", fe,
                      "penjaga berbasis SEBAB hilang — panel kembali bercabang pada 'boleh menguji'")
        # Tombol pintas WAJIB tetap di cabang TERAKHIR — pelajaran 3-Agu: jangan ditawarkan lebih dulu.
        i_uji = fe.index("ujiJalurYangBenar ? (")
        i_tombol = fe.index("onClick={onPulihkan}")
        self.assertLess(i_uji, i_tombol,
                        "tombol pintas mendahului jalur uji — tenant akan menekannya lagi")

    def test_yang_sebabnya_butuh_tindakan_diarahkan_ke_uji(self):
        fe = _baca(self.FE)
        self.assertRegex(fe, r"Jalankan uji & pulihkan|Run & recover",
                         "panel tak mengarahkan ke jalur yang MEMBUKTIKAN")
        # Kalimatnya dipertajam bersama penyempitan aturan: uji kini HANYA ditawarkan untuk sebab yang
        # butuh tindakan tenant, jadi yang dibuktikan adalah PERBAIKAN TENANT — bukan lagi klaim umum
        # "channel Anda sehat" (yang dulu dipakai untuk semua sebab, termasuk yang pulih sendiri).
        self.assertIn("membuktikan perbaikan Anda berhasil", fe,
                      "alasan 'kenapa uji' tak dijelaskan — tenant tak tahu bedanya dengan jalan pintas")

    def test_halaman_meneruskan_keadaan_gerbang(self):
        hal = _baca(self.HAL)
        self.assertIn("onGate=", hal, "halaman tak lagi tahu apakah uji terkunci")
        self.assertIn("bisaUji={!ujiTerkunci}", hal)

    def test_tombol_pintas_tetap_ada_untuk_yang_terjebak(self):
        # Jangan berlebihan: yang ujinya TERKUNCI (masa tenggang / jatah coba habis) tetap butuh
        # jalan keluar — tanpa itu, jebakan yang ditutup [B24] kembali terbuka.
        fe = _baca(self.FE)
        self.assertIn("onPulihkan", fe)
        self.assertIn("Pulihkan produksi", fe)


class TestAntiDriftTigaTempat(unittest.TestCase):
    """
    D — `SELF_HEALING` hidup di TIGA tempat: kode (Python), dokumen (tabel §1), layar (peta resep TS).
    Duplikasi ini tak terhindarkan (tiga bahasa berbeda) — maka diuji, bukan dipercaya.
    """

    def test_setiap_kelas_punya_kepastian(self):
        # Tak boleh ada kelas yang menggantung: ia pulih sendiri, atau butuh tindakan, atau UNKNOWN.
        menggantung = {k.name for k in ErrorClass} - {k.name for k in SELF_HEALING} \
            - {k.name for k in FAST_FAIL} - {ErrorClass.UNKNOWN.name}
        self.assertFalse(menggantung,
                         f"Kelas tanpa kepastian pulih-sendiri/butuh-tindakan: {sorted(menggantung)}")

    def test_dokumen_selaras_dengan_self_healing(self):
        tabel = [b for b in _baca(DOK).splitlines() if b.strip().startswith("| `")]
        for kelas in ErrorClass:
            baris = next((b for b in tabel if f"`{kelas.name}`" in b), None)
            self.assertIsNotNone(baris, f"{kelas.name} tak ada di tabel §1")
            if kelas in SELF_HEALING:
                self.assertIn("✅", baris, f"§1 tak menandai {kelas.name} sebagai pulih-sendiri")
            elif kelas is not ErrorClass.UNKNOWN:
                self.assertIn("❌", baris, f"§1 salah menandai {kelas.name} — ia butuh tindakan")

    def test_layar_selaras_dengan_self_healing(self):
        fe = _baca(FE_PANEL)
        for kelas in ErrorClass:
            if kelas is ErrorClass.UNKNOWN:
                continue   # ditangani resep bawaan
            m = re.search(rf"\n  {kelas.value}: \{{(.*?)\n  \}},", fe, re.S)
            self.assertIsNotNone(m, f"Layar tak punya resep untuk kelas {kelas.value}")
            harus = "true" if kelas in SELF_HEALING else "false"
            self.assertIn(f"pulihSendiri: {harus}", m.group(1),
                          f"Layar menyatakan pulihSendiri yang BERBEDA dari SELF_HEALING utk {kelas.value}")

    def test_layar_admin_selaras_dengan_self_healing(self):
        """Cermin KEEMPAT: daftar channel-berhenti di layar admin."""
        src = _baca(FE_ADMIN)
        m = re.search(r"const SELF_HEALING = \[([^\]]*)\]", src)
        self.assertIsNotNone(m, "layar admin tak lagi punya daftar SELF_HEALING — strukturnya berubah?")
        di_admin = {x.strip().strip('"\'') for x in m.group(1).split(",") if x.strip()}
        di_kode = {k.value for k in SELF_HEALING}
        self.assertEqual(di_admin, di_kode,
                         f"layar admin melenceng.\n  admin: {sorted(di_admin)}\n  kode : {sorted(di_kode)}")

    def test_kartu_kegagalan_admin_pakai_kelas_tersimpan(self):
        """Cermin KELIMA (lahir 2026-08-04): `KELAS_LABEL` di kartu "Pipeline failures by type".

        Kartu itu dulu MENEBAK jenis kegagalan dari teks pesan dan mengabaikan `error_class` yang
        sudah disimpan mesin — angka yang dilihat owner tidak menggambarkan apa yang mesin tahu.
        Sekarang ia memakai kelas tersimpan sebagai FAKTA. Konsekuensinya: setiap kelas baru di
        `src/exceptions.py` WAJIB dapat label, kalau tidak ia jatuh senyap ke keranjang tebakan dan
        kartunya kembali menyesatkan — pelan-pelan, tanpa ada yang sadar. Itu pola melorot yang sama
        dengan empat cermin sebelumnya, karena itu dijaga di sini juga."""
        src = _baca(FE_ADMIN)
        self.assertIn("error_message,error_class", src,
                      "kartu tak lagi mengambil error_class dari DB — kembali menebak dari teks")

        m = re.search(r"const KELAS_LABEL[^=]*=\s*\{(.*?)\n\};", src, re.S)
        self.assertIsNotNone(m, "KELAS_LABEL tak ditemukan — struktur kartu berubah?")
        blok = m.group(1)
        di_layar = set(re.findall(r"^\s{2}(\w+):", blok, re.M))
        harus = {k.value for k in ErrorClass if k is not ErrorClass.UNKNOWN}
        self.assertEqual(di_layar, harus,
                         f"label kelas di kartu admin melenceng dari kode.\n"
                         f"  kartu: {sorted(di_layar)}\n  kode : {sorted(harus)}")

        # `unknown` SENGAJA tak berlabel: ia bukan fakta, jadi harus jatuh ke jalur tebakan-teks.
        self.assertNotIn("unknown:", blok,
                         "`unknown` diberi label = menyamarkan 'tak tahu' sebagai fakta")

        # Kejujuran asal-angka: keranjang hasil tebakan WAJIB ditandai, dan dwibahasa (§3.5).
        for penanda in ("(tebakan dari teks)", "(guessed from text)"):
            self.assertIn(penanda, src,
                          "keranjang tebakan tak ditandai — pembaca akan menganggapnya fakta mesin")

    def test_layar_tak_menyebut_nama_penyedia(self):
        """Arahan owner: penyedia akan terus bertambah → petakan per KELAS, jangan per merek."""
        fe = _baca(FE_PANEL)
        # Buang blok komentar penjelas (di situ nama boleh muncul sebagai contoh sejarah).
        badan = fe[fe.index("const RESEP"):]
        for merek in ("groq", "openai", "elevenlabs", "gemini", "anthropic", "fal.ai", "edge_tts"):
            self.assertNotIn(merek, badan.lower(),
                             f"Nama penyedia '{merek}' muncul di peta layar — layar akan basi "
                             f"pada penyedia berikutnya. Petakan per KELAS.")


class TestSetiapKegagalanDihitungAntiBanjir(unittest.TestCase):
    """⛔⛔ PENCABUTAN 14-Agu — SETIAP kegagalan dihitung, TERMASUK yang pulih sendiri.

    Kelas ini menggantikan `TestSebabPulihSendiriTakMengeremChannel` (12-Agu), yang menjaga
    perilaku SEBALIKNYA dan karena itu menjaga sebuah bug. Arahnya dibalik dengan sengaja.

    **Apa yang dibayar untuk pelajaran ini** (data produksi, bukan taksiran):
      • 13-Agu Thetangga Property — 30 kegagalan / 8 menit (29 jatah-harian) · rem TIDAK menyala
      • 14-Agu BISIK NUSANTARA    — 23 kegagalan / 11 menit (21 jatah-harian) · rem TIDAK menyala
      • satu produksi baru tiap ±14 detik ⇒ ±257 kabar gagal per JAM ke Telegram tenant
      • 50 dari 53 kegagalan `rate_limit` sepanjang umur aplikasi terjadi di dua hari itu (94%)
      • yang akhirnya menghentikannya: **tenant mematikan channelnya sendiri**

    **Sebabnya, dalam satu kalimat:** rem ini menghentikan CHANNEL *dan* menghentikan PERCOBAAN.
    Pengecualian 12-Agu hanya diniatkan untuk yang pertama, tapi yang kedua ikut hilang — dan tak
    ada apa pun di aplikasi ini yang menggantikannya.

    ⛔ **Bila suatu hari ada yang hendak mengecualikan kelas apa pun dari hitungan ini:** jangan,
    sampai ada penahan laju yang menggantikan fungsi kedua itu. Jalan keluar yang benar (jeda
    sementara + satu kabar) menunggu ketokan owner — SSOT §8k.
    """

    def _stub(self, runs):
        class SB:
            def table(_self, _n):
                return _QRuns(runs)
        return SB()

    def _streak(self, runs):
        with patch("src.orchestrator.inventory._sb", return_value=self._stub(runs)):
            from src.orchestrator import inventory
            return inventory.recent_nonready_streak("C1")

    @staticmethod
    def _run(kelas, i=0, status="failed"):
        return {"created_at": f"2026-08-02T1{i}:00:00+00:00", "status": status,
                "error_class": kelas, "error_message": "x"}

    def test_tiga_kegagalan_pulih_sendiri_TETAP_mengerem(self):
        """⛔ INTI PENCABUTAN. Inilah uji yang, bila merah, berarti banjir 13/14-Agu bisa terulang."""
        for kelas in ("rate_limit", "transient"):
            with self.subTest(kelas):
                runs = [self._run(kelas, i) for i in (9, 8, 7)]
                self.assertEqual(
                    self._streak(runs), 3,
                    f"'{kelas}' dikecualikan dari hitungan → mesin mencoba TANPA HENTI dan tenant "
                    f"dibanjiri ±257 kabar gagal per jam (Thetangga 30 kegagalan/8 menit; BISIK "
                    f"23/11 menit). Jangan dikecualikan sebelum ada penahan laju penggantinya.")

    def test_SELURUH_kelas_error_ikut_dihitung(self):
        """Anti-drift menyeluruh: tak satu pun kelas boleh mendapat perlakuan istimewa di sini.

        Ditulis atas SELURUH anggota `ErrorClass`, bukan daftar yang diketik tangan — supaya kelas
        yang ditambahkan kelak ikut terjaga tanpa uji ini perlu disunting."""
        from src.exceptions import ErrorClass
        for kelas in ErrorClass:
            with self.subTest(kelas.value):
                runs = [self._run(kelas.value, i) for i in (9, 8, 7)]
                self.assertEqual(self._streak(runs), 3,
                                 f"'{kelas.value}' tidak dihitung → rem tak pernah menyala untuk "
                                 f"sebab ini, dan tak ada yang menghentikan percobaan berulang")

    def test_campuran_semua_dihitung(self):
        runs = [self._run("rate_limit", 9), self._run("unknown", 8),
                self._run("transient", 7), self._run("auth_invalid", 6)]
        self.assertEqual(self._streak(runs), 4,
                         "setiap kegagalan beruntun dihitung, apa pun kelasnya")

    def test_pulih_sendiri_TIDAK_memutus_hitungan(self):
        """Hanya SUKSES yang memutus. Kalau kegagalan pulih-sendiri memutus, kegagalan nyata
        sebelumnya ikut dimaafkan dan channel yang benar-benar rusak tak pernah direm."""
        runs = [self._run("unknown", 9), self._run("rate_limit", 8), self._run("unknown", 7),
                self._run("unknown", 6)]
        self.assertEqual(self._streak(runs), 4,
                         "kegagalan pulih-sendiri di tengah MEMUTUS hitungan → rem lumpuh")

    def test_sukses_TETAP_memutus_hitungan(self):
        runs = [self._run("unknown", 9), self._run(None, 8, status="success"),
                self._run("unknown", 7)]
        self.assertEqual(self._streak(runs), 1, "run SUKSES wajib tetap memutus hitungan")

    def test_kelas_kosong_TETAP_dihitung(self):
        """Run lama (sebelum kelas disimpan) tak boleh mendadak dimaafkan — perilaku lama dijaga."""
        runs = [self._run(None, 9), self._run("", 8), self._run(None, 7)]
        self.assertEqual(self._streak(runs), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
