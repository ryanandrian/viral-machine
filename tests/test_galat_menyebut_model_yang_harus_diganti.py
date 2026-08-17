"""GALAT "MODEL TIDAK TERSEDIA" WAJIB MENYEBUT MODEL MANA — tenant punya 3 slot AI.

CACAT YANG DIJAGA (keluhan tenant BISIK NUSANTARA, 2026-08-17):
produksi berhenti dengan pesan *"Model AI ini sudah tidak tersedia di penyedianya (dipensiunkan/tak
bisa diakses). Pilih model lain di setting channel."* — tanpa menyebut model yang mana.

Satu channel memakai TIGA slot AI (penulis naskah · pengisi suara · pembuat gambar), jadi
"pilih model lain" tidak bisa dikerjakan: tenant tak tahu slot mana yang harus disentuh.

Padahal vendor sudah memberitahu kita dengan tepat:

    Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does not exist
    or you do not have access to it.', 'code': 'model_not_found'}}

Kita memegang KETIGANYA — penyedia (Groq), slot (penulis naskah), nama model — lalu membuang
semuanya dan menggantinya dengan kalimat umum. Kebingungan tenant buatan kita sendiri, bukan
kekurangan vendor. Sejalan dengan ketetapan owner 08-Agu: *pesan penyedia jangan diterjemahkan*.

Janggalnya asimetris: dari 4 golongan di tabel pesan jalur naskah, TIGA sudah menyebut slotnya
("penulis naskah"). Hanya golongan ini yang tidak — padahal justru ini satu-satunya yang
tindakannya "ganti model", sehingga nama modelnya paling dibutuhkan.

GENERIK (ketetapan owner: vendor & model AI akan terus bertambah) — yang dijaga di sini adalah
PERILAKUnya, bukan kalimat harfiahnya: identitas apa pun yang vendor sebutkan harus sampai ke
tenant, untuk vendor & model mana pun, termasuk yang belum ada hari ini.

Hermetik: nol jaringan.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass, FAST_FAIL  # noqa: E402
from src.providers.llm.adapters import (  # noqa: E402
    _OPENAI_COMPAT_HUMAN,
    _classify_openai_compat_error,
)

# Sampel VERBATIM dari worker.log produksi BISIK NUSANTARA 2026-08-17 13:21 (run direct-61d31ce5).
SAMPEL_GROQ_MATI = (
    "Provider 'Groq' gagal: Error code: 404 - {'error': {'message': 'The model "
    "`llama-3.3-70b-versatile` does not exist or you do not have access to it.', "
    "'type': 'invalid_request_error', 'code': 'model_not_found'}}"
)


class TestA_IdentitasSampaiKeTenant(unittest.TestCase):
    """Tenant harus bisa mengerjakan "pilih model lain" tanpa menebak."""

    def _pesan(self, model="llama-3.3-70b-versatile", nama="Groq"):
        kelas, human = _classify_openai_compat_error(
            Exception(SAMPEL_GROQ_MATI), "groq", model=model, penyedia_nama=nama)
        self.assertEqual(kelas, ErrorClass.MODEL_UNAVAILABLE)
        self.assertTrue(human, "tenant tidak diberi anjuran apa pun")
        return human

    def test_menyebut_nama_model(self):
        self.assertIn(
            "llama-3.3-70b-versatile", self._pesan(),
            "Pesan tidak menyebut model yang mati. Vendor SUDAH menyebutkannya; kita membuangnya, "
            "lalu menyuruh tenant 'pilih model lain' tanpa memberi tahu yang mana.")

    def test_menyebut_slot_yang_harus_disentuh(self):
        self.assertIn(
            "penulis naskah", self._pesan().lower(),
            "Pesan tidak menyebut SLOT-nya. Satu channel punya 3 slot AI (naskah · suara · gambar) "
            "— tanpa ini tenant harus menebak yang mana, dan tiga golongan sebelahnya sudah "
            "menyebutkannya.")

    def test_menyebut_penyedianya(self):
        self.assertIn(
            "Groq", self._pesan(),
            "Pesan tidak menyebut penyedianya — tenant tak tahu akun vendor mana yang dimaksud.")

    def test_tetap_bisa_dikerjakan_tenant(self):
        """Anjuran tindakan JANGAN hilang gara-gara menambah identitas."""
        self.assertIn("Pilih model lain", self._pesan())


class TestB_GenerikUntukVendorBerikutnya(unittest.TestCase):
    """Ketetapan owner: perbaikan berlaku untuk vendor & model yang BELUM ADA."""

    def test_vendor_dan_model_apa_pun_ikut_disebut(self):
        _, human = _classify_openai_compat_error(
            Exception("Error code: 404 - {'error': {'code': 'model_not_found'}}"),
            "vendor_masa_depan", model="model-yang-belum-ada-v9", penyedia_nama="Vendor Masa Depan")
        self.assertIn("model-yang-belum-ada-v9", human or "")
        self.assertIn("Vendor Masa Depan", human or "")

    def test_tanpa_identitas_pesan_tetap_utuh_dan_tak_bocor_kerangka(self):
        """REGRESI: pemanggil lama (1 argumen) tetap sah — dan tenant tak pernah melihat
        kerangka penampung yang belum terisi."""
        _, human = _classify_openai_compat_error(Exception(SAMPEL_GROQ_MATI))
        self.assertTrue(human)
        self.assertNotIn("{", human, "kerangka penampung bocor ke mata tenant")
        self.assertIn("Pilih model lain", human)


class TestC_TigaGolonganLainTakBergeser(unittest.TestCase):
    """REGRESI: hanya golongan 'ganti model' yang disentuh."""

    def test_slot_tetap_disebut_ketiga_golongan_lain(self):
        for kelas in (ErrorClass.AUTH_INVALID, ErrorClass.QUOTA_EXHAUSTED, ErrorClass.RATE_LIMIT):
            self.assertIn("penulis naskah", _OPENAI_COMPAT_HUMAN[kelas].lower(),
                          f"{kelas} kehilangan penyebutan slotnya")

    def test_kunci_ditolak_tetap_menganjurkan_perbaiki_kunci(self):
        _, human = _classify_openai_compat_error(
            Exception("Error code: 401 - {'error': {'code': 'invalid_api_key'}}"), "groq",
            model="apa-pun", penyedia_nama="Groq")
        self.assertIn("Kunci API", human or "")

    def test_galat_tak_dikenal_tetap_tanpa_anjuran(self):
        """Keputusan owner: yang RAGU tetap UNKNOWN, dan jangan mengarang anjuran."""
        kelas, human = _classify_openai_compat_error(
            Exception("gangguan aneh tak dikenal"), "groq", model="m", penyedia_nama="Groq")
        self.assertEqual(kelas, ErrorClass.UNKNOWN)
        self.assertIsNone(human)

    def test_golongan_ini_tetap_mengerem_seketika(self):
        self.assertIn(ErrorClass.MODEL_UNAVAILABLE, FAST_FAIL)


class TestD_AdapterMeneruskanIdentitas(unittest.TestCase):
    """Pesan sebagus apa pun tak berguna bila adapter tak meneruskan identitasnya."""

    def test_setiap_adapter_naskah_meneruskan_model_dan_nama_penyedia(self):
        import inspect
        from src.providers.llm.adapters import ADAPTERS
        lalai = []
        for nama, cls in ADAPTERS.items():
            src = inspect.getsource(cls)
            if "_classify_openai_compat_error" not in src:
                continue
            for panggil in src.split("_classify_openai_compat_error(")[1:]:
                cuplik = panggil[:200]
                if "model=" not in cuplik or "penyedia_nama=" not in cuplik:
                    lalai.append(nama)
                    break
        self.assertEqual(
            lalai, [],
            f"Adapter yang masih membuang identitas: {lalai}. Nama model & penyedia ADA di tangan "
            "di titik itu; tidak meneruskannya membuat tenant menebak slot mana yang rusak.")


if __name__ == "__main__":
    unittest.main()
