import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// Data invoice/bukti bayar untuk order_id. Akses: PEMILIK (sesi) ATAU super-admin. Data = penjual
// (company_profile), pembeli (tenant), transaksi (payments), PPN (app_config, no-hardcode).
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id: order_id } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const isAdmin = user.app_metadata?.role === "super_admin";

  const admin = createAdminClient();
  const { data: pay } = await admin.from("payments")
    .select("order_id,tenant_id,category,plan_type,ref_id,gross_amount,currency,status,payment_type,period_start,period_end,period_months,created_at")
    .eq("order_id", order_id).maybeSingle();
  if (!pay) return NextResponse.json({ error: "not_found" }, { status: 404 });
  if (!isAdmin && pay.tenant_id !== user.id) return NextResponse.json({ error: "forbidden" }, { status: 403 });

  // Nama paket yang dilihat pelanggan = plan_limits.display_name (Pilar 4 — bukan key mentah).
  let planDisplayName: string | null = null;
  if (pay.plan_type) {
    const { data: pl } = await admin.from("plan_limits").select("display_name").eq("plan_type", pay.plan_type).maybeSingle();
    planDisplayName = (pl?.display_name as string | undefined) ?? null;
  }

  const { data: tc } = await admin.from("tenant_configs").select("display_handle").eq("tenant_id", pay.tenant_id).maybeSingle();
  let email: string | null = null;
  try { const { data } = await admin.auth.admin.getUserById(pay.tenant_id); email = data?.user?.email ?? null; } catch { /* best-effort */ }
  const { data: co } = await admin.from("company_profile").select("*").eq("id", 1).maybeSingle();
  const { data: ppn } = await admin.from("app_config").select("value").eq("key", "ppn_percent").maybeSingle();

  return NextResponse.json({
    payment: pay,
    plan_display_name: planDisplayName,
    buyer: { name: (tc as { display_handle?: string } | null)?.display_handle ?? null, email },
    company: co ?? null,
    ppn_percent: (ppn as { value?: number } | null)?.value ?? 0,
  });
}
