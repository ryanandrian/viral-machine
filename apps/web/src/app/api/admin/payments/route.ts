import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Ledger transaksi pembayaran (tabel `payments`) — lintas-tenant, service_role, READ-ONLY.
// (Refund/aksi = via dashboard Midtrans; status langganan per-tenant = halaman Tenant — anti-redundan.)
// Tahap 3 (fix kelas "baca-terpotong-senyap"): angka uang = RPC admin_payments_stats (agregat SQL
// SELURUH tabel, kebal limit) — daftar tetap 500 terbaru + total_count agar FE jujur "X dari Y".
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const [{ data: rows, error }, { data: stats, error: eStats }] = await Promise.all([
    admin.from("payments")
      .select("order_id,tenant_id,category,plan_type,ref_id,gross_amount,currency,status,payment_type,created_at")
      .order("created_at", { ascending: false }).limit(500),
    admin.rpc("admin_payments_stats"),
  ]);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (eStats) return NextResponse.json({ error: eStats.message }, { status: 500 });
  const emails: Record<string, string> = {};
  try {
    // paginate PENUH (pola route tenants) — email jangan terpotong senyap di 1000 user
    for (let page = 1; ; page++) {
      const { data: us, error: eU } = await admin.auth.admin.listUsers({ page, perPage: 200 });
      if (eU || !us?.users?.length) break;
      us.users.forEach((u) => { if (u.id && u.email) emails[u.id] = u.email; });
      if (us.users.length < 200) break;
    }
  } catch { /* best-effort */ }
  const s = (Array.isArray(stats) ? stats[0] : stats) as { revenue_idr?: number; settled_count?: number; pending_count?: number; total_count?: number } | null;
  return NextResponse.json({
    payments: (rows ?? []).map((r) => ({ ...r, tenant_email: emails[r.tenant_id] ?? null })),
    stats: { revenue_idr: Number(s?.revenue_idr ?? 0), settled_count: Number(s?.settled_count ?? 0),
             pending_count: Number(s?.pending_count ?? 0), total_count: Number(s?.total_count ?? 0) },
  });
}
