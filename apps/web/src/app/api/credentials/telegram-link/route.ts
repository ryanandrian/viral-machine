import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { vault } from "@/lib/youtube";

// [TG-LINK] Hubungkan Telegram 1-klik (ketok owner 2026-07-16): terbitkan deep-link t.me ber-token
// utk tenant SESI INI. Pola persis /api/credentials/telegram (authed → proxy vault internal-secret);
// seluruh logika token & nama bot hidup di BE Python (satu sumber, nol HMAC lintas-bahasa).

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try {
    const r = await vault("/api/credentials/telegram/link", { tenant_id: user.id });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
