import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Kunci AI per penyedia (POOL tenant_ai_accounts) — validate-early via vault Python (Fernet).
// AUTHED: tenant_id dari sesi server. Arsitektur: CHANNEL_LOCK_ACTIVATION_PLAN.md.

// GET → daftar status kunci AI per penyedia (TIDAK kembalikan nilai kunci)
export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try {
    const r = await vault("/api/credentials/ai/list", { tenant_id: user.id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}

// POST {provider_key, key, label?} → simpan + UJI; balas {status: valid|invalid|unchecked}
export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const b = await req.json().catch(() => ({}));
  const provider_key = String(b.provider_key || "").trim();
  const key = String(b.key || "").trim();
  if (!provider_key) return NextResponse.json({ error: "provider_key wajib" }, { status: 400 });
  if (!key) return NextResponse.json({ error: "key wajib" }, { status: 400 });
  try {
    const r = await vault("/api/credentials/ai", { tenant_id: user.id, provider_key, key, label: String(b.label || "") });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "simpan gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
