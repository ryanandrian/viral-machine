import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E4 ticket detail + messages + konteks tenant (Phase 10.9).
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const a = createAdminClient();
  const { data: ticket, error } = await a.from("support_tickets").select("*").eq("id", id).maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!ticket) return NextResponse.json({ error: "not_found" }, { status: 404 });
  const [{ data: messages }, { data: cfg }, { data: chCount }] = await Promise.all([
    a.from("support_messages").select("*").eq("ticket_id", id).order("created_at"),
    a.from("tenant_configs").select("display_handle, plan_type, subscription_status, created_at").eq("tenant_id", ticket.tenant_id).maybeSingle(),
    a.from("channels").select("id", { count: "exact", head: true }).eq("tenant_id", ticket.tenant_id),
  ]);
  return NextResponse.json({ ticket, messages: messages ?? [], tenant: cfg ?? null, channels: chCount?.length ?? 0 });
}
