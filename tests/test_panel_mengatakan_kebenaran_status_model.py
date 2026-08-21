"""PANEL WAJIB MENGATAKAN KEBENARAN TENTANG STATUS MODEL — G1–G5.

Pemicu (22-Agu, owner): *"gemini-2.5-flash, MENGAPA TIDAK ADA INDIKATOR UNTUK YANG MATI?"*

Keadaan yang membuat pertanyaan itu lahir — semuanya terukur:
  · `gemini-2.5-flash` dinyalakan kembali; lencana panel berbunyi **"✓ Teruji"** …dari **6 Juli**,
    sementara model itu **terbukti mati di vendor 18-Agu** (3 kegagalan `model_unavailable`),
    dan **Abyss ID (channel AKTIF)** memakainya.
  · Jejak karantina (`unavailable_since`/`unavailable_reason`) SUDAH dikirim rute ke layar
    (`select("*")`) tapi layar **nol kali** menampilkannya = data dikumpulkan tapi tak dipakai.
  · Lebih buruk: B5 (dipasang beberapa jam sebelumnya) MEMBERSIHKAN jejak itu saat model
    dinyalakan ⇒ penghapus bukti dibangun SEBELUM penampil bukti. Cacat rancangan saya.
  · Tabel AI Models tak menyebut berapa channel memakai sebuah model; admin baru tahu pada detik
    ia mematikannya.

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

RUTE  = "apps/web/src/app/api/admin/catalog/route.ts"
LAYAR = "apps/web/src/app/admin/(panel)/catalog/page.tsx"
MIGR  = "migrations/0208_gerbang_aktif_wajib_terbukti.sql"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _tanpa_komentar_sql(rel: str) -> str:
    return "\n".join(l for l in _baca(rel).splitlines() if not l.lstrip().startswith("--"))


class TestG1_TabelMenyebutBerapaChannelMemakai(unittest.TestCase):
    """Admin baru tahu dampaknya pada detik ia mematikan model. Angka itu bisa diketahui SEBELUMNYA."""

    def test_rute_mengirim_pemakaian_per_model(self):
        rute = _baca(RUTE)
        # Jangkar = Promise.all DI DALAM GET. Versi pertama memotong "GET s/d export berikutnya",
        # dan potongan itu ikut memuat `channelPemakai`/`channelTerdampak` yang juga mengueri
        # `channels` ⇒ mencabut kueri GET tetap lolos. Sabotase membuktikannya.
        i = rute.find("export async function GET")
        self.assertGreater(i, 0)
        j = rute.find("await Promise.all([", i)
        self.assertGreater(j, i, "GET tak lagi memuat satu blok Promise.all")
        promise = rute[j:rute.find("]);", j)]
        self.assertTrue(
            re.search(r'from\("channels"\)', promise),
            "GET katalog tak membaca `channels` di blok muatannya ⇒ tabel model mustahil menyebut "
            "pemakaian tanpa kueri tambahan per baris.")
        self.assertIn("catalog_pemakaian", rute,
                      "hitungan pemakaian tak dikirim ke layar dengan nama yang bisa dibaca")

    def test_layar_menampilkannya_di_tabel_model(self):
        layar = _baca(LAYAR)
        self.assertIn("catalog_pemakaian", layar,
                      "layar tak menerima hitungan pemakaian ⇒ kolomnya mustahil ada")
        i = layar.find('{tab === "models" && (')
        self.assertGreater(i, 0)
        blok = layar[i:layar.find('{tab === "fonts"', i)]
        self.assertTrue(
            re.search(r"pemakaiModel|catalog_pemakaian", blok),
            "tabel AI Models tak menampilkan pemakaian — admin tetap baru tahu saat mematikan")

    def test_nol_pemakai_dibedakan_dari_banyak(self):
        """Angka 0 dan 4 harus terlihat BEDA, kalau tidak kolomnya tak menolong keputusan."""
        layar = _baca(LAYAR)
        i = layar.find("const pemakaiModel")
        self.assertGreater(i, 0, "helper pemakaian tak ada")
        blok = layar[i:i + 900]
        self.assertTrue(
            re.search(r"badge-(warning|default|error)", blok),
            "pemakaian ditampilkan tanpa pembeda visual antara 0 dan >0")


class TestG2_JejakKarantinaDITAMPILKAN(unittest.TestCase):
    """Kolom jejak SUDAH dikirim rute ke layar sejak 21-Agu, dan layar nol kali menampilkannya.
    Data yang dikumpulkan tapi tidak digunakan = BUG (definisi owner)."""

    def test_layar_menampilkan_jejak_karantina(self):
        layar = _baca(LAYAR)
        self.assertIn(
            "unavailable_since", layar,
            "Jejak karantina dikirim ke layar tapi tak pernah ditampilkan ⇒ admin menyalakan model "
            "yang terbukti mati tanpa peringatan apa pun.")

    def test_alasannya_ikut_terbaca(self):
        layar = _baca(LAYAR)
        self.assertIn("unavailable_reason", layar,
                      "alasan karantina (pesan vendor apa adanya) tak pernah diperlihatkan ⇒ admin "
                      "tak bisa menilai apakah model itu layak dicoba lagi")


class TestG3_LencanaUjiMenYEBUT_UMURNYA(unittest.TestCase):
    """"✓ Teruji" tanpa tanggal MENYESATKAN: uji 6 Juli dan uji hari ini terlihat sama, padahal
    yang pertama tak membuktikan apa pun tentang keadaan sekarang (kasus `gemini-2.5-flash`)."""

    def test_umur_uji_dihitung_dan_ditampilkan(self):
        layar = _baca(LAYAR)
        # Tuntut DEFINISI-nya, bukan sekadar kemunculan kata: sabotase me-rename definisinya dan
        # pemanggil lama tetap menyebut namanya, sehingga pencarian kata tetap hijau.
        self.assertTrue(
            re.search(r"const\s+umurUji\s*=", layar),
            "Penghitung umur uji tak ada ⇒ lencana '✓ Teruji' dari 6 Juli terlihat sama "
            "meyakinkannya dengan uji hari ini.")
        # Jangkar = KODE lencananya, bukan kemunculan pertama kata "LULUS" (yang ada di komentar).
        # Cacat jangkar-jendela ini sudah tertangkap tiga kali hari ini; jangan diulang.
        i = layar.find('au.startsWith("LULUS")')
        self.assertGreater(i, 0, "lencana status uji tak ditemukan")
        blok = layar[max(0, i - 400):i + 900]
        self.assertTrue(
            re.search(r"umurUji|uu\.hari|uu\.basi", blok),
            "lencana status uji tak memakai umur uji — angkanya dihitung tapi tak dipakai")

    def test_uji_BASI_ditandai_berbeda(self):
        layar = _baca(LAYAR)
        # Kata `basi` juga ada di DEFINISI penghitung, jadi mencarinya di sekitar definisi selalu
        # hijau — sabotase membuktikannya. Yang dikunci: lencananya MERENDER penanda itu, dan
        # warnanya berubah.
        i = layar.find('au.startsWith("LULUS")')
        self.assertGreater(i, 0, "lencana status uji tak ditemukan")
        blok = layar[i:i + 900]
        self.assertTrue(
            re.search(r'id="BASI"|id="basi"|id="Kedaluwarsa"', blok),
            "lencana tak pernah MENAMPILKAN penanda uji basi ⇒ admin tetap ditenangkan lencana "
            "hijau padahal buktinya usang")
        self.assertTrue(
            re.search(r"uu\.basi\s*\?\s*\"badge-warning\"", blok.replace("'", '"')),
            "warna lencana tak berubah saat uji basi ⇒ perbedaannya tak terlihat sekilas")


class TestG4_MenyalakanWAJIB_TERBUKTI(unittest.TestCase):
    """Janji dokumen arsitektur §8: "Model aktif = pasti jalan → ditegakkan tombol Uji". Sampai
    22-Agu janji itu bersandar DISIPLIN, bukan mesin: tak ada yang mencegah model belum-teruji
    dinyalakan. Ditegakkan di DB, bukan di panel — karena jalur yang MEMUTARI panel sudah terbukti
    dipakai (mesin suara Gemini dulu dinyalakan lewat skrip)."""

    def test_migrasinya_ada(self):
        self.assertTrue(os.path.exists(os.path.join(AKAR, MIGR)), "gerbang belum dibangun")

    def test_syarat_audit_LULUS(self):
        src = _tanpa_komentar_sql(MIGR)
        self.assertIn("cost_hint", src, "gerbang tak membaca stempel hasil uji")
        self.assertTrue(re.search(r"LULUS", src), "gerbang tak menuntut hasil uji LULUS")

    def test_audit_wajib_LEBIH_BARU_dari_bukti_kematian(self):
        """Inti kasus `gemini-2.5-flash`: auditnya MEMANG LULUS — tapi dari 6 Juli, sementara model
        terbukti mati 18-Agu. Audit lama tak membuktikan apa pun tentang keadaan sekarang."""
        src = _tanpa_komentar_sql(MIGR)
        self.assertIn(
            "unavailable_since", src,
            "Gerbang hanya menuntut 'pernah LULUS' ⇒ uji dari enam pekan sebelum model mati tetap "
            "meloloskan penyalaan. Audit wajib LEBIH BARU dari bukti kematiannya.")

    def test_HANYA_transisi_menjadi_aktif(self):
        src = _tanpa_komentar_sql(MIGR)
        self.assertTrue(
            re.search(r"not\s+coalesce\(old\.is_active", src, re.I),
            "gerbang tak dibatasi pada TRANSISI ⇒ menyunting harga model aktif bisa ikut ditolak")
        self.assertTrue(
            re.search(r"(coalesce\(\s*)?new\.is_active\s*(,\s*false\s*\))?\s*(=|is)\s*true", src, re.I),
            "gerbang tak bersyarat pada keadaan BARU aktif ⇒ MEMATIKAN pun bisa tertahan")

    def test_trigger_satu_tabel_TIDAK_pakai_case_new(self):
        """Pelajaran 0206: `case tg_table_name … then new.<kolom>` menggagalkan tabel lain. Gerbang
        ini hanya untuk `ai_models`, jadi `new.model_key` sah — tapi polanya dikunci agar tak
        berkembang jadi multi-tabel tanpa sadar."""
        src = _tanpa_komentar_sql(MIGR)
        self.assertNotIn("tg_table_name", src,
                         "gerbang ini khusus satu tabel; memakai `tg_table_name` mengundang cacat "
                         "'record new has no field' yang sudah pernah terjadi")

    def test_rute_menerjemahkan_penolakan_jadi_kode(self):
        self.assertIn("belum_terbukti", _baca(RUTE),
                      "penolakan gerbang tak diterjemahkan jadi kode ⇒ admin melihat pesan mentah DB")

    def test_layar_menerjemahkan_ke_kalimat_dwibahasa(self):
        layar = _baca(LAYAR)
        self.assertIn("belum_terbukti", layar, "layar tak menerjemahkan penolakan")
        i = layar.find('case "belum_terbukti"')
        self.assertGreater(i, 0, "penerjemah kode itu tak ada di daftar pesan")
        self.assertIn("<Bi ", layar[i:i + 700], "pesan penolakan tak dwibahasa")


class TestG5_PembersihanJejakTIDAK_MENGHAPUS_BUKTI(unittest.TestCase):
    """CACAT RANCANGAN SAYA (B5, 22-Agu): jejak karantina dibersihkan hanya karena model dinyalakan.
    Akibatnya bukti kematian hilang tanpa ada uji ulang yang membuktikan model hidup lagi — dan
    itu terjadi pada `gemini-2.5-flash` beberapa jam setelah B5 dipasang."""

    def test_pembersihan_menuntut_uji_yang_LEBIH_BARU(self):
        rute = _baca(RUTE)
        i = rute.find("unavailable_since = null")
        if i < 0:
            i = rute.find("clean.unavailable_since")
        self.assertGreater(i, 0, "jalur pembersihan jejak tak ditemukan")
        blok = rute[max(0, i - 1400):i + 400]
        # `"cost_hint" in blok` LOLOS ketika pembacaan barisnya diganti `const baris = null` —
        # kata itu masih ada di pembacaan properti. Yang dikunci: barisnya sungguh DIBACA dari DB.
        self.assertTrue(
            re.search(r'from\("ai_models"\)[\s\S]{0,200}select\("cost_hint', blok),
            "Jejak karantina dibersihkan TANPA membaca hasil uji dari DB ⇒ bukti kematian hilang "
            "hanya karena admin menyalakan model, dan tak seorang pun bisa tahu model itu pernah mati.")
        self.assertTrue(
            re.search(r"ujiLebihBaru|tglUji", blok),
            "tak ada perbandingan umur uji vs jejak kematian ⇒ pembersihan tetap membuta")


if __name__ == "__main__":
    unittest.main()
