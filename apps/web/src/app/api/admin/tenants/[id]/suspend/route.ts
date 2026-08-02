import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E1 suspend/unsuspend tenant (PHASE10 §2). Body: { action: 'suspend' | 'unsuspend' }.
// subscription_status → 'suspended' | 'active'. Dicatat ke admin_audit.
// Catatan: comp account (is_developer/discount≥100) tetap produce (gate bypass) — suspend tak berbahaya.
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const { action } = await req.json().catch(() => ({}));
  if (action !== "suspend" && action !== "unsuspend") {
    return NextResponse.json({ error: "invalid_action" }, { status: 400 });
  }
  const admin = createAdminClient();
  const next = action === "suspend" ? "suspended" : "active";

  const { error } = await admin
    .from("tenant_configs")
    .update({ subscription_status: next, updated_at: new Date().toISOString() })
    .eq("tenant_id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // [B24 §10c] Diaktifkan kembali → lepas rem circuit-breaker channelnya. Tanpa ini tenant TERJEBAK:
  // channel "Dihentikan sistem", sementara satu-satunya pelepas (tombol Jalankan-ulang) terkunci
  // selama langganannya mati. Kelima jalur reaktivasi memanggil fungsi yang SAMA — bukan lima salinan.
  let resumed = 0;
  if (next === "active") {
    const { data: n, error: rErr } = await admin.rpc("tenant_resume_channels", { p_tenant_id: id });
    if (rErr) console.error("[admin/suspend] lepas rem gagal:", rErr.message);
    else resumed = Number(n ?? 0);
  }

  await admin.from("admin_audit").insert({
    admin_uid: g.user.id,
    action: `tenant.${action}`,
    target_tenant: id,
    detail: { subscription_status: next, channels_resumed: resumed },
  });

  return NextResponse.json({ ok: true, subscription_status: next, channels_resumed: resumed });
}
