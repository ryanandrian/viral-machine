"""Akun terhapus (`subscription_status='deleted'`) wajib punya tempatnya sendiri di layar admin.

LAHIR DARI LAPORAN OWNER 2026-09-02: sesudah menghapus tenant salah-buat lewat panel, owner
melihat barisnya TETAP di daftar dengan status `deleted`.

Barisnya memang SENGAJA disimpan (LIFECYCLE §4.2 / `renewal.py::_hard_delete_tenant`): atribusi
komisi agen berlaku selamanya, klaim channel YouTube harus bertahan (anti masa-coba-berulang), dan
bukti bayar wajib disimpan. Yang dihapus adalah ISINYA, bukan cangkangnya. **Itu bukan cacat.**

Yang CACAT: layar tak menyiapkan tempat untuk cangkang itu —
  • tab "Semua" mencampurnya dengan pelanggan hidup, tanpa saringan untuk memisahkan;
  • KPI "Total tenant" dan angka di tab ikut menghitungnya ⇒ owner membaca jumlah pelanggan
    yang lebih besar dari kenyataan;
  • lencananya jatuh ke fallback dan mencetak kata mentah `deleted` (nol dwibahasa).

Hari ini 1 baris; pada 10× jumlahnya daftar "Semua" penuh bangkai dan angka MRR/total makin
menyesatkan — dan yang menyadarinya MANUSIA, bukan mesin. Karena itu dikunci uji.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = "apps/web/src/app/admin/(panel)/tenants/page.tsx"
API = "apps/web/src/app/api/admin/tenants/route.ts"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """URUTAN PENTING — komentar BARIS dibuang DULU, baru komentar blok.

    Pola lama (blok dulu) menelan 404 baris KODE NYATA di berkas ini: baris `//` di kepala
    berkas memuat teks `/* (service_role, ...` sehingga penghapus blok berlari sampai `*/`
    milik komentar JSX yang jauh di bawah — 72% berkas lenyap dan uji memeriksa sisa yang
    tak berarti. Jangan dibalik lagi, dan jangan disalin dari uji lain tanpa mengecek ini.
    """
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestAkunTerhapusPunyaSaringanSendiri(unittest.TestCase):
    def setUp(self):
        self.layar = _tanpa_komentar(_isi(LAYAR))

    def test_daftar_saringan_memuat_terhapus_dwibahasa(self):
        m = re.search(r"const FILTERS[^=]*=\s*\[(.*?)\];", self.layar, flags=re.S)
        self.assertIsNotNone(m, "daftar FILTERS tidak ditemukan — struktur layar berubah")
        blok = m.group(1)
        self.assertIn('"deleted"', blok,
                      'FILTERS tanpa saringan "deleted" — akun terhapus tak punya tempat.')
        baris = re.search(r'\["deleted",\s*"([^"]+)",\s*"([^"]+)"\]', blok)
        self.assertIsNotNone(baris, 'entri "deleted" wajib berformat [kunci, label-ID, label-EN].')
        self.assertNotEqual(baris.group(1).strip(), "",
                            "label Indonesia untuk saringan Terhapus kosong.")

    def test_tab_semua_tidak_mencampur_akun_terhapus(self):
        """Perilaku yang diikat: `filter === "all"` TIDAK lagi meloloskan status deleted."""
        m = re.search(r"const view = rows\.filter\((.*?)\);", self.layar, flags=re.S)
        self.assertIsNotNone(m, "penyaring `view` tidak ditemukan — struktur layar berubah")
        badan = m.group(1)
        self.assertNotRegex(
            badan, r'filter === "all" \|\|',
            'tab "Semua" masih meloloskan SEMUA status termasuk deleted.',
        )
        self.assertIn('"deleted"', badan,
                      "penyaring `view` tidak menyebut status deleted sama sekali.")

    def test_lencana_status_terhapus_dwibahasa_bukan_kata_mentah(self):
        m = re.search(r"function StBadge.*?\n}", self.layar, flags=re.S)
        self.assertIsNotNone(m, "StBadge tidak ditemukan")
        badan = m.group(0)
        self.assertIn('s === "deleted"', badan,
                      'StBadge tanpa cabang "deleted" — lencana mencetak kata mentah dari DB.')
        cabang = badan[badan.find('s === "deleted"'):]
        self.assertRegex(
            cabang[:400], r"<Bi\s+id=",
            "lencana Terhapus wajib dwibahasa (<Bi id=… en=…>), bukan teks satu bahasa.",
        )


class TestHitunganTakMenggelembungOlehBangkai(unittest.TestCase):
    """Angka yang dibaca owner harus berarti PELANGGAN, bukan cangkang akun terhapus."""

    def test_kpi_total_di_server_mengecualikan_deleted(self):
        api = _tanpa_komentar(_isi(API))
        m = re.search(r"const kpi = \{(.*?)\};", api, flags=re.S)
        self.assertIsNotNone(m, "blok kpi tidak ditemukan di route API")
        total = re.search(r"total:\s*([^,\n]+)", m.group(1))
        self.assertIsNotNone(total, "kunci `total` tidak ditemukan di kpi")
        self.assertNotEqual(
            total.group(1).strip(), "rows.length",
            'kpi.total masih `rows.length` — akun terhapus ikut dihitung sebagai tenant.',
        )
        self.assertIn("deleted", total.group(1),
                      "kpi.total tidak mengecualikan status deleted.")

    def test_angka_di_tab_tenant_mengecualikan_deleted(self):
        layar = _tanpa_komentar(_isi(LAYAR))
        m = re.search(r'aria-selected=\{tab === "tenants"\}.*?</button>', layar, flags=re.S)
        self.assertIsNotNone(m, "tab Tenant tidak ditemukan")
        self.assertNotRegex(
            m.group(0), r"\{rows\.length\}",
            "angka di tab Tenant masih rows.length — menggelembung oleh akun terhapus.",
        )


if __name__ == "__main__":
    unittest.main()
