import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { ADMIN_TEST_TID } from "../route";

// "Test semua kredensial" — validasi NYATA: panggil API provider dgn key tersimpan (channel admin_test).
// Bukan palsu — benar-benar hit endpoint provider + laporkan ok/gagal per kredensial.
async function check(url: string, headers: Record<string, string>): Promise<{ ok: boolean; msg: string }> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12000);
    const r = await fetch(url, { headers, signal: ctrl.signal });
    clearTimeout(t);
    if (r.ok) return { ok: true, msg: "valid" };
    if (r.status === 401 || r.status === 403) return { ok: false, msg: "key ditolak (401/403)" };
    return { ok: false, msg: `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, msg: e instanceof Error ? e.message : "error" };
  }
}

export async function POST() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const { data: cfg } = await a.from("tenant_configs")
    .select("llm_library, llm_api_key, visual_api_key, tts_api_key").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  const { data: cred } = await a.from("tenant_credentials").select("google_refresh_token_enc").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();

  const out: Record<string, { ok: boolean; msg: string }> = {};

  // LLM (anthropic / openai)
  if (cfg?.llm_api_key) {
    out.llm = cfg.llm_library === "anthropic"
      ? await check("https://api.anthropic.com/v1/models", { "x-api-key": cfg.llm_api_key, "anthropic-version": "2023-06-01" })
      : await check("https://api.openai.com/v1/models", { Authorization: `Bearer ${cfg.llm_api_key}` });
  } else out.llm = { ok: false, msg: "belum diisi" };

  // Visual (OpenAI image)
  out.visual = cfg?.visual_api_key
    ? await check("https://api.openai.com/v1/models", { Authorization: `Bearer ${cfg.visual_api_key}` })
    : { ok: false, msg: "belum diisi" };

  // TTS (ElevenLabs) — edge_tts tak perlu key
  out.tts = cfg?.tts_api_key
    ? await check("https://api.elevenlabs.io/v1/user", { "xi-api-key": cfg.tts_api_key })
    : { ok: false, msg: "belum diisi (edge_tts fallback tak perlu key)" };

  // YouTube — presence (alur OAuth BYO-CC terpisah)
  out.youtube = cred?.google_refresh_token_enc
    ? { ok: true, msg: "kredensial OAuth tersimpan" }
    : { ok: false, msg: "belum terhubung (Connect YouTube)" };

  const allOk = out.llm.ok && out.visual.ok && (out.tts.ok || out.tts.msg.includes("edge_tts"));
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.test_credentials", detail: { result: out } });
  return NextResponse.json({ result: out, ready: allOk });
}
