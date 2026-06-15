import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E1 detail tenant by tenant_id (PHASE10 §2). service_role bypass-RLS.
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const admin = createAdminClient();

  const { data: cfg, error } = await admin
    .from("tenant_configs")
    .select("tenant_id, display_handle, plan_type, subscription_status, current_period_end, trial_started_at, is_developer, discount_pct, created_at, timezone")
    .eq("tenant_id", id)
    .maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!cfg) return NextResponse.json({ error: "not_found" }, { status: 404 });

  const [{ data: user }, { data: channels }, { data: runs }, { data: payments }] = await Promise.all([
    admin.auth.admin.getUserById(id),
    admin.from("channels").select("id, channel_name, niche, platform, is_active, publish_privacy, created_at").eq("tenant_id", id),
    admin.from("production_runs").select("id, topic, niche, status, created_at, youtube_url").eq("tenant_id", id).order("created_at", { ascending: false }).limit(8),
    admin.from("payments").select("order_id, plan_type, gross_amount, status, created_at").eq("tenant_id", id).order("created_at", { ascending: false }).limit(10),
  ]);

  const comp = cfg.is_developer || (cfg.discount_pct ?? 0) >= 100;
  return NextResponse.json({
    tenant: {
      ...cfg,
      comp,
      email: user?.user?.email ?? "",
    },
    channels: channels ?? [],
    runs: runs ?? [],
    payments: payments ?? [],
  });
}
