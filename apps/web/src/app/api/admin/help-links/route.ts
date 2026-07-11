import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// [D1] Tombol Help kontekstual SOFTCODE (migr 0153) — kelola pemetaan lokasi→artikel.
// GET: pemetaan + daftar artikel published (bahan dropdown). PATCH: upsert 1 lokasi
// (server MEMVALIDASI slug published — lapisan kedua setelah dropdown). DELETE: reset ke bawaan.

export async function GET() {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const a = createAdminClient();
  const [{ data: links, error: e1 }, { data: docs, error: e2 }] = await Promise.all([
    a.from("help_links").select("location_key,article_slug,updated_at"),
    a.from("docs_articles").select("slug,title,title_en,grp,status").order("sort_order"),
  ]);
  if (e1 || e2) return NextResponse.json({ error: (e1 ?? e2)!.message }, { status: 500 });
  return NextResponse.json({ links: links ?? [], docs: docs ?? [] });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { location_key, article_slug } = await req.json().catch(() => ({}));
  if (!location_key || !article_slug) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const a = createAdminClient();
  // Validasi server: tujuan WAJIB artikel published (dropdown FE = lapisan pertama).
  const { data: doc } = await a.from("docs_articles").select("slug").eq("slug", article_slug).eq("status", "published").maybeSingle();
  if (!doc) return NextResponse.json({ error: "article_not_published" }, { status: 400 });
  const { error } = await a.from("help_links")
    .upsert({ location_key, article_slug, updated_at: new Date().toISOString() }, { onConflict: "location_key" });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "help_links.set", detail: { location_key, article_slug } });
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { location_key } = await req.json().catch(() => ({}));
  if (!location_key) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const a = createAdminClient();
  const { error } = await a.from("help_links").delete().eq("location_key", location_key);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "help_links.reset", detail: { location_key } });
  return NextResponse.json({ ok: true });
}
