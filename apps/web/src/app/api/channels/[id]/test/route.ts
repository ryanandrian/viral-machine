import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { latestTestResult } from "@/lib/test-run";

// Test / Run & recover CHANNEL (Channel Setting) — produksi 1 video uji NYATA memakai config+kredensial
// channel ini (job_type "test" = upload PRIVAT ke YouTube, perilaku disetujui owner). Worker auto-recover:
// direct yang menghasilkan video → unpause channel. FE (TestNichePanel) menampilkan progres + hasil.
// Pola & readiness = mirror /api/niches/mine/test, di-key per-channel.

async function gate(channelId: string) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  // Kepemilikan: channel harus milik tenant ini (RLS tenant_id = auth.uid()).
  const { data: ch } = await supabase.from("channels").select("id").eq("id", channelId).maybeSingle();
  if (!ch) return { error: NextResponse.json({ error: "channel tak ditemukan / bukan milik Anda" }, { status: 404 }) };
  return { user, supabase, admin: createAdminClient() };
}

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const g = await gate(id); if (g.error) return g.error;
  // Gerbang kesiapan channel (RPC tenant-scoped yang dipakai halaman channel).
  const { data: rd } = await g.supabase.rpc("channel_readiness", { p_channel_id: id });
  const ready = (rd as { ready?: boolean; missing?: string[] } | null)?.ready;
  if (!ready) {
    const miss = ((rd as { missing?: string[] } | null)?.missing ?? []).join(" · ");
    return NextResponse.json({ error: `Channel belum siap produksi${miss ? ` — ${miss}` : ""}` }, { status: 400 });
  }
  const { data: job, error } = await g.admin.from("direct_jobs").insert({
    tenant_id: g.user.id, channel_id: id, job_type: "test", publish_privacy: "private", requested_by: g.user.id,
  }).select("id").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, job: job.id });
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const g = await gate(id); if (g.error) return g.error;
  return NextResponse.json({ test: await latestTestResult(g.user.id, "", "test", id) });
}
