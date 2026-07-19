import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { ResellerShell } from "@/components/reseller-shell";

// [B21] F3 — gate PORTAL RESELLER (cermin layout portal agen F2).
export default async function ResellerPortalLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/reseller/login");
  // [B21 MGM §9a.5] reseller murni (role) ATAU tenant ber-tautan (reseller_linked — satu login)
  if (user.app_metadata?.role !== "reseller" && user.app_metadata?.reseller_linked !== true) redirect("/dashboard");
  const admin = createAdminClient();
  const { data: rows } = await admin.from("resellers").select("name,status,agent_id").eq("user_id", user.id).limit(1);
  const rs = rows?.[0];
  if (!rs) redirect("/reseller/login?error=profil-reseller-tidak-ditemukan");
  const { data: ag } = await admin.from("agents").select("company_name").eq("id", rs.agent_id).limit(1);
  return <ResellerShell name={rs.name} agent={ag?.[0]?.company_name ?? ""} status={rs.status}>{children}</ResellerShell>;
}
