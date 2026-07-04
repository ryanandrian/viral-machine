import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, DeleteObjectCommand } from "@aws-sdk/client-s3";

// Aset publik = S3 (aturan owner). Helper hapus objek S3 (best-effort) saat row aset dihapus.
const ASSET_BUCKET = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
function assetEndpoint() { return (process.env.S3_ENDPOINT || "").replace(/\/$/, ""); }
function publicUrl(key: string) { return `${assetEndpoint()}/${ASSET_BUCKET}/${key}`; }
async function s3DeleteObject(key: string): Promise<void> {
  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  if (!endpoint || !accessKeyId || !secretAccessKey) return;
  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try { await s3.send(new DeleteObjectCommand({ Bucket: ASSET_BUCKET, Key: key })); } catch { /* best-effort */ }
}

// Whitelist tabel katalog → kolom yang boleh diubah + PK. Mencegah tulis sembarang kolom/tabel.
const CATALOG: Record<string, { pk: string; cols: string[] }> = {
  ai_models: { pk: "model_key", cols: ["provider_key", "component", "model_id", "display_name", "quality_tier", "is_active", "sort_order", "cost_hint", "default_params", "pricing", "pricing_locked"] },
  ai_providers: { pk: "provider_key", cols: ["display_name", "adapter", "base_url", "auth_type", "key_group", "is_active", "request_param_schema"] },
  content_languages: { pk: "locale", cols: ["display_name", "quality_tier", "caption_font", "is_active", "sort_order", "tts_providers_supported"] },
  voice_catalog: { pk: "voice_key", cols: ["provider_key", "display_name", "locale", "language", "gender", "age", "accent", "use_case", "description", "default_settings", "niche_default", "preview_url", "delivery_wps", "pace_locked", "is_active", "sort_order"] },
  music_library: { pk: "id", cols: ["is_active", "is_default", "name", "mood", "niche", "bpm", "duration_s"] },
  tts_profiles: { pk: "provider_key", cols: ["is_active", "delivery_wps", "tts_class", "speed_param", "param_schema"] },
  moods: { pk: "mood_id", cols: ["keywords", "is_active"] },   // NICHE_DNA F4: kelola mood + keyword deteksi (dwibahasa)
  niche_property_presets: { pk: "id", cols: ["property", "preset_key", "label", "label_en", "description", "description_en", "value", "apply_mode", "sort_order", "is_active"] },
};

// Kolom jsonb: nilai string dari form di-JSON.parse agar tersimpan sbg objek (bukan string mentah).
const JSONB_COLS: Record<string, string[]> = {
  voice_catalog: ["default_settings"],
  tts_profiles: ["param_schema"],
  moods: ["keywords"],
  niche_property_presets: ["value"],
  ai_models: ["pricing"],
};
// Kolom numerik dengan RESET-ke-NULL + guard rentang (F5-01: voice_catalog.delivery_wps pace per-voice).
const NUMERIC_COLS: Record<string, Record<string, [number, number]>> = {
  voice_catalog: { delivery_wps: [1.0, 4.0] },
};
function coerceValue(table: string, col: string, val: unknown): unknown {
  // jsonb: string → objek; kosong → undefined (jangan tulis, pakai default DB)
  if (JSONB_COLS[table]?.includes(col)) {
    if (typeof val !== "string") return val;
    const s = val.trim();
    if (s === "") return undefined;
    try { return JSON.parse(s); } catch { throw new Error(`${col}: JSON tidak valid`); }
  }
  // numerik: kosong/null → NULL (admin bisa RESET); else angka + clamp rentang (tolak di luar)
  const range = NUMERIC_COLS[table]?.[col];
  if (range) {
    if (val === null || val === undefined || (typeof val === "string" && val.trim() === "")) return null;
    const n = Number(val);
    if (!Number.isFinite(n)) throw new Error(`${col}: harus angka`);
    if (n < range[0] || n > range[1]) throw new Error(`${col}: di luar rentang ${range[0]}–${range[1]}`);
    return n;
  }
  return val;
}

// GET semua data katalog (E2 — Phase 10.4-10.7). service_role bypass-RLS.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const [ai_models, ai_providers, music_library, content_languages, voice_catalog, tts_profiles, moods] = await Promise.all([
    a.from("ai_models").select("*").order("component").order("sort_order"),
    a.from("ai_providers").select("*").order("provider_key"),
    a.from("music_library").select("id, name, niche, mood, duration_s, bpm, object_key, is_active, is_default, source").order("niche").order("name"),
    a.from("content_languages").select("*").order("sort_order"),
    a.from("voice_catalog").select("*").order("sort_order"),
    a.from("tts_profiles").select("*").order("provider_key"),
    a.from("moods").select("*").order("mood_id"),
  ]);
  // public_url musik (S3) untuk tombol Play di catalog. voice_catalog sudah simpan preview_url.
  const music = (music_library.data ?? []).map((m) => ({
    ...m, public_url: (m as { object_key?: string }).object_key ? publicUrl((m as { object_key?: string }).object_key!) : null,
  }));
  return NextResponse.json({
    ai_models: ai_models.data ?? [], ai_providers: ai_providers.data ?? [],
    music_library: music, content_languages: content_languages.data ?? [],
    voice_catalog: voice_catalog.data ?? [], tts_profiles: tts_profiles.data ?? [],
    moods: moods.data ?? [],
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
  try {
    for (const c of def.cols) if (patch && c in patch) { const v = coerceValue(table, c, patch[c]); if (v !== undefined) clean[c] = v; }
  } catch (e) { return NextResponse.json({ error: (e as Error).message }, { status: 400 }); }
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
  try {
    for (const c of def.cols) if (c in row) { const v = coerceValue(table, c, row[c]); if (v !== undefined) clean[c] = v; }
  } catch (e) { return NextResponse.json({ error: (e as Error).message }, { status: 400 }); }
  const a = createAdminClient();
  const { data, error } = await a.from(table).insert(clean).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.create.${table}`, detail: { key: row[def.pk] } });
  return NextResponse.json({ ok: true, row: data });
}

// DELETE: { table, key } — hapus baris ASET + objek S3-nya. HANYA tabel aset (music_library, voice_catalog).
const DELETABLE = new Set(["music_library", "voice_catalog"]);
export async function DELETE(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { table, key } = await req.json().catch(() => ({}));
  const def = CATALOG[table];
  if (!def || !DELETABLE.has(table)) return NextResponse.json({ error: "delete_not_allowed" }, { status: 400 });
  if (!key && key !== 0) return NextResponse.json({ error: "key wajib" }, { status: 400 });
  const a = createAdminClient();
  // Hapus objek S3 dulu (best-effort) — aset = S3.
  if (table === "music_library") {
    const { data: row } = await a.from("music_library").select("object_key").eq("id", key).maybeSingle();
    const ok = (row as { object_key?: string } | null)?.object_key;
    if (ok) await s3DeleteObject(ok);
  } else if (table === "voice_catalog") {
    await s3DeleteObject(`voice-previews/${key}.mp3`);   // key = voice_key
  }
  const { error } = await a.from(table).delete().eq(def.pk, key);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.delete.${table}`, detail: { key } });
  return NextResponse.json({ ok: true });
}
