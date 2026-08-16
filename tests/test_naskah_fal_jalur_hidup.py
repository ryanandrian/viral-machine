"""Penjaga jalur NASKAH lewat fal — alamat · pencatatan biaya · kejujuran galat.

LATAR (ditemukan 2026-08-16, ketiganya lolos berbulan-bulan karena modelnya nonaktif sejak lahir):

  A. ALAMAT. Migrasi 0180 menggabungkan tiga baris penyedia fal jadi satu (koreksi yang BENAR untuk
     integritas relasi), tapi `ai_providers.base_url` milik penyedia `fal` adalah alamat ANTREAN
     jalur VISUAL. Jalur naskah memungutnya dan memanggil alamat itu → HTTP 404 pada panggilan
     pertama. Ditambah: endpoint naskah yang dipakai sejak 28-Jul kini dinyatakan DIPENSIUNKAN oleh
     dokumen resmi fal ("This endpoint is deprecated. This model is no longer supported.", dibaca
     2026-08-16). Yang dijaga di sini PERILAKUNYA: alamat naskah tidak boleh datang dari transport
     visual, dan tidak boleh menunjuk endpoint yang sudah dipensiunkan.

  B. BIAYA. `cost_meter.add_llm` dipanggil adapter Anthropic & OpenAI, TAPI TIDAK di adapter fal —
     jadi naskah lewat fal terbaca Rp 0 oleh seluruh sistem tagihan, dan rem "jangan bakar duit
     tenant" buta terhadapnya. Kelas D menjaga arah sebaliknya untuk vendor yang BELUM ADA.

  C. GALAT. fal membalas HTTP 200 dengan field `error` terisi. Jalur itu melempar galat TANPA
     golongan → jatuh ke UNKNOWN = boleh-diulang. Akibat nyata bila saldo tenant habis: 3 produksi
     terbuang sebelum channel direm, dan tenant tak pernah diberi tahu harus mengisi saldo
     (`QUOTA_EXHAUSTED` ∈ FAST_FAIL → rem setelah SATU kegagalan).

Hermetik: nol jaringan, katalog & transport di-patch.
"""
import inspect
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass, FAST_FAIL  # noqa: E402
from src.providers.llm import build_llm_provider, catalog  # noqa: E402
from src.providers.llm.adapters import ADAPTERS, FalAnyLlmAdapter  # noqa: E402
from src.providers.llm.base import LLMError  # noqa: E402
from src.utils import cost_meter  # noqa: E402

# Baris penyedia `fal` PERSIS seperti di DB produksi (dibaca 2026-08-16) — base_url = antrean VISUAL.
BARIS_FAL_DB = {
    "provider_key": "fal", "display_name": "fal.ai", "adapter": "fal_any_llm",
    "base_url": "https://queue.fal.run", "key_group": "fal", "request_param_schema": {},
}
# Endpoint yang dokumen resmi fal nyatakan DIPENSIUNKAN (dibaca 2026-08-16).
ENDPOINT_PENSIUN = "fal-ai/any-llm"


class _Balasan:
    """Pengganti objek respons urlopen (context manager dengan .read())."""

    def __init__(self, muatan: dict):
        self._b = json.dumps(muatan).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _panggil(muatan: dict, adapter=None):
    """Jalankan complete() dgn transport palsu; kembalikan (url_yang_dipanggil, hasil, galat)."""
    dicatat = {}

    def _urlopen(req, *a, **k):
        dicatat["url"] = req.full_url
        dicatat["body"] = json.loads(req.data.decode())
        return _Balasan(muatan)

    p = adapter or FalAnyLlmAdapter(api_key="K", display_name="fal.ai",
                                    base_url=BARIS_FAL_DB["base_url"], provider_key="fal")
    hasil = galat = None
    with patch("src.providers.llm.adapters.urllib.request.urlopen", _urlopen), \
         patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n):
        try:
            hasil = p.complete(system="s", user="u", model="google/gemini-2.5-flash",
                               temperature=0.3, max_tokens=100)
        except Exception as e:      # noqa: BLE001 — sengaja: uji memeriksa jenis & isinya
            galat = e
    return dicatat, hasil, galat


