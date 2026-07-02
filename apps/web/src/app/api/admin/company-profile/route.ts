import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Company Profile (admin) — data perusahaan penerbit (dipakai di invoice) + Telegram ID admin (notifikasi tenant).
// Single-row. service_role + requireSuperAdmin + admin_audit. TERPISAH dari System Config (app_config).
const FIELDS = [
  "legal_name", "brand", "tagline", "website", "email", "phone", "address",
  "npwp", "nib", "sk_menkum", "business_scope", "admin_telegram_chat_id",
] as const;

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin.from("company_profile").select("*").order("id").limit(1).maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ profile: data ?? null });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const body = await req.json().catch(() => ({} as Record<string, unknown>));
  const admin = createAdminClient();

  // ambil baris tunggal (jangan asumsikan id=1)
  const { data: row, error: e0 } = await admin.from("company_profile").select("id").order("id").limit(1).maybeSingle();
  if (e0) return NextResponse.json({ error: e0.message }, { status: 500 });
  if (!row) return NextResponse.json({ error: "company_profile belum ada" }, { status: 404 });

  // whitelist field (trim; string kosong → null utk admin_telegram_chat_id agar alarm mati bersih)
  const upd: Record<string, unknown> = { updated_at: new Date().toISOString() };
  for (const f of FIELDS) {
    if (f in body) {
      const v = typeof body[f] === "string" ? (body[f] as string).trim() : body[f];
      upd[f] = f === "admin_telegram_chat_id" && v === "" ? null : v;
    }
  }

  const { data, error } = await admin.from("company_profile").update(upd).eq("id", row.id).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({
    admin_uid: g.user.id, action: "company_profile.update",
    detail: { fields: Object.keys(upd).filter((k) => k !== "updated_at") },
  });
  return NextResponse.json({ ok: true, profile: data });
}
