// Supabase SERVER client (Phase 9.1) — Server Components / Route Handlers. Cookie-based session.
// Next 16: cookies() async. anon key + RLS. Lihat PHASE9_FRONTEND_WIRING.md §1.
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // dipanggil dari Server Component (read-only) — diabaikan; refresh ditangani middleware.
          }
        },
      },
    },
  );
}
