"""PRESET DNA TIDAK BOLEH MENGHAPUS PROPERTI YANG BUKAN MILIKNYA.

CACAT YANG DIJAGA (ditemukan 2026-08-15, `SISA_KERJA [B32]` T1)
`applyVisual` di editor DNA MENGGANTI seluruh objek `visual_style`:

    setVisual({ ...Object.fromEntries(VISUAL_CORE_KEYS.map(k => [k, ""])), ...preset })

Ke-6 preset `visual_style` hanya memuat 6 kunci (atmosphere · base_style · camera · color_palette ·
lighting · realism), sedangkan niche memakai sampai 16. Jadi SATU KLIK preset menghapus s/d 9 properti
— termasuk **`strict_prohibition`** (larangan agama niche, `DESAIN_PRODUK_SAAS §5b` Lapis-2) dan
**`render_style`** (gaya rupa, satu-satunya alasan niche animasi mungkin). Tenant lalu menekan Simpan
dan larangannya lenyap tanpa satu pun peringatan; kotaknya pun ikut hilang dari layar, jadi tak terlihat.
Terukur saat uji ini lahir: nol niche berjejak 6-kunci-persis di DB ⇒ **ranjau, belum meledak.**

DUA KEPUTUSAN OWNER YANG HARUS DIPATUHI SEKALIGUS — dan itu yang mendefinisikan kontrak di bawah:
  • 2026-07-04 (`NICHE_DNA_AUDIT_REMEDIATION` kepala dokumen): *"preset karakter = pilih-satu"* — memilih
    preset B setelah preset A TIDAK boleh menyisakan sisa-sisa A. Kalau tidak, tenant memperoleh gaya
    campuran yang tak pernah ia pilih. `apply_mode='replace'` di `niche_property_presets` = ini.
  • 2026-08-14 (`DESAIN_PRODUK_SAAS §5b` Lapis-2): tingkat aniconism & gaya rupa = **milik pemilik niche,
    "terlihat & bisa diubah"** — tak boleh terhapus oleh efek samping.
Keduanya dipenuhi HANYA oleh satu semantik: **preset menguasai KELUARGA kuncinya sendiri, dan tak
menyentuh apa pun di luar keluarga itu.** Keluarga = gabungan kunci seluruh preset properti tsb,
DITEMUKAN dari data (bukan dihafal kode) — preset baru dengan kunci baru otomatis ikut terhitung.

KENAPA UJI INI MENJALANKAN KODE ASLINYA, BUKAN MEMBACA TEKSNYA:
alat ukur yang mencocokkan teks gampang salah dan melahirkan temuan palsu (pelajaran
`test_rute_api_terjaga.py`, 04-Agu). `lib/niche-dna.ts` nol-impor, jadi bisa ditranspilasi apa adanya
dengan `tsc` milik repo lalu dijalankan node — yang diuji PERILAKU AKHIR-nya, bukan susunan hurufnya
(pelajaran mengikat [B30] butir 2).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(AKAR, "apps", "web")
LIB_TS = os.path.join(WEB, "src", "lib", "niche-dna.ts")
EDITOR = os.path.join(WEB, "src", "components", "niche-dna-editor.tsx")
TSC = os.path.join(WEB, "node_modules", ".bin", "tsc")

# Keadaan NYATA yang harus selamat — persis bentuk `visual_style` niche `sunnah_harian` (16 kunci
# dipakai di DB; 48 niche memakai 8-11 di antaranya). Bukan sampel karangan.
DNA_NYATA = {
    "base_style": "high-end 3D animated feature production quality",
    "color_palette": "balanced and varied per scene",
    "atmosphere": "kehangatan rumah",
    "camera": "intimate eye-level framing",
    "lighting": "cinematic three-point lighting",
    "realism": "stylized-but-detailed 3D",
    "reference": "modern family 3D animation",
    "color_grading": "rich filmic grade",
    "composition": "clear foreground subject",
    "motion": "calm unhurried movement",
    "render_style": "premium 3D animated feature film still",
    "strict_prohibition": "ABSOLUTE: never depict any prophet, messenger, angel",
    "subject": "orang biasa masa kini",
    "environment": "rumah dan jalan kampung",
    "mandatory_motion": "gerak halus",
}
# Keluarga kunci preset `visual_style` — sama dengan isi ke-6 preset di DB (2026-08-15).
KELUARGA = ["atmosphere", "base_style", "camera", "color_palette", "lighting", "realism"]
PRESET_B = {  # "Ilustrasi 3D Halus" — perhatikan: TANPA `lighting` (sengaja, menguji pembersihan keluarga)
    "atmosphere": "lembut dan ramah",
    "base_style": "soft 3D illustration",
    "camera": "wide friendly framing",
    "color_palette": "pastel",
    "realism": "stylized",
}

_HARNESS = r"""
const m = require(%s);
const f = m.terapkanPreset;
if (typeof f !== "function") { console.log(JSON.stringify({galat: "terapkanPreset tidak diekspor"})); process.exit(0); }
const sekarang = %s, preset = %s, keluarga = %s;
let out;
try { out = f(sekarang, preset, keluarga); }
catch (e) { out = {galat: String(e && e.message || e)}; }
console.log(JSON.stringify(out));
"""


def _jalankan(sekarang: dict, preset: dict, keluarga: list) -> dict:
    """Transpilasi `niche-dna.ts` apa adanya, lalu JALANKAN fungsinya di node."""
    if not os.path.exists(TSC):
        raise AssertionError(
            f"tsc repo tidak ada di {TSC} — uji ini WAJIB bisa menjalankan kode aslinya. "
            f"Jalankan `npm install` di apps/web. (Sengaja GAGAL, bukan dilewati: penjaga yang "
            f"melewatkan dirinya sendiri = penjaga yang lapuk.)"
        )
    tmp = tempfile.mkdtemp(prefix="ujipreset_")
    try:
        r = subprocess.run(
            [TSC, LIB_TS, "--outDir", tmp, "--module", "commonjs", "--target", "es2020",
             "--skipLibCheck"],
            capture_output=True, text=True, timeout=180,
        )
        js = os.path.join(tmp, "niche-dna.js")
        if not os.path.exists(js):
            raise AssertionError(f"transpilasi gagal:\n{r.stdout}\n{r.stderr}")
        skrip = _HARNESS % (json.dumps(js), json.dumps(sekarang), json.dumps(preset), json.dumps(keluarga))
        p = subprocess.run(["node", "-e", skrip], capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise AssertionError(f"node gagal: {p.stderr[:600]}")
        return json.loads(p.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TestPresetTakMenghapusMilikPemilikNiche(unittest.TestCase):
    """Perilaku akhir — dijalankan sungguhan, bukan dibaca."""

    @classmethod
    def setUpClass(cls):
        cls.hasil = _jalankan(DNA_NYATA, PRESET_B, KELUARGA)
        if "galat" in cls.hasil:
            raise AssertionError(cls.hasil["galat"])

    def test_larangan_agama_selamat(self):
        """§5b Lapis-2: `strict_prohibition` milik pemilik niche — preset gaya tak berhak menghapusnya."""
        self.assertEqual(self.hasil["hasil"].get("strict_prohibition"),
                         DNA_NYATA["strict_prohibition"],
                         "larangan agama niche HILANG karena satu klik preset gaya")

    def test_gaya_rupa_selamat(self):
        """`render_style` = satu-satunya alasan niche animasi/ilustrasi mungkin (14-Agu)."""
        self.assertEqual(self.hasil["hasil"].get("render_style"), DNA_NYATA["render_style"])

    def test_seluruh_properti_luar_keluarga_selamat(self):
        luar = [k for k in DNA_NYATA if k not in KELUARGA]
        hilang = [k for k in luar if self.hasil["hasil"].get(k) != DNA_NYATA[k]]
        self.assertEqual(hilang, [], f"properti di luar keluarga preset ikut terhapus: {hilang}")

    def test_preset_mengisi_kuncinya_sendiri(self):
        for k, v in PRESET_B.items():
            self.assertEqual(self.hasil["hasil"].get(k), v, f"preset gagal mengisi `{k}`")

    def test_pilih_satu_karakter_tak_menyisakan_sisa_preset_lama(self):
        """Keputusan 4-Jul: preset karakter = PILIH SATU. Kunci keluarga yang tak diisi preset baru
        WAJIB kosong — kalau tidak, tenant dapat gaya campuran yang tak pernah ia pilih."""
        self.assertEqual(self.hasil["hasil"].get("lighting", ""), "",
                         "sisa `lighting` dari gaya lama tertinggal ⇒ gaya campuran")

    def test_layar_diberi_tahu_apa_yang_terjadi(self):
        """Tenant harus bisa melihat akibatnya, bukan menebak (§3.6 UI layak tenant awam)."""
        for kunci in ("diisi", "dipertahankan", "dikosongkan"):
            self.assertIn(kunci, self.hasil, f"hasil tak memberi tahu `{kunci}` ke layar")
        self.assertIn("strict_prohibition", self.hasil["dipertahankan"])
        self.assertIn("lighting", self.hasil["dikosongkan"])


class TestEditorMemakaiFungsiBersama(unittest.TestCase):
    """Anti-regresi struktur: kalau editor merakit ulang objeknya sendiri, kontrak di atas bisa
    hidup di pustaka tapi MATI di layar — persis kelas 'MENANGKAP ≠ MENYAMPAIKAN' ([B31])."""

    def setUp(self):
        with open(EDITOR, encoding="utf-8") as f:
            self.src = f.read()

    def test_apply_visual_memanggil_fungsi_bersama(self):
        self.assertIn("terapkanPreset", self.src,
                      "editor tidak memakai `terapkanPreset` — preset bisa kembali menghapus properti")

    def test_tak_ada_lagi_perakitan_ulang_dari_kunci_inti(self):
        """Pola lama yang menghapus: `...Object.fromEntries(VISUAL_CORE_KEYS.map(...)), ...preset`."""
        self.assertNotIn("Object.fromEntries(VISUAL_CORE_KEYS.map((k) => [k, \"\"])), ...asDict(p.value)",
                         self.src, "pola perakitan-ulang yang menghapus properti masih ada")
        self.assertNotIn("Object.fromEntries(PERSONA_KEYS.map((k) => [k, \"\"])), ...asDict(p.value)",
                         self.src, "persona masih memakai pola yang sama (kelas cacat identik)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
