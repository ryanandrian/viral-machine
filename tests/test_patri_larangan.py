"""PATRI LARANGAN — tidak bisa dibatalkan, dan BERLAKU OTOMATIS untuk vendor/model yang belum ada.

Ketetapan owner 2026-08-13/14. Yang dipatri di kode hanya yang tetap menempel pada MesinViral walau
tenant sudah menyetujui apa pun: **Allah SWT · Nabi Muhammad ﷺ · tulisan Arab/Al-Qur'an yang terbaca
· keselamatan anak · konten seksual**. Selebihnya milik tenant lewat DNA niche + disclaimer.

⚠️ SYARAT YANG DITEKANKAN OWNER — "HARUS BERSIFAT GENERIK, BERLAKU UNTUK SETIAP PENAMBAHAN AI MODEL
BARU DAN ATAU AI VENDOR BARU KEDEPANNYA". Karena itu patri dipasang **sebelum pembagian ke vendor**
(`_generate_image` / `_generate_video`), bukan di dalam tiap transport. Uji
`test_vendor_yang_BELUM_ADA_otomatis_terikat` membuktikannya dengan mendaftarkan transport palsu
seolah vendor besok — tanpa menyentuh kode patri.

═══ TIGA JEBAKAN YANG DITUTUP SEBELUM SATU BARIS KODE DITULIS (semuanya terukur) ═══

1. **DAFTAR PER-VENDOR = KEBOCORAN.** Larangan gambar yang tenant tulis sendiri DIABAIKAN TOTAL oleh
   FLUX/Cloudflare — 6 dari 11 channel — karena FLUX tak punya kanal larangan dan tak ada yang
   membawa fakta itu naik ke fiturnya. Tenant mengetik, menyimpan, dan mesin tak pernah membacanya.
   Karena itu patri & larangan tenant dilipat ke prompt POSITIF di corong, bukan lewat daftar
   "transport mana yang butuh".

2. **PENYARING NAIF MEMBUNUH PRODUKSI SAH.** Uji-kering pada 679 prompt produksi NYATA: daftar
   kata-benda (mushaf/Qur'an/kaligrafi) memblokir **8** produksi sah; versi "berbasis niat" pertama
   masih memblokir **3** — dan ketiganya sah (halaman masjid sunyi *"melambangkan perjalanan Nabi
   Muhammad"* · mushaf terbuka *"perwujudan wahyu yang diterima Nabi Muhammad"* · timbangan
   *"merenungkan mukjizat Nabi Muhammad"*). Rancangan final: **BLOKIR** hanya niat tak terbantahkan,
   **KUATKAN** bila nama muncul sebagai konteks. Hasil: **0 dari 679 diblokir**.

3. **PATRI DIMAKAN PEMOTONG PROMPT.** Cloudflare memotong keras di 2.048 huruf. Patri ditempel di
   AKHIR agar berbicara terakhir — justru karena itu ia bagian PERTAMA yang hilang saat dipotong.
   Diukur: **12 dari 679 (2%)** melewati batas sesudah patri + larangan niche ikut. `potong_aman`
   mengorbankan rincian adegan, **tidak pernah** patri.
"""
import asyncio
import inspect
import io
import os
import re
import sys
import tokenize
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.providers.visual import patri                                    # noqa: E402
from src.providers.visual.ai_image import AIImageProvider                 # noqa: E402
from src.providers.visual.ai_video import AIVideoProvider                 # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _kode(path: str) -> str:
    """Isi berkas TANPA komentar — uji larangan menilai KODE, bukan penjelasannya."""
    toks = [t for t in tokenize.generate_tokens(io.StringIO(
        open(path, encoding="utf-8").read()).readline) if t.type != tokenize.COMMENT]
    return tokenize.untokenize(toks)


class _Gambar(AIImageProvider):
    """Provider gambar tanpa jaringan/katalog — hanya corong + transport penangkap."""

    def __init__(self, platform="vendor_uji", params=None):
        self.model_config = {"platform": platform, "model_id": "x", "params": params or {}}
        self.terkirim = None
        self.negatif = None

    async def _tangkap(self, prompt, negative_prompt, output_path):
        self.terkirim, self.negatif = prompt, negative_prompt


