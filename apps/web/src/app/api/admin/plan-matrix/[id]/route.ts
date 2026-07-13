import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// PATCH/DELETE satu baris matriks perbandingan (Tahap 4). Aturan sel = SATU sumber lib/admin/plan-matrix
// (token dinormalisasi kapital di titik input — typo "True" tak pernah bocor sebagai teks ke /pricing).
import { MATRIX_CELLS as CELLS, normalizeCell } from "@/lib/admin/plan-matrix";

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const rowId = parseInt(id, 10);
  if (!Number.isInteger(rowId)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  const b = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of ["label_id", "label_en"]) {
    if (k in b) {
      const s = String(b[k] ?? "").trim();
      if (!s || s.length > 80) return NextResponse.json({ error: `invalid ${k}` }, { status: 400 });
      patch[k] = s;
    }
  }
  if ("is_group" in b) patch.is_group = Boolean(b.is_group);
  if ("sort_order" in b) {
    const n = Number(b.sort_order);
    if (!Number.isInteger(n)) return NextResponse.json({ error: "invalid sort_order" }, { status: 400 });
    patch.sort_order = n;
  }
  for (const c of CELLS) {
    if (c in b) {
      const v = normalizeCell(b[c]);
      if (v && typeof v === "object") return NextResponse.json({ error: `invalid ${c}` }, { status: 400 });
      patch[c] = v;
    }
  }
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });
  patch.updated_at = new Date().toISOString();

  const admin = createAdminClient();
  const { data, error } = await admin.from("plan_matrix_rows").update(patch).eq("id", rowId).select("*").maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data) return NextResponse.json({ error: "not_found" }, { status: 404 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "plan_matrix.update", detail: { id: rowId, fields: Object.keys(patch) } });
  return NextResponse.json({ ok: true, row: data });
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const rowId = parseInt(id, 10);
  if (!Number.isInteger(rowId)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  const admin = createAdminClient();
  const { error } = await admin.from("plan_matrix_rows").delete().eq("id", rowId);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "plan_matrix.delete", detail: { id: rowId } });
  return NextResponse.json({ ok: true });
}
