"""
Uji regresi PERMANEN — resolusi model_key → model_id di jalur LLM teks (fix 2026-07-20, insiden MVT).
Hermetik (cache katalog diisi langsung; nol jaringan/vendor).

Jalankan:  python -m unittest tests.test_llm_model_resolution

Yang dijaga:
  A. `resolve_model_id`: model_key ber-id BEDA → diterjemahkan ke model_id resmi (kasus GPT-OSS).
  B. model_key ber-id SAMA → tak berubah (mayoritas katalog; nol dampak).
  C. Nama yang BUKAN model_key (ID mentah/legacy) → lolos APA ADANYA.
  D. Fail-safe: katalog error → nama asli (produksi tak terblokir blip katalog).
  E. WIRING: kedua adapter (Anthropic & OpenAI-compatible) MEMANGGIL resolusi di complete()
     — jaminan "lolos Uji admin = pasti jalan di produksi" hidup di SATU pintu.
"""
import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.providers.llm import catalog  # noqa: E402
from src.providers.llm.adapters import AnthropicMessagesAdapter, OpenAIChatAdapter  # noqa: E402


def _prime_cache():
    catalog._CACHE.update(
        providers={},
        models={
            "openai-gpt-oss-120b": {"model_key": "openai-gpt-oss-120b", "model_id": "openai/gpt-oss-120b"},
            "gpt-4o": {"model_key": "gpt-4o", "model_id": "gpt-4o"},
            "tanpa-id": {"model_key": "tanpa-id", "model_id": None},
        },
        ts=time.time(),
    )


class TestResolveModelId(unittest.TestCase):
    def setUp(self):
        _prime_cache()

    def test_A_key_beda_id__diterjemahkan(self):
        self.assertEqual(catalog.resolve_model_id("openai-gpt-oss-120b"), "openai/gpt-oss-120b")

    def test_B_key_sama_id__tak_berubah(self):
        self.assertEqual(catalog.resolve_model_id("gpt-4o"), "gpt-4o")

    def test_C_nama_asing_dan_id_mentah__lolos_apa_adanya(self):
        self.assertEqual(catalog.resolve_model_id("meta-llama/llama-4-x"), "meta-llama/llama-4-x")
        self.assertEqual(catalog.resolve_model_id("tanpa-id"), "tanpa-id")  # row ada tapi id kosong → nama asli
        self.assertEqual(catalog.resolve_model_id(""), "")

    def test_D_failsafe_katalog_error__nama_asli(self):
        with patch.object(catalog, "get_models", side_effect=RuntimeError("blip")):
            self.assertEqual(catalog.resolve_model_id("openai-gpt-oss-120b"), "openai-gpt-oss-120b")


class _Tanda(Exception):
    """Penanda: resolusi TERPANGGIL (dilempar sebelum menyentuh SDK vendor)."""


class TestWiringAdapters(unittest.TestCase):
    def test_E_kedua_adapter_memanggil_resolusi(self):
        for cls in (AnthropicMessagesAdapter, OpenAIChatAdapter):
            with self.subTest(adapter=cls.__name__):
                ad = cls(api_key="kunci-uji", display_name="Uji")
                with patch("src.providers.llm.adapters._catalog.resolve_model_id",
                           side_effect=_Tanda) as mres:
                    with self.assertRaises(_Tanda):
                        ad.complete(system="s", user="u", model="kunci-katalog")
                    mres.assert_called_once_with("kunci-katalog")


if __name__ == "__main__":
    unittest.main()
