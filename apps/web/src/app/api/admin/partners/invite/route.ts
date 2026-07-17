import { NextResponse, type NextRequest } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { sendMail } from "@/lib/email/smtp";
import { renderAgentInviteEmail } from "@/lib/email/templates";

// [B21] F2 — buat/kirim akses login portal agen (ketok owner: 1 login per agen via agents.user_id;
// TANPA Google — email+password saja). Alur: user auth ber-role 'agent' (app_metadata, service_role)
// → tautkan agents.user_id → email undangan ber-brand (link recovery → set password → /agent).
// Satu email satu peran (SPEC §5g.3): email milik tenant/admin DITOLAK jelas.

function originOf(req: NextRequest): string {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "https";
  return host ? `${proto}://${host}` : "https://mesinviral.com";
}

export async function POST(req: NextRequest) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { agent_id } = await req.json().catch(() => ({}));
  if (!agent_id) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const a = createAdminClient();
  const { data: rows } = await a.from("agents").select("id,company_name,pic_email,user_id,status").eq("id", agent_id).limit(1);
  const agent = rows?.[0];
  if (!agent) return NextResponse.json({ error: "agen tidak ditemukan" }, { status: 404 });
  const email = String(agent.pic_email || "").trim().toLowerCase();
  if (!email) return NextResponse.json({ error: "email PIC kosong — isi dulu di form agen" }, { status: 400 });

  let uid = agent.user_id as string | null;
  if (!uid) {
    // Buat user baru; email sudah terpakai → periksa perannya (1 email = 1 peran, §5g.3)
    const { data: created, error: ce } = await a.auth.admin.createUser({ email, email_confirm: true });
    if (ce) {
      const m = (ce.message || "").toLowerCase();
      if (!(m.includes("registered") || m.includes("already"))) {
        return NextResponse.json({ error: ce.message }, { status: 500 });
      }
      // user sudah ada → cari via generateLink recovery (mengembalikan user tanpa membuat baru)
      const { data: gl, error: ge } = await a.auth.admin.generateLink({ type: "recovery", email });
      if (ge || !gl?.user) return NextResponse.json({ error: ge?.message || "user lookup gagal" }, { status: 500 });
      const exist = gl.user;
      const role = (exist.app_metadata as Record<string, unknown> | null)?.role;
      if (role && role !== "agent") {
        return NextResponse.json({ error: "email ini sudah dipakai akun lain (bukan agen) — gunakan email PIC yang berbeda" }, { status: 400 });
      }
      const { data: tc } = await a.from("tenant_configs").select("tenant_id").eq("tenant_id", exist.id).limit(1);
      if (tc && tc.length > 0) {
        return NextResponse.json({ error: "email ini sudah terdaftar sebagai TENANT — satu email satu peran; gunakan email PIC yang berbeda" }, { status: 400 });
      }
      uid = exist.id;
    } else {
      uid = created.user.id;
    }
    const { error: re } = await a.auth.admin.updateUserById(uid, { app_metadata: { role: "agent" } });
    if (re) return NextResponse.json({ error: `gagal set peran: ${re.message}` }, { status: 500 });
    const { error: le } = await a.from("agents").update({ user_id: uid, updated_at: new Date().toISOString() }).eq("id", agent.id);
    if (le) return NextResponse.json({ error: `gagal tautkan user: ${le.message}` }, { status: 500 });
  }

  // Tautan set-password (recovery) → /auth/callback → /agent/setup (ganti password) → /agent
  const { data: link, error: lke } = await a.auth.admin.generateLink({ type: "recovery", email });
  const props = link?.properties as { hashed_token?: string; verification_type?: string } | undefined;
  if (lke || !props?.hashed_token) {
    return NextResponse.json({ error: lke?.message || "gagal membuat tautan undangan" }, { status: 500 });
  }
  const next = encodeURIComponent("/agent/setup");
  const action = `${originOf(req)}/auth/callback?token_hash=${encodeURIComponent(props.hashed_token)}&type=${props.verification_type}&next=${next}`;
  const { subject, html, text } = renderAgentInviteEmail("id", action, agent.company_name);
  try {
    await sendMail(email, subject, html, text);
  } catch (e) {
    console.error("[partner.invite] SMTP gagal:", e);
    return NextResponse.json({ error: "akun portal SIAP, tapi email undangan gagal terkirim — klik lagi untuk kirim ulang" }, { status: 500 });
  }
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "partner.agent.invite", detail: { agent_id: agent.id, email } });
  return NextResponse.json({ ok: true, linked_user: uid });
}
