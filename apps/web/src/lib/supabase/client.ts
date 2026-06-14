// Supabase BROWSER client (Phase 9.1) — anon key + RLS (auth.uid()). Dipakai Client Components.
// JANGAN pakai service_role di FE (itu hanya worker/webhook backend). Lihat PHASE9_FRONTEND_WIRING.md §0.
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
