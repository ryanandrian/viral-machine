"""SELURUH KOLOM DNA WAJIB SAMPAI KE MESIN — TERMASUK KOLOM YANG DITAMBAHKAN BESOK.

CACAT YANG DIJAGA (`SISA_KERJA [B32]` T4)
`config._load_from_supabase()` menyalin baris niche lewat **daftar kolom yang ditulis tangan**. Kolom di
luar daftar itu hilang **senyap**: tersimpan benar di DB, tak pernah sampai ke penulis naskah/gambar.
Sudah memakan korban DUA kali, dan keduanya tercatat di komentar kode itu sendiri:
  • `emotion_scoring_criteria` — kriteria penilaian emosi admin tak pernah sampai (diperbaiki 4-Jul)
  • `description` — satu-satunya kalimat utuh yang menjelaskan niche, terisi 47 niche, berhenti di DB
    (diperbaiki 1-Agu, dibuktikan dengan menangkap prompt sungguhan: nol kemunculan)
Terukur 15-Agu: **16 kunci sampai ke mesin, 27 kolom ada di DB.**

Selain itu tabel `niches` dibaca dari **TIGA jalur berbeda** (loader · `tenant_config` · kueri langsung
tiap konsumen). Memperbaiki satu jalur tidak memperbaiki yang lain — itu sebabnya kelas cacat ini
berulang. Uji ini mengunci **satu pintu**: hanya `intelligence/config.py` yang boleh menyentuh tabel
`niches`; modul lain wajib lewat pintu itu.

⚠️ KESEGARAN TIDAK BOLEH IKUT KORBAN: sebagian pembaca (musik, kategori YouTube, gaya visual per-run)
selama ini membaca LANGSUNG ke DB = selalu mutakhir. Menyatukan jalur TIDAK boleh mengubahnya jadi
tertunda 300 detik. Karena itu pintu tunggal menyediakan dua pintu-kecil — bercache dan segar — dan uji
di bawah menjaga pembaca yang tadinya segar TETAP segar.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(AKAR, "src")
# Satu-satunya berkas yang boleh menyentuh tabel `niches`.
PINTU_TUNGGAL = os.path.join("intelligence", "config.py")


def _kolom_db() -> set:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(AKAR, ".env"))
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    baris = (sb.table("niches").select("*").limit(1).execute().data or [{}])[0]
    return set(baris.keys())


class TestSeluruhKolomSampaiKeMesin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(AKAR, ".env"))
        from src.intelligence.config import get_niches
        cls.niches = get_niches()
        cls.kolom = _kolom_db()

    def test_nol_kolom_hilang_di_jalan(self):
        contoh = next(iter(self.niches.values()))
        hilang = sorted(self.kolom - set(contoh.keys()) - {"created_at"})
        self.assertEqual(hilang, [],
                         f"kolom DNA ada di DB tapi TIDAK sampai ke mesin: {hilang} — "
                         f"kelas cacat yang sama dengan emotion_scoring_criteria (4-Jul) & description (1-Agu)")

    def test_berlaku_untuk_semua_niche_bukan_satu(self):
        for nid, dna in self.niches.items():
            with self.subTest(niche=nid):
                self.assertIn("visual_style", dna)
                self.assertIn("narration_persona", dna)


class TestSatuPintuBaca(unittest.TestCase):
    """Tiga jalur = satu diperbaiki, dua lainnya tetap rusak. Kunci jadi satu pintu."""

    def test_hanya_config_yang_menyentuh_tabel_niches(self):
        pelanggar = []
        for akar, _, berkas in os.walk(SRC):
            for b in berkas:
                if not b.endswith(".py"):
                    continue
                p = os.path.join(akar, b)
                rel = os.path.relpath(p, SRC)
                if rel == PINTU_TUNGGAL:
                    continue
                with open(p, encoding="utf-8") as f:
                    isi = f.read()
                if 'table("niches")' in isi or "table('niches')" in isi:
                    pelanggar.append(rel)
        self.assertEqual(sorted(pelanggar), [],
                         f"modul ini membaca tabel `niches` sendiri, di luar pintu tunggal: {pelanggar}")

    def test_pintu_segar_tersedia(self):
        """Pembaca yang butuh data mutakhir (musik · kategori · gaya visual per-run) wajib punya jalan
        TANPA menunggu masa berlaku cache — kalau tidak, menyatukan jalur = menanam jeda baru."""
        from src.intelligence.config import muat_niche_segar
        self.assertTrue(callable(muat_niche_segar))

    def test_pintu_segar_mengembalikan_bentuk_yang_sama(self):
        from src.intelligence.config import get_niches, muat_niche_segar
        nid = next(iter(get_niches()))
        segar = muat_niche_segar(nid)
        self.assertIsInstance(segar, dict)
        self.assertEqual(set(segar.keys()), set(get_niches()[nid].keys()),
                         "bentuk data pintu-segar berbeda dari pintu-bercache — dua bentuk = dua bug")


class TestFramePembukaMemakaiSeluruhDna(unittest.TestCase):
    """Frame pembuka = pemikat paling menentukan, tapi hanya membaca 4 dari 16 properti visual
    (tercatat 🟡 di `NICHE_DNA §1.1` sejak 4-Jul, tak pernah ditutup)."""

    def test_prompt_frame_pembuka_membawa_semua_properti(self):
        from src.production.visual_assembler import prompt_frame_pembuka
        vs = {
            "base_style": "GAYADASAR", "color_palette": "PALET", "atmosphere": "SUASANA",
            "camera": "KAMERA", "lighting": "CAHAYA", "realism": "REALISME",
            "reference": "RUJUKAN", "color_grading": "GRADASI", "composition": "KOMPOSISI",
            "motion": "GERAK", "render_style": "GAYARUPA", "strict_prohibition": "LARANGAN",
            "subject": "SUBJEK", "environment": "LINGKUNGAN",
            "camera_motion": {"intensity": "halus"},   # objek bersarang — bukan teks prompt
        }
        p = prompt_frame_pembuka(vs, "sebuah konsep pembuka")
        # Bandingkan tanpa peduli besar-kecil huruf: `render_style` sengaja lewat `.capitalize()`
        # sejak 14-Agu supaya prompt 47 niche lama tetap sama persis. Yang dijaga = NILAINYA sampai,
        # bukan susunan hurufnya (pelajaran [B31]: ikat KONTRAK, jangan ikat teks harfiah).
        pl = p.lower()
        hilang = [k for k, v in vs.items() if isinstance(v, str) and v.lower() not in pl]
        self.assertEqual(hilang, [],
                         f"properti DNA ini tak ikut ke frame pembuka: {hilang}")

    def test_larangan_niche_ikut_ke_frame_pembuka(self):
        """Yang paling berbahaya bila hilang: larangan figur niche (§5b Lapis-2)."""
        from src.production.visual_assembler import prompt_frame_pembuka
        p = prompt_frame_pembuka({"strict_prohibition": "JANGAN GAMBARKAN SOSOK YANG DIMULIAKAN"}, "x")
        self.assertIn("JANGAN GAMBARKAN SOSOK YANG DIMULIAKAN", p)

    def test_visual_style_kosong_tetap_menghasilkan_prompt(self):
        """Nol niche boleh jatuh ke prompt kosong — gagal-aman, bukan gagal-diam."""
        from src.production.visual_assembler import prompt_frame_pembuka
        p = prompt_frame_pembuka({}, "konsep pembuka")
        self.assertIn("konsep pembuka", p)
        self.assertGreater(len(p), 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
