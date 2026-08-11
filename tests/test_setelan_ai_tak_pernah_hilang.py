"""SETELAN AI TAK BOLEH HILANG DI JALAN · GALAT PENYEDIA WAJIB DIGOLONGKAN · SALAH KITA JANGAN
DITIMPAKAN KE TENANT.

MASALAH YANG DIJAGA (dipetakan ujung-ke-ujung 2026-08-11, atas perintah owner "buat rencana tuntas
agar tidak ada lagi issue meski ai provider/model diganti tenant atau model baru ditambahkan")

    daftar setelan yang diserahkan ke pembuat gambar TIDAK memuat nama model LLM
      → penulis-ulang prompt (satu-satunya pemulihan saat gambar gagal) mati di langkah pertama
      → percobaan 2 & 3 TAK PERNAH sampai ke penyedia gambar
      → adegan dilewati, produksi mati, video yang SEBENARNYA bisa diselamatkan dibuang
      → sebab TERAKHIR (= galat KITA) dipakai sebagai sebab yang ditampilkan
      → tenant dibilangi "Kegagalan terjadi di layanan AI Anda" untuk bug MesinViral
      → tenant memeriksa akun AI-nya yang sehat, lalu menyimpulkan MesinViral yang rusak

TERUKUR DI PRODUKSI (worker.log 16-Jun s/d 11-Agu · DB live 11-Agu):
  • 49 kejadian "Rejection rewrite gagal — LLM error: Model untuk 'Groq' tidak ditentukan" (8 hari ini)
  • 28 adegan mati setelah 3 percobaan · pemulihan BERHASIL cuma 1× — di channel owner sendiri,
    satu-satunya tenant yang `llm_models['rewrite']`-nya terisi (17 dari 18 tenant kosong)
  • 35 kegagalan penyedia gambar yang sebabnya TAK PERNAH tercatat (13 Jun · 13 Jul · 9 Agu) —
    inilah kenapa "jatah Cloudflare habis" tak bisa dibuktikan ADA maupun TIDAK ADA
  • 7 dari 11 channel memakai Cloudflare untuk gambar (6 aktif)

LIMA HAL YANG DIJAGA BERKAS INI:
  A. Setelan LLM (termasuk nama model) WAJIB ikut diserahkan ke pembuat gambar.
  B. SETIAP penyedia di daftar transport WAJIB menggolongkan galatnya — tambah penyedia/model baru
     tanpa itu = berkas ini MERAH. Inilah jawaban atas "meski model baru ditambahkan".
  C. Pemetaan Cloudflare & Gemini sesuai DOKUMEN RESMI — khususnya 3036 (berhenti) vs 3040 (ulangi)
     yang dua-duanya HTTP 429. Memetakan dari status HTTP saja = bug.
  D. Galat MILIK KITA tidak boleh dilabeli "layanan AI Anda".
  E. Sebab PERTAMA (jawaban penyedia) yang dipakai, bukan sebab terakhir (= galat kita).
"""
import inspect
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass, FAST_FAIL, SELF_HEALING, VisualError  # noqa: E402
from src.orchestrator.pipeline import Pipeline  # noqa: E402
from src.production.visual_assembler import VisualAssembler  # noqa: E402
from src.providers.visual.ai_image import AIImageProvider  # noqa: E402
from src.providers.visual import base as vbase  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERAKIT = os.path.join(AKAR, "src", "production", "visual_assembler.py")
ADAPTOR = os.path.join(AKAR, "src", "providers", "visual", "ai_image.py")


def _teks(p):
    return open(p, encoding="utf-8", errors="ignore").read()


# ── A. Setelan tak boleh hilang di jalan ────────────────────────────────────────────────────────

