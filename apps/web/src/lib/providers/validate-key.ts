// Validasi NYATA API key provider — SATU sumber dipakai `/api/validate-key` (tenant: onboarding/config)
// + `/api/admin/test-lab` (admin). Hit endpoint provider dgn key yang diberi → {ok, msg}. Key TIDAK
// disimpan/di-log (hanya divalidasi).
//
// F1-09 (REMEDIASI §3.17): ElevenLabs key BYOK ber-scope TTS balas 401 di `/v1/user` (tak punya
// `user_read`) — itu key VALID, bukan ditolak. Bedakan via `detail.status`:
//   - key invalid  → 401 {detail.status:"invalid_api_key"}  (VERIFIED 2026-06-21)
//   - key scoped   → 401 {detail.status:"missing_permissions"} (ter-autentikasi, kurang scope) = VALID
// → cegah false-negative yang memblokir key TTS valid (merugikan onboarding tenant).

export type KeyCheck = { ok: boolean; msg: string };

const TIMEOUT_MS = 12000;

async function probe(url: string, headers: Record<string, string>): Promise<Response> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { headers, signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

// Provider yang validasinya = GET sederhana (200=valid · 401/403=ditolak). Endpoint tak butuh kredit.
async function checkSimple(url: string, headers: Record<string, string>): Promise<KeyCheck> {
  try {
    const r = await probe(url, headers);
    if (r.ok) return { ok: true, msg: "Terhubung · key valid" };
    if (r.status === 401 || r.status === 403) return { ok: false, msg: "Key ditolak (401/403)" };
    return { ok: false, msg: `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, msg: e instanceof Error ? e.message : "error" };
  }
}

// ElevenLabs — SCOPE-AWARE (F1-09). 401/403 dgn detail.status permission = key valid-tapi-scoped.
async function checkElevenLabs(key: string): Promise<KeyCheck> {
  try {
    const r = await probe("https://api.elevenlabs.io/v1/user", { "xi-api-key": key });
    if (r.ok) return { ok: true, msg: "Terhubung · key valid" };
    if (r.status === 401 || r.status === 403) {
      let status = "";
      try {
        const b = await r.json();
        status = String(b?.detail?.status || b?.detail?.message || "").toLowerCase();
      } catch {
        /* body kosong → perlakukan sebagai tak-teridentifikasi (tolak, di bawah) */
      }
      // Key benar-benar SALAH → tolak.
      if (status.includes("invalid_api_key") || status.includes("invalid api key") || status.includes("unusual"))
        return { ok: false, msg: "Key ditolak (tidak valid)" };
      // 401/403 lain (mis. missing_permissions) = key TER-AUTENTIKASI, hanya kurang scope `user_read`.
      // Valid untuk TTS — jangan blokir (akar false-negative F1-09).
      if (status)
        return { ok: true, msg: "Valid · key ber-scope TTS (tanpa akses profil — aman dipakai)" };
      // Body kosong/tak terbaca + 401 → konservatif: tolak (tak bisa pastikan valid).
      return { ok: false, msg: "Key ditolak (401/403)" };
    }
    return { ok: false, msg: `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, msg: e instanceof Error ? e.message : "error" };
  }
}

export const KNOWN_PROVIDERS = ["anthropic", "openai", "elevenlabs"] as const;

export async function validateProviderKey(provider: string, key: string): Promise<KeyCheck> {
  const k = (key || "").trim();
  if (!k) return { ok: false, msg: "key kosong" };
  switch (provider) {
    case "anthropic":
      return checkSimple("https://api.anthropic.com/v1/models", { "x-api-key": k, "anthropic-version": "2023-06-01" });
    case "openai":
      return checkSimple("https://api.openai.com/v1/models", { Authorization: `Bearer ${k}` });
    case "elevenlabs":
      return checkElevenLabs(k);
    default:
      return { ok: false, msg: "provider tak dikenal" };
  }
}
