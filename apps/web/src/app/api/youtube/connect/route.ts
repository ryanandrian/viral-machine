import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Mulai sambung YouTube — OAuth PLATFORM. Tenant TIDAK kirim client creds; platform pakai app-nya sendiri
// (GOOGLE_CLIENT_ID/SECRET di .env, dipegang vault Python). Route AUTHED (sesi → tenant_id) → teruskan ke vault.
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { ret, account_id, label } = await req.json().catch(() => ({}));

  try {
    const r = await vault("/api/youtube/oauth/init", {
      tenant_id: user.id,
      account_id: account_id || null,   // POOL: null = koneksi baru; isi = re-connect akun existing
      label: typeof label === "string" ? label : "",
      ret: typeof ret === "string" && ret.startsWith("/") ? ret : "/integrations",  // anti open-redirect
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "init gagal" }, { status: 502 });
    return NextResponse.json({ authorize_url: j.authorize_url });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