class _Video(AIVideoProvider):
    def __init__(self, platform="vendor_uji"):
        self.model_config = {"platform": platform, "model_id": "x", "params": {}}
        self.terkirim = None

    async def _tangkap(self, prompt, out_path, chosen_duration):
        self.terkirim = prompt
        return 8.0


def _kirim(p, prompt, negatif=""):
    asyncio.run(p._generate_image(prompt, negatif, "/tmp/uji.jpg"))
    return p.terkirim


def _daftar_vendor_uji(kasus):
    """Daftarkan transport palsu — dan SIMPAN daftar aslinya.

    ⚠️ `_TRANSPORTS` itu milik KELAS, bukan milik satu uji. Versi pertama berkas ini menambah
    'vendor_uji' tanpa mengembalikannya, dan uji LAIN yang menyisir seluruh transport (penggolongan
    galat per-penyedia) langsung merah — padahal kodenya sehat. Pencemaran antar-uji seperti ini
    persis "bug baru dari perbaikan" yang tidak boleh terjadi.
    """
    kasus._asli_img = AIImageProvider._TRANSPORTS
    kasus._asli_vid = AIVideoProvider._TRANSPORTS
    AIImageProvider._TRANSPORTS = dict(AIImageProvider._TRANSPORTS)
    AIImageProvider._TRANSPORTS["vendor_uji"] = "_tangkap"
    AIVideoProvider._TRANSPORTS = dict(AIVideoProvider._TRANSPORTS)
    AIVideoProvider._TRANSPORTS["vendor_uji"] = "_tangkap"


def _pulihkan_vendor_uji(kasus):
    AIImageProvider._TRANSPORTS = kasus._asli_img
    AIVideoProvider._TRANSPORTS = kasus._asli_vid


# ══ A. GENERIK — vendor/model baru otomatis terikat ══════════════════════════════════════════════

class TestA_Generik(unittest.TestCase):

    def setUp(self):
        _daftar_vendor_uji(self)

    def tearDown(self):
        _pulihkan_vendor_uji(self)

    def test_vendor_yang_BELUM_ADA_otomatis_terikat(self):
        """SYARAT OWNER. Vendor didaftarkan seolah ditambahkan besok — patri wajib ikut tanpa
        satu baris pun disentuh di kode patri."""
        t = _kirim(_Gambar(), "A quiet courtyard at dawn", "blurry")
        self.assertIn(patri.PATRI_GAMBAR, t,
                      "vendor baru menerima prompt TANPA patri — inilah cara kebocoran FLUX lahir")

    def test_SETIAP_transport_terdaftar_menerima_patri(self):
        """Bukan hanya vendor uji: seluruh transport yang terdaftar hari ini diperiksa satu per satu.
        Menambah transport tanpa membuat patri sampai = uji ini MERAH."""
        for platform in [k for k in AIImageProvider._TRANSPORTS if k != "vendor_uji"]:
            with self.subTest(platform=platform):
                p = _Gambar(platform)
                p._TRANSPORTS = dict(p._TRANSPORTS); p._TRANSPORTS[platform] = "_tangkap"
                self.assertIn(patri.PATRI_GAMBAR, _kirim(p, "a calm street at night"),
                              f"transport '{platform}' menerima prompt tanpa patri")

    def test_jalur_VIDEO_juga_terikat(self):
        v = _Video()
        asyncio.run(v._generate_video("a slow push-in on a mosque courtyard", "/tmp/x.mp4", 8.0))
        self.assertIn(patri.PATRI_GAMBAR, v.terkirim,
                      "jalur video tak punya kanal larangan — tanpa patri di prompt positif ia telanjang")

    def test_larangan_TENANT_ikut_ke_prompt_positif(self):
        """Kebocoran terukur: FLUX mengabaikan kanal larangan ⇒ larangan tenant harus dilipat ke
        prompt positif, bukan menunggu vendor berbaik hati."""
        t = _kirim(_Gambar(), "a street at night", "cartoon, watermark, extra fingers")
        self.assertIn("Avoid: cartoon, watermark, extra fingers", t,
                      "larangan yang tenant tulis sendiri tidak sampai ke mesin gambar")

    def test_patri_ditempel_SEBELUM_pembagian_ke_vendor(self):
        """Kalau ditempel di dalam transport, vendor berikutnya masuk tanpa patri."""
        for berkas, fungsi in ((os.path.join(AKAR, "src/providers/visual/ai_image.py"), "_generate_image"),
                               (os.path.join(AKAR, "src/providers/visual/ai_video.py"), "_generate_video")):
            src = _kode(berkas)
            blok = src[src.find(f"def {fungsi}"):]
            blok = blok[:blok.find("\n    async def ", 10) if "\n    async def " in blok[10:] else len(blok)]
            i_patri = blok.find("_patri.tempel")
            i_bagi = blok.find("_TRANSPORTS.get")
            self.assertTrue(0 <= i_patri < i_bagi,
                            f"{fungsi}: patri tidak ditempel sebelum pembagian vendor")

    def test_NOL_kode_memanggil_transport_vendor_langsung(self):
        """Jalan pintas = patri terlewati. Struktur ini yang menjaganya, bukan ingatan."""
        langgar = []
        for akar, _, berkas in os.walk(os.path.join(AKAR, "src")):
            for b in berkas:
                if not b.endswith(".py"):
                    continue
                path = os.path.join(akar, b)
                if path.endswith(("ai_image.py", "ai_video.py")):
                    continue
                isi = open(path, encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r"_generate_(dalle|cloudflare|gemini|fal)\s*\(", isi):
                    langgar.append(f"{os.path.relpath(path, AKAR)}: {m.group(0)}")
        self.assertFalse(langgar, "transport vendor dipanggil LANGSUNG (patri terlewati):\n  "
                         + "\n  ".join(langgar))


