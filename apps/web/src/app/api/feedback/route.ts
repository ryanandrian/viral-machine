import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";

export const runtime = "nodejs";

// Simpan masukan (PUBLIK — penerima email trial belum tentu login). Write-only via service_role
// (bypass RLS; tak ada kebocoran data). Alasan churn terstruktur + saran bebas.
const REASONS = ["price", "features", "results", "not_ready", "other"];

export async function POST(req: Request) {
  const b = await req.json().catch(() => ({}));
  const reason = REASONS.includes(b?.reason) ? b.reason : "other";
  const message = (b?.message ?? "").toString().slice(0, 2000).trim() || null;
  const email = (b?.email ?? "").toString().slice(0, 200).trim() || null;
  const tenant_id = (b?.ref ?? "").toString().slice(0, 64).trim() || null;
  const source = (b?.source ?? "feedback_page").toString().slice(0, 40);
  if (!message && !b?.reason) return NextResponse.json({ error: "kosong" }, { status: 400 });

  const admin = createAdminClient();
  const { error } = await admin.from("feedback_submissions").insert({ tenant_id, reason, message, email, source });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  // Kabari admin via Telegram (webhook_app pegang token bot + chat_id) — fail-soft, jangan blokir submit.
  try {
    await vault("/api/feedback/notify-admin", { reason, source, tenant_id, email, message });
  } catch { /* fail-soft */ }
  return NextResponse.json({ ok: true });
}
