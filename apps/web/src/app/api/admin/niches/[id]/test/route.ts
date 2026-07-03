import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { ADMIN_TEST_TID, testChannelReadiness } from "@/lib/admin/test-readiness";

// Admin "Test niche" (dirombak 2026-07-04, keputusan owner):
// - POST: cek kesiapan channel test (POOL/katalog — BUKAN kolom kredensial lama yang sudah di-drop 0090)
//   → enqueue direct_job job_type='admin_test'. Worker memproduksi TANPA publish (video → S3 buffer).
// - GET: hasil test TERAKHIR utk niche ini (status/QC/skor + presigned URL video utk ditonton di drawer).
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
  const a = createAdminClient();

  const { data: job } = await a.from("direct_jobs")
    .select("id, status, error, run_id, created_at, started_at, completed_at")
    .eq("tenant_id", ADMIN_TEST_TID).eq("job_type", "admin_test").eq("niche", id)
    .order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (!job) return NextResponse.json({ test: null });

  // Progres NYATA saat berjalan (stepper ala CI, masukan owner 2026-07-04): parse "STEP n/T | label"
  // dari pipeline_run_logs (denyut mesin sungguhan, sumber sama dgn live-tail Runs) + log terakhir.
  let progress: { step: number; total: number; label: string; last_log: string; last_log_at: string } | null = null;
  if (job.run_id && ["pending", "producing"].includes(job.status)) {
    const [{ data: stepRow }, { data: lastRow }] = await Promise.all([
      a.from("pipeline_run_logs").select("message").eq("run_id", job.run_id).like("message", "STEP %").order("created_at", { ascending: false }).limit(1).maybeSingle(),
      a.from("pipeline_run_logs").select("message, created_at").eq("run_id", job.run_id).order("created_at", { ascending: false }).limit(1).maybeSingle(),
    ]);
    const m = /^STEP (\d+)(?:\/(\d+))?(?: DONE)? \|\s*(.*)$/.exec((stepRow?.message as string) ?? "");
    progress = {
      step: m ? Number(m[1]) : 0, total: m?.[2] ? Number(m[2]) : 7,
      label: m?.[3] ?? "", last_log: ((lastRow?.message as string) ?? "").slice(0, 120),
      last_log_at: (lastRow?.created_at as string) ?? "",
    };
  }

  let run: Record<string, unknown> | null = null;
  let video_url: string | null = null;
  if (job.run_id) {
    const { data: pr } = await a.from("production_runs")
      .select("status, qc_passed, viral_score, topic, elapsed_seconds, error_message, run_metadata")
      .eq("run_id", job.run_id).maybeSingle();
    run = pr ?? null;
    const s3key = (pr?.run_metadata as { video_s3?: string } | null)?.video_s3;
    if (s3key) {
      const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY, bucket = process.env.S3_BUCKET;
      if (endpoint && accessKeyId && secretAccessKey && bucket) {
        try {
          const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
          video_url = await getSignedUrl(s3, new GetObjectCommand({ Bucket: bucket, Key: s3key }), { expiresIn: 600 });
        } catch { /* presign gagal → tampil tanpa video, jujur */ }
      }
    }
  }
  return NextResponse.json({ test: { ...job, run, video_url, progress } });
}
