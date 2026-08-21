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
  ai_models: { pk: "model_key", cols: ["provider_key", "component", "model_id", "display_name", "quality_tier", "is_active", "sort_order", "cost_hint", "default_params", "pricing", "pricing_locked", "pricing_pending"] },
  ai_providers: { pk: "provider_key", cols: ["display_name", "adapter", "base_url", "auth_type", "key_group", "is_active", "request_param_schema", "price_feed_prefix", "free_tier_note"] },
  content_languages: { pk: "locale", cols: ["display_name", "quality_tier", "caption_font", "is_active", "sort_order", "tts_providers_supported"] },
  // vendor_voice_id = identitas suara di sisi VENDOR (migr 0181). Kosong = sama dgn voice_key.
  // Dipakai penyedia AGREGATOR (fal menyajikan model ElevenLabs yang sama) — voice_key tetap kunci
  // katalog kita yang dirujuk channels & kalibrasi pace, jadi tak boleh diisi ID vendor.
  voice_catalog: { pk: "voice_key", cols: ["provider_key", "vendor_voice_id", "display_name", "locale", "language", "gender", "age", "accent", "use_case", "description", "default_settings", "niche_default", "preview_url", "delivery_wps", "pace_locked", "is_active", "sort_order"] },
  music_library: { pk: "id", cols: ["is_active", "is_default", "name", "mood", "niche", "bpm", "duration_s"] },
  fonts: { pk: "name", cols: ["is_active"] },   // nama/berkas/ass_scale lahir dari berkas saat unggah — bukan ketikan
  // [21-Agu] `adapter` & `display_name` DITAMBAHKAN. Sebelumnya form mengirimnya tapi whitelist ini
  // tak memuatnya ⇒ loop tulis (yang hanya mengiterasi `def.cols`) membuangnya, dan admin tetap
  // melihat toast "Tersimpan". Efek sampingnya: validasi enum `ENUM_COLS.tts_profiles.adapter`
  // di bawah adalah KODE MATI — ia menjaga kolom yang tak pernah sampai. Kini keduanya hidup.
  tts_profiles: { pk: "provider_key", cols: ["display_name", "adapter", "is_active", "delivery_wps", "tts_class", "speed_param", "param_schema", "max_chars_per_request"] },
  moods: { pk: "mood_id", cols: ["keywords", "is_active"] },   // NICHE_DNA F4: kelola mood + keyword deteksi (dwibahasa)
  niche_property_presets: { pk: "id", cols: ["property", "preset_key", "label", "label_en", "description", "description_en", "value", "apply_mode", "sort_order", "is_active"] },
  // Kendali preset durasi (owner 2026-07-06): kolom engine-critical (beats/visual_beats/render_mode)
  // SENGAJA di luar allowlist — hanya status & teks tampilan yang boleh disunting dari UI.
  duration_presets: { pk: "seconds", cols: ["is_active", "is_default", "use_case", "use_case_en", "notes", "trailing_silence_override"] },
};

// Kolom jsonb: nilai string dari form di-JSON.parse agar tersimpan sbg objek (bukan string mentah).
const JSONB_COLS: Record<string, string[]> = {
  voice_catalog: ["default_settings"],
  tts_profiles: ["param_schema"],
  moods: ["keywords"],
  niche_property_presets: ["value"],
  ai_models: ["pricing", "pricing_pending", "default_params", "cost_hint"],
};
// Kolom numerik dengan RESET-ke-NULL + guard rentang (F5-01: voice_catalog.delivery_wps pace per-voice).
const NUMERIC_COLS: Record<string, Record<string, [number, number]>> = {
  voice_catalog: { delivery_wps: [1.0, 4.0], sort_order: [0, 99999] },
  ai_models: { sort_order: [0, 99999] },
  content_languages: { sort_order: [0, 99999] },
  niche_property_presets: { sort_order: [0, 99999] },
  tts_profiles: { delivery_wps: [1.0, 4.0], max_chars_per_request: [200, 100000] },
  // Jeda akhir per-preset (override; NULL = default tenant 2,5s). Rentang statis 0–6s;
  // batas relatif (≤40% durasi preset) ditegakkan tambahan di PATCH (butuh nilai PK=seconds).
  duration_presets: { trailing_silence_override: [0, 6] },
};
// Error tervalidasi ber-KODE (aturan dwibahasa: API kirim kode, FE menerjemahkan ID/EN — bukan kalimat 1 bahasa).
class ValErr extends Error {
  constructor(public code: string, public detail?: Record<string, unknown>) { super(code); }
}
const valErrResponse = (e: unknown, status = 400) =>
  e instanceof ValErr
    ? NextResponse.json({ error: e.code, detail: e.detail ?? null }, { status })
    : NextResponse.json({ error: (e as Error).message }, { status });

