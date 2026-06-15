import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// CMS admin (Blog/Docs/Demo). service_role: list (incl draft) + create/update/delete. Whitelist tabel+kolom.
const T: Record<string, { cols: string[]; order: string }> = {
  blog_posts: { cols: ["slug", "title", "title_en", "excerpt", "excerpt_en", "body", "body_en", "category", "cover", "status", "published_at", "sort_order"], order: "published_at" },
  docs_articles: { cols: ["slug", "grp", "grp_en", "title", "title_en", "body", "body_en", "status", "sort_order"], order: "sort_order" },
  demo_tours: { cols: ["label", "label_en", "href", "heading", "heading_en", "caption", "caption_en", "bullets", "bullets_en", "is_active", "sort_order"], order: "sort_order" },
};

export async function GET(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const table = new URL(req.url).searchParams.get("table") ?? "";
  if (!T[table]) return NextResponse.json({ error: "table_not_allowed" }, { status: 400 });
  const a = createAdminClient();
  const { data, error } = await a.from(table).select("*").order(T[table].order, { ascending: table === "blog_posts" ? false : true, nullsFirst: false });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ rows: data ?? [] });
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { table, row } = await req.json().catch(() => ({}));
  const def = T[table]; if (!def) return NextResponse.json({ error: "table_not_allowed" }, { status: 400 });
  const clean: Record<string, unknown> = {};
  for (const c of def.cols) if (c in (row ?? {})) clean[c] = row[c];
  const a = createAdminClient();
  const { data, error } = await a.from(table).insert(clean).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `content.create.${table}`, detail: { slug: row?.slug ?? row?.href } });
  return NextResponse.json({ ok: true, row: data });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { table, id, patch } = await req.json().catch(() => ({}));
  const def = T[table]; if (!def || !id) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const clean: Record<string, unknown> = { updated_at: new Date().toISOString() };
  for (const c of def.cols) if (c in (patch ?? {})) clean[c] = patch[c];
  const a = createAdminClient();
  const { data, error } = await a.from(table).update(clean).eq("id", id).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `content.update.${table}`, detail: { id } });
  return NextResponse.json({ ok: true, row: data });
}

export async function DELETE(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { table, id } = await req.json().catch(() => ({}));
  if (!T[table] || !id) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const a = createAdminClient();
  const { error } = await a.from(table).delete().eq("id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `content.delete.${table}`, detail: { id } });
  return NextResponse.json({ ok: true });
}
