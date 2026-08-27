"""PEMULIHAN SEKALI JALAN — atribusi `andarini.nadia` ke AGEN01 + komisi pembayaran 26-Agu.

KENAPA ADA BERKAS INI (owner 27-Agu). Agen AGEN01 (THETANGGA) komplen bahwa `andarini.nadia`
seharusnya tercatat sebagai pelanggan bawaannya. Terbukti: pintu daftar Google tak pernah membawa
kode rujukan (100% karya saya), sehingga atribusinya tak pernah lahir — dan tanpa atribusi, komisi
juga tak pernah lahir saat ia membayar.

⚠️ INI MENYALAHI SSOT §1b BILA TANPA KETOKAN: *"Tanpa kode = bukan bawaan siapa pun. Titik. Tidak
ada klaim belakangan, tidak ada rebutan."* Aturan itu untuk mencegah REBUTAN. Kasus ini beda:
kegagalan mencatat ada di sisi KAMI, dan sistem tak punya jejaknya justru karena cacat itu. Owner
mengetok 27-Agu: *"sudah jelas agen01 komplen, buat apa minta kepastian?"* ⇒ pengecualian ini
tercatat di SSOT bertanggal, bukan diselipkan diam-diam.

Kenapa komisi harus dilahirkan TERPISAH: komisi lahir hanya saat pembayaran diproses
(`record_settlement_commission`, dipanggil dari webhook settlement) dan idempoten per pesanan.
Pembayaran 26-Agu sudah lewat, jadi menambal atribusi saja tidak memunculkan komisinya.

Nilai komisi TIDAK dihitung di berkas ini — dipinjam dari otoritas yang sudah ada (`partner.py`)
supaya angkanya tunduk pada aturan yang sama (persen atas rupiah yang benar-benar masuk, per
bulan-langganan, anti-komisi-diri, rate di-snapshot).

Dijalankan dengan `--kering` lebih dulu (bawaan): menampilkan apa yang AKAN terjadi, nol tulisan.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(AKAR, ".env"))

from supabase import create_client  # noqa: E402

KODE = "AGEN01"
EMAIL = "andarini.nadia@gmail.com"


def main(terapkan: bool) -> int:
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # ── 1. Tenant & kode ──────────────────────────────────────────────────────
    u = next((x for x in (sb.auth.admin.list_users() or [])
              if str(getattr(x, "email", "")).lower() == EMAIL), None)
    if not u:
        print(f"❌ akun {EMAIL} tak ditemukan — BERHENTI")
        return 1
    tenant_id = str(u.id)

    pc = (sb.table("partner_codes").select("code,agent_id,reseller_id,used_count,active")
          .eq("code", KODE).limit(1).execute().data or [None])[0]
    if not pc or not pc.get("active"):
        print(f"❌ kode {KODE} tak ada / tidak aktif — BERHENTI")
        return 1

    ag = (sb.table("agents").select("id,company_name,status,commission_type,commission_value")
          .eq("id", pc["agent_id"]).limit(1).execute().data or [None])[0]
    if not ag or ag.get("status") != "active":
        print("❌ agen pemilik kode tidak aktif — BERHENTI")
        return 1

    sudah = (sb.table("tenant_attribution").select("tenant_id,agent_id,code")
             .eq("tenant_id", tenant_id).limit(1).execute().data or [None])[0]

    # ── 2. Pesanan yang seharusnya berkomisi ──────────────────────────────────
    orders = [o for o in (sb.table("payments")
                          .select("order_id,tenant_id,gross_amount,plan_type,period_months,paid_at,category")
                          .eq("tenant_id", tenant_id).execute().data or [])
              if o.get("paid_at") and (o.get("category") or "subscription") == "subscription"]
    sudah_komisi = {r["order_id"] for r in (sb.table("commission_ledger").select("order_id")
                                            .eq("tenant_id", tenant_id).execute().data or [])}
    perlu = [o for o in orders if o["order_id"] not in sudah_komisi]

    print(f"tenant       : {EMAIL}  ({tenant_id[:8]}…)")
    print(f"agen         : {ag.get('company_name')}  komisi {ag['commission_type']}:{ag['commission_value']}")
    print(f"atribusi kini: {'SUDAH ADA → ' + str(sudah.get('code')) if sudah else 'BELUM ADA'}")
    print(f"pesanan lunas: {len(orders)} · belum berkomisi: {len(perlu)}")
    for o in perlu:
        print(f"   {o['paid_at'][:10]} {o['plan_type']} {o['period_months']}bln "
              f"Rp {float(o['gross_amount']):,.0f}  order={o['order_id']}")

    from src.billing.partner import compute_commission
    total = sum(compute_commission(ag["commission_type"], ag["commission_value"],
                                   int(float(o["gross_amount"])), int(o["period_months"] or 1))
                for o in perlu)
    print(f"komisi agen yang AKAN lahir: Rp {total:,.0f}")

    if not terapkan:
        print("\n(KERING — nol tulisan. Jalankan dengan --terapkan untuk mengeksekusi.)")
        return 0

    # ── 3. Tulis atribusi (sekali; pagar DB migr 0217 melarang mengubah/menghapus) ────
    if not sudah:
        sb.table("tenant_attribution").insert({
            "tenant_id": tenant_id, "agent_id": pc["agent_id"],
            "reseller_id": pc.get("reseller_id"), "code": pc["code"],
        }).execute()
        sb.table("partner_codes").update({"used_count": (pc.get("used_count") or 0) + 1}) \
          .eq("code", pc["code"]).execute()
        print("✅ atribusi ditulis + hitungan pemakaian kode dinaikkan")
    else:
        print("• atribusi sudah ada — dilewati (tak pernah ditimpa, §1b)")

    # ── 4. Lahirkan komisi lewat OTORITAS yang sudah ada ─────────────────────
    from src.billing.partner import record_settlement_commission
    lahir = 0
    for o in perlu:
        hasil = record_settlement_commission(sb, o, o.get("paid_at"))
        if hasil:
            lahir += 1
            print(f"✅ komisi lahir order={o['order_id']}")
    if not perlu:
        print("• nol pesanan yang perlu komisi")

    # ── 5. Bukti sesudah ─────────────────────────────────────────────────────
    cek = sb.table("commission_ledger").select("order_id,agent_amount_idr,status,period_month") \
            .eq("tenant_id", tenant_id).execute().data or []
    print(f"\nbuku komisi tenant ini sekarang: {len(cek)} baris")
    for r in cek:
        print(f"   {r['period_month']} Rp {int(r['agent_amount_idr']):,} status={r['status']}")
    print(f"\nRINGKAS: atribusi {'ADA' if (sudah or True) else '-'} · {lahir} komisi baru lahir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--terapkan" in sys.argv))
