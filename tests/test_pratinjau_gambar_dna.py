"""PRATINJAU 1 GAMBAR WAJIB MEMAKAI PERAKIT PROMPT PRODUKSI — bukan rakitan sendiri.

Ketetapan owner 2026-08-15 (`SISA_KERJA [B32]` T11), lahir dari pertanyaan *"apa pantas dijual?"*:
mencocokkan gaya visual sebuah niche hari ini menuntut **video penuh** — ±4 menit, ±Rp 1.500 sekali
coba. Terukur di sesi ini: enam putaran video hanya untuk menyetel gaya. Beban itu akan diwarisi
SETIAP tenant. Pratinjau = ±6 detik, ±Rp 250, nol video, nol kuota, nol jejak di stok konten.

⚠️ YANG DIJAGA BERKAS INI — dan inilah alasan rancangannya berbentuk begini:
pratinjau HARUS lewat perakit prompt PRODUKSI (`AIImageProvider._build_image_prompt` → corong
`_generate_image` yang menempelkan patri). Kalau layar/rute merakit promptnya sendiri, lahir
**KEBENARAN KEDUA** yang suatu hari berbeda dari produksi — persis kelas cacat yang [B32] tutup
seharian ini (tiga jalur baca DNA · dua tempat menghitung hal yang sama). Pratinjau yang berbohong
lebih berbahaya daripada tidak ada pratinjau: tenant menyetel DNA berdasarkan gambar yang tak pernah
mewakili hasil aslinya.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCER = os.path.join(AKAR, "src", "orchestrator", "producer.py")


class TestJalurPratinjau(unittest.TestCase):
    def test_fungsi_pratinjau_ada(self):
        from src.orchestrator.producer import run_preview_image
        self.assertTrue(callable(run_preview_image))

    def test_memakai_perakit_prompt_produksi(self):
        """Nol prompt dirakit sendiri: wajib lewat `_build_image_prompt` + `_generate_image`."""
        with open(PRODUCER, encoding="utf-8") as f:
            src = f.read()
        i = src.find("def run_preview_image")
        self.assertGreater(i, 0)
        badan = src[i:i + 4000]
        self.assertIn("_build_image_prompt", badan,
                      "pratinjau merakit promptnya sendiri — akan berbeda dari produksi")
        self.assertIn("_generate_image", badan,
                      "pratinjau tidak lewat corong yang menempelkan patri larangan")

    def test_tidak_menyentuh_stok_konten_maupun_kuota(self):
        """Pratinjau bukan produksi: haram menulis inventaris/production_runs atau memanggil pipeline.
        Yang diperiksa = KODE-nya, bukan penjelasannya (docstring justru MENYEBUT ketiganya sebagai
        hal yang sengaja tak disentuh — alat ukur versi pertama saya menandai kalimatnya sendiri)."""
        import ast, inspect
        import src.orchestrator.producer as prod
        fn = ast.parse(inspect.getsource(prod.run_preview_image)).body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(getattr(fn.body[0], "value", None), ast.Constant)):
            fn.body = fn.body[1:]                       # buang docstring
        kode = ast.unparse(fn)
        for terlarang in ("record_producing", "production_runs", "Pipeline("):
            self.assertNotIn(terlarang, kode,
                             f"pratinjau menyentuh `{terlarang}` — ia harus 1 gambar saja")

    def test_dilayani_antrean_direct_job(self):
        with open(PRODUCER, encoding="utf-8") as f:
            src = f.read()
        i = src.find("def run_direct")
        j = src.find("\ndef ", i + 10)                  # seluruh badan run_direct, bukan potongan
        self.assertIn("run_preview_image(sb, job, ch)", src[i:j if j > 0 else len(src)],
                      "jenis job pratinjau tidak dilayani jalur direct-job")


class TestKontrakGagalJujur(unittest.TestCase):
    """Gagal = tercatat & terbaca tenant, bukan diam (§0.6).

    Diikat ke FUNGSINYA (via `inspect`), bukan ke jendela sejumlah huruf: versi pertama uji ini
    menyapu 4.000 huruf pertama, lalu berubah merah begitu fungsinya bertambah panjang — alat ukur
    yang mengikat panjang teks, bukan kontrak."""

    @staticmethod
    def _badan() -> str:
        import inspect
        import src.orchestrator.producer as prod
        return inspect.getsource(prod.run_preview_image)

    def test_kegagalan_ditulis_ke_kolom_error(self):
        badan = self._badan()
        self.assertIn('"error"', badan, "kegagalan pratinjau tidak disampaikan ke layar")
        self.assertIn('"failed"', badan)

    def test_hasil_disimpan_sebagai_kunci_bukan_url(self):
        """Kolom `result_key` = kunci S3; tautan berjangka dibuat saat ditampilkan (pola video uji)."""
        self.assertIn("result_key", self._badan())



class TestPratinjauMemakaiSeluruhDna(unittest.TestCase):
    """CACAT YANG DIJAGA (temuan owner 15-Agu, beberapa menit setelah T11 dipasang):
    pratinjau versi pertama mengirim kalimat adegan MENTAH ⇒ hanya **2 dari 15** properti visual ikut
    (`render_style` + tag kualitas + larangan). Ketiga belas sisanya — pencahayaan, kamera, komposisi,
    realisme, palet, gradasi, atmosfer, rujukan, subjek, lingkungan, larangan niche — TIDAK ikut,
    padahal di produksi semuanya ikut. Pratinjau seperti itu **berbohong**: pemilik niche menyetel DNA
    berdasarkan gambar yang tak pernah memakai isian yang ia ubah."""

    DNA = {"visual_style": {
        "base_style": "GAYADASAR", "lighting": "CAHAYA", "camera": "KAMERA", "composition": "KOMPOSISI",
        "realism": "REALISME", "color_palette": "PALET", "color_grading": "GRADASI",
        "atmosphere": "SUASANA", "reference": "RUJUKAN", "subject": "SUBJEK",
        "environment": "LINGKUNGAN", "strict_prohibition": "LARANGAN", "motion": "GERAK",
        "render_style": "GAYARUPA", "camera_motion": {"intensity": "halus"}}}

    def test_seluruh_properti_visual_ikut(self):
        from src.intelligence.script_engine import prompt_adegan_dari_dna
        p = prompt_adegan_dari_dna(self.DNA, "sebuah adegan")
        hilang = [k for k, v in self.DNA["visual_style"].items() if isinstance(v, str) and v not in p]
        self.assertEqual(hilang, [], f"properti visual ini tak ikut ke pratinjau: {hilang}")

    def test_adegannya_tetap_ada(self):
        from src.intelligence.script_engine import prompt_adegan_dari_dna
        self.assertIn("sebuah adegan", prompt_adegan_dari_dna(self.DNA, "sebuah adegan"))

    def test_niche_tanpa_dna_tetap_menghasilkan_prompt(self):
        from src.intelligence.script_engine import prompt_adegan_dari_dna
        p = prompt_adegan_dari_dna({}, "adegan")
        self.assertIn("adegan", p)
        self.assertGreater(len(p), 40)

    def test_pratinjau_memanggilnya(self):
        import inspect
        import src.orchestrator.producer as prod
        self.assertIn("prompt_adegan_dari_dna", inspect.getsource(prod.run_preview_image),
                      "pratinjau kembali mengirim kalimat mentah — hanya 2 dari 15 properti akan ikut")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestJalurTampilPratinjau(unittest.TestCase):
    """CACAT YANG DIJAGA (temuan owner 15-Agu: "hasil test tidak bisa dilihat"):
    mesin mengunggah gambar pratinjau ke keranjang BUFFER (`S3_BUCKET`, lewat `s3_buffer.upload`,
    sama seperti video uji), tetapi rute layar menandatangani tautannya dari keranjang ASET
    (`mesinviral-assets` — tempat musik & logo). Beda keranjang ⇒ tautan menunjuk berkas yang tidak
    ada ⇒ **gambar tak pernah tampil**.

    ⛔ Kenapa lolos: saya menguji MESINNYA (gambar jadi & tersimpan) lalu menyebutnya "lulus", tanpa
    menguji JALUR TAMPILNYA — pelanggaran §3.4 (*data valid ≠ tampilan valid*), aturan yang saya
    sendiri kutip berkali-kali hari ini."""

    def test_rute_memakai_keranjang_yang_sama_dengan_pengunggah(self):
        rute = os.path.join(AKAR, "apps", "web", "src", "app", "api", "niches", "preview-image", "route.ts")
        with open(rute, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("presignBufferKey", src,
                      "rute pratinjau menandatangani dari keranjang yang salah — gambar tak akan tampil")
        i = src.find("const url_gambar")
        self.assertNotIn("presignAssetKey", src[i:i + 200],
                         "masih memakai keranjang ASET, padahal mesin mengunggah ke keranjang BUFFER")

    def test_mesin_mengunggah_ke_keranjang_buffer(self):
        """Sisi mesin dikunci juga: kalau suatu hari ia pindah keranjang, uji di atas jadi bohong."""
        import inspect
        import src.orchestrator.producer as prod
        self.assertIn("s3_buffer.upload", inspect.getsource(prod.run_preview_image))


class TestPratinjauTakMenumpukDiPenyimpanan(unittest.TestCase):
    """CACAT YANG DIJAGA (teguran owner 15-Agu): video uji punya penyapu ber-TTL; gambar pratinjau
    versi pertama saya TIDAK punya apa pun — kuncinya per-JOB, jadi tiap klik meninggalkan berkas
    ±2 MB di S3 **selamanya**. Untuk fitur yang dirancang agar diklik berkali-kali, itu kebocoran
    penyimpanan yang pasti terjadi, bukan kemungkinan.

    Perbaikannya menghapus masalahnya dari akar, bukan menambah penyapu: kunci TETAP per (tenant,
    niche) ⇒ pratinjau baru menimpa yang lama ⇒ paling banyak satu berkas per niche per tenant."""

    def test_kunci_tetap_per_niche_bukan_per_job(self):
        import inspect
        import src.orchestrator.producer as prod
        src = inspect.getsource(prod.run_preview_image)
        self.assertIn("pratinjau/{niche", src,
                      "kunci pratinjau tidak tetap per-niche — berkas akan menumpuk tiap klik")
        self.assertNotIn("pratinjau/{jid}", src,
                         "kunci masih per-job ⇒ tiap klik meninggalkan berkas baru selamanya")
