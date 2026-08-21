"""KEGAGALAN KAMI HARAM DITIMPAKAN KEPADA TENANT — dan katalog harus BELAJAR.

Batch B dari rencana yang diketok owner 21-Agu. Dua cacat yang dijaga di sini:

═══ CACAT 1 — kegagalan KAMI berbunyi seperti kesalahan TENANT (laporan owner 20-Agu) ═══
RAD The Explorer gagal 21:00 dengan  *"Kredensial wajib belum lengkap: visual_api_key"*  lalu
BERHASIL 21:07 tanpa seorang pun menyentuh apa pun. Kredensialnya tak pernah berubah (akun OpenAI
terakhir disentuh 26-Juni). Yang terjadi, terbaca di log server:

    21:00:11.682 ERROR _set_key_from_pool — resolve pool key provider=elevenlabs
                 gagal: Server disconnected — kosong (no-fallback)

Jaringan ke DB terputus sekejap → kode menyetel kunci KOSONG → gerbang membacanya sebagai
"tenant belum mengisi". Dua titik lain menelan galat TANPA SATU BARIS LOG:
  · `_visual_provider`      → `return None` senyap  (penyebab kegagalan RAD ini)
  · `niche_visual_style={}` → gaya visual jatuh ke default HARDCODE senyap (kelas cacat
                              `sunnah_harian` yang sudah memakan korban 15-Agu)

Terukur: 1× sepanjang sejarah, `error_class='unknown'` ⇒ IKUT DIHITUNG REM. Tiga gangguan
jaringan berurutan akan mengerem channel yang sehat.

Redaksi yang diketok owner: **"sistem akan otomatis mencoba kembali"** — bukan "coba lagi"
(memerintah tenant), bukan "kredensial belum lengkap" (menuduh tenant). Kejujurannya terbukti:
producer adalah loop hidup ±16 detik, dan RAD memang pulih sendiri dalam 7 menit.

═══ CACAT 2 — katalog TIDAK PERNAH BELAJAR ═══
Mesin sudah membuktikan kematian model (7 run ber-`error_class='model_unavailable'`), tapi NOL
baris kode pernah menyentuh `ai_models`. Model yang terbukti mati tetap ditawarkan ke tenant lain.

Keberatan owner 21-Agu: memakai kunci admin/Test Lab untuk membuktikan = **membakar kredit owner
diam-diam**. ⇒ Rancangan itu DIBUANG. Karantina memakai bukti yang SUDAH ada di tangan:
    A (wajib) `dasar` = kode/teks-vendor  — bukan 404 telanjang
    B1 kata GLOBAL di pesan vendor (decommissioned / no longer available / deprecated / retired)
    B2 ≥2 TENANT BERBEDA gagal pada model yang sama
    B3 hilang dari umpan harga publik (price_sync sudah menghitungnya tiap 24 jam)
A tanpa B ⇒ NOL karantina, alarm admin ber-bukti. Nol panggilan berbayar di seluruh jalur.

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from src.exceptions import ErrorClass, FAST_FAIL, SELF_HEALING  # noqa: E402

# Kata-kata yang menyatakan kematian GLOBAL — tak mungkin berarti "akun Anda tak punya akses".
KATA_GLOBAL = ("decommission", "no longer available", "deprecat", "retired", "sunset")


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _tanpa_komentar(rel: str) -> str:
    """Sumber TANPA baris komentar. Sabotase membuktikan komentar menyelamatkan uji palsu:
    mengganti `error_class=ErrorClass.TRANSIENT` → `UNKNOWN` tetap HIJAU, karena komentar di
    sebelahnya menyebut kata "TRANSIENT". Yang dikunci wajib KODE, bukan penjelasan di sampingnya."""
    src = re.sub(r'"\s*\n\s*"', "", _baca(rel))
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))


def _baca_rapat(rel: str) -> str:
    """Sumber dengan sambungan string Python dirapatkan: `"a " \n "b"` → `"a b"`.
    Kode nyata memang dipotong baris agar ≤110 kolom; uji frasa HARAM gagal karenanya."""
    return re.sub(r'"\s*\n\s*"', "", _baca(rel))


class TestA_GagalBacaTidakMenuduhTenant(unittest.TestCase):
    """Titik yang menelan galat WAJIB bersuara, dan pesannya haram menuduh tenant."""

    SRC = "src/config/tenant_config.py"

    def test_visual_provider_tidak_lagi_bisu(self):
        src = _baca(self.SRC)
        i = src.find("def _visual_provider")
        self.assertGreater(i, 0)
        blok = src[i:src.find("def _set_key_from_pool", i)]
        self.assertIn(
            "logger.", blok,
            "`_visual_provider` gagal TANPA satu baris log — inilah titik yang membuat kegagalan RAD "
            "21:00 tak bisa dilacak, lalu dituduhkan ke kredensial tenant.")

    def test_niche_visual_gagal_baca_bersuara(self):
        src = _baca(self.SRC)
        i = src.find("config.niche_visual_style     = {}")
        self.assertGreater(i, 0, "titik jatuh-ke-kosong niche visual tak ditemukan")
        blok = src[i:i + 700]
        self.assertIn("logger.", blok,
                      "DNA niche gagal dibaca → gaya visual jatuh ke default hardcode SENYAP.")

    def test_gagal_baca_DITANDAI_bukan_ditebak(self):
        """Gerbang di hilir harus bisa membedakan "tenant belum mengisi" dari "kami gagal membaca".
        Menebaknya dari teks di hilir = kelas cacat yang sudah dicatat di `exceptions.py`."""
        src = _baca(self.SRC)
        self.assertIn(
            "baca_gagal", src,
            "Tak ada penanda gagal-baca ⇒ hilir mustahil membedakan kegagalan KAMI dari kelalaian "
            "tenant, dan pesan 'kredensial belum lengkap' akan terus menuduh tenant.")

    def test_penanda_diisi_di_KETIGA_titik(self):
        src = _baca(self.SRC)
        # ketiga titik yang bisa menghasilkan nilai kosong karena kegagalan baca
        for nama, jangkar in (
            ("_set_key_from_pool", "resolve pool key provider="),
            ("_visual_provider", "def _visual_provider"),
            ("niche visual", "config.niche_visual_style     = {}"),
        ):
            i = src.find(jangkar)
            self.assertGreater(i, 0, f"jangkar `{nama}` tak ditemukan")
            self.assertIn("baca_gagal", src[max(0, i - 500):i + 900],
                          f"titik `{nama}` tidak menandai gagal-baca")


class TestB_PesanKeTenantMemakaiRedaksiOwner(unittest.TestCase):
    SRC = "src/orchestrator/pipeline.py"

    def test_gerbang_kredensial_membedakan_dua_sebab(self):
        """Versi pertama uji ini LOLOS-LEMAH: ia hanya menuntut kata `baca_gagal` muncul di
        sekitar gerbang — dan komentar penjelas di atas gerbang sudah cukup membuatnya hijau.
        Yang dikunci sekarang: RANTAI-nya tersambung sungguhan — penanda DIBACA dari
        `run_config` (ditandai di titik kejadian, bukan ditebak dari teks di hilir), lalu
        gerbang benar-benar BERCABANG atas dasarnya SEBELUM kalimat yang menuduh tenant."""
        kode = _tanpa_komentar(self.SRC)
        self.assertIn(
            'getattr(run_config, "baca_gagal"', kode,
            "Gerbang tidak MEMBACA penanda gagal-baca dari run_config ⇒ ia mustahil membedakan "
            "kegagalan KAMI dari kelalaian tenant, dan hanya bisa MENEBAK dari teks di hilir.")
        i = kode.find("if _baca_gagal:")
        j = kode.find("Kredensial wajib belum lengkap")
        self.assertGreater(i, 0, "gerbang tak bercabang atas penanda gagal-baca")
        self.assertGreater(j, i,
                           "Cabang gagal-baca berada SESUDAH kalimat 'Kredensial wajib belum "
                           "lengkap' ⇒ tenant tetap dituduh lebih dulu; cabangnya tak pernah dicapai.")

    def test_kalimatnya_persis_redaksi_owner(self):
        src = _baca_rapat(self.SRC)
        self.assertIn(
            "otomatis mencoba kembali", src,
            "Redaksi owner 21-Agu: 'sistem akan otomatis mencoba kembali' — bukan 'coba lagi' "
            "(memerintah tenant, padahal ini mesin otomatis).")
        # Potong CABANG gagal-baca saja. Dua cabang memang berdampingan (gagal-baca lalu
        # kredensial-benar-benar-kosong) — memotong ±400 karakter menangkap cabang SEBELAHNYA dan
        # membuat uji ini gagal untuk alasan yang salah.
        awal = src.find("if _baca_gagal:")
        self.assertGreater(awal, 0, "cabang gagal-baca tak ditemukan")
        cabang = src[awal:src.find("raise ConfigError", src.find("raise ConfigError", awal) + 10)]
        self.assertIn("otomatis mencoba kembali", cabang,
                      "kalimat owner tidak berada di cabang gagal-baca")
        self.assertNotIn(
            "Kredensial wajib belum lengkap", cabang,
            "Cabang gagal-baca masih memakai kalimat yang MENUDUH tenant.")

    def test_digolongkan_TRANSIENT_dan_milik_kita(self):
        """Versi pertama uji ini PALSU, dan sabotase membuktikannya: mengganti
        `error_class=ErrorClass.TRANSIENT` menjadi `UNKNOWN` tetap HIJAU — karena komentar di
        sebelahnya menyebut kata "TRANSIENT". Sekarang komentar dibuang dulu, dan yang dikunci
        adalah penyetelan yang sesungguhnya, di dalam CABANG gagal-baca."""
        kode = _tanpa_komentar(self.SRC)
        awal = kode.find("if _baca_gagal:")
        self.assertGreater(awal, 0, "cabang gagal-baca tak ditemukan")
        cabang = kode[awal:kode.find("raise ConfigError", kode.find("raise ConfigError", awal) + 10)]
        self.assertIn(
            "error_class=ErrorClass.TRANSIENT", cabang,
            "gagal-baca jaringan wajib digolongkan `TRANSIENT` (pulih sendiri). `UNKNOWN` "
            "membuatnya terhitung sebagai kesalahan tak dikenal — dan pesannya jadi menyuruh "
            "tenant bertindak atas sesuatu yang pulih sendiri.")
        self.assertIn(
            "milik_kita=True", cabang,
            "kegagalan KAMI wajib ditandai `milik_kita=True` — tanpa itu permukaan hilir "
            "menempelkan 'kegagalan di layanan AI Anda', yakni menuduh tenant untuk galat kami.")

    def test_ambang_rem_TIDAK_bergeser(self):
        """REGRESI: kalau TRANSIENT masuk FAST_FAIL, channel sehat direm setelah 1 gangguan jaringan."""
        self.assertNotIn(ErrorClass.TRANSIENT, FAST_FAIL, "TRANSIENT tak boleh mengerem seketika")
        self.assertNotIn(ErrorClass.UNKNOWN, FAST_FAIL)
        self.assertIn(ErrorClass.TRANSIENT, SELF_HEALING,
                      "TRANSIENT wajib tergolong pulih-sendiri agar pesannya 'tunggu', bukan 'kerjakan'")


class TestC_KarantinaBerbasisBUKTI_BEBAS_BIAYA(unittest.TestCase):
    """Keberatan owner 21-Agu: HARAM memakai kredit owner untuk membuktikan model mati."""

    SRC = "src/orchestrator/karantina_model.py"

    def test_modulnya_ada(self):
        self.assertTrue(os.path.exists(os.path.join(AKAR, self.SRC)),
                        "jalur karantina belum dibangun — katalog tetap tak pernah belajar")

    def test_HARAM_memanggil_vendor_dengan_kunci_admin(self):
        """Yang dikunci = PEMAKAIAN, bukan penyebutan. Docstring modul memang MENJELASKAN kenapa
        rancangan berbayar ditolak owner — menyebutnya untuk menerangkan tidak sama dengan memakainya."""
        src = _baca(self.SRC)
        kode = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        for terlarang in ("model_tester", "admin_test_internal", "TestLab", "test_model"):
            self.assertFalse(
                re.search(rf"(import\s+[\w.]*{terlarang}|from\s+[\w.]*{terlarang}|{terlarang}\s*\()", kode),
                f"Jalur karantina MEMAKAI `{terlarang}` ⇒ membakar kredit owner diam-diam. "
                "Owner menolak rancangan itu 21-Agu; buktinya wajib dari data yang SUDAH ada.")
        self.assertNotIn(
            "def uji", kode,
            "Jalur karantina mendefinisikan pemanggil uji sendiri — tetap kredit owner yang terbakar.")

    def test_404_telanjang_HARAM_mengarantina(self):
        src = _baca(self.SRC)
        self.assertIn(
            "status-http-umum", src,
            "Jalur karantina tak membedakan 404 telanjang. 404 bisa berarti alamat salah di sisi "
            "KITA — mengarantina darinya akan mematikan model yang masih hidup.")

    def test_tiga_bukti_bebas_biaya_terpakai(self):
        src = _baca(self.SRC)
        self.assertTrue(any(k in src.lower() for k in KATA_GLOBAL),
                        "B1 (kata global di pesan vendor) tak dipakai")
        self.assertTrue(re.search(r"tenant", src) and re.search(r"2|dua", src),
                        "B2 (≥2 tenant berbeda) tak dipakai")
        self.assertIn("pricing", src.lower(), "B3 (hilang dari umpan harga) tak dipakai")

    def test_karantina_MENULIS_jejak_bukan_hanya_mematikan(self):
        src = _baca(self.SRC)
        for kolom in ("unavailable_since", "unavailable_reason"):
            self.assertIn(kolom, src,
                          f"karantina tak mencatat `{kolom}` ⇒ admin tak tahu kenapa model mati")
        self.assertIn("is_active", src, "karantina tak pernah menghentikan penawaran model")

    def test_ada_jalur_BUKA(self):
        """Mandat owner: setiap kunci punya jalur buka. Karantina HARAM menyala sendiri lagi."""
        src = _baca(self.SRC)
        self.assertTrue(
            re.search(r"admin", src, re.I),
            "Tak ada keterangan jalur buka — karantina tanpa jalur buka = jebakan (PAYMENT §10e-2).")


    def test_yang_DINILAI_adalah_pesan_VENDOR_bukan_pesan_KITA(self):
        """Rantai ini rapuh, dan kerapuhannya tak terlihat dari membaca kodenya.

        B1 mencari kata Inggris di pesan vendor (`decommissioned`, `no longer available`).
        Pesan-manusiawi KAMI berbahasa Indonesia — TERUKUR: `bukti_global()` atas
        "Model AI ini sudah tidak tersedia di penyedianya" mengembalikan None. Jadi bila
        seseorang kelak mengalirkan `human_message`/`error_message` ke karantina (dan itu terasa
        LEBIH RAPI — pesan yang sudah manusiawi), B1 jadi MUSTAHIL menyala dan seluruh jalur
        karantina berubah menjadi kode mati, tanpa satu uji pun merah.

        Diurai lewat AST, bukan pencocokan teks: sabotase membuktikan `pass  # karantina(sb, …)`
        LOLOS dari pencocokan teks — panggilannya mati, ujinya tetap hijau. AST hanya melihat
        pernyataan yang sungguh dijalankan."""
        import ast
        pohon = ast.parse(_baca("src/orchestrator/producer.py"))
        panggilan = [n for n in ast.walk(pohon)
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "id", getattr(n.func, "attr", "")) == "karantina"]
        self.assertTrue(
            panggilan,
            "Producer tak pernah MEMANGGIL penilai karantina ⇒ modulnya kode mati dan katalog "
            "tetap tak pernah belajar, persis keadaan sebelum perbaikan ini.")

        # Argumen pesan (ke-4) wajib galat TEKNIS vendor, bukan pesan yang sudah kami terjemahkan.
        arg_pesan = ast.unparse(panggilan[0].args[3]) if len(panggilan[0].args) > 3 else ""
        self.assertIn(
            "'error'", arg_pesan.replace('"', "'"),
            f"Karantina dinilai dari `{arg_pesan}` — bukan galat teknis vendor. Bukti B1 mencari "
            "kata Inggris milik vendor; memberinya pesan lain membuat karantina mustahil menyala.")
        for manusiawi in ("human_message", "human_error", "error_message"):
            self.assertNotIn(
                manusiawi, arg_pesan,
                f"Karantina dinilai dari `{manusiawi}` — pesan yang SUDAH kami terjemahkan ke "
                "bahasa Indonesia. Kata vendor hilang di situ, B1 tak akan pernah menyala, dan "
                "katalog berhenti belajar TANPA ada yang tahu.")


class TestD_ModelKeyYangGagalTERSIMPAN(unittest.TestCase):
    """B2 (bukti-silang antar-tenant) mustahil dihitung bila nama model yang gagal tak disimpan."""

    def test_production_runs_menyimpan_model_yang_gagal(self):
        src = _baca("src/orchestrator/producer.py")
        self.assertIn(
            "failed_model", src,
            "`production_runs` hanya menyimpan `llm_provider`; nama model yang gagal cuma hidup di "
            "teks bebas — padahal vendor SUDAH menyebutkannya. Tanpa ini bukti-silang antar-tenant "
            "(satu-satunya bukti bebas-biaya) mustahil dihitung.")


class TestE_MematikanModelMENYEBUT_DAMPAKNYA(unittest.TestCase):
    """17-Agu: saklar berpindah tanpa suara; 3 channel tenant berhenti tanpa ada yang tahu."""

    RUTE = "apps/web/src/app/api/admin/catalog/route.ts"
    LAYAR = "apps/web/src/app/admin/(panel)/catalog/page.tsx"

    def test_rute_admin_menghitung_channel_terdampak(self):
        """Tiga versi uji ini sudah gugur, dan sebabnya berbeda-beda:
        (1) `"channels" in src` — lolos dari kata di komentar;
        (2) `from("channels")` di SELURUH berkas — lolos karena rute ini sudah mengueri `channels`
            untuk hitungan pemakaian, jadi menghapus penghitung dampak tetap hijau;
        (3) menuntut kuerinya berada DI DALAM `channelTerdampak` — itu mengikat TEMPAT, bukan
            perilaku. 22-Agu kuerinya sengaja dipindah ke penghitung BERSAMA `channelPemakai`
            karena pertanyaan yang sama tadinya dijawab dua tempat (lapis ganda). Uji yang
            mengikat tempat memaksa lapis ganda itu dipertahankan.

        Yang dikunci sekarang = PERILAKUNYA: ada penghitung yang mengueri `channels` dan bisa
        menyaring hanya yang AKTIF, dan jalur MEMATIKAN benar-benar memakainya dengan saringan itu."""
        src = _baca(self.RUTE)
        i = src.find("async function channelPemakai")
        self.assertGreater(i, 0,
                           "Penghitung channel pemakai tak ada ⇒ mematikan model tak tahu siapa yang "
                           "memakainya, dan itulah persisnya kerusakan 17-Agu.")
        blok = src[i:src.find("\nasync function channelTerdampak", i)]
        self.assertTrue(
            re.search(r'from\("channels"\)', blok),
            "Penghitung tak MENGUERI `channels` — angkanya tak berasal dari kenyataan.")
        self.assertTrue(
            re.search(r'eq\("is_active",\s*true\)', blok),
            "Penghitung tak bisa menyaring channel AKTIF ⇒ channel mati/jeda ikut dihitung dan "
            "angkanya menakut-nakuti admin tanpa sebab.")
        j = src.find("async function channelTerdampak")
        self.assertGreater(j, 0, "jalur MEMATIKAN tak punya pemanggilnya sendiri")
        self.assertTrue(
            re.search(r"channelPemakai\(\s*a,\s*table,\s*key,\s*true\s*\)", src[j:j + 500]),
            "Jalur MEMATIKAN tidak meminta 'hanya channel aktif' ⇒ konfirmasi memakai angka yang salah.")
        k = src.find("perlu_konfirmasi")
        self.assertTrue(
            re.search(r"channelTerdampak\(", src[max(0, k - 900):k + 200]),
            "Penghitung ADA tapi cabang PATCH tak pernah memanggilnya — kode mati, admin tetap "
            "mematikan model tanpa suara.")

    def test_hanya_saat_DIMATIKAN_bukan_saat_dihidupkan(self):
        src = _baca(self.RUTE)
        i = src.find("perlu_konfirmasi")
        self.assertGreater(i, 0, "jawaban perlu_konfirmasi tak ditemukan")
        blok = src[max(0, i - 900):i + 200]
        self.assertIn(
            "clean.is_active === false", blok,
            "Penghitung dampak tak bersyarat pada `is_active === false` ⇒ ikut jalan saat "
            "MENGHIDUPKAN model atau saat mengubah harga (pemborosan + konfirmasi yang membingungkan).")
        self.assertIn(
            "x-konfirmasi-dampak", blok,
            "Tak ada jalan LANJUT setelah konfirmasi ⇒ admin terjebak: model yang benar-benar "
            "dipensiunkan vendor jadi tak bisa dimatikan sama sekali.")

    def test_layar_memakai_ConfirmDialog_yang_SUDAH_ADA(self):
        src = _baca(self.LAYAR)
        self.assertIn("ConfirmDialog", src,
                      "Konfirmasi dampak wajib memakai komponen pustaka yang sudah ada "
                      "(aturan owner: jangan bikin komponen baru).")

    def test_BUKAN_penolakan(self):
        """Vendor bisa mematikan model sewaktu-waktu; admin WAJIB tetap bisa mematikannya.
        Blokir keras = 'kunci tanpa jalur buka' (sudah ditegur owner di PAYMENT §10e-2)."""
        src = _baca(self.RUTE)
        i = src.find("perlu_konfirmasi")
        blok = src[max(0, i - 300):i + 300]
        self.assertIn(
            "status: 200", blok,
            "Jawaban dampak bukan 200 ⇒ layar akan memperlakukannya sebagai GAGAL, dan admin "
            "terjebak saat vendor benar-benar mematikan modelnya.")
        for tolak in ("status: 409", "status: 403", "status: 400"):
            self.assertNotIn(
                tolak, blok,
                f"Mematikan model DITOLAK keras ({tolak}) — 'kunci tanpa jalur buka' "
                "(sudah ditegur owner, PAYMENT §10e-2). Yang diminta: konfirmasi, bukan larangan.")


if __name__ == "__main__":
    unittest.main()
