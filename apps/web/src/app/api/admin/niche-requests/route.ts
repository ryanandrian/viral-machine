import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E2.3 — antrian pengajuan custom niche (niche_requests). Admin approve → buat niche EKSKLUSIF
// utk tenant (public_90d: exclusive_until=+90h; private: permanen) lalu tandai request 'live'.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data: reqs, error } = await admin.from("niche_requests").select("*").order("created_at", { ascending: false });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  const emails: Record<string, string> = {};
  try {
    const { data: us } = await admin.auth.admin.listUsers();
    (us?.users ?? []).forEach((u) => { if (u.id && u.email) emails[u.id] = u.email; });
  } catch { /* best-effort */ }
  return NextResponse.json({ requests: (reqs ?? []).map((r) => ({ ...r, tenant_email: emails[r.tenant_id] ?? null })) });
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const admin = createAdminClient();
  const { data: r } = await admin.from("niche_requests").select("*").eq("request_id", b.request_id).single();
  if (!r) return NextResponse.json({ error: "request tak ditemukan" }, { status: 404 });
  const now = new Date().toISOString();

  if (b.action === "reject") {
    await admin.from("niche_requests").update({ status: "rejected", admin_note: b.admin_note ?? null, updated_at: now }).eq("request_id", b.request_id);
    await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche_request.reject", target_tenant: r.tenant_id, detail: { request_id: b.request_id } });
    return NextResponse.json({ ok: true });
  }
  if (b.action === "approve") {
    const niche_id = String(b.niche_id ?? "").trim();
    if (!/^[a-z0-9_]+$/.test(niche_id)) return NextResponse.json({ error: "niche_id slug invalid (a-z0-9_)" }, { status: 400 });
    const exclusive_until = r.request_type === "public_90d" ? new Date(Date.now() + 90 * 864e5).toISOString() : null;
    const { error: ne } = await admin.from("niches").insert({
      niche_id, name: r.title, is_active: true, is_base: false,
      access_type: "private", exclusive_to: r.tenant_id, exclusive_until,
    });
    if (ne) return NextResponse.json({ error: `buat niche gagal: ${ne.message}` }, { status: 500 });
    await admin.from("niche_requests").update({ status: "live", niche_id, admin_note: b.admin_note ?? null, updated_at: now }).eq("request_id", b.request_id);
    await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche_request.approve", target_tenant: r.tenant_id, detail: { request_id: b.request_id, niche_id, exclusive_until } });
    return NextResponse.json({ ok: true, niche_id });
  }
  return NextResponse.json({ error: "action invalid" }, { status: 400 });
}
