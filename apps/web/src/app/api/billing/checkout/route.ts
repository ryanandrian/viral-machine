import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Checkout LANGGANAN: verifikasi sesi tenant → mv-webhook (snap_create_transaction, service-role) →
// {redirect_url}. Frontend redirect user ke halaman bayar Midtrans. Aktivasi final = via webhook.
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { plan_type } = await req.json().catch(() => ({}));
  if (!plan_type || typeof plan_type !== "string") {
    return NextResponse.json({ error: "plan_type wajib" }, { status: 400 });
  }
  const res = await vault("/api/billing/checkout", { tenant_id: user.id, plan_type, email: user.email });
  const j = await res.json().catch(() => ({}));
  return NextResponse.json(j, { status: res.status });
}
