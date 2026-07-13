import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Matriks perbandingan fitur /pricing (Tahap 4) — baris = DATA (plan_matrix_rows).
// GET daftar · POST tambah baris. Aturan sel (token dinormalisasi kapital) = SATU sumber lib/admin/plan-matrix.
import { MATRIX_CELLS as CELLS, normalizeCell } from "@/lib/admin/plan-matrix";

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin.from("plan_matrix_rows").select("*").order("sort_order");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ rows: data ?? [] });
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const label_id = String(b.label_id ?? "").trim();
  const label_en = String(b.label_en ?? "").trim() || label_id;
  if (!label_id || label_id.length > 80 || label_en.length > 80) return NextResponse.json({ error: "invalid_label" }, { status: 400 });
  const row: Record<string, unknown> = {
    label_id, label_en,
    is_group: Boolean(b.is_group),
    sort_order: Number.isInteger(Number(b.sort_order)) ? Number(b.sort_order) : 999,
  };
  for (const c of CELLS) {
    const v = normalizeCell(b[c]);
    if (v && typeof v === "object") return NextResponse.json({ error: `invalid ${c}` }, { status: 400 });
    row[c] = v;
  }
  const admin = createAdminClient();
  const { data, error } = await admin.from("plan_matrix_rows").insert(row).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "plan_matrix.create", detail: { id: data.id, label_id } });
  return NextResponse.json({ ok: true, row: data });
}
