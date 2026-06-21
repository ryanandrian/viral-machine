import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { validateProviderKey, KNOWN_PROVIDERS } from "@/lib/providers/validate-key";

// Validasi NYATA API key (tenant, onboarding/config "Test koneksi"). Butuh sesi login (anti-abuse).
// Key TIDAK disimpan/di-log di sini (hanya divalidasi). Logika validasi (incl. EL scope-aware F1-09)
// = SATU sumber `@/lib/providers/validate-key` (dipakai juga oleh admin Test Lab — nol-duplikat).

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { provider, key } = await req.json().catch(() => ({}));
  if (!provider || !KNOWN_PROVIDERS.includes(provider) || !key?.trim())
    return NextResponse.json({ ok: false, msg: "provider/key tak valid" }, { status: 400 });

  return NextResponse.json(await validateProviderKey(provider, key));
}
