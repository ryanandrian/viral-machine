import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { ADMIN_TEST_TID } from "../route";

// "Test semua kredensial" (model POOL/VENDOR) — status sudah divalidasi saat disimpan (validate-early di /integrations),
// jadi cukup baca STATUS pool (tenant_ai_accounts) + koneksi YouTube. Kunci AI/Telegram diatur di Page Kredensial.
export async function POST() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const { data: aiacc } = await a.from("tenant_ai_accounts").select("key_group,status").eq("tenant_id", ADMIN_TEST_TID);
  const { data: cred } = await a.from("tenant_youtube_accounts").select("google_refresh_token_enc").eq("tenant_id", ADMIN_TEST_TID).limit(1).maybeSingle();

  const accs = (aiacc ?? []) as { key_group: string; status: string }[];
  const stOf = (...kgs: string[]) => { const x = accs.find((y) => kgs.includes(y.key_group)); return x ? x.status : null; };
  const rep = (s: string | null) => s === "valid" ? { ok: true, msg: "valid" } : s === "invalid" ? { ok: false, msg: "kunci ditolak penyedia" } : { ok: false, msg: "belum diisi (di Kredensial)" };

  const out: Record<string, { ok: boolean; msg: string }> = {
    llm: rep(stOf("openai", "anthropic")),        // vendor LLM
    visual: rep(stOf("openai")),                  // vendor Visual (openai serves image)
    tts: rep(stOf("elevenlabs", "openai")),       // vendor TTS (elevenlabs / openai_tts→openai)
    youtube: cred?.google_refresh_token_enc ? { ok: true, msg: "kredensial OAuth tersimpan" } : { ok: false, msg: "belum terhubung (Connect YouTube)" },
  };
  const allOk = out.llm.ok && out.visual.ok && out.tts.ok;
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.test_credentials", detail: { result: out } });
  return NextResponse.json({ result: out, ready: allOk });
}
