// Session refresh + proteksi route (Phase 9.1) — @supabase/ssr pola App Router.
// REFRESH session tiap request + HARD-REDIRECT route ter-proteksi (no session → /auth).
// Publik: marketing (/, /pricing, …), /auth, /auth/callback. Ter-proteksi: app/onboarding/admin.
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Prefix yang WAJIB login. (app) route-group tak muncul di URL → cek path nyata tiap layar.
const PROTECTED = [
  "/dashboard", "/channels", "/runs", "/analytics", "/insights",
  "/compliance", "/config", "/schedule", "/settings", "/billing",
  "/onboarding", "/admin",
];

export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // WAJIB: refresh token (jangan ada logika antara createServerClient & getUser — pola @supabase/ssr).
  const { data: { user } } = await supabase.auth.getUser();

  // Hard-redirect: route ter-proteksi tanpa session → /auth (simpan tujuan di ?next).
  const path = request.nextUrl.pathname;
  const isProtected = PROTECTED.some((p) => path === p || path.startsWith(`${p}/`));
  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth";
    url.search = `?view=login&next=${encodeURIComponent(path)}`;
    return NextResponse.redirect(url);
  }

  return response;
}
