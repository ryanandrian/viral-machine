import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

// Info perusahaan utk halaman PUBLIK — hanya field yang aman dipublikasi (whitelist; company_profile
// berisi juga NPWP/telegram admin yang TIDAK boleh bocor → jangan pernah select *).
export const dynamic = "force-dynamic";

export async function GET() {
  const a = createAdminClient();
  // legal_name masuk whitelist (owner 2026-07-13): dipakai © footer marketing + panel auth —
  // akses anon LANGSUNG ke tabel ditutup migr 0159 (endpoint ini = satu-satunya pintu publik).
  const { data } = await a.from("company_profile").select("website,email,legal_name").limit(1).maybeSingle();
  const cp = data as { website?: string; email?: string; legal_name?: string } | null;
  return NextResponse.json({ website: cp?.website ?? null, email: cp?.email ?? null, legal_name: cp?.legal_name ?? null });
}