# ══ B. PEMOTONG PROMPT TIDAK BOLEH MEMAKAN PATRI ═════════════════════════════════════════════════

class TestB_PotongAman(unittest.TestCase):

    def test_patri_selamat_dari_pemotongan(self):
        panjang = "x" * 5000
        pos, _ = patri.tempel(panjang, "", kanal_negatif=False)
        hasil = patri.potong_aman(pos, 2048)
        self.assertLessEqual(len(hasil), 2048)
        self.assertTrue(hasil.endswith(patri.PATRI_GAMBAR),
                        "patri dimakan pemotong — 2% prompt produksi akan dibuat TANPA patri")

    def test_prompt_pendek_tidak_disentuh(self):
        p = "a short prompt"
        self.assertEqual(patri.potong_aman(p, 2048), p, "prompt yang muat malah diubah")

    def test_batas_dari_DATA_bukan_kode(self):
        """Vendor baru cukup menuliskan batasnya di `ai_models.default_params` — tanpa sentuh kode."""
        _daftar_vendor_uji(self)
        self.addCleanup(_pulihkan_vendor_uji, self)
        p = _Gambar("vendor_uji", {"prompt_max_chars": 300})
        t = _kirim(p, "y" * 900, "ban")
        self.assertLessEqual(len(t), 300)
        self.assertTrue(t.endswith(patri.PATRI_GAMBAR[-40:]), "patri tak selamat pada batas dari DATA")

    def test_cloudflare_memakai_pemotong_aman(self):
        src = _kode(os.path.join(AKAR, "src/providers/visual/ai_image.py"))
        # 2500, bukan 1500: docstring transport CF panjang (skema resmi + pelajaran false-positive).
        # Alat ukur yang terlalu pendek melapor pelanggaran yang tidak ada.
        blok = src[src.find("def _generate_cloudflare"):][:2500]
        self.assertIn("potong_aman", blok, "Cloudflare kembali memotong buta — patri jadi korban pertama")
        self.assertNotIn("prompt[:2048]", blok, "pemotongan buta masih ada")


# ══ C. PENYARING — keras pada pelanggaran, TIDAK membunuh produksi sah ═══════════════════════════

