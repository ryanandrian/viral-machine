import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Monthly-release scheduler (PHASE10 §2) — jadwalkan niche masuk katalog publik.
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { niche_id, scheduled_at } = await req.json().catch(() => ({}));
  if (!niche_id || !scheduled_at) return NextResponse.json({ error: "niche_id_and_scheduled_at_required" }, { status: 400 });
  const admin = createAdminClient();
  const { data, error } = await admin.from("niche_releases")
    .insert({ niche_id, scheduled_at, created_by: g.user.email ?? g.user.id }).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  // tandai niche pending sampai rilis
  await admin.from("niches").update({ access_type: "pending", release_scheduled_at: scheduled_at }).eq("niche_id", niche_id);
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.schedule_release", detail: { niche_id, scheduled_at } });
  return NextResponse.json({ ok: true, row: data });
}
