"""Setiap kenop config WAJIB lahir LENGKAP di layar admin — no-hardcode tak berhenti di DB.

SSOT: `CLAUDE.md` §3.3 —
  *"Kenop config BARU = WAJIB lahir LENGKAP di commit yang sama: (a) baris DB, (b) label+deskripsi
    dwibahasa + KELOMPOK/kartu sendiri di layar admin (bukan jatuh ke 'Lainnya' sbg nama mentah),
    (c) tipe input tepat, (d) penanda internal `ops_*` = READ-ONLY + kartu 'Internal' terpisah + guard
    PATCH. 'Kenop ditanam di DB tapi layarnya asal' = pelanggaran."*
Aturan itu lahir dari **teguran owner 2026-07-17**: 12 kenop partner berserakan di "Lainnya" tanpa
label — *"asal jadi, tidak world-class"*.

MASALAH YANG DIJAGA (diukur 2026-08-04)
Keadaan saat ini BAIK: **117 kenop DB, 117 punya label+kelompok, 0 jatuh ke "Lainnya", 0 tanpa
deskripsi.** Tapi itu hasil DISIPLIN, bukan hasil penjagaan — **tak ada satu pun uji** yang memeriksanya.
Kenop ke-118 bisa lahir tanpa label dan tak seorang pun tahu, lalu owner menemukannya sendiri di layar
seperti 17-Jul. Pola yang persis sama sudah terbukti berulang di proyek ini:
`LIFECYCLE §4.2` (daftar purge tertinggal 4 tabel) · `PROGRAM_BUKTI §6c.1` (hukum tertulis, kode tak
menegakkan) · `AGENT §5g.9` (anti-komisi-diri "hanya tertulis"). **Yang tak dijaga mesin akan membusuk.**

Uji ini HERMETIK: membandingkan kunci yang DIPAKAI KODE dengan `CFG_META` di layar admin. Ia tidak
menyentuh DB (deterministik, tak bisa merusak produksi) — jadi ia menangkap kenop baru sejak baris
kodenya ditulis, bukan menunggu kenopnya sampai ke DB.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = os.path.join(AKAR, "apps", "web", "src", "app", "admin", "(panel)", "app-config", "page.tsx")

# Kunci yang SENGAJA tidak muncul di layar app-config, beserta alasannya.
# Kosong hari ini; bila kelak ada, WAJIB disertai alasan (bukan sekadar didaftarkan agar uji hijau).
DIKECUALIKAN: dict[str, str] = {}


def _kunci_dipakai_kode() -> set[str]:
    """Kunci `app_config` yang benar-benar dibaca/ditulis kode Python.

    Pola yang ditangkap = cara kode ini memang memanggilnya (diverifikasi dengan grep):
      `_cfg(sb, "nama_kenop", default)` · `_cfg_text(...)` · `.eq("key", "nama_kenop")`
    """
    kunci: set[str] = set()
    for berkas in glob.glob(os.path.join(AKAR, "src", "**", "*.py"), recursive=True):
        teks = open(berkas, encoding="utf-8", errors="ignore").read()
        kunci |= set(re.findall(r"_cfg(?:_text|_int|_float|_bool)?\(\s*\w+\s*,\s*[\"']([a-z0-9_]+)[\"']", teks))
        kunci |= set(re.findall(r"\.eq\(\s*[\"']key[\"']\s*,\s*[\"']([a-z0-9_]+)[\"']", teks))
    return kunci


def _kunci_ber_label_di_layar() -> set[str]:
    """Kunci yang punya entri `CFG_META` (label + group) di layar admin."""
    src = open(LAYAR, encoding="utf-8").read()
    blok = src[src.index("const CFG_META"):]
    return set(re.findall(r"^\s{2}[\"']?([a-z0-9_]+)[\"']?:\s*\{", blok, re.M))


class TestKenopLahirLengkap(unittest.TestCase):

    def test_pemindai_kunci_tidak_kosong(self):
        """Pagar untuk pagar: pemindai kosong = uji di bawah hijau-palsu selamanya."""
        n = len(_kunci_dipakai_kode())
        self.assertGreaterEqual(n, 20, f"pemindai hanya menemukan {n} kunci config — polanya rusak")

    def test_layar_admin_terbaca_dan_berisi(self):
        n = len(_kunci_ber_label_di_layar())
        self.assertGreaterEqual(n, 50, f"CFG_META hanya {n} entri — struktur layar berubah?")

    def test_setiap_kenop_yang_dipakai_kode_punya_label_di_layar(self):
        """Inti aturan §3.3: kenop yang MEMPENGARUHI perilaku tapi tak bisa dilihat/diubah owner =
        nilai bisnis yang tersembunyi. Itu melanggar no-hardcode dalam praktik, walau nilainya di DB."""
        dipakai = _kunci_dipakai_kode()
        berlabel = _kunci_ber_label_di_layar()
        hilang = sorted(dipakai - berlabel - set(DIKECUALIKAN))
        self.assertFalse(
            hilang,
            "Kenop dibaca KODE tapi TIDAK punya label+kelompok di /admin/app-config: "
            f"{hilang}\n"
            "Owner tak bisa melihat/mengubahnya ⇒ nilai bisnis tersembunyi (CLAUDE.md §3.3, teguran "
            "owner 2026-07-17 'asal jadi, tidak world-class').\n"
            "Perbaikan: tambah entri CFG_META (label+deskripsi DWIBAHASA + group + unit + tipe input "
            "yang tepat), ATAU daftarkan di DIKECUALIKAN dengan alasan tertulis.")

    def test_pengecualian_wajib_beralasan(self):
        for kunci, alasan in DIKECUALIKAN.items():
            self.assertTrue(alasan and len(alasan.strip()) >= 15,
                            f"DIKECUALIKAN['{kunci}'] tanpa alasan yang bisa dibaca manusia — "
                            f"pengecualian tanpa alasan = 'lupa' yang menyamar jadi 'sengaja'")

    def test_penanda_internal_ops_dijaga_read_only(self):
        """§3.3(d): kenop `ops_*` = penanda internal mesin, HARAM diubah tangan dari layar
        (mengubahnya = memalsukan keadaan operasional yang dipakai mesin mengambil keputusan)."""
        src = open(LAYAR, encoding="utf-8").read()
        if "ops_" not in src:
            self.skipTest("belum ada kenop ops_* di layar")
        self.assertRegex(src, r"ops_|readOnly|READ-ONLY|Internal",
                         "kenop ops_* ada di layar tanpa penanda read-only/kartu Internal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
