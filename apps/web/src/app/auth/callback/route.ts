// Auth callback (Phase 9.1) — tukar PKCE `code` / `token_hash` jadi session cookie server-side.
// @supabase/ssr default = PKCE: link verify-email / reset / OAuth balik dgn `?code=` (atau
// `?token_hash=&type=` utk template email-OTP). Tanpa exchange ini, SSR/middleware tak lihat session.
// Pola kanonik Supabase App Router (Next 16 route handler). Lihat PHASE9_FRONTEND_WIRING.md §9.1.
import { NextResponse, type NextRequest } from "next/server";
import type { EmailOtpType } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/dashboard";
  const dest = next.startsWith("/") ? `${origin}${next}` : `${origin}/dashboard`; // cegah open-redirect

  const supabase = await createClient();

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(dest);
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) return NextResponse.redirect(dest);
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent("Link tidak valid atau kedaluwarsa.")}`);
}
