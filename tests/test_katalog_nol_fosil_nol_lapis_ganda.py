"""FOSIL & LAPIS GANDA di rantai katalog AI — dibereskan, bukan dilabeli "batas".

Definisi owner (mengikat): **BUG** = "sesuatu yang rusak, atau berpotensi merusak, termasuk FOSIL,
atau objek pada screen yang tidak berfungsi atau tidak terwiring, DATA YANG DIKUMPULKAN TAPI TIDAK
DIGUNAKAN, dan sebagainya."

Empat hal yang sempat saya laporkan sebagai "batas" / "menunggu keputusan" — padahal menurut
definisi di atas ketiga pertama adalah BUG dan tak butuh keputusan siapa pun:

  F1 `tts_profiles.has_word_timeframe` (duplikat `tts_class`, nilainya 1:1) ·
     `voice_catalog.pace_sample_n` + `pace_updated_at` (0 dari 44 baris terisi).
     Ketiganya: NOL pembaca & NOL penulis di seluruh src/ dan apps/web/.
     `has_word_timeframe` bukan cuma mati — ia SUMBER KEBENARAN KEDUA untuk hal yang sama dengan
     `tts_class`; mengubah satu tanpa yang lain = kerusakan yang menunggu terjadi.
  F2 `ai_providers.request_param_schema` DIBACA mesin saat membangun penyedia naskah, tapi tak ada
     jalur mengisinya dari panel ⇒ objek terwiring separuh.
  F3 "channel yang memakai baris katalog ini" dihitung di DUA tempat (`refGuard` untuk hapus,
     `channelTerdampak` untuk matikan) — lapis ganda buatan sesi 21-Agu.

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
MIGR  = "migrations/0207_buang_fosil_katalog.sql"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _tanpa_komentar_sql(rel: str) -> str:
    return "\n".join(l for l in _baca(rel).splitlines() if not l.lstrip().startswith("--"))


class TestF1_FosilKolomDibuang(unittest.TestCase):
    """Kolom tanpa pembaca DAN tanpa penulis = data yang dikumpulkan tapi tidak digunakan = BUG."""

    FOSIL = ("has_word_timeframe", "pace_sample_n", "pace_updated_at")

    def test_migrasinya_ada(self):
        self.assertTrue(os.path.exists(os.path.join(AKAR, MIGR)),
                        "fosil kolom katalog belum dibuang")

    def test_ketiganya_dibuang(self):
        src = _tanpa_komentar_sql(MIGR).lower()
        for k in self.FOSIL:
            self.assertTrue(
                re.search(rf"drop column if exists {k}\b", src),
                f"`{k}` tidak dibuang — ia tetap jadi data yang dikumpulkan tapi tak dipakai, "
                "dan sesi berikutnya akan menyangkanya bermakna.")

    def test_TIDAK_menyentuh_kolom_yang_HIDUP(self):
        """Pagar: migrasi pembuang fosil HARAM menyenggol kolom yang dipakai mesin."""
        src = _tanpa_komentar_sql(MIGR)
        dibuang = set(re.findall(r"drop column if exists ([a-z_]+)", src, re.I))
        self.assertEqual(
            set(self.FOSIL), dibuang,
            f"migrasi membuang kolom di luar daftar fosil: {dibuang - set(self.FOSIL)}")
        for hidup in ("tts_class", "delivery_wps", "adapter", "preview_url", "pace_locked",
                      "is_active", "pricing", "model_id", "component"):
            self.assertNotIn(
                f"drop column if exists {hidup}", src.lower(),
                f"`{hidup}` DIPAKAI mesin — membuangnya merusak produksi")

    def test_kode_tak_lagi_menyebut_fosil_itu(self):
        """Kalau kolomnya dibuang tapi kode masih menyebutnya, tulis/baca akan gagal."""
        for rel in (RUTE, LAYAR):
            src = _baca(rel)
            for k in self.FOSIL:
                self.assertNotIn(k, src, f"`{rel}` masih menyebut kolom fosil `{k}`")


class TestF2_KolomHidupPunyaJalurISI(unittest.TestCase):
    """`request_param_schema` dibaca mesin saat membangun penyedia naskah. Kalau admin tak bisa
    mengisinya, ia objek terwiring separuh — dan penyedia yang menuntut parameter khusus mustahil
    disiapkan dari panel."""

    def test_ada_di_form_penyedia(self):
        blok_awal = _baca(LAYAR).find("const ADD_FIELDS:")
        blok = _baca(LAYAR)[blok_awal:]
        i = blok.find('providers: { table: "ai_providers"')
        self.assertGreater(i, 0)
        potong = blok[i:blok.find("] },", i) + 4]
        self.assertIn(
            "request_param_schema", potong,
            "`request_param_schema` DIBACA mesin tapi tak ada jalur mengisinya dari panel ⇒ "
            "penyedia yang menuntut parameter khusus mustahil disiapkan admin.")

    def test_punya_label_dan_arahan_dwibahasa(self):
        layar = _baca(LAYAR)
        i = layar.find("const FIELD_META:")
        j = layar.find("  providers: {", i)
        sub = layar[j:layar.find("\n  },", j)]
        m = re.search(r"request_param_schema:\s*\{", sub)
        self.assertTrue(m, "isian itu tak punya label manusiawi")
        # isi entri diambil dengan penghitung kedalaman (arahan boleh memuat contoh JSON)
        k = sub.find("{", m.start()); d, e = 0, k
        while e < len(sub):
            if sub[e] == "{": d += 1
            elif sub[e] == "}":
                d -= 1
                if d == 0: break
            e += 1
        isi = sub[k + 1:e]
        for bahasa in ("help_id", "help_en"):
            self.assertTrue(re.search(rf"(?<![a-z_]){bahasa}:\s*['\"]", isi),
                            f"arahan `{bahasa}` kosong — layar admin wajib dwibahasa")

    def test_boleh_ditulis_API(self):
        m = re.search(r"\bai_providers:\s*\{[^}]*?cols:\s*\[(.*?)\]",
                      _baca(RUTE), re.S)
        self.assertIn("request_param_schema", m.group(1),
                      "kolom di form tapi dibuang API = kelas buang-senyap yang baru")

    def test_divalidasi_sebagai_JSON(self):
        """Ia jsonb. Tanpa penguraian, teks bebas tersimpan sebagai string mentah dan mesin
        membacanya sebagai objek kosong — gagal SENYAP."""
        m = re.search(r"const JSONB_COLS[^;]*?ai_providers:\s*\[(.*?)\]", _baca(RUTE), re.S)
        self.assertTrue(m, "`ai_providers` tak punya daftar kolom jsonb")
        self.assertIn("request_param_schema", m.group(1),
                      "isian jsonb tak diurai ⇒ tersimpan sebagai string mentah, mesin membacanya "
                      "sebagai kosong, dan admin tak pernah diberi tahu")


class TestF3_SatuSumberKebenaranPemakaiChannel(unittest.TestCase):
    """"Channel yang memakai baris katalog ini" dihitung di DUA tempat sejak 21-Agu. Dua sumber
    kebenaran untuk satu pertanyaan = kelas cacat yang owner larang (lapis ganda)."""

    def test_hanya_SATU_fungsi_yang_menghitungnya(self):
        rute = _baca(RUTE)
        i = rute.find("async function refGuard")
        self.assertGreater(i, 0)
        badan = rute[i:rute.find("\nexport async function DELETE", i)]
        self.assertIn(
            "channelPemakai", badan,
            "`refGuard` masih menghitung pemakai channel sendiri, terpisah dari penghitung yang "
            "dipakai jalur mematikan ⇒ dua sumber kebenaran untuk satu pertanyaan.")

    def test_penghitung_bersama_itu_ada_dan_dipakai_KEDUA_jalur(self):
        rute = _baca(RUTE)
        self.assertTrue(re.search(r"async function channelPemakai", rute),
                        "penghitung bersama belum dibuat")
        i = rute.find("async function channelTerdampak")
        self.assertGreater(i, 0)
        blok = rute[i:rute.find("\nexport async function PATCH", i)]
        self.assertIn("channelPemakai", blok,
                      "jalur MEMATIKAN tak memakai penghitung bersama ⇒ lapis ganda tetap ada")

    def test_perilaku_HAPUS_tidak_melunak(self):
        """REGRESI paling berbahaya dari penyatuan ini: kalau `refGuard` berhenti menahan, baris
        katalog yang masih dipakai channel bisa TERHAPUS dan channel tenant rusak permanen."""
        rute = _baca(RUTE)
        i = rute.find("async function refGuard")
        badan = rute[i:rute.find("\nexport async function DELETE", i)]
        for tabel in ("ai_models", "ai_providers", "content_languages", "tts_profiles", "fonts", "moods"):
            self.assertIn(f'table === "{tabel}"', badan,
                          f"penjaga hapus untuk `{tabel}` hilang saat penyatuan")
        self.assertTrue(
            re.search(r"nonaktifkan saja, jangan hapus", badan),
            "pesan penolakan hapus hilang — admin tak lagi diberi tahu alasannya")

        # Sabotase membuktikan versi pertama uji ini PALSU: mengganti hitungan menjadi `const n = 0`
        # membuat penjaga jadi KODE MATI (hapus selalu lolos) sementara cabang & pesannya tetap ada.
        # Yang dikunci sekarang: setiap cabang berbasis-channel benar-benar MEMANGGIL penghitungnya.
        for tabel in ("ai_models", "ai_providers", "content_languages", "tts_profiles", "voice_catalog"):
            i = badan.find(f'table === "{tabel}"')
            self.assertGreater(i, 0)
            cabang = badan[i:i + 420]
            self.assertIn(
                "await pemakaiChannel()", cabang,
                f"cabang `{tabel}` tidak memanggil penghitung pemakai ⇒ penjaganya KODE MATI dan "
                "baris katalog yang masih dipakai channel bisa TERHAPUS.")
        self.assertNotIn(
            "const n = 0", badan,
            "ada hitungan pemakai yang dipatok nol ⇒ penjaga hapus jadi hiasan")

    def test_mematikan_tetap_menyaring_channel_AKTIF(self):
        """Beda sah antara dua jalur: MEMATIKAN peduli channel aktif saja; MENGHAPUS peduli semua
        channel. Penyatuan haram menghapus perbedaan itu."""
        rute = _baca(RUTE)
        # Versi pertama uji ini LOLOS-LEMAH: kata `hanyaAktif` ada di DEFINISI fungsi, jadi mencabut
        # argumen `true` di pemanggilnya tetap hijau. Yang dikunci: pemanggil jalur MEMATIKAN.
        i = rute.find("async function channelTerdampak")
        self.assertGreater(i, 0, "jalur mematikan tak punya pemanggilnya sendiri")
        blok = rute[i:i + 500]
        self.assertTrue(
            re.search(r"channelPemakai\(\s*a,\s*table,\s*key,\s*true\s*\)", blok),
            "Jalur MEMATIKAN tidak meminta 'hanya channel aktif' ⇒ konfirmasi ikut menghitung "
            "channel yang sedang jeda/mati, dan angkanya menakut-nakuti admin tanpa sebab.")
        self.assertTrue(
            re.search(r"hanyaAktif\s*=\s*false", rute),
            "penghitung bersama tak lagi berbawaan 'semua channel' ⇒ jalur HAPUS bisa melewatkan "
            "channel yang jeda, lalu meloloskan hapus yang merusak.")


class TestF5_SuaraYangDIPAKAI_TakBisaTerhapus(unittest.TestCase):
    """BUG yang ditemukan 22-Agu saat menyatukan penghitung: `voice_catalog` ADA di `DELETABLE`
    tapi `refGuard` tak punya cabang untuknya. ⇒ karakter suara yang sedang dipakai channel tenant
    BISA DIHAPUS, dan channel itu langsung menggantung — tenant kehilangan suaranya tanpa
    peringatan apa pun. Terukur saat ditemukan: 6 channel memakai suara, 3 di antaranya AKTIF.

    Pola yang benar sudah ada di tabel lain: tolak dengan alasan, sarankan nonaktifkan."""

    def test_refGuard_menahan_hapus_suara_yang_dipakai(self):
        rute = _baca(RUTE)
        i = rute.find("async function refGuard")
        self.assertGreater(i, 0)
        badan = rute[i:rute.find("\nexport async function DELETE", i)]
        self.assertIn(
            'table === "voice_catalog"', badan,
            "`voice_catalog` boleh dihapus (ada di DELETABLE) tapi TAK ADA penjaganya di refGuard ⇒ "
            "suara yang sedang dipakai channel tenant bisa terhapus dan channel itu menggantung.")

    def test_penolakannya_MENYARANKAN_nonaktifkan(self):
        """Menolak tanpa memberi jalan = admin terjebak. Pola yang sudah ada: sarankan nonaktifkan."""
        rute = _baca(RUTE)
        i = rute.find("async function refGuard")
        badan = rute[i:rute.find("\nexport async function DELETE", i)]
        j = badan.find('table === "voice_catalog"')
        self.assertGreater(j, 0)
        self.assertIn(
            "nonaktifkan saja", badan[j:j + 400],
            "penolakan hapus suara tak menyarankan jalan keluar (nonaktifkan) ⇒ admin terjebak")

    def test_setiap_tabel_DELETABLE_punya_penjaga(self):
        """Penjaga KELAS: tabel yang boleh dihapus TANPA penjaga = kerusakan menunggu terjadi.
        Inilah cacat yang lolos berbulan-bulan untuk `voice_catalog`."""
        rute = _baca(RUTE)
        m = re.search(r"const DELETABLE = new Set\(\[(.*?)\]\)", rute, re.S)
        self.assertTrue(m)
        deletable = set(re.findall(r'"([a-z_]+)"', m.group(1)))
        i = rute.find("async function refGuard")
        badan = rute[i:rute.find("\nexport async function DELETE", i)]
        dijaga = set(re.findall(r'table === "([a-z_]+)"', badan))
        # `music_library` sengaja tanpa penjaga referensi: track musik dipilih mesin per-mood,
        # tak ada channel/tenant yang menyimpan rujukan langsung ke satu track.
        telanjang = sorted(deletable - dijaga - {"music_library"})
        self.assertEqual(
            [], telanjang,
            f"Tabel ini boleh DIHAPUS tapi tak punya penjaga referensi: {telanjang}. "
            "Menghapus barisnya akan meninggalkan channel/niche menggantung tanpa peringatan.")


if __name__ == "__main__":
    unittest.main()
