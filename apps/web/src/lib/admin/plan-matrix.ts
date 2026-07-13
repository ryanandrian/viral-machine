// SATU sumber aturan sel matriks perbandingan (plan_matrix_rows) — dipakai kedua route admin
// (POST induk + PATCH [id]) agar tak ada duplikasi aturan (finalisasi_tier_plan, penguatan owner 2026-07-13).
// Penerjemah tampilan (resolveCell di /pricing) mencocokkan token PERSIS lowercase — maka token yang
// tersimpan WAJIB ternormalisasi di titik input (anti-human-error §3.1: typo kapital mustahil bocor
// ke halaman publik). Teks bebas non-token (mis. "Email", "∞", "custom") disimpan apa adanya.

export const MATRIX_CELLS = ["v_starter", "v_pro", "v_business", "v_enterprise"] as const;

// Token yang dikenali penerjemah /pricing (lihat resolveCell) — jaga selaras bila menambah token baru.
export const MATRIX_TOKENS = [
  "true", "false",
  "auto:max_channels", "auto:max_videos_per_day", "auto:niche_studio",
] as const;

const TOKEN_SET = new Set<string>(MATRIX_TOKENS);

/** Normalisasi nilai sel: trim → kosong = null · token (case-insensitive) = bentuk lowercase kanonik ·
 *  selain itu teks bebas apa adanya. Return {err:true} bila >60 char. */
export function normalizeCell(v: unknown): string | null | { err: true } {
  if (v == null || v === "") return null;
  const s = String(v).trim();
  if (s === "") return null;
  if (s.length > 60) return { err: true };
  const low = s.toLowerCase();
  return TOKEN_SET.has(low) ? low : s;
}
