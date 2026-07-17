import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { AgentShell } from "@/components/agent-shell";

// [B21] F2 — gate PORTAL AGEN (defense-in-depth selain middleware; cermin admin/(panel)/layout).
// role 'agent' + WAJIB tertaut agents.user_id. /agent/login & /agent/setup di LUAR group ini.
export default async function AgentPortalLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/agent/login");
  if (user.app_metadata?.role !== "agent") redirect("/dashboard");
  const admin = createAdminClient();
  const { data: rows } = await admin.from("agents").select("company_name,status").eq("user_id", user.id).limit(1);
  const agent = rows?.[0];
  if (!agent) redirect("/agent/login?error=profil-agen-tidak-ditemukan");
  return <AgentShell company={agent.company_name} status={agent.status}>{children}</AgentShell>;
}
