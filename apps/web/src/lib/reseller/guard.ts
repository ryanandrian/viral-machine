import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] F3 — gate PORTAL RESELLER (cermin requireAgent). role='reseller' (app_metadata,
// di-set service_role saat agen menyetujui) + WAJIB tertaut resellers.user_id.
// Data selalu difilter reseller.id dari sesi → isolasi antar-reseller ditegakkan server.

export type ResellerRowDb = {
  id: string; agent_id: string; name: string; email: string | null; status: string;
  commission_type: string; commission_value: number;
  bank_name: string | null; bank_holder: string | null; bank_account_enc: string | null;
  user_id: string | null; created_at: string;
};

export async function requireReseller(): Promise<
  { error: NextResponse; user?: undefined; reseller?: undefined }
  | { error?: undefined; user: { id: string }; reseller: ResellerRowDb }
> {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  // [B21 MGM §9a.5, ketok 2026-07-19] reseller murni (role) ATAU tenant ber-tautan reseller
  // (penanda reseller_linked — satu login dua wilayah). Keduanya tetap wajib punya baris
  // `resellers.user_id` di bawah (profil = sumber kebenaran; penanda saja tidak cukup).
  if (user.app_metadata?.role !== "reseller" && user.app_metadata?.reseller_linked !== true) {
    return { error: NextResponse.json({ error: "forbidden" }, { status: 403 }) };
  }
  const admin = createAdminClient();
  const { data: rows } = await admin.from("resellers").select("*").eq("user_id", user.id).limit(1);
  const reseller = rows?.[0] as ResellerRowDb | undefined;
  if (!reseller) return { error: NextResponse.json({ error: "reseller_profile_missing" }, { status: 403 }) };
  return { user: { id: user.id }, reseller };
}
