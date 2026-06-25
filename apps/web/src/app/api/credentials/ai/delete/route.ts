import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Hapus 1 kunci AI dari pool. AUTHED (tenant_id dari sesi). Vault hapus baris tenant_ai_accounts;
// channels.*_account_id yg menunjuknya → NULL otomatis (FK on delete set null).
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { account_id } = await req.json().catch(() => ({}));
  if (!account_id) return NextResponse.json({ error: "account_id wajib" }, { status: 400 });
  try {
    const r = await vault("/api/credentials/ai/delete", { tenant_id: user.id, account_id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "hapus gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
