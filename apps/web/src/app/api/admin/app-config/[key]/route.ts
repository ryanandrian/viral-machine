import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// PATCH app_config[key] (PHASE10 §2) — mis. trial_duration_days (int, admin-editable, no-hardcode).
export async function PATCH(req: Request, { params }: { params: Promise<{ key: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { key } = await params;
  const { value } = await req.json().catch(() => ({}));
  const n = Number(value);
  if (!Number.isInteger(n)) return NextResponse.json({ error: "value must be integer" }, { status: 400 });

  const admin = createAdminClient();
  const { data, error } = await admin.from("app_config")
    .update({ value: n, updated_at: new Date().toISOString() }).eq("key", key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "app_config.update", detail: { key, value: n } });
  return NextResponse.json({ ok: true, row: data });
}
