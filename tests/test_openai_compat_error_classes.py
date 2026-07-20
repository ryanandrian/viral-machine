"""
Uji regresi PERMANEN — [B22] registrasi error OpenAI-compatible ber-BUKTI-SAMPEL (fix 2026-07-20).
Hermetik (nol jaringan; SDK & katalog di-patch). Sampel = string VERBATIM worker.log 20-Jul (insiden MVT).

Jalankan:  python -m unittest tests.test_openai_compat_error_classes

Yang dijaga:
  A. Classifier: sampel 401 `invalid_api_key` → AUTH_INVALID + pesan manusiawi.
  B. Classifier: sampel 404 `model_not_found` → MODEL_UNAVAILABLE + pesan manusiawi.
  C. REGRESI: error tak dikenal → UNKNOWN tanpa pesan (perilaku lama persis).
  D. Taksonomi: MODEL_UNAVAILABLE ∈ FAST_FAIL; 3 kelas fast-fail lama utuh; kelas retryable TIDAK ikut.
  E. WIRING adapter: OpenAIChatAdapter.complete membungkus error vendor dgn error_class+human.
  F. REM CEPAT niche_selector: error FAST_FAIL → 1 percobaan (nol retry) + kelas & pesan
     terpropagasi ke last_error_class/last_human_error (dibaca pipeline → production_runs).
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass, FAST_FAIL, LLMError  # noqa: E402
from src.providers.llm import catalog  # noqa: E402
from src.providers.llm.adapters import OpenAIChatAdapter, _classify_openai_compat_error  # noqa: E402

# String VERBATIM dari worker.log 2026-07-20 (insiden MVT)
SAMPEL_401 = ("Error code: 401 - {'error': {'message': 'Invalid API Key', "
              "'type': 'invalid_request_error', 'code': 'invalid_api_key'}}")
SAMPEL_404 = ("Error code: 404 - {'error': {'message': 'The model `meta-llama/llama-4-scout-17b-16e-instruct` "
              "does not exist or you do not have access to it.', 'type': 'invalid_request_error', "
              "'code': 'model_not_found'}}")


class TestClassifier(unittest.TestCase):
    def test_A_sampel_401__auth_invalid(self):
        ec, human = _classify_openai_compat_error(Exception(SAMPEL_401))
        self.assertEqual(ec, ErrorClass.AUTH_INVALID)
        self.assertIn("Integrasi", human)

    def test_B_sampel_404__model_unavailable(self):
        ec, human = _classify_openai_compat_error(Exception(SAMPEL_404))
        self.assertEqual(ec, ErrorClass.MODEL_UNAVAILABLE)
        self.assertIn("model lain", human)

    def test_C_regresi_error_asing__unknown(self):
        ec, human = _classify_openai_compat_error(Exception("Error code: 500 - internal server error"))
        self.assertEqual(ec, ErrorClass.UNKNOWN)
        self.assertIsNone(human)

    def test_D_taksonomi_fast_fail(self):
        self.assertIn(ErrorClass.MODEL_UNAVAILABLE, FAST_FAIL)
        for lama in (ErrorClass.ACCOUNT_BILLING, ErrorClass.QUOTA_EXHAUSTED, ErrorClass.AUTH_INVALID):
            self.assertIn(lama, FAST_FAIL)
        for retryable in (ErrorClass.RATE_LIMIT, ErrorClass.TRANSIENT, ErrorClass.UNKNOWN):
            self.assertNotIn(retryable, FAST_FAIL)


class TestWiringAdapter(unittest.TestCase):
    def test_E_complete_membungkus_dgn_kelas(self):
        catalog._CACHE.update(providers={}, models={}, ts=time.time())  # resolve = pass-through
        ad = OpenAIChatAdapter(api_key="kunci-uji", display_name="Groq")
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = Exception(SAMPEL_401)
        with patch("openai.OpenAI", return_value=fake_client):
            with self.assertRaises(LLMError) as cm:
                ad.complete(system="s", user="u", model="m")
        self.assertEqual(cm.exception.error_class, ErrorClass.AUTH_INVALID)
        self.assertIn("Integrasi", cm.exception.human_message)


class TestRemCepatNicheSelector(unittest.TestCase):
    def test_F_fast_fail__satu_percobaan_dan_propagasi(self):
        from src.intelligence.niche_selector import NicheSelector
        sel = NicheSelector.__new__(NicheSelector)  # hermetik tanpa __init__
        sel.MAX_RETRIES = 3
        provider = MagicMock()
        provider.complete.side_effect = LLMError(
            SAMPEL_404, error_class=ErrorClass.MODEL_UNAVAILABLE,
            human_message="Model AI ini sudah tidak tersedia di penyedianya. Pilih model lain di setting channel.")
        tc = MagicMock(); tc.niche = "uji_niche"; tc.tenant_id = "t-uji"
        niche_data = {"name": "Uji", "style": "edu", "target_emotion": "curiosity",
                      "keywords": [], "youtube_category_id": 27}
        with patch("src.intelligence.niche_selector.get_niches", return_value={"uji_niche": niche_data}):
            out = sel._analyze_with_ai("(signals)", tc, provider=provider, model="m")
        self.assertEqual(out, [])
        self.assertEqual(provider.complete.call_count, 1, "FAST_FAIL wajib berhenti di percobaan-1 (nol retry)")
        self.assertEqual(sel.last_error_class, ErrorClass.MODEL_UNAVAILABLE)
        self.assertIn("model lain", sel.last_human_error)
        self.assertIn("model lain", sel.last_error)


if __name__ == "__main__":
    unittest.main()
