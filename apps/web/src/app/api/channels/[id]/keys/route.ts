import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Kunci AI per-CHANNEL per-elemen (llm/tts/visual) → channels.<element>_key_enc (Fernet via vault Python).
// AUTHED: tenant_id dari sesi server (BUKAN klien). Master key tak pernah ke Next.
// Owner 2026-06-24: kunci tak di-mask (boleh copy-paste) → GET kembalikan plaintext ke pemilik channel.
const ELEMENTS = ["llm", "tts", "visual"];

// GET → {keys:{llm,tts,visual}} (decrypt, utk ditampilkan/copy-paste oleh tenant pemilik)
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { id } = await params;
  try {
    const r = await vault("/api/channels/keys/get", { tenant_id: user.id, channel_id: id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "baca gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}

// POST {element, key} → simpan kunci 1 elemen (key kosong = hapus kunci)
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const element = String(body.element || "").trim();
  if (!ELEMENTS.includes(element)) return NextResponse.json({ error: "element invalid" }, { status: 400 });
  try {
    const r = await vault("/api/channels/key", {
      tenant_id: user.id, channel_id: id, element, key: String(body.key ?? ""),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "simpan gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
