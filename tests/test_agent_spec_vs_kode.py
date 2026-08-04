"""DOKUMEN ↔ KODE untuk ATURAN UANG program agen. SSOT: `AGENT_AND_AFILIATION_ARCITECTURE.md` §2.

KENAPA UJI INI ADA (teguran owner 2026-08-04)
*"Anda sudah baca AGENT_AND_AFILIATION? buat apa file MD dibuat? pajangan?"* — Claude menanyakan kepada
owner keputusan yang **sudah diketok di dokumen itu** (§5g.8 & §1.3 soal retensi data komisi/atribusi).
Diukur hari itu: dari **47 dokumen** di repo, hanya **5** dijaga mesin. Dokumen yang mengatur **uang ke
pihak ketiga** justru TIDAK — padahal salah di sini = agen dibayar kurang/lebih, dan itu sengketa.

Owner: *"anda selalu abai update dokumen sehingga dokumen tidak bisa dijadikan SSOT yang valid."*
Jawaban atas "entah kenapa": **tak ada yang MEMAKSANYA.** Setiap dokumen yang masih akurat di repo ini
adalah yang dijaga uji anti-drift; yang membusuk adalah yang bergantung pada disiplin. Uji ini
memindahkan §2 (5 aturan bisnis TERKUNCI, diketok owner 2026-07-17) ke kategori pertama.

Yang dijaga:
  A. Aturan §2.1 — komisi flat = PER BULAN-langganan yang dibayar (bayar 12 bulan = 12× komisi).
  B. Aturan §2.2 — basis persen = rupiah settlement yang BENAR-BENAR masuk, bukan harga pajangan.
  C. Aturan §5g.10 — HANYA pembayaran langganan yang berkomisi.
  D. Aturan §2.3/§5e — refund → baris REVERSAL (tarik-balik), bukan menagih transfer balik.
  E. Kalimat aturannya masih ADA di dokumen (kalau dicabut dari dokumen, uji ini merah → memaksa
     keputusan sadar, bukan penghapusan diam-diam).

CATATAN: A-D menguji KODE terhadap aturan; E menguji DOKUMEN masih memuat aturannya. Dua arah, supaya
tak ada sisi yang bisa bergeser sendiri.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing.partner import compute_commission  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(AKAR, "AGENT_AND_AFILIATION_ARCITECTURE.md")


def _spec() -> str:
    return open(SPEC, encoding="utf-8").read()


class TestAturanUangKodeSesuaiSpec(unittest.TestCase):
    """A-C: hitungan uang di kode = aturan §2 yang diketok owner."""

    def test_a_komisi_flat_dikali_bulan_yang_dibayar(self):
        """§2.1: "komisi dihitung per bulan-langganan yang dibayar. Tenant bayar 12 bulan sekaligus
        = 12× komisi bulanan". Kalau ini melorot jadi 1×, agen dibayar 1/12 dari haknya — dan tak
        seorang pun akan sadar sampai agen menghitung sendiri lalu menuntut."""
        satu = compute_commission("flat_idr", 100_000, gross_idr=500_000, months_paid=1)
        dua_belas = compute_commission("flat_idr", 100_000, gross_idr=6_000_000, months_paid=12)
        self.assertEqual(satu, 100_000)
        self.assertEqual(dua_belas, 1_200_000,
                         "komisi flat TIDAK dikali jumlah bulan — melanggar §2.1, agen dibayar kurang")

    def test_a2_flat_tidak_terpengaruh_nilai_transaksi(self):
        """Flat = rupiah tetap per bulan; harga transaksi tak boleh mengubahnya (kalau berubah,
        berarti kode diam-diam memperlakukannya sebagai persen)."""
        murah = compute_commission("flat_idr", 50_000, gross_idr=100_000, months_paid=3)
        mahal = compute_commission("flat_idr", 50_000, gross_idr=9_000_000, months_paid=3)
        self.assertEqual(murah, mahal, "komisi flat berubah mengikuti nilai transaksi — bukan flat lagi")

    def test_b_persen_dari_rupiah_yang_benar_benar_masuk(self):
        """§2.2: "Basis persen = rupiah yang BENAR-BENAR masuk (nilai settlement setelah diskon apa
        pun; bukan harga pajangan). Sistem tidak pernah membagi uang yang tidak diterima."
        Diuji dengan kasus diskon: harga pajangan 1jt, settlement 700rb → komisi 10% = 70rb, BUKAN 100rb."""
        self.assertEqual(compute_commission("percent", 10, gross_idr=700_000, months_paid=1), 70_000)
        # months TIDAK mengalikan persen (persen sudah dari total settlement yang mencakup N bulan) —
        # kalau ikut dikali, agen dibayar 12× lipat pada pembayaran tahunan.
        self.assertEqual(compute_commission("percent", 10, gross_idr=6_000_000, months_paid=12), 600_000,
                         "persen dikali jumlah bulan = pembayaran GANDA (uang keluar 12× lipat)")

    def test_b2_nol_dan_negatif_tidak_pernah_jadi_komisi(self):
        """Nilai rate kosong/nol/negatif harus 0, bukan meledak atau jadi minus (minus = kita menagih
        agen). Kasus nyata: agen baru yang nilai komisinya belum diisi admin."""
        for v in (0, None, -5):
            self.assertEqual(compute_commission("flat_idr", v, 1_000_000, 1), 0)
            self.assertEqual(compute_commission("percent", v, 1_000_000, 1), 0)

    def test_b3_tipe_rate_asing_gagal_JUJUR(self):
        """Tipe tak dikenal harus MELEDAK, bukan diam-diam mengembalikan 0 — komisi yang hilang tanpa
        jejak jauh lebih buruk daripada proses yang berhenti dan melapor (CLAUDE.md §0.6)."""
        with self.assertRaises(ValueError):
            compute_commission("entah_apa", 10, 1_000_000, 1)

    def test_c_hanya_pembayaran_langganan_berkomisi(self):
        """§5g.10: hanya kategori `subscription`. Dijaga di level SUMBER supaya perubahan kategori
        pembayaran (mis. jual aset/top-up) tak diam-diam menciptakan kewajiban komisi baru."""
        src = open(os.path.join(AKAR, "src", "billing", "partner.py"), encoding="utf-8").read()
        self.assertRegex(src, r'\(order\.get\("category"\)\s*or\s*"subscription"\)\s*!=\s*"subscription"',
                         "gerbang 'hanya langganan berkomisi' (§5g.10) hilang dari partner.py")

    def test_d_refund_lewat_baris_reversal_bukan_tagih_balik(self):
        """§2.3: refund setelah komisi dibayar → jadi PENGURANG tagihan bulan berikutnya, bukan
        menagih transfer balik ke agen. Mekanismenya = baris `reversal` yang tetap 'accrued'."""
        src = open(os.path.join(AKAR, "src", "billing", "partner.py"), encoding="utf-8").read()
        self.assertIn('"entry_kind": "reversal"', src, "mekanisme reversal hilang — §2.3 tak ditegakkan")
        self.assertIn("def record_refund_reversal", src)


class TestSpecMasihMemuatAturannya(unittest.TestCase):
    """E: arah sebaliknya — dokumen tak boleh kehilangan aturan yang kode tegakkan.

    Kalau kalimat aturannya dicabut dari dokumen tapi kodenya tetap, dokumen berhenti menjelaskan
    perilaku sistem — itu awal membusuknya SSOT. Uji ini memaksa pencabutan jadi keputusan SADAR.
    """

    def test_lima_aturan_terkunci_masih_ada(self):
        t = _spec()
        m = re.search(r"## §2 ATURAN BISNIS TERKUNCI(.*?)\n---", t, re.S)
        self.assertIsNotNone(m, "§2 ATURAN BISNIS TERKUNCI hilang dari SPEC — struktur berubah?")
        blok = m.group(1)
        for n in range(1, 6):
            self.assertRegex(blok, rf"\n{n}\.\s+\*\*",
                             f"aturan terkunci §2.{n} tak lagi ada di dokumen (diketok owner 17-Jul)")

    def test_kalimat_kunci_aturan_uang_masih_ada(self):
        """Frasa yang menjadi dasar uji A/B di atas. Bila diubah, uji ini merah → yang mengubahnya
        wajib memperbarui uji + kodenya sekaligus, bukan hanya salah satu."""
        t = _spec()
        for frasa in ("per bulan-langganan yang dibayar",
                      "12× komisi bulanan",
                      "rupiah yang BENAR-BENAR masuk"):
            self.assertIn(frasa, t, f"frasa aturan uang hilang dari SPEC: {frasa!r}")

    def test_retensi_data_komisi_masih_tertulis(self):
        """Pasal yang menjawab pertanyaan retensi data 04-Agu (§5g.8) — ini yang membuat sesi
        berikutnya TIDAK perlu menanyakan ulang ke owner. Hilang = pertanyaan itu kembali terbuka."""
        t = _spec()
        self.assertRegex(t, r"ledger/payout\s+\*\*disimpan\*\*",
                         "§5g.8 (ledger/payout DISIMPAN — audit & pajak) hilang dari SPEC")
        self.assertRegex(t, r"terkunci permanen|terkunci selamanya|via kode, permanen",
                         "aturan atribusi PERMANEN hilang dari SPEC — dasar keputusan retensi atribusi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
