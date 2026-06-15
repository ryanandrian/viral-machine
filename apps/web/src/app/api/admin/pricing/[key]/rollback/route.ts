import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

const EDITABLE = ["value_idr", "value_usd_cents", "description", "category", "active", "effective_from", "effective_until"];

// Rollback pricing key ke nilai LAMA dari satu entri pricing_audit (PHASE10 §2).
// Body: { audit_id }. Menulis audit baru (rollback = perubahan baru, bukan hapus histori).
export async function POST(req: Request, { params }: { params: Promise<{ key: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { key } = await params;
  const { audit_id } = await req.json().catch(() => ({}));
  if (!audit_id) return NextResponse.json({ error: "audit_id_required" }, { status: 400 });

  const admin = createAdminClient();
  const { data: entry } = await admin.from("pricing_audit").select("old_value").eq("id", audit_id).eq("key", key).maybeSingle();
  if (!entry?.old_value) return NextResponse.json({ error: "audit_not_found" }, { status: 404 });

  const { data: cur } = await admin.from("pricing_config").select("*").eq("key", key).maybeSingle();
  const old = entry.old_value as Record<string, unknown>;
  const patch: Record<string, unknown> = {};
  for (const k of EDITABLE) if (k in old) patch[k] = old[k];
  patch.updated_by = g.user.email ?? g.user.id;
  patch.updated_at = new Date().toISOString();

  const { data: updated, error } = await admin.from("pricing_config").update(patch).eq("key", key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  await admin.from("pricing_audit").insert({ key, old_value: cur, new_value: updated, changed_by: `${g.user.email ?? g.user.id} (rollback)` });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "pricing.rollback", detail: { key, audit_id } });
  return NextResponse.json({ ok: true, row: updated });
}