class TestA_SetelanLLMIkutDiserahkan(unittest.TestCase):
    """`llm_models['rewrite'] or llm_model` — cabang kedua selalu "" karena `llm_model` tak pernah
    diserahkan. 17 dari 18 tenant tidak punya cabang pertama ⇒ pemulihan mati bagi hampir semua."""

    KUNCI_WAJIB = ("llm_api_key", "llm_library", "llm_provider", "llm_models", "llm_model")

    def test_semua_kunci_llm_ada_di_penyerahan(self):
        sumber = inspect.getsource(VisualAssembler._load_run_config)
        hilang = [k for k in self.KUNCI_WAJIB if f'"{k}"' not in sumber]
        self.assertFalse(
            hilang,
            f"setelan LLM tidak diserahkan ke pembuat gambar: {hilang}. Nilainya ADA di DB dan sudah "
            f"ter-overlay per-channel — kalau tidak diserahkan, pemulihan gambar mati diam-diam.")

    def test_kedua_cabang_penyerahan_konsisten(self):
        """`_load_run_config` punya cabang sukses DAN cabang gagal-baca. Bentuk dict-nya wajib SAMA,
        kalau tidak, kegagalan baca config menghasilkan bug yang hanya muncul saat DB bermasalah."""
        sumber = inspect.getsource(VisualAssembler._load_run_config)
        for k in self.KUNCI_WAJIB:
            self.assertGreaterEqual(
                sumber.count(f'"{k}"'), 2,
                f"kunci '{k}' hanya ada di SATU cabang `_load_run_config` — bentuk dict kedua cabang "
                f"wajib identik")

    def test_diteruskan_ke_pembuat_gambar(self):
        """Diserahkan ke `run_config` belum cukup — jalur gambar menyusun dict-nya SENDIRI lagi,
        jadi kunci bisa hilang di lapis kedua. (Dibaca dari fungsinya langsung, bukan dengan
        mencari pola di seluruh berkas: pola `"visual_provider": visual_mode` juga dipakai jalur
        VIDEO, dan pencarian teks sempat salah menunjuk ke sana.)"""
        sumber = inspect.getsource(VisualAssembler._try_ai_image)
        for k in ("llm_model", "llm_models", "llm_api_key", "llm_library"):
            self.assertIn(f'"{k}"', sumber,
                          f"'{k}' tidak diteruskan ke pembuat gambar di jalur gambar — "
                          f"pemulihan gambar akan mati lagi walau `_load_run_config` sudah benar")


class TestA2_SetelanKosongBerteriak(unittest.TestCase):
    """Dulu "" diteruskan ke factory dan muncul sebagai galat yang tak menyebut siapa yang lupa —
    lalu ditimpakan ke tenant. Bersembunyi 2 bulan, 49 kejadian."""

    def test_gagal_jujur_dan_mengaku_milik_kita(self):
        sumber = inspect.getsource(AIImageProvider._ai_rewrite_on_rejection)
        self.assertRegex(sumber, r"if not rewrite_model",
                         "setelan model kosong masih diteruskan diam-diam ke factory")
        self.assertIn("milik_kita=True", sumber,
                      "setelan kurang = kesalahan MesinViral; wajib ditandai, bukan ditimpakan ke tenant")


# ── B. Penyedia baru WAJIB digolongkan ──────────────────────────────────────────────────────────

class TestB_SetiapPenyediaMenggolongkanGalatnya(unittest.TestCase):
    """INI jawaban atas 'meski model AI baru ditambahkan ke mesinviral.com'.

    Menambah penyedia = +1 method `_generate_<x>` + 1 entri `_TRANSPORTS`. Bila methodnya melempar
    galat tanpa `error_class`, mesin tak bisa membedakan 'berhenti' dari 'ulangi' → jatah tenant
    terbakar atau produksi berhenti keliru. Uji ini MERAH sampai penyedia baru itu menggolongkan.
    """

    def test_semua_transport_terdaftar_punya_penggolongan(self):
        sumber_penuh = _teks(ADAPTOR)
        kurang = []
        for platform, nama_method in AIImageProvider._TRANSPORTS.items():
            method = getattr(AIImageProvider, nama_method, None)
            self.assertIsNotNone(method, f"_TRANSPORTS menunjuk method yang tidak ada: {nama_method}")
            src = inspect.getsource(method)
            if "raise VisualError" not in src:
                continue                      # tak melempar galat sendiri → tak ada yang digolongkan
            if "error_class=" not in src:
                kurang.append(f"{platform} ({nama_method})")
        self.assertFalse(
            kurang,
            "penyedia gambar berikut melempar galat TANPA menggolongkannya: " + ", ".join(kurang)
            + ".\nAkibatnya mesin tak bisa membedakan 'jatah habis' (berhenti) dari 'sesak sesaat' "
              "(ulangi). Wajib: baca dokumen resmi penyedia (AI_ERROR_MANAGEMENT §1 Aturan Emas + §5 "
              "langkah 1), petakan, lalu raise dengan error_class + human_message + penanda asal.")
        self.assertIn("_TRANSPORTS", sumber_penuh)

    def test_daftar_transport_tidak_kosong(self):
        self.assertGreaterEqual(len(AIImageProvider._TRANSPORTS), 4,
                                "daftar penyedia gambar menyusut — periksa apakah ada yang terhapus")


