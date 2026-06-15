import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Whitelist tabel katalog → kolom yang boleh diubah + PK. Mencegah tulis sembarang kolom/tabel.
const CATALOG: Record<string, { pk: string; cols: string[] }> = {
  ai_models: { pk: "model_key", cols: ["provider_key", "component", "model_id", "display_name", "quality_tier", "is_active", "sort_order", "cost_hint", "default_params"] },
  ai_providers: { pk: "provider_key", cols: ["display_name", "adapter", "base_url", "auth_type", "is_active", "request_param_schema"] },
  content_languages: { pk: "locale", cols: ["display_name", "quality_tier", "caption_font", "is_active", "sort_order", "tts_providers_supported"] },
  voice_catalog: { pk: "voice_key", cols: ["provider_key", "display_name", "locale", "gender", "niche_default", "preview_url", "is_active", "sort_order"] },
  music_library: { pk: "id", cols: ["is_active", "is_default", "name", "mood", "niche"] },
  tts_profiles: { pk: "provider_key", cols: ["is_active", "delivery_wps", "tts_class", "speed_param"] },
};

// GET semua data katalog (E2 — Phase 10.4-10.7). service_role bypass-RLS.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const [ai_models, ai_providers, music_library, content_languages, voice_catalog, tts_profiles] = await Promise.all([
    a.from("ai_models").select("*").order("component").order("sort_order"),
    a.from("ai_providers").select("*").order("provider_key"),
    a.from("music_library").select("id, name, niche, mood, duration_s, is_active, is_default, source").order("niche").order("name"),
    a.from("content_languages").select("*").order("sort_order"),
    a.from("voice_catalog").select("*").order("sort_order"),
    a.from("tts_profiles").select("*").order("provider_key"),
  ]);
  return NextResponse.json({
    ai_models: ai_models.data ?? [], ai_providers: ai_providers.data ?? [],
    music_library: music_library.data ?? [], content_languages: content_languages.data ?? [],
    voice_catalog: voice_catalog.data ?? [], tts_profiles: tts_profiles.data ?? [],
  });
}

// PATCH: { table, key, patch } — update baris katalog (whitelist tabel+kolom). + admin_audit.
export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { table, key, patch } = await req.json().catch(() => ({}));
  const def = CATALOG[table];
  if (!def) return NextResponse.json({ error: "table_not_allowed" }, { status: 400 });
  const clean: Record<string, unknown> = {};
  for (const c of def.cols) if (patch && c in patch) clean[c] = patch[c];
  if (Object.keys(clean).length === 0) return NextResponse.json({ error: "no_editable_fields" }, { status: 400 });
  const a = createAdminClient();
  const { data, error } = await a.from(table).update(clean).eq(def.pk, key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.update.${table}`, detail: { key, fields: Object.keys(clean) } });
  return NextResponse.json({ ok: true, row: data });
}

// POST: { table, row } — buat baris katalog baru (whitelist + PK wajib). + admin_audit.
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { table, row } = await req.json().catch(() => ({}));
  const def = CATALOG[table];
  if (!def) return NextResponse.json({ error: "table_not_allowed" }, { status: 400 });
  if (!row?.[def.pk]) return NextResponse.json({ error: `${def.pk}_required` }, { status: 400 });
  const clean: Record<string, unknown> = { [def.pk]: row[def.pk] };
  for (const c of def.cols) if (c in row) clean[c] = row[c];
  const a = createAdminClient();
  const { data, error } = await a.from(table).insert(clean).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.create.${table}`, detail: { key: row[def.pk] } });
  return NextResponse.json({ ok: true, row: data });
}
