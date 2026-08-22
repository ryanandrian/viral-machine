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

    def test_ada_penuntun_satuan_untuk_keempat_jenis(self):
        isi = _tanpa_komentar(_baca())
        m = re.search(r"(SATUAN_HARGA|PENUNTUN_HARGA|satuanHarga)\s*[:=]", isi)
        self.assertIsNotNone(m, "tak ada penuntun satuan harga per jenis model")
        blok = isi[m.start():m.start() + 900]
        for jenis in ("llm", "tts", "image", "video"):
            self.assertRegex(blok, rf"\b{jenis}\b", f"penuntun tak memuat jenis '{jenis}'")

    def test_penuntun_benar_benar_dipakai_editor(self):
        """Penjaga tak boleh jadi kode mati: penuntun WAJIB dibaca saat merender editor harga."""
        isi = _tanpa_komentar(_baca())
        m = re.search(r"(SATUAN_HARGA|PENUNTUN_HARGA|satuanHarga)", isi)
        nama = m.group(1)
        pakai = re.findall(rf"(?<![a-zA-Z_]){re.escape(nama)}(?![a-zA-Z_])", isi)
        self.assertGreaterEqual(len(pakai), 2, f"'{nama}' didefinisikan tapi tak pernah dibaca — kode mati")
        # Jangkar = BLOK editor harga itu sendiri. (Versi pertama uji ini memakai kemunculan
        # `savePricing` PERTAMA — yaitu definisi fungsinya, jauh di atas editor — jadi jendelanya
        # tak pernah mencapai kodenya: pola uji palsu #3.)
        awal = isi.index("priceEdit?.key === mk")
        akhir = isi.index("setPriceEdit(null)", awal)
        self.assertIn(nama, isi[awal:akhir], "penuntun tak dipakai di dalam editor harga")

    def test_menyebut_satuan_yang_dikenal_mesin_biaya(self):
        """Satuan yang disebut wajib yang BENAR-BENAR dihitung mesin biaya (bukan karangan)."""
        isi = _tanpa_komentar(_baca())
        for satuan in ("per_1m_chars", "per_image", "per_second_usd", "in_per_1m"):
            self.assertIn(satuan, isi, f"satuan {satuan} tak disebut di panel")


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
        i = isi.index("fmtPricing(pr)")
        blok = isi[i:i + 900]
        self.assertRegex(blok, r"pr\s*\.\s*source[^=]{0,60}===\s*\"manual\"\s*\?",
                         "asal harga tak dipercabangkan → keterangannya tak bisa membedakan apa pun")
        self.assertIn("otomatis", blok, "keadaan 'otomatis' tak pernah tampil")


if __name__ == "__main__":
    unittest.main()
