"""DESAIN SENDIRI WAJIB DITAATI: yang dikirim ke vendor adalah ID VENDOR, di SEMUA jenis.

Desain katalog (ARSITEKTUR_AI_PROVIDER_MODEL §2): tiap model punya `model_key` (kunci KATALOG kita,
yang disimpan di setelan channel tenant) dan `model_id` (**ID resmi vendor** — "model string untuk
API call"). Produksi WAJIB memakai `model_id`.

Terukur 22-Agu, dan ini melanggar desain itu:
  · naskah  → `resolve_model_id` dipakai di 3 adapter        ✅ taat
  · gambar  → `model_id` dari baris katalog                  ✅ taat
  · video   → `model_id` dari baris katalog                  ✅ taat
  · SUARA   → `channels.tts_model` (= `model_key`) dikirim APA ADANYA ke vendor   ❌ MELANGGAR

Akibat yang menunggu: model suara ber-`model_key` ≠ `model_id` akan **LULUS tombol Uji** (uji memakai
`model_id`, `model_tester` sudah benar) tapi **PASTI GAGAL produksi**. Uji yang berbohong = kelas
kerusakan paling mahal. Persis insiden yang membuat penerjemahan ditambahkan ke jalur naskah 20-Jul —
perbaikan itu tak pernah dibawa ke jalur suara.

Owner 22-Agu: *"kita harus konsisten dan taat dengan desain yang kita buat sendiri, jangan buat
aturan baru lagi yang melanggar desain."* ⇒ solusinya MENERJEMAHKAN, bukan melarang `key ≠ id`.

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

ENGINE = "src/production/tts_engine.py"
LAYAR  = "apps/web/src/app/admin/(panel)/catalog/page.tsx"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


class TestA_JalurSuaraMemakaiIdVendor(unittest.TestCase):

    def test_config_tts_diterjemahkan_ke_model_id(self):
        src = _baca(ENGINE)
        i = src.find('"tts_model":')
        self.assertGreater(i, 0, "penyusun config TTS tak ditemukan")
        baris = src[i:src.find("\n", i)]
        # Yang dikunci: nilai config = HASIL penerjemahan. `rc.tts_model` boleh tetap muncul —
        # ia memang sumbernya — asalkan DIBUNGKUS penerjemah, bukan dikirim mentah.
        self.assertTrue(
            re.search(r'"tts_model":\s*_resolve_model_id\(', baris),
            "Config TTS mengirim `channels.tts_model` (kunci KATALOG) APA ADANYA ke vendor. Desain "
            "menetapkan produksi memakai `model_id`. Model ber-key≠id akan LULUS Uji tapi GAGAL "
            f"produksi — uji yang berbohong. Baris sekarang: {baris.strip()[:110]}")

    def test_memakai_penerjemah_yang_SUDAH_ADA(self):
        """Jangan membangun penerjemah kedua: `resolve_model_id` sudah ada, generik (membaca
        `ai_models` seluruh jenis), dan sudah fail-safe. Penerjemah kedua = dua sumber kebenaran."""
        src = _baca(ENGINE)
        self.assertTrue(
            re.search(r"from\s+src\.providers\.llm\.catalog\s+import[^\n]*resolve_model_id"
                      r"|resolve_model_id", src),
            "penerjemah yang sudah ada tidak dipakai")
        self.assertNotIn(
            'table("ai_models")', src,
            "tts_engine mengueri katalog sendiri ⇒ penerjemah kedua, dua sumber kebenaran")

    def test_fail_safe_dipertahankan(self):
        """`resolve_model_id` sengaja mengembalikan nama apa adanya bila katalog gagal dibaca —
        jangan memblokir produksi karena blip katalog. Jalur suara tak boleh membuatnya fatal."""
        src = _baca("src/providers/llm/catalog.py")
        i = src.find("def resolve_model_id")
        blok = src[i:src.find("\ndef ", i + 10)]
        # Jangkar = cabang EXCEPT-nya. `return name` juga ada di guard awal (`if not name`), jadi
        # mencarinya di seluruh fungsi tetap hijau walau fail-safe-nya dicabut — sabotase membuktikan.
        j = blok.find("except")
        self.assertGreater(j, 0, "penerjemah tak punya cabang except ⇒ tidak fail-safe")
        self.assertIn(
            "return name", blok[j:],
            "fail-safe penerjemah hilang: galat baca katalog tak lagi jatuh ke nama apa adanya ⇒ "
            "blip katalog akan MEMBLOKIR produksi suara.")
        self.assertNotIn("raise", blok[j:],
                         "cabang except MELEMPARKAN galat ⇒ produksi berhenti karena blip katalog")

    def test_uji_admin_TETAP_memakai_model_id(self):
        """`model_tester` sudah benar sejak awal. Perbaikan ini MENYELARASKAN produksi dengan uji —
        haram membalik arahnya (membuat uji memakai model_key)."""
        src = _baca("src/config/model_tester.py")
        i = src.find('"tts_model"')
        self.assertGreater(i, 0)
        self.assertIn("model_id", src[i:i + 120],
                      "uji admin tak lagi memakai ID vendor ⇒ arah perbaikan terbalik")


class TestB_KolomIdentitasTerkunciSaatDipakai(unittest.TestCase):
    """Owner 22-Agu: *"tombol edit berbahaya jika dibiarkan terbuka penuh… untuk kolom yang tidak
    boleh diubah karena sudah ada tenant yang menggunakan maka harus dibuat readonly."*

    Terukur: `model_key` SUDAH terkunci (PK). Tiga kolom lain masih terbuka, dan ketiganya
    berbahaya bila model sudah dipakai channel:
      · `provider_key` → model pindah vendor ⇒ kunci tenant diambil dari vendor yang SALAH
      · `component`    → jenis berubah ⇒ channel memakai model di slot yang salah
      · `model_id`     → SELURUH tenant pemakainya berpindah model TANPA memilih (= ikut campur
                         data tenant, yang owner larang)
    Nol cascade ke `channels` (terukur: 0 FK ke `ai_models`), jadi tak ada jaring pengaman."""

    def test_kolom_identitas_terkunci_bila_dipakai(self):
        layar = _baca(LAYAR)
        self.assertIn("KOLOM_TERKUNCI_BILA_DIPAKAI", layar,
                      "tak ada daftar kolom yang dikunci saat model dipakai tenant")
        i = layar.find("KOLOM_TERKUNCI_BILA_DIPAKAI")
        blok = layar[i:i + 500]
        for k in ("provider_key", "component", "model_id"):
            self.assertIn(k, blok, f"`{k}` tak ikut dikunci padahal mengubahnya merusak channel")

    def test_kunci_HANYA_saat_benar_benar_dipakai(self):
        """Model yang nol pemakai HARUS tetap bisa disunting — kalau tidak, admin terjebak dan
        model salah-isi tak bisa diperbaiki ('kunci tanpa jalur buka')."""
        layar = _baca(LAYAR)
        # Jangkar = tempat penguncian DIHITUNG, bukan tempat petanya dideklarasikan (peta ada di
        # kepala berkas, logikanya jauh di bawah — jendela karakter tak akan mencapainya).
        i = layar.find("const kunciIdentitas")
        self.assertGreater(i, 0, "penguncian identitas tak pernah dihitung")
        baris = layar[i:layar.find("\n", i)]
        self.assertIn("KOLOM_TERKUNCI_BILA_DIPAKAI", baris, "penguncian tak memakai daftar kolomnya")
        self.assertTrue(
            re.search(r"dipakai\s*>\s*0", baris),
            f"penguncian tak bersyarat pada pemakaian NYATA ⇒ model yang belum dipakai pun terkunci "
            f"dan salah-isi tak bisa diperbaiki. Baris: {baris.strip()[:120]}")
        # dan sumber angkanya wajib data pemakaian dari server, bukan tebakan
        blok = layar[max(0, i - 700):i]
        self.assertIn("catalog_pemakaian", blok,
                      "angka pemakaian tak berasal dari hitungan server ⇒ penguncian menebak")

    def test_admin_diberi_TAHU_kenapa_terkunci(self):
        """Isian mati tanpa penjelasan = 'objek pada screen yang tidak berfungsi' (definisi bug owner)."""
        layar = _baca(LAYAR)
        # Teksnya saja tak cukup: sabotase mengubah syaratnya jadi `false` dan teks tetap ada.
        # Yang dikunci: alasan dirender BERSYARAT pada angka pemakaian yang sesungguhnya.
        self.assertTrue(
            re.search(r"\{dipakaiOleh\s*\?", layar),
            "alasan terkunci tak dirender berdasarkan angka pemakaian ⇒ isian bisa mati tanpa "
            "penjelasan (objek pada layar yang tidak berfungsi).")
        i = layar.find("{dipakaiOleh ?")
        blok = layar[i:i + 300]
        self.assertIn("terkunci", blok, "alasannya tak menyebut bahwa isian itu terkunci")
        self.assertIn("dipakaiOleh", blok, "alasannya tak menyebut BERAPA channel memakainya")


class TestC_ServerJugaMenolakUbahIdentitas(unittest.TestCase):
    """Pelajaran hari ini: penjaga yang hanya hidup di panel tak menahan jalur SKRIP — mesin suara
    Gemini dulu dinyalakan lewat skrip, bukan panel. Isian readonly di layar mencegah salah-klik;
    penolakan di server mencegah jalur lain."""

    RUTE = "apps/web/src/app/api/admin/catalog/route.ts"

    def test_PATCH_menolak_ubah_identitas_bila_dipakai(self):
        rute = _baca(self.RUTE)
        self.assertIn(
            "identitas_terkunci", rute,
            "Server tidak menolak perubahan kolom identitas pada model yang dipakai channel ⇒ "
            "jalur skrip/API tetap bisa memindahkan model ke vendor lain atau mengganti ID vendor, "
            "dan seluruh tenant pemakainya berpindah tanpa memilih.")

    def test_hanya_ketiga_kolom_itu(self):
        """Jangan melebar: `display_name`, `quality_tier`, `sort_order`, `pricing`, `is_active`
        WAJIB tetap bisa diubah walau model dipakai — mematikan model yang mati harus tetap bisa."""
        rute = _baca(self.RUTE)
        i = rute.find("identitas_terkunci")
        blok = rute[max(0, i - 900):i + 300]
        for wajib in ("provider_key", "component", "model_id"):
            self.assertIn(wajib, blok, f"`{wajib}` tak ikut dijaga server")
        for jangan in ('"is_active"', '"display_name"', '"pricing"', '"sort_order"'):
            self.assertNotIn(
                jangan, blok,
                f"{jangan} ikut terkunci ⇒ mematikan/menamai ulang model yang dipakai jadi mustahil "
                "— 'kunci tanpa jalur buka' yang sudah ditegur owner")

    def test_layar_menerjemahkan_penolakan_itu(self):
        layar = _baca(LAYAR)
        self.assertIn("identitas_terkunci", layar,
                      "layar tak menerjemahkan penolakan server ⇒ admin melihat kode mentah")


if __name__ == "__main__":
    unittest.main()
