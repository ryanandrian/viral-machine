"""LARANGAN NASKAH: satu aturan, satu angka, dan NOL biaya durasi yang tak dianggarkan.

Ditulis 2026-08-13 setelah owner meminta penilaian ulang seluruh larangan hardcode "dari sudut
pandang kebutuhan viral", lalu memperingatkan: *"perubahan anda jika salah bisa merusak metode preset
durasi quality"*. Peringatan itu TERBUKTI BENAR — satu dari empat usulan diukur dan **dicabut** karena
merusak durasi (lihat §CABUT di bawah). Tiga yang tersisa dikerjakan, dan berkas ini yang menjaganya.

═══ P4 — ELIPSIS: MESIN BERHENTI BERTENGKAR DENGAN DIRINYA SENDIRI ═══
Sebelum ini, satu prompt yang sama berkata DUA hal yang saling membatalkan:
  • *"NEVER use '...' (ellipsis): one ellipsis burns >1 second of silence"*
  • *"Ellipsis (…) sparingly for suspense: 'No one knew what was coming…'"*
dan pemeriksa naskah menandai SETIAP elipsis sebagai cacat. Penulis naskah menerima perintah yang
mustahil dipatuhi sekaligus.
Lebih buruk: **alasannya salah**. Angka TERLATIH per suara di `tts_pace_calibration` (dibaca 13-Agu):
Ardi 0,156 · Guy 0,204 · Gadis 0,288 · Jenny 0,300 · Christopher 0,376 detik — **setara satu koma**,
dan 4–8× LEBIH MURAH dari titik akhir kalimat (0,85–1,37 dtk). Jadi elipsis tak pernah jadi risiko
durasi. Sekarang: SATU jatah (klimaks), satu angka dipakai prompt & pemeriksa.

═══ P3 — GEMA PENUTUP: MENGGANTI, BUKAN MENAMBAH ═══
Bookend (menutup dengan kalimat pembuka yang kini bermakna lain) adalah alat retensi terkuat di
format pendek, tapi dulu terlarang oleh *"FORBIDDEN: Repeating anything said before"*.
⛔ SYARAT DURASI yang dijaga berkas ini: ia MENGGANTIKAN kalimat penutup. Terukur pada kalibrasi
hidup, satu kalimat ±10 kata = **±4,4 dtk** pada suara Ardi = 7% dari preset 60 dtk — kalau
ditambahkan, ia memakan jatah cerita dan mendekati ambang QC 15%.

═══ P1 — MODE CTA KETIGA (`explicit`) ═══
Dulu hanya `implicit` (10 channel) & `soft_sell` (1) — **keduanya melarang meminta apa pun**, jadi
tak ada satu pun cara mengubah penonton jadi pengikut. Mode ketiga membuka SATU pintu sempit: ajakan
yang khas video itu + alasannya, MENGGANTIKAN kalimat penutup. Larangan ajakan GENERIK tetap penuh.

═══ §CABUT — YANG SENGAJA TIDAK DIKERJAKAN (jangan dihidupkan tanpa rencana sendiri) ═══
Usulan "panjang kalimat & sudut pandang pindah ke DNA niche" **DICABUT setelah diukur**. Rumus
anggaran memakai `words_per_sentence` sebagai PENYEBUT, dan angka itu dilatih per-suara dari naskah
nyata. Mengubah perintah panjang kalimat TANPA mengubah rumusnya menghasilkan (preset 60 dtk, Ardi):
15 kata/kalimat → −7,9% · 20 → **−14,4%** · 25 → **−18,4%** · 30 → **−21,0%**.
Toleransi naskah 12%, QC 15% ⇒ mulai 20 kata sudah keluar jalur, di 25 kata **QC MENOLAK**. Bahaya
kedua: `words_per_sentence` dilatih per-SUARA lintas-niche (`niche='*'`) ⇒ satu niche berkalimat
panjang menggeser durasi SEMUA niche lain di suara itu.
"""
import ast
import inspect
import io
import os
import re
import sys
import tokenize
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence import script_checker as sc            # noqa: E402
from src.intelligence import script_engine as se             # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENERBIT = os.path.join(AKAR, "src", "distribution", "youtube_publisher.py")
LAYAR_CHANNEL = os.path.join(AKAR, "apps", "web", "src", "app", "(app)", "channels", "[id]", "page.tsx")


def _kode(path: str) -> str:
    """Isi berkas Python TANPA komentar — uji larangan menilai KODE, bukan penjelasannya.
    (Pelajaran 13-Agu: sabotase lolos karena penjaga menemukan kalimatnya di dalam komentar.)"""
    toks = [t for t in tokenize.generate_tokens(io.StringIO(
        open(path, encoding="utf-8").read()).readline) if t.type != tokenize.COMMENT]
    return tokenize.untokenize(toks)


