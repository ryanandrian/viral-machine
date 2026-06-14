// Root middleware (Phase 9.1) — refresh Supabase session tiap request.
// Proteksi route (redirect ke /auth bila no session) ditambah saat auth-flow ter-wire.
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  // Skip aset statis; jalankan di route lain (refresh session).
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
