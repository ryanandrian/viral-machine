import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { testChannelReadiness } from "@/lib/admin/test-readiness";

// "Cek kesiapan test" — kesiapan per-elemen channel test (config + kunci POOL valid; kunci sudah
// divalidasi NYATA saat disimpan via vault). TANPA YouTube: test niche tidak pernah publish.
export async function POST() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const r = await testChannelReadiness();
  const a = createAdminClient();
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.check_readiness", detail: { result: r.elems, ready: r.ready } });
  return NextResponse.json({ result: r.elems, ready: r.ready });
}
