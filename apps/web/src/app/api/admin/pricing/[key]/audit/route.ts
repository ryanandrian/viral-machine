import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Riwayat perubahan satu pricing key (PHASE10 §2 — tab Audit Log + rollback).
export async function GET(_req: Request, { params }: { params: Promise<{ key: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { key } = await params;
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("pricing_audit").select("id, old_value, new_value, changed_by, changed_at")
    .eq("key", key).order("changed_at", { ascending: false }).limit(50);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ audit: data ?? [] });
}
