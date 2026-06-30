import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// F3-03 / F2-10 — Niche Studio tenant (gated). Tenant ber-entitlement BUAT/EDIT niche CUSTOM
// sendiri (access_type='private', exclusive_to=tenant_id). Tulis via service_role (niches RLS OFF)
// TAPI di-ENFORCE di sini: tenant_id dari SESI (bukan klien), selalu private+exclusive milik dia,
// gating PER-TIER config-driven (plan_limits.niche_studio — owner 2026-06-21, adjustable di Admin tanpa redeploy).

// Field DNA yang boleh tenant edit pada niche PRIVATE miliknya (BUKAN access_type/exclusive_to/is_base).
const EDITABLE = [
  "name", "keywords", "style", "target_emotion", "hook_templates", "default_hashtags", "is_active",
  "visual_style", "visual_fallbacks", "mood_priority", "narration_persona", "emotion_scoring_criteria",
  "section_timing", "image_quality_tags", "image_negative_prompt", "music_config", "youtube_category_id",
];

async function gate() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  const admin = createAdminClient();
  const { data: tc } = await admin.from("tenant_configs").select("plan_type").eq("tenant_id", user.id).maybeSingle();
  const plan = (tc as { plan_type?: string } | null)?.plan_type ?? "starter";
  const { data: pl } = await admin.from("plan_limits").select("niche_studio").eq("plan_type", plan).maybeSingle();
  if (!(pl as { niche_studio?: boolean } | null)?.niche_studio)
    return { error: NextResponse.json({ error: "Niche Studio tidak tersedia di paket Anda — upgrade untuk membuat niche kustom." }, { status: 403 }) };
  return { user, admin };
}

export async function GET() {
  const g = await gate(); if (g.error) return g.error;
  // HANYA niche bikinan-sendiri di Studio (origin='studio'). Niche PESANAN custom (origin='request')
  // dikelola tim & tampil di Pustaka Niche — TAK boleh diedit tenant (cegah campur-aduk/rusak deliverable).
  const { data, error } = await g.admin.from("niches").select("*").eq("exclusive_to", g.user.id).eq("origin", "studio").order("niche_id");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ niches: data ?? [] });
}

export async function POST(req: Request) {
  const g = await gate(); if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const niche_id = String(b.niche_id ?? "").trim();
  if (!/^[a-z0-9_]+$/.test(niche_id)) return NextResponse.json({ error: "niche_id invalid (a-z0-9_)" }, { status: 400 });
  const { data, error } = await g.admin.from("niches").insert({
    niche_id, name: b.name || niche_id, is_active: true, is_base: false,
    access_type: "private", exclusive_to: g.user.id, origin: "studio",   // ENFORCED (tak dari klien)
  }).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, row: data });
}

export async function PATCH(req: Request) {
  const g = await gate(); if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const niche_id = String(b.niche_id ?? "").trim();
  if (!niche_id) return NextResponse.json({ error: "niche_id wajib" }, { status: 400 });
  const patch: Record<string, unknown> = {};
  for (const k of EDITABLE) if (k in b) patch[k] = b[k];
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_editable_fields" }, { status: 400 });
  // ENFORCE: hanya niche PRIVATE milik tenant ini.
  const { data, error } = await g.admin.from("niches").update(patch)
    .eq("niche_id", niche_id).eq("exclusive_to", g.user.id).eq("access_type", "private").eq("origin", "studio").select("*");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data || data.length === 0) return NextResponse.json({ error: "niche tak ditemukan / bukan milik Anda" }, { status: 404 });
  return NextResponse.json({ ok: true, row: data[0] });
}
