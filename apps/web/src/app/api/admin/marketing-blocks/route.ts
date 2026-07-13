import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Blok narasi marketing (Tahap 4 finalisasi_tier_plan) — mis. ilustrasi biaya per video di landing.
// GET daftar (editor di /admin/pricing). Tulis = PATCH per-key (route [key]).
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin.from("marketing_blocks").select("*").order("sort_order");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ blocks: data ?? [] });
}
