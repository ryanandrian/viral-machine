"""Panel katalog: admin harus tahu SATUAN mana yang berlaku untuk jenis model yang ia sunting,
dan dari mana harga barisnya berasal.

MASALAH YANG DIJAGA (owner 2026-08-22: *"anti error jika kedepan admin panel menambah provider dan
ai model baru untuk berbagai tipe"*)
Terukur pada panel hari ini:
  • editor harga menampilkan LIMA kotak (in/out/img/1M chr/dtk) untuk SEMUA jenis model, tanpa satu
    arahan pun mana yang berlaku. Hanya kotak per-detik punya keterangan. Jadi admin yang ingin
    membetulkan harga model suara/gambar/video **menebak**.
  • kolom harga tak menyebut ASAL angkanya. 16 dari 42 model aktif TIDAK ADA di umpan harga publik
    (semua model video kita, ElevenLabs, Cloudflare, Edge, fal) ⇒ harganya WAJIB diketik admin.
    Tanpa keterangan asal, admin tak bisa membedakan "sudah datang sendiri" dari "menunggu diketik".

Yang dijaga = keberadaan penuntun & keterangan asal, BUKAN kata-katanya.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(AKAR, "apps/web/src/app/admin/(panel)/catalog/page.tsx")


def _baca():
    with open(PANEL, encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi):
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))


class TestEditorHargaMenuntunPerJenis(unittest.TestCase):
    """[Diperbarui 23-Agu] Versi pertama uji ini mematok penuntun yang DIKETIK di layar
    (`SATUAN_HARGA` di page.tsx). Itu justru penyakitnya: pengetahuan satuan diketik ulang di layar,
    lalu membusuk sendiri. Kini penuntun & kotak isian DITURUNKAN dari cermin registry kode
    (`catalog_valid_values`, field `pricing_unit:<jenis>`) — jadi yang dijaga: layar TIDAK BOLEH
    punya daftar satuannya sendiri, dan WAJIB membaca cermin itu untuk jenis baris yang disunting.
    Kelengkapan 4 jenis dijaga di sumbernya oleh `test_gerbang_rantai_biaya.py` G2."""

    def test_layar_membaca_cermin_satuan(self):
        """Yang diperiksa: cermin benar-benar DISARING per jenis. Versi pertama uji ini lolos saat
        syarat saringnya diganti `false` — karena kata 'pricing_unit:' masih ada di tempat lain."""
        isi = _tanpa_komentar(_baca())
        self.assertRegex(isi, r"field\s*===\s*`pricing_unit:\$\{",
                         "panel tak menyaring cermin satuan per jenis → ia menanam daftarnya sendiri")

    def test_penuntun_dan_kotak_isian_mengikuti_JENIS_baris(self):
        """Turunan wajib per-JENIS: satu daftar untuk semua jenis = jebakan lama kembali."""
        isi = _tanpa_komentar(_baca())
        m = re.search(r"const\s+(satuanJenis|satuanUntukJenis)\s*=\s*\(?\s*(\w+)", isi)
        self.assertIsNotNone(m, "tak ada penurun satuan per-jenis")
        nama = m.group(1)
        awal = isi.index("priceEdit?.key === mk")
        akhir = isi.index("setPriceEdit(null)", awal)
        self.assertIn(nama, isi[awal:akhir],
                      "editor harga tak memakai penurun satuan → kotak isiannya kembali tetap")
        self.assertRegex(isi, rf"{nama}\(String\(m\.component",
                         "penurun tak diberi JENIS baris yang sedang disunting")

    def test_layar_tak_punya_daftar_satuan_sendiri(self):
        """Dijaga ganda dengan G1 — di sini dari sisi maknanya: nol nama satuan diketik di layar."""
        isi = _tanpa_komentar(_baca())
        for satuan in ("per_1m_chars", "per_image", "per_second_usd", "in_per_1m"):
            self.assertNotIn(satuan, isi,
                             f"nama satuan '{satuan}' masih diketik di layar (harus dari cermin)")


class TestAsalHargaTerlihat(unittest.TestCase):

    def test_kolom_harga_menyebut_asalnya(self):
        isi = _tanpa_komentar(_baca())
        # Yang diperiksa: field `source` benar-benar DIBACA dari baris harga (bukan kata 'source'
        # muncul entah di mana). Versi pertama uji ini memakai pola yang tak cocok dengan bentuk
        # bacaan sebenarnya (`pr.source`) — uji yang salah, bukan kode yang salah.
        self.assertRegex(isi, r"\bpr\s*\.\s*source\b|pricing\s*\.\s*source\b",
                         "kolom harga tak membaca asal harga (otomatis vs manual)")
        self.assertRegex(isi, r"manual", "kata pembeda asal harga ('manual') tak tampil")

    def test_asal_harga_bukan_kode_mati(self):
        """Nilai asal wajib MEMBEDAKAN dua keadaan yang terlihat mata (manual vs otomatis).
        Versi pertama uji ini lolos saat isinya diganti `{"·"}` — karena kata 'source' masih ada
        di atribut `title`. Yang diperiksa sekarang: percabangan atas nilai `source`."""
        isi = _tanpa_komentar(_baca())
        i = isi.index("fmtPricing(pr,")
        blok = isi[i:i + 900]
        self.assertRegex(blok, r"pr\s*\.\s*source[^=]{0,60}===\s*\"manual\"\s*\?",
                         "asal harga tak dipercabangkan → keterangannya tak bisa membedakan apa pun")
        self.assertIn("otomatis", blok, "keadaan 'otomatis' tak pernah tampil")


if __name__ == "__main__":
    unittest.main()
