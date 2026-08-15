import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { testChannelReadiness, ADMIN_TEST_TID } from "@/lib/admin/test-readiness";
import { presignAssetKey } from "@/lib/test-run";

// [B32] T11 — PRATINJAU 1 GAMBAR dari DNA niche. Dipakai DUA layar sekaligus:
// Niche Studio (tenant, niche miliknya) & Niche Library (admin, niche mana pun).
//
// KENAPA ADA (pertanyaan owner 2026-08-15 "apa pantas dijual?"): mencocokkan gaya visual sebuah niche
// hari ini menuntut VIDEO PENUH — ±4 menit, ±Rp 1.500 sekali coba. Pratinjau: ±25 detik, ±Rp 250 (terukur 15-Agu).
//
// ⚠️ Rute ini TIDAK memanggil vendor gambar sendiri dan TIDAK merakit prompt. Ia hanya mengantre
// pekerjaan; PEKERJA yang membuat gambarnya dengan perakit prompt PRODUKSI apa adanya. Merakit prompt
// di sini = kebenaran KEDUA yang suatu hari berbeda dari produksi — kelas cacat yang [B32] tutup.

async function tenantGate() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  return { user, admin: createAdminClient() };
}

export async function POST(req: Request) {
  const b = await req.json().catch(() => ({}));
  const nicheId = String(b.niche_id ?? "").trim();
  const asAdmin = Boolean(b.admin);
  if (!nicheId) return NextResponse.json({ error: "niche_id wajib" }, { status: 400 });

  let tenantId: string, admin: ReturnType<typeof createAdminClient>;
  if (asAdmin) {
    const g = await requireSuperAdmin();
    if (g.error) return g.error;
    tenantId = ADMIN_TEST_TID;
    admin = createAdminClient();
  } else {
    const g = await tenantGate(); if (g.error) return g.error;
    tenantId = g.user.id; admin = g.admin;
    // Tenant hanya boleh melihat pratinjau niche yang MEMANG tersedia baginya (miliknya atau publik aktif).
    const { data: n } = await admin.from("niches").select("niche_id, access_type, exclusive_to, is_active")
      .eq("niche_id", nicheId).maybeSingle();
    const boleh = n && (n.exclusive_to === tenantId || (!n.exclusive_to && n.is_active && n.access_type === "public"));
    if (!boleh) return NextResponse.json({ error: "niche tak tersedia untuk Anda" }, { status: 404 });
  }

  // Channel + kredensial yang dipakai = milik pemilik pratinjau sendiri (BYOK), sama seperti test niche.
  const r = await testChannelReadiness(tenantId);
  if (!r.channel_id) return NextResponse.json({ error: "Belum ada channel siap produksi." }, { status: 400 });
  if (!r.elems.visual.ok) return NextResponse.json({ error: `Generator visual belum siap — ${r.elems.visual.msg}` }, { status: 400 });

  const { data: job, error } = await admin.from("direct_jobs").insert({
    tenant_id: tenantId, channel_id: r.channel_id, job_type: "preview_image",
    niche: nicheId, publish_privacy: "private", requested_by: tenantId,
  }).select("id").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, job: job.id });
}

// Polling hasil: status + tautan berjangka (kunci S3 TIDAK pernah dikirim mentah ke layar).
export async function GET(req: Request) {
  const url = new URL(req.url);
  const jobId = url.searchParams.get("job");
  if (!jobId) return NextResponse.json({ error: "job wajib" }, { status: 400 });

  const asAdmin = url.searchParams.get("admin") === "1";
  let pemilik: string;
  if (asAdmin) {
    const g = await requireSuperAdmin(); if (g.error) return g.error;
    pemilik = ADMIN_TEST_TID;
  } else {
    const g = await tenantGate(); if (g.error) return g.error;
    pemilik = g.user.id;
  }
  const admin = createAdminClient();
  const { data: j } = await admin.from("direct_jobs")
    .select("status, error, result_key, tenant_id, job_type")
    .eq("id", jobId).maybeSingle();
  if (!j || j.job_type !== "preview_image" || j.tenant_id !== pemilik)
    return NextResponse.json({ error: "not found" }, { status: 404 });

  const url_gambar = j.result_key ? await presignAssetKey(j.result_key as string) : null;
  return NextResponse.json({ status: j.status, error: j.error, url: url_gambar });
}
