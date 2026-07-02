import { NextResponse, type NextRequest } from "next/server";
import { vault } from "@/lib/youtube";

// Reaktivasi 1-klik dari email (LIFECYCLE B9). PUBLIK — token HMAC = auth (tenant belum tentu login).
// Delegasi ke mv-webhook (verify_state + aksi): trial_expired+tuas → perpanjang trial gratis; lain → checkout.
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { token } = await req.json().catch(() => ({}));
  if (!token || typeof token !== "string") {
    return NextResponse.json({ error: "token wajib" }, { status: 400 });
  }
  const res = await vault("/api/lifecycle/reactivate", { token });
  const j = await res.json().catch(() => ({}));
  return NextResponse.json(j, { status: res.status });
}
