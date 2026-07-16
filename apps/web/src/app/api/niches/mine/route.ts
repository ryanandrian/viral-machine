import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { validateDnaPatch, TEMPLATE_COPY_COLUMNS } from "@/lib/niche-dna";

// F3-03 / F2-10 — Niche Studio tenant (gated). Tenant ber-entitlement BUAT/EDIT niche CUSTOM
// sendiri (access_type='private', exclusive_to=tenant_id). Tulis via service_role (niches RLS OFF)
// TAPI di-ENFORCE di sini: tenant_id dari SESI (bukan klien), selalu private+exclusive milik dia,
// gating PER-TIER config-driven (plan_limits.niche_studio — owner 2026-06-21, adjustable di Admin tanpa redeploy).

// Field DNA yang boleh tenant edit pada niche PRIVATE miliknya (BUKAN access_type/exclusive_to/is_base).
const EDITABLE = [
  "name", "keywords", "style", "target_emotion", "default_hashtags", "is_active",
  "description", "description_en",
  "visual_style", "visual_fallbacks", "mood_priority", "narration_persona", "voice_expression", "emotion_scoring_criteria",
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
  const [{ data, error }, { data: templates }] = await Promise.all([
    g.admin.from("niches").select("*").eq("exclusive_to", g.user.id).eq("origin", "studio").order("niche_id"),
    // Template wizard: niche DASAR publik (copy DNA "gaya" saat buat niche baru — owner 2026-07-04).
    g.admin.from("niches").select("niche_id, name").eq("is_base", true).eq("access_type", "public").eq("is_active", true).order("niche_id"),
  ]);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ niches: data ?? [], templates: templates ?? [] });
}

export async function POST(req: Request) {
  const g = await gate(); if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const niche_id = String(b.niche_id ?? "").trim();
  if (!/^[a-z0-9_]+$/.test(niche_id)) return NextResponse.json({ error: "niche_id invalid (a-z0-9_)" }, { status: 400 });

  // WIZARD TEMPLATE (owner 2026-07-04): niche baru TIDAK lahir kosong — copy DNA dari niche base
  // publik pilihan user (kolom "gaya"; keywords/hashtags/contoh-shot TIDAK di-copy: spesifik topik).
  const seed: Record<string, unknown> = {};
  const tpl = String(b.template_niche_id ?? "").trim();
  if (tpl) {
    const { data: base } = await g.admin.from("niches").select("*").eq("niche_id", tpl).eq("is_base", true).eq("access_type", "public").maybeSingle();
    if (!base) return NextResponse.json({ error: "template tidak ditemukan / bukan niche dasar publik" }, { status: 400 });
    for (const c of TEMPLATE_COPY_COLUMNS) seed[c] = (base as Record<string, unknown>)[c];
  }
  const { data, error } = await g.admin.from("niches").insert({
    ...seed,
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
  // Validasi skema DNA — TOLAK dengan pesan per-field (pengganti pola lama silent-skip JSON rusak).
  const errs = validateDnaPatch(patch);
  if (Object.keys(errs).length) return NextResponse.json({ error: "dna_invalid", fields: errs }, { status: 400 });
  // ENFORCE: hanya niche PRIVATE milik tenant ini.
  const { data, error } = await g.admin.from("niches").update(patch)
    .eq("niche_id", niche_id).eq("exclusive_to", g.user.id).eq("access_type", "private").eq("origin", "studio").select("*");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data || data.length === 0) return NextResponse.json({ error: "niche tak ditemukan / bukan milik Anda" }, { status: 404 });
  return NextResponse.json({ ok: true, row: data[0] });
}
