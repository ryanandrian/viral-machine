import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

const EDITABLE = ["value_idr", "value_usd_cents", "description", "category", "active", "effective_from", "effective_until"];

// PATCH pricing_config[key] (PHASE10 §2). Snapshot old→pricing_audit, lalu update + updated_by/at.
// Whitelist kolom (jangan biarkan ubah key/PK). + admin_audit.
export async function PATCH(req: Request, { params }: { params: Promise<{ key: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { key } = await params;
  const body = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of EDITABLE) if (k in body) patch[k] = body[k];
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_editable_fields" }, { status: 400 });

  const admin = createAdminClient();
  const { data: old, error: e0 } = await admin.from("pricing_config").select("*").eq("key", key).maybeSingle();
  if (e0) return NextResponse.json({ error: e0.message }, { status: 500 });
  if (!old) return NextResponse.json({ error: "not_found" }, { status: 404 });

  patch.updated_by = g.user.email ?? g.user.id;
  patch.updated_at = new Date().toISOString();
  const { data: updated, error } = await admin.from("pricing_config").update(patch).eq("key", key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  await admin.from("pricing_audit").insert({ key, old_value: old, new_value: updated, changed_by: g.user.email ?? g.user.id });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "pricing.update", detail: { key, fields: Object.keys(patch) } });
  return NextResponse.json({ ok: true, row: updated });
}
