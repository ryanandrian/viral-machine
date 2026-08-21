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
  // [22-Agu B4] `display_name` & `adapter` DITAMBAHKAN. Sebelumnya form mengirim keduanya tapi
  // whitelist ini tak memuatnya ⇒ loop tulis (yang hanya mengiterasi `def.cols`) membuangnya, dan
  // admin tetap melihat toast "Tersimpan". Efek ikutan: validasi enum `ENUM_COLS.tts_profiles.adapter`
  // di bawah adalah KODE MATI — ia menjaga kolom yang tak pernah sampai. Kini keduanya hidup.
  tts_profiles: { pk: "provider_key", cols: ["display_name", "adapter", "is_active", "delivery_wps", "tts_class", "speed_param", "max_chars_per_request", "param_schema"] },
  moods: { pk: "mood_id", cols: ["keywords", "is_active"] },   // NICHE_DNA F4: kelola mood + keyword deteksi (dwibahasa)
  niche_property_presets: { pk: "id", cols: ["property", "preset_key", "label", "label_en", "description", "description_en", "value", "apply_mode", "sort_order", "is_active"] },
  // Kendali preset durasi (owner 2026-07-06): kolom engine-critical (beats/visual_beats/render_mode)
  // SENGAJA di luar allowlist — hanya status & teks tampilan yang boleh disunting dari UI.
  duration_presets: { pk: "seconds", cols: ["is_active", "is_default", "use_case", "use_case_en", "notes", "trailing_silence_override"] },
};

