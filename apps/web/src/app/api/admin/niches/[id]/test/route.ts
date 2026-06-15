import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { ADMIN_TEST_TID } from "../../../test-lab/route";

// Admin "Test niche" — enqueue direct_job (admin_test) di channel internal admin-test, niche override.
// Butuh kredensial admin-test sudah diisi (Test Lab). Produksi private → progress live di D5.
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const a = createAdminClient();

  const { data: ch } = await a.from("channels").select("id").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  if (!ch) return NextResponse.json({ error: "channel admin-test belum ada" }, { status: 400 });

  // pastikan kredensial AI terisi (kalau kosong, produksi pasti gagal)
  const { data: cfg } = await a.from("tenant_configs").select("llm_api_key, visual_api_key").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  if (!cfg?.llm_api_key || !cfg?.visual_api_key) {
    return NextResponse.json({ error: "Kredensial admin-test belum lengkap — isi di Test Lab dulu." }, { status: 400 });
  }

  const { data: job, error } = await a.from("direct_jobs").insert({
    tenant_id: ADMIN_TEST_TID, channel_id: ch.id, job_type: "admin_test",
    niche: id, publish_privacy: "private", requested_by: g.user.id,
  }).select("id").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.test", detail: { niche_id: id, job: job.id } });
  return NextResponse.json({ ok: true, job: job.id });
}
