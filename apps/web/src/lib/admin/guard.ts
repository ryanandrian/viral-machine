import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Gate super-admin untuk SETIAP route-handler /api/admin/*. Baca sesi dari cookie (server client + RLS),
// cek app_metadata.role (di-set service_role, tak bisa dipalsukan tenant). Defense-in-depth selain
// proxy/middleware + route-group layout. Pakai di awal handler: const g = await requireSuperAdmin(); if (g.error) return g.error;
export async function requireSuperAdmin() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return { user: null, error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  }
  if (user.app_metadata?.role !== "super_admin") {
    return { user: null, error: NextResponse.json({ error: "forbidden" }, { status: 403 }) };
  }
  return { user, error: null as null };
}
