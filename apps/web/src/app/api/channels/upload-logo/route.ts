import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// Upload logo brand channel → S3 (mesinviral-assets/brand-logo/{tenant}/{channel}.png) → URL ke channels.brand_logo.
// Pipeline (video_renderer._overlay_logo) ambil dari URL itu (sudah jalan). Aturan UKURAN platform (branding_config,
// admin DB): TOLAK bila dimensi > maks (default 220x220). Reuse pola route upload musik (@aws-sdk PutObject).
export const dynamic = "force-dynamic";

// Dimensi PNG dari header IHDR (sig 8B + len 4B + "IHDR" 4B → width@16, height@20, big-endian). null bila bukan PNG.
function pngDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 24) return null;
  if (buf.readUInt32BE(0) !== 0x89504e47) return null; // \x89 P N G
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const channelId = String(form.get("channel_id") || "").trim();

  if (!(file instanceof File)) return NextResponse.json({ error: "file (PNG) wajib" }, { status: 400 });
  if (!channelId) return NextResponse.json({ error: "channel_id wajib" }, { status: 400 });

  // Channel WAJIB milik tenant ini (RLS: select hanya channel milik user).
  const { data: ch } = await supabase.from("channels").select("id").eq("id", channelId).maybeSingle();
  if (!ch) return NextResponse.json({ error: "channel tak ditemukan / bukan milik Anda" }, { status: 404 });

  const isPng = file.type.includes("png") || file.name.toLowerCase().endsWith(".png");
  if (!isPng) return NextResponse.json({ error: "Logo harus berkas PNG (transparan)." }, { status: 400 });
  if (file.size > 5 * 1024 * 1024) return NextResponse.json({ error: "Ukuran file maksimal 5MB." }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  const dim = pngDimensions(body);
  if (!dim) return NextResponse.json({ error: "Berkas bukan PNG valid." }, { status: 400 });

  // Aturan ukuran platform (branding_config DB, id=1) — fallback 220x220. SAMA dgn yg dipakai renderer.
  const admin = createAdminClient();
  const { data: bc } = await admin.from("branding_config").select("logo_max_w_px,logo_max_h_px").eq("id", 1).maybeSingle();
  const maxW = Number((bc as { logo_max_w_px?: number } | null)?.logo_max_w_px) || 220;
  const maxH = Number((bc as { logo_max_h_px?: number } | null)?.logo_max_h_px) || 220;
  if (dim.w > maxW || dim.h > maxH) {
    return NextResponse.json({ error: `Logo terlalu besar (${dim.w}×${dim.h}px). Maksimal ${maxW}×${maxH}px — perkecil dulu.` }, { status: 400 });
  }

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const object_key = `brand-logo/${user.id}/${channelId}.png`;   // 1 objek per channel (timpa); URL ber-cache-bust di bawah
  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    // ACL public-read WAJIB: bucket privat; tanpa ini renderer download logo = 403 (bug laten, ketahuan saat uji blog-cover 2026-07-03).
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: object_key, Body: body, ContentType: "image/png", ACL: "public-read" }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  // ?v= → cache-bust (objek di-timpa di key sama; URL berubah tiap upload → renderer/cache ambil yg baru).
  const public_url = `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}?v=${Date.now()}`;
  return NextResponse.json({ ok: true, public_url, width: dim.w, height: dim.h });
}