def _teks(path: str) -> str:
    return open(path, encoding="utf-8", errors="ignore").read()


def _prompt(**kw) -> str:
    """Prompt naskah yang benar-benar dikirim ke penulis, untuk topik netral."""
    return se._build_user_prompt({"topic": "Sunnah bangun pagi", "angle": ""},
                                "kisah_teladan_islami", **kw)


# ══ P4. ELIPSIS ═════════════════════════════════════════════════════════════════════════════════

class TestP4_Elipsis(unittest.TestCase):

    def test_tak_ada_lagi_perintah_yang_bertabrakan(self):
        """Inti P4: tidak boleh ada satu pun perintah 'jangan pernah pakai elipsis' yang hidup
        bersamaan dengan perintah 'pakai sesekali untuk ketegangan'."""
        k = _kode(os.path.join(AKAR, "src", "intelligence", "script_engine.py"))
        for pola in (r"NEVER use '\.\.\.'", r"Never use '\.\.\.'", r"TANPA tanda '\.\.\.'"):
            self.assertIsNone(re.search(pola, k),
                              f"perintah lama {pola!r} hidup lagi — mesin akan bertengkar dengan "
                              f"dirinya sendiri seperti sebelum 13-Agu")

    def test_satu_jatah_dipakai_prompt_DAN_pemeriksa(self):
        self.assertEqual(sc._MAKS_ELIPSIS, 1, "jatah elipsis berubah tanpa alasan tercatat")
        p = _prompt(preset_seconds=60, resep_durasi={"kata_min": 120, "kata_maks": 150,
                                                    "kata_bidik": 136, "kalimat": 12})
        self.assertRegex(p, r"AT MOST ONE|maksimal SATU",
                         "prompt tidak menyebut jatah elipsis — penulis naskah tak tahu batasnya")
        self.assertRegex(p, r"climax only|klimaks",
                         "jatah disebut tapi tanpa TEMPATnya (klimaks) → dipakai sembarangan")

    def test_angka_biaya_yang_SALAH_tidak_kembali(self):
        """Angka lama (">1 second", "≈0.6–1.0s") melebihkan 3–6× dari kalibrasi hidup. Angka yang
        dilebihkan membuat penulis naskah menghindari alat drama yang sebenarnya murah."""
        k = _kode(os.path.join(AKAR, "src", "intelligence", "script_engine.py"))
        for salah in ("burns >1 second", "burns over a second", "≈0.6–1.0s"):
            self.assertNotIn(salah, k, f"angka biaya jeda yang keliru kembali: {salah!r}")
        self.assertIn("0.16–0.38s", k, "angka TERUKUR tidak disebut — penulis tak punya acuan benar")

    def test_satu_elipsis_BERSIH_dua_ditandai(self):
        bersih = "Ini kalimat pertama. Tak ada yang menduga apa yang datang… Semua berubah."
        dua    = "Ini pertama… lalu kedua… dan berubah."
        j1 = [x["jenis"] for x in sc.periksa_naskah(bersih)]
        j2 = [x["jenis"] for x in sc.periksa_naskah(dua)]
        self.assertNotIn("elipsis", j1, "satu elipsis (jatah sah) masih ditandai cacat")
        self.assertIn("elipsis", j2, "dua elipsis lolos — jatahnya tidak ditegakkan")

    def test_biaya_elipsis_MEMANG_dihargai_mesin_durasi(self):
        """Mengizinkan elipsis hanya aman bila mesin durasi menghitungnya. Diperiksa langsung ke
        model durasi, bukan diasumsikan."""
        from src.production.duration_model import BAWAAN, ciri_teks
        self.assertIn("sec_per_ellipsis", BAWAAN, "mesin durasi tak punya suku biaya elipsis")
        self.assertGreater(BAWAAN["sec_per_ellipsis"], 0)
        self.assertEqual(ciri_teks("Satu… dua.")["ellipsis"], 1, "elipsis tak ikut terhitung")
        # dan tetap MURAH dibanding titik — dasar keputusan melonggarkannya
        self.assertLess(BAWAAN["sec_per_ellipsis"], BAWAAN["sec_per_sentence"] / 2,
                        "premis P4 patah: elipsis ternyata tidak lebih murah dari titik")


# ══ P3. GEMA PENUTUP ════════════════════════════════════════════════════════════════════════════