class TestC_Penyaring(unittest.TestCase):

    KASUS = [
        ("A cinematic portrait of Prophet Muhammad standing in Medina", "blokir"),
        ("Nabi Muhammad walking through the desert at dawn, face visible", "blokir"),
        ("A depiction of Allah in the clouds", "blokir"),
        ("Mosque wall with readable Quranic verse in gold", "blokir"),
        ("Dinding masjid dengan tulisan بسم الله", "blokir"),
        ("Empty moonlit courtyard symbolizing the journey of Nabi Muhammad", "kuatkan"),
        ("Open Mushaf representing the wahyu received by Nabi Muhammad", "kuatkan"),
        ("An open mushaf on a wooden rehal, oil lamp beside it", None),
        ("macro on calligraphy ink and prayer beads", None),
        ("A young man praying in a courtyard at golden hour, 3D animation", None),
    ]

    def test_dua_arah_sepuluh_kasus(self):
        for teks, harap in self.KASUS:
            with self.subTest(teks=teks[:40]):
                h = patri.periksa_prompt(teks)
                dapat = None if h is None else ("kuatkan" if h == "kuatkan" else "blokir")
                self.assertEqual(dapat, harap, f"penyaring salah untuk: {teks}")

    def test_patri_SENDIRI_tidak_memicu_penyaringnya(self):
        """Teks patri memuat 'depict … the Prophet Muhammad'. Kalau ikut diperiksa, penjaga akan
        memblokir prompt gara-gara kalimat penjaganya sendiri."""
        self.assertIsNone(patri.periksa_prompt(f"a calm street\n\n{patri.PATRI_GAMBAR}"),
                          "penjaga memblokir kalimatnya sendiri")
        self.assertIsNone(patri.periksa_prompt(f"a calm street\n\n{patri.PENEGAS_KONTEKS}"))

    def test_konteks_DIKUATKAN_bukan_diblokir(self):
        _daftar_vendor_uji(self)
        self.addCleanup(_pulihkan_vendor_uji, self)
        t = _kirim(_Gambar(), "Empty courtyard symbolizing the journey of Nabi Muhammad")
        self.assertIn(patri.PENEGAS_KONTEKS, t, "prompt konteks tidak dikuatkan")
        self.assertIn(patri.PATRI_GAMBAR, t)

    def test_pelanggaran_DITAHAN_sebelum_dikirim(self):
        _daftar_vendor_uji(self)
        self.addCleanup(_pulihkan_vendor_uji, self)
        p = _Gambar()
        with self.assertRaises(Exception):
            _kirim(p, "A cinematic portrait of Prophet Muhammad standing in Medina")
        self.assertIsNone(p.terkirim, "prompt terlarang TETAP DIKIRIM ke penyedia")

    def test_penyaring_GAGAL_TERBUKA(self):
        """Kesalahan di kode kami tak boleh menghentikan produksi tenant."""
        self.assertIsNone(patri.periksa_prompt(None))

    def test_NOL_prompt_produksi_lama_diblokir(self):
        """Angka yang menjaga janji: 0 dari seluruh prompt yang pernah diproduksi boleh diblokir."""
        try:
            from dotenv import load_dotenv
            from supabase import create_client
            load_dotenv(os.path.join(AKAR, ".env"))
            sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
            rows = sb.table("content_inventory").select("metadata").limit(1000).execute().data
        except Exception as e:                                        # noqa: BLE001
            self.skipTest(f"DB tak terbaca ({type(e).__name__}) — pemeriksaan ini menuntut data nyata")
        diblokir, total = [], 0
        for r in rows:
            for v in (((r.get("metadata") or {}).get("script") or {}).get("visual_suggestions") or []):
                total += 1
                h = patri.periksa_prompt(str(v))
                if h and h != "kuatkan":
                    diblokir.append(str(v)[:100])
        self.assertGreater(total, 100, "data prompt produksi terlalu sedikit untuk menilai")
        self.assertFalse(diblokir, f"{len(diblokir)} dari {total} prompt produksi SAH akan diblokir:\n  "
                         + "\n  ".join(diblokir[:5]))


# ══ D. LARANGAN NARASI TENANT = PENGHENTI, BUKAN SARAN ═══════════════════════════════════════════

