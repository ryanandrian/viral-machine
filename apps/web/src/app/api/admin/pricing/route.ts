import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E5 Pricing (PHASE10 §2) — sumber harga SELURUH sistem. service_role bypass-RLS.
// Baca pricing_config (semua) + plan_limits + app_config. POST = tambah entri (Tahap 3).

// Tambah entri pricing_config dari UI (Tahap 3 finalisasi_tier_plan — utk add-on masa depan DESAIN §4).
// Validasi ketat di titik input: key snake_case unik, IDR bulat ≥0. Audit: pricing_audit (old=null) + admin_audit.
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const key = String(b.key ?? "").trim();
  if (!/^[a-z0-9_]{3,64}$/.test(key)) return NextResponse.json({ error: "invalid_key" }, { status: 400 });
  const value_idr = Number(b.value_idr);
  if (!Number.isInteger(value_idr) || value_idr < 0) return NextResponse.json({ error: "invalid_value_idr" }, { status: 400 });
  const category = String(b.category ?? "one_time").trim().slice(0, 40) || "one_time";
  const description = String(b.description ?? "").trim().slice(0, 200) || null;

  const admin = createAdminClient();
  const { data: dup } = await admin.from("pricing_config").select("key").eq("key", key).maybeSingle();
  if (dup) return NextResponse.json({ error: "key_exists" }, { status: 409 });

  const { data: created, error } = await admin.from("pricing_config")
    .insert({ key, value_idr, category, description, active: Boolean(b.active ?? true), updated_by: g.user.email ?? g.user.id })
    .select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  await admin.from("pricing_audit").insert({ key, old_value: null, new_value: created, changed_by: g.user.email ?? g.user.id });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "pricing.create", detail: { key, value_idr, category } });
  return NextResponse.json({ ok: true, row: created });
}

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const [pricing, planLimits, appConfig] = await Promise.all([
    admin.from("pricing_config").select("*").order("category").order("key"),
    admin.from("plan_limits").select("*").order("max_channels"),
    admin.from("app_config").select("*").order("key"),
  ]);
  if (pricing.error) return NextResponse.json({ error: pricing.error.message }, { status: 500 });
  return NextResponse.json({
    pricing: pricing.data ?? [],
    plan_limits: planLimits.data ?? [],
    app_config: appConfig.data ?? [],
  });
}
