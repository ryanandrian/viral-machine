import { createClient } from "@supabase/supabase-js";

// SERVICE_ROLE client — BYPASS RLS. SERVER-ONLY: pakai HANYA di route-handler `/api/admin/*`
// SETELAH requireSuperAdmin() lolos. JANGAN pernah import dari komponen client / file ber-"use client"
// (akan membocorkan service_role ke browser). Key = SUPABASE_SERVICE_ROLE_KEY (tanpa NEXT_PUBLIC_).
// Pola data admin: PHASE10_ADMIN_WIRING.md §0.
export function createAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}
