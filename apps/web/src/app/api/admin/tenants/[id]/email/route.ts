import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E1 "Kirim email" (PHASE10 §3) — ANTRE ke email_outbox; worker Python yang resolve email tenant
// (Auth admin API) + kirim SMTP (fail-soft). Owner pilih platform-queue. Dicatat ke admin_audit.
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const { subject, body } = await req.json().catch(() => ({}));
  if (!subject?.trim() || !body?.trim()) {
    return NextResponse.json({ error: "subject_and_body_required" }, { status: 400 });
  }
  const admin = createAdminClient();

  const { data, error } = await admin
    .from("email_outbox")
    .insert({ tenant_id: id, subject: subject.trim(), body: body.trim(), created_by: g.user.id })
    .select("id")
    .single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  await admin.from("admin_audit").insert({
    admin_uid: g.user.id,
    action: "tenant.email_queued",
    target_tenant: id,
    detail: { email_id: data.id, subject: subject.trim() },
  });

  return NextResponse.json({ ok: true, queued: data.id });
}