# ── C. Pemetaan sesuai dokumen resmi ────────────────────────────────────────────────────────────

class TestC_PemetaanSesuaiDokumenResmi(unittest.TestCase):
    """Sumber: developers.cloudflare.com/workers-ai/platform/errors/ + ai.google.dev/gemini-api/docs/
    api-errors, dibaca 2026-08-11."""

    def _cf(self, kode, pesan="pesan penyedia"):
        return vbase.classify_cloudflare_error({"success": False,
                                                "errors": [{"code": kode, "message": pesan}]})

    def test_3036_jatah_harian_habis_BERHENTI(self):
        kelas, pesan, kita = self._cf(3036, "You have used up your daily free allocation of 10,000 neurons")
        self.assertEqual(kelas, ErrorClass.QUOTA_EXHAUSTED)
        self.assertIn(kelas, FAST_FAIL, "jatah harian habis WAJIB berhenti — mengulang percuma")
        self.assertFalse(kita, "jatah tenant habis = milik tenant, bukan milik kita")
        self.assertIn("neurons", pesan or "", "pesan penyedia wajib diteruskan apa adanya")

    def test_3040_kapasitas_sesaat_ULANGI(self):
        """PALING PENTING: 3040 juga HTTP 429. Kalau ini ikut dianggap 'jatah habis', produksi
        channel tenant berhenti atas dasar yang SALAH."""
        kelas, _, kita = self._cf(3040, "Capacity temporarily exceeded")
        self.assertEqual(kelas, ErrorClass.TRANSIENT)
        self.assertNotIn(kelas, FAST_FAIL, "kapasitas sesaat HARAM menghentikan produksi")
        self.assertIn(kelas, SELF_HEALING, "kapasitas sesaat pulih sendiri")
        self.assertFalse(kita)

    def test_3036_dan_3040_TIDAK_sama(self):
        self.assertNotEqual(self._cf(3036)[0], self._cf(3040)[0],
                            "dua kode 429 yang berlawanan dipetakan sama = bug yang dokumen resmi "
                            "justru menyelamatkan kita darinya")

    def test_permintaan_kita_cacat_ditandai_milik_kita(self):
        for kode in (3003, 5004, 3006):
            _, _, kita = self._cf(kode)
            self.assertTrue(kita, f"kode {kode}: Cloudflare menyatakan permintaan KITA cacat — "
                                  f"haram ditimpakan ke tenant")

    def test_kelas_lain_cloudflare(self):
        self.assertEqual(self._cf(3023)[0], ErrorClass.ACCOUNT_BILLING)
        self.assertEqual(self._cf(5035)[0], ErrorClass.ACCOUNT_BILLING)
        self.assertEqual(self._cf(5016)[0], ErrorClass.AUTH_INVALID)
        self.assertEqual(self._cf(5007)[0], ErrorClass.MODEL_UNAVAILABLE)
        self.assertEqual(self._cf(3042)[0], ErrorClass.MODEL_UNAVAILABLE)

    def test_kode_asing_tetap_UNKNOWN(self):
        """Perilaku lama dipertahankan: yang tak dikenal = boleh diulang, tidak mengarang."""
        self.assertEqual(self._cf(999999)[0], ErrorClass.UNKNOWN)
        self.assertEqual(vbase.classify_cloudflare_error(None)[0], ErrorClass.UNKNOWN)
        self.assertEqual(vbase.classify_cloudflare_error("bukan json")[0], ErrorClass.UNKNOWN)

    def test_bentuk_DAFTAR_cloudflare_terbaca(self):
        """Cloudflare mengirim galat sebagai DAFTAR. Penilai lama (dirancang utk objek) buta total."""
        kelas, _, _ = vbase.classify_cloudflare_error({"errors": [{"code": 3036, "message": "x"}]})
        self.assertEqual(kelas, ErrorClass.QUOTA_EXHAUSTED,
                         "kode di dalam `errors: [...]` tidak terbaca — inilah bentuk NYATA Cloudflare")

    def test_gemini_harian_vs_permenit_dibedakan(self):
        q = vbase.classify_gemini_error({"error": {"status": "quota_exceeded", "message": "m"}})
        r = vbase.classify_gemini_error({"error": {"status": "rate_limit_exceeded", "message": "m"}})
        self.assertEqual(q[0], ErrorClass.QUOTA_EXHAUSTED)
        self.assertEqual(r[0], ErrorClass.RATE_LIMIT)
        self.assertIn(r[0], SELF_HEALING)

    def test_gemini_resource_exhausted_konservatif(self):
        """RESOURCE_EXHAUSTED menaungi harian DAN per-menit. Tanpa kode spesifik → pilih yang boleh
        diulang: salah-rem jauh lebih mahal daripada satu percobaan tambahan."""
        kelas, _, _ = vbase.classify_gemini_error({"error": {"status": "RESOURCE_EXHAUSTED"}})
        self.assertEqual(kelas, ErrorClass.RATE_LIMIT)
        self.assertNotIn(kelas, FAST_FAIL)

    def test_gemini_kelas_lain(self):
        self.assertEqual(vbase.classify_gemini_error(
            {"error": {"status": "authentication"}})[0], ErrorClass.AUTH_INVALID)
        self.assertEqual(vbase.classify_gemini_error(
            {"error": {"status": "failed_precondition"}})[0], ErrorClass.ACCOUNT_BILLING)
        self.assertEqual(vbase.classify_gemini_error(
            {"error": {"status": "model_not_found"}})[0], ErrorClass.MODEL_UNAVAILABLE)
        self.assertTrue(vbase.classify_gemini_error(
            {"error": {"status": "invalid_request"}})[2], "permintaan cacat = milik kita")


