import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { vault } from "@/lib/youtube";

// Uji-NYATA satu model katalog (butir-1: aktif = terbukti jalan). Super-admin only → proxy ke
// vault Python (webhook_app) yang menjalankan adapter produksi dgn kunci uji (tak disimpan).
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { model_key, key } = await req.json().catch(() => ({}));
  if (!model_key) return NextResponse.json({ ok: false, error: "model_key wajib" }, { status: 400 });
  try {
    const r = await vault("/api/admin/catalog/test-model", { model_key, key: key || "" });
    const j = await r.json().catch(() => ({ ok: false, error: "respons vault tidak valid" }));
    return NextResponse.json(j, { status: r.ok ? 200 : 400 });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message }, { status: 500 });
  }
}
