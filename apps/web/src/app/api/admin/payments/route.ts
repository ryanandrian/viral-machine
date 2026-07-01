import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Ledger transaksi pembayaran (tabel `payments`) — lintas-tenant, service_role, READ-ONLY.
// (Refund/aksi = via dashboard Midtrans; status langganan per-tenant = halaman Tenant — anti-redundan.)
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data: rows, error } = await admin.from("payments")
    .select("order_id,tenant_id,category,plan_type,ref_id,gross_amount,currency,status,payment_type,created_at")
    .order("created_at", { ascending: false }).limit(500);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  const emails: Record<string, string> = {};
  try {
    const { data: us } = await admin.auth.admin.listUsers({ perPage: 1000 });
    (us?.users ?? []).forEach((u) => { if (u.id && u.email) emails[u.id] = u.email; });
  } catch { /* best-effort */ }
  return NextResponse.json({ payments: (rows ?? []).map((r) => ({ ...r, tenant_email: emails[r.tenant_id] ?? null })) });
}
