"""
Uji regresi PERMANEN — [B21] Anti-komisi-diri di mesin komisi (fix 2026-07-19).
Hermetik (nol DB/jaringan — FakeSB meniru rantai sb.table().select().eq().limit().execute()).

Jalankan:  python -m unittest tests.test_partner_self_commission

Yang dijaga (SPEC AGENT_AND_AFILIATION §5g.9 + §6 — dulu hanya tertulis, tak ditegakkan kode):
  A. Pembayar == pemilik login AGEN  → agent_amount_idr = 0 (baris ledger tetap lahir; jejak audit).
  B. Pembayar == pemilik login RESELLER → reseller_amount_idr = 0, komisi agen TETAP utuh.
  C. REGRESI: order normal (tanpa hubungan identitas) → nominal TIDAK berubah.
  D. REGRESI: user_id agen/reseller NULL (belum diundang) → tidak meledak, nominal utuh.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing.partner import record_settlement_commission  # noqa: E402


# ── FakeSB: meniru persis rantai panggilan supabase-py yang dipakai partner.py ──
class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink):
        self._rows, self._sink = rows, sink
        self._inserted = None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, row):
        self._inserted = row
        self._sink.append(row)
        return self

    def execute(self):
        if self._inserted is not None:
            return _Result([{**self._inserted, "id": "ledger-uji-1"}])
        return _Result(self._rows)


class FakeSB:
    def __init__(self, tables):
        self._tables = tables
        self.inserted = []  # semua baris insert (commission_ledger) tertangkap di sini

    def table(self, name):
        return _Query(self._tables.get(name, []), self.inserted)


AGENT_UID    = "agent-login-uid-001"
RESELLER_UID = "reseller-login-uid-002"
TENANT_BIASA = "tenant-uid-lain-003"


def _tables(agent_user_id, reseller_user_id, with_reseller=True):
    return {
        "tenant_attribution": [{
            "tenant_id": "DIISI-PER-UJI", "agent_id": "ag-1",
            "reseller_id": ("rs-1" if with_reseller else None), "code": "KODE1",
        }],
        "agents": [{
            "id": "ag-1", "status": "active", "commission_type": "flat_idr",
            "commission_value": 100000, "user_id": agent_user_id,
        }],
        "resellers": [{
            "id": "rs-1", "commission_type": "flat_idr",
            "commission_value": 25000, "user_id": reseller_user_id,
        }],
        "app_config": [],
        "commission_ledger": [],
    }


def _order(tenant_id):
    return {"order_id": "MV-uji-1", "tenant_id": tenant_id, "category": "subscription",
            "gross_amount": 349000, "period_months": 1, "paid_at": "2026-07-19T10:00:00+00:00"}


def _run(tables, tenant_id):
    tables["tenant_attribution"][0]["tenant_id"] = tenant_id
    sb = FakeSB(tables)
    res = record_settlement_commission(sb, _order(tenant_id))
    ledger = [r for r in sb.inserted if r.get("entry_kind") == "accrual"]
    assert len(ledger) == 1, f"ledger harus tepat 1 baris, dapat {len(ledger)}"
    return res, ledger[0]


class TestAntiKomisiDiri(unittest.TestCase):
    def test_A_pembayar_adalah_login_agen__komisi_agen_nol(self):
        res, row = _run(_tables(AGENT_UID, RESELLER_UID), tenant_id=AGENT_UID)
        self.assertEqual(row["agent_amount_idr"], 0)
        self.assertEqual(res["agent_amount_idr"], 0)
        # jatah reseller tak ikut hangus oleh self-referral agen
        self.assertEqual(row["reseller_amount_idr"], 25000)

    def test_B_pembayar_adalah_login_reseller__jatah_reseller_nol_agen_utuh(self):
        _res, row = _run(_tables(AGENT_UID, RESELLER_UID), tenant_id=RESELLER_UID)
        self.assertEqual(row["reseller_amount_idr"], 0)
        self.assertEqual(row["agent_amount_idr"], 100000)  # agen tak bersalah — tetap dibayar

    def test_C_regresi_order_normal__nominal_tak_berubah(self):
        _res, row = _run(_tables(AGENT_UID, RESELLER_UID), tenant_id=TENANT_BIASA)
        self.assertEqual(row["agent_amount_idr"], 100000)
        self.assertEqual(row["reseller_amount_idr"], 25000)

    def test_D_regresi_user_id_null__tak_meledak_nominal_utuh(self):
        _res, row = _run(_tables(None, None), tenant_id=TENANT_BIASA)
        self.assertEqual(row["agent_amount_idr"], 100000)
        self.assertEqual(row["reseller_amount_idr"], 25000)

    def test_E_regresi_tanpa_reseller__jalur_agen_saja_utuh(self):
        _res, row = _run(_tables(AGENT_UID, RESELLER_UID, with_reseller=False), tenant_id=TENANT_BIASA)
        self.assertEqual(row["agent_amount_idr"], 100000)
        self.assertEqual(row["reseller_amount_idr"], 0)


if __name__ == "__main__":
    unittest.main()
