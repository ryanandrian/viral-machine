// Auth callback (Phase 9.1) — tukar PKCE `code` / `token_hash` jadi session cookie server-side.
// @supabase/ssr default = PKCE: link verify-email / reset / OAuth balik dgn `?code=` (atau
// `?token_hash=&type=` utk template email-OTP). Tanpa exchange ini, SSR/middleware tak lihat session.
// Pola kanonik Supabase App Router (Next 16 route handler). Lihat PHASE9_FRONTEND_WIRING.md §9.1.
import { NextResponse, type NextRequest } from "next/server";
import type { EmailOtpType } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/dashboard";
  const safeNext = next.startsWith("/") ? next : "/dashboard"; // cegah open-redirect

  // Next.js 16 di belakang reverse-proxy me-resolve `new URL(request.url).origin` ke alamat bind
  // server (localhost:3000), MENGABAIKAN header Host → semua redirect callback nyasar ke localhost.
  // origin publik HARUS diambil dari header yang dikirim nginx (proxy_set_header Host $host).
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? new URL(request.url).host;
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const origin = `${proto}://${host}`;

  const supabase = await createClient();

  // Akun baru tanpa channel → /onboarding, bukan /dashboard (hanya bila next masih default /dashboard).
  const resolveDest = async (): Promise<string> => {
    if (safeNext !== "/dashboard") return safeNext;
    const { count } = await supabase.from("channels").select("id", { count: "exact", head: true });
    return (count ?? 0) > 0 ? "/dashboard" : "/onboarding";
  };

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}${await resolveDest()}`);
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) return NextResponse.redirect(`${origin}${await resolveDest()}`);
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent("Link tidak valid atau kedaluwarsa.")}`);
}
