import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E1 list tenant (PHASE10 §2). service_role bypass-RLS lintas-tenant. MRR = pembayaran lunas terakhir
// per tenant ÷ period_months (active & non-comp; fallback harga list bila tanpa jejak bayar — Tahap 3).
// Email dari Auth admin API. Last activity = production_runs terbaru per tenant.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();

  const { data: tenants, error } = await admin
    .from("tenant_configs")
    .select("tenant_id, display_handle, plan_type, subscription_status, current_period_end, trial_started_at, is_developer, discount_pct, created_at, lead_temp, suspended_at, blocked_at, deletion_scheduled_at")
    .order("created_at", { ascending: false });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // email per uid (Auth admin, paginate)
  const emailMap = new Map<string, string>();
  for (let page = 1; ; page++) {
    const { data, error: e } = await admin.auth.admin.listUsers({ page, perPage: 200 });
    if (e || !data?.users?.length) break;
    for (const u of data.users) emailMap.set(u.id, u.email ?? "");
    if (data.users.length < 200) break;
  }

  // channels count + last activity
  const { data: chs } = await admin.from("channels").select("tenant_id");
  const chCount = new Map<string, number>();
  (chs ?? []).forEach((c) => chCount.set(c.tenant_id, (chCount.get(c.tenant_id) ?? 0) + 1));

  const { data: runs } = await admin
    .from("production_runs").select("tenant_id, created_at").order("created_at", { ascending: false });
  const lastAct = new Map<string, string>();
  (runs ?? []).forEach((r) => { if (!lastAct.has(r.tenant_id)) lastAct.set(r.tenant_id, r.created_at); });

  // MRR = pembayaran NYATA terakhir yang lunas per tenant, dinormalkan bulanan (gross ÷ period_months)
  // — Tahap 3 finalisasi_tier_plan: diskon/tahunan tercermin jujur, bukan harga list pura-pura.
  // Fallback harga list hanya utk tenant active tanpa jejak pembayaran (kasus lawas/manual).
  const { data: pricing } = await admin
    .from("pricing_config").select("key, value_idr").eq("active", true).eq("category", "subscription");
  const priceMap = new Map((pricing ?? []).map((p) => [p.key, p.value_idr as number]));
  const { data: paid } = await admin.from("payments")
    .select("tenant_id, gross_amount, period_months, status, created_at")
    .eq("category", "subscription").in("status", ["settlement", "capture", "paid"])
    .order("created_at", { ascending: false });
  const paidMonthly = new Map<string, number>();
  (paid ?? []).forEach((p) => {
    if (!paidMonthly.has(p.tenant_id)) {
      paidMonthly.set(p.tenant_id, Math.round((p.gross_amount ?? 0) / Math.max(1, p.period_months ?? 1)));
    }
  });

  const rows = (tenants ?? []).map((t) => {
    const comp = t.is_developer || (t.discount_pct ?? 0) >= 100;
    const paying = !comp && t.subscription_status === "active";
    return {
      tenant_id: t.tenant_id,
      handle: t.display_handle ?? "",
      email: emailMap.get(t.tenant_id) ?? "",
      plan: t.plan_type,
      status: t.subscription_status,
      comp,
      mrr_idr: paying ? (paidMonthly.get(t.tenant_id) ?? priceMap.get(`plan_${t.plan_type}`) ?? 0) : 0,
      channels: chCount.get(t.tenant_id) ?? 0,
      joined: t.created_at,
      last_activity: lastAct.get(t.tenant_id) ?? null,
      current_period_end: t.current_period_end,
      trial_started_at: t.trial_started_at,
      lead_temp: t.lead_temp ?? null,
      suspended_at: t.suspended_at ?? null,
      blocked_at: t.blocked_at ?? null,
      deletion_scheduled_at: t.deletion_scheduled_at ?? null,
    };
  });

  const kpi = {
    total: rows.filter((r) => r.status !== "deleted").length,   // cangkang akun terhapus bukan tenant
    mrr_idr: rows.reduce((s, r) => s + r.mrr_idr, 0),
    trials: rows.filter((r) => r.status === "trial").length,
    trial_expired: rows.filter((r) => r.status === "trial_expired").length,
    suspended: rows.filter((r) => r.status === "suspended").length,
    blocked: rows.filter((r) => r.status === "blocked").length,
  };
  return NextResponse.json({ rows, kpi });
}
