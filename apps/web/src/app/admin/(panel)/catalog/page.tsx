"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { Plus, Target, ArrowRight, X, Trash2, AlertTriangle } from "lucide-react";
import PresetTables from "@/components/preset-tables";
import "./catalog.css";

// E2 Admin Catalog (Phase 10.4-10.7) — DATA NYATA via /api/admin/catalog (service_role).
// Tab: AI Models · Providers · Music · Voice · Languages · Niche(link). Toggle active + add (whitelisted). Prefix cat-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Cat = {
  ai_models: Record<string, unknown>[]; ai_providers: Record<string, unknown>[]; music_library: Record<string, unknown>[];
  content_languages: Record<string, unknown>[]; voice_catalog: Record<string, unknown>[]; tts_profiles: Record<string, unknown>[];
  duration_presets: Record<string, unknown>[];
  moods: Record<string, unknown>[];
  fonts: Record<string, unknown>[];
  catalog_valid_values?: { field: string; value: string; label: string }[];
  // Kalibrasi durasi per-suara — DITULIS MESIN, read-only di sini. Ada karena "config yang bohong":
  // admin mengisi "Pace voice" tapi mesin memakai angka kalibrasi yang MENIMPANYA, dan angka yang
  // BERLAKU tak terlihat di mana pun → admin menyetel sesuatu yang tak berefek tanpa tahu.
  tts_pace_calibration?: { voice_key: string; delivery_wps: number | null; sec_per_char: number | null;
    sec_per_sentence: number | null; sec_per_comma: number | null; sec_per_ellipsis: number | null;
    sec_per_em_dash: number | null; sec_per_digit: number | null;
    chars_per_word: number | null; words_per_sentence: number | null;
    calib_error_secs: number | null; sample_n: number | null; updated_at?: string;
    pause_source?: string | null; pause_measured_at?: string | null }[];
  // Teks ALAT UKUR biaya jeda (0185) — read-only; mengubah isinya = mengubah alat ukurnya.
  duration_probe_texts?: { lang: string; idx: number; clauses: string[]; is_active: boolean }[];
};

// Kolom yang WAJIB dropdown (nilai-sah dari registry KODE via catalog_valid_values) — anti-typo.
// Sinkron dgn ENUM_COLS di api/admin/catalog/route.ts (validasi server sbg backstop).
const ENUM_FIELD_SRC: Record<string, Record<string, string[]>> = {
  providers: { adapter: ["llm_adapter", "tts_adapter", "visual_transport"], auth_type: ["auth_type"] },
  models: { component: ["component"], quality_tier: ["model_tier"] },
  languages: { quality_tier: ["language_tier"] },
  voice: { gender: ["gender"] },
  ttsprof: { adapter: ["tts_adapter"], tts_class: ["tts_class"] },
};

// A1/A2 (owner 2026-07-08): label MANUSIAWI dwibahasa + bantuan/contoh per field — nama kolom DB tampil
// kecil sbg referensi teknis, bukan jadi label. Field tanpa entri → pakai label lama (fallback).
const FIELD_META: Record<string, Record<string, { id: string; en: string; help_id?: string; help_en?: string }>> = {
  providers: {
    provider_key: { id: "ID Penyedia", en: "Provider ID", help_id: "Huruf kecil tanpa spasi, permanen. Contoh: openai, groq", help_en: "Lowercase, no spaces, permanent. E.g.: openai, groq" },
    display_name: { id: "Nama tampil", en: "Display name", help_id: "Nama yang dilihat admin & tenant. Contoh: OpenAI GPT", help_en: "Shown to admins & tenants. E.g.: OpenAI GPT" },
    adapter: { id: "Protokol koneksi", en: "Connection protocol", help_id: "Cara mesin bicara ke vendor — pilih dari daftar yang didukung kode.", help_en: "How the engine talks to the vendor — pick from code-supported list." },
    auth_type: { id: "Cara autentikasi", en: "Auth method", help_id: "api_key = perlu token · none = gratis tanpa kunci (mis. edge_tts)", help_en: "api_key = token required · none = free, no key (e.g. edge_tts)" },
    key_group: { id: "Kelompok kunci (vendor)", en: "Key group (vendor)", help_id: "Vendor pemilik kunci — 1 kunci dipakai semua elemennya. Contoh: openai_tts → openai", help_en: "Key-owning vendor — one key serves all its elements. E.g.: openai_tts → openai" },
    base_url: { id: "Alamat API (opsional)", en: "API base URL (optional)", help_id: "Hanya untuk vendor OpenAI-compatible. Contoh: https://api.groq.com/openai/v1", help_en: "Only for OpenAI-compatible vendors. E.g.: https://api.groq.com/openai/v1" },
    price_feed_prefix: { id: "Prefix sumber harga", en: "Price feed prefix", help_id: "Nama vendor di feed harga bila beda dari ID. Contoh: openai_tts → openai", help_en: "Vendor name in the price feed when it differs. E.g.: openai_tts → openai" },
    free_tier_note: { id: "Catatan gratis harian", en: "Free tier note", help_id: "Tampil ke tenant bila vendor memberi kuota gratis. Kosongkan bila tidak ada.", help_en: "Shown to tenants when the vendor has a free quota. Leave empty otherwise." },
  },
  models: {
    provider_key: { id: "Penyedia (induk)", en: "Provider (parent)" },
    component: { id: "Jenis model", en: "Model type", help_id: "llm = penulis naskah · tts = suara · image/video = visual", help_en: "llm = script writer · tts = voice · image/video = visuals" },
    model_key: { id: "ID internal", en: "Internal ID", help_id: "Kunci unik di katalog kita, permanen. Contoh: gpt-4o-mini", help_en: "Unique key in our catalog, permanent. E.g.: gpt-4o-mini" },
    model_id: { id: "ID resmi di vendor", en: "Vendor model ID", help_id: "Salin PERSIS dari dokumentasi vendor (sertakan versi). Contoh: FLUX.1-schnell. Salah ketik = gagal produksi — buktikan dgn tombol Uji.", help_en: "Copy EXACTLY from vendor docs (include version). Typos fail production — prove with the Test button." },
    display_name: { id: "Nama tampil", en: "Display name", help_id: "Jelas versinya untuk manusia. Contoh: GPT-4o mini", help_en: "Human-clear incl. version. E.g.: GPT-4o mini" },
    quality_tier: { id: "Tingkat kualitas", en: "Quality tier", help_id: "Dipakai tenant memilih sesuai budget: basic/standard/premium/fast", help_en: "Used by tenants to pick per budget: basic/standard/premium/fast" },
    sort_order: { id: "Urutan tampil", en: "Sort order", help_id: "Angka kecil tampil lebih dulu di pemilih tenant.", help_en: "Smaller numbers appear first in tenant pickers." },
  },
  ttsprof: {
    provider_key: { id: "ID Penyedia", en: "Provider ID" },
    display_name: { id: "Nama tampil", en: "Display name" },
    adapter: { id: "Protokol TTS", en: "TTS protocol", help_id: "Pilih dari daftar yang didukung kode.", help_en: "Pick from code-supported list." },
    tts_class: { id: "Kelas timing", en: "Timing class", help_id: "timed = ada word-timestamp (caption karaoke presisi) · fast_fallback = tanpa timestamp presisi", help_en: "timed = word timestamps (precise karaoke captions) · fast_fallback = no precise timestamps" },
    delivery_wps: { id: "Tempo dasar (kata/detik)", en: "Base pace (words/sec)", help_id: "Dipakai menghitung panjang naskah. Rentang 1.0–4.0.", help_en: "Used for script length budgeting. Range 1.0–4.0." },
    speed_param: { id: "Nama parameter kecepatan", en: "Speed param name", help_id: "speed / rate — kosongkan bila vendor tak punya.", help_en: "speed / rate — empty if unsupported." },
    param_schema: { id: "Skema parameter (JSON)", en: "Param schema (JSON)" },
  },
  languages: {
    locale: { id: "Kode bahasa", en: "Locale code", help_id: "Format BCP-47. Contoh: id-ID", help_en: "BCP-47 format. E.g.: id-ID" },
    display_name: { id: "Nama tampil", en: "Display name" },
    quality_tier: { id: "Status dukungan", en: "Support status", help_id: "official = teruji penuh · experimental = coba-coba", help_en: "official = fully tested · experimental = trial" },
    caption_font: { id: "Font caption", en: "Caption font" },
  },
  voice: {
    voice_key: { id: "ID Voice (dari vendor)", en: "Voice ID (from vendor)", help_id: "Salin persis voice_id milik vendor.", help_en: "Copy the vendor's voice_id exactly." },
    provider_key: { id: "Penyedia", en: "Provider" },
    display_name: { id: "Nama tampil", en: "Display name" },
    locale: { id: "Kode bahasa", en: "Locale", help_id: "Contoh: id-ID", help_en: "E.g.: id-ID" },
    language: { id: "Bahasa", en: "Language", help_id: "Contoh: Indonesian", help_en: "E.g.: Indonesian" },
    gender: { id: "Gender suara", en: "Voice gender" },
    delivery_wps: { id: "Tempo voice (kata/detik)", en: "Voice pace (words/sec)", help_id: "Kosongkan = ikut tempo engine. Rentang 1.0–4.0.", help_en: "Empty = engine default. Range 1.0–4.0." },
    preview_url: { id: "Contoh suara (URL .mp3)", en: "Voice sample (.mp3 URL)" },
    default_settings: { id: "Setelan default (JSON)", en: "Default settings (JSON)", help_id: 'Contoh: {"stability":0.3,"style":0.5}', help_en: 'E.g.: {"stability":0.3,"style":0.5}' },
  },
  durations: {
    seconds: { id: "Durasi (detik)", en: "Duration (seconds)" },
    use_case: { id: "Kegunaan (teks ID)", en: "Use case (ID text)" },
    use_case_en: { id: "Kegunaan (teks EN)", en: "Use case (EN text)" },
    notes: { id: "Catatan admin", en: "Admin notes" },
  },
};

// Penerjemah KODE error API → pesan dwibahasa (aturan: API kirim kode, FE menerjemahkan).
function errText(code: string, detail?: Record<string, unknown> | null): React.ReactNode {
  const col = String(detail?.col ?? "");
  switch (code) {
    case "duplicate_key": return <Bi id={`ID '${String(detail?.value ?? "")}' sudah terpakai — gunakan ID lain.`} en={`ID '${String(detail?.value ?? "")}' is already taken — use another.`} />;
    case "invalid_enum": return <Bi id={`${col}: nilai tidak didukung mesin. Pilihan: ${(detail?.allowed as string[] | undefined)?.join(", ") ?? "-"}`} en={`${col}: value not supported. Options: ${(detail?.allowed as string[] | undefined)?.join(", ") ?? "-"}`} />;
    case "invalid_json": return <Bi id={`${col}: format JSON tidak valid.`} en={`${col}: invalid JSON.`} />;
    case "not_number": return <Bi id={`${col}: harus angka.`} en={`${col}: must be a number.`} />;
    case "out_of_range": return <Bi id={`${col}: di luar rentang ${detail?.min}–${detail?.max}.`} en={`${col}: outside range ${detail?.min}–${detail?.max}.`} />;
    case "pk_required": return <Bi id={`${col}: wajib diisi.`} en={`${col}: required.`} />;
    case "no_editable_fields": return <Bi id="Tidak ada perubahan untuk disimpan." en="No changes to save." />;
    default: return code || <Bi id="Gagal menyimpan." en="Save failed." />;
  }
}

