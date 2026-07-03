import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

// Info perusahaan utk halaman PUBLIK — hanya field yang aman dipublikasi (whitelist; company_profile
// berisi juga NPWP/telegram admin yang TIDAK boleh bocor → jangan pernah select *).
export const dynamic = "force-dynamic";

export async function GET() {
  const a = createAdminClient();
  const { data } = await a.from("company_profile").select("website,email").limit(1).maybeSingle();
  const cp = data as { website?: string; email?: string } | null;
  return NextResponse.json({ website: cp?.website ?? null, email: cp?.email ?? null });
}
