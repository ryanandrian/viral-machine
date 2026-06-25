import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Test Lab — kredensial channel internal "admin_test" untuk test produksi niche (Phase: direct/admin_test).
// GET: status (key mana yang terisi + llm_library + channel id). PATCH: simpan key (service_role).
export const ADMIN_TEST_TID = "admin_test_internal";

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const { data: cfg } = await a.from("tenant_configs").select("llm_library").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  const { data: ch } = await a.from("channels").select("id, channel_name").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  const { data: cred } = await a.from("tenant_youtube_accounts").select("google_refresh_token_enc").eq("tenant_id", ADMIN_TEST_TID).limit(1).maybeSingle();
  // Kunci AI = POOL tenant_ai_accounts (model VENDOR; kolom kunci tenant_configs didrop 0090). Set via /integrations.
  const { data: aiacc } = await a.from("tenant_ai_accounts").select("status").eq("tenant_id", ADMIN_TEST_TID);
  const aiValid = (aiacc ?? []).some((x: { status: string }) => x.status === "valid");
  return NextResponse.json({
    llm_library: cfg?.llm_library ?? "openai",
    has: { llm: aiValid, visual: aiValid, tts: aiValid, youtube: !!cred?.google_refresh_token_enc },
    channel_id: ch?.id ?? null, channel_name: ch?.channel_name ?? null,
  });
}

const KEYS = ["llm_library"];  // kunci AI kini di POOL (/integrations), bukan tenant_configs (kolom didrop 0090)
export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const body = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of KEYS) if (k in body && String(body[k]).trim()) patch[k] = String(body[k]).trim();
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });
  patch.updated_at = new Date().toISOString();
  const a = createAdminClient();
  const { error } = await a.from("tenant_configs").update(patch).eq("tenant_id", ADMIN_TEST_TID);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.save_keys", detail: { fields: Object.keys(patch) } });
  return NextResponse.json({ ok: true });
}