// Urutan hierarki (owner 2026-07-04): PROVIDER dulu → AI Models (model = DETAIL dari provider).
const TABS: [string, string][] = [["providers", "Providers"], ["models", "AI Models"], ["music", "Music"], ["moods", "Moods"], ["voice", "Voice"], ["languages", "Languages"], ["durations", "Durasi"], ["fonts", "Fonts"], ["niche", "Niche"]];

// field minimal untuk "Add" per tabel (PK + wajib)
const ADD_FIELDS: Record<string, { table: string; fields: [string, string][] }> = {
  models: { table: "ai_models", fields: [["provider_key", "Provider (induk model ini)"], ["component", "component"], ["model_key", "model_key (PK)"], ["model_id", "model_id (ID resmi di provider — SERTAKAN versi, mis. FLUX.1-schnell)"], ["display_name", "display_name (jelas versinya utk manusia)"], ["quality_tier", "tier (basic/standard/premium/fast)"], ["sort_order", "sort_order (urutan tampil)"], ["default_params", 'default_params JSON — parameter per-model (image: {"size","steps"} · video: {"aspect_ratio","duration","duration_param","allowed_durations"})']] },
  providers: { table: "ai_providers", fields: [["provider_key", "provider_key (PK)"], ["display_name", "display_name"], ["adapter", "adapter (mis. openai_chat)"], ["auth_type", "auth_type (api_key/none)"], ["key_group", "key_group (vendor kunci — mis. openai_tts→openai)"], ["base_url", "base_url (opsional)"], ["price_feed_prefix", "price_feed_prefix (prefix feed harga; kosong = provider_key)"], ["free_tier_note", "free_tier_note (keterangan gratis-harian; tampil ke tenant)"]] },
  voice: { table: "voice_catalog", fields: [["voice_key", "voice_key (PK — kunci KATALOG kita; dirujuk channel & kalibrasi pace)"], ["provider_key", "provider_key (mis. elevenlabs)"], ["vendor_voice_id", "vendor_voice_id (ID suara di sisi vendor; kosong = sama dgn voice_key)"], ["display_name", "display_name"], ["locale", "locale (mis. id-ID)"], ["language", "language (mis. Indonesian)"], ["gender", "gender (male/female)"], ["age", "age (mis. young/middle-aged)"], ["accent", "accent (opsional)"], ["use_case", "use_case (mis. narration)"], ["description", "description (opsional)"], ["default_settings", "default_settings JSON {stability,style,speed}"], ["niche_default", "niche_default (opsional)"], ["preview_url", "preview_url (URL contoh suara .mp3, opsional)"], ["delivery_wps", "delivery_wps (pace voice 1.0–4.0; kosong = ikut engine)"]] },
  languages: { table: "content_languages", fields: [["locale", "locale (PK)"], ["display_name", "display_name"], ["quality_tier", "tier (official/experimental)"], ["caption_font", "caption_font"]] },
  moods: { table: "moods", fields: [["mood_id", "mood_id (PK, huruf kecil)"], ["keywords", 'keywords JSON — kata pemicu deteksi dari NASKAH, campur ID+EN, mis. ["misterius","mysterious"]']] },
  // entri EDIT-only (tanpa tombol Tambah): kesetaraan sunting semua tab (owner 2026-07-06)
  ttsprof: { table: "tts_profiles", fields: [["provider_key", "provider_key (PK)"], ["display_name", "display_name"], ["adapter", "adapter (elevenlabs/openai_speech/edge/gemini_speech)"], ["tts_class", "tts_class (timed/fast_fallback)"], ["delivery_wps", "delivery_wps (pace dasar engine)"], ["speed_param", "speed_param (speed/rate; kosong bila tak ada)"], ["param_schema", "param_schema JSON"]] },
  durations: { table: "duration_presets", fields: [["seconds", "seconds (PK)"], ["use_case", "Kegunaan (ID)"], ["use_case_en", "Use case (EN)"], ["notes", "notes (catatan admin)"], ["trailing_silence_override", "Jeda akhir — override detik (kosong = ikut default 2,5s)"]] },
};
const PK_OF: Record<string, string> = { models: "model_key", providers: "provider_key", voice: "voice_key", languages: "locale", moods: "mood_id", ttsprof: "provider_key", durations: "seconds" };

// [Jeda-akhir preset] Pratinjau dampak + validasi — MIRROR rumus mesin `format_catalog.effective_overhead`:
// jendela narasi = detik − jeda efektif (override||2,5 default) − loop bersih (±1,0s, setelan tenant umum).
// Angka yang admin lihat = angka yang mesin pakai (insiden 20-Jul: 15s + jeda 3,5s → narasi dipadatkan 1,2×).
function durOverridePreview(values: Record<string, string>): { node: React.ReactNode; invalid: boolean } {
  const secs = Number(values.seconds);
  const raw = (values.trailing_silence_override ?? "").trim().replace(",", ".");
  const maxRel = Math.round(secs * 0.4 * 10) / 10;
  const provided = raw !== "";
  const n = Number(raw);
  const invalid = provided && (!Number.isFinite(n) || n < 0 || n > maxRel);
  const trail = provided && Number.isFinite(n) ? n : 2.5;
  const win = Math.max(0, secs - trail - 1.0);
  const pct = secs > 0 ? win / secs : 0;
  const status = pct >= 0.8
    ? { ic: "✅", id: "pace normal", en: "normal pace", color: "var(--success, #16a34a)" }
    : pct >= 0.7
      ? { ic: "⚠️", id: "agak padat", en: "slightly dense", color: "var(--warning, #d97706)" }
      : { ic: "🔴", id: "narasi akan terdengar dipadatkan", en: "narration will sound compressed", color: "var(--danger, #dc2626)" };
  return {
    invalid,
    node: (
      <div className="card" style={{ padding: "0.6rem 0.75rem", background: "var(--surface-2)", fontSize: "var(--text-xs)" }}>
        {invalid ? (
          <div style={{ color: "var(--danger)" }}>
            <Bi id={`Nilai tidak valid — isi angka 0 s/d ${maxRel} (maks 40% durasi preset), atau kosongkan utk default.`}
                en={`Invalid value — enter 0 to ${maxRel} (max 40% of preset), or leave empty for default.`} />
          </div>
        ) : (
          <>
            <div style={{ marginBottom: "0.35rem" }}>
              📐 <Bi id={`Jendela narasi: ${win.toFixed(1)}s dari ${secs}s (${Math.round(pct * 100)}%)`}
                     en={`Narration window: ${win.toFixed(1)}s of ${secs}s (${Math.round(pct * 100)}%)`} />{" "}
              <span style={{ color: status.color, fontWeight: 600 }}>{status.ic} <Bi id={status.id} en={status.en} /></span>
            </div>
            <div style={{ display: "flex", height: 8, borderRadius: 999, overflow: "hidden", background: "var(--surface-3, var(--border))" }} aria-hidden>
              <div style={{ width: `${Math.round(pct * 100)}%`, background: status.color }} />
            </div>
            <div className="muted" style={{ marginTop: "0.3rem" }}>
              <Bi id={`Narasi ${win.toFixed(1)}s │ jeda ${trail.toLocaleString("id-ID")}s + loop ±1,0s. Hitungan = rumus mesin (bukan ilustrasi).`}
                  en={`Narration ${win.toFixed(1)}s │ pause ${trail}s + loop ±1.0s. Same formula the engine uses (not an illustration).`} />
            </div>
          </>
        )}
      </div>
    ),
  };
}

// [DURASI-F5] Bobot antar-adegan (content_beats.weight/weight_locked) — form di tab Durasi.
type BeatW = { beat_key: string; sort_order: number; label_id: string; label_en: string; weight: number; weight_locked: boolean };

