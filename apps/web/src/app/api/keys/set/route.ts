import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Simpan API key AI tenant TERENKRIPSI (Fernet) via vault Python — master key tak pernah ke Next.
// AUTHED (sesi Supabase → tenant_id dari server, BUKAN dari klien). Whitelist field; billing tak tersentuh.
const ALLOWED = ["llm_api_key", "visual_api_key", "tts_api_key", "youtube_api_key", "llm_library", "tts_provider"];

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const fwd: Record<string, unknown> = { tenant_id: user.id };
  for (const k of ALLOWED) if (body[k] != null && String(body[k]).trim() !== "") fwd[k] = body[k];

  try {
    const r = await vault("/api/keys/set", fwd);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "simpan gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