// Kolom jsonb: nilai string dari form di-JSON.parse agar tersimpan sbg objek (bukan string mentah).
const JSONB_COLS: Record<string, string[]> = {
  // [22-Agu F2] `ai_providers.request_param_schema` DIBACA mesin saat membangun penyedia naskah,
  // tapi tak ada jalur mengisinya dari panel ⇒ objek terwiring separuh. Kini bisa diisi, dan
  // WAJIB diurai di sini: tanpa penguraian, teks admin tersimpan sebagai string mentah, mesin
  // membacanya sebagai objek kosong, dan tak seorang pun diberi tahu — gagal SENYAP.
  ai_providers: ["request_param_schema"],
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

/** Galat trigger "aktif wajib terbukti" (migr 0208) → jawaban ber-KODE, bukan pesan mentah DB.
 *  Sebabnya dua, dan keduanya perlu kalimat berbeda di layar:
 *    belum_lulus_uji                → model belum pernah lulus uji sama sekali
 *    uji_lebih_tua_dari_kematian    → PERNAH lulus, tapi ujinya lebih tua dari bukti kematiannya
 *                                     (kasus `gemini-2.5-flash`: lulus 6-Jul, mati 18-Agu) */
const PENANDA_TERBUKTI = "MODEL_BELUM_TERBUKTI:";
function terbuktiResponse(error: { message?: string } | null) {
  const m = error?.message ?? "";
  const i = m.indexOf(PENANDA_TERBUKTI);
  if (i < 0) return null;
  const sebab = m.slice(i + PENANDA_TERBUKTI.length).trim().split(/\s/)[0] || "belum_lulus_uji";
  // 409: syaratnya belum terpenuhi — bukan kerusakan (500), bukan salah ketik (400).
  return NextResponse.json({ error: "belum_terbukti", detail: { sebab } }, { status: 409 });
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
  const [ai_models, ai_providers, music_library, content_languages, voice_catalog, tts_profiles, moods, fonts, duration_presets, valid_values, pace_calib, probe_texts, chSlot] = await Promise.all([
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
    // [22-Agu G1] Slot AI tiap channel — dipakai menghitung "dipakai berapa channel" per baris
    // katalog. SATU kueri (13 baris hari ini), bukan satu kueri per model. Sampai 22-Agu admin
    // baru tahu dampaknya pada DETIK ia mematikan model; angkanya bisa diketahui sebelum itu.
    a.from("channels").select("is_active, llm_model, tts_model, voice_key, visual_mode, tts_provider, llm_library, content_language"),
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
    // {tabel: {kunci: {total, aktif}}} — dihitung di server sekali, dipakai layar tanpa kueri lagi.
    catalog_pemakaian: hitungPemakaian((chSlot.data ?? []) as Record<string, string | boolean | null>[]),
  });
}

/** Hitung "dipakai berapa channel" untuk SETIAP baris katalog, dari satu potret slot channel.
 *  Logikanya SAMA dengan `channelPemakai` (satu-satunya sumber kebenaran untuk pertanyaan itu);
 *  di sini ia dijalankan sekali untuk semua kunci sekaligus, bukan per baris. */
function hitungPemakaian(rows: Record<string, string | boolean | null>[]) {
  const out: Record<string, Record<string, { total: number; aktif: number }>> = {
    ai_models: {}, ai_providers: {}, tts_profiles: {}, voice_catalog: {}, content_languages: {},
  };
  const tambah = (tabel: string, kunci: string | null, aktif: boolean) => {
    if (!kunci) return;
    const t = (out[tabel][kunci] ??= { total: 0, aktif: 0 });
    t.total += 1;
    if (aktif) t.aktif += 1;
  };
  for (const c of rows) {
    const aktif = c.is_active === true;
    const vm = String(c.visual_mode ?? "");
    const vModel = vm.includes(":") ? vm.split(":")[1] : null;
    tambah("ai_models", String(c.llm_model ?? "") || null, aktif);
    tambah("ai_models", String(c.tts_model ?? "") || null, aktif);
    tambah("ai_models", vModel, aktif);
    tambah("voice_catalog", String(c.voice_key ?? "") || null, aktif);
    tambah("content_languages", String(c.content_language ?? "") || null, aktif);
    tambah("ai_providers", String(c.llm_library ?? "") || null, aktif);
    tambah("ai_providers", String(c.tts_provider ?? "") || null, aktif);
    tambah("tts_profiles", String(c.tts_provider ?? "") || null, aktif);
  }
  return out;
}

// PATCH: { table, key, patch } — update baris katalog (whitelist tabel+kolom). + admin_audit.
/** Channel yang menunjuk baris katalog ini — SATU-SATUNYA penghitung untuk pertanyaan itu.
 *
 *  [22-Agu F3] Sebelumnya pertanyaan yang sama dijawab DUA tempat: `refGuard` (jalur HAPUS) dan
 *  `channelTerdampak` (jalur MATIKAN, dibuat 21-Agu). Dua sumber kebenaran untuk satu pertanyaan =
 *  lapis ganda; kalau salah satu diperbaiki dan yang lain lupa, angka yang dilihat admin berbeda
 *  dari kenyataan. Kini satu fungsi, dua pemakai.
 *
 *  `hanyaAktif` adalah perbedaan yang SAH antara keduanya, bukan kelalaian:
 *    · MEMATIKAN → hanya channel AKTIF (yang jeda/mati tak berhenti produksi karena ini)
 *    · MENGHAPUS → SEMUA channel (baris yang dirujuk channel mana pun tak boleh hilang)
 *  Hanya membaca; nol perubahan. Gagal baca → daftar kosong pada jalur MATIKAN (hiasan yang gagal
 *  dibaca tak boleh menghalangi admin) — jalur HAPUS menanganinya sendiri (lihat `refGuard`). */
async function channelPemakai(a: ReturnType<typeof createAdminClient>, table: string, key: string,
                              hanyaAktif = false): Promise<string[]> {
  let q = a.from("channels")
    .select("channel_name, is_active, llm_model, tts_model, voice_key, visual_mode, tts_provider, llm_library, content_language");
  if (hanyaAktif) q = q.eq("is_active", true);
  const { data, error } = await q;
  if (error) throw error;
  const rows = (data ?? []) as Record<string, string | null>[];
  return rows.filter((c) => {
    const vModel = (c.visual_mode ?? "").includes(":") ? (c.visual_mode ?? "").split(":")[1] : null;
    if (table === "ai_models") return c.llm_model === key || c.tts_model === key || vModel === key;
    if (table === "voice_catalog") return c.voice_key === key;
    if (table === "content_languages") return c.content_language === key;
    // penyedia / mesin suara: channel terdampak bila slotnya memakai penyedia itu
    return c.tts_provider === key || c.llm_library === key;
  }).map((c) => c.channel_name || "(tanpa nama)");
}

/** Jalur MEMATIKAN: channel AKTIF yang masih memakainya, untuk memperlihatkan DAMPAK sebelum
 *  saklar berpindah (17-Agu: 4 channel berhenti 4 hari tanpa ada yang tahu). Fail-soft. */
async function channelTerdampak(a: ReturnType<typeof createAdminClient>, table: string, key: string) {
  try { return await channelPemakai(a, table, key, true); } catch { return [] as string[]; }
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

  // ── [22-Agu B5] MENYALAKAN MODEL = MEMBERSIHKAN JEJAK KARANTINA ───────────────────────────
  // Migr 0205 menulis sendiri: "Ditulis mesin; dibersihkan admin saat menghidupkan kembali."
  // Sampai 22-Agu janji itu TIDAK ADA jalurnya: panel tak bisa menyentuh kedua kolom, jadi jejak
  // melekat selamanya dan model hidup tetap bertanda "mati di vendor" — kunci tanpa jalur buka
  // (sudah ditegur owner, PAYMENT §10e-2). Ini melunasi hutang itu, bukan fitur baru.
  // HANYA saat is_active → true: karantina MENULIS jejak ketika mematikan, jadi membersihkannya di
  // jalur mati akan menghapus bukti yang baru saja ditulis mesin.
  // Kedua kolom sengaja TIDAK masuk whitelist: jejak adalah tulisan MESIN, admin tak boleh mengarangnya.
  // [22-Agu G5] KOREKSI B5. Versi pertama membersihkan jejak hanya karena model DINYALAKAN — jadi
  // bukti kematian hilang tanpa satu pun uji yang membuktikan model hidup lagi. Itu terjadi pada
  // `gemini-2.5-flash` beberapa jam setelah B5 dipasang: jejaknya terhapus, lencana "✓ Teruji"
  // (dari 6 Juli) tetap tampil, dan tak ada apa pun yang mengingatkan admin.
  // Sekarang: jejak dibersihkan HANYA bila ada uji yang LEBIH BARU daripada jejak itu — yakni
  // bukti bahwa model benar-benar hidup kembali. Kalau tidak, jejaknya DIBIARKAN (dan trigger 0208
  // menahan penyalaannya sampai admin menekan Uji).
  if (table === "ai_models" && "is_active" in clean && clean.is_active === true) {
    const { data: baris } = await a.from("ai_models")
      .select("cost_hint, unavailable_since").eq("model_key", key).maybeSingle();
    const r = baris as { cost_hint?: { audit?: string } | null; unavailable_since?: string | null } | null;
    const audit = r?.cost_hint?.audit ?? "";
    const mati = r?.unavailable_since ?? null;
    const tglUji = /\d{4}-\d{2}-\d{2}/.exec(audit)?.[0] ?? null;
    const ujiLebihBaru = !!(tglUji && mati && new Date(tglUji) >= new Date(mati));
    if (!mati || ujiLebihBaru) {
      clean.unavailable_since = null;
      clean.unavailable_reason = null;
    }
  }

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
    // Gerbang "aktif wajib terbukti" (0208) menahan penyalaan → kode, bukan pesan mentah Postgres.
    const terbukti = terbuktiResponse(error);
    if (terbukti) return terbukti;
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

  // ── [22-Agu B6] MODEL SUARA BARU → SIAPKAN BARIS SETELAN SUARANYA ─────────────────────────
  // `tts_profiles` adalah SATU-SATUNYA tabel yang boleh dihapus dari panel tapi tak bisa dibuat
  // darinya. Itu sebab mesin suara Gemini dulu lahir dari SKRIP, bukan dari layar owner.
  // Rancangan 21-Agu (tombol Tambah baru di tab Voice) DITOLAK owner: "anda membuat jalur baru."
  // Rancangan ini: barisnya lahir dari langkah yang admin SUDAH lakukan — membuat model
  // ber-`component='tts'` (langkah 2 koridor ARSITEKTUR_AI_PROVIDER_MODEL §9.1). Nol tombol,
  // nol tab, nol berkas layar tersentuh; melengkapinya memakai editor ✎ yang SUDAH ADA.
  // LAHIR NONAKTIF: layar tenant menyaring `tts_profiles.is_active` ⇒ baris ini tak terlihat
  // tenant sampai admin melengkapi protokolnya dan menyalakannya.
  // TIDAK MENIMPA: baris yang sudah ada dibiarkan apa adanya — tempo/kelas/batas huruf di sana
  // sudah dipakai produksi.
  // FAIL-SOFT: ini kemudahan, bukan jalur kerja. Kegagalannya HARAM membatalkan pembuatan model
  // yang sudah benar.
  if (table === "ai_models" && String(clean.component ?? "") === "tts") {
    try {
      const pk = String(clean.provider_key ?? "");
      const { data: sudahAda } = await a.from("tts_profiles").select("provider_key").eq("provider_key", pk).maybeSingle();
      if (pk && !sudahAda) {
        const { data: prov } = await a.from("ai_providers").select("display_name").eq("provider_key", pk).maybeSingle();
        await a.from("tts_profiles").insert({
          provider_key: pk,
          display_name: (prov as { display_name?: string } | null)?.display_name ?? pk,
          adapter: null,               // WAJIB diisi admin lewat ✎ — protokol tak boleh ditebak sistem
          tts_class: "fast_fallback",  // paling konservatif: tanpa klaim timestamp presisi
          delivery_wps: 2.4,           // angka jatuh-senyap yang sudah jadi bawaan mesin (bukan angka baru)
          is_active: false,
        });
      }
    } catch (e) {
      console.warn("[catalog] siapkan tts_profiles gagal — non-fatal:", (e as Error)?.message);
    }
  }
  return NextResponse.json({ ok: true, row: data });
}

// DELETE: { table, key } — hapus baris ASET + objek S3-nya. HANYA tabel aset (music_library, voice_catalog).
const DELETABLE = new Set(["music_library", "voice_catalog", "ai_models", "ai_providers", "content_languages", "tts_profiles", "moods", "fonts"]);

// Guard referensi (owner 2026-07-06): entitas katalog yang SEDANG DIPAKAI tak boleh terhapus —
// ditolak ber-alasan (409), bukan merusak channel/niche yang merujuknya.
async function refGuard(a: ReturnType<typeof createAdminClient>, table: string, key: string): Promise<string | null> {
  const cnt = async (q: PromiseLike<{ count: number | null }>) => ((await q).count ?? 0);
  // [22-Agu F3] Bagian "channel yang memakai" memakai penghitung BERSAMA `channelPemakai`
  // (SEMUA channel — beda dari jalur mematikan yang hanya peduli channel aktif). Sisa pemeriksaan
  // per-tabel di bawah TIDAK disentuh: ia menanyakan hal LAIN (jumlah model, voice, track musik,
  // niche, pengaturan tenant), bukan channel.
  // Gagal baca di sini HARAM diam-diam meloloskan hapus: kalau daftar pemakai tak terbaca, kita
  // TAHAN dengan alasan jelas, bukan menganggap "tidak ada yang memakainya".
  const pemakaiChannel = async (): Promise<string[]> => {
    try { return await channelPemakai(a, table, key); }
    catch { throw new Error("daftar channel pemakai gagal dibaca — hapus ditahan demi keamanan"); }
  };
  if (table === "ai_models") {
    const n = (await pemakaiChannel()).length;
    if (n > 0) return `dipakai ${n} channel — nonaktifkan saja, jangan hapus`;
  }
  if (table === "ai_providers") {
    const m = await cnt(a.from("ai_models").select("model_key", { count: "exact", head: true }).eq("provider_key", key));
    if (m > 0) return `punya ${m} model — hapus/pindahkan modelnya dulu`;
    const n = (await pemakaiChannel()).length;
    if (n > 0) return `dipakai ${n} channel`;
  }
  // [22-Agu F5] BUG yang ditemukan saat menyatukan penghitung: `voice_catalog` ADA di DELETABLE
  // tapi tak punya penjaga di sini ⇒ karakter suara yang sedang dipakai channel tenant BISA
  // TERHAPUS, dan channel itu langsung menggantung tanpa peringatan apa pun. Terukur saat
  // ditemukan: 6 channel memakai suara, 3 di antaranya AKTIF. Pola penolakannya mengikuti
  // `ai_models` yang sudah ada: tolak + sarankan nonaktifkan, jangan menjebak admin.
  if (table === "voice_catalog") {
    const n = (await pemakaiChannel()).length;
    if (n > 0) return `dipakai ${n} channel — nonaktifkan saja, jangan hapus`;
  }
  if (table === "content_languages") {
    const n = (await pemakaiChannel()).length;
    if (n > 0) return `dipakai ${n} channel`;
  }
  if (table === "tts_profiles") {
    const n = (await pemakaiChannel()).length;
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
