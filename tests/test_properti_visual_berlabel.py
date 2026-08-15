"""SETIAP PROPERTI VISUAL NICHE WAJIB PUNYA LABEL MANUSIAWI — TERMASUK YANG DITAMBAHKAN BESOK.

CACAT YANG DIJAGA (terukur 2026-08-15, `SISA_KERJA [B32]` T3)
Editor DNA hanya memberi label pada **3** kunci `visual_style` (`base_style`/`color_palette`/
`atmosphere`). **13 kunci lain** — yang justru dipakai 47–48 dari 48 niche — tampil sebagai **nama kode
Inggris di kotak kosong**: `color_grading`, `strict_prohibition`, `render_style`, … Tenant Business yang
membuka Niche Studio melihat 3 kotak yang bisa dipahami dan 11 kotak yang tidak.

Itu melanggar DUA hal yang sudah diketok owner:
  • `NICHE_DNA_AUDIT_REMEDIATION §2` butir 2 (4-Jul): *"NOL JSON mentah — setiap properti dipecah jadi
    field ber-label bahasa awam + placeholder contoh nyata + penjelasan 1 kalimat 'apa dampaknya ke video'"*
  • `DESAIN_PRODUK_SAAS §5b` Lapis-2 (14-Agu): tingkat aniconism & gaya rupa = **"milik pemilik niche,
    TERLIHAT & bisa diubah"**. `strict_prohibition` bernama kode = tidak "terlihat".

KENAPA UJI INI MEMBACA DAFTAR KUNCINYA DARI DATABASE, BUKAN DARI DAFTAR DI DALAM UJI:
supaya ia MERAH otomatis ketika properti ke-17 lahir tanpa label. Kalau daftarnya dihafal di sini,
penjaga ini buta terhadap yang baru — persis kelas kesalahan yang dibayar mahal di
`test_rute_api_terjaga.py` (04-Agu). Deklarasi label pun DIJALANKAN (transpilasi `tsc` repo → node),
bukan dicocokkan teksnya (pelajaran [B30] butir 2: uji PERILAKU AKHIR).
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

# `camera_motion` sengaja di luar daftar teks: ia objek bersarang dan SUDAH punya seksi sendiri
# ("Gerakan Kamera", 4 tombol berlabel awam) — bukan kotak teks.
BUKAN_KOTAK_TEKS = {"camera_motion"}


def _deklarasi_label() -> dict:
    """Jalankan `VISUAL_PROPS` dari lib/niche-dna.ts apa adanya."""
    if not os.path.exists(TSC):
        raise AssertionError(f"tsc repo tidak ada di {TSC} — jalankan `npm install` di apps/web. "
                             f"Sengaja GAGAL, bukan dilewati.")
    tmp = tempfile.mkdtemp(prefix="ujilabel_")
    try:
        subprocess.run([TSC, LIB_TS, "--outDir", tmp, "--module", "commonjs", "--target", "es2020",
                        "--skipLibCheck"], capture_output=True, text=True, timeout=180)
        js = os.path.join(tmp, "niche-dna.js")
        if not os.path.exists(js):
            raise AssertionError("transpilasi lib/niche-dna.ts gagal")
        p = subprocess.run(
            ["node", "-e", f'const m=require({json.dumps(js)});console.log(JSON.stringify(m.VISUAL_PROPS||null));'],
            capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise AssertionError(f"node gagal: {p.stderr[:400]}")
        return json.loads(p.stdout.strip().splitlines()[-1]) or {}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _kunci_dipakai_produksi() -> dict:
    """Kunci `visual_style` yang BENAR-BENAR dipakai 48 niche di DB — sumbernya kenyataan, bukan hafalan."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(AKAR, ".env"))
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    rows = sb.table("niches").select("niche_id,visual_style").execute().data or []
    pakai: dict[str, int] = {}
    for r in rows:
        for k in (r.get("visual_style") or {}):
            pakai[k] = pakai.get(k, 0) + 1
    return pakai


class TestSetiapPropertiVisualPunyaLabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.props = _deklarasi_label()
        cls.dipakai = _kunci_dipakai_produksi()

    def test_deklarasi_ada(self):
        self.assertTrue(self.props, "`VISUAL_PROPS` belum ada di lib/niche-dna.ts — properti visual "
                                    "masih tampil sebagai nama kode di layar admin & tenant")

    def test_semua_kunci_produksi_terdeklarasi(self):
        kurang = sorted(k for k in self.dipakai if k not in BUKAN_KOTAK_TEKS and k not in self.props)
        self.assertEqual(kurang, [], f"kunci dipakai niche tapi TANPA label manusiawi: "
                                     f"{[(k, self.dipakai[k]) for k in kurang]}")

    def test_tiap_deklarasi_lengkap_dan_dwibahasa(self):
        """§3.5: teks UI dwibahasa. §2 butir 2: label + penjelasan dampak + contoh nyata."""
        for kunci, d in self.props.items():
            with self.subTest(kunci=kunci):
                for bidang in ("label", "labelEn", "hint", "hintEn", "contoh"):
                    self.assertIn(bidang, d, f"`{kunci}` tak punya `{bidang}`")
                    self.assertTrue(str(d[bidang]).strip(), f"`{kunci}`.{bidang} kosong")
                # Label Indonesia WAJIB berbeda dari nama kunci (kuncinya bahasa Inggris).
                self.assertNotEqual(d["label"].strip().lower(), kunci.lower(),
                                    f"`{kunci}`: label Indonesia masih nama kode, bukan bahasa awam")
                # Label Inggris BOLEH kebetulan sama kata dengan kuncinya ("Atmosphere", "Lighting")
                # — itu memang kata manusia. Yang dilarang: bentuk KODE (snake_case).
                self.assertNotIn("_", d["labelEn"], f"`{kunci}`: label EN masih bentuk kode (snake_case)")
                self.assertNotIn("_", d["label"], f"`{kunci}`: label ID masih bentuk kode (snake_case)")

    def test_larangan_dan_gaya_rupa_ikut_berlabel(self):
        """Dua properti §5b Lapis-2 yang WAJIB 'terlihat' bagi pemilik niche."""
        for kunci in ("strict_prohibition", "render_style"):
            self.assertIn(kunci, self.props, f"`{kunci}` (§5b Lapis-2) masih tanpa label")


class TestEditorMerenderDariDeklarasi(unittest.TestCase):
    """Deklarasi yang tak dibaca layar = label yang tak pernah sampai ke tenant ([B31]: MENANGKAP ≠ MENYAMPAIKAN)."""

    def setUp(self):
        with open(EDITOR, encoding="utf-8") as f:
            self.src = f.read()

    def test_editor_memakai_deklarasi(self):
        self.assertIn("VISUAL_PROPS", self.src, "editor tidak membaca deklarasi label")

    def test_kotak_bernama_kode_hanya_untuk_properti_di_luar_deklarasi(self):
        """Kontrak sebenarnya: kunci YANG TERDEKLARASI wajib tampil berlabel. Kunci yang ditambahkan
        sendiri oleh pemilik niche ("properti tambahan") boleh tampil apa adanya — tak ada label yang
        bisa dikarang untuk kata yang ia ciptakan sendiri; dan `test_semua_kunci_produksi_terdeklarasi`
        di atas memastikan cabang itu tak pernah kena properti yang benar-benar dipakai produksi.
        Yang dijaga di sini: cabang nama-kode HARUS bersyarat `!(k in VISUAL_PROPS)`."""
        i = self.src.find('className="mono"')
        while i != -1:
            potongan = self.src[max(0, i - 700):i]
            if "<Fld" in potongan.rsplit("<Fld", 1)[-1] or "label={<span" in self.src[i - 40:i]:
                self.assertIn("!(k in VISUAL_PROPS)", potongan,
                              "ada kotak bernama kode TANPA syarat 'di luar deklarasi' — properti "
                              "resmi bisa kembali tampil sebagai kode mentah di layar")
                break
            i = self.src.find('className="mono"', i + 1)
        self.assertIn("!(k in VISUAL_PROPS)", self.src,
                      "cabang properti-tambahan tak lagi bersyarat deklarasi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
