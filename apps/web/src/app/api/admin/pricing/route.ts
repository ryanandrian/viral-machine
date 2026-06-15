import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E5 Pricing (PHASE10 §2) — sumber harga SELURUH sistem. service_role bypass-RLS.
// Baca pricing_config (semua) + plan_limits + app_config.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const [pricing, planLimits, appConfig] = await Promise.all([
    admin.from("pricing_config").select("*").order("category").order("key"),
    admin.from("plan_limits").select("*").order("max_channels"),
    admin.from("app_config").select("*").order("key"),
  ]);
  if (pricing.error) return NextResponse.json({ error: pricing.error.message }, { status: 500 });
  return NextResponse.json({
    pricing: pricing.data ?? [],
    plan_limits: planLimits.data ?? [],
    app_config: appConfig.data ?? [],
  });
}
