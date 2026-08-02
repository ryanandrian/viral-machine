import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// LIFECYCLE (B9) — aksi manual admin di halaman Tenants. Pola sama dgn /suspend & /comp
// (requireSuperAdmin + service_role + admin_audit). NO-HARDCODE: jumlah hari default dari
// app_config (nurture_trial_extend_days / block_retention_days) bila admin tak mengisi.
//   action:
//     extend            → perpanjang trial (status trial/trial_expired) → trial + N hari, reset penanda nurture
//     postpone_deletion → undur jadwal hapus (status blocked) → deletion_scheduled_at + N hari
//     reactivate_clean  → aktifkan bersih (status suspended/blocked) → reset SEMUA penanda (identik jalur bayar
//                         midtrans._apply_settlement) lalu beri trial + N hari (tanpa bayar = trial, bukan active)
const DAY_MS = 86_400_000;

// PAGAR STATUS (Tahap 1.5 finalisasi_tier_plan, anti-human-error): tiap aksi hanya sah pada status
// yang tepat — tanpa pagar ini, salah-klik "extend" pada tenant AKTIF-BERBAYAR menurunkannya jadi trial.
const ACTION_ALLOWED_STATUS: Record<string, string[]> = {
  extend: ["trial", "trial_expired"],
  postpone_deletion: ["blocked"],
  reactivate_clean: ["suspended", "blocked"],
};

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const body = await req.json().catch(() => ({} as Record<string, unknown>));
  const action = body.action;
  const admin = createAdminClient();

  if (typeof action !== "string" || !(action in ACTION_ALLOWED_STATUS)) {
    return NextResponse.json({ error: "invalid_action" }, { status: 400 });
  }
  const { data: tcur } = await admin.from("tenant_configs")
    .select("subscription_status").eq("tenant_id", id).maybeSingle();
  if (!tcur) return NextResponse.json({ error: "tenant_not_found" }, { status: 404 });
  const curStatus = String(tcur.subscription_status ?? "");
  if (!ACTION_ALLOWED_STATUS[action].includes(curStatus)) {
    return NextResponse.json({ error: "invalid_status_for_action", status: curStatus }, { status: 400 });
  }

  async function cfgInt(key: string, dflt: number): Promise<number> {
    const { data } = await admin.from("app_config").select("value").eq("key", key).maybeSingle();
    const v = parseInt(String(data?.value ?? ""), 10);
    return Number.isFinite(v) && v > 0 ? v : dflt;
  }
  const bodyDays = parseInt(String(body.days ?? ""), 10);
  const nowIso = new Date().toISOString();

  let upd: Record<string, unknown>;
  let detail: Record<string, unknown>;

  if (action === "extend") {
    const days = Number.isFinite(bodyDays) && bodyDays > 0 ? bodyDays : await cfgInt("nurture_trial_extend_days", 3);
    const end = new Date(Date.now() + days * DAY_MS).toISOString();
    upd = {
      subscription_status: "trial", current_period_end: end,
      // [B24 §10c] FAKTA perpanjangan → titik mulai hitung jatah uji bila kenop
      // `trial_quota_reset_on_extend` menyala. Perpanjangan admin = memang sedang diberi kesempatan.
      trial_extended_at: nowIso,
      nurture_step: 0, nurture_last_sent_at: null, trial_reminder_sent_at: null,
      winback_offer_pct: null, winback_offer_expires_at: null, lead_temp: null,
      updated_at: nowIso,
    };
    detail = { days, new_period_end: end };
  } else if (action === "postpone_deletion") {
    const days = Number.isFinite(bodyDays) && bodyDays > 0 ? bodyDays : await cfgInt("block_retention_days", 30);
    const { data: cur } = await admin.from("tenant_configs")
      .select("deletion_scheduled_at").eq("tenant_id", id).maybeSingle();
    const base = cur?.deletion_scheduled_at ? new Date(cur.deletion_scheduled_at as string) : new Date();
    const anchor = Math.max(base.getTime(), Date.now());
    const newDel = new Date(anchor + days * DAY_MS).toISOString();
    upd = { deletion_scheduled_at: newDel, deletion_warn_sent: 0, updated_at: nowIso };
    detail = { days, new_deletion: newDel };
  } else if (action === "reactivate_clean") {
    const days = Number.isFinite(bodyDays) && bodyDays > 0 ? bodyDays : await cfgInt("nurture_trial_extend_days", 3);
    const end = new Date(Date.now() + days * DAY_MS).toISOString();
    // reset kanonik — SAMA dgn midtrans._apply_settlement (jalur bayar) agar tenant bersih dari jejak lapsed/blokir
    upd = {
      subscription_status: "trial", current_period_end: end,
      trial_extended_at: nowIso,   // [B24 §10c] idem cabang 'extend' — jatah uji ikut segar
      renewal_reminder_sent_at: null, suspend_notified_at: null, trial_reminder_sent_at: null,
      suspended_at: null, blocked_at: null, deletion_scheduled_at: null,
      deletion_warn_sent: 0, nurture_step: 0, nurture_last_sent_at: null,
      lead_temp: null, raw_assets_purged_at: null,
      winback_offer_pct: null, winback_offer_expires_at: null,
      updated_at: nowIso,
    };
    detail = { days, new_period_end: end };
  } else {
    return NextResponse.json({ error: "invalid_action" }, { status: 400 });
  }

  const { error } = await admin.from("tenant_configs").update(upd).eq("tenant_id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // [B24 §10c] Aksi yang MENGHIDUPKAN langganan → lepas rem circuit-breaker channelnya, supaya
  // tenant tak terjebak (channel berhenti + pelepasnya terkunci). 'postpone_deletion' tidak
  // menghidupkan apa pun, jadi tidak ikut.
  let resumed = 0;
  if (action === "extend" || action === "reactivate_clean") {
    const { data: n, error: rErr } = await admin.rpc("tenant_resume_channels", { p_tenant_id: id });
    if (rErr) console.error("[admin/lifecycle] lepas rem gagal:", rErr.message);
    else resumed = Number(n ?? 0);
  }

  await admin.from("admin_audit").insert({
    admin_uid: g.user.id, action: `tenant.lifecycle.${action}`, target_tenant: id,
    detail: { ...detail, channels_resumed: resumed },
  });
  return NextResponse.json({ ok: true, action, ...detail, channels_resumed: resumed });
}
