// Session refresh middleware (Phase 9.1) — @supabase/ssr pola App Router.
// SAAT INI: hanya REFRESH session (NON-BREAKING — mock tetap bisa di-browse tanpa login).
// Hard-redirect proteksi route (app)/* DITAMBAH saat auth-flow ter-wire (9.1 lanjutan).
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

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
  await supabase.auth.getUser();

  return response;
}
