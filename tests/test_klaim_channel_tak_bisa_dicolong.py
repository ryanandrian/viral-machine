"""KLAIM CHANNEL YOUTUBE — masa coba tak bisa diputar ulang dengan akun baru.

CELAH YANG DIJAGA (ketokan owner 2026-08-20): tenant masa coba BOLEH mendaftar ulang — itu haknya.
Yang tidak boleh: membawa channel YouTube yang sudah terdaftar di akun MesinViral lain, sehingga
masa coba bisa diputar tanpa batas dengan email baru. Kuncinya di INTEGRASI, bukan di pendaftaran.

Sebelum perbaikan ini, DUA indeks unik yang ada di-scope per-tenant (`migrations/0146`) dan
`disconnect()` MENGHAPUS baris pool (`youtube_oauth.py`) — jadi tenant tinggal cabut → daftar akun
baru → sambung lagi. Kuncian yang menumpang di tabel pool ikut terhapus.

Arsitektur & progress: CHANNEL_LOCK_ACTIVATION_PLAN.md §7.

Hermetik: nol jaringan, nol DB. Klien Supabase dipalsukan.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing import youtube_oauth as yo  # noqa: E402

TENANT_A = "aaaaaaaa-0000-0000-0000-000000000001"
TENANT_B = "bbbbbbbb-0000-0000-0000-000000000002"
CHANNEL = "UCsudah_diklaim_tenant_A"


class _Sel:
    """Peniru rantai .select().eq().limit().execute() milik supabase-py."""
    def __init__(self, baris): self._baris = baris; self._filter = {}
    def select(self, *_a, **_k): return self
    def eq(self, k, v): self._filter[k] = v; return self
    def limit(self, *_a): return self
    def maybe_single(self): return self
    def execute(self):
        hasil = [b for b in self._baris if all(b.get(k) == v for k, v in self._filter.items())]
        return type("R", (), {"data": hasil})()


class _Sb:
    def __init__(self, klaim): self._klaim = klaim; self.disisipkan = []
    def table(self, nama):
        assert nama == "youtube_channel_claims", nama
        sel = _Sel(self._klaim)
        sel.insert = lambda baris: type("I", (), {"execute": lambda _s: self.disisipkan.append(baris)})()
        sel.upsert = sel.insert
        return sel


def _pasang(test, klaim, saklar=1):
    """Pasang klien palsu + saklar induk; dibongkar otomatis seusai tes."""
    sb = _Sb(klaim)
    asli_sb = yo._sb
    yo._sb = lambda: sb
    import src.config.app_config as ac
    asli_get = ac.get_int
    ac.get_int = lambda key, default: (saklar if key == "channel_claim_enabled" else asli_get(key, default))
    test.addCleanup(lambda: (setattr(yo, "_sb", asli_sb), setattr(ac, "get_int", asli_get)))
    return sb


class TestA_KecolonganDitutup(unittest.TestCase):
    def test_channel_milik_tenant_lain_DITOLAK(self):
        _pasang(self, [{"yt_channel_id": CHANNEL, "tenant_id": TENANT_A}])
        pemilik = yo.klaim_pemilik_lain(TENANT_B, CHANNEL)
        self.assertEqual(
            pemilik, TENANT_A,
            "Tenant B boleh menyambung channel milik tenant A ⇒ masa coba bisa diputar tanpa batas "
            "dengan email baru. Ini kecolongan yang dijaga tes ini.")

    def test_pemilik_sendiri_TETAP_BOLEH(self):
        """REGRESI TERPENTING: tenant sah mencabut koneksi (barisnya terhapus) lalu menyambung ulang."""
        _pasang(self, [{"yt_channel_id": CHANNEL, "tenant_id": TENANT_A}])
        self.assertIsNone(
            yo.klaim_pemilik_lain(TENANT_A, CHANNEL),
            "Penjaga kebablasan: tenant terkunci dari channelnya SENDIRI setelah cabut-sambung ulang.")

    def test_belum_pernah_diklaim_BOLEH(self):
        _pasang(self, [])
        self.assertIsNone(yo.klaim_pemilik_lain(TENANT_B, "UCbelum_pernah_ada"))

    def test_satu_akun_google_dua_channel_DUA_DUANYA_BOLEH(self):
        """Insiden nyata (PER_CHANNEL_OAUTH_MIGRATION §3b): satu akun Google memuat beberapa channel.
        Terukur 2026-08-20: 4 tenant mengalaminya, satu punya 4 channel. Kunci pada akun Google
        akan memblokir mereka — karena itu kuncinya pada identitas CHANNEL."""
        _pasang(self, [{"yt_channel_id": "UCsatu", "tenant_id": TENANT_A},
                       {"yt_channel_id": "UCdua", "tenant_id": TENANT_A}])
        self.assertIsNone(yo.klaim_pemilik_lain(TENANT_A, "UCsatu"))
        self.assertIsNone(yo.klaim_pemilik_lain(TENANT_A, "UCdua"))

    def test_koneksi_tanpa_identitas_TAK_DISENTUH(self):
        """6 koneksi live tanpa `yt_channel_id` — tak bisa diklaim, jangan sampai ikut ditolak."""
        _pasang(self, [{"yt_channel_id": CHANNEL, "tenant_id": TENANT_A}])
        for kosong in (None, "", "   "):
            self.assertIsNone(yo.klaim_pemilik_lain(TENANT_B, kosong))


class TestB_SaklarInduk(unittest.TestCase):
    """Mandat owner: tiap gerbang bisa dimatikan SEKETIKA tanpa deploy."""

    def test_saklar_mati_penjaga_diam(self):
        _pasang(self, [{"yt_channel_id": CHANNEL, "tenant_id": TENANT_A}], saklar=0)
        self.assertIsNone(
            yo.klaim_pemilik_lain(TENANT_B, CHANNEL),
            "app_config.channel_claim_enabled=0 harus mematikan kuncian total (jaring pengaman).")


class TestC_UrutanDanCaraMenolak(unittest.TestCase):
    """Temuan evaluasi final §7c — dua di antaranya akan jadi bug baru bila salah."""

    def _src(self):
        import inspect
        return inspect.getsource(yo.handle_callback)

    def test_klaim_diperiksa_SEBELUM_dedup_se_tenant(self):
        s = self._src()
        self.assertIn("klaim_pemilik_lain", s, "penjaga tidak dipasang di handle_callback")
        self.assertLess(
            s.index("klaim_pemilik_lain"), s.index("_find_existing_connection"),
            "Klaim harus diperiksa SEBELUM dedup se-tenant — kalau tidak, alur "
            "'sudah terhubung → segarkan token' mendahului penolakan.")

    def test_menolak_TANPA_mencabut_token_ke_google(self):
        """§7c-1: 4 tenant punya beberapa channel di SATU akun Google; mencabut refresh token
        berisiko membatalkan grant lain dan merusak koneksi yang sedang sehat."""
        s = self._src()
        potong = s[s.index("klaim_pemilik_lain"):s.index("_find_existing_connection")]
        self.assertNotIn(
            "_revoke_google_token", potong,
            "Cabang penolakan mencabut token ke Google — berisiko mematikan koneksi sehat "
            "tenant lain dari akun Google yang sama.")

    def test_klaim_dicatat_SESUDAH_token_tersimpan(self):
        """§7b-5: klaim sebelum simpan → koneksi gagal meninggalkan klaim ⇒ tenant terkunci
        dari channelnya sendiri oleh bug kita."""
        s = self._src()
        self.assertIn("klaim_catat", s, "klaim tidak pernah dicatat ⇒ kuncian kosong")
        # Kaidah sebenarnya: TIDAK ADA satu pun pencatatan klaim yang mendahului penyimpanan token.
        # (Bukan "sebelum satu baris tertentu" — ada dua cabang simpan: koneksi baru & penyegaran.)
        simpan = [i for i in range(len(s)) if s.startswith("_store_tokens(", i)]
        catat = [i for i in range(len(s)) if s.startswith("klaim_catat(", i)]
        self.assertTrue(simpan and catat)
        for c in catat:
            self.assertTrue(
                any(t < c for t in simpan),
                "Ada pencatatan klaim yang mendahului SEMUA penyimpanan token ⇒ koneksi yang gagal "
                "meninggalkan klaim, dan tenant terkunci dari channelnya sendiri oleh bug kita.")


class TestD_MigrasiTakMenghidupkanLubang(unittest.TestCase):
    """Klaim WAJIB bertahan walau koneksi dicabut / channel dihapus / tenant dihapus."""

    def setUp(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "migrations", "0203_klaim_channel_youtube.sql")
        self.sql = io.open(p, encoding="utf-8").read().lower()
        self.badan = self.sql[self.sql.index("create table if not exists youtube_channel_claims"):]
        self.badan = self.badan[:self.badan.index(");")]

    def test_tanpa_foreign_key_dan_tanpa_cascade(self):
        for terlarang in ("references", "cascade"):
            self.assertNotIn(
                terlarang, self.badan,
                f"Tabel klaim memakai '{terlarang}' ⇒ klaim ikut terhapus saat koneksi/channel/tenant "
                "dihapus, dan kuncian lenyap. Inilah lubang yang tabel ini ada untuk menutup.")

    def test_kunci_primer_pada_identitas_channel(self):
        self.assertIn("yt_channel_id", self.badan)
        self.assertIn("primary key", self.badan,
                      "Tanpa kunci primer, dua akun yang menyambung di detik yang sama sama-sama lolos.")

    def test_rls_nyala_dan_hak_tenant_dicabut(self):
        self.assertIn("enable row level security", self.sql)
        self.assertIn("revoke all on table youtube_channel_claims from anon, authenticated", self.sql)

    def test_isi_mundur_gagal_berisik_bila_bentrok(self):
        self.assertIn("raise exception", self.sql,
                      "Migrasi harus MATI bila satu channel dipakai >1 tenant — bukan memilih pemenang.")


class TestE_HapusAkunBukanJalanPintas(unittest.TestCase):
    """TABRAKAN PDP ⟷ KUNCIAN (ditangkap penjaga `test_purge_pdp_lengkap` saat dibangun).

    Hak hapus data (UU PDP) menuntut pengenal tenant dibuang. Kuncian menuntut klaim BERTAHAN.
    Kalau klaim ikut dihapus, penyalahguna dapat jalan pintas paling mudah:
    **hapus akun → daftar baru → sambung channel yang sama.**
    Jalan tengahnya (pola yang SUDAH dipakai `tenant_configs`/`feedback_submissions`):
    baris disimpan, `tenant_id` dianonimkan.
    """

    def test_purge_MENGANONIMKAN_bukan_menghapus(self):
        import inspect
        from src.billing import renewal
        s = inspect.getsource(renewal._hard_delete_tenant)
        self.assertIn('youtube_channel_claims', s, "purge tenant tak menyentuh klaim sama sekali")
        potong = s[s.index('youtube_channel_claims') - 200:s.index('youtube_channel_claims') + 200]
        self.assertIn("update(", potong,
                      "Klaim harus DI-UPDATE (dianonimkan), bukan dihapus.")
        self.assertNotIn(".delete()", potong,
                         "Klaim DIHAPUS saat akun dihapus ⇒ kuncian lenyap lewat jalur termudah "
                         "penyalahguna: hapus akun → daftar baru → sambung channel yang sama.")

    def test_klaim_terdaftar_sebagai_DISIMPAN(self):
        from src.billing.renewal import _KEEP_TABLES, _PURGE_TABLES
        self.assertIn("youtube_channel_claims", _KEEP_TABLES)
        self.assertNotIn("youtube_channel_claims", _PURGE_TABLES)

    def test_pemilik_yang_akunnya_dihapus_TETAP_mengunci(self):
        from src.billing.renewal import TENANT_DIHAPUS
        _pasang(self, [{"yt_channel_id": CHANNEL, "tenant_id": TENANT_DIHAPUS}])
        self.assertEqual(
            yo.klaim_pemilik_lain(TENANT_B, CHANNEL), TENANT_DIHAPUS,
            "Channel milik akun yang sudah dihapus harus TETAP terkunci sampai admin melepasnya.")


if __name__ == "__main__":
    unittest.main()