/** Galat trigger gerbang kelayakan (migr 0206) → jawaban ber-KODE + daftar kekurangan.
 *  Trigger sengaja mengirim DAFTAR KODE, bukan kalimat: kalimatnya milik FE (dwibahasa ID/EN).
 *  Bukan galat gerbang → null, biar penanganan galat lain tidak berubah sedikit pun. */
const PENANDA_GERBANG = "CATALOG_ACTIVATION_BLOCKED:";
function gerbangResponse(error: { message?: string } | null) {
  const m = error?.message ?? "";
  const i = m.indexOf(PENANDA_GERBANG);
  if (i < 0) return null;
  const kurang = m.slice(i + PENANDA_GERBANG.length).split(",").map((x) => x.trim()).filter(Boolean);
  // 409: syarat belum lengkap — BUKAN 500 (bukan kerusakan) dan bukan 400 (bukan salah ketik admin).
  return NextResponse.json({ error: "activation_blocked", detail: { missing: kurang } }, { status: 409 });
}

function coerceValue(table: string, col: string, val: unknown): unknown {
  // jsonb: string → objek; kosong → undefined (jangan tulis, pakai default DB)
  if (JSONB_COLS[table]?.includes(col)) {
    if (typeof val !== "string") return val;
    const s = val.trim();
    if (s === "") return undefined;
    try { return JSON.parse(s); } catch { throw new ValErr("invalid_json", { col }); }
  }
  // numerik: kosong/null → NULL (admin bisa RESET); else angka + clamp rentang (tolak di luar)
  const range = NUMERIC_COLS[table]?.[col];
  if (range) {
    if (val === null || val === undefined || (typeof val === "string" && val.trim() === "")) return null;
    const n = Number(typeof val === "string" ? val.trim().replace(",", ".") : val); // terima koma desimal ID ("1,0")
    if (!Number.isFinite(n)) throw new ValErr("not_number", { col });
    if (n < range[0] || n > range[1]) throw new ValErr("out_of_range", { col, min: range[0], max: range[1] });
    return n;
  }
  return val;
}

// Kolom ENUM: nilai WAJIB ∈ catalog_valid_values (cermin registry KODE; anti-typo → anti machine-error).
// ai_providers.adapter dibaca jalur LLM (openai_chat/anthropic_messages); providernon-LLM simpan
// identitas TTS/visual → terima union agar tak-menolak data sah + tetap tolak typo. auth_type/component
// & tts_profiles.adapter tervalidasi ketat. Sumber tunggal = tabel cermin (di-sync mesin saat startup).
const ENUM_COLS: Record<string, Record<string, string[]>> = {
  ai_providers:      { adapter: ["llm_adapter", "tts_adapter", "visual_transport"], auth_type: ["auth_type"] },
  ai_models:         { component: ["component"], quality_tier: ["model_tier"] },
  content_languages: { quality_tier: ["language_tier"] },
  voice_catalog:     { gender: ["gender"] },
  tts_profiles:      { adapter: ["tts_adapter"], tts_class: ["tts_class"] },
};

