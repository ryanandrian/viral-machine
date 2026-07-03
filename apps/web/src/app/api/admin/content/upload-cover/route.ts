import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { imageDimensions } from "@/lib/media-sig";

// Upload feature image (cover) artikel blog → S3 (mesinviral-assets/blog-cover/{slug|uuid}.{ext}) → URL ke
// blog_posts.cover. ADMIN-ONLY (requireSuperAdmin). Reuse pola upload-logo (@aws-sdk PutObject + validasi dimensi
// dari header byte, tanpa lib gambar). Kartu blog landing: grid 3 kolom @1200px → cover ±363×168 → retina 2×.
export const dynamic = "force-dynamic";

const MIN_W = 720;                 // ≥ lebar kartu retina 2× (±726px) — di bawah ini buram di landing
const MAX_BYTES = 5 * 1024 * 1024; // 5MB — cover di-download tiap pengunjung blog

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const slug = String(form.get("slug") || "").trim().toLowerCase().replace(/[^a-z0-9-]/g, "");
  if (!(file instanceof File)) return NextResponse.json({ error: "file gambar wajib" }, { status: 400 });
  if (file.size > MAX_BYTES) return NextResponse.json({ error: "Ukuran file maksimal 5MB." }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  const dim = imageDimensions(body);
  if (!dim) return NextResponse.json({ error: "Format harus PNG atau JPG (berkas valid)." }, { status: 400 });
  if (dim.w < MIN_W) {
    return NextResponse.json({ error: `Gambar terlalu kecil (${dim.w}×${dim.h}px). Minimal lebar ${MIN_W}px agar tajam di landing (disarankan ±760×352, rasio ~2,2:1).` }, { status: 400 });
  }

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const object_key = `blog-cover/${slug || crypto.randomUUID()}.${dim.ext}`; // folder khusus; 1 objek per artikel (timpa), URL ber-cache-bust
  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    // ACL public-read WAJIB: bucket privat; tanpa ini GET publik = 403 (terverifikasi 2026-07-03).
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: object_key, Body: body, ContentType: dim.contentType, ACL: "public-read" }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  const public_url = `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}?v=${Date.now()}`;
  return NextResponse.json({ ok: true, public_url, width: dim.w, height: dim.h });
}
