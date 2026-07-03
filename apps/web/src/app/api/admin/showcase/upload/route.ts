import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

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
};

function pngDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 24 || buf.readUInt32BE(0) !== 0x89504e47) return null;
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}
function jpegDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 4 || buf[0] !== 0xff || buf[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const marker = buf[i + 1];
    if (marker === 0xc0 || marker === 0xc1 || marker === 0xc2) return { w: buf.readUInt16BE(i + 7), h: buf.readUInt16BE(i + 5) };
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue; }
    i += 2 + buf.readUInt16BE(i + 2);
  }
  return null;
}
// MP4: box pertama umumnya "ftyp" di offset 4 ("....ftyp").
function isMp4(buf: Buffer): boolean {
  return buf.length > 12 && buf.toString("latin1", 4, 8) === "ftyp";
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const kind = String(form.get("kind") || "").trim();
  const rule = RULES[kind];
  if (!rule) return NextResponse.json({ error: "kind harus screen|video|poster" }, { status: 400 });
  if (!(file instanceof File)) return NextResponse.json({ error: "file wajib" }, { status: 400 });
  if (file.size > rule.maxBytes) return NextResponse.json({ error: `Ukuran file maksimal ${Math.round(rule.maxBytes / 1048576)}MB.` }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  let ext: string, contentType: string;
  if (rule.image) {
    const isPng = body.length > 4 && body.readUInt32BE(0) === 0x89504e47;
    const isJpeg = body.length > 2 && body[0] === 0xff && body[1] === 0xd8;
    if (!isPng && !isJpeg) return NextResponse.json({ error: "Format harus PNG atau JPG." }, { status: 400 });
    const dim = isPng ? pngDimensions(body) : jpegDimensions(body);
    if (!dim) return NextResponse.json({ error: "Berkas gambar tidak valid." }, { status: 400 });
    if (dim.w < rule.minW) return NextResponse.json({ error: `Gambar terlalu kecil (${dim.w}×${dim.h}px) — minimal lebar ${rule.minW}px.` }, { status: 400 });
    ext = isPng ? "png" : "jpg"; contentType = isPng ? "image/png" : "image/jpeg";
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
