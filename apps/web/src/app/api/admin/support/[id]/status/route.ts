import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E4 ubah status tiket (Phase 10.9) — resolve/reopen. Body: { status }.
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const { status } = await req.json().catch(() => ({}));
  if (!["open", "pending", "resolved"].includes(status)) return NextResponse.json({ error: "invalid_status" }, { status: 400 });
  const a = createAdminClient();
  const { error } = await a.from("support_tickets").update({ status, updated_at: new Date().toISOString() }).eq("id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "support.status", detail: { ticket_id: id, status } });
  return NextResponse.json({ ok: true, status });
}
