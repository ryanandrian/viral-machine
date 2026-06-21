import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// F2-09 — Tambah AKUN API ke vault (tenant_api_accounts) TERENKRIPSI (Fernet) via vault Python.
// AUTHED (tenant_id dari sesi server, BUKAN klien). Master key tak pernah ke Next.

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const component = String(body.component || "").trim();
  const key = String(body.key || "").trim();
  if (!["llm", "tts", "image", "video"].includes(component)) return NextResponse.json({ error: "component invalid" }, { status: 400 });
  if (!key) return NextResponse.json({ error: "key wajib" }, { status: 400 });

  try {
    const r = await vault("/api/accounts/set", {
      tenant_id: user.id, component, key,
      label: String(body.label || "").trim(), provider: String(body.provider || "").trim() || null,
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "simpan gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
