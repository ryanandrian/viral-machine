"""
Uji regresi PERMANEN — koherensi VENDOR pada resolusi kunci per-slot (fix 2026-07-20, insiden MVT).
Hermetik (FakeSupabase meniru rantai .table().select().eq()...execute(); decrypt di-patch).

Jalankan:  python -m unittest tests.test_key_pool_vendor_coherence

Yang dijaga (`TenantConfigManager._set_key_from_pool`):
  A. Akun ditugaskan SEPADAN vendor penyedia → kunci akun itu dipakai.
  B. Akun ditugaskan BEDA vendor (bug MVT: kunci OpenAI utk slot Groq) → akun DIABAIKAN →
     jatuh ke akun-tunggal vendor yang BENAR (kunci salah TIDAK pernah terkirim ke vendor salah).
  C. REGRESI: akun ditugaskan tak-valid → auto vendor (perilaku lama utuh).
  D. REGRESI: tanpa akun apa pun utk vendor → kunci '' (gagal jujur, no-fallback).
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.tenant_config import TenantConfigManager, TenantRunConfig  # noqa: E402


# ── FakeSupabase: meniru persis rantai panggilan yang dipakai _set_key_from_pool ──
class _Q:
    def __init__(self, rows_by_table, table):
        self._rows = rows_by_table.get(table, [])
        self._filters = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        out = [r for r in self._rows if all(r.get(c) == v for c, v in self._filters.items())]
        class R:  # noqa: N801
            data = out
        return R()


class FakeSB:
    def __init__(self, rows_by_table):
        self._t = rows_by_table

    def table(self, name):
        return _Q(self._t, name)


TENANT = "tenant-uji-1"
KEY_GROQ, KEY_OPENAI = "enc-groq", "enc-openai"


def _tables(assigned_status="valid"):
    return {
        "ai_providers": [
            {"provider_key": "groq", "key_group": "groq"},
            {"provider_key": "openai", "key_group": "openai"},
        ],
        "tenant_ai_accounts": [
            {"id": "acct-groq", "tenant_id": TENANT, "key_group": "groq",
             "status": "valid", "key_enc": KEY_GROQ},
            {"id": "acct-openai", "tenant_id": TENANT, "key_group": "openai",
             "status": assigned_status, "key_enc": KEY_OPENAI},
        ],
    }


def _resolve(tables, provider, account_id):
    loader = TenantConfigManager.__new__(TenantConfigManager)  # tanpa __init__ (hermetik)
    loader._supabase = FakeSB(tables)
    cfg = TenantRunConfig(tenant_id=TENANT)
    with patch("src.utils.crypto.decrypt", side_effect=lambda enc: f"plain:{enc}"):
        loader._set_key_from_pool(cfg, TENANT, provider, "llm_api_key", account_id)
    return cfg.llm_api_key


class TestKoherensiVendorKunci(unittest.TestCase):
    def test_A_akun_sepadan__kunci_akun_dipakai(self):
        key = _resolve(_tables(), provider="openai", account_id="acct-openai")
        self.assertEqual(key, f"plain:{KEY_OPENAI}")

    def test_B_akun_beda_vendor__diabaikan_pakai_akun_vendor_benar(self):
        # Insiden MVT persis: slot Groq ber-akun OpenAI → WAJIB memakai kunci Groq, BUKAN OpenAI.
        key = _resolve(_tables(), provider="groq", account_id="acct-openai")
        self.assertEqual(key, f"plain:{KEY_GROQ}")
        self.assertNotEqual(key, f"plain:{KEY_OPENAI}")

    def test_C_regresi_akun_tak_valid__auto_vendor(self):
        key = _resolve(_tables(assigned_status="invalid"), provider="openai", account_id="acct-openai")
        # akun openai tak-valid → auto vendor openai TIDAK menemukan akun valid → '' (gagal jujur)
        self.assertEqual(key, "")
        # sedangkan slot groq (vendor lain) tetap sehat
        key2 = _resolve(_tables(assigned_status="invalid"), provider="groq", account_id=None)
        self.assertEqual(key2, f"plain:{KEY_GROQ}")

    def test_D_regresi_vendor_tanpa_akun__kosong_gagal_jujur(self):
        t = _tables()
        t["tenant_ai_accounts"] = [a for a in t["tenant_ai_accounts"] if a["key_group"] != "groq"]
        key = _resolve(t, provider="groq", account_id=None)
        self.assertEqual(key, "")


if __name__ == "__main__":
    unittest.main()