class TestP3_GemaPenutup(unittest.TestCase):

    def _p(self) -> str:
        return _prompt(preset_seconds=60, resep_durasi={"kata_min": 120, "kata_maks": 150,
                                                       "kata_bidik": 136, "kalimat": 12})

    def test_gema_diizinkan_sebagai_penutup(self):
        self.assertRegex(self._p(), r"Bookend echo|bookend",
                         "gema penutup tidak pernah ditawarkan ke penulis naskah")

    def test_WAJIB_mengganti_bukan_menambah(self):
        """⛔ PENJAGA DURASI. Kalau gema ditambahkan alih-alih mengganti, satu kalimat ±10 kata =
        ±4,4 dtk pada suara Ardi = 7% dari preset 60 dtk, memakan jatah cerita."""
        p = self._p()
        i = p.find("Bookend echo")
        self.assertGreater(i, 0)
        cuplik = p[i:i + 420]
        self.assertIn("REPLACES", cuplik,
                      "gema tidak dinyatakan MENGGANTIKAN penutup → durasi bertambah tanpa anggaran")
        self.assertRegex(cuplik, r"never add it on top|jangan menambah",
                         "larangan menambah tidak eksplisit — model akan menambahkan")

    def test_pengulangan_TAK_SENGAJA_tetap_terlarang(self):
        p = self._p()
        self.assertRegex(p, r"accidental repetition|Restating a fact already given",
                         "larangan pengulangan tak sengaja hilang — naskah jadi bertele-tele")

    def test_gema_TIDAK_tertangkap_pemeriksa_frasa_berulang(self):
        """Bookend = frasa muncul 2×. Pemeriksa menandai ≥3×. Diuji, bukan diasumsikan."""
        gema = ("Langit malam itu menyimpan rahasia. "
                "Pada 1965 seorang nelayan menemukan bangkai kapal di kedalaman dua ratus meter. "
                "Catatan pelayaran menyebut delapan awak hilang tanpa jejak apa pun. "
                "Penyelidik menutup berkasnya empat tahun kemudian tanpa satu kesimpulan. "
                "Langit malam itu menyimpan rahasia.")
        jenis = [x["jenis"] for x in sc.periksa_naskah(gema)]
        self.assertNotIn("frasa_berulang", jenis,
                         "gema penutup (2 kemunculan) ditandai cacat → P3 mustahil dipakai")

    def test_tiga_kemunculan_TETAP_ditandai(self):
        tiga = ("Rahasia itu nyata. " * 3) + "Catatan sejarah menyebut peristiwa besar itu berulang kali."
        self.assertIn("frasa_berulang", [x["jenis"] for x in sc.periksa_naskah(tiga)],
                      "pengulangan 3× lolos — profil yang didemonetisasi YouTube")


# ══ P1. MODE CTA `explicit` ═════════════════════════════════════════════════════════════════════

