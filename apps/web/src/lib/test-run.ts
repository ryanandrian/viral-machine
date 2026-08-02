import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// Hasil TEST niche tanpa-publish — SATU logika utk route ADMIN (Pustaka Niche) & TENANT (Niche Studio).
// job terakhir + run + progres stepper NYATA (parse "STEP n/T | label" dari pipeline_run_logs) +
// presigned URL video (bucket buffer privat). Dipanggil server-side SETELAH pemanggil memverifikasi hak.

export type TestProgress = { step: number; total: number; label: string; last_log: string; last_log_at: string };
export type TestResult = {
  id: string; status: string; error: string | null; run_id: string | null;
  created_at: string; started_at: string | null; completed_at: string | null;
  run: Record<string, unknown> | null; video_url: string | null; progress: TestProgress | null;
} | null;

export async function presignBufferKey(key: string): Promise<string | null> {
  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY, bucket = process.env.S3_BUCKET;
  if (!endpoint || !accessKeyId || !secretAccessKey || !bucket) return null;
  try {
    const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
    return await getSignedUrl(s3, new GetObjectCommand({ Bucket: bucket, Key: key }), { expiresIn: 600 });
  } catch { return null; }
}

// Presign objek ASET (bucket mesinviral-assets — musik/logo). Beda bucket dari buffer video.
export async function presignAssetKey(key: string): Promise<string | null> {
  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return null;
  try {
    const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
    return await getSignedUrl(s3, new GetObjectCommand({ Bucket: bucket, Key: key }), { expiresIn: 600 });
  } catch { return null; }
}

// key by niche (Niche Studio/admin) ATAU channel (Channel Setting) — channelId truthy → key channel.
export async function latestTestResult(tenantId: string, nicheId: string, jobType: string, channelId?: string | null): Promise<TestResult> {
  const a = createAdminClient();
  let q = a.from("direct_jobs")
    .select("id, status, error, run_id, created_at, started_at, completed_at")
    .eq("tenant_id", tenantId).eq("job_type", jobType);
  q = channelId ? q.eq("channel_id", channelId) : q.eq("niche", nicheId);
  const { data: job } = await q.order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (!job) return null;

  let progress: TestProgress | null = null;
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
      .select("status, qc_passed, viral_score, topic, elapsed_seconds, error_message, run_metadata, youtube_video_id, youtube_url")
      .eq("run_id", job.run_id).maybeSingle();
    run = pr ?? null;
    let s3key = (pr?.run_metadata as { video_s3?: string } | null)?.video_s3;
    if (!s3key) {
      const { data: inv } = await a.from("content_inventory").select("s3_key")
        .eq("tenant_id", tenantId).like("s3_key", `%${job.run_id}%`).limit(1).maybeSingle();
      s3key = (inv?.s3_key as string) ?? undefined;
    }
    // [B24 §10a pintu 6] Tautan unduh video uji = pintu keluar nilai yang paling senyap: tak perlu
    // menekan apa pun, cukup membuka halaman, dan tautannya diterbitkan ulang setiap kali. Tanpa
    // gerbang ini, tenant yang langganannya sudah mati tetap bisa memanen video uji terakhirnya
    // berkali-kali. Dipakai gerbang PRODUKSI (bukan gerbang uji): ini "melihat hasil produksi",
    // sehingga masa tenggang (grace) TETAP boleh — sama seperti pintu unduh stok gudang.
    if (s3key) {
      const { data: bolehLihat, error: gErr } = await a.rpc("tenant_produce_allowed", { p_tenant_id: tenantId });
      if (gErr) console.error("[test-run] gerbang produksi gagal:", gErr.message);
      // Gagal jujur: saat kita tak bisa memastikan, tautan TIDAK diterbitkan.
      if (bolehLihat === true) video_url = await presignBufferKey(s3key);
    }
  }
  return { ...job, run, video_url, progress };
}
