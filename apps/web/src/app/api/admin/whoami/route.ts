import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Diagnostik fondasi admin (PHASE10 §1): buktikan gate super-admin + akses service_role lintas-tenant.
// no-session → 401, tenant biasa → 403, super-admin → 200 + jumlah tenant (bypass RLS).
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;

  const admin = createAdminClient();
  const { count, error } = await admin
    .from("tenant_configs")
    .select("tenant_id", { count: "exact", head: true });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({
    email: g.user.email,
    role: g.user.app_metadata?.role,
    tenant_count: count ?? 0,
  });
}