# ── D. Salah kita jangan ditimpakan ke tenant ───────────────────────────────────────────────────

class TestD_SalahKitaTidakDitimpakanKeTenant(unittest.TestCase):
    """Cacat yang dikirim pada commit 0d64f79, terjadi live 11-Agu 12:21."""

    def _p(self):
        return Pipeline.__new__(Pipeline)

    SCRIPT = {"beat_durations": [2.4, 17.0, 14.1, 12.8, 9.4]}

    def test_galat_penyedia_menyebut_layanan_tenant(self):
        pesan = self._p()._periksa_kelengkapan_klip(
            ["a", "b", "c", "d"], self.SCRIPT,
            "You have used up your daily free allocation of 10,000 neurons", False)
        self.assertIn("layanan AI Anda", pesan)
        self.assertIn("neurons", pesan, "pesan penyedia wajib apa adanya")

    def test_galat_KITA_TIDAK_menyebut_layanan_tenant(self):
        pesan = self._p()._periksa_kelengkapan_klip(
            ["a", "b"], self.SCRIPT, "Model untuk 'Groq' tidak ditentukan", True)
        # Yang dijaga adalah TUDUHANNYA, bukan sekadar kemunculan kata. Menyebut "BUKAN di layanan
        # AI Anda" justru wajib — itu yang menghentikan tenant memeriksa akun yang sehat.
        self.assertNotIn("Kegagalan terjadi di layanan AI Anda", pesan,
                         "MesinViral menuduh penyedia tenant untuk bug MesinViral — kejadian NYATA "
                         "11-Agu 12:21; 75 kegagalan di worker.log milik KITA")
        self.assertIn("MesinViral", pesan, "wajib menyatakan terang bahwa ini pihak kita")
        self.assertRegex(pesan, r"BUKAN di layanan AI Anda",
                         "tenant harus tahu TERANG bahwa akun AI-nya tidak perlu diperiksa")

    def test_klip_lengkap_tetap_tak_diganggu(self):
        """ANTI-REGRESI: 168 dari 180 render sehat wajib tetap jalan."""
        self.assertIsNone(self._p()._periksa_kelengkapan_klip(
            ["a", "b", "c", "d", "e"], self.SCRIPT, None, False))

    def test_penanda_asal_dibawa_exception(self):
        e = VisualError("x", milik_kita=True)
        self.assertTrue(e.milik_kita)
        self.assertFalse(VisualError("y").milik_kita, "default WAJIB False (tak menuduh siapa pun)")