// Validasi nilai enum di `clean` terhadap cermin. Throw Error (pesan jelas) bila di luar daftar sah.
async function assertEnums(a: ReturnType<typeof createAdminClient>, table: string, clean: Record<string, unknown>): Promise<void> {
  const spec = ENUM_COLS[table];
  if (!spec) return;
  const cols = Object.keys(spec).filter((c) => c in clean && clean[c] != null && clean[c] !== "");
  if (cols.length === 0) return;
  const { data } = await a.from("catalog_valid_values").select("field,value");
  const byField = new Map<string, Set<string>>();
  for (const r of (data ?? []) as { field: string; value: string }[]) {
    if (!byField.has(r.field)) byField.set(r.field, new Set());
    byField.get(r.field)!.add(r.value);
  }
  for (const c of cols) {
    const allowed = new Set<string>();
    for (const f of spec[c]) for (const v of byField.get(f) ?? []) allowed.add(v);
    if (!allowed.has(String(clean[c]))) {
      throw new ValErr("invalid_enum", { col: c, value: String(clean[c]), allowed: [...allowed].sort() });
    }
  }
}

// GET semua data katalog (E2 — Phase 10.4-10.7). service_role bypass-RLS.
export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const a = createAdminClient();
  const [ai_models, ai_providers, music_library, content_languages, voice_catalog, tts_profiles, moods, fonts, duration_presets, valid_values, pace_calib, probe_texts, kelayakan] = await Promise.all([
    a.from("ai_models").select("*").order("component").order("sort_order"),
    a.from("ai_providers").select("*").order("provider_key"),
    a.from("music_library").select("id, name, niche, mood, duration_s, bpm, object_key, is_active, is_default, source").order("niche").order("name"),
    a.from("content_languages").select("*").order("sort_order"),
    a.from("voice_catalog").select("*").order("sort_order"),
    a.from("tts_profiles").select("*").order("provider_key"),
    a.from("moods").select("*").order("mood_id"),
    a.from("fonts").select("*").order("name"),
    a.from("duration_presets").select("*").order("seconds"),
    a.from("catalog_valid_values").select("field,value,label").order("field").order("value"),
    // Kalibrasi durasi per-suara (DITULIS MESIN, read-only di layar). Ada karena "config yang bohong":
    // admin mengisi Tempo voice di layar ini, tapi mesin memakai angka HASIL KALIBRASI yang menimpanya —
    // dan angka yang BERLAKU itu tak terlihat di mana pun. Admin jadi menyetel sesuatu yang tak berefek.
    a.from("tts_pace_calibration").select("voice_key,niche,delivery_wps,sec_per_char,sec_per_digit,"
      + "sec_per_sentence,sec_per_comma,sec_per_ellipsis,sec_per_em_dash,chars_per_word,"
      + "words_per_sentence,calib_error_secs,sample_n,updated_at,pause_source,pause_measured_at")
      .eq("niche", "*").order("voice_key"),
    // Teks ALAT UKUR biaya jeda (0185). Read-only di layar: mengubah isinya = mengubah alat ukurnya,
    // jadi ia harus TERLIHAT (janji migrasi 0185) tapi tidak diubah tanpa sengaja.
    a.from("duration_probe_texts").select("lang,idx,clauses,is_active").order("lang").order("idx"),
    // Kelayakan SELURUH baris katalog dalam SEKALI jalan (migr 0206 `catalog_missing_all`).
    // Gunanya MENCEGAH: admin melihat apa yang kurang sebelum menyentuh saklar. Fail-soft —
    // ini keterangan, bukan jalur kerja; gagal baca tak boleh membuat panel gelap.
    a.rpc("catalog_missing_all"),
  ]);
  // public_url musik (S3) untuk tombol Play di catalog. voice_catalog sudah simpan preview_url.
  const music = (music_library.data ?? []).map((m) => ({
    ...m, public_url: (m as { object_key?: string }).object_key ? publicUrl((m as { object_key?: string }).object_key!) : null,
  }));
  return NextResponse.json({
    ai_models: ai_models.data ?? [], ai_providers: ai_providers.data ?? [],
    music_library: music, content_languages: content_languages.data ?? [],
    voice_catalog: voice_catalog.data ?? [], tts_profiles: tts_profiles.data ?? [],
    moods: moods.data ?? [], duration_presets: duration_presets.data ?? [],
    fonts: fonts.data ?? [],
    catalog_valid_values: valid_values.data ?? [],
    tts_pace_calibration: pace_calib.data ?? [],
    duration_probe_texts: probe_texts.data ?? [],
    catalog_missing: kelayakan.data ?? {},
  });
}

