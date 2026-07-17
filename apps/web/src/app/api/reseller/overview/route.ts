import { NextResponse } from "next/server";
import { requireReseller } from "@/lib/reseller/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] F3 — SATU pintu data portal reseller: HANYA miliknya (filter reseller.id dari sesi).
// Angka = reseller_amount_idr dari buku besar yang sama (satu sumber). Catatan penting bagi
// reseller: ini PERHITUNGAN; pembayarannya dilakukan AGEN Anda tiap bulan (SPEC §1a).
export async function GET() {
  const g = await requireReseller(); if (g.error) return g.error;
  const a = createAdminClient();
  const rs = g.reseller;
  const [{ data: codes }, { data: att }, { data: ledger }, { data: ag }] = await Promise.all([
    a.from("partner_codes").select("code,active,used_count").eq("reseller_id", rs.id),
    a.from("tenant_attribution").select("tenant_id,locked_at").eq("reseller_id", rs.id),
    a.from("commission_ledger")
      .select("id,entry_kind,reseller_amount_idr,period_month,months_paid,created_at")
      .eq("reseller_id", rs.id).order("id", { ascending: false }).limit(300),
    a.from("agents").select("company_name").eq("id", rs.agent_id).limit(1),
  ]);
  const tenantIds = (att ?? []).map((r) => r.tenant_id);
  const { data: tenants } = tenantIds.length
    ? await a.from("tenant_configs").select("tenant_id,display_handle,subscription_status").in("tenant_id", tenantIds)
    : { data: [] };
  // agregat per bulan (pencapaian per periode — SPEC §1e)
  const monthly: Record<string, { total: number; n: number }> = {};
  for (const l of ledger ?? []) {
    const m = (monthly[l.period_month] ??= { total: 0, n: 0 });
    m.total += Number(l.reseller_amount_idr);
    if (l.entry_kind === "accrual") m.n += 1;
  }
  return NextResponse.json({
    reseller: { name: rs.name, status: rs.status, commission_type: rs.commission_type,
      commission_value: rs.commission_value, bank_name: rs.bank_name, bank_holder: rs.bank_holder,
      bank_account_set: Boolean(rs.bank_account_enc), agent_company: ag?.[0]?.company_name ?? "" },
    code: (codes ?? []).find((c) => c.active)?.code ?? null,
    tenants: (tenants ?? []).map((t) => ({
      label: t.display_handle || `Tenant ${t.tenant_id.slice(0, 6)}…`, status: t.subscription_status,
      locked_at: (att ?? []).find((x) => x.tenant_id === t.tenant_id)?.locked_at ?? null,
    })),
    monthly: Object.entries(monthly).map(([period, v]) => ({ period, total_idr: v.total, n_payment: v.n }))
      .sort((x, y) => (x.period < y.period ? 1 : -1)),
  });
}
