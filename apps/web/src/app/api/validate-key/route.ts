import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Validasi NYATA API key (tenant, onboarding/config "Test koneksi"). Panggil endpoint provider dgn key
// yang di-input → ok/gagal. Butuh sesi login (anti-abuse). Key TIDAK disimpan/di-log di sini (hanya divalidasi).
const ENDPOINT: Record<string, (key: string) => { url: string; headers: Record<string, string> }> = {
  anthropic: (k) => ({ url: "https://api.anthropic.com/v1/models", headers: { "x-api-key": k, "anthropic-version": "2023-06-01" } }),
  openai: (k) => ({ url: "https://api.openai.com/v1/models", headers: { Authorization: `Bearer ${k}` } }),
  elevenlabs: (k) => ({ url: "https://api.elevenlabs.io/v1/user", headers: { "xi-api-key": k } }),
};

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { provider, key } = await req.json().catch(() => ({}));
  const make = ENDPOINT[provider];
  if (!make || !key?.trim()) return NextResponse.json({ ok: false, msg: "provider/key tak valid" }, { status: 400 });

  try {
    const { url, headers } = make(key.trim());
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12000);
    const r = await fetch(url, { headers, signal: ctrl.signal });
    clearTimeout(t);
    if (r.ok) return NextResponse.json({ ok: true, msg: "Terhubung · key valid" });
    if (r.status === 401 || r.status === 403) return NextResponse.json({ ok: false, msg: "Key ditolak (401/403)" });
    return NextResponse.json({ ok: false, msg: `HTTP ${r.status}` });
  } catch (e) {
    return NextResponse.json({ ok: false, msg: e instanceof Error ? e.message : "error" });
  }
}
