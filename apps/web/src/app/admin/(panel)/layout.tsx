import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AdminShell } from "@/components/admin-shell";

// Gate SUPER-ADMIN (defense-in-depth — selain proxy/middleware). Konvensi: app_metadata.role='super_admin'
// ([[decisions_auth_rbac]]) — di-set service_role, TAK bisa dipalsukan tenant (bukan user_metadata).
// /admin/login berada di luar group ini → tidak ke-gate (jalur masuk admin).
// Catatan: data admin lintas-tenant (E1/E5/E2.3) = bypass-RLS via server-route service_role (PHASE9 §1.5).
export default async function AdminPanelLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/admin/login");
  if (user.app_metadata?.role !== "super_admin") redirect("/dashboard");

  return <AdminShell>{children}</AdminShell>;
}
