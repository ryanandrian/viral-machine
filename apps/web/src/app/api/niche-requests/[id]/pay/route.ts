import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Bayar ADD-ON custom-niche: verifikasi sesi tenant → mv-webhook (snap_create_niche_addon) →
// {redirect_url}. Kepemilikan + status awaiting_payment divalidasi di sisi server (service-role).
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { id } = await params;
  const res = await vault("/api/billing/niche-checkout", { tenant_id: user.id, request_id: id, email: user.email });
  const j = await res.json().catch(() => ({}));
  return NextResponse.json(j, { status: res.status });
}