// PATCH: { table, key, patch } — update baris katalog (whitelist tabel+kolom). + admin_audit.
/** Channel AKTIF yang masih menunjuk baris katalog ini. Dipakai untuk memperlihatkan DAMPAK
 *  sebelum admin mematikannya (17-Agu: 4 channel berhenti 4 hari tanpa ada yang tahu).
 *  Hanya membaca; nol perubahan. Gagal baca → daftar kosong (jangan menghalangi admin karena
 *  hiasan yang gagal dibaca). */
async function channelTerdampak(a: ReturnType<typeof createAdminClient>, table: string, key: string) {
  try {
    const { data } = await a.from("channels")
      .select("channel_name, llm_model, tts_model, voice_key, visual_mode, tts_provider, llm_library")
      .eq("is_active", true);
    const rows = (data ?? []) as Record<string, string | null>[];
    return rows.filter((c) => {
      const vModel = (c.visual_mode ?? "").includes(":") ? (c.visual_mode ?? "").split(":")[1] : null;
      if (table === "ai_models") return c.llm_model === key || c.tts_model === key || vModel === key;
      if (table === "voice_catalog") return c.voice_key === key;
      // penyedia / mesin suara: channel terdampak bila slotnya memakai penyedia itu
      return c.tts_provider === key || c.llm_library === key;
    }).map((c) => c.channel_name || "(tanpa nama)");
  } catch { return [] as string[]; }
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { table, key, patch } = await req.json().catch(() => ({}));
  const def = CATALOG[table];
  if (!def) return NextResponse.json({ error: "table_not_allowed" }, { status: 400 });
  const clean: Record<string, unknown> = {};
  try {
    for (const c of def.cols) if (patch && c in patch) { const v = coerceValue(table, c, patch[c]); if (v !== undefined) clean[c] = v; }
  } catch (e) { return valErrResponse(e); }
  if (Object.keys(clean).length === 0) return NextResponse.json({ error: "no_editable_fields" }, { status: 400 });
  // Guard relatif jeda-akhir (anti-human-error §3.1, lapis server): override > 40% durasi preset
  // = jendela narasi rusak → tolak jelas. (Lapis FE menolak lebih dini dgn pratinjau dampak.)
  if (table === "duration_presets" && clean.trailing_silence_override != null) {
    const secs = Number(key);
    const maxRel = Number.isFinite(secs) ? Math.round(secs * 0.4 * 10) / 10 : 6;
    if (Number(clean.trailing_silence_override) > maxRel) {
      return valErrResponse(new ValErr("out_of_range", { col: "trailing_silence_override", min: 0, max: maxRel }));
    }
  }
  const a = createAdminClient();
  try { await assertEnums(a, table, clean); } catch (e) { return valErrResponse(e); }

  // ── DAMPAK MEMATIKAN BARIS KATALOG — terlihat SEBELUM tombol ditekan (AI_ERROR_MGMT §9b) ────
  // 17-Agu: model `llama-3.3-70b-versatile` dimatikan (benar — vendor memang mematikannya), tapi
  // saklar itu berpindah TANPA SUARA. Tidak ada yang memberi tahu bahwa 3 channel tenant masih
  // memakainya. Mereka berhenti, dan tak seorang pun tahu selama 4 HARI — dua di antaranya tenant
  // BERBAYAR langganan aktif.
  // Ini BUKAN penolakan: kalau vendor mematikan model, admin WAJIB tetap bisa mematikannya —
  // blokir keras = "kunci tanpa jalur buka" (sudah ditegur owner, PAYMENT §10e-2). Yang berubah
  // hanya satu: akibatnya terlihat sebelum bertindak, bukan empat hari sesudahnya.
  // Dikirim HANYA saat is_active berubah menjadi TIDAK aktif (nol biaya untuk perubahan lain).
  if ((table === "ai_models" || table === "ai_providers" || table === "voice_catalog" || table === "tts_profiles")
      && "is_active" in clean && clean.is_active === false && !req.headers.get("x-konfirmasi-dampak")) {
    const terdampak = await channelTerdampak(a, table, String(key));
    if (terdampak.length > 0) {
      return NextResponse.json({ perlu_konfirmasi: true, dipakai: terdampak }, { status: 200 });
    }
  }

  const { data, error } = await a.from(table).update(clean).eq(def.pk, key).select("*").single();
  if (error) {
    // Gerbang kelayakan menahan penyalaan → kode + daftar kekurangan, bukan pesan mentah Postgres.
    const gerbang = gerbangResponse(error);
    if (gerbang) return gerbang;
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
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
  if (!row?.[def.pk]) return NextResponse.json({ error: "pk_required", detail: { col: def.pk } }, { status: 400 });
  const clean: Record<string, unknown> = { [def.pk]: row[def.pk] };
  try {
    for (const c of def.cols) if (c in row) { const v = coerceValue(table, c, row[c]); if (v !== undefined) clean[c] = v; }
  } catch (e) { return valErrResponse(e); }
  // ── LAHIR NONAKTIF (rencana 6c-4) ──────────────────────────────────────────────────────────
  // Dulu `is_active` tak pernah disetel di sini ⇒ mengikuti bawaan DB, dan bawaan itu `true`
  // (terukur: 0014_tts_profiles.sql:13 · 0038_voice_catalog.sql:12). Akibatnya penyedia/model
  // yang BELUM diuji langsung ditawarkan ke tenant. Ditulis EKSPLISIT — bawaan DB (yang untuk
  // `ai_models`/`ai_providers` tak bisa diintrospeksi lewat klien) jadi tak relevan, bukan
  // diasumsikan. Menyalakannya = langkah TERPISAH yang melewati gerbang kelayakan (migr 0206).
  if (CATALOG[table].cols.includes("is_active")) clean.is_active = false;
  const a = createAdminClient();
  try { await assertEnums(a, table, clean); } catch (e) { return valErrResponse(e); }
  // A3 anti-bingung: ID (PK) sudah terpakai → 409 kode 'duplicate_key' (bukan error mentah Postgres 500).
  const { data: dup } = await a.from(table).select(def.pk).eq(def.pk, row[def.pk]).limit(1).maybeSingle();
  if (dup) return NextResponse.json({ error: "duplicate_key", detail: { col: def.pk, value: String(row[def.pk]) } }, { status: 409 });
  const { data, error } = await a.from(table).insert(clean).select("*").single();
  if (error) {
    if ((error as { code?: string }).code === "23505")  // race: unique violation → tetap 409 ramah
      return NextResponse.json({ error: "duplicate_key", detail: { col: def.pk, value: String(row[def.pk]) } }, { status: 409 });
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.create.${table}`, detail: { key: row[def.pk] } });
  return NextResponse.json({ ok: true, row: data });
}

// DELETE: { table, key } — hapus baris ASET + objek S3-nya. HANYA tabel aset (music_library, voice_catalog).
const DELETABLE = new Set(["music_library", "voice_catalog", "ai_models", "ai_providers", "content_languages", "tts_profiles", "moods", "fonts"]);

// Guard referensi (owner 2026-07-06): entitas katalog yang SEDANG DIPAKAI tak boleh terhapus —
// ditolak ber-alasan (409), bukan merusak channel/niche yang merujuknya.
async function refGuard(a: ReturnType<typeof createAdminClient>, table: string, key: string): Promise<string | null> {
  const cnt = async (q: PromiseLike<{ count: number | null }>) => ((await q).count ?? 0);
  if (table === "ai_models") {
    const n = await cnt(a.from("channels").select("id", { count: "exact", head: true })
      .or(`llm_model.eq.${key},tts_model.eq.${key},visual_mode.eq.ai_image:${key},visual_mode.eq.ai_video:${key}`));
    if (n > 0) return `dipakai ${n} channel — nonaktifkan saja, jangan hapus`;
  }
  if (table === "ai_providers") {
    const m = await cnt(a.from("ai_models").select("model_key", { count: "exact", head: true }).eq("provider_key", key));
    if (m > 0) return `punya ${m} model — hapus/pindahkan modelnya dulu`;
    const n = await cnt(a.from("channels").select("id", { count: "exact", head: true }).or(`llm_library.eq.${key},tts_provider.eq.${key}`));
    if (n > 0) return `dipakai ${n} channel`;
  }
  if (table === "content_languages") {
    const n = await cnt(a.from("channels").select("id", { count: "exact", head: true }).eq("content_language", key));
    if (n > 0) return `dipakai ${n} channel`;
  }
  if (table === "tts_profiles") {
    const n = await cnt(a.from("channels").select("id", { count: "exact", head: true }).eq("tts_provider", key));
    if (n > 0) return `dipakai ${n} channel`;
    const v = await cnt(a.from("voice_catalog").select("voice_key", { count: "exact", head: true }).eq("provider_key", key));
    if (v > 0) return `punya ${v} voice — hapus voice-nya dulu`;
  }
  if (table === "fonts") {
    // Anton = jaring pengaman mesin render (_resolve_font_path jatuh ke sini bila font lain hilang).
    if (key === "Anton") return "font cadangan sistem — tak boleh dihapus";
    const n = await cnt(a.from("channels").select("id", { count: "exact", head: true })
      .or(`caption_style->>font_name.eq.${key},hook_title_style->>font_name.eq.${key}`));
    if (n > 0) return `dipakai ${n} channel — nonaktifkan saja, jangan hapus`;
    const t = await cnt(a.from("tenant_configs").select("tenant_id", { count: "exact", head: true })
      .or(`caption_style->>font_name.eq.${key},hook_title_style->>font_name.eq.${key}`));
    if (t > 0) return `dipakai ${t} pengaturan tenant`;
  }
  if (table === "moods") {
    const n = await cnt(a.from("music_library").select("id", { count: "exact", head: true }).eq("mood", key));
    if (n > 0) return `dipakai ${n} track musik`;
    const z = await cnt(a.from("niches").select("niche_id", { count: "exact", head: true }).contains("mood_priority", JSON.stringify([key])));
    if (z > 0) return `dipakai ${z} niche (mood_priority)`;
  }
  return null;
}
export async function DELETE(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { table, key } = await req.json().catch(() => ({}));
  const def = CATALOG[table];
  if (!def || !DELETABLE.has(table)) return NextResponse.json({ error: "delete_not_allowed" }, { status: 400 });
  if (!key && key !== 0) return NextResponse.json({ error: "key wajib" }, { status: 400 });
  const a = createAdminClient();
  const blocked = await refGuard(a, table, String(key));
  if (blocked) return NextResponse.json({ error: `masih dirujuk: ${blocked}` }, { status: 409 });
  // Hapus objek S3 dulu (best-effort) — aset = S3.
  if (table === "music_library") {
    const { data: row } = await a.from("music_library").select("object_key").eq("id", key).maybeSingle();
    const ok = (row as { object_key?: string } | null)?.object_key;
    if (ok) await s3DeleteObject(ok);
  } else if (table === "voice_catalog") {
    await s3DeleteObject(`voice-previews/${key}.mp3`);   // key = voice_key
  } else if (table === "fonts") {
    const { data: row } = await a.from("fonts").select("file_name").eq("name", key).maybeSingle();
    const fn = (row as { file_name?: string } | null)?.file_name;
    if (fn) await s3DeleteObject(`fonts/${fn}`);
  }
  const { error } = await a.from(table).delete().eq(def.pk, key);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await a.from("admin_audit").insert({ admin_uid: g.user.id, action: `catalog.delete.${table}`, detail: { key } });
  return NextResponse.json({ ok: true });
}
