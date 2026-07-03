import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { ADMIN_TEST_TID } from "@/lib/admin/test-readiness";

// Test Lab (dirombak 2026-07-04, keputusan owner): fasilitas uji-produksi niche ADMIN.
// - Kredensial AI channel test = POOL tenant_ai_accounts (tenant admin_test_internal) via vault
//   (validate-early NYATA) — route ./credentials. TANPA YouTube (test TIDAK pernah publish).
// - Pilihan penyedia+model per elemen = LENGKAP dari katalog DB (ai_providers/ai_models/voice_catalog),
//   nol hardcode — disimpan ke row channels admin_test (kolom sama dgn channel tenant).

// Konfigurasi channel test yang boleh diubah dari Test Lab (subset kolom channel tenant).
const CH_FIELDS = ["llm_library", "llm_model", "tts_provider", "tts_model", "voice_key", "visual_mode"] as const;

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const [{ data: ch }, { data: models }, { data: providers }, { data: voices }, { data: accounts }] = await Promise.all([
    a.from("channels").select("id, channel_name, llm_library, llm_model, tts_provider, tts_model, voice_key, visual_mode").eq("tenant_id", ADMIN_TEST_TID).maybeSingle(),
    a.from("ai_models").select("model_key, provider_key, component, display_name").eq("is_active", true).order("component"),
    a.from("ai_providers").select("provider_key, display_name, key_group, auth_type"),
    a.from("voice_catalog").select("voice_key, provider_key, display_name").eq("is_active", true).order("voice_key"),
    a.from("tenant_ai_accounts").select("id, key_group, label, status, validated_at").eq("tenant_id", ADMIN_TEST_TID).order("created_at"),
  ]);
  return NextResponse.json({
    channel: ch ?? null,
    catalog: { models: models ?? [], providers: providers ?? [], voices: voices ?? [] },
    accounts: accounts ?? [],
  });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const body = await req.json().catch(() => ({}));
  const a = createAdminClient();

  const patch: Record<string, string> = {};
  for (const k of CH_FIELDS) if (k in body && typeof body[k] === "string") patch[k] = body[k].trim();
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });

  // Validasi katalog server-side (nol asumsi FE): model harus ada+aktif utk komponen & penyedianya.
  const { data: models } = await a.from("ai_models").select("model_key, provider_key, component").eq("is_active", true);
  const has = (component: string, provider: string, model: string) =>
    (models ?? []).some((m) => m.component === component && m.provider_key === provider && m.model_key === model);
  if (patch.llm_library && patch.llm_model && !has("llm", patch.llm_library, patch.llm_model)) {
    return NextResponse.json({ error: `model LLM tak ada di katalog: ${patch.llm_library}/${patch.llm_model}` }, { status: 400 });
  }
  if (patch.tts_provider && patch.tts_model && !has("tts", patch.tts_provider, patch.tts_model)) {
    return NextResponse.json({ error: `model TTS tak ada di katalog: ${patch.tts_provider}/${patch.tts_model}` }, { status: 400 });
  }
  if (patch.voice_key) {
    const { data: v } = await a.from("voice_catalog").select("voice_key").eq("voice_key", patch.voice_key).eq("is_active", true).maybeSingle();
    if (!v) return NextResponse.json({ error: `voice tak ada di katalog: ${patch.voice_key}` }, { status: 400 });
  }
  if (patch.visual_mode) {
    const [kind, vModel] = patch.visual_mode.split(":");
    const comp = kind === "ai_video" ? "video" : "image";
    const okVis = (models ?? []).some((m) => m.component === comp && m.model_key === vModel);
    if (!(kind === "ai_image" || kind === "ai_video") || !okVis) {
      return NextResponse.json({ error: `visual_mode tak valid: ${patch.visual_mode}` }, { status: 400 });
    }
  }

  const { error } = await a.from("channels").update(patch).eq("tenant_id", ADMIN_TEST_TID);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: "test_lab.channel_config", detail: patch });
  return NextResponse.json({ ok: true });
}
