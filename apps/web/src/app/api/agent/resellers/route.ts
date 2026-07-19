import { NextResponse, type NextRequest } from "next/server";
import { requireAgent } from "@/lib/agent/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";
import { sendMail } from "@/lib/email/smtp";
import { renderResellerInviteEmail, renderResellerLinkedEmail } from "@/lib/email/templates";

// [B21] F3 — kelola reseller oleh AGEN (SPEC §1c/5f): tautan rekrut · antrean setujui/tolak ·
// rate reseller (Rp/%) DIATUR AGEN · kode (beku setelah dipakai §5g.2) · kinerja per periode.
// Semua difilter paksa agent.id dari sesi. Persetujuan = lahirnya login reseller (ketok F3)
// via pola undangan yang sama dgn agen (email tenant/admin/agen DITOLAK — 1 email 1 peran).

const CODE_RE = /^[A-Z0-9]{4,12}$/;
function randCode(prefix: string): string {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; // tanpa I/L/O/0/1 (anti salah-ketik)
  let s = "";
  for (let i = 0; i < 6; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return (prefix + s).slice(0, 12);
}
function originOf(req: NextRequest): string {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "https";
  return host ? `${proto}://${host}` : "https://mesinviral.com";
}

export async function GET(req: NextRequest) {
  const g = await requireAgent(); if (g.error) return g.error;
  const a = createAdminClient();
  const period = new URL(req.url).searchParams.get("period") || "";
  const periodMonth = /^\d{4}-\d{2}$/.test(period) ? `${period}-01` : null;
  const [{ data: rs }, { data: codes }, { data: att }] = await Promise.all([
    a.from("resellers").select("id,name,email,phone,status,commission_type,commission_value,bank_name,bank_holder,bank_account_enc,created_at").eq("agent_id", g.agent.id).order("created_at"),
    a.from("partner_codes").select("code,reseller_id,active,used_count").eq("agent_id", g.agent.id).eq("owner_kind", "reseller"),
    a.from("tenant_attribution").select("reseller_id").eq("agent_id", g.agent.id).not("reseller_id", "is", null),
  ]);
  let breakdown: Record<string, { total_idr: number; n_payment: number }> = {};
  let breakdownOk = false; // [AUDIT T-3] hitung gagal ≠ nol — UI wajib tampilkan "—", bukan Rp 0 palsu
  if (periodMonth) {
    try {
      const r = await vault("/api/partner/op", { op: "reseller_breakdown", agent_id: g.agent.id, period_month: periodMonth });
      const j = await r.json().catch(() => ({}));
      if (r.ok) {
        breakdown = Object.fromEntries((j.rows ?? []).map((x: { reseller_id: string; total_idr: number; n_payment: number }) => [x.reseller_id, x]));
        breakdownOk = true;
      }
    } catch { /* breakdownOk tetap false → UI beri tanda jelas */ }
  }
  const nTen: Record<string, number> = {}; (att ?? []).forEach((r) => { if (r.reseller_id) nTen[r.reseller_id] = (nTen[r.reseller_id] ?? 0) + 1; });
  const codeOf: Record<string, { code: string; active: boolean; used_count: number }> = {};
  (codes ?? []).forEach((c) => { if (c.reseller_id) codeOf[c.reseller_id] = c; });
  return NextResponse.json({
    join_code: g.agent.join_code,
    breakdown_ok: breakdownOk || !periodMonth,
    resellers: (rs ?? []).map((r) => ({
      id: r.id, name: r.name, email: r.email, phone: r.phone, status: r.status,
      commission_type: r.commission_type, commission_value: r.commission_value,
      bank_name: r.bank_name, bank_holder: r.bank_holder, bank_account_set: Boolean(r.bank_account_enc),
      code: codeOf[r.id]?.code ?? null, code_used: codeOf[r.id]?.used_count ?? 0,
      tenants: nTen[r.id] ?? 0, period_total_idr: breakdown[r.id]?.total_idr ?? 0,
      period_n_payment: breakdown[r.id]?.n_payment ?? 0,
    })),
  });
}

export async function POST(req: NextRequest) {
  const g = await requireAgent(); if (g.error) return g.error;
  const a = createAdminClient();
  const b = await req.json().catch(() => ({}));
  const action = b.action as string;

  if (action === "join_code") {
    // buat/ganti tautan rekrut (bukan kode atribusi — boleh diganti; tautan lama otomatis mati)
    for (let i = 0; i < 5; i++) {
      const jc = randCode("JN");
      const { error } = await a.from("agents").update({ join_code: jc, updated_at: new Date().toISOString() }).eq("id", g.agent.id);
      if (!error) return NextResponse.json({ ok: true, join_code: jc });
      // unique collision (langka) → coba kode lain
    }
    return NextResponse.json({ error: "gagal membuat tautan — coba lagi" }, { status: 500 });
  }

  const rid = String(b.reseller_id ?? "");
  const { data: rrows } = await a.from("resellers").select("*").eq("id", rid).eq("agent_id", g.agent.id).limit(1);
  const rs = rrows?.[0];
  if (!rs) return NextResponse.json({ error: "reseller tidak ditemukan" }, { status: 404 });

  if (action === "reject") {
    if (rs.status !== "pending") return NextResponse.json({ error: "hanya calon pending yang bisa ditolak" }, { status: 400 });
    await a.from("resellers").update({ status: "rejected", updated_at: new Date().toISOString() }).eq("id", rs.id);
    return NextResponse.json({ ok: true });
  }

  if (action === "rate") {
    const ct = b.commission_type;
    const cv = Number(b.commission_value);
    if (!["flat_idr", "percent"].includes(ct) || Number.isNaN(cv) || cv < 0) {
      return NextResponse.json({ error: "rate tidak valid" }, { status: 400 });
    }
    // snapshot per-baris (SPEC §3.6): berlaku utk pembayaran BERIKUTNYA, baris lama tak berubah
    await a.from("resellers").update({ commission_type: ct, commission_value: cv, updated_at: new Date().toISOString() }).eq("id", rs.id);
    return NextResponse.json({ ok: true });
  }

  if (action === "toggle") {
    const to = rs.status === "active" ? "suspended" : rs.status === "suspended" ? "active" : null;
    if (!to) return NextResponse.json({ error: "hanya reseller aktif/suspended" }, { status: 400 });
    await a.from("resellers").update({ status: to, updated_at: new Date().toISOString() }).eq("id", rs.id);
    await a.from("partner_codes").update({ active: to === "active" }).eq("reseller_id", rs.id); // cascade kode (§5g.7)
    return NextResponse.json({ ok: true, status: to });
  }

  if (action === "code") {
    const nc = String(b.code ?? "").trim().toUpperCase();
    if (!CODE_RE.test(nc)) return NextResponse.json({ error: "kode wajib 4-12 huruf besar/angka" }, { status: 400 });
    const { data: cur } = await a.from("partner_codes").select("code,used_count").eq("reseller_id", rs.id).limit(1);
    const old = cur?.[0];
    if (!old) return NextResponse.json({ error: "reseller belum punya kode (belum disetujui)" }, { status: 400 });
    if (old.code === nc) return NextResponse.json({ ok: true });
    if ((old.used_count ?? 0) > 0) return NextResponse.json({ error: "kode sudah pernah dipakai mendaftar — BEKU (jejak atribusi)" }, { status: 400 });
    const { error: ie } = await a.from("partner_codes").insert({ code: nc, owner_kind: "reseller", agent_id: g.agent.id, reseller_id: rs.id });
    if (ie) return NextResponse.json({ error: ie.message.includes("duplicate") ? "kode sudah dipakai" : ie.message }, { status: 400 });
    // [AUDIT T-2] cermin fix admin: delete gagal → rollback kode baru (anti dua-kode senyap)
    const { error: de } = await a.from("partner_codes").delete().eq("code", old.code);
    if (de) {
      await a.from("partner_codes").delete().eq("code", nc);
      return NextResponse.json({ error: "kode lama tidak bisa dilepas (sudah dipakai atribusi) — kode BEKU" }, { status: 400 });
    }
    return NextResponse.json({ ok: true, code: nc });
  }

  if (action === "approve") {
    const email = String(rs.email || "").trim().toLowerCase();
    if (!email) return NextResponse.json({ error: "email calon kosong" }, { status: 400 });
    if (rs.status === "active" && rs.user_id) {
      // sudah aktif → approve ulang = KIRIM ULANG (tanpa menyentuh kode/peran).
      // [MGM §9a.5] tenant tertaut = email "portal aktif" (BUKAN link set-password — link recovery
      // akan mereset password akun TENANT-nya, salah pesan & berbahaya).
      const { data: tcr } = await a.from("tenant_configs").select("tenant_id").eq("tenant_id", rs.user_id).limit(1);
      let m2: { subject: string; html: string; text: string };
      if (tcr && tcr.length > 0) {
        m2 = renderResellerLinkedEmail("id", `${originOf(req)}/reseller`, g.agent.company_name);
      } else {
        const { data: link2, error: lke2 } = await a.auth.admin.generateLink({ type: "recovery", email });
        const p2 = link2?.properties as { hashed_token?: string; verification_type?: string } | undefined;
        if (lke2 || !p2?.hashed_token) return NextResponse.json({ error: lke2?.message || "gagal membuat tautan" }, { status: 500 });
        const url2 = `${originOf(req)}/auth/callback?token_hash=${encodeURIComponent(p2.hashed_token)}&type=${p2.verification_type}&next=${encodeURIComponent("/reseller/setup")}`;
        m2 = renderResellerInviteEmail("id", url2, g.agent.company_name);
      }
      try { await sendMail(email, m2.subject, m2.html, m2.text); } catch (e) {
        console.error("[reseller.resend] SMTP gagal:", e);
        return NextResponse.json({ error: "email gagal terkirim — coba lagi" }, { status: 500 });
      }
      return NextResponse.json({ ok: true, resent: true });
    }
    if (rs.status !== "pending") return NextResponse.json({ error: "hanya calon pending yang bisa disetujui" }, { status: 400 });
    // — buat/temukan user auth + tolak email peran lain (pola invite agen yang terbukti)
    // [B21 fix 2026-07-19] role diset SAAT createUser → trigger handle_new_tenant (migr 0173)
    // tidak mencetak user reseller sebagai tenant trial (bug tenant-hantu).
    let uid: string | null = null;
    let tenantLink = false; // [B21 MGM §9a.5, ketok 2026-07-19] email = TENANT existing → TAUTKAN, bukan tolak
    const { data: created, error: ce } = await a.auth.admin.createUser({ email, email_confirm: true, app_metadata: { role: "reseller" } });
    if (ce) {
      const m = (ce.message || "").toLowerCase();
      if (!(m.includes("registered") || m.includes("already"))) return NextResponse.json({ error: ce.message }, { status: 500 });
      const { data: gl, error: ge } = await a.auth.admin.generateLink({ type: "recovery", email });
      if (ge || !gl?.user) return NextResponse.json({ error: ge?.message || "user lookup gagal" }, { status: 500 });
      const role = (gl.user.app_metadata as Record<string, unknown> | null)?.role;
      if (role && role !== "reseller") return NextResponse.json({ error: "email ini sudah dipakai akun lain — minta calon memakai email berbeda" }, { status: 400 });
      const { data: tc } = await a.from("tenant_configs").select("tenant_id").eq("tenant_id", gl.user.id).limit(1);
      // MGM (member-get-member): tenant boleh merangkap reseller dengan SATU login. Penanda
      // reseller_linked (bukan role) menjaga akses dashboard tenant-nya tetap hidup.
      tenantLink = Boolean(tc && tc.length > 0);
      uid = gl.user.id;
    } else {
      uid = created.user.id;
    }
    // [AUDIT T-5] satu email = satu identitas reseller: sudah tertaut reseller LAIN (agen mana pun)
    // → tolak jelas (portal reseller hanya bisa menampilkan satu profil; uang tetap benar tapi
    // tampilan sebagian = membingungkan — lebih baik jujur di muka).
    const { data: linked } = await a.from("resellers").select("id").eq("user_id", uid).neq("id", rs.id).limit(1);
    if (linked && linked.length > 0) {
      return NextResponse.json({ error: "email ini sudah menjadi reseller terdaftar (di agen lain) — minta calon memakai email berbeda" }, { status: 400 });
    }
    if (tenantLink) {
      // [MGM §9a.5] MERGE manual metadata (anti-asumsi: perlakukan update sbg REPLACE — ambil
      // metadata sekarang, pertahankan seluruh isinya, tambah penanda; role TIDAK disentuh).
      const { data: curU, error: gue } = await a.auth.admin.getUserById(uid);
      if (gue || !curU?.user) return NextResponse.json({ error: gue?.message || "user lookup gagal" }, { status: 500 });
      const meta = { ...(curU.user.app_metadata as Record<string, unknown> | null ?? {}), reseller_linked: true };
      const { error: re } = await a.auth.admin.updateUserById(uid, { app_metadata: meta });
      if (re) return NextResponse.json({ error: `gagal menautkan: ${re.message}` }, { status: 500 });
    } else {
      const { error: re } = await a.auth.admin.updateUserById(uid, { app_metadata: { role: "reseller" } });
      if (re) return NextResponse.json({ error: `gagal set peran: ${re.message}` }, { status: 500 });
    }
    // — kode unik reseller (global registry; retry anti-tabrakan)
    let code: string | null = null;
    for (let i = 0; i < 5 && !code; i++) {
      const cand = randCode("RS");
      const { error: ie } = await a.from("partner_codes").insert({ code: cand, owner_kind: "reseller", agent_id: g.agent.id, reseller_id: rs.id });
      if (!ie) code = cand;
      else if (!ie.message.includes("duplicate")) return NextResponse.json({ error: ie.message }, { status: 500 });
    }
    if (!code) return NextResponse.json({ error: "gagal membuat kode unik — coba lagi" }, { status: 500 });
    await a.from("resellers").update({ user_id: uid, status: "active", updated_at: new Date().toISOString() }).eq("id", rs.id);
    // — email: tenant tertaut = portal AKTIF (login existing, TANPA set-password);
    //   reseller murni = undangan set-password → /reseller/setup (perilaku lama persis)
    let subject: string, html: string, text: string;
    if (tenantLink) {
      ({ subject, html, text } = renderResellerLinkedEmail("id", `${originOf(req)}/reseller`, g.agent.company_name));
    } else {
      const { data: link, error: lke } = await a.auth.admin.generateLink({ type: "recovery", email });
      const props = link?.properties as { hashed_token?: string; verification_type?: string } | undefined;
      if (lke || !props?.hashed_token) return NextResponse.json({ error: lke?.message || "gagal membuat tautan undangan" }, { status: 500 });
      const action_url = `${originOf(req)}/auth/callback?token_hash=${encodeURIComponent(props.hashed_token)}&type=${props.verification_type}&next=${encodeURIComponent("/reseller/setup")}`;
      ({ subject, html, text } = renderResellerInviteEmail("id", action_url, g.agent.company_name));
    }
    try {
      await sendMail(email, subject, html, text);
    } catch (e) {
      console.error("[reseller.approve] SMTP gagal:", e);
      return NextResponse.json({ ok: true, code, warning: "reseller AKTIF tapi email undangan gagal terkirim — hubungi reseller / coba setujui ulang utk kirim ulang" });
    }
    return NextResponse.json({ ok: true, code, linked_tenant: tenantLink });
  }

  return NextResponse.json({ error: "action tidak dikenal" }, { status: 400 });
}
