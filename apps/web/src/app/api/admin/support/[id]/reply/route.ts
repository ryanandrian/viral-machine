import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E4 admin balas tiket (Phase 10.9) — insert support_messages(sender='admin') + ticket → pending + touch.
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const { body } = await req.json().catch(() => ({}));
  if (!body?.trim()) return NextResponse.json({ error: "body_required" }, { status: 400 });
  const a = createAdminClient();
  const { error } = await a.from("support_messages").insert({ ticket_id: id, sender: "admin", body: body.trim() });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("support_tickets").update({ status: "pending", updated_at: new Date().toISOString(), assigned_to: g.user.email ?? g.user.id }).eq("id", id);
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "support.reply", detail: { ticket_id: id } });
  return NextResponse.json({ ok: true });
}
