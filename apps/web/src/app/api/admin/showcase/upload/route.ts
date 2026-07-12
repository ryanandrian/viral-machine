import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { imageDimensions, isMp4 } from "@/lib/media-sig";

// Upload media Showcase (ADMIN) → S3 folder khusus per jenis. kind:
//   screen → showcase-screens/  (PNG/JPG screenshot halaman tenant; min lebar 1000px agar tajam)
//   video  → showcase-videos/   (MP4 contoh konten hasil mesin, 9:16)
//   poster → showcase-posters/  (PNG/JPG thumbnail opsional utk video)
// Validasi dari header byte (tanpa lib gambar) — pola sama upload-cover blog. ACL public-read WAJIB (bucket privat).
export const dynamic = "force-dynamic";

const RULES: Record<string, { folder: string; image: boolean; minW: number; maxBytes: number }> = {
  screen: { folder: "showcase-screens", image: true, minW: 1000, maxBytes: 5 * 1024 * 1024 },
  poster: { folder: "showcase-posters", image: true, minW: 360, maxBytes: 3 * 1024 * 1024 },
  video: { folder: "showcase-videos", image: false, minW: 0, maxBytes: 80 * 1024 * 1024 },
  // Foto testimoni (migr 0154) — tampil bulat kecil; 200px cukup tajam
  testimonial: { folder: "testimonial-photos", image: true, minW: 200, maxBytes: 3 * 1024 * 1024 },
};

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const kind = String(form.get("kind") || "").trim();
  const rule = RULES[kind];
  if (!rule) return NextResponse.json({ error: "kind harus screen|video|poster|testimonial" }, { status: 400 });
  if (!(file instanceof File)) return NextResponse.json({ error: "file wajib" }, { status: 400 });
  if (file.size > rule.maxBytes) return NextResponse.json({ error: `Ukuran file maksimal ${Math.round(rule.maxBytes / 1048576)}MB.` }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  let ext: string, contentType: string;
  if (rule.image) {
    const dim = imageDimensions(body);
    if (!dim) return NextResponse.json({ error: "Format harus PNG atau JPG (berkas valid)." }, { status: 400 });
    if (dim.w < rule.minW) return NextResponse.json({ error: `Gambar terlalu kecil (${dim.w}×${dim.h}px) — minimal lebar ${rule.minW}px.` }, { status: 400 });
    ext = dim.ext; contentType = dim.contentType;
  } else {
    if (!isMp4(body)) return NextResponse.json({ error: "Format video harus MP4 (H.264)." }, { status: 400 });
    ext = "mp4"; contentType = "video/mp4";
  }

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const object_key = `${rule.folder}/${crypto.randomUUID()}.${ext}`;
  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    // ACL public-read WAJIB: bucket privat; tanpa ini GET publik = 403 (terverifikasi 2026-07-03).
    await s3.send(new PutObjectCommand({ Bucket: bucket, Key: object_key, Body: body, ContentType: contentType, ACL: "public-read" }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  const public_url = `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}`;
  return NextResponse.json({ ok: true, public_url });
}
