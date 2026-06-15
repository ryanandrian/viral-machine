// Server-only: panggil "credential vault" Python (webhook_app) yang memegang Fernet + dance OAuth.
// Opsi A (owner): SELURUH enkripsi & tukar-token di server Python — master key TAK pernah ke Vercel.
// X-Internal-Secret meng-otentikasi panggilan; tenant_id sudah diverifikasi pemanggil (sesi Supabase).
const BASE = (process.env.MV_API_BASE || "http://localhost:8088").replace(/\/$/, "");
const SECRET = process.env.MV_INTERNAL_SECRET || "";

export async function vault(path: string, body: Record<string, unknown>): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-internal-secret": SECRET },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}
