import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { validateProviderKey } from "@/lib/providers/validate-key";
import { ADMIN_TEST_TID } from "../route";

// "Test semua kredensial" — validasi NYATA: panggil API provider dgn key tersimpan (channel admin_test).
// Bukan palsu — benar-benar hit endpoint provider + laporkan ok/gagal per kredensial.
// Logika validasi (incl. EL scope-aware F1-09) = SATU sumber `@/lib/providers/validate-key` (nol-duplikat).

export async function POST() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const { data: cfg } = await a.from("tenant_configs")
    .select("llm_library, llm_api_key, visual_api_key, tts_api_key").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();
  const { data: cred } = await a.from("tenant_credentials").select("google_refresh_token_enc").eq("tenant_id", ADMIN_TEST_TID).maybeSingle();

  const out: Record<string, { ok: boolean; msg: string }> = {};

  // LLM (anthropic / openai)
  out.llm = cfg?.llm_api_key
    ? await validateProviderKey(cfg.llm_library === "anthropic" ? "anthropic" : "openai", cfg.llm_api_key)
    : { ok: false, msg: "belum diisi" };

  // Visual (OpenAI image)
  out.visual = cfg?.visual_api_key
    ? await validateProviderKey("openai", cfg.visual_api_key)
    : { ok: false, msg: "belum diisi" };

  // TTS (ElevenLabs) — scope-aware (F1-09: key TTS-scoped tak lagi false-negative); edge_tts tak perlu key
  out.tts = cfg?.tts_api_key
    ? await validateProviderKey("elevenlabs", cfg.tts_api_key)
    : { ok: false, msg: "belum diisi (edge_tts fallback tak perlu key)" };

  // YouTube — presence (alur OAuth BYO-CC terpisah)
  out.youtube = cred?.google_refresh_token_enc
    ? { ok: true, msg: "kredensial OAuth tersimpan" }
    : { ok: false, msg: "belum terhubung (Connect YouTube)" };

  const allOk = out.llm.ok && out.visual.ok && (out.tts.ok || out.tts.msg.includes("edge_tts"));
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.test_credentials", detail: { result: out } });
  return NextResponse.json({ result: out, ready: allOk });
}
