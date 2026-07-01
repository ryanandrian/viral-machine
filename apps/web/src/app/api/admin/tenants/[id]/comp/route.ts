import { NextResponse, type NextRequest } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Set COMP/DISKON tenant (is_developer = gratis-selamanya; discount_pct 0-100). Super-admin only + audit.
// Comp (is_developer / discount≥100) → tenant EXEMPT dari sweep billing (selalu producing).
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const b = await req.json().catch(() => ({}));
  const upd: Record<string, unknown> = {};
  if (typeof b.is_developer === "boolean") upd.is_developer = b.is_developer;
  if (b.discount_pct != null) upd.discount_pct = Math.max(0, Math.min(100, parseInt(b.discount_pct, 10) || 0));
  if (Object.keys(upd).length === 0) return NextResponse.json({ error: "tidak ada perubahan" }, { status: 400 });

  const admin = createAdminClient();
  const { error } = await admin.from("tenant_configs").update(upd).eq("tenant_id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "tenant.comp", target_tenant: id, detail: upd });
  return NextResponse.json({ ok: true, ...upd });
}
