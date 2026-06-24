import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Mulai sambung YouTube BYO-CC. Tenant kirim OAuth app MEREKA (client_id+secret). Route ini AUTHED
// (sesi Supabase → tenant_id) lalu teruskan ke vault Python (yang enkripsi secret + bangun consent URL).
// Secret TIDAK pernah disimpan/di-log di sisi Next — hanya numpang-lewat sekali ke server pemegang-kunci.
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { client_id, client_secret, ret, account_id, label } = await req.json().catch(() => ({}));
  if (!client_id?.trim() || !client_secret?.trim())
    return NextResponse.json({ error: "client_id & client_secret wajib" }, { status: 400 });

  try {
    const r = await vault("/api/youtube/oauth/init", {
      tenant_id: user.id,
      client_id: client_id.trim(),
      client_secret: client_secret.trim(),
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
