import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { ADMIN_TEST_TID, testChannelReadiness } from "@/lib/admin/test-readiness";
import { latestTestResult } from "@/lib/test-run";

// Admin "Test niche" — POST: cek kesiapan channel admin_test → enqueue direct_job 'admin_test'
// (worker produksi TANPA publish; video status='test' di buffer). GET: hasil terakhir + progres +
// presigned video (logika bersama lib/test-run — sama dgn tenant Niche Studio).
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const a = createAdminClient();

  const r = await testChannelReadiness();
  if (!r.channel_id) return NextResponse.json({ error: "channel admin-test belum ada" }, { status: 400 });
  if (!r.ready) {
    const miss = Object.entries(r.elems).filter(([, e]) => !e.ok).map(([k, e]) => `${k}: ${e.msg}`).join(" · ");
    return NextResponse.json({ error: `Channel test belum siap — ${miss}` }, { status: 400 });
  }

  const { data: job, error } = await a.from("direct_jobs").insert({
    tenant_id: ADMIN_TEST_TID, channel_id: r.channel_id, job_type: "admin_test",
    niche: id, publish_privacy: "private", requested_by: g.user.id,
  }).select("id").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.test", detail: { niche_id: id, job: job.id } });
  return NextResponse.json({ ok: true, job: job.id });
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  return NextResponse.json({ test: await latestTestResult(ADMIN_TEST_TID, id, "admin_test") });
}