class TestP1_AjakanSpesifik(unittest.TestCase):

    def test_blok_izin_HANYA_muncul_di_mode_explicit(self):
        for mode in ("implicit", "soft_sell"):
            self.assertNotIn("EXPLICIT-CTA MODE", _prompt(cta_mode=mode, brand_name="Merek"),
                             f"pintu ajakan terbuka di mode {mode} — perubahan perilaku tak diminta")
        self.assertIn("EXPLICIT-CTA MODE", _prompt(cta_mode="explicit"),
                      "mode explicit tidak mengizinkan apa pun — tak ada gunanya")

    def test_larangan_ajakan_GENERIK_tetap_berlaku_di_semua_mode(self):
        for mode in ("implicit", "soft_sell", "explicit"):
            p = _prompt(cta_mode=mode, brand_name="Merek")
            self.assertIn("Smash the like button", p, f"pagar anti-generik hilang di mode {mode}")
            self.assertRegex(p, r"'Follow', 'Subscribe'", f"daftar larangan rusak di mode {mode}")

    def test_ajakan_WAJIB_mengganti_penutup(self):
        """⛔ PENJAGA DURASI kedua: ajakan hidup di JATAH bagian penutup, tidak menambah kalimat."""
        p = _prompt(cta_mode="explicit")
        i = p.find("EXPLICIT-CTA MODE")
        cuplik = p[i:i + 900]
        self.assertRegex(cuplik, r"MENGGANTIKAN kalimat penutup",
                         "ajakan tidak dinyatakan mengganti → durasi bertambah tanpa anggaran")
        self.assertRegex(cuplik, r"jatah kata bagian CTA tidak berubah|BUKAN menambah",
                         "syarat jatah kata tidak disebut")

    def test_ajakan_wajib_KHAS_video_itu(self):
        cuplik = _prompt(cta_mode="explicit")
        self.assertRegex(cuplik, r"HANYA masuk akal untuk video/topik/channel INI",
                         "ajakan generik akan lolos — itu justru yang menurunkan mutu")

    def test_arahan_pemilik_channel_ikut_bila_diisi(self):
        p = _prompt(cta_mode="explicit", brand_cta_text="besok bahas sunnah bangun tidur")
        self.assertIn("besok bahas sunnah bangun tidur", p, "arahan pemilik channel diabaikan")

    def test_footer_deskripsi_ikut_mode_explicit(self):
        k = _kode(PENERBIT)
        self.assertRegex(k, r'mode in \("soft_sell", "explicit"\)',
                         "footer deskripsi tidak mengenal mode explicit → tenant mengisi teks CTA "
                         "tapi tak muncul di mana pun")

    def test_kata_yang_DITULIS_TENANT_SENDIRI_tak_dituduh_melanggar(self):
        """Niche melarang kata X; tenant menulis X di teks ajakannya sendiri. Menolak naskahnya =
        mesin membatalkan setelan tenant tanpa memberi tahu."""
        niche = {"narration_persona": {"avoid": "subscribe"}}
        teks = "Ini kisahnya. Kalau mau kebagian, subscribe sekarang juga ya."
        tanpa_izin = [x["jenis"] for x in sc.periksa_naskah(teks, niche_profile=niche)]
        dengan_izin = [x["jenis"] for x in sc.periksa_naskah(
            teks, niche_profile=niche, teks_ajakan_channel="subscribe untuk bagian berikutnya")]
        self.assertIn("kata_terlarang_niche", tanpa_izin, "prasyarat uji tak terpenuhi")
        self.assertNotIn("kata_terlarang_niche", dengan_izin,
                         "kata yang tenant tulis sendiri masih dituduh melanggar")

    def test_larangan_niche_TETAP_berkuasa_di_luar_teks_ajakan(self):
        """Pengecualian tidak boleh jadi pintu belakang: kata terlarang LAIN tetap ditangkap."""
        niche = {"narration_persona": {"avoid": "subscribe, magis"}}
        teks = "Peristiwa itu terjadi secara magis pada tahun 1965."
        jenis = [x["jenis"] for x in sc.periksa_naskah(
            teks, niche_profile=niche, teks_ajakan_channel="subscribe untuk bagian berikutnya")]
        self.assertIn("kata_terlarang_niche", jenis,
                      "pengecualian ajakan melumpuhkan seluruh larangan niche")

    def test_layar_channel_menawarkan_TIGA_pilihan(self):
        s = _teks(LAYAR_CHANNEL)
        for v in ('"implicit"', '"soft_sell"', '"explicit"'):
            self.assertIn(v, s, f"pilihan {v} tak ada di layar — kenop mati bagi tenant")
        self.assertRegex(s, r'ctaMode === "explicit"',
                         "mode explicit tak punya isian arahannya di layar")


# ══ ANTI-REGRESI DURASI (§7.3 — gerbang terkunci) ═══════════════════════════════════════════════

class TestDurasiTidakDisentuh(unittest.TestCase):
    """Ketiga perubahan ini menyentuh TEKS PERINTAH, bukan rumus durasi. Uji di sini memastikan
    rumus & angkanya benar-benar tak tergeser — dan bahwa usulan yang DICABUT tetap tercabut."""

    def test_rumus_anggaran_kata_tidak_berubah(self):
        from src.production import duration_model as dm
        k = inspect.getsource(dm.resep)
        self.assertIn("jeda_per_kalimat / a[\"words_per_sentence\"]", k,
                      "penyebut rumus anggaran berubah — durasi seluruh preset ikut bergeser")

    def test_panjang_kalimat_TETAP_dari_kalibrasi_bukan_dari_niche(self):
        """§CABUT. Kalau suatu saat panjang kalimat diambil dari niche TANPA ikut masuk rumus
        anggaran, durasi melenceng −8% s/d −21% (terukur) dan QC menolak di ≥25 kata/kalimat."""
        k = _kode(os.path.join(AKAR, "src", "intelligence", "script_engine.py"))
        self.assertNotRegex(
            k, r"narration_persona.{0,40}(sentence_max_words|max_words_per_sentence|point_of_view)",
            "panjang kalimat/sudut pandang mulai dibaca dari DNA niche — usulan ini DICABUT karena "
            "merusak durasi; hidupkan hanya lewat rencana sendiri yang juga mengubah rumus anggaran "
            "dan memisahkan kalibrasi per-niche")

    def test_perintah_jumlah_kalimat_masih_dikirim(self):
        p = _prompt(preset_seconds=60, resep_durasi={"kata_min": 120, "kata_maks": 150,
                                                    "kata_bidik": 136, "kalimat": 12})
        self.assertRegex(p, r"About 12 sentences", "perintah jumlah kalimat hilang — model menaati "
                                                  "jumlah kalimat jauh lebih baik daripada jumlah kata")
        self.assertRegex(p, r"TOTAL 120–150 words", "batas kata total hilang")


if __name__ == "__main__":
    unittest.main(verbosity=2)
