import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { vault } from "@/lib/youtube";

// [B21] Operasi UANG & rekening program agen — proxy ke mv-webhook /api/partner/op
// (X-Internal-Secret) agar hitungan tetap SATU otoritas di partner.py. Gated super-admin.
const OPS = new Set(["payouts_build", "payout_approve", "payout_paid", "bank_set", "bank_reveal"]);

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const body = await req.json().catch(() => ({}));
  if (!OPS.has(body?.op)) return NextResponse.json({ error: "op tidak dikenal" }, { status: 400 });
  try {
    const r = await vault("/api/partner/op", body);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: r.status === 400 ? 400 : 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
