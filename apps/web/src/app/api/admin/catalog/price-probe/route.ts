import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { vault } from "@/lib/youtube";

// Probe harga 1 model (butir-4): deteksi model_id/prefix salah saat admin simpan model.
// Super-admin only → vault Python jalankan sync_prices utk 1 model → {priced:boolean}.
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { model_key } = await req.json().catch(() => ({}));
  if (!model_key) return NextResponse.json({ ok: false, error: "model_key wajib" }, { status: 400 });
  try {
    const r = await vault("/api/admin/catalog/price-probe", { model_key });
    const j = await r.json().catch(() => ({ ok: false }));
    return NextResponse.json(j, { status: r.ok ? 200 : 400 });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message }, { status: 500 });
  }
}
