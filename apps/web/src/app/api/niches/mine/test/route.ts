import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { testChannelReadiness } from "@/lib/admin/test-readiness";
import { latestTestResult } from "@/lib/test-run";
import { gateCode, testGate } from "@/lib/test-gate";

// NICHE_DNA F5 — Test niche TENANT (Niche Studio, Business+): produksi 1 video uji NYATA memakai
// KREDENSIAL + CHANNEL tenant sendiri (biaya AI = kunci mereka/BYOK), TANPA publish ke YouTube
// (worker: job_type 'test_nopub' → inventory status='test', tak diklaim publisher, TTL ±3 hari).
// Enforce: hanya niche STUDIO milik tenant (origin='studio', exclusive_to=tenant).

async function gate() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  const admin = createAdminClient();
  const { data: tc } = await admin.from("tenant_configs").select("plan_type").eq("tenant_id", user.id).maybeSingle();
  const plan = (tc as { plan_type?: string } | null)?.plan_type ?? "starter";
  const { data: pl } = await admin.from("plan_limits").select("niche_studio").eq("plan_type", plan).maybeSingle();
  if (!(pl as { niche_studio?: boolean } | null)?.niche_studio)
    return { error: NextResponse.json({ error: "Niche Studio tidak tersedia di paket Anda." }, { status: 403 }) };
  return { user, admin };
}

async function ownNiche(admin: ReturnType<typeof createAdminClient>, userId: string, nicheId: string) {
  const { data } = await admin.from("niches").select("niche_id")
    .eq("niche_id", nicheId).eq("exclusive_to", userId).eq("origin", "studio").maybeSingle();
  return !!data;
}

export async function POST(req: Request) {
  const g = await gate(); if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const nicheId = String(b.niche_id ?? "").trim();
  if (!nicheId) return NextResponse.json({ error: "niche_id wajib" }, { status: 400 });
  if (!(await ownNiche(g.admin, g.user.id, nicheId))) return NextResponse.json({ error: "niche tak ditemukan / bukan milik Anda" }, { status: 404 });

  // [B24 §10c LAPIS 2] Gerbang UJI — insert di bawah memakai kunci layanan yang MELEWATI aturan akses
  // tabel. Video uji niche tidak diunggah ke YouTube, tapi disajikan lewat tautan unduh berjangka —
  // tetap video jadi yang bisa dipakai tenant. Kode dwibahasa (§3.5); `error` diisi utk nol regresi.
  const tgn = await testGate(g.user.id);
  if (!tgn.allowed) {
    return NextResponse.json({ error: gateCode(tgn), error_code: gateCode(tgn) }, { status: 403 });
  }

  const r = await testChannelReadiness(g.user.id);
  if (!r.channel_id) return NextResponse.json({ error: "Anda belum punya channel — buat channel dulu." }, { status: 400 });
  if (!r.ready) {
    const miss = Object.entries(r.elems).filter(([, e]) => !e.ok).map(([, e]) => e.msg).join(" · ");
    return NextResponse.json({ error: `Channel Anda belum siap produksi — ${miss}` }, { status: 400 });
  }

  const { data: job, error } = await g.admin.from("direct_jobs").insert({
    tenant_id: g.user.id, channel_id: r.channel_id, job_type: "test_nopub",
    niche: nicheId, publish_privacy: "private", requested_by: g.user.id,
  }).select("id").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, job: job.id });
}

export async function GET(req: Request) {
  const g = await gate(); if (g.error) return g.error;
  const nicheId = new URL(req.url).searchParams.get("niche_id") ?? "";
  if (!nicheId) return NextResponse.json({ error: "niche_id wajib" }, { status: 400 });
  if (!(await ownNiche(g.admin, g.user.id, nicheId))) return NextResponse.json({ error: "niche tak ditemukan / bukan milik Anda" }, { status: 404 });
  // `gate` ikut dikirim → layar menampilkan tombol TERKUNCI sebelum ditekan (K6).
  const [test, tg] = await Promise.all([latestTestResult(g.user.id, nicheId, "test_nopub"), testGate(g.user.id)]);
  return NextResponse.json({ test, gate: { allowed: tg.allowed, code: tg.allowed ? null : gateCode(tg) } });
}