class TestD_LaranganNarasi(unittest.TestCase):

    def test_naskah_pelanggar_menghentikan_run(self):
        src = _kode(os.path.join(AKAR, "src/intelligence/script_engine.py"))
        i = src.find('jenis") == "kata_terlarang_niche"')
        self.assertGreater(i, 0, "penghenti larangan niche tidak ada — larangan tenant kembali jadi saran")
        self.assertIn("raise LLMError", src[i:i + 700],
                      "pelanggaran hanya dicatat, tidak menghentikan")

    def test_cacat_mutu_lain_TIDAK_menghentikan(self):
        """Hanya larangan tenant yang menghentikan. Elipsis/spasi ganda tetap lewat jalur perbaikan —
        kalau tidak, produksi berhenti karena hal sepele."""
        src = _kode(os.path.join(AKAR, "src/intelligence/script_engine.py"))
        i = src.find('jenis") == "kata_terlarang_niche"')
        blok = src[max(0, i - 400):i + 700]
        for sepele in ("elipsis", "artefak_sambungan", "frasa_berulang"):
            self.assertNotIn(f'== "{sepele}"', blok, f"{sepele} ikut menghentikan run — terlalu galak")


# ══ E. GAYA VISUAL = MILIK NICHE, dan 47 niche lama TIDAK BERUBAH ════════════════════════════════

class TestE_GayaPerNiche(unittest.TestCase):

    def test_bawaan_membuat_teks_SAMA_PERSIS(self):
        """Bawaan 'photorealistic' di keenam titik — termasuk KAPITALISASI aslinya. Tiga titik dulu
        berhuruf besar; satu nilai bawaan yang disisipkan mentah akan mengubah teks 47 niche."""
        for berkas in ("src/intelligence/script_engine.py", "src/production/visual_assembler.py",
                       "src/providers/visual/ai_image.py"):
            src = _kode(os.path.join(AKAR, berkas))
            with self.subTest(berkas=berkas):
                self.assertNotIn('"photorealistic"', src.replace('or "photorealistic"', ""),
                                 "masih ada kata gaya yang dipatri di luar nilai bawaan")
        se_src = _kode(os.path.join(AKAR, "src/intelligence/script_engine.py"))
        self.assertEqual(se_src.count('gaya.capitalize()'), 2,
                         "kapitalisasi per-titik hilang → teks prompt 47 niche berubah")

    def test_gaya_niche_BENAR_BENAR_dipakai(self):
        _daftar_vendor_uji(self)
        self.addCleanup(_pulihkan_vendor_uji, self)
        p = _Gambar()
        p.niche_visual_style = {"render_style": "stylized 3D character animation",
                                "base_style": "b", "atmosphere": "a"}
        p.llm_models, p.llm_model_flat = {}, ""
        src = inspect.getsource(AIImageProvider._ai_rewrite_on_rejection)
        self.assertIn('niche_style.get("render_style")', src,
                      "penulis-ulang masih memaksa gaya foto-realistis")

    def test_no_people_frame_pembuka_TIDAK_disentuh(self):
        """Diputuskan sadar: judul pembuka digambar di 15% dari atas; membuka 'ada orang' di frame itu
        perubahan tersendiri dengan pertanyaannya sendiri."""
        src = _kode(os.path.join(AKAR, "src/production/visual_assembler.py"))
        self.assertIn("No people.", src, "'No people.' dicabut tanpa rencana tersendiri")


# ══ F. PENOLAKAN SAAT SIMPAN DNA (lapis kedua, di layar) ═════════════════════════════════════════

class TestF_PenolakanSimpan(unittest.TestCase):

    def test_validator_menolak_upaya_membatalkan_patri(self):
        s = open(os.path.join(AKAR, "apps/web/src/lib/niche-dna.ts"), encoding="utf-8").read()
        self.assertIn("PATRI_BYPASS", s, "penolakan saat simpan tidak ada")
        for pola in ("abaikan", "ignore", "gambarkan", "depict"):
            self.assertIn(pola, s, f"pola '{pola}' tak dijaga saat simpan")

    def test_kedua_pintu_tulis_memakai_validator(self):
        for rute in ("apps/web/src/app/api/niches/mine/route.ts",
                     "apps/web/src/app/api/admin/niches/[id]/route.ts"):
            s = open(os.path.join(AKAR, rute), encoding="utf-8").read()
            self.assertIn("validateDnaPatch", s, f"{rute} tidak memvalidasi DNA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
