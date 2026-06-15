import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Transition niche → PUBLIC (PHASE10 §2 — exclusivity pipeline "Transition to public").
// access_type='public', released_at=now, hapus exclusive_to/until. + admin_audit.
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const admin = createAdminClient();
  const { data, error } = await admin.from("niches").update({
    access_type: "public", released_at: new Date().toISOString(), exclusive_to: null, exclusive_until: null,
  }).eq("niche_id", id).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.transition_public", target_tenant: data?.exclusive_to ?? null, detail: { niche_id: id } });
  return NextResponse.json({ ok: true, row: data });
}