# ── E. Sebab PERTAMA yang dipakai ───────────────────────────────────────────────────────────────

class TestE_SebabPertamaBukanTerakhir(unittest.TestCase):
    """Percobaan 2 & 3 memanggil penulis-ulang prompt DULU, jadi sebab TERAKHIR hampir selalu galat
    milik kita. Sebab PERTAMA = jawaban penyedia yang sebenarnya."""

    def test_sebab_pertama_yang_disimpan(self):
        sumber = _teks(ADAPTOR)
        m = re.search(r"GAGAL setelah 3 attempt.{0,600}", sumber, re.S)
        self.assertIsNotNone(m, "cabang 'adegan dilewati' tak ditemukan")
        blok = m.group(0)
        self.assertIn("scene_errors.append(_sebab_pertama)", blok,
                      "yang disimpan bukan sebab PERTAMA — galat kita akan menutupi jawaban penyedia")

    def test_sebab_percobaan_pertama_ikut_dicatat_di_log(self):
        """35 kegagalan penyedia (Jun-Agu) sebabnya tak pernah tersimpan karena baris log ini
        hanya menyebut BAHWA percobaan 1 gagal."""
        sumber = _teks(ADAPTOR)
        m = re.search(r"attempt \{attempt-1\} gagal.{0,200}", sumber, re.S)
        self.assertIsNotNone(m, "baris log percobaan-1 tak ditemukan")
        self.assertRegex(m.group(0), r"Sebab: \{e\}",
                         "sebab percobaan PERTAMA masih dibuang dari log — kebutaan yang sama kembali")

    def test_penampung_terstruktur_ada(self):
        self.assertIn("scene_failures", _teks(ADAPTOR),
                      "tak ada penampung terstruktur (sebab+kelas+asal) — hilir kembali menebak")

    def test_pemilih_sebab_mengutamakan_yang_bisa_dikerjakan_tenant(self):
        pilih = VisualAssembler._pilih_sebab_adegan([
            {"sebab": "galat kita", "kelas": "unknown", "milik_kita": True},
            {"sebab": "jatah habis", "kelas": ErrorClass.QUOTA_EXHAUSTED.value, "milik_kita": False},
        ])
        self.assertEqual(pilih["sebab"], "jatah habis",
                         "bug MesinViral menutupi masalah yang tenant sendiri bisa selesaikan")

    def test_pemilih_tetap_jujur_bila_hanya_galat_kita(self):
        pilih = VisualAssembler._pilih_sebab_adegan(
            [{"sebab": "galat kita", "kelas": "unknown", "milik_kita": True}])
        self.assertEqual(pilih["sebab"], "galat kita",
                         "galat kita ditaruh paling belakang, BUKAN disembunyikan")

    def test_pemilih_aman_saat_kosong(self):
        self.assertIsNone(VisualAssembler._pilih_sebab_adegan([]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
