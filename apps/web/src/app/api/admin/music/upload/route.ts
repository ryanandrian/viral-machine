import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// M2 — Upload musik (admin): file mp3 + metadata → S3 (kunci OPAK mesinviral-assets/music/{uuid}.mp3, §10.G)
// + insert music_library (object_key; decouple storage↔taksonomi → tak ada kelas-bug double-prefix).
// Aset = S3 (aturan owner). Durasi dikirim FE (client-side <audio>.duration) → tak butuh ffprobe di web-node.
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const name = String(form.get("name") || "").trim();
  const niche = String(form.get("niche") || "").trim();
  const mood = String(form.get("mood") || "").trim();
  const bpmRaw = form.get("bpm"); const durRaw = form.get("duration_s");
  const bpm = bpmRaw && !isNaN(Number(bpmRaw)) ? Math.round(Number(bpmRaw)) : null;
  const duration_s = durRaw && !isNaN(Number(durRaw)) ? Math.round(Number(durRaw)) : null;

  if (!(file instanceof File)) return NextResponse.json({ error: "file (mp3) wajib" }, { status: 400 });
  if (!name || !niche || !mood) return NextResponse.json({ error: "name, niche, mood wajib" }, { status: 400 });
  const isMp3 = file.type.includes("mpeg") || file.type.includes("mp3") || file.name.toLowerCase().endsWith(".mp3");
  if (!isMp3) return NextResponse.json({ error: "harus berkas .mp3" }, { status: 400 });
  if (file.size > 25 * 1024 * 1024) return NextResponse.json({ error: "maksimal 25MB" }, { status: 400 });

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const id = crypto.randomUUID();
  const object_key = `music/${id}.mp3`;                               // kunci OPAK (§10.G) — decouple storage↔taksonomi
  const body = Buffer.from(await file.arrayBuffer());

  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: object_key, Body: body, ContentType: "audio/mpeg" }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  const a = createAdminClient();
  const { data, error } = await a.from("music_library").insert({
    id, name, niche, mood, object_key, duration_s, bpm, source: "upload", is_active: true,
  }).select("*").single();
  if (error) return NextResponse.json({ error: `DB insert gagal: ${error.message}` }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "music.upload", detail: { name, niche, mood, object_key } });
  return NextResponse.json({ ok: true, row: data, public_url: `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}` });
}
