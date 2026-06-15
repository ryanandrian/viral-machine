import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E4 Support inbox (Phase 10.9) — semua tiket lintas-tenant (service_role) + handle tenant + preview.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const [{ data: tickets, error }, { data: msgs }, { data: tenants }] = await Promise.all([
    a.from("support_tickets").select("*").order("updated_at", { ascending: false }),
    a.from("support_messages").select("ticket_id, sender, body, created_at").order("created_at", { ascending: true }),
    a.from("tenant_configs").select("tenant_id, display_handle"),
  ]);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  const handle = new Map((tenants ?? []).map((t) => [t.tenant_id, t.display_handle ?? ""]));
  const lastMsg = new Map<string, { body: string; sender: string }>();
  const count = new Map<string, number>();
  (msgs ?? []).forEach((m) => { lastMsg.set(m.ticket_id, { body: m.body, sender: m.sender }); count.set(m.ticket_id, (count.get(m.ticket_id) ?? 0) + 1); });
  const rows = (tickets ?? []).map((t) => ({
    ...t, tenant_handle: handle.get(t.tenant_id) ?? t.tenant_id.slice(0, 8),
    preview: lastMsg.get(t.id)?.body ?? "", messages: count.get(t.id) ?? 0,
  }));
  const counts = { open: rows.filter((r) => r.status === "open").length, pending: rows.filter((r) => r.status === "pending").length, resolved: rows.filter((r) => r.status === "resolved").length };
  return NextResponse.json({ tickets: rows, counts });
}
