import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Putuskan sambungan YouTube (hapus token; OAuth app tenant tetap → reconnect satu-klik). AUTHED.
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { account_id } = await req.json().catch(() => ({}));
  try {
    const r = await vault("/api/youtube/oauth/disconnect", { tenant_id: user.id, account_id: account_id || null });
    if (!r.ok) return NextResponse.json({ error: "disconnect gagal" }, { status: 502 });
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
