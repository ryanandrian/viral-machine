import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// Preview video buffer utk /review (Opsi C) — presigned URL S3 (Biznet, privat), TTL pendek.
// Ownership ditegakkan RLS: server client (anon + sesi user) hanya bisa SELECT content_inventory
// milik tenant sendiri (policy content_inventory_tenant_read). Tak ada s3_key bocor lintas-tenant.
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id wajib" }, { status: 400 });

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { data: item } = await supabase
    .from("content_inventory")
    .select("s3_key, status")
    .eq("id", id)
    .maybeSingle();
  if (!item || !item.s3_key) return NextResponse.json({ error: "not found" }, { status: 404 });

  const endpoint = process.env.S3_ENDPOINT;
  const accessKeyId = process.env.S3_ACCESS_KEY;
  const secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_BUCKET;
  if (!endpoint || !accessKeyId || !secretAccessKey || !bucket) {
    return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });
  }

  try {
    const s3 = new S3Client({
      endpoint,
      region: process.env.S3_REGION || "idn",
      credentials: { accessKeyId, secretAccessKey },
      forcePathStyle: true,
    });
    const url = await getSignedUrl(
      s3,
      new GetObjectCommand({ Bucket: bucket, Key: item.s3_key }),
      { expiresIn: 600 },
    );
    return NextResponse.json({ url });
  } catch (e) {
    return NextResponse.json({ error: `presign gagal: ${(e as Error).message}` }, { status: 500 });
  }
}
