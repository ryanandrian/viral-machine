import { NextResponse } from "next/server";
import { requireAgent } from "@/lib/agent/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";

// [B21] F4 — "Hubungkan Telegram" AGEN: mekanisme 1-klik yang SAMA dgn tenant (ketok owner):
// POST → token deep-link t.me dari BE (satu otoritas token) · DELETE → putuskan (hapus chat_id).
export async function POST() {
  const g = await requireAgent(); if (g.error) return g.error;
  try {
    const r = await vault("/api/credentials/telegram/link", { agent_id: g.agent.id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}

export async function DELETE() {
  const g = await requireAgent(); if (g.error) return g.error;
  const a = createAdminClient();
  const { error } = await a.from("agents").update({ telegram_chat_id: null, updated_at: new Date().toISOString() }).eq("id", g.agent.id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
