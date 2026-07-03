import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// Upload feature image (cover) artikel blog → S3 (mesinviral-assets/blog-cover/{slug|uuid}.{ext}) → URL ke
// blog_posts.cover. ADMIN-ONLY (requireSuperAdmin). Reuse pola upload-logo (@aws-sdk PutObject + validasi dimensi
// dari header byte, tanpa lib gambar). Kartu blog landing: grid 3 kolom @1200px → cover ±363×168 → retina 2×.
export const dynamic = "force-dynamic";

const MIN_W = 720;                 // ≥ lebar kartu retina 2× (±726px) — di bawah ini buram di landing
const MAX_BYTES = 5 * 1024 * 1024; // 5MB — cover di-download tiap pengunjung blog

// Dimensi PNG dari header IHDR (sig 8B + len 4B + "IHDR" 4B → width@16, height@20, big-endian).
function pngDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 24 || buf.readUInt32BE(0) !== 0x89504e47) return null;
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

// Dimensi JPEG: scan marker sampai SOF0/1/2 (0xC0/C1/C2) → height@+5, width@+7 (big-endian).
function jpegDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 4 || buf[0] !== 0xff || buf[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const marker = buf[i + 1];
    if (marker === 0xc0 || marker === 0xc1 || marker === 0xc2) {
      return { w: buf.readUInt16BE(i + 7), h: buf.readUInt16BE(i + 5) };
    }
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue; }
    i += 2 + buf.readUInt16BE(i + 2);
  }
  return null;
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const slug = String(form.get("slug") || "").trim().toLowerCase().replace(/[^a-z0-9-]/g, "");
  if (!(file instanceof File)) return NextResponse.json({ error: "file gambar wajib" }, { status: 400 });
  if (file.size > MAX_BYTES) return NextResponse.json({ error: "Ukuran file maksimal 5MB." }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  const isPng = body.length > 4 && body.readUInt32BE(0) === 0x89504e47;
  const isJpeg = body.length > 2 && body[0] === 0xff && body[1] === 0xd8;
  if (!isPng && !isJpeg) return NextResponse.json({ error: "Format harus PNG atau JPG." }, { status: 400 });

  const dim = isPng ? pngDimensions(body) : jpegDimensions(body);
  if (!dim) return NextResponse.json({ error: "Berkas gambar tidak valid / dimensi tak terbaca." }, { status: 400 });
  if (dim.w < MIN_W) {
    return NextResponse.json({ error: `Gambar terlalu kecil (${dim.w}×${dim.h}px). Minimal lebar ${MIN_W}px agar tajam di landing (disarankan ±760×352, rasio ~2,2:1).` }, { status: 400 });
  }

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const ext = isPng ? "png" : "jpg";
  const object_key = `blog-cover/${slug || crypto.randomUUID()}.${ext}`; // folder khusus; 1 objek per artikel (timpa), URL ber-cache-bust
  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    // ACL public-read WAJIB: bucket privat; tanpa ini GET publik = 403 (terverifikasi 2026-07-03).
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: object_key, Body: body, ContentType: isPng ? "image/png" : "image/jpeg", ACL: "public-read" }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  const public_url = `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}?v=${Date.now()}`;
  return NextResponse.json({ ok: true, public_url, width: dim.w, height: dim.h });
}
