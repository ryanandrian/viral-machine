import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// Telegram validate-early: kirim pesan TES via bot platform → bukti chat_id benar + bot di-Start.
// Hanya simpan chat_id bila tes sukses. AUTHED: tenant_id dari sesi server.

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const b = await req.json().catch(() => ({}));
  const chat_id = String(b.chat_id || "").trim();
  if (!chat_id) return NextResponse.json({ error: "chat_id wajib" }, { status: 400 });
  try {
    const r = await vault("/api/credentials/telegram/test", { tenant_id: user.id, chat_id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
