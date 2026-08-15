"""KATALOG NICHE TIDAK BOLEH BISA DITULIS DARI LUAR.

LUBANG YANG DIJAGA (dibuktikan 2026-08-15, `SISA_KERJA [B32]` T2 · migr 0199)
Dengan **kunci publik yang dipegang setiap browser**, TANPA login sama sekali, tabel `niches`,
`moods`, dan `music_library` bisa **DITULIS**. Pembuktiannya memakai tulisan yang tidak mengubah
apa pun — menulis nilai yang SAMA PERSIS dengan isinya — lalu melihat server mengembalikan barisnya:

    UPDATE niches SET name = <nilai yang memang sudah ada> WHERE niche_id = 'sunnah_harian'   → 1 baris

Artinya siapa pun bisa menulis ulang DNA niche mana pun, atau mematikan katalognya.
Sebabnya: RLS ketiganya sengaja tak pernah dinyalakan (migr 0071) dan izin tulis peran publik tak
pernah dicabut. Sapuan 19 tabel: **hanya ketiga tabel katalog ini** yang terbuka — seluruh data tenant
sudah terkunci rapat.

KENAPA UJI INI MEMAKAI KUNCI PUBLIK SUNGGUHAN, BUKAN TIRUAN:
yang diuji adalah **izin di database**, dan itu hanya nyata bila ditanya kepada database dengan kunci
yang sama seperti penyerang. Tiruan hanya menguji kode kita sendiri — persis kelas "uji hijau di
sekeliling bug" yang membuat 880 uji lolos saat rem lumpuh ([B29]).

⚠️ Uji ini TIDAK PERNAH mengubah data: tulisannya bernilai identik dengan isi yang sudah ada, dan
sisipannya sengaja kosong (ditolak batasan kolom sebelum baris mana pun lahir).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FE = os.path.join(AKAR, "apps", "web", ".env.local")
TABEL_KATALOG = ("niches", "moods", "music_library")


def _klien_publik():
    """Klien dengan kunci PUBLIK — persis yang dipegang browser siapa pun."""
    from dotenv import dotenv_values
    if not os.path.exists(ENV_FE):
        raise AssertionError(
            f"{ENV_FE} tidak ada — uji ini WAJIB bisa bertanya ke database dengan kunci publik. "
            f"Sengaja GAGAL, bukan dilewati: penjaga yang melewatkan dirinya sendiri = penjaga lapuk."
        )
    e = dotenv_values(ENV_FE)
    url, key = e.get("NEXT_PUBLIC_SUPABASE_URL"), e.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise AssertionError("NEXT_PUBLIC_SUPABASE_URL/ANON_KEY tak lengkap di .env.local")
    from supabase import create_client
    return create_client(url, key)


class TestTulisPublikTertutup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = _klien_publik()

    def test_menyisipkan_baris_ditolak(self):
        """Sisipan KOSONG: ditolak izin → aman · ditolak batasan kolom → izinnya ADA = lubang."""
        for tabel in TABEL_KATALOG:
            with self.subTest(tabel=tabel):
                try:
                    self.sb.table(tabel).insert({}).execute()
                    self.fail(f"`{tabel}`: sisipan publik MASUK tanpa galat — lubang menganga")
                except Exception as ex:
                    m = str(ex).lower()
                    izin_ada = ("null value" in m or "not-null" in m or "23502" in m
                                or "violates check" in m or "duplicate key" in m)
                    self.assertFalse(
                        izin_ada,
                        f"`{tabel}`: sisipan ditolak oleh BATASAN KOLOM, bukan oleh izin — artinya "
                        f"peran publik masih boleh menulis. Galat: {str(ex)[:200]}")

    def test_mengubah_baris_yang_ada_ditolak(self):
        """Uji paling menentukan — dan tak mengubah apa pun (menulis nilai yang sama persis)."""
        r = self.sb.table("niches").select("niche_id,name").eq("is_active", True).limit(1).execute()
        self.assertTrue(r.data, "tak ada satu pun niche terbaca publik — periksa policy BACA")
        niche = r.data[0]
        # DUA bentuk penolakan yang sama-sama sah, tergantung lapis mana yang menahan:
        #   • izin tabel dicabut  → server melempar 42501 "permission denied"
        #   • policy RLS menyaring → tak melempar, tapi NOL baris kena
        # Keduanya = aman. Yang GAGAL hanya bila baris benar-benar kembali (artinya tulisan diterima).
        try:
            hasil = self.sb.table("niches").update({"name": niche["name"]}).eq("niche_id", niche["niche_id"]).execute()
        except Exception as ex:
            m = str(ex).lower()
            self.assertTrue("permission denied" in m or "42501" in m or "row-level security" in m,
                            f"`niches`: galat tak dikenal saat menulis — periksa: {str(ex)[:200]}")
            return
        self.assertEqual(
            len(hasil.data or []), 0,
            f"`niches`: perubahan dari kunci publik DITERIMA pada `{niche['niche_id']}` — "
            f"siapa pun bisa menulis ulang DNA niche")


class TestBacaYangSahTetapJalan(unittest.TestCase):
    """Mengunci tulis TIDAK BOLEH mematikan layar. Predikat di bawah = yang dipakai 4 titik baca FE."""

    @classmethod
    def setUpClass(cls):
        cls.sb = _klien_publik()

    def test_katalog_niche_publik_tetap_terbaca(self):
        r = self.sb.table("niches").select("niche_id,access_type,exclusive_to,is_active").eq("is_active", True).execute()
        self.assertGreater(len(r.data or []), 0,
                           "nol niche terbaca → layar Pustaka Niche & pemilih niche channel akan KOSONG")

    def test_dna_privat_tenant_tak_ikut_terkirim(self):
        """Yang privat milik orang lain berhenti sampai ke browser — dijaga DB, bukan disaring layar."""
        r = self.sb.table("niches").select("niche_id,access_type,exclusive_to").execute()
        bocor = [x["niche_id"] for x in (r.data or []) if x.get("exclusive_to")]
        self.assertEqual(bocor, [],
                         f"DNA niche privat tenant masih terkirim ke pembaca tanpa sesi: {bocor}")

    def test_katalog_musik_dan_mood_tak_terbuka_tanpa_sesi(self):
        """Editor DNA membacanya SESUDAH login; tanpa sesi tak ada alasan katalog ini terbaca."""
        for tabel in ("moods", "music_library"):
            with self.subTest(tabel=tabel):
                r = self.sb.table(tabel).select("*", count="exact", head=True).execute()
                self.assertEqual(r.count or 0, 0,
                                 f"`{tabel}` masih terbaca tanpa sesi ({r.count} baris)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
