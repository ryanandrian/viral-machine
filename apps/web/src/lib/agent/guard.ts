import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] F2 — gate PORTAL AGEN utk API route (cermin requireSuperAdmin, defense-in-depth selain
// middleware). Konvensi: app_metadata.role='agent' (di-set service_role saat undangan — tak bisa
// dipalsukan) + WAJIB tertaut baris agents.user_id. Data selalu difilter agent.id dari sesi
// (bukan input klien) → isolasi antar-agen ditegakkan server.

export type AgentRowDb = {
  id: string; company_name: string; pic_name: string | null; pic_email: string; status: string;
  commission_type: string; commission_value: number; tax_status: string;
  bank_name: string | null; bank_holder: string | null; bank_account_enc: string | null;
  join_code: string | null; user_id: string | null; telegram_chat_id: string | null; created_at: string;
};

export async function requireAgent(): Promise<
  { error: NextResponse; user?: undefined; agent?: undefined }
  | { error?: undefined; user: { id: string }; agent: AgentRowDb }
> {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  if (user.app_metadata?.role !== "agent") {
    return { error: NextResponse.json({ error: "forbidden" }, { status: 403 }) };
  }
  const admin = createAdminClient();
  const { data: rows } = await admin.from("agents").select("*").eq("user_id", user.id).limit(1);
  const agent = rows?.[0] as AgentRowDb | undefined;
  if (!agent) return { error: NextResponse.json({ error: "agent_profile_missing" }, { status: 403 }) };
  return { user: { id: user.id }, agent };
}
