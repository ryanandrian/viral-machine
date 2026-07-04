import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { TEMPLATE_COPY_COLUMNS } from "@/lib/niche-dna";

// E2.3 Niches list (PHASE10 §2) — niches (semua) + derive video/tenant count + avg viral_score.
// (releases/niche_releases DIHAPUS 2026-07-04 — penjadwal rilis tanpa eksekutor, lihat page niches.)
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();

  const [{ data: niches, error }, { data: vids }, { data: tenants }] = await Promise.all([
    admin.from("niches").select("*").order("niche_id"),
    admin.from("videos").select("niche, viral_score"),
    admin.from("tenant_configs").select("niche, niche_pool"),
  ]);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const vCount = new Map<string, number>(); const vScore = new Map<string, number[]>();
  (vids ?? []).forEach((v) => {
    if (!v.niche) return;
    vCount.set(v.niche, (vCount.get(v.niche) ?? 0) + 1);
    if (v.viral_score != null) vScore.set(v.niche, [...(vScore.get(v.niche) ?? []), v.viral_score]);
  });
  const tCount = new Map<string, number>();
  (tenants ?? []).forEach((t) => {
    const set = new Set<string>([...(t.niche ? [t.niche] : []), ...((t.niche_pool as string[]) ?? [])]);
    set.forEach((n) => tCount.set(n, (tCount.get(n) ?? 0) + 1));
  });

  const rows = (niches ?? []).map((n) => {
    const scores = vScore.get(n.niche_id) ?? [];
    return {
      ...n,
      video_count: vCount.get(n.niche_id) ?? 0,
      tenant_count: tCount.get(n.niche_id) ?? 0,
      avg_viral: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null,
    };
  });
  return NextResponse.json({ niches: rows });
}

// New Niche — id+name+akses + WIZARD TEMPLATE (owner 2026-07-04): copy DNA "gaya" dari niche base
// pilihan (keywords/hashtags/contoh-shot TIDAK di-copy — spesifik topik niche baru).
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const niche_id = String(b.niche_id ?? "").trim();
  if (!/^[a-z0-9_]+$/.test(niche_id)) return NextResponse.json({ error: "niche_id invalid (a-z0-9_)" }, { status: 400 });
  const admin = createAdminClient();
  const seed: Record<string, unknown> = {};
  const tpl = String(b.template_niche_id ?? "").trim();
  if (tpl) {
    const { data: base } = await admin.from("niches").select("*").eq("niche_id", tpl).eq("is_base", true).maybeSingle();
    if (!base) return NextResponse.json({ error: "template tidak ditemukan / bukan niche dasar" }, { status: 400 });
    for (const c of TEMPLATE_COPY_COLUMNS) seed[c] = (base as Record<string, unknown>)[c];
  }
  const { data, error } = await admin.from("niches").insert({
    ...seed,
    niche_id, name: b.name ?? niche_id, is_base: !!b.is_base, is_active: b.is_active ?? true,
    access_type: b.access_type ?? "public", exclusive_to: b.exclusive_to ?? null, exclusive_until: b.exclusive_until ?? null,
    origin: "admin",
  }).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.create", detail: { niche_id } });
  return NextResponse.json({ ok: true, row: data });
}