class TestA_AlamatNaskah(unittest.TestCase):
    """Alamat naskah tidak boleh datang dari transport visual, tidak boleh endpoint pensiun."""

    def test_tidak_memakai_alamat_antrean_visual(self):
        dicatat, _, _ = _panggil({"output": "ok", "error": None})
        self.assertNotIn(
            "queue.fal.run", dicatat["url"],
            "Naskah memanggil alamat ANTREAN jalur VISUAL — vendor menjawab 404 dan SELURUH "
            "produksi tenant gagal pada panggilan pertama.")

    def test_tidak_memakai_endpoint_yang_dipensiunkan(self):
        dicatat, _, _ = _panggil({"output": "ok", "error": None})
        self.assertNotIn(
            ENDPOINT_PENSIUN, dicatat["url"],
            f"Naskah memanggil '{ENDPOINT_PENSIUN}' — dokumen resmi fal menyatakan endpoint ini "
            "dipensiunkan dan tak lagi didukung. Ia masih menjawab hari ini; ia berhenti menjawab "
            "kapan saja, tanpa pemberitahuan, langsung di depan tenant berbayar.")

    def test_alamat_dibangun_dari_katalog_tanpa_tercemar(self):
        """Dari pintu masuk PRODUKSI (build_llm_provider), bukan dari adapter yang dirakit tangan."""
        with patch.object(catalog, "get_providers", lambda: {"fal": BARIS_FAL_DB}):
            p = build_llm_provider({"llm_library": "fal", "llm_api_key": "K"})
        dicatat, _, _ = _panggil({"output": "ok", "error": None}, adapter=p)
        self.assertNotIn("queue.fal.run", dicatat["url"])
        self.assertNotIn(ENDPOINT_PENSIUN, dicatat["url"])


class TestB_BiayaTercatat(unittest.TestCase):
    """Uang tenant yang terpakai WAJIB terlihat sistem — kalau tidak, rem pelindungnya buta."""

    def setUp(self):
        cost_meter.reset()

    def test_pemakaian_naskah_fal_tercatat(self):
        _panggil({"output": "ok", "error": None,
                  "usage": {"prompt_tokens": 21, "completion_tokens": 16, "total_tokens": 37}})
        llm = cost_meter.summary().get("llm", {})
        self.assertIn("google/gemini-2.5-flash", llm,
                      "Naskah lewat fal tidak tercatat sama sekali — biaya tenant terbaca Rp 0.")
        self.assertEqual(llm["google/gemini-2.5-flash"]["tokens_in"], 21)
        self.assertEqual(llm["google/gemini-2.5-flash"]["tokens_out"], 16)
        self.assertEqual(llm["google/gemini-2.5-flash"]["calls"], 1)

    def test_tanpa_laporan_token_pun_panggilannya_tetap_terhitung(self):
        """Penyedia yang tak melaporkan token tidak boleh menghilang dari tagihan."""
        _panggil({"output": "ok", "error": None})
        llm = cost_meter.summary().get("llm", {})
        self.assertEqual(llm.get("google/gemini-2.5-flash", {}).get("calls"), 1)


class TestC_GalatJujur(unittest.TestCase):
    """fal membalas 200 dengan `error` terisi — golongannya menentukan REM atau ULANGI."""

    def test_saldo_habis_menggolongkan_kuota_habis(self):
        _, _, galat = _panggil({"output": None, "error": "Exhausted balance. User is locked."})
        self.assertIsInstance(galat, LLMError)
        self.assertEqual(
            getattr(galat, "error_class", None), ErrorClass.QUOTA_EXHAUSTED,
            "Saldo habis tidak digolongkan → dianggap boleh-diulang: tenant kehilangan 3 produksi "
            "sebelum channel direm, dan tak pernah diberi tahu harus mengisi saldo.")
        self.assertIn(ErrorClass.QUOTA_EXHAUSTED, FAST_FAIL)
        self.assertTrue((getattr(galat, "human_message", "") or "").strip(),
                        "Tenant harus diberi tahu tindakan yang perlu ia lakukan.")

    def test_galat_tak_dikenal_tetap_boleh_diulang(self):
        """REGRESI: yang RAGU tetap UNKNOWN (keputusan owner) — jangan mengerem karena tebakan."""
        _, _, galat = _panggil({"output": None, "error": "gangguan tak dikenal"})
        self.assertIsInstance(galat, LLMError)
        self.assertEqual(getattr(galat, "error_class", ErrorClass.UNKNOWN), ErrorClass.UNKNOWN)


class TestD_BerlakuUntukVendorBerikutnya(unittest.TestCase):
    """Ketetapan owner: perbaikan harus GENERIK — vendor & model AI akan terus bertambah."""

    def test_setiap_adapter_naskah_mencatat_pemakaiannya(self):
        lalai = [nama for nama, cls in ADAPTERS.items()
                 if "cost_meter.add_llm" not in inspect.getsource(cls)]
        self.assertEqual(
            lalai, [],
            f"Adapter naskah tanpa pencatatan biaya: {lalai}. Pencatatan ditulis di dalam SETIAP "
            "adapter (pola yang sudah ada), jadi adapter baru pasti melewatkannya kecuali dijaga "
            "di sini — dan yang terlewat membuat uang tenant terbakar tanpa terlihat siapa pun.")


if __name__ == "__main__":
    unittest.main()
