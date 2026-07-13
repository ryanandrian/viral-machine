import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// PATCH blok narasi marketing (Tahap 4): title_id/en ≤160, lines = array ≤8 baris {id,en} ≤400 char
// (baris ilustrasi bisa panjang). Validasi keras di titik input; audit ke admin_audit.
export async function PATCH(req: Request, { params }: { params: Promise<{ key: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { key } = await params;
  const body = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of ["title_id", "title_en"]) {
    if (k in body) {
      const s = String(body[k] ?? "").trim();
      if (s.length > 160) return NextResponse.json({ error: `invalid ${k}` }, { status: 400 });
      patch[k] = s || null;
    }
  }
  if ("lines" in body) {
    const ls = body.lines;
    if (!Array.isArray(ls) || ls.length > 8) return NextResponse.json({ error: "invalid_lines" }, { status: 400 });
    const clean: { id: string; en: string }[] = [];
    for (const l of ls) {
      const idTxt = String((l as { id?: unknown })?.id ?? "").trim();
      const enTxt = String((l as { en?: unknown })?.en ?? "").trim() || idTxt;
      if (!idTxt || idTxt.length > 400 || enTxt.length > 400) return NextResponse.json({ error: "invalid_lines" }, { status: 400 });
      clean.push({ id: idTxt, en: enTxt });
    }
    patch.lines = clean;
  }
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });
  patch.updated_at = new Date().toISOString();

  const admin = createAdminClient();
  const { data, error } = await admin.from("marketing_blocks").update(patch).eq("key", key).select("*").maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data) return NextResponse.json({ error: "not_found" }, { status: 404 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "marketing_block.update", detail: { key, fields: Object.keys(patch) } });
  return NextResponse.json({ ok: true, row: data });
}
