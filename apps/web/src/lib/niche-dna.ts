// NICHE DNA — skema + validasi BERSAMA (klien editor & server API, admin & tenant).
// Sumber kebenaran bentuk = konsumen mesin (audit NICHE_DNA_AUDIT_REMEDIATION.md §1.1):
// - narration_persona: dict string (5 key inti: tone/style/avoid/hook_style/emotion_arc; key ekstra boleh)
// - visual_style: dict string (3 key inti: base_style/color_palette/atmosphere; ekstra: camera/lighting/…)
// - music_config: {mode: auto|random|fixed, mood?, track_id?}
// - mood_priority: string[] (nilai = moods.mood_id)
// - section_timing: {} ATAU LENGKAP 8 key int>0 (validasi ketat script_engine — parsial diabaikan mesin)
// - keywords/default_hashtags/visual_fallbacks: string[]
// - image_quality_tags/image_negative_prompt/emotion_scoring_criteria/style/target_emotion: string
// PENTING: DB tetap JSONB apa adanya — lib ini murni memastikan bentuk yang ditulis SELALU bisa
// dicerna pipeline (kesepakatan owner 2026-07-04: FE bongkar-pasang JSON, mesin tak berubah).

export const PERSONA_KEYS = ["tone", "style", "avoid", "hook_style", "emotion_arc"] as const;
export const VISUAL_CORE_KEYS = ["base_style", "color_palette", "atmosphere"] as const;
export const SECTION_KEYS = ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "curiosity_bridge", "climax", "cta"] as const;
export const MUSIC_MODES = ["auto", "random", "fixed"] as const;
export const MOTION_INTENSITIES = ["halus", "normal", "dinamis", "cepat"] as const;  // Ken Burns per-niche (visual_style.camera_motion)

// Label & penjelasan awam per bagian naskah (dipakai editor; ID/EN)
export const SECTION_LABELS: Record<string, [string, string, string, string]> = {
  hook:              ["Hook pembuka", "Opening hook", "Detik pertama yang menahan jempol penonton", "The first seconds that stop the scroll"],
  mystery_drop:      ["Umpan misteri", "Mystery drop", "Janji jawaban yang bikin bertahan", "The promise that keeps them watching"],
  build_up:          ["Membangun cerita", "Build up", "Konteks & ketegangan menuju inti", "Context & tension toward the core"],
  pattern_interrupt: ["Kejutan pola", "Pattern interrupt", "Selingan singkat pengusir bosan", "A quick jolt against boredom"],
  core_facts:        ["Fakta inti", "Core facts", "Isi utama yang dijanjikan", "The main promised content"],
  curiosity_bridge:  ["Jembatan penasaran", "Curiosity bridge", "Transisi yang memancing ke klimaks", "Transition teasing the climax"],
  climax:            ["Klimaks", "Climax", "Momen emosi tertinggi", "The emotional peak"],
  cta:               ["Ajakan penutup", "Closing CTA", "Penutup + ajakan (ikut cta_mode channel)", "Closer + call-to-action"],
};

export type DnaErrors = Record<string, string>;

const isStr = (v: unknown): v is string => typeof v === "string";
const isStrArr = (v: unknown): v is string[] => Array.isArray(v) && v.every(isStr);
const isStrDict = (v: unknown): v is Record<string, string> =>
  !!v && typeof v === "object" && !Array.isArray(v) && Object.values(v as object).every(isStr);

// Validasi patch DNA (subset field boleh). Return errors per-field (kosong = valid).
// Dipakai SERVER (tolak + pesan — pengganti silent-skip) dan KLIEN (disable Simpan + pesan inline).
export function validateDnaPatch(patch: Record<string, unknown>): DnaErrors {
  const e: DnaErrors = {};
  const has = (k: string) => k in patch && patch[k] !== undefined;

  if (has("name") && (!isStr(patch.name) || !(patch.name as string).trim())) e.name = "Nama tidak boleh kosong.";
  for (const k of ["style", "target_emotion", "image_quality_tags", "image_negative_prompt", "emotion_scoring_criteria"]) {
    if (has(k) && patch[k] !== null && !isStr(patch[k])) e[k] = "Harus berupa teks.";
  }
  for (const k of ["keywords", "default_hashtags", "visual_fallbacks", "mood_priority"]) {
    if (has(k) && !isStrArr(patch[k])) e[k] = "Harus berupa daftar teks.";
  }
  if (has("narration_persona") && !isStrDict(patch.narration_persona)) e.narration_persona = "Setiap isian persona harus teks.";
  if (has("visual_style")) {
    const vs = patch.visual_style as Record<string, unknown>;
    if (!vs || typeof vs !== "object" || Array.isArray(vs)) e.visual_style = "Gaya visual tidak valid.";
    else {
      // camera_motion = objek bersarang (Ken Burns); sisanya WAJIB teks.
      const { camera_motion: cm, ...flat } = vs;
      if (!isStrDict(flat)) e.visual_style = "Setiap isian gaya visual harus teks.";
      else if (cm !== undefined) {
        const inten = (cm as Record<string, unknown> | null)?.intensity;
        if (!cm || typeof cm !== "object" || Array.isArray(cm) || !MOTION_INTENSITIES.includes(inten as typeof MOTION_INTENSITIES[number]))
          e.visual_style = `Intensitas gerak kamera harus salah satu: ${MOTION_INTENSITIES.join("/")}.`;
      }
    }
  }

  if (has("music_config")) {
    const mc = patch.music_config as Record<string, unknown>;
    if (!mc || typeof mc !== "object" || Array.isArray(mc)) e.music_config = "Konfigurasi musik tidak valid.";
    else {
      const mode = String(mc.mode ?? "auto");
      if (!MUSIC_MODES.includes(mode as typeof MUSIC_MODES[number])) e.music_config = `Mode musik harus salah satu: ${MUSIC_MODES.join("/")}.`;
      else if (mode === "fixed" && !isStr(mc.track_id)) e.music_config = "Mode 'satu lagu tetap' butuh pilihan track.";
      else if (mode === "random" && mc.mood != null && !isStr(mc.mood)) e.music_config = "Mood harus teks.";
    }
  }

  if (has("section_timing")) {
    const st = patch.section_timing as Record<string, unknown>;
    if (!st || typeof st !== "object" || Array.isArray(st)) e.section_timing = "Struktur durasi tidak valid.";
    else if (Object.keys(st).length > 0) {
      const missing = SECTION_KEYS.filter((k) => !(k in st));
      const bad = SECTION_KEYS.filter((k) => k in st && (!Number.isFinite(Number(st[k])) || Number(st[k]) <= 0));
      if (missing.length) e.section_timing = `Harus LENGKAP 8 bagian (mesin mengabaikan yang parsial). Kurang: ${missing.join(", ")}.`;
      else if (bad.length) e.section_timing = `Durasi harus angka detik > 0: ${bad.join(", ")}.`;
    }
  }
  return e;
}

// Kolom DNA yang di-copy saat buat niche baru dari template (wizard — keputusan owner: copy-dari-base).
// keywords/hashtags/fallbacks TIDAK di-copy (spesifik topik niche — harus milik niche baru).
export const TEMPLATE_COPY_COLUMNS = [
  "style", "target_emotion", "narration_persona", "visual_style", "mood_priority",
  "emotion_scoring_criteria", "section_timing", "image_quality_tags", "image_negative_prompt",
  "music_config", "youtube_category_id",
] as const;
