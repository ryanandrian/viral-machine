import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { presignAssetKey } from "@/lib/test-run";

// Preview track music_library (login apa pun: tenant di editor DNA / admin di Catalog) —
// presigned URL S3 (bucket aset PRIVAT; URL publik = 403). TTL pendek, aset tak bocor permanen.
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id wajib" }, { status: 400 });
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { data: t } = await createAdminClient().from("music_library").select("object_key").eq("id", id).eq("is_active", true).maybeSingle();
  if (!t?.object_key) return NextResponse.json({ error: "track tak ditemukan" }, { status: 404 });
  const url = await presignAssetKey(t.object_key as string);
  if (!url) return NextResponse.json({ error: "presign gagal" }, { status: 500 });
  return NextResponse.json({ url });
}
