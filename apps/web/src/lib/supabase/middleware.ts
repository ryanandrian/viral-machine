// Session refresh + proteksi route (Phase 9.1) — @supabase/ssr pola App Router.
// REFRESH session tiap request + HARD-REDIRECT route ter-proteksi (no session → /auth).
// Publik: marketing (/, /pricing, …), /auth, /auth/callback. Ter-proteksi: app/onboarding/admin.
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Prefix yang WAJIB login tenant. (app) route-group tak muncul di URL → cek path nyata tiap layar.
// /admin DITANGANI TERPISAH (gate super-admin di bawah), BUKAN di sini.
const PROTECTED = [
  "/dashboard", "/channels", "/runs", "/analytics", "/insights",
  "/compliance", "/config", "/schedule", "/settings", "/billing",
  "/onboarding", "/support",
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

  const path = request.nextUrl.pathname;
  const isSuperAdmin = user?.app_metadata?.role === "super_admin";

  // ── Gate ADMIN (super-admin only) ──
  // /admin/login = PUBLIK (jalur masuk admin). Sudah super-admin → langsung ke panel.
  if (path === "/admin/login") {
    if (isSuperAdmin) {
      const url = request.nextUrl.clone();
      url.pathname = "/admin/tenants";
      url.search = "";
      return NextResponse.redirect(url);
    }
    return response;
  }
  // /admin/* lain: wajib super-admin. No session → /admin/login; tenant biasa → /dashboard (bukan miliknya).
  if (path === "/admin" || path.startsWith("/admin/")) {
    if (!user) {
      const url = request.nextUrl.clone();
      url.pathname = "/admin/login";
      url.search = `?next=${encodeURIComponent(path)}`;
      return NextResponse.redirect(url);
    }
    if (!isSuperAdmin) {
      const url = request.nextUrl.clone();
      url.pathname = "/dashboard";
      url.search = "";
      return NextResponse.redirect(url);
    }
    return response;
  }

  // ── Route TENANT ter-proteksi ──
  const isProtected = PROTECTED.some((p) => path === p || path.startsWith(`${p}/`));
  // Super-admin TIDAK boleh masuk panel tenant (jalur terpisah — owner 2026-06-15) → balik ke /admin.
  // Mau rasakan sisi tenant = pakai akun tenant khusus, bukan akun admin.
  if (isProtected && isSuperAdmin) {
    const url = request.nextUrl.clone();
    url.pathname = "/admin/tenants";
    url.search = "";
    return NextResponse.redirect(url);
  }
  // Hard-redirect: tanpa session → /auth (simpan tujuan di ?next).
  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth";
    url.search = `?view=login&next=${encodeURIComponent(path)}`;
    return NextResponse.redirect(url);
  }

  return response;
}
