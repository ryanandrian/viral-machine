import { createAdminClient } from "@/lib/supabase/admin";

// Kesiapan channel TEST admin (admin_test_internal) — SATU logika utk route test-lab/test dan
// niches/[id]/test. Pola = subset gerbang channel_missing (provider-aware: penyedia gratis tanpa kunci;
// kunci dicek di POOL per key_group vendor, status='valid' = validate-early).
export const ADMIN_TEST_TID = "admin_test_internal";

export type ElemStatus = { ok: boolean; msg: string };
export type TestReadiness = {
  channel_id: string | null;
  elems: { llm: ElemStatus; tts: ElemStatus; visual: ElemStatus };
  ready: boolean;
};

export async function testChannelReadiness(): Promise<TestReadiness> {
  const a = createAdminClient();
  const [{ data: ch }, { data: providers }, { data: models }, { data: accounts }] = await Promise.all([
    a.from("channels").select("id, llm_library, llm_model, tts_provider, tts_model, voice_key, visual_mode").eq("tenant_id", ADMIN_TEST_TID).maybeSingle(),
    a.from("ai_providers").select("provider_key, key_group, auth_type"),
    a.from("ai_models").select("model_key, provider_key, component").eq("is_active", true),
    a.from("tenant_ai_accounts").select("key_group, status").eq("tenant_id", ADMIN_TEST_TID),
  ]);
  const prov = new Map((providers ?? []).map((p) => [p.provider_key as string, p]));
  const needsKey = (p: string) => (prov.get(p)?.auth_type ?? "api_key") !== "none";
  const keyValid = (p: string) => {
    const kg = prov.get(p)?.key_group ?? p;
    return (accounts ?? []).some((acc) => acc.key_group === kg && acc.status === "valid");
  };
  const keyMsg = (p: string) => needsKey(p) ? (keyValid(p) ? "" : `kunci ${prov.get(p)?.key_group ?? p} belum valid (isi di Test Lab)`) : "";

  const elem = (provider: string | null, model: string | null, extraMissing: string): ElemStatus => {
    if (!provider) return { ok: false, msg: "penyedia belum dipilih" };
    if (!model) return { ok: false, msg: "model belum dipilih" };
    if (extraMissing) return { ok: false, msg: extraMissing };
    const km = keyMsg(provider);
    if (km) return { ok: false, msg: km };
    return { ok: true, msg: "siap" };
  };

  const llm = elem(ch?.llm_library ?? null, ch?.llm_model ?? null, "");
  const tts = elem(ch?.tts_provider ?? null, ch?.tts_model ?? null, ch?.voice_key ? "" : (ch?.tts_provider ? "voice belum dipilih" : ""));

  let visual: ElemStatus;
  const vm = ch?.visual_mode ?? "";
  if (!vm) visual = { ok: false, msg: "generator visual belum dipilih" };
  else {
    const [kind, vModel] = vm.split(":");
    const comp = kind === "ai_video" ? "video" : "image";
    const m = (models ?? []).find((x) => x.component === comp && x.model_key === vModel);
    if (!m) visual = { ok: false, msg: `model visual tak ada di katalog: ${vm}` };
    else {
      const km = keyMsg(m.provider_key as string);
      visual = km ? { ok: false, msg: km } : { ok: true, msg: "siap" };
    }
  }

  return { channel_id: ch?.id ?? null, elems: { llm, tts, visual }, ready: llm.ok && tts.ok && visual.ok && !!ch?.id };
}
