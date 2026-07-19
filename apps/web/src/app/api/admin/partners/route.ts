import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] Admin Program Agen (F1). service_role (RLS tabel partner terkunci total di F1).
// Rate & status pajak agen = HANYA dari sini (SPEC §1c — bukan dari aplikasi agen).
// Uang (build/approve/paid/bank) = /api/admin/partners/ops → mv-webhook → partner.py (SATU otoritas).

const CODE_RE = /^[A-Z0-9]{4,12}$/;
const AGENT_FIELDS = ["company_name", "pic_name", "pic_email", "pic_phone", "status",
  "commission_type", "commission_value", "tax_status", "npwp", "notes"] as const;

function cleanAgent(body: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of AGENT_FIELDS) if (f in body) out[f] = body[f];
  if ("commission_value" in out && (Number.isNaN(Number(out.commission_value)) || Number(out.commission_value) < 0)) {
    throw new Error("nilai komisi tidak valid");
  }
  return out;
}

export async function GET(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const a = createAdminClient();
  const id = new URL(req.url).searchParams.get("id");

  if (id) {
    // Rinci per-agen (SPEC §1f: layar yang sama dgn yang kelak dilihat agen)
    const [{ data: agent }, { data: codes }, { data: att }, { data: ledger }, { data: payouts }] = await Promise.all([
      a.from("agents").select("*").eq("id", id).single(),
      a.from("partner_codes").select("code,owner_kind,active,used_count").eq("agent_id", id),
      a.from("tenant_attribution").select("tenant_id,code,locked_at").eq("agent_id", id),
      a.from("commission_ledger").select("*").eq("agent_id", id).order("id", { ascending: false }).limit(200),
      a.from("agent_payouts").select("*").eq("agent_id", id).order("period_month", { ascending: false }),
    ]);
    if (!agent) return NextResponse.json({ error: "not_found" }, { status: 404 });
    const tenantIds = (att ?? []).map((r) => r.tenant_id);
    const { data: tenants } = tenantIds.length
      ? await a.from("tenant_configs").select("tenant_id,display_handle,plan_type,subscription_status").in("tenant_id", tenantIds)
      : { data: [] };
    // nomor rekening TIDAK ikut (terenkripsi; buka via ops bank_reveal saat transfer saja)
    const { bank_account_enc, ...safe } = agent as Record<string, unknown>;
    return NextResponse.json({
      agent: { ...safe, bank_account_set: Boolean(bank_account_enc) },
      codes: codes ?? [], attributions: att ?? [], tenants: tenants ?? [],
      ledger: ledger ?? [], payouts: payouts ?? [],
    });
  }

  const [{ data: agents }, { data: att }, { data: ledger }, { data: payouts }, { data: cfg }] = await Promise.all([
    a.from("agents").select("id,company_name,pic_name,pic_email,status,commission_type,commission_value,tax_status,created_at").order("created_at"),
    a.from("tenant_attribution").select("agent_id"),
    a.from("commission_ledger").select("agent_id,agent_amount_idr,status,entry_kind"),
    a.from("agent_payouts").select("*").order("period_month", { ascending: false }).limit(60),
    a.from("app_config").select("key,value").in("key", ["partner_payout_day", "partner_min_payout_idr", "partner_program_enabled"]),
  ]);
  const nTen: Record<string, number> = {}; (att ?? []).forEach((r) => { nTen[r.agent_id] = (nTen[r.agent_id] ?? 0) + 1; });
  const sums: Record<string, { accrued: number; paid: number }> = {};
  (ledger ?? []).forEach((r) => {
    const s = (sums[r.agent_id] ??= { accrued: 0, paid: 0 });
    if (r.status === "accrued" || r.status === "approved") s.accrued += Number(r.agent_amount_idr);
    if (r.status === "paid") s.paid += Number(r.agent_amount_idr);
  });
  const { data: codes } = await a.from("partner_codes").select("agent_id,code,owner_kind").eq("owner_kind", "agent");
  const codeOf: Record<string, string> = {}; (codes ?? []).forEach((c) => { codeOf[c.agent_id] = c.code; });
  return NextResponse.json({
    agents: (agents ?? []).map((x) => ({ ...x, code: codeOf[x.id] ?? null, tenants: nTen[x.id] ?? 0,
      accrued_idr: sums[x.id]?.accrued ?? 0, paid_idr: sums[x.id]?.paid ?? 0 })),
    payouts: payouts ?? [],
    config: Object.fromEntries((cfg ?? []).map((c) => [c.key, c.value])),
  });
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const body = await req.json().catch(() => ({}));
  const a = createAdminClient();
  let clean: Record<string, unknown>;
  try { clean = cleanAgent(body); } catch (e) { return NextResponse.json({ error: String(e) }, { status: 400 }); }
  const code = String(body.code ?? "").trim().toUpperCase();
  if (!clean.company_name || !clean.pic_email) return NextResponse.json({ error: "nama perusahaan & email PIC wajib" }, { status: 400 });
  if (!CODE_RE.test(code)) return NextResponse.json({ error: "kode wajib 4-12 huruf besar/angka" }, { status: 400 });
  const { data: agent, error } = await a.from("agents").insert(clean).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  const { error: ce } = await a.from("partner_codes").insert({ code, owner_kind: "agent", agent_id: agent.id });
  if (ce) { // kode tabrakan → agen batal utuh (jangan setengah-jadi)
    await a.from("agents").delete().eq("id", agent.id);
    return NextResponse.json({ error: ce.message.includes("duplicate") ? "kode sudah dipakai" : ce.message }, { status: 400 });
  }
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "partner.agent.create", detail: { id: agent.id, code } });
  return NextResponse.json({ ok: true, agent: { ...agent, code } });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const { id, patch } = await req.json().catch(() => ({}));
  if (!id) return NextResponse.json({ error: "bad_request" }, { status: 400 });
  const a = createAdminClient();
  let clean: Record<string, unknown>;
  try { clean = cleanAgent(patch ?? {}); } catch (e) { return NextResponse.json({ error: String(e) }, { status: 400 }); }
  // [B21 pagar 2026-07-19] Ganti pic_email pada agen yang SUDAH punya login = DITOLAK jelas.
  // Insiden nyata 19-Jul (THETANGGA): pic_email diganti saat troubleshooting SMTP → login (user_id)
  // tetap milik email lama → "Kirim ulang undangan" menembak email tanpa akun + tautan Google putus.
  // Memindahkan login ke email baru = keputusan sadar (buka ketok terpisah), bukan efek samping edit form.
  if (typeof clean.pic_email === "string") {
    const { data: curAg } = await a.from("agents").select("pic_email,user_id").eq("id", id).limit(1);
    const cur0 = curAg?.[0];
    if (cur0?.user_id && String(clean.pic_email).trim().toLowerCase() !== String(cur0.pic_email || "").trim().toLowerCase()) {
      return NextResponse.json({ error: "Email PIC tidak bisa diganti: agen ini SUDAH punya akun login yang terikat ke email lama (undangan/Google). Mengganti email = memutus login & undangan. Bila memang harus pindah email, hubungi developer (perlu pemindahan akun, bukan sekadar edit). / PIC email is locked: this agent already has a login bound to the old email." }, { status: 400 });
    }
  }
  // Ganti kode: HANYA bila kode lama belum pernah dipakai mendaftar (BEKU §5g.2)
  if (patch?.code) {
    const nc = String(patch.code).trim().toUpperCase();
    if (!CODE_RE.test(nc)) return NextResponse.json({ error: "kode wajib 4-12 huruf besar/angka" }, { status: 400 });
    const { data: cur } = await a.from("partner_codes").select("code,used_count").eq("agent_id", id).eq("owner_kind", "agent").limit(1);
    const old = cur?.[0];
    if (old && old.code !== nc) {
      if ((old.used_count ?? 0) > 0) return NextResponse.json({ error: "kode sudah pernah dipakai mendaftar — BEKU (jejak atribusi). Buat agen memakai kode itu terus." }, { status: 400 });
      const { error: ie } = await a.from("partner_codes").insert({ code: nc, owner_kind: "agent", agent_id: id });
      if (ie) return NextResponse.json({ error: ie.message.includes("duplicate") ? "kode sudah dipakai" : ie.message }, { status: 400 });
      // [AUDIT T-2] delete kode lama WAJIB dicek — gagal (mis. FK atribusi) dgn insert sudah jadi
      // = dua kode aktif senyap. Gagal → rollback kode baru + pesan jujur.
      const { error: de } = await a.from("partner_codes").delete().eq("code", old.code);
      if (de) {
        await a.from("partner_codes").delete().eq("code", nc);
        return NextResponse.json({ error: "kode lama tidak bisa dilepas (sudah dipakai atribusi) — kode BEKU" }, { status: 400 });
      }
    } else if (!old) {
      const { error: ie } = await a.from("partner_codes").insert({ code: nc, owner_kind: "agent", agent_id: id });
      if (ie) return NextResponse.json({ error: ie.message }, { status: 400 });
    }
  }
  if (Object.keys(clean).length) {
    clean.updated_at = new Date().toISOString();
    const { error } = await a.from("agents").update(clean).eq("id", id);
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  }
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "partner.agent.update", detail: { id } });
  return NextResponse.json({ ok: true });
}
