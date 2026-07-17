import { NextResponse } from "next/server";
import { requireAgent } from "@/lib/agent/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] F2 — SATU pintu data portal agen. Semua query difilter PAKSA agent.id dari sesi
// (SPEC §6: agen hanya melihat miliknya; nomor rekening TIDAK pernah ikut — hanya penanda terisi).
// Angka bersumber tabel yang sama dgn admin rinci-per-agen (SPEC §1f: satu sumber, nol selisih).
export async function GET() {
  const g = await requireAgent(); if (g.error) return g.error;
  const a = createAdminClient();
  const id = g.agent.id;
  const [{ data: codes }, { data: att }, { data: ledger }, { data: payouts }, { data: cfg }] = await Promise.all([
    a.from("partner_codes").select("code,owner_kind,active,used_count").eq("agent_id", id),
    a.from("tenant_attribution").select("tenant_id,code,locked_at").eq("agent_id", id),
    a.from("commission_ledger")
      .select("id,order_id,entry_kind,status,agent_amount_idr,period_month,months_paid,created_at")
      .eq("agent_id", id).order("id", { ascending: false }).limit(200),
    a.from("agent_payouts").select("*").eq("agent_id", id).order("period_month", { ascending: false }),
    a.from("app_config").select("key,value").in("key", ["partner_payout_day", "partner_min_payout_idr"]),
  ]);
  const tenantIds = (att ?? []).map((r) => r.tenant_id);
  const { data: tenants } = tenantIds.length
    ? await a.from("tenant_configs").select("tenant_id,display_handle,plan_type,subscription_status").in("tenant_id", tenantIds)
    : { data: [] };
  const ag = g.agent;
  return NextResponse.json({
    agent: {
      company_name: ag.company_name, pic_name: ag.pic_name, status: ag.status,
      commission_type: ag.commission_type, commission_value: ag.commission_value,
      bank_name: ag.bank_name, bank_holder: ag.bank_holder,
      bank_account_set: Boolean(ag.bank_account_enc),
    },
    codes: codes ?? [],
    tenants: (tenants ?? []).map((t) => ({
      // label seperlunya (SPEC §6) — tanpa email/identitas penuh
      label: t.display_handle || `Tenant ${t.tenant_id.slice(0, 6)}…`,
      plan: t.plan_type, status: t.subscription_status,
      locked_at: (att ?? []).find((x) => x.tenant_id === t.tenant_id)?.locked_at ?? null,
      code: (att ?? []).find((x) => x.tenant_id === t.tenant_id)?.code ?? null,
    })),
    ledger: ledger ?? [],
    payouts: payouts ?? [],
    config: Object.fromEntries((cfg ?? []).map((c) => [c.key, c.value])),
  });
}
