"""PENJAGA ATAS PENJAGA — gerbang kerja tidak boleh hilang, mati, atau dilucuti diam-diam.

KENAPA BERKAS INI ADA
Gerbang kerja (Mode Rencana · gerbang penyimpanan · gerbang komponen) dipasang 2026-08-11 atas
perintah owner: *"bikin aturan kerja dengan gerbang yang ketat agar anda selalu taat, tanpa alasan
setitikpun untuk melanggarnya di setiap sesi baru dan pasca compacting"*.

Masalahnya: gerbang itu **dipasang oleh Claude sendiri**. Artinya Claude juga bisa membuangnya —
dan owner (non-teknis) tidak akan pernah tahu. Persis pola yang sudah terbukti berulang: aturan
berupa NIAT dilanggar, aturan berupa BENDA yang bisa diperiksa dipatuhi.

Maka keberadaan gerbang dijadikan BENDA yang diperiksa mesin. Karena gerbang penyimpanan menolak
commit saat berkas uji merah, berkas ini menutup lingkarannya: **membuang gerbang = uji merah =
pekerjaan tidak bisa disimpan.**

BATAS YANG JUJUR — jangan mengira ini pagar sempurna:
  * Berkas ini menjaga KEBERADAAN gerbang, bukan KEJUJURAN Claude. Aturan 1, 2, 3 (tanpa asumsi ·
    bukan asal kerja · tidak buru-buru menyimpulkan) tidak bisa diperiksa mesin mana pun.
  * Mode Rencana tinggal di setelan Claude Code pada komputer owner, DI LUAR folder proyek —
    perubahannya tidak meninggalkan jejak di riwayat proyek. Diperiksa di sini bila berkasnya
    terbaca; bila tidak ada (mesin lain), uji itu dilewati, bukan dipaksa merah.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETELAN_PROYEK = os.path.join(AKAR, ".claude", "settings.json")
HOOK_COMMIT = os.path.join(AKAR, ".claude", "hooks", "gerbang_commit.sh")
HOOK_KOMPONEN = os.path.join(AKAR, ".claude", "hooks", "gerbang_komponen.sh")
ATURAN = os.path.join(AKAR, "CLAUDE.md")
SETELAN_GLOBAL = os.path.expanduser("~/.claude/settings.json")


def _teks(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestBerkasGerbangMasihAda(unittest.TestCase):

    def test_setelan_proyek_ada(self):
        self.assertTrue(os.path.exists(SETELAN_PROYEK),
                        "setelan gerbang proyek HILANG — dua gerbang mati sekaligus")

    def test_kedua_hook_ada_dan_bisa_dijalankan(self):
        for p in (HOOK_COMMIT, HOOK_KOMPONEN):
            self.assertTrue(os.path.exists(p), f"berkas gerbang HILANG: {p}")
            self.assertTrue(os.access(p, os.X_OK),
                            f"gerbang ada tapi TIDAK bisa dijalankan (izin dicabut) = mati diam-diam: {p}")


class TestGerbangMasihTerdaftar(unittest.TestCase):
    """Berkasnya ada belum cukup — ia harus benar-benar dipanggil."""

    def _hooks(self):
        return json.loads(_teks(SETELAN_PROYEK)).get("hooks", {}).get("PreToolUse", [])

    def test_gerbang_commit_terdaftar_pada_perintah(self):
        cocok = [h for grup in self._hooks() if grup.get("matcher") == "Bash"
                 for h in grup.get("hooks", []) if "gerbang_commit.sh" in h.get("command", "")]
        self.assertTrue(cocok, "gerbang penyimpanan tidak lagi terdaftar — commit rusak bisa lolos")

    def test_gerbang_komponen_terdaftar_pada_pembuatan_berkas(self):
        cocok = [h for grup in self._hooks() if grup.get("matcher") == "Write"
                 for h in grup.get("hooks", []) if "gerbang_komponen.sh" in h.get("command", "")]
        self.assertTrue(cocok, "gerbang komponen tidak lagi terdaftar — komponen baru bisa lahir diam-diam")

    def test_tenggat_gerbang_commit_cukup_untuk_seluruh_uji(self):
        """813 uji butuh ±57 detik. Tenggat yang dipangkas = gerbang gagal lalu dianggap lolos."""
        for grup in self._hooks():
            for h in grup.get("hooks", []):
                if "gerbang_commit.sh" in h.get("command", ""):
                    self.assertGreaterEqual(
                        h.get("timeout", 0), 120,
                        "tenggat gerbang penyimpanan dipangkas di bawah 120 detik — seluruh uji "
                        "tak akan sempat selesai, dan gerbang berubah jadi pajangan")


class TestIsiGerbangTidakDilucuti(unittest.TestCase):
    """Berkas boleh ada, terdaftar, tapi isinya dikosongkan. Yang dijaga: DUA penjaga di dalamnya."""

    def test_penjaga_uji_merah_masih_ada(self):
        self.assertIn("pytest", _teks(HOOK_COMMIT),
                      "gerbang penyimpanan tak lagi menjalankan pemeriksaan otomatis (aturan 4 mati)")

    def test_penjaga_dokumen_masih_ada(self):
        t = _teks(HOOK_COMMIT)
        self.assertIn("tanpa-dokumen", t,
                      "penjaga dokumen dicabut dari gerbang penyimpanan (aturan 5 mati)")
        self.assertIn(r"\.md$", t, "gerbang tak lagi memeriksa keikutsertaan dokumen")

    def test_gerbang_komponen_masih_menolak(self):
        self.assertIn("deny", _teks(HOOK_KOMPONEN),
                      "gerbang komponen tak lagi menolak apa pun (aturan 6 mati)")


class TestDelapanAturanMasihTertulis(unittest.TestCase):
    """Gerbang mesin hanya menjaga 3 dari 8 aturan. Lima sisanya hidup sebagai TEKS yang dibaca
    setiap sesi — maka teksnya sendiri yang dijaga agar tak pernah 'hilang saat merapikan'."""

    def test_blok_delapan_aturan_ada(self):
        t = _teks(ATURAN)
        self.assertIn("§00 DELAPAN ATURAN OWNER", t,
                      "blok delapan aturan owner HILANG dari buku aturan")
        self.assertIn("PASCA-COMPACTING", t,
                      "kalimat 'berlaku pasca-compacting' hilang — sesi setelah ingatan terpotong "
                      "tidak lagi merasa terikat")

    def test_kedelapan_barisnya_utuh(self):
        t = _teks(ATURAN)
        kunci = ["Tanpa asumsi", "Bukan asal kerja", "Tidak buru-buru menyimpulkan",
                 "Nol bug baru", "ikut diperbarui", "pustaka komponen yang sudah ada",
                 "sampai 100% tuntas", "Bahasa yang owner pahami"]
        hilang = [k for k in kunci if k not in t]
        self.assertFalse(hilang, f"aturan owner hilang dari buku aturan: {hilang}")

    def test_larangan_beralasan_masih_tegas(self):
        self.assertIn("TIDAK ADA SATU PUN ALASAN YANG SAH", _teks(ATURAN),
                      "kalimat penolakan alasan dilunakkan/dihapus")

    def test_prosedur_rencana_masih_ada(self):
        self.assertIn("RENCANA DISETUJUI DULU", _teks(ATURAN),
                      "prosedur §0.8 (rencana → persetujuan → tuntas) hilang")


class TestModeRencanaMasihMenyala(unittest.TestCase):
    """Satu-satunya gerbang yang tinggal di luar folder proyek — perubahannya tak berjejak."""

    def test_mode_rencana(self):
        if not os.path.exists(SETELAN_GLOBAL):
            self.skipTest("setelan Claude Code tak ditemukan di mesin ini — bukan kegagalan")
        mode = json.loads(_teks(SETELAN_GLOBAL)).get("permissions", {}).get("defaultMode")
        self.assertEqual(
            mode, "plan",
            f"Mode Rencana MATI (sekarang: {mode!r}). Aturan 7 tidak lagi dipagari mesin — Claude "
            "bisa menyunting apa pun tanpa rencana yang disetujui owner.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
