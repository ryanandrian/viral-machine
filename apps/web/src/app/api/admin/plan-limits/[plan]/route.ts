import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// PATCH plan_limits[plan] (PHASE10 §2) — caps admin-editable (DESAIN §4 no-hardcode).
export async function PATCH(req: Request, { params }: { params: Promise<{ plan: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { plan } = await params;
  const body = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of ["max_videos_per_day", "max_channels", "sort_order"]) {
    if (k in body) {
      const n = Number(body[k]);
      if (!Number.isInteger(n) || n < 0) return NextResponse.json({ error: `invalid ${k}` }, { status: 400 });
      patch[k] = n;
    }
  }
  // Tier config-driven (owner 2026-06-21): nama-tampil + fasilitas Niche Studio per-tier (no-hardcode).
  if ("display_name" in body) {
    const s = String(body.display_name ?? "").trim();
    if (!s || s.length > 40) return NextResponse.json({ error: "invalid display_name" }, { status: 400 });
    patch.display_name = s;
  }
  if ("niche_studio" in body) patch.niche_studio = Boolean(body.niche_studio);
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });

  const admin = createAdminClient();
  const { data, error } = await admin.from("plan_limits").update(patch).eq("plan_type", plan).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "plan_limits.update", detail: { plan, patch } });
  return NextResponse.json({ ok: true, row: data });
}