export default function AdminCatalogPage() {
  const [tab, setTab] = useState("providers");
  const [data, setData] = useState<Cat | null>(null);
  const [fUp, setFUp] = useState<{ name: string; file: File | null } | null>(null);
  // Status pemuatan font di browser. Tanpa ini, font yang gagal dimuat tetap tampil "normal" dengan
  // huruf pengganti — admin mengira beres padahal berkasnya bermasalah (kelas bug yang sama dgn
  // "font terdaftar tapi tak ada di server"). Dicek pakai API browser, bukan diasumsikan.
  const [fontOk, setFontOk] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<React.ReactNode>(null);
  // [DURASI-F5] bobot antar-adegan + preset terpilih utk pratinjau porsi narasi.
  const [beatW, setBeatW] = useState<BeatW[]>([]);
  const [wPreset, setWPreset] = useState<string>("");
  const [add, setAdd] = useState<Record<string, string> | null>(null);
  // A4: error form INLINE di modal (bukan toast 2 dtk) — {node ReactNode, col field bermasalah}.
  const [formErr, setFormErr] = useState<{ node: React.ReactNode; col?: string } | null>(null);
  // A5: cari/saring tab AI Models (skala ratusan model).
  const [mSearch, setMSearch] = useState("");
  const [mComp, setMComp] = useState("");
  // Uji model (butir-1): dialog kunci uji + jalankan nyata.
  const [tm, setTm] = useState<{ mk: string; name: string; needsKey: boolean } | null>(null);
  const [tmKey, setTmKey] = useState("");
  const [tmBusy, setTmBusy] = useState(false);
  const [tmMsg, setTmMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    // [DURASI-F5] beats dimuat paralel (fail-soft: gagal → seksi bobot tampil kosong, tab lain utuh).
    const [r, rb] = await Promise.all([fetch("/api/admin/catalog"), fetch("/api/admin/beats")]);
    if (r.ok) setData(await r.json());
    if (rb.ok) { const jb = await rb.json().catch(() => ({ beats: [] })); setBeatW(jb.beats ?? []); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  // [DURASI-F5] preset default utk pratinjau porsi: is_default → else preset aktif pertama.
  useEffect(() => {
    if (wPreset || !data) return;
    const act = (data.duration_presets ?? []).filter((d) => d.is_active);
    const def = act.find((d) => d.is_default) ?? act[0];
    if (def) setWPreset(String(def.seconds));
  }, [data, wPreset]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { if (add) setFormErr(null); }, [add !== null]);  // buka modal Tambah → bersihkan error lama

  // Opsi dropdown: provider_key (dari daftar provider) + kolom enum (nilai-sah registry KODE).
  const fieldOptions = useCallback((mapKey: string, col: string): { value: string; label: string }[] | null => {
    if (col === "provider_key") {
      const ps = (data?.ai_providers ?? []).map((p) => ({ value: String(p.provider_key), label: String(p.display_name || p.provider_key) }));
      return ps.length ? ps : null;
    }
    const src = ENUM_FIELD_SRC[mapKey]?.[col];
    if (!src) return null;
    // Opsi = nilai kunci NETRAL-bahasa (openai_chat/api_key/llm) — dwi-bahasa-aman (<option> tak bisa <Bi>).
    const opts = (data?.catalog_valid_values ?? []).filter((r) => src.includes(r.field)).map((r) => ({ value: r.value, label: r.value }));
    return opts.length ? opts : null;
  }, [data]);

  async function runTest() {
    if (!tm) return;
    setTmBusy(true); setTmMsg(null);
    try {
      const r = await fetch("/api/admin/catalog/test-model", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model_key: tm.mk, key: tmKey.trim() }) });
      const j = await r.json().catch(() => ({ ok: false, error: "respons tidak valid" }));
      setTmMsg({ ok: !!j.ok, text: j.ok ? (j.result || "LULUS") : (j.error || "GAGAL") });
      await load();  // refresh: audit ter-stamp
    } catch (e) {
      setTmMsg({ ok: false, text: (e as Error).message });
    } finally { setTmBusy(false); }
  }

  // Butir-4: probe harga 1 model saat simpan → peringatan seketika bila model_id/prefix salah.
  async function probePrice(modelKey: string) {
    try {
      const r = await fetch("/api/admin/catalog/price-probe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model_key: modelKey }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok && j.ok && j.priced === false) setToast("⚠️ Harga tak ditemukan di feed — cek model_id/prefix, atau isi harga manual di baris ini.");
      await load();
    } catch { /* non-fatal */ }
  }

  // Renderer field TERPADU (Add + Edit sama) — dropdown bila kolom enum/FK, else teks. disabled utk PK saat edit.
  const renderField = (mapKey: string, k: string, value: string, onChange: (v: string) => void, disabled: boolean) => {
    const opts = disabled ? null : fieldOptions(mapKey, k);
    if (opts) return (
      <select className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">— pilih —</option>
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
    // A7: key_group = datalist saran (nilai existing; vendor baru tetap boleh diketik).
    const dl = mapKey === "providers" && k === "key_group" ? "kg-dl" : undefined;
    return <input className="input" list={dl} disabled={disabled} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
  };
  // A1/A2: satu blok field utk kedua modal — label manusiawi (Bi) + kode kolom kecil + bantuan + tanda error.
  // FUNGSI render (dipanggil {fieldBlock(...)}), BUKAN komponen bersarang — komponen yang didefinisikan
  // di dalam komponen berganti identitas tiap render → React remount subtree → input kehilangan fokus tiap ketikan.
  const fieldBlock = (mapKey: string, k: string, fallbackLabel: string, value: string, onChange: (v: string) => void, disabled: boolean, pkNote?: boolean) => {
    const meta = FIELD_META[mapKey]?.[k];
    const isErr = formErr?.col === k;
    return (
      <div key={k}>
        <label className="label" style={isErr ? { color: "var(--danger)" } : undefined}>
          {meta ? <Bi id={meta.id} en={meta.en} /> : fallbackLabel}
          <span className="muted mono" style={{ fontSize: "0.625rem", marginLeft: 6 }}>{k}</span>
          {pkNote && <span className="muted"> — <Bi id="terkunci" en="locked" /></span>}
        </label>
        {renderField(mapKey, k, value, onChange, disabled)}
        {meta?.help_id && <div className="muted" style={{ fontSize: "0.6875rem", marginTop: 2, lineHeight: 1.4 }}><Bi id={meta.help_id} en={meta.help_en ?? meta.help_id} /></div>}
        {isErr && <div style={{ color: "var(--danger)", fontSize: "var(--text-xs)", marginTop: 2 }}>{formErr!.node}</div>}
      </div>
    );
  };

  async function toggle(table: string, key: string, value: boolean) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table, key, patch: { is_active: value } }) });
    if (r.ok) { setToast("Tersimpan"); await load(); } else setToast("Gagal");
  }
  // F2-06: admin set contoh suara (preview_url) per voice — tenant ▶ memutarnya (nol biaya runtime).
  const [prevEdit, setPrevEdit] = useState<{ key: string; url: string } | null>(null);
  async function savePreview(key: string, url: string) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "voice_catalog", key, patch: { preview_url: url.trim() || null } }) });
    if (r.ok) { setToast("Contoh disimpan"); setPrevEdit(null); await load(); } else setToast("Gagal");
  }
  // F5-01: admin set pace PER-VOICE (voice_catalog.delivery_wps). Kosong → RESET ke NULL (ikut pace engine).
  // Server validasi rentang [1.0,4.0]. Beda level dari tts_profiles.delivery_wps (pace DASAR engine).
  const [paceEdit, setPaceEdit] = useState<{ key: string; val: string } | null>(null);
  async function savePace(key: string, val: string) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "voice_catalog", key, patch: { delivery_wps: val.trim() === "" ? null : val.trim() } }) });
    if (r.ok) { setToast(val.trim() === "" ? "Pace di-reset (ikut engine)" : "Pace voice disimpan"); setPaceEdit(null); await load(); }
    else { const j = await r.json().catch(() => ({})); setToast(<><Bi id="Gagal: " en="Failed: " />{errText(String(j.error ?? r.status), j.detail)}</>); }
  }
  // [DURASI-F5] simpan bobot / kunci beat (auto-save; server pagari bulat 1–30 & boolean).
  async function patchBeatW(beat_key: string, body: { weight?: number; weight_locked?: boolean }) {
    const r = await fetch("/api/admin/beats", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ beat_key, ...body }) });
    if (r.ok) {
      setToast(body.weight_locked !== undefined
        ? (body.weight_locked ? <Bi id="Adegan dikunci — mesin tidak akan menyentuh bobotnya" en="Beat locked — the machine won't touch its weight" />
                              : <Bi id="Kunci dibuka — mesin boleh menyelaraskan lagi" en="Unlocked — the machine may align it again" />)
        : "Tersimpan");
      const rb = await fetch("/api/admin/beats");
      if (rb.ok) { const jb = await rb.json().catch(() => ({ beats: [] })); setBeatW(jb.beats ?? []); }
    } else {
      const j = await r.json().catch(() => ({}));
      setToast(<><Bi id="Gagal: " en="Failed: " />{String(j.hint ?? j.error ?? r.status)}</>);
    }
  }
  // M2: CRUD musik di catalog (upload→S3, edit, delete, play). Aset = S3 (aturan owner). Durasi dibaca client-side.
  const [mUp, setMUp] = useState<{ name: string; niche: string; mood: string; bpm: string; duration_s: string; file: File | null } | null>(null);
  const [mEdit, setMEdit] = useState<{ id: string; name: string; niche: string; mood: string; bpm: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  function onMusicFile(f: File | null) {
    if (!f) { setMUp((m) => m ? { ...m, file: null } : m); return; }
    setMUp((m) => m ? { ...m, file: f } : m);
    const url = URL.createObjectURL(f);
    const au = new Audio(url);
    au.addEventListener("loadedmetadata", () => { setMUp((m) => m ? { ...m, duration_s: au.duration ? String(Math.round(au.duration)) : m.duration_s } : m); URL.revokeObjectURL(url); }, { once: true });
    au.addEventListener("error", () => URL.revokeObjectURL(url), { once: true });
  }
  // Unggah font: berkas .ttf/.otf → S3 + baris `fonts`. Skala render DIHITUNG server dari isi
  // berkas (bukan diketik), supaya pratinjau tenant selalu sama dengan hasil video.
  async function uploadFont() {
    if (!fUp?.file || !fUp.name.trim()) { setToast("Lengkapi nama font dan berkas / Fill in the font name and file"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", fUp.file); fd.append("name", fUp.name.trim());
    const r = await fetch("/api/admin/fonts/upload", { method: "POST", body: fd });
    setUploading(false);
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      setFUp(null); await load();
      setToast(j.nama_final && j.nama_final !== j.diketik_admin
        ? `Terunggah sebagai "${j.nama_final}" — nama diambil dari dalam berkas agar mesin subtitle menemukannya. / Uploaded as "${j.nama_final}" — the name comes from inside the file so the subtitle engine can find it.`
        : `Font diunggah (skala render ${j.ass_scale}) / Font uploaded (render scale ${j.ass_scale})`);
    } else setToast(`Gagal: ${j.error ?? r.status}`);
  }
  async function uploadMusic() {
    if (!mUp?.file || !mUp.name.trim() || !mUp.niche.trim() || !mUp.mood.trim()) { setToast("Lengkapi file, nama, niche, mood"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", mUp.file); fd.append("name", mUp.name.trim()); fd.append("niche", mUp.niche.trim()); fd.append("mood", mUp.mood.trim());
    if (mUp.bpm.trim()) fd.append("bpm", mUp.bpm.trim());
    if (mUp.duration_s.trim()) fd.append("duration_s", mUp.duration_s.trim());
    const r = await fetch("/api/admin/music/upload", { method: "POST", body: fd });
    setUploading(false);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast("Musik diunggah ke S3"); setMUp(null); await load(); } else setToast(`Gagal: ${j.error ?? r.status}`);
  }
  async function saveMusicEdit() {
    if (!mEdit) return;
    const patch = { name: mEdit.name, niche: mEdit.niche, mood: mEdit.mood, bpm: mEdit.bpm.trim() === "" ? null : Number(mEdit.bpm) };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "music_library", key: mEdit.id, patch }) });
    if (r.ok) { setToast("Tersimpan"); setMEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }
  async function delAsset(table: string, key: string, label: string) {
    if (typeof window !== "undefined" && !window.confirm(`Hapus "${label}"? Berkas di S3 ikut dihapus.`)) return;
    const r = await fetch("/api/admin/catalog", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table, key }) });
    if (r.ok) { setToast("Dihapus"); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }

  // ── Editor baris GENERIK (kesetaraan ✎ semua tab; owner 2026-07-06) — reuse peta ADD_FIELDS ──
  const [rowEdit, setRowEdit] = useState<{ mapKey: string; values: Record<string, string> } | null>(null);
  const openRowEdit = (mapKey: string, row: Record<string, unknown>) => {
    const def = ADD_FIELDS[mapKey]; if (!def) return;
    const values: Record<string, string> = {};
    for (const [k] of def.fields) {
      const v = row[k];
      values[k] = v == null ? "" : (typeof v === "object" ? JSON.stringify(v) : String(v));
    }
    setFormErr(null);
    setRowEdit({ mapKey, values });
  };
  async function saveRowEdit() {
    if (!rowEdit) return;
    const def = ADD_FIELDS[rowEdit.mapKey]; const pk = PK_OF[rowEdit.mapKey];
    const patch: Record<string, unknown> = {};
    for (const [k] of def.fields) if (k !== pk) patch[k] = rowEdit.values[k] === "" ? null : rowEdit.values[k];
    setFormErr(null);
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ table: def.table, key: rowEdit.values[pk], patch }) });
    if (r.ok) { const wasModel = def.table === "ai_models"; const mk = rowEdit.values[pk]; setToast("Tersimpan"); setRowEdit(null); await load(); if (wasModel && mk) await probePrice(String(mk)); }
    else { const j = await r.json().catch(() => ({})); setFormErr({ node: errText(String(j.error ?? ""), j.detail), col: (j.detail as { col?: string } | null)?.col }); }
  }
  // PEMUTAR TUNGGAL (owner 2026-07-04, world-class): satu audio aktif; play record lain otomatis
  // stop yang sedang bunyi; klik ulang = stop; pindah tab/keluar halaman = stop.
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingKey, setPlayingKey] = useState<string | null>(null);
  const stopAudio = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setPlayingKey(null);
  }, []);
  useEffect(() => { stopAudio(); }, [tab, stopAudio]);
  useEffect(() => () => { audioRef.current?.pause(); }, []);
  function togglePlay(key: string, url?: string | null) {
    if (!url) return;
    if (playingKey === key) { stopAudio(); return; }
    audioRef.current?.pause();
    const audio = new Audio(url);
    audio.addEventListener("ended", () => { if (audioRef.current === audio) { audioRef.current = null; setPlayingKey(null); } });
    audio.play().catch(() => { setToast("Gagal memutar"); if (audioRef.current === audio) { audioRef.current = null; setPlayingKey(null); } });
    audioRef.current = audio;
    setPlayingKey(key);
  }
  const PlayBtn = ({ k, url, emptyLabel = "—" }: { k: string; url?: string | null; emptyLabel?: string }) => (
    url
      ? <button className="btn btn-ghost btn-sm" title={playingKey === k ? "Stop" : "Putar"} onClick={() => togglePlay(k, url)}>{playingKey === k ? "⏹" : "▶"}</button>
      : <span className="muted" style={{ fontSize: "0.7rem" }}>{emptyLabel}</span>
  );

  // B2 cost-tracking: edit manual harga model (USD per satuan). Simpan manual → pricing_locked=true
  // (sinkron feed harian TIDAK menimpa). Utk model di luar feed (ElevenLabs = tergantung paket langganan).
  const [priceEdit, setPriceEdit] = useState<{ key: string; in1m: string; out1m: string; img: string; chars1m: string; sec: string } | null>(null);
  async function savePricing() {
    if (!priceEdit) return;
    const num = (s: string) => (s.trim() === "" ? null : Number(s));
    // MERGE di atas pricing lama (bug laten, temuan owner 2026-07-15): dulu REPLACE total → field
    // harga VIDEO ber-basis-klip (per_video_base_usd/base_seconds/per_extra_second_usd) TERHAPUS
    // saat admin menyimpan dari form. Kini kunci di luar form dipertahankan; +field /detik (video).
    const prev = (data?.ai_models.find((m) => String(m.model_key) === priceEdit.key)?.pricing as Record<string, unknown> | null) ?? {};
    const pricing = { ...prev, in_per_1m: num(priceEdit.in1m), out_per_1m: num(priceEdit.out1m), per_image: num(priceEdit.img), per_1m_chars: num(priceEdit.chars1m), per_second_usd: num(priceEdit.sec), source: "manual", synced_at: new Date().toISOString() };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key: priceEdit.key, patch: { pricing, pricing_locked: true } }) });
    if (r.ok) { setToast("Harga disimpan (terkunci dari sinkron otomatis)"); setPriceEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }
  // Sanity-guard: usulan harga DITAHAN (berubah drastis dari sinkron) → admin Terapkan / Abaikan.
  async function resolvePending(key: string, pending: Record<string, unknown>, apply: boolean) {
    const patch = apply
      ? { pricing: Object.fromEntries(Object.entries(pending).filter(([k]) => k !== "reason")), pricing_pending: null }
      : { pricing_pending: null };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key, patch }) });
    if (r.ok) { setToast(apply ? "Usulan harga diterapkan" : "Usulan diabaikan (harga lama dipertahankan)"); await load(); } else setToast("Gagal");
  }
  async function toggleLock(key: string, locked: boolean) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key, patch: { pricing_locked: locked } }) });
    if (r.ok) { setToast(locked ? "Harga dikunci (sinkron tak menimpa)" : "Harga dibuka (ikut sinkron harian)"); await load(); } else setToast("Gagal");
  }
  const fmtPricing = (p: Record<string, unknown> | null | undefined): string => {
    if (!p) return "";
    const parts: string[] = [];
    if (p.in_per_1m != null) parts.push(`in $${p.in_per_1m}/1M`);
    if (p.out_per_1m != null) parts.push(`out $${p.out_per_1m}/1M`);
    if (p.per_image != null) parts.push(`$${p.per_image}/img`);
    if (p.per_1m_chars != null) parts.push(`$${p.per_1m_chars}/1M chr`);
    // Harga VIDEO ([B6]): per-detik ATAU basis-klip + detik-tambahan — dulu tak dikenal formatter
    // → kolom harga model video tampil KOSONG (temuan owner 2026-07-15, "tidak jelas berfungsi").
    if (p.per_second_usd != null) parts.push(`$${p.per_second_usd}/dtk`);
    if (p.per_video_base_usd != null) parts.push(`$${p.per_video_base_usd}/klip${p.base_seconds != null ? ` ${p.base_seconds}s` : ""}${p.per_extra_second_usd != null ? ` +$${p.per_extra_second_usd}/dtk` : ""}`);
    return parts.join(" · ");
  };

  // NICHE_DNA F4: edit keyword deteksi mood (dipakai music_selector mendeteksi mood dari NASKAH —
  // wajib campur ID+EN agar naskah Indonesia terdeteksi; audit 2026-07-04: dulu EN-only = deteksi mati).
  const [kwEdit, setKwEdit] = useState<{ mood_id: string; text: string } | null>(null);
  async function saveKeywords() {
    if (!kwEdit) return;
    const keywords = kwEdit.text.split(",").map((s) => s.trim()).filter(Boolean);
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "moods", key: kwEdit.mood_id, patch: { keywords } }) });
    if (r.ok) { setToast("Keywords disimpan"); setKwEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }

  async function createRow() {
    if (!add) return;
    const def = ADD_FIELDS[tab];
    setFormErr(null);
    const r = await fetch("/api/admin/catalog", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: def.table, row: add }) });
    if (r.ok) { const mk = add.model_key; setToast("Ditambah"); setAdd(null); await load(); if (def.table === "ai_models" && mk) await probePrice(String(mk)); }
    else { const j = await r.json().catch(() => ({})); setFormErr({ node: errText(String(j.error ?? r.status), j.detail), col: (j.detail as { col?: string } | null)?.col }); }
  }

  useEffect(() => {
    const daftar = (data?.fonts ?? []).filter((f) => f.file_url).map((f) => f.name as string);
    if (!daftar.length || typeof document === "undefined" || !document.fonts) return;
    let batal = false;
    (async () => {
      const hasil: Record<string, boolean> = {};
      for (const nm of daftar) {
        try { await document.fonts.load(`16px "${nm}"`); hasil[nm] = document.fonts.check(`16px "${nm}"`); }
        catch { hasil[nm] = false; }
      }
      if (!batal) setFontOk(hasil);
    })();
    return () => { batal = true; };
  }, [data?.fonts]);

  const Switch = ({ table, k, on }: { table: string; k: string; on: boolean }) => (
    <label className="switch"><input type="checkbox" checked={on} onChange={(e) => toggle(table, k, e.target.checked)} /><span className="track" /><span className="thumb" /></label>
  );

  return (
    <>
      <div style={{ marginBottom: "1.25rem" }}><h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.25rem" }}>Catalog</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Kelola model/provider AI, musik, voice, bahasa" en="Manage AI models/providers, music, voice, languages" /></div></div>

      <div className="cat-tabs">{TABS.map(([k, l]) => <button key={k} className={`cat-tab${tab === k ? " active" : ""}`} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === "durations" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Durasi & segmentasi konten" en="Duration & content segmentation" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Kendali preset (semua, termasuk nonaktif): matikan/hidupkan durasi yang ditawarkan ke tenant. Di bawahnya = acuan segmentasi persis seperti yang dilihat tenant (hanya yang aktif)." en="Preset control (all, incl. inactive): toggle which durations are offered to tenants. Below it = the segmentation reference exactly as tenants see it (active only)." /></p>
          {data && <div className="card" style={{ marginBottom: "1.25rem" }}><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th><Bi id="Detik" en="Seconds" /></th><th>Beats</th><th>render_mode</th><th title="Jeda tanpa narasi di akhir video (override per-preset; kosong = default 2,5s). Menentukan jendela narasi — terlalu besar di preset pendek = narasi terdengar dipadatkan."><Bi id="Jeda akhir" en="End pause" /></th><th><Bi id="Kegunaan" en="Use case" /></th><th>default</th><th>active</th></tr></thead>
            <tbody>{data.duration_presets.map((d) => (
              <tr key={String(d.seconds)} style={{ opacity: d.is_active ? 1 : .55 }}>
                <td className="num" style={{ fontWeight: 600 }}>{String(d.seconds)}s</td>
                <td className="num">{String(d.visual_beats)}</td>
                <td className="mono" style={{ fontSize: "var(--text-xs)" }}>{String(d.render_mode)}</td>
                <td className="num" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{d.trailing_silence_override != null
                  ? <>{Number(d.trailing_silence_override).toLocaleString("id-ID")}s <span className="badge badge-default" title="Nilai khusus preset ini (bukan default)">⚙ override</span></>
                  : <span className="muted">2,5s (default)</span>}</td>
                <td className="muted" style={{ fontSize: "var(--text-xs)", maxWidth: 260 }}>{String(d.use_case ?? "")}</td>
                <td>{d.is_default ? <span className="badge badge-default">default</span> : "—"}</td>
                <td><Switch table="duration_presets" k={String(d.seconds)} on={d.is_active as boolean} /> <button className="btn btn-ghost btn-sm" title="Edit kegunaan/catatan" onClick={() => openRowEdit("durations", d)}>✎</button></td>
              </tr>))}</tbody>
          </table></div></div>}
          <PresetTables />

          {/* [DURASI-F5] Bobot antar-adegan — porsi kata narasi per beat (GLOBAL: semua preset/niche/tenant).
              Mesin (align_beat_weights, self_learning harian) menyelaraskan otomatis dari data produksi;
              🔒 = weight_locked (mesin tidak menyentuh). Pratinjau % = rumus persis _distribute_words
              (weight ÷ Σ weight beat-aktif preset terpilih; beat di luar kosakata dihitung 5 — mirror engine). */}
          <div className="card" style={{ marginTop: "1.25rem", padding: "1rem" }}>
            <h4 style={{ margin: "0 0 0.3rem" }}><Bi id="Bobot antar-adegan (berlaku global)" en="Per-beat weights (global)" /></h4>
            <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "0.35rem" }}>
              <Bi id="Bobot = porsi kata narasi tiap adegan — berlaku untuk SEMUA preset, niche, dan tenant. Mesin menyetel ANGKA bobot ini otomatis tiap hari dari data produksi nyata (bergeser halus, maks ±20%/hari). Ubah manual hanya bila benar-benar perlu."
                  en="Weight = each beat's share of narration words — applied to ALL presets, niches, and tenants. The machine auto-tunes these NUMBERS daily from real production data (gentle steps, max ±20%/day). Adjust manually only when truly needed." />
            </p>
            <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "0.75rem" }}>
              <Bi id="Analogi: preset menentukan SIAPA pemain di lapangan (adegan yang ikut); bobot = jatah menit main tiap pemain; mesin = pelatih yang menyetel jatah dari statistik; kunci 🔒 = perintah Anda 'jatah pemain ini jangan diutak-atik pelatih' — adegannya TETAP ikut produksi normal."
                  en="Analogy: the preset decides WHO plays (which beats are used); weight = each player's minutes; the machine = a coach tuning minutes from stats; lock 🔒 = your order 'don't touch this player's minutes' — the beat itself is STILL produced normally." />
            </p>
            <div style={{ marginBottom: "0.35rem", fontSize: "var(--text-sm)" }}>
              <label className="muted" style={{ marginRight: 8 }}><Bi id="Pratinjau porsi narasi pada preset:" en="Preview narration share for preset:" /></label>
              <select value={wPreset} onChange={(e) => setWPreset(e.target.value)}>
                {(data?.duration_presets ?? []).filter((d) => d.is_active).map((d) => (
                  <option key={String(d.seconds)} value={String(d.seconds)}>{String(d.seconds)}s</option>
                ))}
              </select>
            </div>
            <p className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}>
              <Bi id="Baris ABU-ABU = adegan yang tidak dipakai preset terpilih di pratinjau ini (kolom porsi '—'). Bukan nonaktif — tetap bisa diatur; ganti preset di atas untuk melihat porsinya."
                  en="GRAY rows = beats not used by the preset selected above (share column '—'). Not disabled — still editable; switch the preset above to see their share." />
            </p>
            {(() => {
              const act = ((data?.duration_presets ?? []).find((d) => String(d.seconds) === wPreset)?.beats as string[] | null) ?? [];
              const wOf = (k: string) => beatW.find((b) => b.beat_key === k)?.weight ?? 5;   // mirror _BEAT_WEIGHT.get(b,5)
              const tot = act.reduce((s, k) => s + wOf(k), 0) || 1;
              return (
                <div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
                  <thead><tr><th><Bi id="Adegan" en="Beat" /></th><th><Bi id="Bobot" en="Weight" /></th><th title="Kunci angka: 🔒 = angka bobot ini TIDAK diubah penyetel otomatis harian (adegan tetap diproduksi normal)"><Bi id="Kunci angka" en="Lock number" /></th><th><Bi id={`Porsi narasi @${wPreset}s`} en={`Share @${wPreset}s`} /></th></tr></thead>
                  <tbody>{beatW.map((b) => (
                    <tr key={b.beat_key} style={{ opacity: act.includes(b.beat_key) ? 1 : 0.55 }}>
                      <td><span data-id>{b.label_id}</span><span data-en>{b.label_en}</span> <span className="mono muted" style={{ fontSize: "var(--text-xs)" }}>({b.beat_key})</span></td>
                      <td className="num">
                        <input type="number" min={1} max={30} step={1} defaultValue={b.weight} key={`${b.beat_key}-${b.weight}`}
                          style={{ width: 64 }}
                          onBlur={(e) => {
                            const v = Number(e.target.value);
                            if (v === b.weight) return;
                            if (!Number.isInteger(v) || v < 1 || v > 30) { setToast(<Bi id="Bobot harus bilangan bulat 1–30" en="Weight must be an integer 1–30" />); e.target.value = String(b.weight); return; }
                            patchBeatW(b.beat_key, { weight: v });
                          }} />
                      </td>
                      <td>
                        <button className="btn btn-ghost btn-sm"
                          title={b.weight_locked
                            ? "🔒 Angka bobot ini DIBEKUKAN — penyetel otomatis harian melewatinya (adegan tetap diproduksi normal). Klik untuk membuka."
                            : "🔓 Angka bobot ini boleh disetel halus oleh mesin tiap hari dari data nyata (disarankan). Klik untuk membekukan angka."}
                          onClick={() => patchBeatW(b.beat_key, { weight_locked: !b.weight_locked })}>
                          {b.weight_locked ? "🔒" : "🔓"}
                        </button>
                      </td>
                      <td className="num">{act.includes(b.beat_key) ? `${Math.round(100 * wOf(b.beat_key) / tot)}%` : <span className="muted" title="Adegan ini tidak aktif di preset terpilih">—</span>}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              );
            })()}
          </div>
        </div>
      )}

      {loading && tab !== "durations" && <div className="card card-pad muted">Memuat…</div>}
      {!loading && data && (<>
        {tab === "providers" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Provider AI = INDUK. Model adalah detailnya — tambah model langsung dari baris provider (＋ Model)." en="AI providers = PARENT. Models are their details — add a model straight from the provider row." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah provider" en="Add provider" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th>display</th><th>adapter</th><th>auth</th><th>key_group</th><th><Bi id="model" en="models" /></th><th>active</th><th></th></tr></thead>
            <tbody>{data.ai_providers.map((p) => {
              const pk = p.provider_key as string;
              const nModels = data.ai_models.filter((m) => m.provider_key === pk).length;
              return (
                <tr key={pk}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{pk}</td>
                  <td>{p.display_name as string}</td><td className="mono" style={{ fontSize: "var(--text-xs)" }}>{p.adapter as string}</td>
                  <td className="muted">{p.auth_type as string}</td>
                  <td className="mono" style={{ fontSize: "var(--text-xs)" }}>{(p.key_group as string) || pk}</td>
                  <td><span className={`badge ${nModels > 0 ? "badge-default" : "badge-warning"}`}>{nModels}</span></td>
                  <td><Switch table="ai_providers" k={pk} on={p.is_active as boolean} /></td>
                  <td style={{ whiteSpace: "nowrap" }}><button className="btn btn-secondary btn-sm" title="Tambah model utk provider ini" onClick={() => { setTab("models"); setAdd({ provider_key: pk }); }}><Plus size={12} /> Model</button> <button className="btn btn-ghost btn-sm" title="Edit provider" onClick={() => openRowEdit("providers", p)}>✎</button><button className="btn btn-ghost btn-sm" title="Hapus provider (ditolak bila masih dirujuk)" onClick={() => delAsset("ai_providers", pk, (p.display_name as string) || pk)}><Trash2 size={13} /></button></td>
                </tr>
              );
            })}</tbody>
          </table></div></div>
        </>)}

        {tab === "models" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Model = DETAIL dari provider (dikelompokkan per provider)." en="Models = details of a provider (grouped by provider)." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => { setFormErr(null); setAdd({}); }}><Plus size={14} /> <Bi id="Tambah model" en="Add model" /></button></div></div>
          {/* A5: cari + saring jenis — skala ratusan model (reuse .input + .radio-pill) */}
          <div style={{ display: "flex", gap: ".5rem", alignItems: "center", flexWrap: "wrap", margin: "0 0 .6rem" }}>
            <input className="input" style={{ height: 30, maxWidth: 260 }} placeholder="Cari model / ID / provider…" value={mSearch} onChange={(e) => setMSearch(e.target.value)} />
            <span className={`radio-pill${mComp === "" ? " sel" : ""}`} onClick={() => setMComp("")}><Bi id="Semua" en="All" /></span>
            {["llm", "tts", "image", "video"].map((c) => <span key={c} className={`radio-pill${mComp === c ? " sel" : ""}`} onClick={() => setMComp(mComp === c ? "" : c)}>{c}</span>)}
          </div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider</th><th>model_key</th><th>component</th><th><Bi id="harga (USD, auto-sync harian)" en="pricing (USD, auto-synced daily)" /></th><th>tier</th><th>active</th><th></th></tr></thead>
            <tbody>{[...data.ai_models].filter((m) => {
              if (mComp && m.component !== mComp) return false;
              const q = mSearch.trim().toLowerCase();
              if (!q) return true;
              return [m.model_key, m.model_id, m.display_name, m.provider_key].some((v) => String(v ?? "").toLowerCase().includes(q));
            }).sort((a, b) => String(a.provider_key).localeCompare(String(b.provider_key)) || String(a.component).localeCompare(String(b.component))).map((m, i, arr) => {
              const mk = m.model_key as string;
              const pr = m.pricing as Record<string, unknown> | null;
              return (
                <tr key={mk}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{i === 0 || arr[i - 1].provider_key !== m.provider_key ? (m.provider_key as string) : <span className="muted" style={{ opacity: .35 }}>·</span>}</td>
                  <td className="mono">{mk}</td><td><span className="badge badge-default">{m.component as string}</span></td>
                  <td style={{ maxWidth: 300 }}>
                    {priceEdit?.key === mk ? (
                      <span style={{ display: "inline-flex", gap: ".3rem", alignItems: "center", flexWrap: "wrap" }}>
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="in/1M" value={priceEdit.in1m} onChange={(e) => setPriceEdit({ ...priceEdit, in1m: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="out/1M" value={priceEdit.out1m} onChange={(e) => setPriceEdit({ ...priceEdit, out1m: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="/img" value={priceEdit.img} onChange={(e) => setPriceEdit({ ...priceEdit, img: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 76 }} placeholder="/1M chr" value={priceEdit.chars1m} onChange={(e) => setPriceEdit({ ...priceEdit, chars1m: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 64 }} placeholder="/dtk" title="Harga video per-detik (USD) — harga basis-klip diedit via kolom pricing model (dipertahankan otomatis)" value={priceEdit.sec} onChange={(e) => setPriceEdit({ ...priceEdit, sec: e.target.value })} />
                        <button className="btn btn-default btn-sm" onClick={savePricing}>✓</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => setPriceEdit(null)}>✕</button>
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", gap: ".4rem", alignItems: "center", flexWrap: "wrap" }}>
                        {pr ? <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{fmtPricing(pr)}</span>
                          : (m.is_active ? <span className="badge badge-warning" title="Model aktif tanpa harga → biaya video tampil 'belum lengkap'">⚠️ kosong</span> : <span className="muted" style={{ fontSize: "0.7rem" }}>—</span>)}
                        {m.pricing_locked ? <span title="Terkunci — sinkron otomatis tak menimpa (klik utk buka)" style={{ cursor: "pointer" }} onClick={() => toggleLock(mk, false)}>🔒</span>
                          : pr ? <span title="Ikut sinkron harian (klik utk kunci)" style={{ cursor: "pointer", opacity: .45 }} onClick={() => toggleLock(mk, true)}>🔓</span> : null}
                        <button className="btn btn-ghost btn-sm" title="Edit harga manual" onClick={() => setPriceEdit({ key: mk, in1m: String(pr?.in_per_1m ?? ""), out1m: String(pr?.out_per_1m ?? ""), img: String(pr?.per_image ?? ""), chars1m: String(pr?.per_1m_chars ?? ""), sec: String(pr?.per_second_usd ?? "") })}>✎</button>
                        {(m.pricing_pending as Record<string, unknown> | null) && (
                          <span style={{ display: "inline-flex", gap: ".3rem", alignItems: "center", padding: ".15rem .4rem", borderRadius: 6, background: "var(--warning-soft)", fontSize: "0.6875rem" }} title={String((m.pricing_pending as Record<string, unknown>).reason ?? "")}>
                            ⚠️ <Bi id="usulan baru:" en="new proposal:" /> {fmtPricing(m.pricing_pending as Record<string, unknown>)}
                            <button className="btn btn-default btn-sm" style={{ height: 20, padding: "0 .4rem", fontSize: "0.625rem" }} onClick={() => resolvePending(mk, m.pricing_pending as Record<string, unknown>, true)}><Bi id="Terapkan" en="Apply" /></button>
                            <button className="btn btn-ghost btn-sm" style={{ height: 20, padding: "0 .4rem", fontSize: "0.625rem" }} onClick={() => resolvePending(mk, m.pricing_pending as Record<string, unknown>, false)}><Bi id="Abaikan" en="Dismiss" /></button>
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className="muted">{m.quality_tier as string}</td>
                  <td><Switch table="ai_models" k={mk} on={m.is_active as boolean} /></td>
                  <td style={{ whiteSpace: "nowrap" }}>{(() => {
                    const au = String((m.cost_hint as { audit?: string } | null)?.audit || "");
                    if (au.startsWith("LULUS")) return <span className="badge badge-success" title={au} style={{ fontSize: "0.65rem", marginRight: ".3rem" }}>✓ <Bi id="Teruji" en="Tested" /></span>;
                    if (au) return <span className="badge badge-warning" title={au} style={{ fontSize: "0.65rem", marginRight: ".3rem" }}>✗ <Bi id="belum lolos" en="not passed" /></span>;
                    return <span className="muted" title="Belum pernah diuji — klik Uji" style={{ fontSize: "0.65rem", marginRight: ".3rem" }}><Bi id="belum diuji" en="not tested" /></span>;
                  })()}<button className="btn btn-ghost btn-sm" title="Uji model — jalankan nyata ke vendor (butir-1: aktif = terbukti jalan)" onClick={() => { setTmMsg(null); setTmKey(""); setTm({ mk, name: (m.display_name as string) || mk, needsKey: (data.ai_providers.find((p) => String(p.provider_key) === String(m.provider_key))?.auth_type) === "api_key" }); }}><Bi id="Uji" en="Test" /></button><button className="btn btn-ghost btn-sm" title="Edit model" onClick={() => openRowEdit("models", m)}>✎</button><button className="btn btn-ghost btn-sm" title="Hapus model (ditolak bila dipakai channel)" onClick={() => delAsset("ai_models", mk, (m.display_name as string) || mk)}><Trash2 size={13} /></button></td>
                </tr>
              );
            })}</tbody>
          </table></div></div>
        </>)}

        {tab === "fonts" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}>{data.fonts.length} <Bi id="font · S3 + server render" en="fonts · S3 + render server" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setFUp({ name: "", file: null })}><Plus size={14} /> <Bi id="Tambah font" en="Add font" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th><Bi id="nama" en="name" /></th><th><Bi id="berkas" en="file" /></th><th className="num"><Bi id="skala render" en="render scale" /></th><th><Bi id="contoh" en="sample" /></th><th><Bi id="aktif" en="active" /></th><th></th></tr></thead>
            <tbody>
              {data.fonts.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: "1rem", textAlign: "center" }}><Bi id="Belum ada font. Unggah untuk mulai." en="No fonts yet. Upload one to start." /></td></tr>}
              {data.fonts.map((f) => (
                <tr key={f.name as string}>
                  <td style={{ color: "var(--text-primary)", fontFamily: `"${f.name as string}",Geist,sans-serif`, fontSize: "1.15rem" }}>{f.name as string}</td>
                  <td className="muted"><code>{f.file_name as string}</code></td>
                  <td className="num muted" title="unitsPerEm ÷ (winAscent+winDescent) — dibaca dari berkas, agar pratinjau tenant = hasil video / read from the file so the tenant preview matches the rendered video">{f.ass_scale ? Number(f.ass_scale).toFixed(4) : "—"}</td>
                  <td style={{ minWidth: 300 }}>
                    {fontOk[f.name as string] === false ? (
                      <span className="badge badge-error" title="Browser menolak berkas ini — periksa berkasnya; mesin render mungkin ikut bermasalah / Browser rejected this file — check it; the render server may fail too"><AlertTriangle size={11} /> <Bi id="gagal dimuat" en="failed to load" /></span>
                    ) : (
                      <div style={{ fontFamily: `"${f.name as string}",Geist,sans-serif`, color: "var(--text-primary)", lineHeight: 1.25 }}>
                        <div style={{ fontSize: "1.5rem" }}><Bi id="Rahasia Alam Semesta" en="The quick brown fox" /></div>
                        <div style={{ fontSize: "0.95rem", opacity: 0.8 }}>ABCDEFGHIJ abcdefghij 0123456789</div>
                      </div>
                    )}
                  </td>
                  <td><Switch table="fonts" k={f.name as string} on={f.is_active as boolean} /></td>
                  <td style={{ whiteSpace: "nowrap" }}><button className="btn btn-ghost btn-sm" title="Hapus font (ditolak bila masih dipakai channel) / Delete font (refused while still used by a channel)" onClick={() => delAsset("fonts", f.name as string, f.name as string)}><Trash2 size={13} /></button></td>
                </tr>
              ))}
            </tbody></table></div></div>
          <div className="tip" style={{ marginTop: "0.75rem", fontSize: "var(--text-xs)" }}>
            <Bi id="Berkas font disimpan di S3 dan diunduh sendiri oleh server render saat pertama dipakai — tidak perlu menyentuh server. Skala render dibaca dari isi berkas, bukan diketik." en="Font files live in S3 and are fetched by the render server on first use — no server access needed. Render scale is read from the file, never typed." />
          </div>
          {/* pemuat font aktif agar kolom "contoh" memakai huruf aslinya */}
          {/* format() WAJIB ikut ekstensi: .otf dideklarasikan "truetype" → browser menolak diam-diam,
              contoh huruf jatuh ke font lain tanpa ada yang sadar. */}
          <style>{data.fonts.filter((f) => f.file_url).map((f) => {
            const url = f.file_url as string;
            const fmt = url.toLowerCase().endsWith(".otf") ? "opentype" : "truetype";
            return `@font-face{font-family:"${f.name as string}";src:url("${url}") format("${fmt}");font-display:swap}`;
          }).join("")}</style>
        </>)}

        {tab === "music" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}>{data.music_library.length} tracks · S3</span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setMUp({ name: "", niche: "", mood: "", bpm: "", duration_s: "", file: null })}><Plus size={14} /> <Bi id="Tambah musik" en="Add music" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>name</th><th>niche</th><th>mood</th><th className="num">durasi</th><th className="num">bpm</th><th>putar</th><th>active</th><th></th></tr></thead>
            <tbody>
              {data.music_library.length === 0 && <tr><td colSpan={8} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Belum ada musik. Unggah untuk mulai.</td></tr>}
              {data.music_library.map((t) => (mEdit && mEdit.id === t.id ? (
                <tr key={t.id as string}>
                  <td><input className="input" style={{ height: 28 }} value={mEdit.name} onChange={(e) => setMEdit({ ...mEdit, name: e.target.value })} /></td>
                  <td><input className="input" style={{ height: 28, width: 120 }} list="mus-niche-dl" value={mEdit.niche} onChange={(e) => setMEdit({ ...mEdit, niche: e.target.value })} /></td>
                  <td><input className="input" style={{ height: 28, width: 100 }} list="mus-mood-dl" value={mEdit.mood} onChange={(e) => setMEdit({ ...mEdit, mood: e.target.value })} /></td>
                  <td className="num muted">{t.duration_s ? `${t.duration_s}s` : "—"}</td>
                  <td><input className="input" style={{ height: 28, width: 56 }} value={mEdit.bpm} placeholder="bpm" onChange={(e) => setMEdit({ ...mEdit, bpm: e.target.value })} /></td>
                  <td colSpan={3}><button className="btn btn-default btn-sm" onClick={saveMusicEdit}>✓</button> <button className="btn btn-ghost btn-sm" onClick={() => setMEdit(null)}>✕</button></td>
                </tr>
              ) : (
                <tr key={t.id as string}>
                  <td style={{ color: "var(--text-primary)" }}>{t.name as string}</td><td className="muted">{t.niche as string}</td>
                  <td><span className="badge badge-default">{t.mood as string}</span></td>
                  <td className="num muted">{t.duration_s ? `${t.duration_s}s` : "—"}</td>
                  <td className="num muted">{(t.bpm as number) || "—"}</td>
                  <td><button className="btn btn-ghost btn-sm" title={playingKey === `music:${t.id}` ? "Stop" : "Putar"} onClick={async () => {
                    if (playingKey === `music:${t.id}`) { stopAudio(); return; }
                    // bucket aset PRIVAT → URL publik 403; putar via presigned URL (route auth)
                    const j = await fetch(`/api/music/preview?id=${t.id}`).then((r) => r.json()).catch(() => ({}));
                    if (j.url) togglePlay(`music:${t.id}`, j.url); else setToast("Gagal memutar");
                  }}>{playingKey === `music:${t.id}` ? "⏹" : "▶"}</button></td>
                  <td><Switch table="music_library" k={t.id as string} on={t.is_active as boolean} /></td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn btn-ghost btn-sm" title="Edit" onClick={() => setMEdit({ id: t.id as string, name: (t.name as string) || "", niche: (t.niche as string) || "", mood: (t.mood as string) || "", bpm: t.bpm != null ? String(t.bpm) : "" })}>✎</button>
                    <button className="btn btn-ghost btn-sm" title="Hapus" onClick={() => delAsset("music_library", t.id as string, (t.name as string) || "track")}><Trash2 size={13} /></button>
                  </td>
                </tr>
              )))}
            </tbody>
          </table></div></div>
          <datalist id="mus-niche-dl">{[...new Set(data.music_library.map((t) => t.niche as string).filter(Boolean))].map((n) => <option key={n} value={n} />)}</datalist>
          <datalist id="mus-mood-dl">{[...new Set(data.music_library.map((t) => t.mood as string).filter(Boolean))].map((m) => <option key={m} value={m} />)}</datalist>
        </>)}

        {tab === "voice" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Voice catalog + kelas TTS provider" en="Voice catalog + TTS provider classes" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah voice" en="Add voice" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>voice_key</th><th>provider</th><th>display</th><th>locale</th><th>gender</th><th title="Pace voice (kata/detik @speed 1.0). Kosong = ikut pace DASAR engine di bawah. Override per-voice (mis. voice lebih cepat).">Pace voice</th><th title="Angka yang BENAR-BENAR dipakai mesin untuk meramal durasi, hasil kalibrasi otomatis dari suara nyata. MENIMPA kolom di sebelah kiri. Ditulis mesin — tak bisa diedit di sini; kunci lewat pace_locked bila ingin angka Anda yang menang.">Dipakai mesin (kalibrasi)</th><th>Contoh suara</th><th>active</th><th></th></tr></thead>
            <tbody>
              {data.voice_catalog.length === 0 && <tr><td colSpan={10} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Belum ada voice. Tambah untuk mulai.</td></tr>}
              {data.voice_catalog.map((v) => (
                <tr key={v.voice_key as string}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{v.voice_key as string}</td><td>{v.provider_key as string}</td>
                  <td>{v.display_name as string}</td><td className="muted">{(v.locale as string) || "—"}</td><td className="muted">{(v.gender as string) || "—"}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>
                    {(() => {
                      const k = (data.tts_pace_calibration ?? []).find((c) => c.voice_key === v.voice_key);
                      const jedaUkur = k?.pause_source === "measured";
                      if (!k || (k.sec_per_char == null && !jedaUkur)) return <Bi id="belum dikalibrasi" en="not calibrated yet" />;
                      const err = k.calib_error_secs != null ? `±${Number(k.calib_error_secs).toFixed(2)}s` : "";
                      // Angka mana yang TERUKUR dan mana yang jatuh ke bawaan harus terlihat: baris yang
                      // kolomnya kosong diam-diam memakai angka bawaan, dan bawaan itu pernah 5–9× salah
                      // (elipsis 1,376 dtk padahal terukur 0,29). Admin tak boleh menebak.
                      const bawaan = ([["sec_per_char", "huruf"], ["sec_per_digit", "angka"],
                                       ["sec_per_sentence", "kalimat"], ["sec_per_comma", "koma"],
                                       ["sec_per_ellipsis", "elipsis"], ["sec_per_em_dash", "em-dash"]] as const)
                        .filter(([c]) => (k as Record<string, unknown>)[c] == null).map(([, n]) => n);
                      const rincian = `detik = ${k.sec_per_char ?? "bawaan"}/huruf + ${k.sec_per_sentence ?? "bawaan"}/kalimat`
                        + ` + ${k.sec_per_comma ?? "bawaan"}/koma + ${k.sec_per_em_dash ?? "bawaan"}/em-dash`
                        + ` + ${k.sec_per_ellipsis ?? "bawaan"}/elipsis + ${k.sec_per_digit ?? "bawaan"}/angka`
                        + ` · ${k.chars_per_word ?? "—"} huruf/kata · dari ${k.sample_n ?? 0} render`
                        + (jedaUkur ? ` · biaya jeda DIUKUR langsung${k.pause_measured_at ? " pada " + new Date(k.pause_measured_at).toLocaleDateString("id-ID") : ""}, bukan hasil regresi` : "")
                        + (bawaan.length ? ` · memakai angka bawaan untuk: ${bawaan.join(", ")}` : "");
                      return (<span title={rincian}>
                        <b style={{ color: "var(--text-primary)" }}>{k.delivery_wps != null ? Number(k.delivery_wps).toFixed(2) + " kata/dtk" : "—"}</b><br />
                        <span style={{ opacity: 0.75 }}>
                          {jedaUkur ? <Bi id="jeda diukur" en="pauses measured" /> : <Bi id="jeda dari regresi" en="pauses fitted" />}
                          {err ? ` · ${err}` : ""} · n={k.sample_n ?? 0}
                          {bawaan.length ? <> · <span title={`kolom kosong → angka bawaan: ${bawaan.join(", ")}`}>{bawaan.length} <Bi id="pakai bawaan" en="use defaults" /></span></> : null}
                        </span>
                      </span>);
                    })()}
                  </td>
                  <td>
                    {paceEdit && paceEdit.key === v.voice_key
                      ? <span style={{ display: "inline-flex", gap: "0.25rem", alignItems: "center" }}>
                          <input className="input" style={{ height: 26, width: 58, fontSize: "0.72rem" }} value={paceEdit.val} placeholder="2.0" onChange={(e) => setPaceEdit({ key: v.voice_key as string, val: e.target.value })} />
                          <button className="btn btn-default btn-sm" title="Simpan (1.0–4.0)" onClick={() => savePace(v.voice_key as string, paceEdit.val)}>✓</button>
                          <button className="btn btn-ghost btn-sm" title="Reset ke pace engine (NULL)" onClick={() => savePace(v.voice_key as string, "")}>⟲</button>
                          <button className="btn btn-ghost btn-sm" title="Batal" onClick={() => setPaceEdit(null)}>✕</button>
                        </span>
                      : <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "center" }}>
                          {v.delivery_wps != null ? <span className="mono">{String(v.delivery_wps)}</span> : <span className="muted" style={{ fontSize: "0.7rem" }}>— ikut engine</span>}
                          <button className="btn btn-ghost btn-sm" title="Set pace voice (kosong=ikut engine)" onClick={() => setPaceEdit({ key: v.voice_key as string, val: v.delivery_wps != null ? String(v.delivery_wps) : "" })}>✎</button>
                        </span>}
                  </td>
                  <td>
                    <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "center" }}>
                      <PlayBtn k={`voice:${v.voice_key}`} url={v.preview_url as string | null} emptyLabel="kosong" />
                      {prevEdit && prevEdit.key === v.voice_key
                        ? <><input className="input" style={{ height: 26, fontSize: "0.7rem", width: 150 }} value={prevEdit.url} onChange={(e) => setPrevEdit({ key: v.voice_key as string, url: e.target.value })} placeholder="https://… .mp3" /><button className="btn btn-default btn-sm" onClick={() => savePreview(v.voice_key as string, prevEdit.url)}>✓</button><button className="btn btn-ghost btn-sm" onClick={() => setPrevEdit(null)}>✕</button></>
                        : <button className="btn btn-ghost btn-sm" title="Set contoh" onClick={() => setPrevEdit({ key: v.voice_key as string, url: (v.preview_url as string) || "" })}>✎</button>}
                    </span>
                  </td>
                  <td><Switch table="voice_catalog" k={v.voice_key as string} on={v.is_active as boolean} /></td>
                  <td><button className="btn btn-ghost btn-sm" title="Hapus voice (+ contoh S3)" onClick={() => delAsset("voice_catalog", v.voice_key as string, (v.display_name as string) || (v.voice_key as string))}><Trash2 size={13} /></button></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
          <div className="cat-toolbar" style={{ marginTop: "1.25rem" }}><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Pace DASAR & kelas per-ENGINE — fallback untuk SEMUA voice (tts_profiles). 'Pace voice' di atas menimpa ini khusus per-voice." en="Per-ENGINE base pace & class — fallback for ALL voices (tts_profiles). 'Pace voice' above overrides this per-voice." /></span></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th title="timed = punya timestamp per-kata (caption presisi); fast_fallback = tanpa timestamp (murah/gratis)">class</th><th className="num" title="Pace DASAR engine (kata/dtk) — fallback semua voice di engine ini">delivery_wps (engine)</th><th className="num" title="Batas huruf SATU permintaan ke penyedia ini, dari dokumentasi RESMI vendor. Naskah lebih panjang (video Regular 2-12 menit) dipotong di batas kalimat. Kosong = pakai kenop global yang konservatif — JANGAN diisi angka karangan: salah isi = produksi gagal di tengah naskah panjang.">batas huruf/permintaan</th><th>active</th></tr></thead>
            <tbody>{data.tts_profiles.map((p) => (
              <tr key={p.provider_key as string}><td className="mono">{p.provider_key as string}</td><td>{p.tts_class as string}</td><td className="num">{String(p.delivery_wps)}</td><td className="num">{p.max_chars_per_request != null ? String(p.max_chars_per_request) : <span className="muted" style={{ fontSize: "0.7rem" }}>— kenop global</span>}</td><td><Switch table="tts_profiles" k={p.provider_key as string} on={p.is_active as boolean} /> <button className="btn btn-ghost btn-sm" title="Edit profil engine" onClick={() => openRowEdit("ttsprof", p)}>✎</button></td></tr>
            ))}</tbody>
          </table></div></div>
          <div className="cat-toolbar" style={{ marginTop: "1.25rem" }}><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="ALAT UKUR biaya jeda per tanda baca. Mesin menyusun tiap baris jadi 5 versi ber-HURUF IDENTIK (tanpa tanda / koma / em-dash / elipsis / titik), lalu mengukur selisih durasinya — jadi selisih itu hanya bisa milik tandanya. Read-only: mengubah isinya berarti mengubah alat ukurnya." en="Pause-cost MEASURING INSTRUMENT. The engine turns each row into 5 versions with IDENTICAL letters (none / comma / em-dash / ellipsis / period) and measures the duration difference — so the difference can only belong to the mark. Read-only: changing it changes the instrument." /></span></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th><Bi id="bahasa" en="language" /></th><th className="num">#</th><th><Bi id="klausa" en="clauses" /></th><th><Bi id="contoh" en="sample" /></th><th>active</th></tr></thead>
            <tbody>
              {(data.duration_probe_texts ?? []).length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: "1rem", textAlign: "center" }}><Bi id="Belum ada teks alat ukur — suara baru akan memakai angka bawaan." en="No probe texts yet — new voices will fall back to default numbers." /></td></tr>}
              {(data.duration_probe_texts ?? []).map((t) => (
                <tr key={`${t.lang}-${t.idx}`}>
                  <td className="mono">{t.lang}</td><td className="num">{t.idx}</td>
                  <td className="num">{(t.clauses ?? []).length}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{((t.clauses ?? [])[0] || "").slice(0, 70)}…</td>
                  <td>{t.is_active ? <span className="badge badge-success"><span className="dot" />on</span> : <span className="badge badge-warning"><span className="dot" />off</span>}</td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
        </>)}

        {tab === "languages" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Bahasa konten — dikelola admin, dibaca per-channel" en="Content languages — admin-managed" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah bahasa" en="Add language" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>locale</th><th><Bi id="Bahasa" en="Language" /></th><th>Tier</th><th>font</th><th>Active</th></tr></thead>
            <tbody>{data.content_languages.map((l) => (
              <tr key={l.locale as string}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{l.locale as string}</td><td>{l.display_name as string}</td>
                <td>{l.quality_tier === "official" ? <span className="badge badge-success"><span className="dot" />Official</span> : <span className="badge badge-warning"><span className="dot" />Experimental</span>}</td>
                <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{(l.caption_font as string) || "—"}</td>
                <td><Switch table="content_languages" k={l.locale as string} on={l.is_active as boolean} /></td>
                <td style={{ whiteSpace: "nowrap" }}><button className="btn btn-ghost btn-sm" title="Edit bahasa" onClick={() => openRowEdit("languages", l)}>✎</button><button className="btn btn-ghost btn-sm" title="Hapus bahasa (ditolak bila dipakai channel)" onClick={() => delAsset("content_languages", l.locale as string, l.display_name as string)}><Trash2 size={13} /></button></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "moods" && data && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Mood musik + kata pemicu deteksi dari naskah (campur ID+EN). Dipakai pemilih musik & paket mood niche." en="Music moods + script detection trigger words (mix ID+EN)." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah mood" en="Add mood" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>mood</th><th><Bi id="Track di library" en="Library tracks" /></th><th><Bi id="Kata pemicu (deteksi dari naskah)" en="Trigger words" /></th><th>Active</th><th></th></tr></thead>
            <tbody>{data.moods.map((m) => {
              const mid = m.mood_id as string;
              const kws = Array.isArray(m.keywords) ? (m.keywords as string[]) : [];
              const nTracks = data.music_library.filter((t) => t.mood === mid && t.is_active).length;
              return (
                <tr key={mid}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{mid}</td>
                  <td>{nTracks > 0 ? <span className="badge badge-success">{nTracks}</span> : <span className="badge badge-warning">0</span>}</td>
                  <td style={{ maxWidth: 480 }}>
                    {kwEdit?.mood_id === mid ? (
                      <div style={{ display: "flex", gap: ".4rem" }}>
                        <textarea className="textarea" rows={2} style={{ flex: 1 }} value={kwEdit.text} onChange={(e) => setKwEdit({ mood_id: mid, text: e.target.value })} />
                        <button className="btn btn-default btn-sm" onClick={saveKeywords}>OK</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => setKwEdit(null)}>Batal</button>
                      </div>
                    ) : (
                      <span className="muted" style={{ fontSize: "var(--text-xs)", cursor: "pointer" }} title="Klik untuk edit" onClick={() => setKwEdit({ mood_id: mid, text: kws.join(", ") })}>{kws.join(", ") || "(kosong — klik utk isi)"}</span>
                    )}
                  </td>
                  <td><Switch table="moods" k={mid} on={m.is_active as boolean} /></td>
                  <td></td>
                </tr>
              );
            })}</tbody>
          </table></div></div>
        </>)}

        {tab === "niche" && (
          <div className="card card-pad" style={{ textAlign: "center", padding: "3rem" }}>
            <div style={{ color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", justifyContent: "center" }}><Target size={32} /></div>
            <p className="muted" style={{ marginBottom: "1rem" }}><Bi id="Niche library punya halaman khusus (drawer, exclusivity, release)." en="Niche library has a dedicated page." /></p>
            <Link href="/admin/niches" className="btn btn-default btn-sm"><Bi id="Buka Niche Library" en="Open Niche Library" /> <ArrowRight size={14} /></Link>
          </div>
        )}
      </>)}

      {/* A7: saran key_group dari vendor existing (nilai baru tetap boleh) */}
      <datalist id="kg-dl">{[...new Set((data?.ai_providers ?? []).map((p) => String(p.key_group || p.provider_key)))].sort().map((kg) => <option key={kg} value={kg} />)}</datalist>

      {add && ADD_FIELDS[tab] && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setAdd(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong>Tambah {ADD_FIELDS[tab].table}</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setAdd(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {ADD_FIELDS[tab].fields.map(([k, label]) =>
                fieldBlock(tab, k, label, add[k] ?? "", (v) => setAdd({ ...add, [k]: v }), false)
              )}
              {formErr && !formErr.col && <div style={{ color: "var(--danger)", fontSize: "var(--text-xs)" }}>{formErr.node}</div>}
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} onClick={createRow}><Bi id="Simpan" en="Save" /></button>
            </div>
          </div>
        </>
      )}

      {rowEdit && ADD_FIELDS[rowEdit.mapKey] && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setRowEdit(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong>Edit {ADD_FIELDS[rowEdit.mapKey].table}</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setRowEdit(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {ADD_FIELDS[rowEdit.mapKey].fields.map(([k, label]) =>
                fieldBlock(rowEdit.mapKey, k, label, rowEdit.values[k] ?? "", (v) => setRowEdit({ ...rowEdit, values: { ...rowEdit.values, [k]: v } }), k === PK_OF[rowEdit.mapKey], k === PK_OF[rowEdit.mapKey])
              )}
              {(() => {
                // [Jeda-akhir] pratinjau dampak hidup + kunci Simpan saat nilai di luar rentang (§3.1)
                const durPrev = rowEdit.mapKey === "durations" ? durOverridePreview(rowEdit.values) : null;
                return (
                  <>
                    {durPrev?.node}
                    {formErr && !formErr.col && <div style={{ color: "var(--danger)", fontSize: "var(--text-xs)" }}>{formErr.node}</div>}
                    <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} disabled={!!durPrev?.invalid} onClick={saveRowEdit}><Bi id="Simpan" en="Save" /></button>
                  </>
                );
              })()}
            </div>
          </div>
        </>
      )}

      {tm && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => { if (!tmBusy) setTm(null); }} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(460px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}><strong><Bi id="Uji model:" en="Test model:" /> {tm.name}</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} disabled={tmBusy} onClick={() => setTm(null)}><X size={16} /></button></div>
            <p className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}>
              <Bi id="Menjalankan panggilan NYATA sekali ke vendor untuk membuktikan model ini benar jalan di pipeline — uji memakai kuota vendor." en="Runs one REAL call to the vendor to prove this model works in the pipeline — the test uses vendor quota." />{" "}
              {tm.needsKey ? <Bi id="Tempel token uji (TIDAK disimpan), atau kosongkan untuk memakai kunci Test Lab bila tersedia." en="Paste a test token (NOT stored), or leave empty to use the Test Lab key if available." /> : <Bi id="Provider gratis — tanpa kunci." en="Free provider — no key needed." />}{" "}
              <Bi id="Hasil disimpan sebagai jejak audit." en="Result is saved as an audit trail." />
            </p>
            {tm.needsKey && <input className="input" type="password" placeholder="API token uji (kosongkan = kunci Test Lab)" value={tmKey} onChange={(e) => setTmKey(e.target.value)} style={{ marginBottom: "0.6rem" }} />}
            {tmMsg && <div style={{ padding: "0.5rem 0.7rem", borderRadius: 8, marginBottom: "0.6rem", background: tmMsg.ok ? "var(--success-soft, #e6f7ec)" : "var(--warning-soft, #fde7e7)", color: "var(--text-primary)", fontSize: "var(--text-sm)" }}>{tmMsg.ok ? "✅ " : "⚠️ "}{tmMsg.text}</div>}
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost btn-sm" disabled={tmBusy} onClick={() => setTm(null)}><Bi id="Tutup" en="Close" /></button>
              <button className="btn btn-primary btn-sm" disabled={tmBusy} onClick={runTest}>{tmBusy ? <Bi id="Menguji…" en="Testing…" /> : <Bi id="Jalankan uji" en="Run test" />}</button>
            </div>
          </div>
        </>
      )}

      {fUp && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => { if (!uploading) setFUp(null); }} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong><Bi id="Unggah font (→ S3)" en="Upload font (→ S3)" /></strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} disabled={uploading} onClick={() => setFUp(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <div><label className="label"><Bi id="Berkas (.ttf / .otf, maks 10MB)" en="File (.ttf / .otf, max 10MB)" /></label><input className="input" type="file" accept=".ttf,.otf,font/ttf,font/otf" onChange={(e) => setFUp({ ...fUp, file: e.target.files?.[0] ?? null })} /></div>
              {fUp.file && <div className="muted" style={{ fontSize: "0.7rem" }}>{fUp.file.name} · {(fUp.file.size / 1024).toFixed(0)}KB</div>}
              <div><label className="label"><Bi id="Nama font" en="Font name" /></label><input className="input" value={fUp.name} onChange={(e) => setFUp({ ...fUp, name: e.target.value })} placeholder="mis. Oswald / e.g. Oswald" /></div>
              <div className="muted" style={{ fontSize: "0.7rem" }}><Bi id="Nama resmi diambil dari dalam berkas font (agar mesin subtitle menemukannya); isian ini hanya cadangan bila berkas tak memuat nama. Skala render juga dibaca otomatis." en="The official name is taken from inside the font file (so the subtitle engine can find it); this field is only a fallback. Render scale is read automatically too." /></div>
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} disabled={uploading || !fUp.file || !fUp.name.trim()} onClick={uploadFont}>{uploading ? <Bi id="Mengunggah…" en="Uploading…" /> : <Bi id="Unggah ke S3" en="Upload to S3" />}</button>
            </div>
          </div>
        </>
      )}
      {mUp && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => { if (!uploading) setMUp(null); }} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong><Bi id="Unggah musik (→ S3)" en="Upload music (→ S3)" /></strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} disabled={uploading} onClick={() => setMUp(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <div><label className="label">Berkas (.mp3, maks 25MB)</label><input className="input" type="file" accept="audio/mpeg,.mp3" onChange={(e) => onMusicFile(e.target.files?.[0] ?? null)} /></div>
              {mUp.file && <div className="muted" style={{ fontSize: "0.7rem" }}>{mUp.file.name} · {(mUp.file.size / (1024 * 1024)).toFixed(1)}MB{mUp.duration_s ? ` · ${mUp.duration_s}s` : ""}</div>}
              <div><label className="label">Nama</label><input className="input" value={mUp.name} onChange={(e) => setMUp({ ...mUp, name: e.target.value })} /></div>
              <div><label className="label">Niche</label><input className="input" list="mus-niche-dl" value={mUp.niche} onChange={(e) => setMUp({ ...mUp, niche: e.target.value })} placeholder="mis. dark_history" /></div>
              <div><label className="label">Mood</label><input className="input" list="mus-mood-dl" value={mUp.mood} onChange={(e) => setMUp({ ...mUp, mood: e.target.value })} placeholder="mis. dark" /></div>
              <div><label className="label">BPM (opsional)</label><input className="input" value={mUp.bpm} onChange={(e) => setMUp({ ...mUp, bpm: e.target.value })} /></div>
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} disabled={uploading || !mUp.file} onClick={uploadMusic}>{uploading ? "Mengunggah…" : "Unggah ke S3"}</button>
            </div>
          </div>
        </>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "#1f2937", color: "#fff", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 6px 20px rgba(0,0,0,0.35)", fontSize: "var(--text-sm)" }}>{toast}</div>}
    </>
  );
}
