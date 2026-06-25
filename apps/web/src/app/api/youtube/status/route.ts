import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Status sambungan YouTube tenant (connected/has_client/channel_id). AUTHED. Baca via vault Python
// (pool tenant_youtube_accounts dibaca via vault service_role). Jika vault tak terjangkau
// (mis. dev tanpa worker) → balas 'degraded' supaya FE tampil jujur, bukan crash.
export async function GET(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  // POOL: kembalikan daftar koneksi YouTube tenant (degraded bila vault tak terjangkau).
  const fallback = { ok: false, accounts: [], degraded: true };
  try {
    const r = await vault("/api/youtube/oauth/status", { tenant_id: user.id });
    if (!r.ok) return NextResponse.json(fallback);
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json(fallback);
  }
}
